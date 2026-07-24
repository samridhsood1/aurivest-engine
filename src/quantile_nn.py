"""Neural-network quantile forecaster - a drop-in COMPARISON to the LightGBM
net-load stack (forecast/netload.py), for the head-to-head the founder asked
for on the *identical* walk-forward gate.

Why this exists (docs/model-architecture-survey.md, Families 2 and 7). The
survey's honest expectation is that on the SCARCE head (~120 coincident-peak
events) a from-scratch deep net is parity-at-best against a tuned GBDT. But
this model is NOT trained on the 120 events: like the tree stack it is trained
on the ABUNDANT regime - the F1 hourly net-load matrix, ~210k hourly rows over
~24 seasons of rich weather/price/calendar covariates - "every hour a training
example, never rare-event classification" (CLAUDE.md). That is the regime where
a net can genuinely work, and it makes the comparison legitimate rather than a
strawman: same as-of matrix, same taus, same crossing repair, same seed-ensemble
determinism discipline, same gate.

Contract parity with netload.QuantileModel (so it slots into the harness with no
call-site change):
  - fit(matrix: pl.DataFrame) -> self ; sets .features = feature_columns(matrix)
  - predict(matrix) -> the input frame + one q<tau> column per tau (q05..q95),
    crossing-repaired by sorting across taus
  - TAUS, ENSEMBLE_SEEDS, feature_columns mirror netload's contract EXACTLY
    (same values). They are DELIBERATELY re-declared here rather than imported:
    netload.py is under concurrent edit, and this module must stay importable and
    independently testable regardless of that file's transient state. The values
    are pre-registered constants; if they ever diverge, tests/test_nn_model.py's
    parity check against the real QuantileModel fails loudly.

Model. An MLP with a shared trunk and 5 simultaneous quantile output heads (one
Linear -> len(TAUS) outputs), trained JOINTLY on the pinball/quantile loss summed
over all taus - not one model per tau. (An FT-Transformer-lite trunk is the
documented alternative; the MLP is the strong, fast default for this tabular,
data-rich regime - TabM/RealMLP line, survey Family 2.) Pipeline:
  1. finite-mask + per-column median impute (trees eat NaN natively; a net does
     not - the F1 matrix is full of honest nulls before each series' data start),
     then standardize INPUTS and the TARGET. Target standardization is not
     cosmetic: net-load is ~20,000 MW and pinball's L1-type gradient under Adam
     cannot walk the output bias to that level in a sane epoch budget; quantiles
     are equivariant under positive affine scaling, so training on standardized y
     and rescaling predictions back is exact. Imputer + scalers are FIT ON TRAIN
     and frozen for predict.
  2. per-seed MLP with early stopping on an internal validation split.
  3. fixed-seed ENSEMBLE: average the len(seeds) runs (variance reduction +
     determinism), exactly like the tree stack, THEN sort across taus.

Determinism. torch/numpy/random are seeded per member and deterministic algorithms
are requested. Device auto-selects MPS>CPU; MPS may introduce minor float
non-determinism run-to-run, so the determinism GATE (and the determinism test)
pin device="cpu". Pass n_jobs to pin the CPU thread count for bit-stability, the
same knob QuantileModel uses.
"""
from __future__ import annotations

import random
import sys
import warnings
from dataclasses import dataclass, field

import numpy as np
import polars as pl
import torch
from torch import nn

# --- OpenMP coexistence guard (macOS/Apple-Silicon, verified 2026-07-22) -------
# torch and lightgbm each bundle their OWN libomp; two copies resident in one
# process is undefined behaviour. Import alone is fine, but the moment torch
# opens an OpenMP parallel region (its intra-op threadpool, triggered by any
# real training step) in a process that also loaded lightgbm, the process
# SEGFAULTS (signal 11 / exit 139) - reproduced deterministically in all
# import orders. The nn_v0 gate ALWAYS co-resides with lightgbm: eval_netload
# imports netload (`import lightgbm` at module top) to reuse its metrics and the
# tree PeakHourClassifier. Pinning torch to a single thread keeps it from ever
# opening the region, which sidesteps the collision entirely. The cost is
# negligible here: the MLP is tiny and every fit is on a small in-memory matrix,
# and device="cpu" is pinned for the determinism gate anyway (thread count is
# irrelevant on MPS/CUDA). set_num_interop_threads must be set BEFORE the interop
# pool is first used, so it is done once here at import and guarded.
try:
    torch.set_num_interop_threads(1)
