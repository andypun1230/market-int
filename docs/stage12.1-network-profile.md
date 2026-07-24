# Stage 12.1 Network Profile

**Classification:** PASS WITH CONDITIONS

## Environment

Measurements used the local production web export against the existing local backend. Network and CPU throttling were disabled so the results isolate application/backend behavior; they are not estimates for cellular or geographically remote users.

## Endpoint timings

Repeated direct requests show a large cold-to-warm difference:

| Endpoint | Representative warm latency | Payload | Cold browser observation |
|---|---:|---:|---:|
| `/data-sources/status` | 21.8 ms median | 17.6 KB | 23–25 ms |
| `/home/dashboard` | 44–48 ms after first request | 1.67 MB | 3.74 s |
| `/market/core-snapshot` | 41–45 ms | 831 KB | 3.62 s cluster |
| `/market/sectors/snapshot/latest` | 30–31 ms | 1.28 MB | 6.8–7.0 s cluster |
| `/market/themes` | 23–25 ms warm | **6.55 MB** | 6.8–7.0 s cluster |
| `/watchlist/summary?symbols=NVDA` | 2–21 ms | 20.5 KB | up to 21 ms per request |
| `/stock-analysis/NVDA` | 5–7 ms | 260 KB | repeated at 0.37, 1.65, and 3.66 s |
| `/intelligence/news/market` | 1.5–1.8 ms | 1.9 KB | 3.74 s when cold/contended |
| Report history | 4–27 ms | 18.9 KB | not critical to library paint |

The warm endpoint logic is generally fast. Cold browser concurrency exposes backend initialization/contention, serialization, and transfer costs. Market's four primary intelligence endpoints all finish around 3.61–3.63 seconds, while six history calls complete in 4–46 ms.

## Route network findings

- **Home:** the 1.67 MB dashboard and market-news calls delay decision readiness to 4.02 seconds.
- **Market:** 11 requests complete by 3.93 seconds. The critical delay is shared across macro, market news, market session, and core snapshot.
- **Sectors:** `/market/themes` dominates at 6.55 MB. Along with the 1.28 MB sector snapshot, the route transfers 9.25 MB.
- **Sector Rotation:** base datasets complete near seven seconds; only then does the 46 ms rotation request start.
- **Theme Rotation:** the rotation request starts after the base dependency and takes another 3.39 seconds.
- **Compare:** the compare response is only 289 bytes but takes 3.57 seconds; the page remains gated by the themes response.
- **Stock Detail:** existing refresh behavior issues three analysis reads over 3.3 seconds. This adds roughly 520 KB of repeated analysis transfer.

## Cache and provider observations

Snapshot after profiling:

| Counter | Value |
|---|---:|
| Cache items | 63 |
| Memory hits | 641 |
| Memory misses | 1,156 |
| Persistent hits | 401 |
| Stale hits | 262 |
| Provider calls | 408 |
| Background refreshes / failures | 262 / 0 |
| History jobs started / succeeded / failed | 108 / 108 / 0 |
| History retries / queue timeouts | 0 / 0 |
| Maximum concurrent history work | 2 |

Derived rates:

- Memory hit rate: **35.7%** (`641 / (641 + 1156)`).
- Effective memory-plus-persistent reuse: **58.0%** (`(641 + 401) / (641 + 1156)`). Persistent hits occur after the memory-miss path, so this is reported as a derived reuse metric rather than a native counter.
- Provider-call ratio: **22.7%**.
- Stale-serving ratio: **14.6%**.
- Retry and background-refresh failure rate: **0%**.

## Budgets and status

| Budget | Current | Status |
|---|---:|---|
| Initial route API payload <= 2 MB | Sectors APIs ~7.9 MB | Fail |
| Individual response <= 1 MB | Themes 6.55 MB; sector snapshot 1.28 MB | Fail |
| Effective cache reuse >= 70% | 58.0% derived | Fail |
| History retries <= 1 | 0 | Pass |
| History coordinator failures = 0 | 0 | Pass |

## Opportunities

- **High:** return compact, paged, or route-specific theme data; expected to remove more than 6 MB from sector-only loads.
- **High:** precompute or parallelize rotation dependencies; expected to save approximately six seconds on the observed Theme Rotation cold path.
- **High:** warm or incrementally materialize Home/Market aggregates; expected cold decision-ready gain of at least 1.5 seconds locally.
- **Medium:** consolidate snapshot refreshes and terminate Stock Detail polling as soon as a usable snapshot is complete; expected readiness under 1.5 seconds and about 520 KB less repeated transfer.

No network behavior was changed in Stage 12.1.
