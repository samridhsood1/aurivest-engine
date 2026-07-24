"""The room of experts and the bounded gating master (the 'expert of experts').

Founder direction (2026-07-23): don't pick gbt-vs-nn; build a committee whose
members cover each other's failure modes, then a master NN that learns, from the
raw context, HOW MUCH to trust each expert where. Survivability is structural:
the master emits convex (softmax, sum-to-1) weights, so the final quantiles are a
weighted average of the experts and can NEVER leave their envelope - it can weigh
but never fabricate a blow-up. That is the gatekeeper that has no off-switch.

Members (each matches netload.QuantileModel's fit/predict/feature_columns):
  - LightGBM quantile stack (netload.QuantileModel)   - junk-robust, calibrated.
  - QuantileNN (nn_model)                             - high-capacity, adaptive.
  - LinearSplineQuantile (here)                       - smooth linear-extrapolating
        floor: spline bases on the key continuous drivers + linear on the rest,
        one linear quantile head per tau. Cannot erupt like an MLP; extrapolates
        the capacity/temperature trend smoothly past the training range.

GatingMaster (here) consumes every member's quantile vector + a context subset +
the members' disagreement, and outputs per-row convex weights over members.

Determinism + the torch<>lightgbm libomp single-thread pin are inherited by
importing nn_model (its module top pins the threads)."""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field

import numpy as np
import polars as pl
import torch
from torch import nn

from .nn_model import (TAUS, ENSEMBLE_SEEDS, feature_columns, pinball_loss,
                       _seed_everything, _configure_determinism, _resolve_device)

# Continuous drivers worth spline bases (from the doc + permutation importance):
# temperature (nonlinear cooling response), its lags/rolls, sunset geometry,
# dew point (latent AC load), and the dominant demand lags.
SPLINE_HINTS = ("temp", "dew_point", "hours_to_sunset", "day_length",
                "demand_lag", "demand_latest", "demand_min", "heat_stress")


def _spline_basis(x: np.ndarray, knots: np.ndarray) -> np.ndarray:
    """Piecewise-linear (hat) spline bases at `knots` for one column: returns the
    column plus max(0, x-knot) hinges. Linear outside the outer knots -> smooth
    linear extrapolation (the stable-floor property), no scikit dependency."""
    hinges = [np.maximum(0.0, x[:, None] - knots[None, :])]
    return np.concatenate([x[:, None], *hinges], axis=1)


