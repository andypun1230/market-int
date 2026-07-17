# Market Data Phase 4.1

Phase 4.1 establishes a provider-neutral market-data foundation without migrating the full app.

## Flow

```text
Consumer endpoint or service
  -> MarketDataRepository
  -> in-memory TTL cache and in-flight request registry
  -> configured provider
     -> Finnhub live provider
     -> generated test-data provider
     -> deterministic mock provider fallback
```

The frontend never calls Finnhub or any external market-data provider directly.

## Providers

- `generated_test_data`: default development and automated-test mode.
- `mock`: deterministic offline mock provider.
- `finnhub`, `live`, `auto`: Finnhub quote and daily-history pilot provider.

Mock and generated test data remain first-class providers for UI development, tests, reports, Copilot, and provider-failure simulation. Mock fallback is always labelled with `source=mock-fallback`, `source_state=mock`, and `fallback_used=true`.

## Repository Responsibilities

`app.services.market_data_repository.MarketDataRepository`:

- normalizes symbols through `normalize_market_symbol`
- deduplicates symbols for batch quotes
- applies small in-memory TTL caching
- prevents duplicate simultaneous upstream requests with single-flight in-flight tracking
- routes to the configured provider
- applies explicit mock fallback only when enabled
- annotates source state, provider, cache hit, cache age, and fallback reason
- exposes provider health and cache status

## Source States

Supported source states:

- `live`
- `delayed`
- `cached`
- `stale`
- `mock`
- `mixed`
- `unavailable`

Screen-level aggregation should not label a mixed response as live. Existing frontend types accept optional cache and fallback metadata on quote and history responses.

## Environment Variables

Important Phase 4.1 variables:

```text
DATA_PROVIDER=test
MARKET_DATA_PROVIDER=test
MARKET_DATA_API_KEY=
FINNHUB_API_KEY=
MARKET_DATA_BASE_URL=
MARKET_DATA_TIMEOUT_SECONDS=8
MARKET_DATA_MAX_RETRIES=2
MARKET_DATA_CACHE_ENABLED=true
MARKET_DATA_QUOTE_TTL_SECONDS=20
MARKET_DATA_HISTORY_TTL_SECONDS=1800
MARKET_DATA_ALLOW_MOCK_FALLBACK=true
MARKET_DATA_LOG_PROVIDER_CALLS=false
MARKET_DATA_DEFAULT_HISTORY_DAYS=365
```

API keys are backend-only and must not appear in frontend environment variables, logs, Copilot context, reports, or error payloads.

## Pilot Integrations

Migrated pilot paths:

- `GET /market/indexes`
- `GET /market/indexes/{symbol}/history`
- `GET /market/live/quote/{symbol}`
- `GET /market/live/history/{symbol}`
- `GET /market/live/quotes`
- `GET /system/provider-status`
- `GET /market-data/status`

The rest of the market engines may still use existing generated test data or deterministic mock data until later migration phases.

## Health and Cache Diagnostics

- `GET /system/provider-status`
- `GET /market-data/status`
- `GET /system/provider-cache`
- `POST /system/provider-cache/clear`

Diagnostics expose provider names, source states, health, fallback flags, and cache counts only. They do not expose API keys, raw authenticated URLs, or secret headers.

## Tests

Automated tests must default to test/mock providers and must not call live providers. Live-provider validation is manual and opt-in by setting `DATA_PROVIDER=finnhub` and `FINNHUB_API_KEY`.

## Known Limitations

- No Redis or new persistent cache was added for Phase 4.1.
- Existing persistent cache utilities remain in the codebase from earlier performance work, but the repository pilot uses a small in-memory TTL cache.
- No websocket, tick data, intraday aggregation, options, macro, sector constituent ingestion, or full market-engine migration is included.
- Finnhub candle availability depends on account permissions; failures can fall back to mock only when `MARKET_DATA_ALLOW_MOCK_FALLBACK=true`.

## Phase 4.2 Recommendations

- Expand repository usage into technical engines after provider quality is verified.
- Add provider-specific symbol mapping for non-US assets.
- Add opt-in live integration tests with recorded HTTP fixtures.
- Add rate-limit aware batching for larger watchlists.
- Revisit persistent cache strategy once live provider behavior is stable.
