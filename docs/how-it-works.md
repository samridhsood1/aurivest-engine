# Aurivest, end to end: what we built, how it works, why it wins

Written 2026-07-23 for the founder to study and defend (YC + diligence). Every
number here is reproducible from the repo; where evidence is external or a value
is illustrative, it says so.

---

## 1. The business in one paragraph

Ontario bills its largest electricity consumers (Class A) a charge called the
**Global Adjustment (GA)** — the dominant line on the bill, routinely **70–85%**
of the commodity cost. Under the **Industrial Conservation Initiative (ICI)**, a
Class A customer's *entire annual GA bill* is set by its share of provincial
demand during just **five hours a year** — the "five coincident peaks" (5CP), the
five highest-demand hours of the base period (May 1–Apr 30), each on a different
day. Shave your load during those five hours and your GA bill falls almost
proportionally. The prize is roughly **$350–400k per MW of avoided peak, per
year** (IESO 2024/25 PDF rate; verify on-runner before quoting).

Aurivest **owns and operates a battery behind a client's meter**, predicts those
five hours, and discharges to erase the client's contribution — then stacks
additional revenue (capacity auction, demand response, energy arbitrage) on the
same asset. **The whole game is (a) predicting the five hours and (b) dispatching
against that prediction under a limited energy budget.** This repo is (a) and (b).

Why it's hard, and why it's a moat: the 5CP is **not a passive weather outcome —
it is an actively-defended, self-deforming target.** In 2025 roughly **2,116 MW**
was *intentionally shaved* off the observed provincial peak (ICI + Peak Perks +
capacity auction), and that number grows every year. The peak is a *fixed point of
everyone's forecast* — Goodhart's law on the target. A competitor watching only
temperature gets the timing wrong; the winner models the **net load after the
collective response**, and does it with a live, continuously-retrained data flow
that a static model can't copy.

---

## 2. The predictor — the core idea

**We do not classify "is this a peak?"** With only ~5 peak events a year (~120 in
24 years), that target is far too rare to learn a rich model on — it would
catastrophically overfit. Instead we predict the **continuous net-load curve**:
every hour of every day is a training example (~210k rows), a data-abundant
regression problem. The peak ranking and the dispatch decision are *derived on top*
of that calibrated curve. (This "regress the curve, don't classify the rare event"
choice is the single most important design decision, and the literature backs it —
Jiang et al. 2014 solve Ontario's 5CP exactly this way.)

**Net load, not gross demand.** The five peaks are set by *net* load = consumption
minus embedded/behind-the-meter generation (rooftop solar, wind). As rooftop solar
grew, the net-load peak **shifted later into the evening** (the "duck curve") — the
peak now lands when solar fades and demand is still high, not at max temperature.
A gross-demand model misplaces the hour; we model the demand stack and the
embedded-generation stack and their interaction. (This is why the solar/irradiance
feature work matters — see §4.)

**Probabilistic, not a point.** We predict **quantiles** (q05, q25, q50, q75, q95)
of net load per hour, so the dispatch layer sees the *distribution* and its
uncertainty, not a single guess. This is what lets us act on a cost-asymmetric
operating point (§3).

---

## 3. The model architecture (what actually runs)

We built and tested a **committee of diverse experts** and a combiner, then — on
the evidence — simplified to an **NN-primary** design. The honest path:

**The experts** (each a calibrated quantile model, `src/predictor/forecast/`):
- **Gradient-boosted trees** (LightGBM, `netload.py`) — the junk-robust,
  well-calibrated base. Best-evidenced model class for tabular data (won the M5
  competition's point *and* quantile tracks).
- **Neural net** (`nn_model.py`, `QuantileNN`) — an MLP with 5 joint quantile
  heads on the pinball loss, seed-ensembled. **The best single model on our tests**
  (pinball 94.3, captured 4.2/5 peaks). It adapts to the shifting regime where the
  saturated tree plateaus.
- **Linear-spline** (`committee.py`) — a smooth, *linear-extrapolating* floor. It
  can't erupt like an MLP, and crucially it *doesn't saturate* at a record (trees
  flatline past their training range; this one extrapolates).
- **Quantile random forest** — bagging vs boosting, a decorrelated error profile.

**The combiner decision, made on evidence, not vibe.** We first built a *bounded
gating master* that convex-averages the experts. It is survivable (its output
can't leave the experts' envelope) but we **measured** that it *under-shoots the
peak by 266 MW more than the best expert* on the top-0.5% hours — it **holds the
NN back**. Three independent research passes (all cited in `HANDOFF.md`) explained
why: **averaging quantiles is provably "always sharper" — it shrinks the upper tail
and deletes the lone record-warning** (Lichtendahl 2013). So we removed the
averaging master. **The NN leads.**

**How the NN is made un-failable *without* being held back** (`primary.py`,
`NnPrimary`) — three thin, *asymmetric* safety layers instead of an average:
1. **OOD blow-up guards** (input winsorization + output envelope): a broken run
   can't emit garbage. (Fixed a real failure where the NN blew up to 10× on a thin
   season.)
2. **Crisis-conditional EVT upper tail**: in a heat crisis (forecast temperature in
   its upper regime) we *extend* the upper quantiles with a Generalized-Pareto tail
   fit to historical exceedances — so a genuine record goes **higher** than the
   training range instead of clamping. This cut peak-misses on crisis hours from
   **8% → 1%**. Boosted trees structurally cannot do this (Browell-Fasiolo 2021).
3. **Isolated-failure floor**: only if the NN diverges grossly from the stable
   models *with no crisis signal* do we pull it back — a lone failure is caught, a
   *consensus* extreme (real crisis) is trusted. This is your "don't let an expert
   fail, but don't hold it back in a crisis," written as math (a robust aggregator's
   breakdown point = the tolerated blow-up fraction; Huber 1964).