@dataclass
class LinearSplineQuantile:
    """Smooth linear-extrapolating quantile floor. Spline bases on the continuous
    drivers + linear terms on the rest; one linear head per tau on pinball loss.
    Extrapolates linearly (can't blow up), calibrated, cheap. Same contract as
    netload.QuantileModel so it slots into the committee/harness unchanged."""
    taus: tuple[float, ...] = TAUS
    seeds: tuple[int, ...] = (7,)         # linear + convex loss -> 1 seed suffices
    n_jobs: int | None = None
    device: str | None = "cpu"
    n_knots: int = 6
    input_clip: float = 6.0
    lr: float = 5e-3
    max_epochs: int = 300
    features: list[str] = field(default_factory=list)
    _spline_cols: list[int] = field(default_factory=list, repr=False)
    W: object = field(default=None, repr=False)

    def _design(self, x: np.ndarray, fit: bool) -> np.ndarray:
        cols = []
        for j in range(x.shape[1]):
            col = x[:, j]
            if j in self._spline_cols:
                if fit:
                    qs = np.linspace(0, 1, self.n_knots + 2)[1:-1]
                    self._knots.setdefault(j, np.nanquantile(col, qs))
                cols.append(_spline_basis(col, self._knots[j]))
            else:
                cols.append(col[:, None])
        return np.concatenate(cols, axis=1)

    def fit(self, m: pl.DataFrame) -> "LinearSplineQuantile":
        _configure_determinism()
        if self.n_jobs is not None:
            torch.set_num_threads(max(1, self.n_jobs))
        self.features = feature_columns(m)
        self._spline_cols = [i for i, c in enumerate(self.features)
                             if any(h in c for h in SPLINE_HINTS)]
        self._knots: dict[int, np.ndarray] = {}
        x = m.select(self.features).to_numpy().astype(np.float64)
        x = np.where(np.isfinite(x), x, np.nan)
        self._med = np.where(np.isfinite(np.nanmedian(x, axis=0)),
                             np.nanmedian(x, axis=0), 0.0)
        x = np.where(np.isnan(x), self._med, x)
        d = self._design(x, fit=True)
        self._mean, self._std = d.mean(0), np.where(d.std(0) < 1e-8, 1.0, d.std(0))
        d = np.clip((d - self._mean) / self._std, -self.input_clip, self.input_clip)
        y = m["y"].to_numpy().astype(np.float64)
        self._ym, self._ys = float(np.nanmean(y)), max(float(np.nanstd(y)), 1e-8)
        dev = _resolve_device(self.device)
        xt = torch.tensor(d, dtype=torch.float32, device=dev)
        yt = torch.tensor((y - self._ym) / self._ys, dtype=torch.float32, device=dev)
        taus_t = torch.tensor(self.taus, device=dev).view(1, -1)
        _seed_everything(self.seeds[0])
        lin = nn.Linear(d.shape[1], len(self.taus)).to(dev)
        opt = torch.optim.Adam(lin.parameters(), lr=self.lr, weight_decay=1e-6)
        for _ in range(self.max_epochs):
            opt.zero_grad()
            loss = pinball_loss(lin(xt), yt, taus_t)
            loss.backward(); opt.step()
        self.W = lin
        self._dev = dev
        return self

    def predict(self, m: pl.DataFrame) -> pl.DataFrame:
        x = m.select(self.features).to_numpy().astype(np.float64)
        x = np.where(np.isfinite(x), x, np.nan)
        x = np.where(np.isnan(x), self._med, x)
        d = self._design(x, fit=False)
        d = np.clip((d - self._mean) / self._std, -self.input_clip, self.input_clip)
        with torch.no_grad():
            p = self.W(torch.tensor(d, dtype=torch.float32, device=self._dev)).cpu().numpy()
        p = np.sort(p * self._ys + self._ym, axis=1)
        return m.with_columns(**{f"q{int(t*100):02d}": pl.Series(p[:, i])
                                 for i, t in enumerate(self.taus)})


@dataclass
class QuantileForest:
    """Quantile Random Forest (Meinshausen 2006, via the quantile-forest pkg):
    bagged trees with EMPIRICAL leaf quantiles - a genuinely different bias from
    the boosted LightGBM stack (bagging not boosting; empirical not pinball-fit
    quantiles), so its errors decorrelate from the tree expert. That decorrelation
    is precisely what lets a convex master beat its best single member. Subsamples
    training for tractability. Same fit/predict contract as the other experts."""
    taus: tuple[float, ...] = TAUS
    seeds: tuple[int, ...] = (7,)
    n_jobs: int | None = None
    n_estimators: int = 300
    min_samples_leaf: int = 40
    max_train: int = 90000
    features: list[str] = field(default_factory=list)
    rf: object = field(default=None, repr=False)

    def fit(self, m: pl.DataFrame) -> "QuantileForest":
        from quantile_forest import RandomForestQuantileRegressor
        self.features = feature_columns(m)
        x = m.select(self.features).to_numpy().astype(np.float64)
        x = np.where(np.isfinite(x), x, np.nan)
        med = np.nanmedian(x, axis=0)
        self._med = np.where(np.isfinite(med), med, 0.0)
        x = np.where(np.isnan(x), self._med, x)
        y = m["y"].to_numpy()
        if len(y) > self.max_train:                       # RF on ~180k rows is slow
            idx = np.random.default_rng(self.seeds[0]).choice(len(y), self.max_train, replace=False)
            x, y = x[idx], y[idx]
        self.rf = RandomForestQuantileRegressor(
            n_estimators=self.n_estimators, min_samples_leaf=self.min_samples_leaf,
            random_state=self.seeds[0], n_jobs=self.n_jobs or -1).fit(x, y)
        return self

    def predict(self, m: pl.DataFrame) -> pl.DataFrame:
        x = m.select(self.features).to_numpy().astype(np.float64)
        x = np.where(np.isfinite(x), x, np.nan)
        x = np.where(np.isnan(x), self._med, x)
        q = np.sort(self.rf.predict(x, quantiles=list(self.taus)), axis=1)
        return m.with_columns(**{f"q{int(t*100):02d}": pl.Series(q[:, i])
                                 for i, t in enumerate(self.taus)})


