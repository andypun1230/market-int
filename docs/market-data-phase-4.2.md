# Market Data Phase 4.2

## Summary

Phase 4.2 adds a durable cache and capability-aware provider-routing layer on top of the Phase 4.1 repository foundation.

The app can now route quotes and daily history independently. This matters because Finnhub live quote access works, while the configured Finnhub plan returns `HTTP 403` for `/stock/candle`.

## Architecture

```text
Consumer
  ↓
MarketDataRepository
  ↓
Memory Cache
  ↓
Persistent SQLite Cache
  ↓
Provider Router
  ├── Finnhub Quotes
  └── Mock/Test History
```

## SQLite Cache

The Phase 4.2 cache lives at:

```text
backend/data/market_cache.sqlite3
```

The database is ignored by Git.

Table:

```text
market_data_cache
- key TEXT PRIMARY KEY
- domain TEXT NOT NULL
- provider TEXT NOT NULL
- source_state TEXT NOT NULL
- payload_json TEXT NOT NULL
- fetched_at TEXT NOT NULL
- market_timestamp TEXT NULL
- expires_at TEXT NOT NULL
- stale_until TEXT NULL
- created_at TEXT NOT NULL
- updated_at TEXT NOT NULL
- schema_version INTEGER NOT NULL
- payload_hash TEXT NULL
- size_bytes INTEGER NULL
- access_count INTEGER NOT NULL DEFAULT 0
- last_accessed_at TEXT NULL
```

Payloads are JSON only. The cache does not use pickle and does not store credentials.

## Cache Policies

Policies are centralized in `CachePolicyRegistry`.

Initial defaults:

- Quotes: memory `20s`, persistent `60s`, stale `300s`
- Daily history: memory `15m`, persistent `12h`, stale `7d`
- Technical history: supported as a separate domain for future indicator-output caching

Environment overrides:

```text
MARKET_DATA_PERSISTENT_CACHE_ENABLED=true
MARKET_DATA_CACHE_DB_PATH=backend/data/market_cache.sqlite3
MARKET_DATA_CACHE_SCHEMA_VERSION=1
MARKET_DATA_STALE_WHILE_REVALIDATE=true
MARKET_DATA_ALLOW_STALE_ON_PROVIDER_ERROR=true
MARKET_DATA_QUOTE_PERSISTENT_TTL_SECONDS=60
MARKET_DATA_QUOTE_STALE_SECONDS=300
MARKET_DATA_HISTORY_PERSISTENT_TTL_SECONDS=43200
MARKET_DATA_HISTORY_STALE_SECONDS=604800
```

## Stale While Revalidate

Fresh memory hits return immediately.

Fresh persistent hits return immediately and hydrate memory.

Stale persistent hits return immediately with:

```text
source_state=stale
is_stale=true
background_refresh_started=true
```

The refresh runs in a bounded local background thread and is deduplicated per key. Failed refreshes do not delete the last-known stale value.

## Provider Routing

Quotes and daily history are routed separately:

```text
QUOTE_DATA_PROVIDER=finnhub
HISTORY_DATA_PROVIDER=mock
```

Fallback remains explicit and controlled by:

```text
MARKET_DATA_ALLOW_MOCK_FALLBACK=true
```

## Provider Capabilities

Capability metadata distinguishes provider support by domain.

Current Finnhub capability:

- Quotes: `available`
- Daily history: `restricted`

Reason:

```text
HTTP 403 {"error":"You don't have access to this resource."}
```

The router avoids repeatedly calling providers known to lack a capability. If a future plan supports Finnhub candles, `FINNHUB_DAILY_HISTORY_ACCESS_STATE=available` can be used while validating.

## Technical History Migration

The existing stock technical pipeline already consumes history through `app/services/candle_data.py`.

Phase 4.2 upgrades that shared path through `MarketDataRepository`, so these consumers inherit layered cache and routing behavior:

- stock detail chart history
- support/resistance
- trendline
- volume analysis
- risk ATR inputs
- relative strength
- timeframe signal inputs

One repository history request can feed multiple indicator calculations through cache reuse.

## Source States

The repository preserves:

- `live`
- `delayed`
- `cached`
- `stale`
- `mock`
- `mixed`
- `unavailable`

Fallback is separate metadata:

- `fallback_used`
- `fallback_reason`
- `original_provider`

## Diagnostics

Endpoints:

```text
GET  /market-data/status
GET  /market-data/cache/status
POST /market-data/cache/invalidate
POST /market-data/cache/cleanup
```

Diagnostics include memory/persistent counts, stale counts, provider routing, capabilities, and repository metrics. Payloads and secrets are not exposed.

## Frontend Handling

Data Sources shows quote/history providers and capability state.

Data Usage shows persistent cache status and provides a working clear-cached-market-data action.

Stock Detail can now represent live quotes with mock/stale/cached history as mixed-source analysis through existing source metadata.

## Test Strategy

Automated tests cover:

- persistent cache restart reuse
- stale-while-revalidate
- failed refresh preserving stale data
- provider routing for Finnhub quotes and mock history
- restricted Finnhub history capability
- repository history reuse for technical consumers

Live provider tests are not required for automated runs.

## Known Limitations

- Finnhub daily candles remain restricted under the configured plan.
- No alternate paid history provider is implemented yet.
- Breadth, sectors, themes, macro, reports, and broad market prefetch are not migrated in this phase.
- Persistent cache is local SQLite, not Redis or distributed cache.

## Phase 4.3 Recommendations

- Add a real history-capable provider adapter.
- Validate daily history quality against known fixtures.
- Migrate additional technical and comparison endpoints.
- Add provider-specific symbol mapping only after real coverage gaps appear.
- Keep source-state labels conservative while live and mock domains coexist.
