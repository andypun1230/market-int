# Stage 8 News Intelligence

## Purpose and current production state

Stage 8 News Intelligence is a provider-neutral, deterministic event-intelligence pipeline. It accepts controlled news metadata, normalizes and classifies it, maps it to existing market entities, clusters repeated coverage and corrections, scores materiality, attaches supported daily market reactions, and returns one immutable typed result.

There is **no live News provider implementation or licensed production News feed configured**. `NewsProviderMode.LIVE` is reserved in the contract for a future implementation, but `get_default_news_provider()` and `get_news_intelligence_service()` deliberately use `UnavailableNewsProvider`. The production singleton also has no metadata repository. Existing quote or daily-history credentials are never interpreted as News entitlement. Its `query()` therefore returns a structured `unavailable` result. Injecting a repository does not change which provider `query()` invokes; cached reads require `query_cached()` or `query_cached_event()` explicitly.

The implementation manifest is `backend/app/intelligence/news/news_manifest.json`; the configured credibility registry is `backend/app/intelligence/news/source_registry.json`.

## Stable Python API

The supported import seam is:

```python
from app.intelligence.news import (
    MarketReactionObservation,
    NewsIntelligenceResult,
    NewsIntelligenceService,
    NewsQuery,
    NewsQueryMode,
    get_news_intelligence_service,
)
```

The service methods are:

```python
class NewsIntelligenceService:
    def query(
        self,
        query: NewsQuery,
        *,
        reaction_observations: tuple[MarketReactionObservation, ...] = (),
        watchlist_symbols: tuple[str, ...] = (),
    ) -> NewsIntelligenceResult: ...

    def query_cached(
        self,
        query: NewsQuery,
        *,
        watchlist_symbols: tuple[str, ...] = (),
    ) -> NewsIntelligenceResult: ...

    def query_cached_event(
        self,
        event_id: str,
        *,
        as_of: datetime,
    ) -> NewsIntelligenceResult: ...

    latest = query_cached
```

`query()` invokes only the provider configured on that service instance. Provider exceptions are caught and converted to a typed unavailable result with `news_provider_failure:<ExceptionType>`; no replacement data is fabricated.

`query_cached()` requires an injected `NewsMetadataReader`. It creates an explicit `CachedNewsProvider`, reads the repository, and never invokes the service's configured provider. `query_cached_event()` uses the same cache-only boundary but performs a direct event-ID lookup and reconstructs the requested event's stored cluster. With no repository or no matching cached metadata, either method returns a typed unavailable result. `latest` is an alias for `query_cached()`. Merely injecting a repository does not cause `query()` to read it; `query()` still invokes only its configured provider, although it may persist eligible provider results through an injected writer.

For deterministic tests or offline workflows, dependencies are injected explicitly:

```python
service = NewsIntelligenceService(
    provider=HermeticNewsProvider(items),
    repository=repository,
    mapper=mapper,
)
result = service.query(
    NewsQuery(
        mode=NewsQueryMode.SECURITY,
        as_of=as_of,
        symbols=("NVDA",),
    ),
    reaction_observations=observations,
    watchlist_symbols=("NVDA",),
)
```

### Query contract

`NewsQuery` contains:

| Field | Contract |
|---|---|
| `mode` | `market`, `index`, `sector`, `theme`, `security`, or `watchlist` |
| `as_of` | Required timezone-aware timestamp |
| `start_at`, `end_at` | Optional timezone-aware range; `end_at >= start_at` and `end_at <= as_of` |
| `entity_id` | Required for index, sector, and theme queries; security/watchlist require this or symbols |
| `symbols` | Uppercased, de-duplicated symbols, at most 20 characters each |
| `event_types` | Closed `NewsEventType` values |
| `source_qualities` | Closed `SourceQuality` values |
| `minimum_materiality` | Integer from 0 through 100 |
| `limit` | Integer from 1 through 100; default 20 |

