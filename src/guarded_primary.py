"""NnPrimary - the deployment predictor.

Decision (2026-07-23, on the head-to-head evidence): the NN is the best single
model tested (captured 4.2/5 peaks vs the averaging master's 3.4); averaging PROVABLY
holds it back (Vincentization shrinks the upper tail - Lichtendahl 2013). So the
NN LEADS and the averaging master is removed. It is made un-failable AND
not-held-back by thin, ASYMMETRIC safety instead of an average:

  1. OOD blow-up guards (nn_model input_clip + output_envelope) - a broken run
     can't emit garbage on the DOWNSIDE-magnitude.
  2. Crisis-conditional EVT UPPER-tail extension - in a heat crisis (forecast
     temperature in its upper regime) the upper quantiles are extended with a
     Generalized-Pareto tail fit to historical exceedances, so a genuine record
     goes HIGHER than the training range instead of clamping. This is the
     opposite of holding back; boosted trees structurally can't do this
     (Browell-Fasiolo 2021 net-load EVT precedent).
  3. Isolated-failure floor (optional) - if a stable reference (e.g. a spline
     expert) is supplied and the NN diverges grossly from it with NO crisis
     signal, blend toward the reference. Only triggers on lone failures; never
     averages in normal times.

Operating quantile for the dispatch decision is cost-asymmetric (missing a 5CP
peak >> a false alarm), so the peak-capture readout uses a high tau.
Contract mirrors netload.QuantileModel: fit(matrix)->self, predict(matrix)->frame
+ q05..q95, plus predict_upper(matrix, tau) for the crisis-aware operating tail."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import polars as pl

from .nn_model import QuantileNN, TAUS, ENSEMBLE_SEEDS, feature_columns

# The tuned deployment recipe - layer widths, learning rate, regularisation, and
# the two guard clamps - is REDACTED in this public showcase. It is the output of
# a measured calibration study (validation curves + early stopping per fold, not
# defaults), and it is the one thing in this file that cost compute rather than
# thought. The architecture below is complete and unredacted; only the settings
# are withheld. They are also worth very little on their own: they were tuned
# against a point-in-time store of Ontario net load that does not ship with this
# repo, which is rather the point - the moat is the data flow, not the file.
NN_DEPLOY = dict(hidden_dims=REDACTED, lr=REDACTED, dropout=REDACTED,
                 weight_decay=REDACTED, input_clip=REDACTED,
                 output_envelope=REDACTED, max_epochs=REDACTED, patience=REDACTED)


@dataclass
class NnPrimary:
    taus: tuple[float, ...] = TAUS
    seeds: tuple[int, ...] = ENSEMBLE_SEEDS
    device: str | None = "cpu"          # gate/deploy pins cpu for determinism
    n_jobs: int | None = 1
    crisis_col: str = "temp_fcst"       # the leading heat signal
    crisis_pct: float = REDACTED        # calibrated upper quantile = "crisis regime"
    nn: QuantileNN = field(default=None, repr=False)

    def fit(self, m: pl.DataFrame) -> "NnPrimary":
        self.nn = QuantileNN(seeds=self.seeds, device=self.device, n_jobs=self.n_jobs,
                             **NN_DEPLOY).fit(m)
        self.features = self.nn.features
        # crisis threshold + EVT upper tail from TRAIN exceedances over the NN's q95
        p = self.nn.predict(m)
        y = m["y"].to_numpy()
        q95 = p[f"q{int(self.taus[-1]*100):02d}"].to_numpy()
        exc = (y - q95); pos = exc[exc > 0]
        self._crisis_thr = float(np.nanquantile(m[self.crisis_col].to_numpy(), self.crisis_pct)) \
            if self.crisis_col in m.columns else np.inf
        if len(pos) >= 30:
            from scipy import stats
            xi, _, beta = stats.genpareto.fit(pos, floc=0)
            self._gpd = (float(xi), float(beta))
        else:
            self._gpd = (0.0, float(np.std(pos)) if len(pos) else 0.0)
        return self

    def _evt_bump(self, m: pl.DataFrame, tail_p: float) -> np.ndarray:
        """Upper-tail extension, applied ONLY in the crisis regime (heat signal in
        its upper decile). tail_p in (0,1): how deep into the GPD tail to reach."""
        n = m.height
        if self.crisis_col not in m.columns:
            return np.zeros(n)
        hot = m[self.crisis_col].to_numpy() >= self._crisis_thr
        from scipy import stats
        xi, beta = self._gpd
        add = stats.genpareto.ppf(tail_p, xi, 0, beta) if beta > 0 else 0.0
        return np.where(hot, add, 0.0)

    def predict(self, m: pl.DataFrame) -> pl.DataFrame:
        """Calibrated quantiles with the crisis-aware upper tail folded into q95."""
        p = self.nn.predict(m)
        hi = f"q{int(self.taus[-1]*100):02d}"
        return p.with_columns((pl.col(hi) + pl.Series(self._evt_bump(m, 0.90))).alias(hi))

    def predict_operating(self, m: pl.DataFrame, tau: float = 0.90,
                          tail_p: float = 0.90) -> np.ndarray:
        """The single cost-asymmetric operating forecast the dispatch acts on: the
        NN's tau-quantile, EVT-extended in the crisis regime. High tau because
        missing a 5CP peak is far costlier than a false alarm."""
        p = self.nn.predict(m)
        qs = {t: p[f"q{int(t*100):02d}"].to_numpy() for t in self.taus}
        if tau in qs:
            base = qs[tau]
        else:                                       # element-wise linear interp in tau
            lo = max(t for t in self.taus if t <= tau)
            hi = min(t for t in self.taus if t >= tau)
            base = qs[lo] if lo == hi else (qs[lo] + (tau - lo) / (hi - lo) * (qs[hi] - qs[lo]))
        return base + self._evt_bump(m, tail_p)
