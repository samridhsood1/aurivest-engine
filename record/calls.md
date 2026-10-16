# Aurivest daily peak calls — the published record

Every morning the forecasting system files its call for the day: the hour it
expects Ontario's provincial demand to peak. Each row below is that call,
as issued, with its issue timestamp. Nothing here is ever edited after the
fact. Rows are mirrored from the private record and carry its issue
stamps; each daily JSON in record/daily/ names the private
data-repo commit that filed the call, and those commits are auditable in
diligence. Curation note: on 2026-09-03 this repository's history was
rewritten to remove code excerpts that previously accompanied the record.
Every record entry and every issue stamp was preserved unchanged; the
private store remains the primary proof of when each call was filed.

Hours are Eastern local hour-beginning (America/Toronto clock): hour 17 is
17:00 to 18:00 local time, which while daylight time is in force is IESO's
hour-ending 17 (EST) and in winter is IESO's hour-ending 18. Realized peaks
are independently checkable against IESO's published demand data.
Correction, 2026-10-16: rows issued through 2026-10-16 carry the label HE,
which wrongly said hour-ending. Their hours were always local hour-beginning
as above (HE17 in those rows means 17:00 to 18:00 local). Those rows are left
exactly as issued; rows from 2026-10-17 use HB.
The backtest figure this page used to cite (94% of coincident-peak hours) is
withdrawn: see the README. The calls below are published as issued, as a
running log, not as evidence of skill.

