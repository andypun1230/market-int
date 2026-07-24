# Stage 12.1 Validation Report

**Date:** 2026-07-24

**Baseline commit:** `e2de1f415260593541e641ee2c4cb3f2382a7634`

**Final classification:** **PASS WITH CONDITIONS**

## Scope validation

- Production Expo web export completed successfully with 25 static routes.
- Required screens were profiled: Home, Market, Sectors, Watchlist, Reports, Copilot, and canonical NVDA Stock Detail.
- Required analytical views were traced: heatmap, sector rotation, theme rotation, compare, and watchlist/Stock Detail paths.
- Network latency, cache/provider counters, memory trends, bundle composition, and duplication were measured.
- No application source, tests, routes, UI, business logic, intelligence logic, financial model, commit, or tag was changed.

## Evidence validation

| Check | Result |
|---|---|
| Three clean Home startup runs | PASS |
| Required-screen clean navigations | PASS |
| Heavy-view performance traces | PASS |
| Five warm reload observations | PASS |
| Repeated primary navigation | PASS — 25 transitions |
| Repeated Reports / Copilot / Stock Detail | PASS — 10 each |
| Independent endpoint timing | PASS — five reads per representative endpoint |
| Cache/provider coordinator snapshot | PASS |
| Production bundle inventory and gzip measurement | PASS |
| JSON artifact parse/schema sanity | PASS — stage, classification, and nine deliverables verified |
| Documentation-only diff | PASS — exactly eight Markdown reports and one JSON artifact are untracked |
| `git diff --check` | PASS |
| Browser runtime log review | PASS WITH NOTE — no crash/error; web animated-driver fallback warnings and one expected navigation-abort log |

## Important conditions

1. Measurements are production **web** results on a local Mac with an unthrottled local backend. Native iOS/Android cold launch, warm launch, frame pacing, and heap snapshots were not available.
2. Exact React commit/rerender counts require profiler instrumentation. Stage 12.1 used trace long tasks, visual timing, and stable DOM cardinality as non-invasive proxies.
3. Reports were profiled at the library level and Copilot at the existing-session shell level. Generating reports or sending prompts was intentionally avoided because it would mutate user-visible state.
4. Performance budget failures are present on Home, Market, Sectors-family pages, Stock Detail, bundle size, icon font, cache reuse, and heatmap dropped frames.

## Classification rationale

The profiling deliverable is complete and reproducible enough to direct optimization work. The shell is fast, main-thread blocking is controlled, and no web-session leak was confirmed. The result is not an unconditional PASS because critical decision-ready budgets fail and native-device evidence remains outstanding. It is not a FAIL because the application remains functional, core shell performance is healthy, and the identified constraints are bounded and prioritizable.

**Result: PASS WITH CONDITIONS.**
