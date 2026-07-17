# Market Data Phase 4.3

## Summary

Phase 4.3 adds Polygon/Massive as the first real daily OHLCV history provider while preserving the existing Phase 4.1 and 4.2 repository/cache architecture.

Provider split:

```text
Quotes:        Finnhub
Daily history: Polygon / Massive
Mock/test:     deterministic development and fallback modes
```

The internal provider id remains `polygon` even though Polygon's current documentation and UI may use Massive branding.

## Provider Endpoint

Daily stock and ETF history uses the stocks aggregate endpoint:

```text
GET /v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from}/{to}
```

Phase 4.3 maps daily history as:

```text
multiplier=1
timespan=day
adjusted=true
sort=asc
limit=50000
```

`POLYGON_BASE_URL` defaults to:

```text
https://api.polygon.io
```

The provider documentation currently redirects Polygon docs to Massive branding; this app keeps `polygon` as the stable internal provider id.

## Environment

Canonical routing variables:

```text
QUOTE_DATA_PROVIDER=finnhub
HISTORY_DATA_PROVIDER=polygon
```

Provider variables:

```text
POLYGON_API_KEY=
POLYGON_BASE_URL=https://api.polygon.io
POLYGON_HISTORY_ADJUSTED=true
POLYGON_HISTORY_LIMIT=50000
POLYGON_TIMEOUT_SECONDS=15
POLYGON_MAX_RETRIES=2
POLYGON_MAX_PAGES=10
POLYGON_DEBUG=false
```

`HISTORY_PROVIDER` remains supported as a compatibility fallback, but `HISTORY_DATA_PROVIDER` is authoritative.

## Normalization

Polygon aggregate records are normalized into the existing `HistoryData` model.

Required fields:

```text
timestamp
open
high
low
close
volume
```

Optional fields:

```text
vwap
transactions
```

Normalization behavior:
- converts Polygon Unix millisecond timestamps to timezone-aware ISO timestamps,
- sorts bars ascending,
- removes duplicate timestamps,
- rejects invalid OHLC relationships,
- rejects negative prices and negative volume,
- preserves zero volume,
- skips malformed individual bars when safe,
- raises a controlled provider error if all bars are invalid.

## Adjusted History

Adjusted daily bars are requested by default with:

```text
adjusted=true
```

This supports split-adjusted chart continuity and technical indicator consistency. The provider adjustment metadata is reflected by `HistoryData.adjusted=true`.

Dividend adjustment methodology can vary by provider and should not be described as total-return adjustment.

## Pagination

The provider supports `next_url` pagination.

Behavior:
- follows `next_url` when present,
- attaches the API key to next-page requests without logging it,
- guards against repeated `next_url` loops,
- stops at `POLYGON_MAX_PAGES`,
- removes duplicate bars across pages.

Most Stock Detail daily-history windows fit in one request, but pagination support prevents silent truncation.

## Error Handling

Provider errors are classified as:

```text
authentication
permission
invalid_symbol
rate_limited
transient
network
invalid_json
no_data
unsupported_provider
unsupported_resolution
```

Retries are limited to transient/network cases and selected provider throttling. Stable 400/401/403/404/no-data conditions are not retried.

`POLYGON_DEBUG=true` enables safe diagnostics:
- symbol,
- date range,
- adjusted flag,
- URL without API key,
- HTTP status,
- result counts,
- page count,
- normalized bar count,
- first/latest timestamp,
- latency,
- error category.

API keys and full history payloads are not logged.

## Provider Routing

`MarketDataProviderRouter` now registers:

```text
polygon:
  supports_quotes: false
  supports_batch_quotes: false
  supports_daily_history: true when configured
  supports_intraday_history: false
```

Expected routing:

```text
QUOTE_DATA_PROVIDER=finnhub
HISTORY_DATA_PROVIDER=polygon
```

Result:
- quote requests route to Finnhub,
- daily-history requests route to Polygon,
- Finnhub candles are not called,
- unsupported providers raise a controlled error instead of falling through to generated test data.

## Cache Behavior

Polygon history uses the existing `daily_history` cache policy.

Cache keys include provider identity:

```text
history:polygon:{symbol}:{resolution}:{days}
history:mock:{symbol}:{resolution}:{days}
```

This prevents cross-provider contamination when switching between mock/test and Polygon history.

Expected behavior:
- first request calls Polygon,
- memory cache is populated,
- SQLite cache is populated,
- repeated request uses memory,
- repository recreation uses persistent SQLite,
- stale history returns immediately,
- background refresh deduplicates,
- failed refresh preserves stale history.

## Technical Pipeline

Stock Detail technical consumers continue to use:

```text
app/services/candle_data.py
```

That shared path uses `get_market_data_provider()`, which now resolves through `MarketDataRepository`, layered cache, and provider router.

The same normalized history series feeds:
- chart history,
- EMA/SMA calculations,
- RSI,
- MACD,
- volume analysis,
- support/resistance,
- trendline and risk inputs where already migrated.

Breadth, sectors, themes, macro, reports, and Copilot are not migrated in this phase.

## Quote/History Timing

Finnhub quotes may represent a current live price while Polygon daily bars may end at the previous completed session.

The app should treat this as:

```text
Quote: live/delayed Finnhub
History: daily Polygon bars through last available session
Overall: mixed providers/timing where applicable
```

Phase 4.3 does not append a live quote to the daily history line.

## Fallback Behavior

When `MARKET_DATA_ALLOW_MOCK_FALLBACK=true`:
- Polygon failure may return mock fallback history,
- `fallback_used=true`,
- `fallback_reason` is populated,
- `requested_provider=polygon`,
- `provider=mock`,
- source is explicitly mock fallback.

When `MARKET_DATA_ALLOW_MOCK_FALLBACK=false`:
- Polygon history failure returns a controlled unavailable error,
- live quote data may still display,
- no generated history is silently substituted.

## Known Limitations

- Only U.S. stock and ETF daily history is required.
- Intraday bars are not integrated.
- Current-session daily bar construction is out of scope.
- Finnhub remains the quote provider.
- Index-specific history may need separate provider support.
- Breadth, sectors, themes, macro, reports, options, and Copilot remain outside this phase.
- Live Polygon access must be validated with a real configured key before Phase 4.3 can be called fully complete.