class _Gate(nn.Module):
    """context -> softmax weights over E experts (convex combination)."""
    def __init__(self, ctx_dim: int, n_experts: int, hidden: int = 64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(ctx_dim, hidden), nn.ReLU(), nn.Dropout(0.1),
            nn.Linear(hidden, hidden), nn.ReLU(),
            nn.Linear(hidden, n_experts))

    def forward(self, ctx):                    # ctx: (B, ctx_dim)
        return torch.softmax(self.net(ctx), dim=1)   # (B, E), rows sum to 1


@dataclass
class GatingMaster:
    """The expert-of-experts. Learns per-row convex weights over the members from
    the raw context + the members' medians + their disagreement, then returns the
    weighted-average quantile vector. Output is bounded by the members' envelope
    BY CONSTRUCTION (weights >= 0, sum to 1) - it cannot blow up, so it can safely
    down-weight a haywire member without any member being able to poison the
    result. taus and expert order are fixed at fit."""
    taus: tuple[float, ...] = TAUS
    ctx_features: tuple[str, ...] = ()        # raw context the gate sees
    seeds: tuple[int, ...] = ENSEMBLE_SEEDS
    device: str | None = "cpu"
    lr: float = 1e-3
    max_epochs: int = 150
    patience: int = 12
    hidden: int = 64
    n_experts: int = 0
    gates: list = field(default_factory=list, repr=False)

    def _ctx(self, ctx_df: pl.DataFrame, P: np.ndarray) -> np.ndarray:
        # gate input = raw context features + each expert's median + cross-expert
        # disagreement (std of medians) so it can learn "when they disagree here,
        # trust member k". P: (N, E, T).
        j = self.taus.index(0.5)
        meds = P[:, :, j]                                    # (N, E)
        raw = (ctx_df.select(list(self.ctx_features)).to_numpy()
               if self.ctx_features else np.zeros((P.shape[0], 0)))
        disagree = meds.std(axis=1, keepdims=True)
        c = np.concatenate([raw, meds, disagree], axis=1).astype(np.float64)
        c = np.where(np.isfinite(c), c, 0.0)
        return c

    def fit(self, P: np.ndarray, y: np.ndarray, ctx_df: pl.DataFrame) -> "GatingMaster":
        # P: (N, E, T) out-of-fold expert quantiles; y: (N,) realized net load.
        _configure_determinism()
        self.n_experts = P.shape[1]
        c = self._ctx(ctx_df, P)
        self._cm, self._cs = c.mean(0), np.where(c.std(0) < 1e-8, 1.0, c.std(0))
        c = (c - self._cm) / self._cs
        dev = _resolve_device(self.device)
        n = len(y); rng = np.random.default_rng(0)
        perm = rng.permutation(n); nval = max(1, int(0.15 * n))
        vi, ti = perm[:nval], perm[nval:]
        Pt = torch.tensor(P, dtype=torch.float32, device=dev)
        ct = torch.tensor(c, dtype=torch.float32, device=dev)
        yt = torch.tensor(y, dtype=torch.float32, device=dev)
        taus_t = torch.tensor(self.taus, device=dev).view(1, -1)
        self.gates = []
        for seed in self.seeds:
            _seed_everything(seed)
            g = _Gate(c.shape[1], self.n_experts, self.hidden).to(dev)
            opt = torch.optim.Adam(g.parameters(), lr=self.lr, weight_decay=1e-5)
            best, bad, best_state = float("inf"), 0, None
            for _ in range(self.max_epochs):
                g.train(); opt.zero_grad()
                w = g(ct[ti])                                # (b, E)
                q = torch.einsum("be,bet->bt", w, Pt[ti])    # convex combo -> (b, T)
                loss = pinball_loss(q, yt[ti], taus_t)
                loss.backward(); opt.step()
                g.eval()
                with torch.no_grad():
                    wv = g(ct[vi]); qv = torch.einsum("be,bet->bt", wv, Pt[vi])
                    v = pinball_loss(qv, yt[vi], taus_t).item()
                if v < best - 1e-6:
                    best, bad, best_state = v, 0, {k: t.clone() for k, t in g.state_dict().items()}
                else:
                    bad += 1
                    if bad >= self.patience:
                        break
            if best_state:
                g.load_state_dict(best_state)
            self.gates.append(g)
        self._dev = dev
        return self

    def predict(self, P: np.ndarray, ctx_df: pl.DataFrame) -> np.ndarray:
        c = (self._ctx(ctx_df, P) - self._cm) / self._cs
        Pt = torch.tensor(P, dtype=torch.float32, device=self._dev)
        ct = torch.tensor(c, dtype=torch.float32, device=self._dev)
        outs = []
        with torch.no_grad():
            for g in self.gates:
                g.eval()
                w = g(ct)
                outs.append(torch.einsum("be,bet->bt", w, Pt).cpu().numpy())
        q = np.mean(outs, axis=0)
        q.sort(axis=1)                          # taus monotone (convex combo keeps it, sort is belt-and-braces)
        return q

    def weights(self, P: np.ndarray, ctx_df: pl.DataFrame) -> np.ndarray:
        """Per-row expert weights (for legibility / the desk overlay)."""
        c = (self._ctx(ctx_df, P) - self._cm) / self._cs
        ct = torch.tensor(c, dtype=torch.float32, device=self._dev)
        with torch.no_grad():
            return np.mean([g(ct).cpu().numpy() for g in self.gates], axis=0)


