# Aurivest — the public record

Ontario bills its largest industrial consumers on **five hours a year**: the
five provincial "coincident peak" hours set each factory's Global Adjustment
charge, routinely the largest line on the bill, at $347,191/yr per MW of peak
contribution (2024 Class A rate). Miss those hours and you overpay seven
figures. Hit them and the bill collapses.

Aurivest puts a battery behind the factory's meter, predicts those five
hours, and discharges through them, then stacks capacity-auction,
demand-response, and arbitrage revenue on the same asset.

This repository is the company's **public record**: the forecasting system's
daily calls, filed every morning before the day unfolds, and the results
they produce. It exists so that a counterparty can check our numbers against
independent public data (IESO's published Ontario demand) rather than take
our word for them.

## Results (walk-forward backtest, 16 complete seasons 2010-2025 + the live 2026 season)

| metric | result |
|---|---|
| CP hours **delivered at 50%+ of nameplate**, through battery physics and settlement | **75/80 (94%)** (REAL-vintage leg 33/35, mean 9.4 MW of 10) |
| CP hours contained by the armed discharge window | **79/80 (99%)** |
| **Live 2026 season to date** (base period incomplete) | **5/5 contained** |
| Modeled net value per 10 MW / 60 MWh site (backtest basis) | **~$3.4M/yr** |
| Forward, at capacity prices already cleared for 2026/27 | **~$5.0M/yr (~$500k/MW-yr)** |

Every number is **selection-clean**: hyperparameters and design choices were
tuned only on pre-2022 seasons; 2022-2026 was evaluated once. Backtest and
live operation share one code path over a bitemporal store, so "as of 6 AM
that morning" is enforced by construction: the backtest physically cannot
peek. These figures have been corrected upward and downward in public as the
engineering record moved; the private repository carries every dated
correction and the pre-registered pass/fail gate behind each number.

## The record

- **`record/calls.md`**: every daily call as issued, with its issue
  timestamp. Gaps are recorded as gaps, never backfilled.
- **`record/daily/*.json`**: the machine-readable form of each call. Each
  file carries the issue timestamp, the model artifact identifier and config
  hash, and the commit hash of the private data-repo push that filed the
  call. Those hashes are the audit trail: in diligence, each call is
  reproducible from the private store as of its issue time.

Realized peaks are independently checkable against IESO's published Ontario
demand data. That is the point of this repository.

## What is not here

The system itself (models, features, data pipeline, dispatch logic, and
evaluation harness) is private. Method-level material that previously
appeared in this repository was removed on 2026-09-03, history included, and
should be considered superseded; the record entries and their issue stamps
were preserved unchanged. Verification happens two ways: anyone can score
the public record against IESO data at any time, and counterparties in
diligence are walked through the private repositories under NDA.

## Honesty ledger

The backtest is a backtest; the live public record began July 2026 and is
young. It is a seed, not evidence, and it will keep accumulating either way.
Where a claim depends on a tariff rate, the rate is verified against the
primary source before it is quoted externally.

---

*Built end-to-end by a solo founder. Contact: sam@aurivestenergy.com*
