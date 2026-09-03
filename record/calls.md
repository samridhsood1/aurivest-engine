# Aurivest daily peak calls — the published record

Every morning the forecasting system files its call for the day: the hour it
expects Ontario's provincial demand to peak. Each row below is that call,
as issued, with its issue timestamp. Nothing here is ever edited after the
fact. Rows are mirrored from the private bitemporal store and carry the
store's issue stamps; each daily JSON in record/daily/ names the private
data-repo commit that filed the call, and those commits are auditable in
diligence. Curation note: on 2026-09-03 this repository's history was
rewritten to remove code excerpts that previously accompanied the record.
Every record entry and every issue stamp was preserved unchanged; the
private store remains the primary proof of when each call was filed.

Hours are Eastern local hour-ending. Realized peaks are independently
checkable against IESO's published demand data — that is the point.
The system's tested history (7 seasons walk-forward on real forecast
vintages, 94% of coincident-peak hours) is held in the private
repositories and shown in diligence; the table below is the LIVE record
that discipline produces.

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
| 2026-08-19 | 2026-08-19 11:23 | HE17 | 21,571 | HE17 (0.59), HE18 (0.32), HE20 (0.02) |
| 2026-08-20 | 2026-08-20 11:23 | HE17 | 21,612 | HE17 (0.50), HE18 (0.36), HE20 (0.03) |
| 2026-08-21 | 2026-08-21 11:23 | HE17 | 21,139 | HE17 (0.57), HE18 (0.28), HE0 (0.08) |
| 2026-08-22 | 2026-08-22 11:23 | HE17 | 19,132 | HE17 (0.57), HE18 (0.31), HE0 (0.05) |
| 2026-08-23 | 2026-08-23 11:23 | HE17 | 17,858 | HE17 (0.60), HE18 (0.29), HE0 (0.04) |
| 2026-08-24 | 2026-08-24 11:23 | HE17 | 18,928 | HE17 (0.70), HE18 (0.18), HE16 (0.04) |
| 2026-08-25 | 2026-08-25 11:23 | HE17 | 20,620 | HE17 (0.67), HE18 (0.26), HE0 (0.02) |
| 2026-08-26 | 2026-08-26 11:23 | HE17 | 21,453 | HE17 (0.69), HE18 (0.25), HE20 (0.01) |
| 2026-08-27 | 2026-08-27 11:23 | HE17 | 21,664 | HE17 (0.69), HE18 (0.25), HE20 (0.01) |
| 2026-08-28 | 2026-08-28 11:23 | HE18 | 19,720 | HE18 (0.49), HE17 (0.42), HE16 (0.01) |
| 2026-08-29 | 2026-08-29 11:23 | HE17 | 19,842 | HE17 (0.66), HE18 (0.26), HE0 (0.02) |
| 2026-08-30 | 2026-08-30 11:23 | HE17 | 18,457 | HE17 (0.62), HE18 (0.26), HE16 (0.04) |
| 2026-08-31 | 2026-08-31 11:33 | HE17 | 21,136 | HE17 (0.73), HE18 (0.11), HE16 (0.08) |
| 2026-09-01 | — | *no morning call filed* | — | gap recorded as a gap, never backfilled |
| 2026-09-02 | 2026-09-02 11:25 | HE17 | 22,285 | HE17 (0.60), HE18 (0.26), HE16 (0.05) |
| 2026-09-03 | — | *no morning call filed* | — | gap recorded as a gap, never backfilled |
