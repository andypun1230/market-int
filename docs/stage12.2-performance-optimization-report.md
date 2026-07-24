# Stage 12.2 Performance Optimization Report

**Date:** 2026-07-24  
**Baseline commit:** `e2de1f415260593541e641ee2c4cb3f2382a7634`  
**Branch:** `main`  
**Classification:** **PASS WITH CONDITIONS**

## Outcome

All measured desktop-web hard budgets pass at p50 and conservative three-run p95. Theme Rotation decision-ready latency fell from 10.48 s to 0.35 s p50, the Theme summary contract fell from 6.55 MB raw to 86.7 KB, and Home initial JavaScript fell from 909 KB gzip to 588 KB gzip. Product behavior, routes, financial models, intelligence ownership, scoring, report selection, and visual design were not changed.

The result is conditional because native iOS/Android profiling is still outstanding and historical visual artifacts cannot be refreshed under the explicit instruction to leave historical artifacts unchanged. Their source/snapshot freshness gates therefore report stale evidence after authorized Stage 12.2 changes.

## Implemented boundaries

- `/market/themes` now emits `theme_summary_v1`, a backend field projection of canonical Theme Intelligence. It excludes detail-only member, evidence, provenance, and rotation-series data.
- `/market/themes/{theme_id}` remains the canonical detail destination and exposes the full authoritative row on demand.
- `/market/themes/rotation/summary` emits `theme_rotation_summary_v1`, preserving snapshot/taxonomy/model identity, coordinates, trails, confidence, freshness, availability, rank, and labels without duplicated series/tails.
- The legacy `/market/themes/rotation` route and full contract remain intact.
- Theme Rotation begins independently of the Theme Directory payload. Noncritical taxonomy, registry, status, and sector requests are deferred.
- Identical client requests share an in-flight promise. Immutable rotation/detail responses use snapshot-, taxonomy-, model-, profile-, and timeframe-aware cache keys with a bounded 128-entry LRU.
- Theme Detail is requested only after the user opens detail. A failed detail request retains the truthful published summary.
- Durable store schema migration/canonicalization runs once per storage instance instead of once per read. Publication continues to update the same service-local immutable snapshot cache.
- Expo Router production-web async routes split route-specific code while preserving native behavior and existing routes.
- User Timing marks now distinguish first analytical content, decision-ready, and route complete.

## Before and after

| Metric | Stage 12.1 | Stage 12.2 | Change |
|---|---:|---:|---:|
| Theme summary raw | 6,553,498 B | 86,710 B | -98.68% |
| Theme summary gzip | 639,751 B | 8,360 B | -98.69% |
| Theme rotation raw | 497,499 B | 114,347 B | -77.02% |
| Theme rotation gzip | 47,571 B | 15,332 B | -67.77% |
| Home initial JS gzip | 908,888 B | 587,699 B | -35.34% |
| Home unused JavaScript | 60.49% | 41.52% | -18.97 pp |
| Effective repository reuse | 58.0% | 66.7% | +8.7 pp |

## Request count and sequencing

| Path | Stage 12.1 | Stage 12.2 | Disposition |
|---|---:|---:|---|
| Theme Rotation decision-critical analytical requests | 2 sequential (directory, then rotation) | 1 compact rotation | sequential gate removed |
| Theme Rotation fully loaded requests | 7 | 7 | count unchanged; six noncritical reads no longer gate the map |
| Stock Detail stock-analysis reads | 3 | 1 | duplicate refresh reads removed in measured final runs |
| Theme detail records shipped before selection | 26 embedded records | 0 | one detail request only after selection |
| Per-theme Rotation requests | 0 | 0 | N+1 guard preserved |

The primary gain is dependency removal and payload projection, not indiscriminate request-count reduction. Home, Market, and Sectors retain their authoritative domains; independent requests overlap and secondary domains do not gate the instrumented decision layer.

## Decision-ready latency

Three independent production-export desktop runs used an unthrottled local network/CPU. p95 is the maximum of three runs, a conservative small-sample estimate.

| Route | Baseline | p50 | p95 | Hard budget | Result |
|---|---:|---:|---:|---:|---|
| Home | 4,020 ms | 498 ms | 563 ms | 2,000 ms | PASS |
| Market | 3,972 ms | 460 ms | 483 ms | 2,000 ms | PASS |
| Sectors | 7,113 ms | 2,225 ms | 2,232 ms | 2,500 ms | PASS |
| Theme Rotation | 10,480 ms | 354 ms | 356 ms | 3,000 ms | PASS |
| Stock Detail | 3,697 ms | 394 ms | 824 ms | 2,000 ms | PASS |
| Reports shell | 327 ms | 339 ms | 348 ms | informational | PASS |
| Copilot shell | 428 ms | 237 ms | 414 ms | informational | PASS |