**The operating point is cost-asymmetric.** Missing a 5CP peak is ~19× costlier
than a false alarm, so the dispatch acts on a **high quantile** (≈0.90), not the
median. Predicting the median is *why* an averaging model holds back; operating high
is why NN-primary captures **4.2/5 peaks at 5 alert days** vs the master's 3.4.

---

## 4. The data — the real moat

The predictor is only as good as the signal, and this is where a rigorous shop
pulls ahead. What we feed it, and why:

- **Weather, load-weighted and GTA-heavy** (ECCC, 8 stations, 2002–2026): dry-bulb
  temperature (the dominant driver, ~+345 MW/°C above 20°C), and the **humidity
  family** (dew point, humidex) — "the most underused high-value signal"; a humid
  32° day draws far more AC than a dry one. Plus heat-wave persistence (day 3 > day
  1, buildings heat-soak), overnight lows, and lagged/rolling temperature.
- **Real forecast vintages** (NBM): we train on the *forecast* weather that would
  have been known at decision time, never the realized weather — the single most
  common, most fatal backtesting mistake, which our bitemporal store prevents by
  construction (§5).
- **Irradiance / the duck curve** (NASA POWER, since NREL's endpoint is DNS-dead
  from every environment we run in): all-sky + clear-sky GHI → a *clearness index*
  and cloud-loss signal that drives embedded solar and thus the net-peak *timing*.
- **Supply-side tightness** (IESO): per-fuel supply and outage forecasts, wind
  generation (near-zero on the hot still evenings when you need it — a supply
  crunch), intertie import headroom, embedded-generation forecast.
- **The adversarial layer** (the research-identified edge): the growing
  **reflexive-capacity bundle** — ICI + demand-response + storage MW enrolled, year
  over year — so the model *sees the defense growing* and doesn't confidently
  over-predict a peak that everyone else will shave flat.

**Discipline: guilty-until-proven-noise.** We do not drop a feature by intuition.
A permutation-importance tool on the junk-robust tree *measures* each feature's
incremental signal (interactions included), and nothing is called noise without
that measurement. The full universe was tested; the ~86-feature calibrated set the
NN runs on is the *measured* signal subset, while the tree can safely hold more.

---

## 5. How it's coded (the engineering that makes it defensible)

- **Bitemporal store** (`src/predictor/store/`): every record carries an
  `event_time` (when it happened) and a `knowledge_time` (when we learned it).
  Every read is `as_of(decision_time)`. There is **no separate live path** — the
  backtest and the live system are the *same code* reading the same store at a
  different `as_of`. This is the anti-leakage guarantee and the reproducibility
  guarantee in one, and it is also the **evidentiary record** a diligence team or a
  tribunal can replay years later.
- **Config-driven ingestion** (`src/predictor/ingest/` + `config/sources/*.yaml`):
  one module per source family; anomalies are documented in YAML, never absorbed in
  code. Full backfills fail loud on validation — the dangerous failure mode is
  *confident-wrong*, not a crash.
- **Feature assembly** (`features/matrix.py`): as-of feature matrices; calendar
  features derived in local Eastern time; the leakage harness proves as-of reads
  never return a value before its `knowledge_time`.
- **Forecasting** (`forecast/`): `netload.py` (tree stack), `nn_model.py` (the NN),
  `committee.py` (experts + the — now retired — master), `primary.py` (NN-primary),
  `search.py` + `search_netload.py` (the registered hyperparameter search harness).
