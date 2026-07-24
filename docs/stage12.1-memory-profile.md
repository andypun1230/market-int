# Stage 12.1 Memory Profile

**Classification:** PASS WITH CONDITIONS

## Result

No memory leak was confirmed in the measured production web session. Renderer and backend RSS fell below their starting values after repeated navigation and an idle/reclamation period, and DOM cardinality did not grow monotonically. Two retention risks remain: unbounded frontend request-cache maps and unbounded report-library history.

## Single-load trace memory

| View | JS heap start | JS heap end | JS heap peak | Final DOM nodes | Event listeners |
|---|---:|---:|---:|---:|---:|
| Sector heatmap | 1.64 MB | 28.33 MB | 28.33 MB | 521 | 813 |
| Sector rotation | 1.64 MB | 32.30 MB | 32.30 MB | 980 | 1,037 |
| Theme rotation | 18.23 MB* | 21.30 MB | 37.57 MB | 585 | 1,109 |
| Compare | 8.18 MB* | 36.45 MB | 36.45 MB | 769 | 859 |

\*Trace counter sampling began after some initialization, so the starting number is not comparable to a process-start heap baseline.

## Long-session navigation

| Point | Browser renderer RSS | Backend RSS |
|---|---:|---:|
| Initial | 322.3 MB | 838.5 MB |
| After 25 primary-tab transitions | 357.3 MB | 873.4 MB |
| After 10 Reports + 10 Copilot + 10 Stock Detail visits and idle | **302.8 MB** | **365.6 MB** |

OS RSS is affected by compression, shared renderer processes, garbage collection, and backend cache reclamation. It is used only as a trend signal. The final value below baseline argues against a retained-session leak but does not prove native heap safety.

## DOM retention checks

- Primary tab cycles stabilized at approximately Home 959, Market 971, Sectors 950, Watchlist 960, and More 950 nodes.
- Ten Reports cycles returned 1,091 nodes open and 950 after return on every cycle.
- Ten Copilot cycles returned 1,283 nodes open and 950 after return on every cycle.
- Ten NVDA Stock Detail cycles returned 1,329 nodes open and 960 after return on every cycle.

There was no monotonic DOM growth across these cycles.

## Retention risks found by source inspection

1. **Request cache — Medium.** `frontend/src/services/requestCache.ts` holds `cache` and `inflight` Maps. TTL is checked on reads, but there is no size cap or periodic sweep. Broad symbol exploration can leave expired dynamic keys resident until reload or explicit clearing.
2. **Report library — Medium.** report history is persisted and loaded into application state without an observed record-count cap. Repeated generation can grow storage and in-memory collection size.
3. **Copilot history — Low/Medium.** existing saved content produced a 1,283-node view. Repeated visits were stable, but very long conversations can increase live tree size.

No reports or Copilot requests were created during profiling because those actions would mutate user-visible data.

## Budgets

| Budget | Current | Status |
|---|---:|---|
| Startup/heavy-view JS heap <= 40 MB | Peak 37.57 MB | Pass |
| DOM growth after 30 cycles < 5% | No growth observed | Pass |
| Renderer RSS after idle <= 10% over baseline | 6% below baseline | Pass |
| Native heap growth after repeat navigation < 10% | Not measured | Condition |

## Opportunities

- **Medium:** use bounded LRU behavior and an expiry sweep for request-cache entries; expected gain is bounded long-session heap rather than immediate route speed.
- **Medium:** define report retention/pagination so the full lifetime library is not always resident.
- **Medium:** virtualize long Copilot histories and verify on a large saved conversation.
- **Required follow-up:** native Instruments/Android Studio heap snapshots at startup, after 30 navigation cycles, repeated reports, repeated distinct Stock Detail symbols, and a long Copilot session.

No memory-management code was changed.
