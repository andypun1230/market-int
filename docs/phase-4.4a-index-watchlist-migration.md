# Phase 4.4A Index And Watchlist Migration

## Scope

Phase 4.4A keeps the existing Finnhub quote and Polygon daily-history provider split. It does not migrate Breadth, Sectors, Themes, Macro, or add a provider.

## Canonical Index Registry

The backend canonical index universe is defined in `backend/app/validation/symbol_registry.py`.

Core enabled indexes:

- `SPY` - S&P 500
- `QQQ` - Nasdaq-100
- `IWM` - Russell 2000
- `DIA` - Dow Jones

Optional equal-weight indexes:

- `RSP` - S&P 500 Equal Weight
- `QQEW` - Nasdaq-100 Equal Weight

Canonical aliases are enforced in `backend/app/providers/symbols.py` before repository routing, cache keys, history coordinator keys, persistent-cache lookup, and provider request formation:

- `SPX -> SPY`
- `NDX -> QQQ`
- `IXIC -> QQQ`
- `RUT -> IWM`
- `DJI -> DIA`
- `QQQEW -> QQEW`

## IndexSnapshot Behavior

`MarketSnapshotBuilder` builds the `indexes` section from the already-fetched `MarketSnapshotInputBundle`. This prevents Home and Market from calculating or requesting separate index quote/history values during snapshot construction.

The `IndexSnapshot` model now carries provider/source metadata:

- display symbol and display name
- provider-bound symbol
- quote and history providers
- quote timestamp and latest history date
- source state and stale state
- previous close
- warning list

`/market/indexes` reads the latest MarketSnapshot `indexes` section when available, with the previous index service retained only for cold-start compatibility.

## Gain Calculation

Quote gain policy is centralized in `backend/app/services/gain_policy.py`.

Quote gains use:

- `change = current_price - previous_close`
- `change_percent = change / previous_close * 100`

Historical period gain remains separate and uses:

- `last_visible_close / first_visible_close - 1`

Frontend consumers should use backend-provided gain fields and not recalculate daily quote percentage independently.

## Watchlist Fast-Read Path

`/watchlist/summary` now uses `MarketDataRepository.get_batch_quotes()` for bounded quote/cache reuse. Optional rating, relative-strength, and pattern fields are read only from existing service cache entries.

The initial watchlist summary does not fetch history and does not build StockAnalysisSnapshots.

The watchlist summary includes:

- `snapshot_id`
- `created_at`
- `membership_hash`
- `status`
- `source_state`
- requested/available/unavailable symbols
- `coverage_ratio`
- items
- leaders and laggards
- warnings

One unavailable symbol remains isolated to that item and does not fail the whole list.

## Membership Hash

The membership hash is generated from normalized symbols plus a version. It is used in the service-cache key as `watchlist-summary:{membership_hash}` so membership changes invalidate the summary deterministically.

## Sorting Policy

Frontend watchlist sorting remains stable and numeric:

- gain and loss sorts use numeric `change_percent`
- missing values sort predictably after available values
- manual order uses original item order

## Source Metadata

Index, Home, Market, Watchlist, and Stock Detail quote paths now have consistent provider/source fields available:

- quote provider: Finnhub in live routing
- history provider: Polygon where history is shown
- source state: live/cached/stale/mixed/unavailable
- stale flags and timestamps

## Remaining Limitations

Cold live watchlist latency still depends on Finnhub quote latency. Optional watchlist analytics may be absent until their existing cached services have produced values.

## Phase 4.4B Readiness

The index/watchlist consistency work is isolated from Breadth, Sectors, Themes, and Macro so later migrations can reuse the same snapshot/cache conventions without changing provider architecture.
