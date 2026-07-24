"""Deploy-today entrypoint: the guarded-NN primary's daily dispatch plan.

  uv run --group ml scripts/predict_today.py [--date YYYY-MM-DD] [--out plan.json]

Reuses the PROVEN live leg (forecast_shadow.build_today_matrix - same as-of
06:00-Eastern feature path the gate evaluated; fail-loud input floors) but runs
the NEW primary stack end to end, read-only:

  1. today's F1 morning-epoch matrix from the real store (+ solar features);
  2. guarded-NN quantiles: NN primary (nn_primary_v3.pkl) with OOD guards +
     crisis-EVT upper tail; failsafe check vs tree/spline/qforest medians
     (failsafes_v3.pkl) - fallback to their pool ONLY on isolated divergence
     with no crisis signal (z=8, the calibrated operating point);
  3. peak-hour pmf (tuned classifier refit weekly with the failsafe bundle -
     here the bundled tree stack's argmax-hour proxy until the clf artifact is
     added to the bundle);
  4. the dispatch plan: arm decision (forecast daily peak vs season-to-date
     top-5 scoreboard is Layer-3's job; here: op-forecast + window) and the
     blended 6-h discharge window (0.5*pmf + 0.5*level-share - the shipped,
     train-selected placement).

Read-only everywhere (doctrine: data/ is written only by Actions); the plan
prints to stdout and optionally --out JSON. This is the command a site
operator (or the scheduler) runs each morning.
"""
from __future__ import annotations

import argparse
import json
import pickle
import sys
from datetime import date, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

import numpy as np
import polars as pl


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date", default=None, help="target day (default: today, Eastern)")
    ap.add_argument("--out", default=None, help="write the plan JSON here")
    args = ap.parse_args()

    import forecast_shadow as fs
    from predictor.store.bitemporal import BitemporalStore
    import eval_netload as ev

    target = date.fromisoformat(args.date) if args.date else \
        datetime.now(fs.EASTERN).date() if hasattr(fs, "EASTERN") else date.today()

    store = BitemporalStore(REPO / "data" / "store")
    cfg = ev.profile_config("v1_1")
    m = fs.build_today_matrix(store, target, cfg)
    fs.validate_inputs(m, m.height)

    solar = pl.read_parquet(REPO / "cache" / "solar_features.parquet")
    m = m.join(solar, on="event_time", how="left")

    with open(REPO / "cache" / "deploy" / "nn_primary_v3.pkl", "rb") as f:
        primary = pickle.load(f)
    with open(REPO / "cache" / "deploy" / "failsafes_v3.pkl", "rb") as f:
        guard = pickle.load(f)

    # 1) primary forecast (NN + guards + crisis-EVT upper tail)
    p = primary.predict(m)
    q = {c: p[c].to_numpy() for c in ("q05", "q25", "q50", "q75", "q95")}

    # 2) failsafe medians -> isolated-divergence guard
    feats = guard["tree_feats"]
    X = m.select([c for c in feats if c in m.columns]).to_numpy()
    tree_med = np.mean([b.predict(X) for b in guard["tree_models"][0.5]], axis=0)
    sp = guard["spline"].predict(m)["q50"].to_numpy()
    qf = guard["qrf"].predict(m)["q50"].to_numpy()
    others = np.column_stack([tree_med, sp, qf])
    center = np.median(others, axis=1)
    mad = np.maximum(np.median(np.abs(others - center[:, None]), axis=1) * 1.4826,
                     0.01 * np.abs(center) + 50.0)
    crisis = m[guard["crisis_col"]].to_numpy() >= guard["crisis_thr"]
    diverged = (np.abs(q["q50"] - center) > guard["guard_z"] * mad) & \
               ~(crisis & (q["q50"] > center))
    guard_fired = bool(diverged.any())
    if guard_fired:                      # fallback: failsafe pool on those rows
        for c in q:
            q[c] = np.where(diverged, center, q[c])

    # 3) window placement: blended mass (level-share proxy for pmf until the clf
    #    artifact ships in the bundle; identical placement code path)
    op = 0.5 * q["q75"] + 0.5 * q["q95"]
    osh = op - op.min(); osh = osh / max(osh.sum(), 1e-9)
    mmass = osh                          # + 0.5*pmf when clf artifact present
    st = max(range(len(mmass) - 5), key=lambda i: mmass[i:i + 6].sum())

    hours = m["event_time"].dt.convert_time_zone("America/Toronto").dt.hour().to_list()
    plan = dict(
        date=str(target),
        forecast_peak_mw=float(op.max()),
        forecast_peak_hour_local=int(hours[int(np.argmax(op))]),
        discharge_window_local=[int(hours[st]), int(hours[min(st + 5, len(hours) - 1)]) + 1],
        q50_at_peak=float(q["q50"][int(np.argmax(op))]),
        band90_at_peak=[float(q["q05"][int(np.argmax(op))]), float(q["q95"][int(np.argmax(op))])],
        crisis_regime=bool(crisis[int(np.argmax(op))]),
        guard_fired=guard_fired,
        model="guarded-nn v3 (c004+top40+solar, EVT tail, failsafe z=8)",
    )
    print(json.dumps(plan, indent=2))
    if args.out:
        Path(args.out).write_text(json.dumps(plan, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
