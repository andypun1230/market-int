# Phase 4.4B Breadth Architecture

## Current-State Audit

Before this phase, `app.services.breadth` calculated a small `core` basket synchronously through `basket_data`. The same result was independently requested by Market Health, Market Regime, MarketSnapshot, Market Core, and `/market/breadth`. That made breadth screen-triggered, allowed generated fallback data, and had no durable constituent history, coverage contract, or common snapshot identity.

Phase 4.4B adds a parallel fast-read path. The legacy calculator remains only for explicit compatibility/test callers; strict live mode returns unavailable rather than substituting a mock constituent set.

## Security Master And Universe

`app.securities` persists canonical uppercase securities, explicit Finnhub/Polygon symbols, class-share mappings (for example `BRK.B` to `BRK-B`), normalized sectors, active state, provenance, and metadata version in SQLite.

`breadth_universes` and `breadth_universe_members` are immutable versions. The intended live universe name is `sp100`; the official maintenance reference is [S&P Dow Jones Indices S&P 100](https://www.spglobal.com/spdji/en/indices/equity/sp-100/). Runtime never scrapes it. The reviewed dated source is `backend/data/reference/sp100-2026-07-18.csv`; its provenance and review notes are in the adjacent Markdown file. A maintainer imports a reviewed source file with:

```bash
cd backend
python3 scripts/validate_security_universe_source.py --source-file data/reference/sp100-2026-07-18.csv --expected-members 101
python3 scripts/import_security_universe.py --universe sp100 --source-file data/reference/sp100-2026-07-18.csv --dry-run
python3 scripts/import_security_universe.py --universe sp100 --source-file data/reference/sp100-2026-07-18.csv --apply
```

The source contains `members`, version, source timestamp, ticker, company name, and sector. Import creates a new universe version and retains prior membership rows.

## Durable Data Lifecycle

`app.market_history.daily_price_bars` stores adjusted Polygon daily OHLCV keyed by ticker/provider/session/adjusted. Upserts validate OHLC, non-negative volume, UTC timestamps, and future-session rejection. It is distinct from the layered market-data cache.

Initial seed is explicit and resumable:

```bash
python3 scripts/seed_breadth_universe.py --universe sp100 --lookback-calendar-days 450 --resume
```

Before a full seed, use the five-session strict live provider probe. The staged seed accepts either an explicit reviewed ticker list or a deterministic `--limit`:

```bash
MARKET_DATA_ALLOW_MOCK_FALLBACK=false python3 scripts/validate_breadth_provider_support.py --universe sp100 --remote
MARKET_DATA_ALLOW_MOCK_FALLBACK=false python3 scripts/seed_breadth_universe.py --universe sp100 --limit 10 --lookback-calendar-days 450
```

It checkpoints each completed ticker. The incremental updater uses latest stored session plus a seven-day overlap; it does not refetch the full seed window. Neither job runs from an HTTP read.

## Calculation Policy

The pure `app.breadth.engine.calculate_breadth` consumes only stored bars and universe metadata. EMA uses the standard alpha `2/(span+1)` recursion. A member advances, declines, or is unchanged by comparing its session close with the previous session close. EMA20/50/200 require 20/50/200 bars. 52-week highs/lows use the current close against the preceding 251 closes in a 252-session window.

Each indicator denominator is the eligible members with sufficient stored bars for that indicator. Missing, stale, and invalid members are explicit; no value is fabricated. Complete requires overall and EMA200 coverage of at least 90%; partial requires overall and EMA50 coverage of at least 75%; otherwise breadth is unavailable. These thresholds are configurable through `BREADTH_MIN_COMPLETE_COVERAGE` and `BREADTH_MIN_PARTIAL_COVERAGE`.

The documented score weights are 15% EMA20, 30% EMA50, 25% EMA200, 15% daily participation, and 15% highs/lows leadership, renormalized only across valid metrics. Statuses are strong, healthy, mixed, weak, and oversold. Conservative divergence requires ten persisted breadth snapshots and a meaningful opposite ten-session benchmark/breadth move.

## Snapshots And Reads

`BreadthSnapshot` rows are immutable and namespace their latest and last-known-good pointers by provider mode, history provider, and universe. Test snapshots cannot be served in live mode. An unavailable rebuild retains last-known-good. Snapshot retention defaults to 260 rows.

Background orchestration loads persisted state immediately, schedules a non-blocking refresh, deduplicates builds, and never silently seeds a 100-symbol universe. `BREADTH_ENABLED`, `BREADTH_STARTUP_DELAY_SECONDS`, `BREADTH_REFRESH_INTERVAL_SECONDS`, and coverage/retention variables control it.

The APIs `/market/breadth`, `/market/breadth/snapshot/latest`, `/market/breadth/snapshot/{id}`, `/market/breadth/snapshot/status`, `/market/breadth/status`, and `/market/breadth/history` only read persisted snapshots. `/market/breadth/snapshot/refresh` schedules a background build. The MarketSnapshot/Health/Regime adapters carry the same `breadth_snapshot_id`; no user-facing request fetches constituent bars.

Frontend source details describe the universe version, latest completed market session, coverage, warnings, and Polygon daily-history provenance. Daily breadth is never labelled intraday live breadth.
