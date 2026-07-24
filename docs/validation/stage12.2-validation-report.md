# Stage 12.2 Validation Report

**Date:** 2026-07-24  
**Baseline:** Stage 12.1 at `e2de1f415260593541e641ee2c4cb3f2382a7634`  
**Classification:** **PASS WITH CONDITIONS**

## Result

The optimized desktop-web paths meet every hard Stage 12.2 performance budget and preserve canonical intelligence identity, freshness, provider state, route behavior, and visual hierarchy. Strict PASS is withheld because native-device performance evidence remains outstanding and historical visual artifacts were explicitly required to remain unchanged, so their source/snapshot-fingerprint gates correctly report stale evidence after this source change.

## Functional and contract validation

| Validation | Result | Evidence |
|---|---|---|
| Focused Stage 12.2 backend contracts | PASS, 4/4 | summary/detail separation, compact/full coordinate identity, payload budgets, one-time storage init |
| Theme/rotation focused backend tests | PASS, 12/12 integration plus focused suite | legacy and compact contracts coexist |
| Full backend regression | PASS WITH PRE-EXISTING ARTIFACT CONDITION, 635/636 | only Stage 8.75 historical visual snapshot ID mismatch |
| Full frontend tests | PASS, 64 files | existing and Stage 12.2 coverage |
| Stage 12.2 frontend optimization test | PASS | request/cache/hooks/route contract assertions |
| TypeScript | PASS | no type errors |
| Expo lint | PASS | no lint failures |
| Production web export | PASS | 25 static routes |
| Data/UI contracts | PASS | canonical data-state presentation preserved |
| Route validation | PASS | paths unchanged |
| Stage 11.2A visual-system source validator | PASS | shared system intact |
| Stage 11.2B navigation-layout source validator | PASS | navigation/layout source intact |
| Stage 11.2C accessibility source validator | PASS | accessibility source contract intact |
| Stage 11.3 Settings source/artifact/tests | PASS | Settings unaffected |
| `git diff --check` | PASS | no whitespace errors |

## Historical artifact disposition

No Stage 8.75, 10.2, 11.2B, 11.2C, or 12.1 artifact was modified. Consequently:

- Stage 8.75 full-regression visual evidence refers to snapshot `theme-2026-07-22-c8d9a44cdd`, while the independently published service snapshot at validation was `theme-2026-07-22-202acb645c`.
- Stage 10.2, 11.2B, and 11.2C visual fingerprint validators report stale source evidence after the authorized Stage 12.2 implementation.
- Their source-level validators pass.

These are evidence-freshness conditions, not an authorization to rewrite historical records. Refreshing those artifacts requires a separate, explicitly authorized validation stage.

## Performance validation

| Route | Baseline | p50 | p95 | Hard limit | Result |
|---|---:|---:|---:|---:|---|
| Home | 4,020 ms | 498 ms | 563 ms | 2,000 ms | PASS |
| Market | 3,972 ms | 460 ms | 483 ms | 2,000 ms | PASS |
| Sectors | 7,113 ms | 2,225 ms | 2,232 ms | 2,500 ms | PASS |
| Theme Rotation | 10,480 ms | 354 ms | 356 ms | 3,000 ms | PASS |
| Stock Detail | 3,697 ms | 394 ms | 824 ms | 2,000 ms | PASS |

Payload, parse, cache, bundle, render, and memory results are recorded in `artifacts/stage12.2-performance.json` and the supporting reports.

## Visual and interaction acceptance

Twenty required cases are represented by 23 browser screenshots. They cover critical and fully loaded states, lazy detail, cached revisits, stale refresh, partial data, secondary failure with retained critical content, desktop/mobile widths, Reports, Copilot, directory, and comparison. No redesign or hierarchy change was introduced.

The browser accessibility source gate passes. Absolute Lighthouse accessibility scores (Home 96, Theme Rotation 86, Stock Detail 78) expose pre-existing title, label, and ARIA work that remains outside this performance-only scope; no Stage 12.2 regression was identified.

## Conditions and release decision

1. Run native iOS and Android cold/warm startup, frame pacing, repeated-navigation heap, repeated Stock Detail, Reports, and Copilot profiles.
2. Refresh historical visual evidence only in a separately authorized validation stage.
3. Continue Sectors work toward the 2.0 s target and cache reuse toward 70% without weakening freshness or availability semantics.
4. Track constrained-mobile-web LCP separately from decision-ready timing.

Desktop web is ready to freeze. Cross-platform Stage 12.2 is **not ready for strict freeze** until conditions 1 and 2 are resolved. No commit or tag was created.
