# Stage 8.75 Theme Intelligence

## Architecture and repository audit

Before Stage 8.75, Theme Intelligence already had a sound but pilot-scoped path: versioned Markdown definitions and CSV members were imported through `app.themes`, durable equal-weight baskets were calculated by the theme engine, and immutable two-theme snapshots were published by `app.theme_snapshots`. The canonical snapshot was consumed by Sectors, Watchlist, Home context, Reports, and Copilot. Report research already enforced materiality, completeness, constituent-count, freshness, and figure gates.

The main duplicate path was the static industry-group/theme preference data used where a reviewed ThemeSnapshot was unavailable. Its provenance correctly marked it as a strategy preference, but it was not a launch taxonomy. The decisive snapshot-coverage defect was narrower: `ThemeSnapshotBuilder` enumerated `ThemeDefinitionService.active()`, which returned only the two durable pilot definitions. The other 24 canonical launch definitions therefore never reached symbol resolution, history planning, or materialization.

Stage 8.75 keeps one canonical `ThemeIntelligenceService` and now materializes the launch registry through the existing immutable `ThemeSnapshot`. The builder resolves all mappings against the security master, reads every unique constituent and benchmark in one durable batch, applies the deterministic analytics and Stage 7.5 governance engines, then persists available and partial rows under both the compatibility namespace and a taxonomy-versioned namespace. The two original reviewed rows retain their validated calculation path and are merged by canonical ID.

## Taxonomy

Taxonomy version `2026.07.1` contains 26 active launch themes and one retired theme-lineage record. IDs are stable snake-case machine identifiers because `memory_storage` and `cybersecurity` were already durable IDs. Hyphenated names and prior pilot IDs are migration aliases. Definitions include parent sectors, related industries, benchmark symbols, minimum constituent gates, inclusion rationale, exclusion notes, and lifecycle metadata.

The retired `cloud_data_centers_legacy` record documents the split between Data Centers and Cloud Computing. Retired themes cannot receive new mappings or analytics.

The final security-master coverage pass did not change that taxonomy or the 227-row active mapping count. It corrected three provider-blocking legacy symbols without changing theme or exposure: `SQ` to `XYZ`, `FI` to `FISV`, and merger predecessor `PARA` to `PSKY`. The three prior mapping rows remain as date-bounded lineage records, while security aliases and provider-symbol segments preserve the exact adjusted-history transitions.

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

Quality gates cover minimum mapped constituents, minimum history coverage, benchmark availability, freshness, 20/50/200-day history sufficiency, concentration, evidence completeness, and mapping confidence. `available` requires at least 75% 21-session mapped coverage, the registry minimum, SPY and every parent-sector reference, current freshness, and moderate confidence. `partial` requires at least two computable registered histories but fails one or more normal gates; it is persisted but unranked. `unavailable` is below that computation floor or lacks SPY, and missing values remain N/A rather than zero.

## Repository and caching

`ThemeRegistry` precomputes ID, alias, theme-to-symbol, and symbol-to-theme indexes. `ThemeIntelligenceService` supplies taxonomy, definition, directory, ranking, detail, constituents, symbol mappings, history, changes, evidence, saved-theme resolution, search, and material Home changes. It merges immutable pilot snapshots and never recalculates themes per consumer. Provider or durable-storage absence degrades to stable partial/unavailable payloads.

The production build requests 225 unique constituent/reference symbols with one batched daily-history query and resolves mapped equities with one security-master query. It performs zero provider calls on the snapshot build/warm-read path. The published `2026.07.1` snapshot contains repository-call statistics, 35 reused overlapping constituent mappings, 48 reused benchmark references, and the complete 26-theme coverage audit. Published warm reads use the existing taxonomy-versioned snapshot namespace; the canonical build reads the durable repositories directly, so its cache hit/miss counters are truthfully zero rather than inferred.

## Final Theme Rotation analytical patch

The 26-theme integration was complete, but its legacy `relative-return-momentum-v1` axes were fixed-window theme-minus-SPY return and the lagged change of that return, shifted by 100. Five sparse overlapping-window coordinates had no continuous relative-price trend, smoothing, relative-volatility scaling, or robust normalization. The pre-change formulas and consumers are frozen in `docs/stage8.75-theme-rotation-mathematics-audit.md`.

Theme Rotation now uses `theme-relative-trend-momentum-v1`. Governed adjusted constituent returns chain a daily-rebalanced equal-weight theme index. Exact shared dates create `theme_index / SPY_adjusted_close`; missing sessions are neither forward-filled nor bridged. Relative Trend is the fast-minus-slow EMA spread of log relative price, scaled by causal EWMA relative volatility and a trailing zero-centered robust magnitude. Relative Momentum is a smoothed lagged change of Relative Trend, normalized with the same causal robust policy. Every winsorized value is flagged. Full formulas, parameters, confidence, limitations, migration, and intellectual-property disclaimer are in `docs/stage8.75-theme-rotation-model-specification.md`.

