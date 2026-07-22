# Stage 8.75 Theme Intelligence

## Architecture and repository audit

Before Stage 8.75, Theme Intelligence already had a sound but pilot-scoped path: versioned Markdown definitions and CSV members were imported through `app.themes`, durable equal-weight baskets were calculated by the theme engine, and immutable two-theme snapshots were published by `app.theme_snapshots`. The canonical snapshot was consumed by Sectors, Watchlist, Home context, Reports, and Copilot. Report research already enforced materiality, completeness, constituent-count, freshness, and figure gates.

The main duplicate path was the static industry-group/theme preference data used where a reviewed ThemeSnapshot was unavailable. Its provenance correctly marked it as a strategy preference, but it was not a launch taxonomy. The main gaps were the six-ID normalizer, two active reviewed definitions, no reverse symbol mapping API, no all-theme unavailable contract, and no single service exposing taxonomy, mappings, history, changes, evidence, and aliases.

Stage 8.75 wraps the validated pilot snapshot pipeline with one canonical `ThemeIntelligenceService`. It does not replace or regenerate existing Stage 7, 7.5, or 8 artifacts. Live pilot rows are merged into the launch registry; themes without governed history remain explicitly unavailable. Reports and Copilot receive only published available/partial rows, while the directory and Watchlist can retrieve all launch definitions.

## Taxonomy

Taxonomy version `2026.07.1` contains 26 active launch themes and one retired lineage record. IDs are stable snake-case machine identifiers because `memory_storage` and `cybersecurity` were already durable IDs. Hyphenated names and prior pilot IDs are migration aliases. Definitions include parent sectors, related industries, benchmark symbols, minimum constituent gates, inclusion rationale, exclusion notes, and lifecycle metadata.

The retired `cloud_data_centers_legacy` record documents the split between Data Centers and Cloud Computing. Retired themes cannot receive new mappings or analytics.

## Constituent mapping methodology

Mapping priority is:

1. Primary business exposure.
2. Reliable product or revenue exposure.
3. Industry classification.
4. Recognized benchmark or ETF membership.
5. Curated expert inclusion.
6. Keywords as supporting evidence only.

Every mapping records its theme, symbol, exposure tier, source, method, rationale, confidence, effective date, taxonomy version, review status, and benchmark context. Keyword matches never create core exposure. Overlap is intentional and exposed through the reverse symbol index. Diversified companies are significant or adjacent unless the theme is a primary business driver.

## Exposure definitions

- `core`: the theme is a primary business or product driver.
- `significant`: reliable material product or revenue exposure exists, but the company is not a pure play.
- `adjacent`: the company enables or benefits from the theme without primary exposure.
- `experimental`: the relationship is plausible and documented but has lower mapping confidence or a less mature business.

## Analytics

`ThemeAnalyticsEngine` is deterministic and accepts caller-supplied histories; it never fetches data and never invokes a model. It calculates equal-weight and median returns, relative strength versus SPY and every configured benchmark, breadth above 20/50/200-day averages, advance/decline, breadth excluding the largest contributor, multi-window momentum and agreement, acceleration, leadership state, persistence, contribution ranking, top-one/top-three concentration, HHI, effective constituent count, constituent leaders/laggards, and material change events.

Unavailable constituents are excluded rather than converted to zero. A theme cannot become `leading` without 1-month SPY-relative strength, 50-day breadth, positive medium momentum, sufficient coverage, and non-narrow concentration.

## Evidence, confidence, and availability

The engine reuses the Stage 7.5 freshness/availability, contradiction-preservation, and confidence-adjustment engines. Metric evidence is keyed by theme, metric, and market date. Missing benchmarks, missing windows, partial coverage, stale or mixed sources, test data, and contradictions remain visible and cap confidence. Hermetic data is labeled `HERMETIC TEST DATA — NOT LIVE`; it is never substituted for production data.

Quality gates cover minimum mapped constituents, minimum history coverage, benchmark availability, freshness, 20/50/200-day history sufficiency, concentration, evidence completeness, and mapping confidence. A canonical definition can be launch-ready while its current market snapshot remains unavailable.

## Repository and caching

`ThemeRegistry` precomputes ID, alias, theme-to-symbol, and symbol-to-theme indexes. `ThemeIntelligenceService` supplies taxonomy, definition, directory, ranking, detail, constituents, symbol mappings, history, changes, evidence, saved-theme resolution, search, and material Home changes. It merges immutable pilot snapshots and never recalculates themes per consumer. Provider or durable-storage absence degrades to stable partial/unavailable payloads.