The returned `NewsIntelligenceResult` contains the original query, service status, provider provenance, `as_of`, canonical events, their selected clusters, evidence, preserved contradictions, confidence and its rule contributions, limitations, errors, deep links, processing metrics, aggregate freshness, and `service_version=news-intelligence-v1`.

## Strict contracts and taxonomy

Every News DTO derives from `NewsContractModel`, which forbids extra fields, freezes instances, strips surrounding string whitespace, and validates controlled enums, identifier formats, safe URLs, ranges, and timezone-aware timestamps. Unavailable or failed results cannot contain events. Hermetic results must remain freshness state `test`.

The controlled event taxonomy is:

- macro and policy: `monetary_policy`, `inflation`, `employment`, `economic_growth`, `government_policy`, `regulation`, `geopolitics`;
- issuer events: `earnings`, `guidance`, `merger_acquisition`, `capital_raise`, `buyback`, `dividend`, `product_launch`, `supply_chain`, `customer_contract`, `legal`, `management_change`;
- market and research events: `analyst_action`, `credit_rating`, `cybersecurity_incident`, `exchange_notice`, `market_structure`, `positioning_commentary`;
- fallback: `other`.

Structured provider taxonomy wins when present. Otherwise `NewsTaxonomyEngine` applies versioned, deterministic English-language regular-expression rules and falls back to `other`. Expected direction is `positive`, `negative`, `neutral`, or `unknown`; structured direction wins, otherwise a small deterministic pattern set is used. This is classification, not generative interpretation.

Event state is separately controlled as `confirmed`, `developing`, `corrected`, `retracted`, `disputed`, or `unverified`. Correction lineage is `none`, `corrected`, `superseded`, or `retracted`, with provider/event references and an optional sanitized reason.

## Provider modes and provenance

All providers implement `NewsProvider.fetch_events(NewsProviderRequest)`, `health()`, and `capabilities()`. Convenience methods derive ticker, macro, official-release, and earnings requests without exposing provider-specific objects.

| Mode | Implementation | Behavior |
|---|---|---|
| `unavailable` | `UnavailableNewsProvider` | Production-safe default. Returns no items, `source_state=unavailable`, a fallback reason, and `news_provider_unavailable`. |
| `test` | `HermeticNewsProvider` | Explicit deterministic fixture mode with time, symbol, event-type, macro, official, earnings, limit, and cursor filtering. It can only report freshness `test`. |
| `cached` | `CachedNewsProvider` | Reads `StoredNewsEventMetadata` only. It returns `source_state=cached` when rows exist and `unavailable` when empty. It never falls through to fixtures or another provider. |
| `live` | None | The enum exists for future licensed integration; no live provider class or factory path is configured. |

`NewsProviderProvenance` records `provider`, `mode`, `source_state`, `as_of`, `fetched_at`, `cache_hit`, `fallback_reason`, `errors`, and `latency_ms`. Validation prevents hermetic data from being labelled non-test, unavailable mode from claiming an available state, live mode from claiming test data, and cached mode from claiming live or delayed state.

Cache replay preserves each event's original provider, original provider mode, and original fetch timestamp. Consequently, cached hermetic metadata remains test-labelled after replay. Cache replay deliberately reconstructs an empty summary and no confirmed facts; the cache is not a hidden article or evidence store.

## Source registry and quality rules

Source quality is assigned by the versioned source registry, never by a provider claim. Each record fixes its hostname, quality tier, allowed event types, primary-source categories, activity/test-only state, and storage policy.

The production registry currently recognizes five official primary-source identities:

- SEC EDGAR (`sec.gov`);
- Federal Reserve (`federalreserve.gov`);
- Bureau of Labor Statistics (`bls.gov`);
- Bureau of Economic Analysis (`bea.gov`);
- New York Stock Exchange (`nyse.com`).

