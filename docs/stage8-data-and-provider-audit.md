# Stage 8 Data and Provider Audit

Audit date: 2026-07-22  
Baseline: `30dc780de6c004e239fe5d768bcc4cc098464573` (`stage7.5-validated`)

## Decision

The repository has live current quotes and live adjusted daily OHLCV, but it does not have an entitled production news feed, official-event feed, filings feed, earnings feed, or intraday market-data feed. Stage 8 therefore uses explicit provider-neutral interfaces, hermetic fixtures, metadata-only caching, and typed unavailable or daily-only production states. It never treats fixture data as live.

Observed credentials prove only that the already-integrated quote and daily-history calls can authenticate. They do not prove news entitlement, redistribution rights, article-body storage rights, correction behavior, or intraday access.

## Source inventory

### Finnhub current quote

- Provider/dataset: Finnhub current quote.
- Source type: secondary market-data vendor.
- Availability: integrated and live-testable; an authenticated SPY request succeeded during this audit.
- Authentication: `FINNHUB_API_KEY` is configured; no credential value is recorded here.
- Rate limits: plan-specific and not represented by a verified repository contract; treat as unknown.
- Historical coverage: not applicable to the current-quote adapter. Daily candles are separately capability-gated.
- Real-time delay: not contractually established in the repository; each response retains its observed market timestamp.
- Licensing/storage restrictions: unknown; retain normalized quote metadata only under the existing cache policy.
- Supported entities: registered ticker symbols accepted by the existing provider adapter.
- Timestamp quality: provider market timestamp is available, but quote volume is not.
- Current integration: `backend/app/providers/finnhub_provider.py`, routed through `backend/app/providers/router.py` and `backend/app/services/market_data_repository.py`.
- Recommended Stage 8 use: current-price confirmation only; never news evidence, session volume, or an intraday sequence.
- Live testing: yes, for the already-integrated quote operation.

### Polygon adjusted daily OHLCV

- Provider/dataset: Polygon adjusted daily aggregates.
- Source type: secondary market-data vendor.
- Availability: integrated and live-testable; authenticated SPY daily bars through 2026-07-21 succeeded during this audit.
- Authentication: `POLYGON_API_KEY` is configured; no credential value is recorded here.
- Rate limits: plan-specific and not encoded as a verified repository contract; the adapter caps a request at 1,500 bars.
- Historical coverage: observed local holdings span 2024-06-18 through 2026-07-17 for 126 tickers; this is an observation, not a provider guarantee.
- Real-time delay: not contractually established; daily bars are treated as completed-session evidence only.
- Licensing/storage restrictions: unknown beyond the project's existing normalized daily-bar cache use.
- Supported entities: registered ticker symbols; adjusted daily interval only in the current adapter.
- Timestamp quality: date/time is normalized; provider aggregate VWAP and transaction count may be present, but downstream Stage 7 analytics do not retain an intraday VWAP series.
- Current integration: `backend/app/providers/polygon_provider.py`, daily history routing, persistent caches, and `backend/app/market_history/`.
- Recommended Stage 8 use: close-to-close and multi-session reaction windows, daily candle, and volume-versus-history where coverage is sufficient.
- Live testing: yes, for the already-integrated daily-history operation.

### Intraday OHLCV and session data

- Provider/dataset: none in production.
- Source type: unavailable.
- Availability/authentication: both configured real providers declare `supports_intraday_history=False` and reject non-daily intervals.
- Rate limits/historical coverage/real-time delay/licensing: unavailable or unknown because no integration exists.
- Supported entities: hermetic Stage 8 fixtures cover benchmarks, sector ETFs, and selected stocks; fixtures are test-only.
- Timestamp quality: test bars are timezone-aware and validated against an injected US exchange calendar.
- Current integration: no production interface before Stage 8.
- Recommended Stage 8 use: production returns `daily_only` or `unavailable`; deterministic 5-minute and 15-minute analysis is exercised only with explicitly hermetic input.
- Live testing: no.

### News, corporate announcements, and professional wires

- Provider/dataset: none integrated.
- Source type: potentially primary or secondary depending on publisher, but unavailable in production.
- Availability/authentication: no provider interface, endpoint, credential binding, pagination contract, or health check existed before Stage 8.
- Rate limits/historical coverage/real-time delay: unknown.
- Licensing/storage restrictions: entitlement, redistribution, correction, canonical-URL, excerpt, and article-body rights are unknown. Stage 8 must not store article bodies.
- Supported entities: provider-neutral contracts support market, index, sector, theme, security, and watchlist queries; production returns unavailable until explicitly configured.
- Timestamp quality: required by the normalized contract; missing or invalid timestamps fail closed.
- Current integration: Stage 8 adds unavailable, cached, and hermetic implementations only.
- Recommended Stage 8 use: exercise normalization and intelligence logic with permanent fixtures; do not enable a live label from an existing market-data credential.
- Live testing: no.

### SEC/official filings

- Provider/dataset: no EDGAR retrieval integration. Static provenance documents elsewhere in the repository are not a current filings feed.
- Source type: primary when retrieved from an official regulator endpoint.
- Availability/authentication: unavailable; SEC access policy, user agent, pacing, retry, correction, and retention controls are not implemented.
- Rate limits/historical coverage/real-time delay: not audited as an integrated source.
- Licensing/storage restrictions: official-document terms and retention rules must be reviewed before implementation; Stage 8 stores no filing body.
- Supported entities/timestamp quality: future integration should map issuer identifiers and retain filed/accepted times.
- Current integration: none.
- Recommended Stage 8 use: source-registry metadata and hermetic fixtures only.
- Live testing: no.