Shared histories and benchmark series are passed once to the pure analytics engine. The validated legacy basket builder continues to batch durable histories for published pilot snapshots.

## API

- `GET /market/themes`
- `GET /market/themes/ranking`
- `GET /market/themes/taxonomy`
- `GET /market/themes/search/results?q=`
- `GET /market/themes/mappings/{symbol}`
- `GET /market/themes/{theme_id}`
- `GET /market/themes/{theme_id}/constituents`
- `GET /market/themes/{theme_id}/history`
- `GET /market/themes/{theme_id}/changes`
- `GET /market/themes/{theme_id}/evidence`

Existing snapshot, rotation, alerts, overlap, status, and refresh endpoints remain backward compatible. Responses include explicit status, taxonomy version, source state, missing data, confidence, deterministic ordering, and pagination where lists can grow. Errors never expose internal stack traces.

## Frontend integration

Sectors and Watchlist now retrieve the canonical directory rather than the two-theme endpoint. The Theme directory displays all launch definitions and keeps unavailable metrics as N/A; rotation excludes unavailable themes. Stock Detail retrieves primary and secondary canonical mappings. Existing theme bookmarking remains the saved-theme seam. Home retains its compact purpose and receives only material published changes. No navigation, layout system, report design, or PDF design was changed.

Search aliases are exposed by the canonical search API without duplicate results. The existing deep-link and watchlist IDs continue to use stable canonical IDs.

## Reports and Copilot

Reports and Copilot use `ThemeIntelligenceService.available_rows()`, so unavailable catalog entries do not become research candidates or claims. Existing report selection thresholds are unchanged: saved relevance cannot bypass freshness, completeness, constituent, classification, materiality, or supported-figure gates. The 26-theme directory therefore does not create 26 report topics. All 15 existing Copilot agents remain registered; no new top-level agent was added.

## Tests and fixtures

The Stage 8.75 hermetic catalog covers taxonomy lifecycle and migrations, duplicate aliases and IDs, mapping tiers and overlaps, provenance, broad and narrow leadership, concentration, conflicting windows, missing benchmarks/history, unavailable constituents, test labels, transitions, Stock Detail mapping, saved-theme resolution, search, stable unavailable API contracts, report flood prevention, and the 15-agent registry.

Fixtures use deterministic generated price arrays in process. The benchmark blocks socket creation across every measured region and performs zero model calls.

## Validation and performance

Run:

```sh
make validate-stage8-75 PYTHON=python3
```

The target does not skip failures. It runs focused Stage 8.75 tests, Stage 8 fixture checks and regression tests, the Stage 7 frozen corpus, runtime and reference evaluations, Stage 7.5 semantic equivalence, the full backend suite, frontend type check/lint/data validation, existing frontend regression scripts, web route export, the hermetic benchmark, and validation artifact generation.

Performance artifacts contain p50 and p95 for taxonomy, ranking, detail, symbol mapping, report candidates, Copilot retrieval, and Theme API endpoints. They describe local hermetic performance only and are not production latency claims.

## Known limitations and provider plan

- The launch taxonomy and mappings are ready, but only existing reviewed pilot themes can be live until governed provider histories are published.
- Current-basket history is used; historical membership reconstruction is not claimed.
- Market-cap weighting is supplementary only; deterministic analytics are equal-weight and median-first.
- Some benchmark ETFs may not be configured in the current provider and therefore reduce confidence rather than triggering substitution.
- Mapping confidence is curated metadata, not a revenue-estimation model.

Future provider work should batch all unique constituent and benchmark histories, validate security-master identity and corporate actions, publish immutable per-date inputs, and rebuild snapshots through the same service seam. No licensed provider should be enabled without an existing usable contract.

## Review and retirement policy

Review mappings at least quarterly and after material corporate actions, segment reporting changes, acquisitions, ticker changes, or benchmark reconstitutions. Changes require a new taxonomy version and effective date. Retain prior definitions and mappings for lineage. Retire a theme when it falls below its minimum meaningful constituent count, duplicates another theme, loses a defensible economic definition, or cannot maintain adequate evidence. A retired ID must resolve for historical records but cannot accept new mappings or rankings.

The generated validation report contains the complete per-theme table with parent sectors, constituent/core counts, coverage, benchmarks, and known limitations.