The remaining four entries are explicitly test-only fixtures: company IR (`primary`), newswire (`high_confidence_secondary`), commentary (`supporting_secondary`), and unverified source (`unverified`). There is no configured production secondary-news source.

Credibility evaluation applies these rules:

1. Registry misses become `unavailable`, not an assumed quality tier.
2. Inactive sources are unavailable.
3. Test-only records are rejected outside hermetic mode.
4. An event type outside a source's allow-list becomes unverified.
5. A supplied source URL must be HTTPS, contain no credentials, and use the configured hostname or a subdomain. A mismatch is treated as source spoofing and quarantined.
6. `primary_source=True` requires an allowed active `primary` source and an event type listed in that source's primary categories.
7. Unverified or unavailable sources cannot produce a confirmed event; confirmed facts are removed and the event becomes unverified.
8. Persistence additionally requires an active registry record with `metadata_storage_allowed=true`.

All registry entries set `article_body_storage_allowed=false`, and the Pydantic registry contract rejects a record that tries to enable it.

## Normalization and security quarantine

Normalization is deterministic and fail-closed:

- `published_at` is required; missing timestamps are rejected.
- Publication and update timestamps more than five minutes ahead of `now` are rejected.
- `first_seen_at` cannot precede publication.
- Event IDs are stable hashes of effective provider, provider event ID, source identifier, and publication timestamp.
- Market date and session phase are derived in `America/New_York`.
- One evidence record is created per retained confirmed fact; when no fact is retained, the event receives source-metadata evidence instead.

Before taxonomy, evidence, mapping, or persistence, the security engine sanitizes the headline, summary, source name, subtype, correction reason, and every fact. It converts HTML to plain text, removes script/style/iframe/object/embed content, strips Markdown images, link destinations, and control markup, removes control characters, normalizes whitespace, and enforces bounded output.

The event is quarantined when input contains a prompt-injection pattern, a secret, executable markup, a dangerous URL scheme, oversized untrusted text, malformed markup, or a spoofed source URL. Quarantine behavior is explicit:

- unsafe text is not exposed as evidence;
- the headline becomes a neutral quarantine placeholder;
- event status becomes `unverified`;
- confirmed facts are cleared;
- reasons are retained in `quarantine_reasons` and normalization issues;
- entity mapping is skipped; and
- the service does not persist the event.

## Deduplication, clustering, and corrections

The clustering pipeline first reuses the Stage 7.5 stable evidence-deduplication engine on `event_id`. Conflicting payloads for the same ID are reported as errors.

Events are joined when they share an explicit canonical provider reference, when correction/supersession lineage links their provider IDs, or when all deterministic heuristic gates pass:

- same event type;
- publication within 48 hours;
- no conflict between two non-empty symbol sets; and
- headline-token Jaccard similarity of at least 0.55 when either event has symbols, otherwise 0.65.

Canonical selection ranks non-quarantined records first, then configured source quality, event status, publication time, and stable ID. Each cluster preserves all source members and exposes its earliest event, primary-source event when present, update IDs, correction IDs, contradiction IDs, unique source count, and duplicate count.

Repeated or syndicated coverage is represented by cluster membership and `duplicate_count`; it is not counted as independent confirmation and receives a materiality penalty. Corrected, superseded, retracted, and disputed records remain linked rather than being overwritten. Retractions/disputes and reaction classifications that reject the expected direction are passed to contradiction preservation.

After clustering, the canonical event receives the de-duplicated union of validated entity mappings from its cluster members.

## Entity mapping

The mapping engine validates candidates against existing project registries. Its default adapters read the Security Master and active Theme definitions; tests may inject resolvers.

Candidate symbols may come from structured provider metadata, explicit `$SYMBOL` text, parenthetical uppercase symbols, or an injected company-name resolver. Candidates must resolve to an active Security Master record. Ambiguous parenthetical common words such as `AI`, `IT`, or `ALL` fail closed.

For a validated security, the engine can emit versioned, evidence-backed mappings for:

- directly named security or ETF;
- company parent;
- configured sector and industry membership;
- configured index/benchmark membership;
- active reviewed theme membership; and
- explicit watchlist overlap supplied by the caller.

Every mapping carries a relationship, source, confidence, evidence ID, source freshness, and mapping version. The current engine does not infer suppliers, customers, holdings, peers, or other business relationships. Watchlist overlap changes only `user_relevance`; it does not increase market or entity materiality.

## Transparent materiality

Materiality is a ranking score, **not a return forecast**. Every scalar input is bounded to `[0, 1]`. Define:

- `C`: source credibility after the quality cap (`primary=1.0`, `high_confidence_secondary=0.8`, `supporting_secondary=0.5`, `unverified=0.1`, `unavailable=0.0`);
- `D`: directness; `S`: structured surprise; `M`: mapped market scope; `E`: entity significance;
- `P`: observed price-reaction strength; `V`: volume strength; `B`: breadth strength; `X`: cross-asset strength;
- `R`: duration; `F`: freshness; `W`: explicit watchlist relevance;
- `N`: duplicate count; and `U`: uncertainty.

With `score(x) = max(0, min(100, round(x)))`, the formulas are:

```text
market_materiality = score(
    15C + 18D + 12S + 12M + 10E
  + 14P + 10V + 8B + 8X + 5R + 5F
  - min(10, 2N) - 20U
)

entity_materiality = score(
    10C + 25D + 15S + 15E + 20P + 10V + 5R - 20U
)

user_relevance = score(100W)
```

The result includes each non-zero market contribution with component name, points, and reason, plus `methodology_version=news-materiality-v1`.

The service currently derives market scope as `0.9` for configured macro event types, otherwise `0.75` for index mappings, `0.55` for sector mappings, `0.4` for theme mappings, `0.25` for a direct entity, and `0` otherwise. Direct entity significance is currently `0.5`. Freshness maps from `1.0` live through `0.0` stale/unavailable. Uncertainty is `0` confirmed, `0.15` corrected, `0.4` developing, and `1.0` disputed/unverified/retracted. Surprise and duration remain zero unless a future caller or pipeline stage supplies them.

## Daily market-reaction contract

The reaction engine supports only:

- `close_to_close`;
- `next_session`; and
- `multi_day`.

Although intraday window values exist in the shared contract for forward compatibility, `5_minutes`, `15_minutes`, `30_minutes`, `60_minutes`, and `session_to_date` observations are excluded with `intraday_reaction_unavailable_daily_only`.

Classification uses benchmark-relative price return, `price_return - benchmark_return`, when a traceable benchmark observation exists. Otherwise it uses the explicitly labelled absolute price return and discloses that benchmark-relative reaction is unavailable. The default material threshold is 0.5%. The controlled classifications are:

- `confirms_positive` and `confirms_negative`;
- `rejects_positive` and `rejects_negative`;
- `mixed`;
- `no_material_reaction`; and
- `insufficient_data`.

No supported observation with a price return yields insufficient data. Returns below the threshold yield no material reaction. Opposite material signs across windows yield mixed. Otherwise, the material sign is compared with the expected direction; neutral or unknown direction yields mixed.

Volume ratio, breadth change, and cross-asset confirmation create transparent strength inputs when supplied, but price direction drives the classification. The current reaction engine emits window-level price-reaction evidence; the volume, breadth, and cross-asset evidence enum values are reserved for inputs that have their own validated evidence records. Missing price, benchmark, volume, expected direction, or source lineage is disclosed in `limitations`. A missing benchmark is never substituted with zero. A price observation without evidence IDs, source ID, and source quality cannot drive a reaction classification or evidence record.

Reaction observations must have timezone-aware ordered windows and controlled evidence IDs. Evidence is attached to the event by normalized event ID or provider event ID. The engine's summaries intentionally use noncausal language such as “was followed by,” “was consistent with,” “was not confirmed by,” or “was contradicted by.” Temporal association and price consistency do not establish that the event caused the move.