### Federal Reserve, government statistics, regulators, exchanges, and courts

- Provider/dataset: no production release/calendar collector.
- Source type: primary official source.
- Availability/authentication: no integrated API or feed; hard-coded event-like strings in risk/report/watchlist services are not authoritative event evidence.
- Rate limits/historical coverage/real-time delay: source-specific and unknown for this project.
- Licensing/storage restrictions: source-specific; official status does not remove the need to record usage and retention terms.
- Supported entities: macro, policy, regulation, exchange, and legal event types in the Stage 8 taxonomy.
- Timestamp quality: future feeds must retain release, revision, and retrieval timestamps plus timezone.
- Current integration: configured source registry and hermetic fixtures only.
- Recommended Stage 8 use: primary-source credibility anchors in tests; live output remains unavailable.
- Live testing: no.

### Earnings and company guidance

- Provider/dataset: none integrated.
- Source type: primary when sourced from issuer IR/filing; otherwise secondary.
- Availability/authentication/rate limits/coverage/delay/licensing: unavailable or unknown.
- Supported entities: event contracts support earnings and guidance; no production calendar or transcript is present.
- Timestamp quality: future integration must distinguish scheduled time, publication time, update time, and market session.
- Current integration: older static watchlist earnings values are not accepted as Stage 8 evidence.
- Recommended Stage 8 use: hermetic primary-release and correction fixtures only.
- Live testing: no.

### Breadth, sector, theme, stock, and market snapshots

- Provider/dataset: project-owned derived immutable-snapshot contracts backed by normalized market data.
- Source type: derived secondary evidence.
- Availability: durable latest snapshots exist, but retained histories have uneven dates and some domains currently have only one distinct market date.
- Authentication/rate limits: inherited from upstream market-data providers.
- Historical coverage: observed breadth/sector/theme durable data ended 2026-07-17 at audit time; direct quote/history caches reached 2026-07-21.
- Real-time delay: mixed by snapshot and upstream source; each result must retain evidence date, generated time, source state, and coverage.
- Licensing/storage restrictions: inherits upstream restrictions; no article content is involved.
- Supported entities: registered US market, sectors, themes, indexes, and stock symbols.
- Timestamp quality: `MarketSnapshot.market_timestamp` can reflect fetch time rather than the latest candle. Stage 8 dates claims from underlying bars/events, not that field.
- Current integration: snapshot services and `TrustedCopilotSources`.
- Recommended Stage 8 use: daily reaction, entity/taxonomy mapping, and contextual evidence only; no fabricated intraday breadth timeline.
- Live testing: locally testable; availability is snapshot-specific.

### Cross-asset proxies

- Provider/dataset: ETF and other price proxies in existing market services.
- Source type: derived secondary market evidence.
- Availability: daily market-data coverage varies.
- Authentication/rate limits/coverage/delay/licensing: inherited from Finnhub/Polygon paths.
- Supported entities: registered proxy symbols only.
- Timestamp quality: underlying daily-bar date.
- Current integration: macro/regime services and market snapshots.
- Recommended Stage 8 use: explicitly label bond, dollar, commodity, or volatility proxies. Do not report a direct yield, credit spread, or live VIX from an ETF price. Existing hard-coded mock VIX values are excluded.
- Live testing: only to the extent the underlying registered market-data call is supported.

### OpenAI/model infrastructure

- Provider/dataset: OpenAI model access, not a factual market source.
- Source type: optional transformation infrastructure.
- Availability: a credential is configured, but Stage 8 does not require or call a model.
- Authentication/rate limits/storage: not exercised by the deterministic Stage 8 path.
- Supported entities/timestamp quality: not applicable.
- Current integration: other application surfaces may have model infrastructure; the validated Copilot pipeline reports zero model calls.
- Recommended Stage 8 use: none in the default pipeline. A future optional classifier must run after deterministic normalization, use strict output schema, remain disabled in hermetic tests, and never create or validate facts.
- Live testing: intentionally not performed.

## Cache and persistence observations

- `backend/.cache/market_cache.sqlite3` held 56,228 daily bars across 126 tickers during the audit, plus market/breadth/sector/theme/stock snapshots.
- `backend/data/market_cache.sqlite3` held 566 cache entries including live Polygon history and Finnhub quote entries.
- These counts are local observations, not contractual historical coverage.
- The existing quote and daily-history cache policies do not confer rights to store news bodies.
- Stage 8 news persistence is metadata-only. It records bounded identity metadata, canonical headline, timestamps, provenance, correction lineage, and quarantine metadata; it deliberately excludes summaries, confirmed facts, evidence statements, materiality, reactions, and article bodies.

## Release gates

1. A production news provider cannot be enabled until endpoint access, entitlement, delay, source lineage, corrections, rate limits, canonical URLs, and storage/redistribution rights are documented and tested.
2. Intraday narration cannot be enabled until a real intraday provider and exchange calendar are integrated and validated.
3. Repeated syndicated coverage is one cluster, not independent confirmation.
4. Missing consensus, price, volume, breadth, or cross-asset data stays missing.
5. Any provider-mode mismatch, secret leakage, article-body persistence, stale-as-current event, or daily-data intraday claim is release-blocking.