except RuntimeError:
    pass  # interop pool already initialised; the intra-op pin below still holds
torch.set_num_threads(1)

# --- netload.QuantileModel contract, mirrored EXACTLY (see module docstring) ---
TAUS = (0.05, 0.25, 0.50, 0.75, 0.95)
ENSEMBLE_SEEDS = (7, 17, 27, 37, 47)
NON_FEATURES = {"event_time", "decision_time", "y"}


def feature_columns(m: pl.DataFrame) -> list[str]:
    """Numeric columns that are not targets/timestamps - identical rule to
    netload.feature_columns so both models see the same feature set."""
    return [c for c in m.columns
            if c not in NON_FEATURES and m.schema[c].is_numeric()]


def _resolve_device(pref: str | None) -> torch.device:
    """Auto-select MPS>CPU; an explicit preference wins (the gate pins 'cpu')."""
    if pref is not None:
        return torch.device(pref)
    mps = getattr(torch.backends, "mps", None)
    if mps is not None and mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def _seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _configure_determinism() -> None:
    """Request deterministic kernels. warn_only=True so an op without a
    deterministic implementation degrades to a warning, never a hard crash
    mid-gate (the standard MLP path here has deterministic CPU kernels)."""
    try:
        torch.use_deterministic_algorithms(True, warn_only=True)
    except Exception:
        pass
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def pinball_loss(pred: torch.Tensor, y: torch.Tensor,
                 taus: torch.Tensor) -> torch.Tensor:
    """Mean pinball loss over a batch and all taus jointly.

    pred: (B, T) one column per tau; y: (B,); taus: (1, T). For each tau the
    loss is max(tau*e, (tau-1)*e) with e = y - pred - the quantile-regression
    objective, the exact continuous analogue of LightGBM's `objective="quantile"`
    used per-tau in QuantileModel.
    """
    e = y.unsqueeze(1) - pred                      # (B, T)
    return torch.maximum(taus * e, (taus - 1.0) * e).mean()


class _MLP(nn.Module):
    """Shared trunk + a single Linear head emitting one value per tau. The head's
    T output rows ARE the T quantile heads; they are trained jointly."""

    def __init__(self, in_dim: int, hidden: tuple[int, ...], out_dim: int,
                 dropout: float):
        super().__init__()
        layers: list[nn.Module] = []
        d = in_dim
        for h in hidden:
            layers += [nn.Linear(d, h), nn.ReLU(), nn.Dropout(dropout)]
            d = h
        layers.append(nn.Linear(d, out_dim))
        self.net = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


