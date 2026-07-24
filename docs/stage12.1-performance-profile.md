# Stage 12.1 Performance Profile

**Date:** 2026-07-24

**Baseline:** `e2de1f415260593541e641ee2c4cb3f2382a7634` (`main`)

**Classification:** **PASS WITH CONDITIONS**

## Executive summary

The production web shell is fast and main-thread work is controlled, but several intelligence views are not decision-ready quickly enough. The principal constraint is data acquisition and payload size, not initial React rendering. Home and Market take about four seconds to reach final decision data on a cold local run; Sectors takes 7.1 seconds; Theme Rotation takes 10.5 seconds. The 6.55 MB themes response is the largest recurring bottleneck.

No optimization, route, UI, business-logic, or intelligence changes were made during this stage.

## Method

- Built the existing Expo web application with `npx expo export --platform web`.
- Served the production export locally and measured with Chrome/Lighthouse 13.4.1.
- Used clean Lighthouse navigations for cold web measurements and repeated in-app reloads/navigation for warm and long-session observations.
- Used an unthrottled local network and CPU. Backend providers were Finnhub for quotes and Polygon for daily history; fallback was not active.
- Collected Chrome performance traces for heatmap, sector rotation, theme rotation, and compare.
- Timed representative APIs independently with repeated local requests.

These figures are reproducible local-web measurements, not native-device certification. Native cold start, native frame pacing, and native heap snapshots remain a release-validation condition.

### Metric definitions

- **Cold launch / first interactive:** clean Lighthouse navigation to an interactive application shell.
- **Warm launch:** repeated same-origin production reload with the app already initialized and local caches available.
- **JS initialization:** Lighthouse JavaScript boot-up time.
- **Decision-ready:** final critical API completion plus the last observed visual update.
- **State/render proxy:** time between the last critical API response and the last observed visual update.
- **Rerender proxy:** trace/DOM stability and long-task observations. Exact React commit counts require instrumentation and were not added during this profiling-only stage.

## Startup profile

Three clean Home runs produced:

| Metric | Run 1 | Run 2 | Run 3 | Median |
|---|---:|---:|---:|---:|
| Lighthouse performance | 100 | 100 | 100 | 100 |
| First paint / FCP | 79 ms | 71 ms | 69 ms | **71 ms** |
| LCP | 79 ms | 71 ms | 69 ms | **71 ms** |
| First interactive / TTI | 179 ms | 173 ms | 169 ms | **173 ms** |
| JS initialization | 193 ms | 186 ms | 182 ms | **186 ms** |
| Total blocking time | 41 ms | 39 ms | 38 ms | **39 ms** |
| Main-thread work | 258 ms | 250 ms | 242 ms | **250 ms** |
| Startup transfer | 6.305 MB | 6.305 MB | 6.305 MB | **6.305 MB** |

Warm reloads were 103, 81, 82, 79, and 72 ms; median **81 ms**. The interactive shell was present in every run.

The distinction between shell-ready and decision-ready is material: Home's shell was interactive in 179 ms, while `/home/dashboard` and market news completed near 3.99 seconds and the final visual state appeared at 4.02 seconds.

## Screen profile

| Screen | Shell interactive | Critical API ready | Final visual | API count | Transfer | Post-API render | Result |
|---|---:|---:|---:|---:|---:|---:|---|
| Home | 179 ms | 3,989 ms | **4,020 ms** | 3 | 6.31 MB | 31 ms | Conditional |
| Market | 307 ms | 3,926 ms | **3,972 ms** | 11 | 2.65 MB | 46 ms | Conditional |
| Sectors / heatmap | 208 ms | 7,079 ms | **7,113 ms** | 6 | 9.25 MB | 34 ms | Over budget |
| Watchlist | 208 ms | 401 ms | **420 ms** | 2 | 1.36 MB | 19 ms | Pass |
| Reports library | 208 ms | 297 ms | **327 ms** | 1 | 1.34 MB | 30 ms | Pass |
| Copilot shell | 210 ms | 294 ms | **428 ms** | 1 | 1.34 MB | 134 ms | Pass |
| Stock Detail — NVDA | 209 ms | 3,678 ms | **3,697 ms** | 9 | 2.17 MB | 19 ms | Over budget |

Reports were profiled at the library/shell level. Generating a report would have changed user-visible state and was intentionally excluded. Copilot was profiled without sending a prompt for the same reason.

## Key bottlenecks

1. **Themes payload and dependency fan-out — High.** `/market/themes` returns 6.55 MB and delays Sectors-family pages to roughly 6.8–7.1 seconds.
2. **Theme Rotation request sequencing — High.** Rotation begins after base datasets complete, then adds 3.39 seconds, producing a 10.48-second final visual state.
3. **Cold backend materialization — High.** Home and Market critical datasets cluster around 3.6–3.7 seconds cold, but the same endpoints are tens of milliseconds warm.
4. **Single application bundle — High.** The one 3.59 MB raw / 909 KB gzip JavaScript bundle delivers approximately 60.5% unused JavaScript on Home.
5. **Stock Detail refresh polling — Medium.** Three stock-analysis requests and a second watchlist summary extend final readiness to 3.70 seconds. Source inspection confirms this is current snapshot-refresh behavior, not a changed route or calculation.
6. **Heatmap load frame loss — Medium.** The trace contains two explicit dropped-frame events and one approximately 96 ms long task.

## Performance budgets

| Area | Budget |
|---|---|
| FCP | p50 <= 500 ms local; <= 1.5 s target device |
| Shell interactive | p50 <= 1 s; p95 <= 2 s |
| JS initialization | <= 250 ms |
| Total blocking time | <= 200 ms |
| Home / Market decision-ready | p50 <= 2.5 s; p95 <= 5 s |
| Sector / rotation / compare decision-ready | p50 <= 3 s; p95 <= 6 s |
| Watchlist / Reports / Copilot shell | p50 <= 1 s |
| Stock Detail decision-ready | p50 <= 1.5 s; p95 <= 3 s |
| Initial route API payload | <= 2 MB |
| Individual API payload | <= 1 MB |
| JS gzip | <= 750 KB |
| Dropped frames | <= 1 per load; target sustained 60 FPS |
| Long tasks over 50 ms | <= 2 per load |

## Assessment

Stage 12.1 is **PASS WITH CONDITIONS**. The profiling objective is fulfilled and the evidence identifies actionable constraints without modifying the product. Strict PASS is withheld because sector-family and Stock Detail decision-ready budgets fail, Home/Market are above the preferred decision-ready target, and native-device startup/FPS/heap measurements remain outstanding.
