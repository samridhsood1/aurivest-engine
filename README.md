# Aurivest: the public record

Large electricity customers pay for a handful of hours and prices: the few peak hours that set capacity and
transmission charges for a whole year, and energy prices that swing hour by hour. Many of them already have load
that can move (cooling, pumping, process heat, charging, batteries) but nobody schedules it against those hours.

Aurivest is software for that. It forecasts the hours and prices that set a site's bill and schedules the site's
existing flexible load around them: use or curtail a load; charge, discharge or idle a battery. It owns no
equipment; it is paid from what it saves against the bill the site would have paid without it. Markets in order:
ISO-NE and PJM first, then Ontario, then NYISO.

This repository is Aurivest's public record: the forecasting system's daily call, filed every morning before the day
unfolds, so anyone can check it against independent public data instead of taking our word for it.

## The record

- **`record/calls.md`**: every daily call as issued, with its issue time. Rows are never edited after the fact; a
  day with no call is shown as a gap, never backfilled.
- **`record/daily/*.json`**: the machine-readable form of each call: issue time, model identifier and config hash,
  and the hash and time of the private data-repository commit that filed it (the audit trail, shown in diligence).

The live call is for Ontario: the hour each day when provincial demand peaks, the signal behind Ontario's
coincident-peak charges. Realized peaks can be checked against IESO's published Ontario demand.

## Read the calls as a running log, not as evidence

The backtest figures this page used to show (94% of coincident-peak hours delivered, about $3.4M a year per site)
are **withdrawn**. In October 2026 an internal audit of the data layer found an input stamped as known before it
was actually published, which lets a backtest see the future. Every input series is now being re-verified, and the
models will be re-tested under rules registered before the run. New figures will appear here only after that.

The daily calls keep being published as issued in the meantime, whatever their quality: the gap is the thing a
public record must not have.

## Publication dates

From 2026-08-19 to 2026-09-02, and from 2026-10-15 on, this repository's own commit history shows when each call
became public. The calls of 2026-09-04 to 2026-10-14 were filed every morning in the private data repository but
not mirrored here until 2026-10-15; each carries the hash and time of the private commit that filed it.

## What is not here

The system itself (models, features, data pipeline, dispatch and evaluation) is private. Method-level material that
once appeared in this repository was removed on 2026-09-03, history included. Counterparties in diligence are walked
through the private repositories under NDA.

---

*Built by a solo founder. Contact: sam@aurivestenergy.com*