A point still requires row-level available status, finite profile coordinates, usable governed confidence, active non-test provenance, and evidence references. The existing 75% availability floor is unchanged; global partial status never hides an individually available row; N/A is never zero. Theme ranking and all stock/sector/report/Copilot scoring remain independent of these visualization coordinates.

The normalized midpoint remains 100. Leading is Trend ≥ 100 and Momentum ≥ 100; Improving is Trend < 100 and Momentum ≥ 100; Weakening is Trend ≥ 100 and Momentum < 100; Lagging is Trend < 100 and Momentum < 100. Exact boundaries treat 100 as non-negative. The backend supplies genuine chronological tails from one continuity segment: 8 daily Short points, 10 daily Medium points spaced three sessions, or 8 last-complete-session weekly Long points. The frontend uses all profile/snapshot tail coordinates for one padded domain, so quadrant and label filters cannot move or remove an unchanged point and no valid coordinate is clipped.

The analytical snapshot is `theme-2026-07-22-ba4e56088a`; the security-master baseline was `theme-2026-07-22-f892477741` and the preceding 26-theme integration snapshot was `theme-2026-07-22-213feef062`. All use taxonomy `2026.07.1`.

| Profile | Input / trend EMA | Tail | Eligible | Excluded | Leading | Improving | Weakening | Lagging | Common date |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| Short | daily 10 / 30 | 8 | 26 | 0 | 2 | 5 | 6 | 13 | 2026-07-21 |
| Medium | daily 20 / 50 | 10 | 26 | 0 | 5 | 5 | 8 | 8 | 2026-07-21 |
| Long | weekly 10 / 26 | 8 | 26 | 0 | 4 | 6 | 10 | 6 | 2026-07-17 |

On the default 300px card, Smart renders six prioritized labels, All renders 26, and None renders zero. All modes retain 26 points before a quadrant filter. Smart combines canonical rank, quadrant/material movement, and existing selected/watchlist priorities. All and Smart use deterministic fallback placement after normal collision avoidance, so the footer is the rendered-label count rather than an attempted-label estimate.

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
- `GET /market/themes/rotation?profile=medium` (`timeframe=1M` and `interval` remain backward-compatible aliases)

Existing snapshot, rotation, alerts, overlap, status, and refresh endpoints remain backward compatible. Responses include explicit status, taxonomy version, source state, missing data, confidence, deterministic ordering, and pagination where lists can grow. Errors never expose internal stack traces.

## Frontend integration

Sectors and Watchlist retrieve the canonical directory. The Theme directory displays all launch definitions and keeps unavailable metrics as N/A. Theme Rotation retrieves the selected canonical profile through one model-versioned typed hook; it never calculates indicators or tails. The chart labels x as Relative Trend, y as Relative Momentum, explains the profile semantics, retains every eligible point under Smart labels, and uses a filter-stable unclipped domain. Stock Detail retrieves primary and secondary canonical mappings. Existing theme bookmarking remains the saved-theme seam. Home retains its compact purpose and receives only material published changes. No navigation, layout system, report design, or PDF design was changed.

Search aliases are exposed by the canonical search API without duplicate results. The existing deep-link and watchlist IDs continue to use stable canonical IDs.

## Reports and Copilot

Reports and Copilot use `ThemeIntelligenceService.available_rows()`, which now returns only fully available ranked rows. Partial and unavailable catalog entries do not become research candidates or strong claims. Existing report selection thresholds are unchanged: saved relevance cannot bypass freshness, completeness, constituent, classification, materiality, or supported-figure gates. The 26-theme directory therefore does not create 26 report topics. All 15 existing Copilot agents remain registered; no new top-level agent was added.

## Tests and fixtures

The focused Stage 8.75 suite covers taxonomy/governance and 26-theme integration plus equal-weight indexing, missing-return exclusion, continuous benchmark-relative price, smoothing, volatility scaling, robust normalization, winsor metadata, no look-ahead, eight synthetic mechanics, continuity breaks, genuine tails, profile differences, direction/speed, deterministic versioning, API compatibility, cache identity, label modes, filters, footer counts, and N/A safety.

Fixtures use deterministic generated price arrays in process. The benchmark blocks socket creation across every measured region and performs zero model calls.

## Validation and performance

Run:

```sh
make validate-stage8-75 PYTHON=python3
```

The target does not skip failures. It runs focused Stage 8.75 tests, Stage 8 fixture checks and regression tests, the Stage 7 frozen corpus, runtime and reference evaluations, Stage 7.5 semantic equivalence, the full backend suite, frontend type check/lint/data validation, existing frontend regression scripts, web route export, the hermetic benchmark, and validation artifact generation.

Performance artifacts contain p50 and p95 for security-master/history batches, theme-index construction, benchmark-relative calculation, Relative Trend/Momentum kernels, complete 26-theme profile serialization, warm profile/API retrieval, frontend transformation, quadrant filtering, and Smart-label selection. They describe local hermetic performance only and are not production latency claims.

