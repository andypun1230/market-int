# Stage 12.2 Request Waterfall Report

## Dependency classification

| Screen | Independent critical | Required sequence | Secondary/deferred |
|---|---|---|---|
| Home | provider state, Home dashboard, market news | none | lower cards within canonical dashboard |
| Market | provider state, core snapshot, macro/news/session/history | detail groups load when selected | structure, decision, institutional detail groups |
| Sectors | provider state, sector snapshot | rotation requires sector snapshot identity | theme status/directory and registries when not needed by active section |
| Theme Rotation | provider state and compact rotation | none for initial map | Theme Directory, registries, sector snapshot, Theme Detail |
| Stock Detail | watchlist summary, aggregate, quote, theme mappings, news | StockCard mounts after canonical list item exists | snapshot refresh and evidence tabs |
| Reports | report history | none | report generation/PDF only when requested |
| Copilot | persisted shell/session | prompt submission only on user action | agent response stream |

## Removed waterfall

Stage 12.1 loaded the 6.55 MB Theme Directory, then started Theme Rotation. Stage 12.2 starts the compact rotation request without a Theme Directory identity dependency. Optional Theme Directory/status/registry reads begin after the decision path and cannot gate the map.

No one-request-per-theme behavior exists. The final fully loaded request count remains seven for Theme Rotation, but the only decision-critical analytical request is the compact rotation response. The sequential dependency was removed rather than hidden with a longer timeout.

| Counted path | Before | After |
|---|---:|---:|
| Theme Rotation critical analytical chain | 2 | 1 |
| Theme Rotation fully loaded | 7 | 7 |
| Stock Detail stock-analysis reads | 3 | 1 |
| Theme Detail reads before a user opens detail | embedded for all 26 themes | 0 |
| Per-theme Rotation fan-out | 0 | 0 |

## Correctness

- Identical concurrent rotations share one in-flight promise.
- A latest response primes its immutable snapshot key, avoiding a second request when summary identity arrives.
- Route changes abort cancellable transport work; request sequence IDs prevent older responses from overwriting newer state.
- Failed secondary detail retains the published summary and renders an explicit error, verified in browser acceptance.
- Atomic loading/stale/error reducers remain unchanged.

## Result

| Screen | Baseline final | Stage 12.2 p50 | Critical request effect |
|---|---:|---:|---|
| Home | 4,020 ms | 498 ms | warmed service/cache path |
| Market | 3,972 ms | 460 ms | core summary no longer waits for detail groups |
| Sectors | 7,113 ms | 2,225 ms | summary payload reduction removes transfer/parse gate |
| Theme Rotation | 10,480 ms | 354 ms | list→rotation sequence removed |
| Stock Detail | 3,697 ms | 394 ms | one aggregate request in final runs |