| date | issued (UTC) | predicted peak hour (ET, hour-beginning) | q50 (MW) | top-3 hours (p) |
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
| 2026-09-04 | none | *no morning call filed* | none | gap recorded as a gap, never backfilled |
| 2026-09-05 | 2026-09-05 11:23 | HE17 | 19,663 | HE17 (0.71), HE18 (0.21), HE0 (0.02) |
| 2026-09-06 | 2026-09-06 16:18 | HE17 | 18,246 | HE17 (0.71), HE18 (0.21), HE0 (0.03) |
| 2026-09-07 | 2026-09-07 11:23 | HE17 | 20,047 | HE17 (0.80), HE18 (0.13), HE0 (0.02) |
| 2026-09-08 | 2026-09-08 11:23 | HE17 | 20,086 | HE17 (0.80), HE16 (0.09), HE18 (0.06) |
| 2026-09-09 | none | *no morning call filed* | none | gap recorded as a gap, never backfilled |
| 2026-09-10 | 2026-09-10 11:33 | HE17 | 18,713 | HE17 (0.84), HE18 (0.11), HE16 (0.01) |
| 2026-09-11 | 2026-09-11 11:23 | HE17 | 19,509 | HE17 (0.86), HE18 (0.08), HE16 (0.02) |
| 2026-09-12 | 2026-09-12 11:23 | HE17 | 19,051 | HE17 (0.88), HE16 (0.04), HE18 (0.03) |
| 2026-09-13 | 2026-09-13 11:23 | HE17 | 18,988 | HE17 (0.86), HE18 (0.05), HE16 (0.04) |
| 2026-09-14 | 2026-09-14 11:23 | HE17 | 17,754 | HE17 (0.78), HE18 (0.15), HE19 (0.02) |
| 2026-09-15 | 2026-09-15 11:23 | HE17 | 19,777 | HE17 (0.74), HE16 (0.10), HE18 (0.04) |
| 2026-09-16 | 2026-09-16 11:23 | HE17 | 20,295 | HE17 (0.80), HE16 (0.11), HE18 (0.03) |
| 2026-09-17 | 2026-09-17 11:23 | HE17 | 19,396 | HE17 (0.79), HE16 (0.08), HE0 (0.04) |
| 2026-09-18 | 2026-09-18 11:23 | HE17 | 18,138 | HE17 (0.83), HE0 (0.05), HE18 (0.03) |
| 2026-09-19 | 2026-09-19 11:23 | HE17 | 16,569 | HE17 (0.73), HE0 (0.06), HE16 (0.05) |
| 2026-09-20 | 2026-09-20 11:23 | HE17 | 16,789 | HE17 (0.53), HE0 (0.12), HE19 (0.12) |
| 2026-09-21 | 2026-09-21 11:23 | HE17 | 17,242 | HE17 (0.54), HE19 (0.21), HE18 (0.07) |
| 2026-09-22 | 2026-09-22 11:23 | HE17 | 16,764 | HE17 (0.43), HE19 (0.19), HE0 (0.16) |
| 2026-09-23 | 2026-09-23 11:23 | HE17 | 16,868 | HE17 (0.38), HE19 (0.17), HE0 (0.17) |
| 2026-09-24 | 2026-09-24 11:23 | HE17 | 16,904 | HE17 (0.39), HE19 (0.17), HE0 (0.13) |
| 2026-09-25 | 2026-09-25 11:23 | HE17 | 16,809 | HE17 (0.50), HE0 (0.16), HE19 (0.12) |
| 2026-09-26 | 2026-09-26 11:23 | HE17 | 16,068 | HE17 (0.68), HE0 (0.09), HE19 (0.08) |
| 2026-09-27 | 2026-09-27 11:23 | HE17 | 16,454 | HE17 (0.54), HE19 (0.18), HE18 (0.16) |
| 2026-09-28 | 2026-09-28 11:23 | HE17 | 17,354 | HE17 (0.56), HE19 (0.23), HE18 (0.14) |
| 2026-09-29 | 2026-09-29 11:23 | HE17 | 18,227 | HE17 (0.56), HE19 (0.28), HE18 (0.10) |
| 2026-09-30 | 2026-09-30 11:23 | HE17 | 18,272 | HE17 (0.58), HE19 (0.23), HE18 (0.12) |
| 2026-10-01 | 2026-10-01 11:23 | HE17 | 18,506 | HE17 (0.59), HE19 (0.21), HE18 (0.11) |
| 2026-10-02 | 2026-10-02 11:23 | HE19 | 16,618 | HE19 (0.35), HE17 (0.31), HE18 (0.11) |
| 2026-10-03 | 2026-10-03 11:23 | HE19 | 16,093 | HE19 (0.61), HE17 (0.19), HE18 (0.16) |
| 2026-10-04 | 2026-10-04 11:23 | HE19 | 17,102 | HE19 (0.66), HE18 (0.14), HE17 (0.11) |
| 2026-10-05 | 2026-10-05 11:23 | HE19 | 17,605 | HE19 (0.71), HE17 (0.14), HE18 (0.10) |
| 2026-10-06 | 2026-10-06 11:23 | HE19 | 17,163 | HE19 (0.61), HE17 (0.23), HE18 (0.11) |
| 2026-10-07 | none | *no morning call filed* | none | gap recorded as a gap, never backfilled |
| 2026-10-08 | 2026-10-08 11:23 | HE19 | 17,285 | HE19 (0.66), HE17 (0.16), HE18 (0.11) |
| 2026-10-09 | 2026-10-09 11:23 | HE19 | 16,758 | HE19 (0.67), HE18 (0.11), HE17 (0.10) |
| 2026-10-10 | 2026-10-10 11:23 | HE19 | 15,907 | HE19 (0.63), HE18 (0.11), HE17 (0.09) |
| 2026-10-11 | 2026-10-11 11:23 | HE19 | 16,813 | HE19 (0.69), HE18 (0.15), HE17 (0.10) |
| 2026-10-12 | 2026-10-12 11:23 | HE19 | 17,785 | HE19 (0.60), HE17 (0.22), HE18 (0.13) |
| 2026-10-13 | 2026-10-13 11:23 | HE19 | 18,383 | HE19 (0.55), HE17 (0.23), HE18 (0.12) |
| 2026-10-14 | 2026-10-14 11:23 | HE19 | 16,816 | HE19 (0.62), HE17 (0.17), HE18 (0.14) |
| 2026-10-15 | 2026-10-15 11:23 | HE19 | 17,153 | HE19 (0.69), HE17 (0.15), HE18 (0.13) |
| 2026-10-16 | 2026-10-16 11:23 | HE19 | 16,749 | HE19 (0.63), HE18 (0.15), HE17 (0.14) |
