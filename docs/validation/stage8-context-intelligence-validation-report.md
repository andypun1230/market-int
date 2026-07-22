# Stage 8 Context Intelligence Validation Report

Generated: 22 July 2026 (Asia/Hong_Kong)

## Verdict

**PASS WITH CONDITIONS**

Stage 8 adds deterministic, evidence-linked News Intelligence and Session Narrative capabilities without weakening the validated Stage 7 and Stage 7.5 boundaries. The release conditions are provider entitlement, presentation completeness, centralized tracing, and manual native-device validation—not fabricated data or ignored failing gates.

## Baseline and scope

- Baseline commit: `30dc780de6c004e239fe5d768bcc4cc098464573`
- Baseline tag: `stage7.5-validated`
- Final commit: not available; the Stage 8 work remains an uncommitted working-tree change.
- Registered Copilot agents: 15 before and after Stage 8; no new agent was registered.
- Stage 8 added no Report/PDF design, Portfolio Intelligence, Scenario Probability, Probability Intelligence, Decision Intelligence, order routing, or automatic trading.

The provider audit covered Finnhub quote/news capability, Polygon daily/intraday OHLCV entitlement, economic calendars, filings, earnings, announcements, local daily history and immutable snapshots, persistence, timezones, evidence registries, provider health, and model infrastructure.

## Provider truth

Implemented provider boundaries are:

- `UnavailableNewsProvider`: production default.
- `HermeticNewsProvider`: explicit offline test data only.
- `CachedNewsProvider`: whitelisted metadata-cache reads only.
- `ProductionSessionDataAdapter`: `daily_only` or `unavailable`; daily bars are never resampled into intraday claims.

No licensed live News provider, production 5/15-minute OHLCV provider, live filings/calendar/earnings feed, or intraday breadth history is configured. Finnhub is used for current quotes elsewhere in the repository and Polygon storage supplies adjusted daily OHLCV; neither is represented as a live Stage 8 news or intraday-session entitlement. The production News singleton has no metadata repository configured, so collection reads are honestly unavailable by default. Cached event detail is available only when metadata has been explicitly persisted.

## Service inventory

News Intelligence (`news-intelligence-v1`) provides strict provider/query contracts, 25 event types, a nine-record source registry, input normalization and quarantine, source credibility, deterministic classification, clustering/correction lineage, registry-backed entity mapping, transparent materiality contributions, daily reaction windows, confidence/contradiction handling, metadata-only persistence, cache-only retrieval, and typed unavailable states.

The 25 event types are monetary policy, inflation, employment, economic growth, government policy, regulation, geopolitics, earnings, guidance, merger/acquisition, capital raise, buyback, dividend, product launch, supply chain, customer contract, legal, management change, analyst action, credit rating, cybersecurity incident, exchange notice, market structure, positioning commentary, and other.

Session Narrative (`session-narrative-v1`) provides exchange-calendar-aware segmentation, normal and shortened-session handling, enriched phase aggregates, premarket/after-hours/holiday/weekend states, deterministic confirmed turning points, VWAP/volume analysis where evidence supports it, evidence-linked catalyst timelines, strict claim-to-evidence validation, and a production adapter that refuses to infer intraday behavior from daily data.

Both services reuse the Stage 7.5 Freshness and Availability, Evidence Validation, Contradiction Preservation, and Confidence Adjustment engines.

## API and consumer integration

Registered Stage 8 API routes are:

- `GET /intelligence/news/market`
- `GET /intelligence/news/index/{index_id}`
- `GET /intelligence/news/security/{symbol}`
- `GET /intelligence/news/sector/{sector_id}`
- `GET /intelligence/news/theme/{theme_id}`
- `GET /intelligence/news/watchlist`
- `GET /intelligence/news/events/{event_id}`
- `GET /intelligence/session/market`
- `GET /intelligence/session/{symbol}`

Collection News routes use the configured production provider boundary and therefore return typed unavailable data today. Event detail performs a direct metadata-cache lookup and does not invoke the configured provider. Session routes consult local Polygon daily-bar storage only through the New York market date implied by `as_of`, then return `daily_only` or `unavailable` without intraday prose.

Copilot preserves the existing 15-agent registry. Explicit News intents can feed Market, Index, Macro, Leadership, Risk, Sector, Theme, Stock, Watchlist, and Research agents; explicit Session intents feed Market, Index, and Stock. The Report agent has a typed News/Session retrieval seam and executable retrieval test, with no PDF renderer change. Legacy intents retain their Stage 7 source-call and routing behavior.

Frontend consumers are integrated on Home, Market Overview, Sector/Theme detail, Stock detail, and Watchlist through the shared typed result normalizers and request deduplication. The current cards render headline, source quality, materiality scores, affected labels, reaction summary, top contradiction, freshness, and limitations. Presentation remains incomplete for interactive event links, confirmed-fact/evidence detail, reaction windows/classification, structured session turning points, sector/theme breadth/thesis/horizon, stock volume/technical/thesis implications, and named watchlist state badges.

## Validation evidence

The permanent fixture file contains 150 unique, hermetic scenario-catalog rows, including all 30 required release cases. It permits zero network calls, zero model calls, and zero article-body persistence. Catalog rows executed end-to-end: 0. Five executable corpus-integrity tests validate the catalog. This is a permanent scenario catalog backed by targeted executable suites, not 150 passing end-to-end fixtures.

Current Stage 8 focused result: **122/122 tests passed**. Coverage includes News, Session, APIs, exact routing prompts, Copilot evidence adaptation, safety, failure paths, fixture integrity, and performance. The final machine artifact is authoritative for the consolidated release run.

The refreshed 250-iteration hermetic benchmark observed:

- 20 synthetic provider events normalized into 10 canonical clusters; duplicate reduction ratio `0.50`.
- Mapped canonical-event ratio `1.00`; mapping evidence-lineage ratio `1.00`.
- 80 transparent materiality contributions and 10 traceable reaction evidence references.
- News pipeline p95 `12.231792 ms`; Session pipeline p95 `2.867833 ms`.
- Copilot routing p95 `0.047542 ms`; full Copilot pipeline p95 `39.749542 ms`.
- News endpoint p95 `1.330250 ms`; Session endpoint p95 `16.721083 ms`.
- Network calls `0`; model calls `0`; all benchmark thresholds passed.

These figures are deterministic in-process observations on synthetic metadata and recorded bars. They are not production mapping accuracy, production deduplication efficacy, deployed-network latency, or service-level objectives.

Materiality validation keeps market, entity, and user/watchlist relevance separate; watchlist overlap cannot raise market materiality. Reaction validation requires traceable price evidence, an explicit supported window, and validated source quality. Missing benchmark data uses an explicitly labeled absolute return rather than a zero substitute; missing price remains insufficient data with no invented evidence. Timing and correlation are never promoted to causation.

Session validation covers exact normal/early-close boundaries, final-hour windows, partial sessions, enriched aggregates, extended-hours-only and closed states, conservative turning points, catalyst ordering/publication boundaries, daily-only production behavior, and nested narrative claim-to-evidence references.

Safety validation treats all News text as untrusted and covers prompt injection, HTML, Markdown, scripts, malicious URLs, invalid tickers, source spoofing, fake official domains, oversized text, credential-reveal requests, secret redaction, and repository/body-persistence guards. Failure validation covers provider timeout/rate limit, malformed records, invalid timestamps, duplicate/conflicting IDs, entity-map failure, stale cache, corrupt bars/calendar/query data, storage failure, and structured endpoint degradation. Some requested failures are grouped into shared executable methods rather than one method per label; breadth-unavailable and generic service-timeout breadth remain conditions.

The benchmark and DTOs expose event/cluster/source/evidence IDs, mappings, materiality components, reaction windows, phase and turning-point evidence, fallback state, cache state, latency, contradictions, and confidence. A centralized trace recorder is not integrated; current observability is structured result metadata plus the hermetic benchmark.

## Regression status

The final consolidated `make validate-stage8 PYTHON=venv/bin/python` run passed with zero failed gates. It executed **536/536 backend tests** before the focused Stage 8 component rerun and final artifact aggregation.

The saved pre-implementation baseline passed:

- Stage 7 backend: 414/414.
- Stage 7 runtime: 30/30 with zero release blockers.
- Stage 7 frozen reference corpus: 165/165, explicitly non-release-bearing.
- Stage 7 failure injection: 7/7.
- Stage 7 routing accuracy/required-agent recall: 100%; unnecessary-agent and invalid-route rates: 0%.
- Stage 7.5 backend: 414/414.
- Stage 7.5 focused Stage 7 tests: 91/91.
- Institutional Copilot: 39/39.
- Stage 7.5 semantic equivalence: 30/30.
- Frontend TypeScript, lint, data-UI, focused Copilot tests, and 25-route static web export: passed.

The final command reran every listed regression gate before generating the machine-readable Stage 8 artifact. Its Stage 7 runtime result was 30/30 with zero release blockers, the reference corpus was 165/165, Stage 7.5 semantic equivalence was 30/30, the Stage 8 suite was 122/122, and all frontend checks plus the 25-route static export passed.

## Defects fixed during validation

- Removed generated reaction evidence/source identifiers and required referentially valid source lineage.
- Prevented missing price or benchmark evidence from becoming a supported reaction claim.
- Preserved News/Session evidence, contradictions, confidence caps, and missing-data semantics through Copilot.
- Added direct cached event reconstruction so cluster members and deep links survive event-detail retrieval.
- Added exact routing coverage for all twelve specified user prompts and typed Leadership/Risk/Research/Report seams.
- Rejected future News ranges and future Session dates and bounded daily provenance by query `as_of`.
- Corrected normal, early-close, final-hour, extended-hours, and closed-session behavior.
- Added executable oversized-content and credential-reveal security cases.
- Prevented Stage 8 API tests from starting production background refresh workers, keeping the suite network-hermetic.

## Remaining conditions

1. Configure and license a production News provider before any result can be labeled live.
2. Configure eligible 5/15-minute OHLCV and intraday breadth sources before production intraday narratives or breadth timelines are enabled.
3. Complete the listed frontend presentation fields and interactive deep links.
4. Add centralized trace-system integration if operational traces—not only structured DTO metrics—are required.
5. Expand distinct failure-injection cases for breadth-unavailable and generic service timeout.
6. Complete native-device visual and rapid-navigation checks; automated TypeScript, lint, data-UI, focused consumer tests, and static export do not replace them.

## Reproduction commands

From `/Users/andypun/Downloads/market-intelligence-app`:

```bash
make validate-stage8 PYTHON=venv/bin/python
make test-stage8-news PYTHON=venv/bin/python
make test-stage8-session PYTHON=venv/bin/python
make test-stage8-routing PYTHON=venv/bin/python
make test-stage8-safety PYTHON=venv/bin/python
make test-stage8-performance PYTHON=venv/bin/python
```

Human report: `docs/validation/stage8-context-intelligence-validation-report.md`

Machine artifact: `artifacts/stage8-context-intelligence-validation.json`

## Release confirmations

- Report/PDF design was unchanged; only a retrieval seam was added.
- Stage 8 added no Portfolio, Scenario, Probability, or Decision Intelligence.
- Stage 8 added no automatic trading or order execution.
- Hermetic/mock data is explicitly test-labeled; unavailable production data remains unavailable and is never silently shown as live.
