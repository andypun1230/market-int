# Stock Detail Snapshot Performance

## Before Request Graph

Opening one Stock Detail view used a synchronous aggregate call plus chart-specific history calls:

- `/market/stock-analysis/{symbol}` fanned out to support/resistance, trendline, volume, risk, multi-timeframe, patterns, relative strength, rating, options, and liquidity.
- The selected symbol history was fetched repeatedly by those services, usually at `240`, `365`, or service-specific windows.
- `StockMiniChart` separately requested `/market/live/history/{symbol}` for `1M`, `6M`, and `1Y`, so period switching could create additional provider/cache work.
- Relative strength could request `SPY`, `QQQ`, and sector benchmark histories during the primary detail path.
- Compare loaded peer histories separately, but the primary aggregate still had enough synchronous history work to reach 10-20 seconds on cold or degraded provider paths.

## New Fast Path

Stock Detail now reads a per-symbol `StockAnalysisSnapshot`:

- One canonical selected-symbol daily history request is planned by `StockDetailInputPlanner` (`450` days by default).
- Chart windows (`1D`, `1W`, `1M`, `6M`, `1Y`) are sliced from the canonical history.
- Overview, Technical, Signals, Risk, summary, rating, support/resistance, trend, volume, relative strength, pattern, and leadership sections consume one prepared input bundle.
- Benchmark histories are cache-only optional inputs; missing benchmark data degrades relative strength without blocking selected-stock analysis.
- `/market/stock-analysis/{symbol}` is now a compatibility fast-read endpoint over the snapshot service.
- `/market/stock-snapshot/{symbol}`, `/status`, and `/refresh` expose direct snapshot operations.
- No snapshot returns an immediate `initializing` payload and queues one background build.
- Stale snapshots return immediately and queue a deduped background refresh.
- Failed refreshes do not overwrite the latest last-known-good snapshot.
- Compare remains outside the primary snapshot and continues to load lazily.

## Validation Snapshot

Latest test-mode validator run:

- Warm `/market/stock-analysis/NVDA`: `15 ms`
- Warm `/market/stock-snapshot/NVDA`: `5 ms`
- Warm provider calls: `0` quote, `0` history
- Canonical selected history windows: `[450]`
- Period-switch provider calls: `0`
- Restart persistence: passed
- HTTP 500 count in application validation: `0`

Remaining conditions are cold external-provider latency and native visual checks for rapid tab/modal transitions.