## Stage 7.5 engine reuse and evidence boundaries

The service reuses the frozen Stage 7.5 engines rather than redefining their behavior:

| Capability | Version | News use |
|---|---|---|
| Freshness and availability | `freshness-availability-v1` | Event and aggregate state, source/cache age, test/stale/partial/unavailable propagation |
| Evidence validation | `evidence-validation-v1` | Stable de-duplication, collision reporting, mapping de-duplication, and source-timestamp lineage validation |
| Contradiction preservation | `contradiction-preservation-v1` | Preserves explicit retractions, disputes, and reaction rejections with evidence IDs |
| Confidence adjustment | `confidence-adjustment-v1` | Adjusts confidence for evidence, freshness, missing data, test/stale/partial/unavailable state, contradictions, unsupported dimensions, and fallback use |

Evidence kinds are controlled: confirmed fact, source metadata, entity mapping, price reaction, volume reaction, breadth reaction, cross-asset reaction, and missing evidence. Interpretation is separately labelled as observed fact, engine conclusion, missing evidence, or contradiction.

Confirmed facts require evidence IDs, and each retained fact gets its own evidence record. Mapping and reaction conclusions carry their own evidence IDs. Result-level evidence and contradictions are filtered to the selected clusters so unrelated provider rows cannot leak into a scoped response. The evidence engine validates identity and source/timestamp lineage; it does not independently prove that a provider statement is true. Source quality, clustering, price reaction, and temporal proximity are therefore never presented as causal proof.

## Metadata-only persistence

`NewsMetadataRepository` (SQLite) and `InMemoryNewsMetadataRepository` implement a whitelist-only persistence contract, `news-metadata-v1`. The stored shape contains:

- event/cluster IDs and canonical headline;
- taxonomy and expected direction;
- source identity, accepted URL, configured quality, and primary flag;
- publication/update/first-seen timestamps, language, market date, and session phase;
- directly named symbols;
- event status and correction lineage;
- provider metadata; and
- quarantine metadata and schema version.

The service saves only non-quarantined events whose active source-registry record allows metadata storage. The repository recursively rejects keys including article/body/content/full-text/HTML/raw-content/summary/source-summary/text/transcript variants.

It does **not** store article bodies, provider article content, summaries, confirmed facts, evidence statements, expanded entity mappings, materiality, or market reactions. The canonical headline is retained as bounded event metadata. The stable identity tuple—event ID, headline, event type, source, publication timestamp, provider, and provider event ID—cannot change for an existing event ID; other whitelisted metadata can be revisioned.

## Observability

Consumers should read state from the contracts rather than infer it from row presence.

Result observability includes:

- `status`: `complete`, `partial`, `stale`, `unavailable`, or `failed`;
- provider provenance fields listed above;
- freshness: state, availability, market date, generated/observed/expiry times, age, completeness, provider, fallback/mixed-source flags, confidence-cap recommendation, warnings, and engine version;
- confidence label and rule contributions;
- explicit `limitations` and de-duplicated `errors`;
- per-event provider metadata, evidence IDs, source quality, correction lineage, freshness, quarantine state, materiality methodology, and reaction methodology;
- cluster membership, source members, duplicate/source counts, and cluster version; and
- deep links for mapped stock, sector, and theme destinations.

`NewsProcessingMetrics` exposes:

```text
provider_fetch_ms
normalization_ms
clustering_ms
mapping_ms
materiality_ms
reaction_ms
materiality_reaction_ms
total_ms
provider_event_count
normalized_event_count
cluster_count
returned_event_count
duplicate_reduction_ratio
cache_hit
```

These IDs and component timings are contract-level observability and benchmark inputs. Stage 8 does not implement a centralized trace/span recorder or an exported production-trace integration.

## Consumer, Copilot, and report seam

FastAPI exposes the same `NewsIntelligenceResult` contract at:

```text
GET /intelligence/news/market
GET /intelligence/news/index/{index_id}
GET /intelligence/news/security/{symbol}
GET /intelligence/news/sector/{sector_id}
GET /intelligence/news/theme/{theme_id}
GET /intelligence/news/watchlist?symbols=NVDA,MSFT
GET /intelligence/news/events/{event_id}
```

The market, index, security, sector, theme, and watchlist collection routes call the production singleton's configured provider through `query()`. Because that provider is explicitly unavailable, their current default is a successful HTTP response containing typed `unavailable` state, no events, limited confidence, and an explicit limitation. The event-detail route is different: it calls `query_cached_event()` for a direct cached event/cluster lookup and also returns typed unavailable state when the production singleton has no repository or the event is absent. Filters use the same closed enums and bounded materiality/limit fields as `NewsQuery`. Watchlist symbols are batched and de-duplicated.

Copilot uses `TrustedCopilotSources.news_intelligence()` and the existing 15-agent registry. For explicit News collection intents it builds a scoped `NewsQuery` and calls `query_cached()`; event-detail intent calls `query_cached_event()`. Neither path invokes a News provider. Typed unavailable News becomes an unavailable agent result rather than invented evidence. Available results are adapted into scalar News evidence while preserving event IDs, cluster IDs, mapping IDs, reaction windows, source mode, freshness, limitations, contradictions, confidence, and the underlying evidence source IDs. News routing reuses Market, Index, Leadership, Sector, Theme, Macro, Risk, Stock, Watchlist, and Research; the Report Agent additionally has a validated typed retrieval seam for News and Session evidence. No News-specific Copilot agent was added.

There is currently **no direct News import or rendering path in the Report/PDF builders** and no new PDF section. The Report Agent retrieval seam operates through the common typed agent registry; it does not mutate `ReportDocument` or the PDF renderer. A future report consumer should retrieve typed results through the service/cache boundary, render only validated contract fields, preserve provenance/freshness/limitations, and never fetch provider payloads, re-cluster, re-score, infer causality, or render article bodies.

## Known limitations

1. No live or licensed production News provider is implemented; official registry entries configure trust rules but do not acquire data.
2. The production singleton has neither a live provider nor a metadata repository, so direct API queries and Copilot cache reads honestly default to unavailable.
3. Reaction analysis is daily-only. The service does not fetch reaction data; callers must supply explicit `MarketReactionObservation` records. Intraday reactions and intraday causal narratives are unsupported.
4. Session phase uses New York weekday clock boundaries only. It has no exchange-holiday or shortened-session calendar.
5. The deterministic text taxonomy is a bounded English pattern set. Unknown or novel event language falls back to `other`/`unknown`.
6. Entity coverage is limited to existing active Security Master and Theme registry records. The default engine has no company-name resolver and does not infer business relationships.
7. Heuristic clustering is lexical and time-bounded; explicit canonical references and correction lineage are stronger than token similarity, but incomplete provider metadata can still miss a relationship.
8. The metadata cache is intentionally lossy: it omits summaries, facts, evidence, expanded mappings, materiality, and reaction analysis. Replay reconstructs intelligence from metadata and can therefore be less complete than the original result.
9. Materiality is deterministic ranking, not predicted impact. Surprise and duration are currently unpopulated by the service, and reaction-dependent components remain zero without caller-supplied daily observations.
10. Evidence validation checks structured identity and lineage, not the external truth of a source statement. No output should be described as causal proof.
11. There is no current Report/PDF rendering integration; only the typed Report Agent retrieval seam is supported.

## Focused validation

Run the News-specific Stage 8 tests from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend backend/venv/bin/python -m unittest discover -s backend/tests/stage8 -p 'test_news_*.py' -q
```

The exact focused and full counts are recorded by `artifacts/stage8-context-intelligence-validation.json`; use the command above rather than relying on a stale documentation count.
