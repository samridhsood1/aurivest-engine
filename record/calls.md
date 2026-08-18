# Aurivest daily peak calls — the published record

Every morning the forecasting system files its call for the day: the hour it
expects Ontario's provincial demand to peak. Each row below is that call,
as issued, with its issue timestamp. Nothing here is ever edited after the
fact — from 2026-08-19 onward this repo's own commit history is the
public proof; entries before that were mirrored from the private bitemporal
store on first publish and carry the store's issue stamps (the underlying
commits are auditable in diligence).

Hours are Eastern local hour-ending. Realized peaks are independently
checkable against IESO's published demand data — that is the point.
The system's tested history (7 seasons walk-forward on real forecast
vintages, 94% of coincident-peak hours) is documented in this repo's
docs/; the table below is the LIVE record that discipline produces.

| date | issued (UTC) | predicted peak hour (ET, HE) | q50 (MW) | top-3 hours (p) |
|---|---|---|---|---|
| 2026-08-06 | 2026-08-06 13:06 | HE17 | 20,994 | HE17 (0.66), HE18 (0.31), HE19 (0.01) |
| 2026-08-07 | 2026-08-07 12:21 | HE17 | 20,202 | HE17 (0.64), HE18 (0.28), HE16 (0.03) |
| 2026-08-08 | 2026-08-08 11:49 | HE17 | 19,947 | HE17 (0.58), HE18 (0.38), HE16 (0.01) |
| 2026-08-09 | 2026-08-09 11:59 | HE17 | 21,382 | HE17 (0.47), HE18 (0.41), HE0 (0.05) |
| 2026-08-10 | 2026-08-10 05:35 | HE17 | 21,465 | HE17 (0.49), HE18 (0.42), HE19 (0.02) |
| 2026-08-11 | 2026-08-11 11:23 | HE17 | 21,933 | HE17 (0.49), HE18 (0.42), HE19 (0.01) |
| 2026-08-12 | 2026-08-12 11:23 | HE17 | 21,183 | HE17 (0.51), HE18 (0.38), HE19 (0.02) |
| 2026-08-13 | 2026-08-13 11:23 | HE17 | 22,368 | HE17 (0.50), HE18 (0.41), HE19 (0.02) |
| 2026-08-14 | 2026-08-14 11:23 | HE18 | 21,106 | HE18 (0.58), HE17 (0.28), HE20 (0.02) |
| 2026-08-15 | 2026-08-15 11:23 | HE18 | 19,989 | HE18 (0.50), HE17 (0.37), HE20 (0.02) |
| 2026-08-16 | 2026-08-16 11:38 | HE17 | 20,144 | HE17 (0.55), HE18 (0.33), HE16 (0.04) |
| 2026-08-17 | 2026-08-17 11:23 | HE18 | 21,645 | HE18 (0.51), HE17 (0.40), HE20 (0.02) |
| 2026-08-18 | — | *no morning call filed* | — | gap recorded as a gap, never backfilled |
