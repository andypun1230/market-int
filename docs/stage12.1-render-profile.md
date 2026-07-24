# Stage 12.1 Render Profile

**Classification:** PASS WITH CONDITIONS

## Summary

Initial shell rendering is healthy: required screens generally incur one long task, total blocking time remains between 38 and 52 ms, and post-API visual updates complete in 19–134 ms. The visible delays on analytical screens are overwhelmingly network/dependency delays. Heatmap load is the sole trace with explicit dropped frames.

## Required screens

| Screen | TBT | Main-thread work | Long tasks | DOM elements | Post-API visual work |
|---|---:|---:|---:|---:|---:|
| Home | 41 ms | 258 ms | 1 | 318 | 31 ms |
| Market | 52 ms | 292 ms | 2 | 276 | 46 ms |
| Sectors / heatmap | 38 ms | 267 ms | 1 | 216 audit count | 34 ms |
| Watchlist | 39 ms | 241 ms | 1 | 248 | 19 ms |
| Reports | 39 ms | 211 ms | 1 | 177 | 30 ms |
| Copilot shell | 39 ms | 211 ms | 1 | 177 clean / 1,283 with saved history | 134 ms |
| Stock Detail | 39 ms | 412 ms | 1 | 627 | 19 ms |

## Analytical view traces

| View | Final visual / LCP | TBT | Longest task | Final DOM nodes | Event listeners | Heap peak | Dropped-frame events |
|---|---:|---:|---:|---:|---:|---:|---:|
| Sector heatmap | 6.81 s data-ready | 46 ms | 96 ms | 521 | 813 | 28.33 MB | **2** |
| Sector rotation | 7.40 s LCP | 39 ms | 89 ms | 980 | 1,037 | 32.30 MB | 0 |
| Theme rotation | 10.48 s final visual | 39 ms | 89 ms | 585 | 1,109 | 37.57 MB | 0 |
| Compare | 6.91 s data-ready | 39 ms | 89 ms | 769 | 859 | 36.45 MB | 0 |

Chrome's active compositor cadence had a median 8.33 ms interval, consistent with the 120 Hz host display. This is not equivalent to a sustained native FPS measurement. The defensible conclusion is that traces show no broad frame-collapse pattern, while the heatmap has two concrete load-time drops.

## Rerender assessment

Exact React commit and component-rerender counts were unavailable without adding profiler instrumentation, which the profiling-only constraint did not authorize. The following non-invasive proxies were used:

- one or two long tasks per route rather than repeated main-thread stalls;
- stable DOM cardinality across repeated route cycles;
- stable per-route node counts across ten repeated Reports, Copilot, and Stock Detail visits;
- post-API update windows below 50 ms except Copilot at 134 ms.

These proxies reveal no retained rendering loop or monotonic tree growth. They do not replace a React Profiler capture, which remains a condition for strict render certification.

## Budgets

| Budget | Current | Status |
|---|---:|---|
| Total blocking time <= 200 ms | 38–52 ms | Pass |
| Long tasks >50 ms <= 2/load | 1–2 | Pass |
| Dropped frames <= 1/load | Heatmap 2 | Fail |
| Standard screen DOM <= 1,000 | 177–980 | Pass |
| Modal/long-chat DOM <= 1,500 | 1,283–1,329 | Pass |
| Target sustained FPS >= 60 | Not native-certified | Condition |

## Opportunities

- **High:** reduce and decouple sector/theme data work before rendering; this addresses the largest perceived delay even though it is not primarily a render problem.
- **Medium:** batch or virtualize heatmap cell work to remove the two observed dropped frames and approximately 96 ms task.
- **Medium:** virtualize or collapse offscreen Copilot messages for long histories; expected DOM reduction of roughly 30–60% for large conversations.
- **Low:** collect React commit counts and native frame pacing in the next device-validation pass before choosing component-level memoization work.

No render code was changed.