## Final security-master coverage pass

The machine audit fixes the scope to the exact 138 symbols absent from the canonical master at the validated baseline. Every row has one governed category, provider reference identity where available, current/historical status, exchange, asset type, adjusted-history dates and counts, mapped themes and exposure, recommended action, evidence endpoints, and a manual-review flag. The classification result is 129 valid current missing registrations, two verified ticker renames, one verified merger successor, two delisted symbols, and four OTC ADR/special-instrument decisions.

The pass registered 132 canonical US-exchange listings. Canonical IDs are derived from Polygon composite FIGI, or a share-class-safe fallback when a FIGI is absent. Exchange-listed ADRs are recorded as `adr`; current common shares are `equity`. OTC ADRs are not registered. Provider identity is kept separate from sector research: Polygon SIC text is retained as industry provenance, while an absent governed sector is recorded as `Unknown` instead of being inferred.

The existing strict-live router/updater refreshed 164 deduplicated canonical and benchmark symbols. It inserted 69,362 adjusted daily bars, updated 121 overlap bars, recorded no failures, no test/mock rows, and no rate-limit events. The provider refresh reached `2026-07-22`; the latest common date across all 26 theme calculations is `2026-07-21`. All 186 registered mapped symbols are 21-, 50-, and 200-session capable, with duplicate-session count zero.

The security-master coverage snapshot `theme-2026-07-22-f892477741` contained all 26 rows and all 26 were available and ranked. The mathematical migration published `theme-2026-07-22-ba4e56088a`, also with 26 available/ranked rows and complete Short/Medium/Long tails. Twenty-one baseline-constrained themes were promoted directly to available: 12 from partial and 9 from unavailable. Six affected themes remain honestly below the 90% complete-coverage disclosure threshold but above the unchanged 75% availability threshold; they stay available/ranked with their exact missing symbols disclosed.

## Manual Theme Rotation acceptance checklist

Native-device visual verification remains manual. Use the final validated snapshot and complete these checks:

1. Open Theme Rotation.
2. Select 1M.
3. Select All quadrants.
4. Select Smart labels.
5. Confirm 26 points appear, not two.
6. Confirm the footer reads 26 points and six labels.
7. Select All labels.
8. Confirm the footer reads 26 points and 26 labels.
9. Select None.
10. Confirm the footer reads 26 points and zero labels.
11. Filter Leading, Improving, Weakening, and Lagging and compare counts with the table above.
12. Return to All and confirm all 26 points return.
13. Switch among 1W, 1M, and 3M and confirm coordinates and quadrant counts change without stale points.
14. Inspect Cybersecurity.
15. Inspect Obesity & Metabolic Health, Digital Payments, Data Centers, and Nuclear Energy.
16. Confirm partial-coverage themes remain present when available.
17. Confirm no N/A point appears at zero.
18. Confirm no duplicate theme appears.
19. Reload and confirm the legacy two-theme result does not return.
20. Restart the app and refresh its cache; confirm the 26-point result persists.

## Remaining limitations and provider plan

- Six active mapping symbols remain outside the master: `ABB`, `ADYEY`, `DESP`, `FANUY`, `JNPR`, and `NTDOY`.
- `ADYEY`, `FANUY`, and `NTDOY` are current OTC ADRs with provider history but require an explicit instrument-policy decision. `ABB` has no supported current identity under that symbol; `ABBNY` is an unapproved OTC ADR candidate and is not substituted. `DESP` and `JNPR` are historical/delisted in current provider reference data and are not registered as active.
- Current-basket history is used; historical membership reconstruction is not claimed.
- Market-cap weighting is supplementary only; deterministic analytics are equal-weight and median-first.
- Optional thematic benchmark ETFs may be absent; required SPY and parent-sector references are complete and optional gaps remain disclosed without substitution.
- Mapping confidence is curated metadata, not a revenue-estimation model.

Future coverage expansion must validate security-master identity, exchange, asset type, provider symbol, and corporate-action lineage before fetching new histories. Use `scripts/complete_stage8_75_theme_coverage.py` only for an approved live maintenance run, then rebuild through `scripts/build_theme_snapshot.py` and run the hermetic release gate. No consumer-specific snapshot path is required.

## Review and retirement policy

Review mappings at least quarterly and after material corporate actions, segment reporting changes, acquisitions, ticker changes, or benchmark reconstitutions. Methodology, exposure, or membership changes require a new taxonomy version and effective date. A provider-symbol-only corporate-action correction may retain the thematic taxonomy version only when theme, exposure, rationale, provenance and review semantics are preserved and explicit retired mapping plus security-alias lineage is added. Retire a theme when it falls below its minimum meaningful constituent count, duplicates another theme, loses a defensible economic definition, or cannot maintain adequate evidence. A retired ID must resolve for historical records but cannot accept new mappings or rankings.

The generated validation report contains the complete per-theme table with parent sectors, constituent/core counts, coverage, benchmarks, and known limitations.