- **Walk-forward evaluation** (`backtest/walkforward.py`): expanding-window, one
  training example per hour, evaluated on held-out future seasons — and the models
  are **selection-clean** (hyperparameters tuned on ≤2014, gated on 2015–2026).
- **The single-writer data pipeline** (GitHub Actions): the data store is written
  *only* by CI — every developer clone is read-only — so the live data flow is a
  controlled, auditable asset, not a pile of local files.
- **Ops reality we solved**: torch and LightGBM each bundle their own OpenMP and
  segfault together on Apple Silicon (fixed by pinning torch single-thread); the
  harness reaps background jobs (fixed by detached, resume-safe runs). These aren't
  incidental — a commercial system has to survive its own infrastructure.

---

## 6. The revenue stack (how the asset pays)

Priority order (the founder's: "first the CP should be peak"):

1. **GA / 5CP avoidance — the primary.** Capture the five peak hours, shave the
   client's peak-demand factor, cut ~70%+ of their GA. ~$350–400k/MW-yr of avoided
   peak. This is the anchor and the moat (it needs the predictor).
2. **Capacity auction** — storage is explicitly eligible; the December 2025 auction
   cleared near record highs. An availability *obligation* that competes with
   discretionary 5CP dispatch — the optimizer trades these off (Layer 4).
3. **Demand response** — the client/IESO calls DR events; we log when DR was asked
   and dispatch into them. Overlaps with, and must be de-conflicted against, the
   5CP shave.
4. **Energy arbitrage** — charge cheap, discharge dear on the OEMP curve, on the
   hours not reserved for the above.

The dispatch engine (`optimizer/`, `settlement/streams.py`) already stacks these
and books them correctly (a settlement bug where recharge cost was mispriced was
found and fixed — the clairvoyant upper bound is a bound again). The **new
NN-primary forecast plugs straight into this** as a better input; the recent
diagnostic had the engine at ~$2.7M/season on a single site, ~75% of the
perfect-foresight ceiling — the gap the better forecast attacks.

---

## 7. Why we win — the defensible edges (the YC answer)

1. **We predict *net load after the collective response*, not gross demand.** The
   target is adversarial and shifting; we model that explicitly. Competitors
   watching temperature misplace the peak hour as solar and storage grow.
2. **The moat is the data *flow*, not a model file.** Continuously-refreshed,
   bitemporal, retrained on schedule. A seized or copied model goes stale the day
   it's cut from the flow — that's the moat working as designed.
3. **We own and operate the asset** (the structural inverse of Stem Inc, which
   resold hardware at thin margins and blew up). Recurring grid-market value over
   the asset life, no hardware residual risk, ROI not vanity bookings.
4. **Survivable autonomy.** The predictor is built to *not go bankrupt in a crisis*
   before there's a trading desk: the NN can't blow up (guards), can't be held back
   in a crisis (EVT upper tail + high operating quantile), and fails *loud* to a
   conservative fallback rather than confidently wrong.
5. **Legibility as diligence-defense.** Every decision is reconstructable from a
   logged, vintage-stamped snapshot — the going-concern record that can't be
   reconstructed retroactively.

**Honest risks to state, not hide** (this is what a good YC answer does): capital
intensity (financing-access risk, not negative-unit-economics), ITC dependence
(model a reduced-ITC case), interconnection timing, and at-scale GA drift once the
fleet is large enough to move the provincial peak. And the honest technical caveat:
no published result shows a model *combination* beating the best *single* model on
peak capture specifically, which is exactly why we went NN-primary and why the
combiner must *earn* its keep on the captured-peak gate before it ships.

---

## 8. Honest state (what's built vs next)

**FINAL NUMBERS (2026-07-24 rebuild-to-best):** primary = guarded-NN (test pinball 89.6, 19/25 peak-days; guard trigger 0.01%); rebuilt tree failsafe 97.6; dispatcher 95% 5CP capture (81/85 over 17 seasons), ~$5.39M/yr per 10 MW site; master empirically scrapped (93.0/18 - not better than the best single expert).

**Built + validated:** the bitemporal store + ingestion; the net-load forecasting
layer (gated — beats the pre-registered baselines, 22/22 seasons); the committee
experts; the NN-primary predictor with crisis-aware bounds (captures 4.2/5 peaks,
1% crisis-miss); the captured-peak metric; the dispatch + settlement engine.

**Next (in priority):** train the all-data deployment NN; wire NN-primary through
the dispatch for the captured-peak-revenue backtest and gate it on peaks-captured /
stacked revenue (not RMSE); land the reflexive-capacity + solar features through the
permutation-importance gate; the layer-3 P(top-5) ranking calibration; and the
shadow-season live track record (build-plan step 14 — live and backtest are the same
code path).