@dataclass
class QuantileNN:
    """MLP quantile ensemble matching netload.QuantileModel's fit/predict contract.

    Defaults target the data-rich F1 regime. The ensemble averages one MLP per
    seed then sorts across taus (no crossing), deterministic given the seed list,
    device, and thread count. seeds=(7,) is a single-member run; the default
    ENSEMBLE_SEEDS mirrors the tree stack's 5-seed ensemble.
    """
    taus: tuple[float, ...] = TAUS
    seeds: tuple[int, ...] = ENSEMBLE_SEEDS
    n_jobs: int | None = None          # None -> torch default thread count
    device: str | None = None          # None -> auto MPS>CPU; gate pins "cpu"
    hidden_dims: tuple[int, ...] = (256, 128)
    dropout: float = 0.1
    lr: float = 1e-3
    weight_decay: float = 1e-5
    batch_size: int = 2048
    max_epochs: int = 200
    patience: int = 12                 # early-stopping patience (val epochs)
    min_delta: float = 0.0
    val_fraction: float = 0.15         # internal validation split for stopping
    # --- out-of-distribution blow-up guards (None -> off; nn_v0 leaves both off,
    # so its committed gate result is unchanged). The 2026 season exposed the
    # failure: an extreme out-of-range feature, once standardized, becomes a huge
    # input that explodes the MLP's activations -> a wild prediction (MAE 4105 vs
    # the tree's 489). input_clip winsorizes standardized inputs to +/- this many
    # sd (kills the driver); output_envelope clamps final MW predictions to
    # [y_min - k*range, y_max + k*range] over the TRAIN target (the hard net).
    # Both barely touch in-range behaviour (few points exceed ~4 sd) and only
    # bite on true OOD - so adaptation is preserved, catastrophe is capped.
    input_clip: float | None = None    # e.g. 6.0
    output_envelope: float | None = None  # e.g. 0.5
    features: list[str] = field(default_factory=list)
    nets: list = field(default_factory=list, repr=False)
    history: list = field(default_factory=list, repr=False)

    # -- input preparation: finite-mask -> median impute -> standardize -------- #
    def _fit_prep(self, x_raw: np.ndarray) -> np.ndarray:
        x = np.asarray(x_raw, dtype=np.float64)
        x = np.where(np.isfinite(x), x, np.nan)
        with warnings.catch_warnings():          # all-null column -> nanmedian nan
            warnings.simplefilter("ignore", category=RuntimeWarning)
            med = np.nanmedian(x, axis=0)
        med = np.where(np.isfinite(med), med, 0.0)   # all-null -> impute 0.0
        self._impute = med
        nan_idx = np.where(np.isnan(x))
        x[nan_idx] = np.take(med, nan_idx[1])
        mean = x.mean(axis=0)
        std = x.std(axis=0)
        std = np.where(std < 1e-8, 1.0, std)         # constant column -> unit std
        self._mean = mean
        self._std = std
        return self._standardize(x)

    def _prep(self, x_raw: np.ndarray) -> np.ndarray:
        x = np.asarray(x_raw, dtype=np.float64)
        x = np.where(np.isfinite(x), x, np.nan)
        nan_idx = np.where(np.isnan(x))
        x[nan_idx] = np.take(self._impute, nan_idx[1])
        return self._standardize(x)

    def _standardize(self, x: np.ndarray) -> np.ndarray:
        """Standardize with the frozen train mean/std, then (if input_clip is set)
        winsorize to +/- input_clip sd so a single extreme OOD feature can't drive
        the MLP into a blow-up. Shared by fit and predict so both see the guard."""
        z = ((x - self._mean) / self._std).astype(np.float32)
        if self.input_clip is not None:
            z = np.clip(z, -self.input_clip, self.input_clip)
        return z

    def _fit_target(self, y_raw: np.ndarray) -> np.ndarray:
        """Standardize y; store the scale to invert at predict (see docstring).
        Also record the train target range for the predict-time output envelope."""
        y = np.asarray(y_raw, dtype=np.float64)
        self._y_mean = float(np.nanmean(y))
        s = float(np.nanstd(y))
        self._y_std = s if s > 1e-8 else 1.0
        self._y_lo = float(np.nanmin(y))
        self._y_hi = float(np.nanmax(y))
        return ((y - self._y_mean) / self._y_std).astype(np.float32)

    def _fit_one(self, x: np.ndarray, y: np.ndarray, seed: int,
                 device: torch.device) -> tuple[nn.Module, dict]:
        _seed_everything(seed)
        n = x.shape[0]
        # deterministic internal train/val split (seeded permutation)
        perm = np.random.default_rng(seed).permutation(n)
        n_val = min(max(1, int(round(self.val_fraction * n))), n - 1)
        val_idx, tr_idx = perm[:n_val], perm[n_val:]

        xt = torch.from_numpy(x)
        yt = torch.from_numpy(y.astype(np.float32))
        x_tr, y_tr = xt[tr_idx].to(device), yt[tr_idx].to(device)
        x_val, y_val = xt[val_idx].to(device), yt[val_idx].to(device)
        taus_t = torch.tensor(self.taus, dtype=torch.float32,
                              device=device).view(1, -1)

        net = _MLP(x.shape[1], tuple(self.hidden_dims), len(self.taus),
                   self.dropout).to(device)
        opt = torch.optim.Adam(net.parameters(), lr=self.lr,
                               weight_decay=self.weight_decay)

        def _val_loss() -> float:
            net.eval()
            with torch.no_grad():
                return float(pinball_loss(net(x_val), y_val, taus_t).item())

        initial_val = _val_loss()                    # pre-training baseline
        best_val, best_state, bad, last_epoch = initial_val, None, 0, 0
        shuf = torch.Generator(device="cpu")
        shuf.manual_seed(seed)
        batch = max(1, min(self.batch_size, x_tr.shape[0]))
        for epoch in range(self.max_epochs):
            last_epoch = epoch + 1
            net.train()
            order = torch.randperm(x_tr.shape[0], generator=shuf)
            for s in range(0, x_tr.shape[0], batch):
                b = order[s:s + batch].to(device)
                opt.zero_grad()
                loss = pinball_loss(net(x_tr[b]), y_tr[b], taus_t)
                loss.backward()
                opt.step()
            v = _val_loss()
            if v < best_val - self.min_delta:
                best_val = v
                best_state = {k: t.detach().clone()
                              for k, t in net.state_dict().items()}
                bad = 0
            else:
                bad += 1
                if bad >= self.patience:
                    break
        if best_state is not None:
            net.load_state_dict(best_state)
        net.eval()
        return net, {"seed": seed, "initial_val": initial_val,
                     "best_val": best_val, "epochs": last_epoch}

    def fit(self, m: pl.DataFrame) -> "QuantileNN":
        _configure_determinism()
        if self.n_jobs is not None:
            # NEVER raise torch above one thread while lightgbm is co-resident:
            # its OpenMP region collides with lightgbm's libomp and segfaults
            # (see the coexistence guard at module top). n_jobs still pins the
            # thread count for bit-stability - it just cannot exceed 1 here.
            safe = 1 if "lightgbm" in sys.modules else max(1, self.n_jobs)
            torch.set_num_threads(safe)
        self.features = feature_columns(m)
        x = self._fit_prep(m.select(self.features).to_numpy())
        y = self._fit_target(m["y"].to_numpy())
        self._device = _resolve_device(self.device)
        self.nets, self.history = [], []
        for seed in self.seeds:
            net, hist = self._fit_one(x, y, seed, self._device)
            self.nets.append(net)
            self.history.append(hist)
        return self

    def predict(self, m: pl.DataFrame) -> pl.DataFrame:
        """Input frame + one q<tau> column per tau, crossing-repaired.

        Seed members are averaged per tau (like the tree stack), THEN sorted
        across taus so quantiles are monotone in tau for every row.
        """
        if not self.nets:
            raise RuntimeError("QuantileNN.predict before fit")
        x = self._prep(m.select(self.features).to_numpy())
        xt = torch.from_numpy(x).to(self._device)
        outs = []
        with torch.no_grad():
            for net in self.nets:
                net.eval()
                outs.append(net(xt).cpu().numpy())
        preds = np.mean(outs, axis=0) * self._y_std + self._y_mean  # back to MW
        preds.sort(axis=1)                           # rearrangement: monotone taus
        if self.output_envelope is not None:         # hard net vs OOD blow-up
            rng = self._y_hi - self._y_lo
            lo = self._y_lo - self.output_envelope * rng
            hi = self._y_hi + self.output_envelope * rng
            preds = np.clip(preds, lo, hi)           # monotone -> taus stay sorted
        cols = {f"q{int(tau * 100):02d}": preds[:, i]
                for i, tau in enumerate(self.taus)}
        return m.with_columns(**{k: pl.Series(v) for k, v in cols.items()})
