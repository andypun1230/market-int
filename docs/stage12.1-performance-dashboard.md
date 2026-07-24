# Stage 12.1 Performance Dashboard

**Overall classification:** **PASS WITH CONDITIONS**

**Profile baseline:** `e2de1f415260593541e641ee2c4cb3f2382a7634`

## Launch dashboard

| Metric | Current | Budget | Status |
|---|---:|---:|---|
| Cold FCP, median | 71 ms | <= 500 ms local | PASS |
| Cold shell interactive, median | 173 ms | <= 1 s | PASS |
| Warm reload, median | 81 ms | <= 500 ms | PASS |
| JS initialization, median | 186 ms | <= 250 ms | PASS |
| Total blocking time, median | 39 ms | <= 200 ms | PASS |
| Home decision-ready | 4.02 s | p50 <= 2.5 s | FAIL |

## Screen dashboard

| Screen | Decision-ready | Budget | Main constraint | Status |
|---|---:|---:|---|---|
| Home | 4.02 s | 2.5 s | Cold dashboard/news materialization | FAIL |
| Market | 3.97 s | 2.5 s | Four cold intelligence aggregates | FAIL |
| Sectors / heatmap | 7.11 s | 3.0 s | 6.55 MB themes payload | FAIL |
| Watchlist | 0.42 s | 1.0 s | None material | PASS |
| Reports library | 0.33 s | 1.0 s | Local-library shell only | PASS |
| Copilot shell | 0.43 s | 1.0 s | Saved-history density | PASS |
| Stock Detail | 3.70 s | 1.5 s | Snapshot refresh sequence | FAIL |
| Sector Rotation | 7.40 s | 3.0 s | Base datasets before rotation | FAIL |
| Theme Rotation | 10.48 s | 3.0 s | Sequential 3.39 s rotation call | FAIL |
| Compare | 6.91 s | 3.0 s | Themes/base-data gate | FAIL |

## Resource dashboard

| Metric | Current | Budget | Status |
|---|---:|---:|---|
| JS gzip | 909 KB | <= 750 KB | FAIL |
| Unused JS on Home | 60.49% | <= 35% | FAIL |
| Icon font gzip | 425 KB | <= 150 KB | FAIL |
| Total web export | 5.71 MiB | <= 5 MiB | FAIL |
| Largest API response | 6.55 MB | <= 1 MB | FAIL |
| Effective cache reuse | 58.0% | >= 70% | FAIL |
| Heavy-view JS heap peak | 37.57 MB | <= 40 MB | PASS |
| Renderer RSS after idle | 6% below baseline | <= 10% over | PASS |
| Heatmap dropped frames | 2 | <= 1/load | FAIL |
| Long tasks | 1–2/load | <= 2/load | PASS |

## Severity dashboard

| Severity | Finding | Expected gain if addressed |
|---|---|---|
| High | Single eager JS bundle | 450–600 KB gzip and 40–90 ms JS init |
| High | Full themes payload on sector views | >6 MB transfer; sector readiness toward <2 s warm/local |
| High | Sequential Theme Rotation dependency | Approximately 6 s cold-path gain |
| High | Cold Home/Market materialization | At least 1.5 s decision-ready gain |
| Medium | Stock Detail refresh sequence | About 2.2 s and 520 KB repeated transfer |
| Medium | Full icon font | 300–400 KB gzip |
| Medium | Unbounded cache/report retention | Bounded long-session memory risk |
| Medium | Heatmap load work | Remove two observed dropped frames |
| Low | Duplicate static route HTML | About 231 KB deployment size |

## Release interpretation

The application shell is responsive and no web-session leak was observed. The product is not yet within the proposed decision-ready and payload budgets for data-heavy screens. Native launch, sustained FPS, and heap validation are still required; consequently Stage 12.1 cannot be classified as an unconditional PASS.