Reports added 12 ms at p50 but remain far below one second. Copilot improved. Deferred route chunks did not create a material route-open regression.

## Rendering and memory

- Desktop Lighthouse total blocking time was 0 ms on measured routes.
- No new dropped-frame event was confirmed; chart systems were not rewritten.
- Simulated mobile TBT ranged from 193 to 238 ms. Mobile LCP remains network/viewport sensitive and is documented separately from decision-ready web budgets.
- After 28 repeated major-route navigations, the identified renderer changed from 84,464 KB to 84,544 KB RSS (+80 KB), with stable final DOM cardinality. No retained-memory leak was confirmed.
- Native heap snapshots and native frame pacing remain required.

## Compatibility disposition

- Existing route paths were not removed or redirected.
- The oversized list response intentionally stops duplicating `rows`, coverage audit, repository stats, and detail-only fields. All repository consumers were migrated to `items`; full detail remains available at the canonical detail/evidence routes.
- The existing full Theme Rotation endpoint is unchanged for legacy validators and consumers.
- No frontend calculation reconstructs omitted intelligence; frontend adapters only normalize names and types.

## Exact file disposition

Modified application files:

- `backend/app/api/market.py`
- `backend/app/sector_snapshots/storage.py`
- `backend/app/theme_snapshots/readers.py`
- `backend/app/theme_snapshots/storage.py`
- `backend/app/themes/intelligence.py`
- `backend/app/themes/storage.py`
- `frontend/app.json`
- `frontend/package.json`
- `frontend/src/app/(tabs)/index.tsx`
- `frontend/src/app/(tabs)/market.tsx`
- `frontend/src/app/(tabs)/sectors.tsx`
- `frontend/src/components/watchlist/StockCard.tsx`
- `frontend/src/features/themes/components/ThemeRotationExperience.tsx`
- `frontend/src/features/themes/themeRotation.ts`
- `frontend/src/features/themes/themeSnapshot.ts`
- `frontend/src/hooks/useAsyncData.ts`
- `frontend/src/hooks/useThemeRotation.ts`
- `frontend/src/hooks/useThemeSnapshot.ts`
- `frontend/src/services/api.ts`
- `frontend/src/services/requestCache.ts`
- `frontend/src/types/market.ts`

New test, hook, and validation files:

- `backend/tests/test_stage12_2_performance_contracts.py`
- `frontend/src/hooks/useRoutePerformanceMarks.ts`
- `frontend/src/hooks/useThemeDetail.ts`
- `frontend/tests/stage12PerformanceOptimization.test.ts`
- `frontend/scripts/validate-stage12-performance.js`

New deliverables:

- The nine required Stage 12.2 Markdown reports.
- `artifacts/stage12.2-performance.json`
- `artifacts/stage12.2-validation.json`
- `artifacts/stage12.2-visual-acceptance.json`
- 23 files under `artifacts/stage12.2-screenshots/`, indexed by the visual-acceptance artifact.

No Stage 12.1 or earlier artifact was modified. No commit or tag was created.

## Validation summary

| Gate | Result |
|---|---|
| Stage 12.2 backend contracts | PASS, 4/4 |
| Theme Rotation integration | PASS, 12/12 |
| Full backend | 635/636; one unchanged historical Stage 8.75 visual-evidence mismatch |
| Full frontend standalone suite | PASS, 64/64 files |
| TypeScript | PASS |
| Expo lint | PASS |
| Production web export | PASS, 25 routes |
| Data/UI and route contracts | PASS |
| Stage 11.2A/11.2B/11.2C source validators | PASS |
| Stage 11.3 validation | PASS |
| Browser visual acceptance | PASS, 20 cases / 23 screenshots |
| Accessibility source contract | PASS; existing absolute Lighthouse issues recorded |
| Stage 12.2 artifact/budget validator | PASS |
| `git diff --check` | PASS |

## Freeze decision

The desktop-web implementation is ready to freeze. Stage 12.2 as a cross-platform release gate is **not ready for strict freeze** until native-device profiling is completed and a separately authorized process refreshes historical visual evidence. No historical artifact was overwritten here.