@dataclass
class MechanisticNetLoad:
    """Physics-style additive net-load model - the LEGIBLE expert with failure
    modes orthogonal to every ML member (doctrine: plottable policies):
        y ~ baseline(month, daytype, hour) + piecewise-linear temp response
            - solar carve (GHI x per-era coefficient) + annual trend
    Quantiles = point + empirical residual quantiles by (month, hour-block).
    No boosting/backprop to break; extrapolates the temp slope linearly past the
    training range (a heat record raises it, never flatlines); trains in seconds.
    Same fit/predict contract as the other experts."""
    taus: tuple[float, ...] = TAUS
    seeds: tuple[int, ...] = (7,)
    n_jobs: int | None = None
    knots: tuple[float, ...] = (10.0, 15.0, 20.0, 25.0)
    features: list[str] = field(default_factory=list)

    def _parts(self, m: pl.DataFrame) -> pl.DataFrame:
        et = pl.col("event_time").dt.convert_time_zone("America/Toronto")
        return m.with_columns(et.dt.month().alias("_mo"), et.dt.hour().alias("_hr"),
                              (et.dt.weekday() >= 6).cast(pl.Int8).alias("_we"),
                              et.dt.year().alias("_yr"))

    def _temp_design(self, t: np.ndarray) -> np.ndarray:
        t = np.where(np.isfinite(t), t, 10.0)
        return np.column_stack([t] + [np.maximum(0.0, t - k) for k in self.knots])

    def fit(self, m: pl.DataFrame) -> "MechanisticNetLoad":
        self.features = feature_columns(m)
        d = self._parts(m)
        base = d.group_by(["_mo", "_we", "_hr"]).agg(pl.col("y").median().alias("_b"))
        d = d.join(base, on=["_mo", "_we", "_hr"], how="left")
        self._base = base
        r = (d["y"] - d["_b"]).to_numpy().astype(np.float64)
        temp = d["temp_fcst"].to_numpy().astype(np.float64) if "temp_fcst" in d.columns else np.zeros(len(r))
        ghi = d["solar_ghi_allsky"].to_numpy().astype(np.float64) if "solar_ghi_allsky" in d.columns else np.zeros(len(r))
        ghi = np.where(np.isfinite(ghi), ghi, 0.0)
        yr = d["_yr"].to_numpy().astype(np.float64)
        era = np.clip((yr - 2015.0) / 10.0, 0.0, 1.5)          # solar-capacity ramp proxy
        lag = d["demand_lag_168h"].to_numpy().astype(np.float64) if "demand_lag_168h" in d.columns else np.zeros(len(r))
        lag = np.where(np.isfinite(lag), lag - np.nanmean(lag), 0.0)   # weekly persistence (centred)
        X = np.column_stack([self._temp_design(temp), ghi, ghi * era, yr - yr.mean(), lag])
        X = np.column_stack([X, np.ones(len(r))])
        mask = np.isfinite(r)
        self._beta, *_ = np.linalg.lstsq(X[mask], r[mask], rcond=None)
        self._yr_mean = float(yr.mean())
        self._lag_mean = float(np.nanmean(d["demand_lag_168h"].to_numpy())) if "demand_lag_168h" in d.columns else 0.0
        resid = r - X @ self._beta
        d = d.with_columns(pl.Series("_res", resid), (pl.col("_hr") // 6).alias("_hb"))
        recent = d.filter(pl.col("_yr") >= pl.col("_yr").max() - 2)    # recency: last 3 seasons' residuals
        qs = recent.group_by(["_mo", "_hb"]).agg(
            *[pl.col("_res").quantile(t).alias(f"_rq{i}") for i, t in enumerate(self.taus)])
        self._rq = qs
        rr = recent["_res"].to_numpy()
        self._rq_glob = [float(np.nanquantile(rr[np.isfinite(rr)], t)) for t in self.taus]
        return self

    def predict(self, m: pl.DataFrame) -> pl.DataFrame:
        d = self._parts(m).join(self._base, on=["_mo", "_we", "_hr"], how="left")
        d = d.with_columns(pl.col("_b").fill_null(strategy="mean"))
        temp = d["temp_fcst"].to_numpy().astype(np.float64) if "temp_fcst" in d.columns else np.zeros(d.height)
        ghi = d["solar_ghi_allsky"].to_numpy().astype(np.float64) if "solar_ghi_allsky" in d.columns else np.zeros(d.height)
        ghi = np.where(np.isfinite(ghi), ghi, 0.0)
        yr = d["_yr"].to_numpy().astype(np.float64)
        era = np.clip((yr - 2015.0) / 10.0, 0.0, 1.5)
        lag = d["demand_lag_168h"].to_numpy().astype(np.float64) if "demand_lag_168h" in d.columns else np.zeros(d.height)
        lag = np.where(np.isfinite(lag), lag - self._lag_mean, 0.0)
        X = np.column_stack([self._temp_design(temp), ghi, ghi * era, yr - self._yr_mean,
                             lag, np.ones(d.height)])
        point = d["_b"].to_numpy() + X @ self._beta
        d = d.with_columns((pl.col("_hr") // 6).alias("_hb")).join(self._rq, on=["_mo", "_hb"], how="left")
        cols = {}
        for i, t in enumerate(self.taus):
            rq = d[f"_rq{i}"].to_numpy().astype(np.float64)
            rq = np.where(np.isfinite(rq), rq, self._rq_glob[i])
            cols[f"q{int(t*100):02d}"] = point + rq
        arr = np.sort(np.column_stack([cols[f"q{int(t*100):02d}"] for t in self.taus]), axis=1)
        return m.with_columns(**{f"q{int(t*100):02d}": pl.Series(arr[:, i])
                                 for i, t in enumerate(self.taus)})
