# Stage 9.2A Validation Report

## Summary

Classification: **PASS WITH CONDITIONS**.

The changed architecture passes compile, lint, contract, and targeted regression gates. The condition is five pre-existing failures in an ad-hoc run of all 53 standalone frontend test files.

## Passing gates

| Gate | Result |
|---|---|
| `npx tsc --noEmit` | Pass |
| `npm run lint` | Pass |
| `npm run validate:data-ui` | Pass; 28 screens represented |
| `npx expo export --platform web` | Pass; 25 static routes exported |
| Backend `unittest discover` | Pass; 624 tests |
| `architectureRegistries.test.ts` | Pass |
| `appPreferences.test.ts` | Pass |
| `sectorThemeSearchModel.test.ts` | Pass |
| `copilotDestinations.test.ts` | Pass |
| `commandSearch.test.ts` | Pass |
| `homeSummary.test.ts` | Pass |
| `themeHomeSummary.test.ts` | Pass |

The architecture test asserts unique output owners, unique interaction IDs, one or more consumers per persisted setting, registered entity routes, and canonical parameters for Stock, Sector, Theme, and Report.

## Full standalone frontend sweep

- 53 files executed.
- 48 passed.
- 5 failed.

Each failure was reproduced against an archive of `HEAD` before Stage 9.2A:

| Baseline failure | Baseline result | Stage 9.2A result | Assessment |
|---|---|---|---|
| `macroAnalysis.test.ts` | Fail: inflation scenario assertion | Same | Pre-existing data/fixture expectation |
| `sectorAnalysisFeatures.test.ts` | Fail: Node runner cannot transform React Native Flow syntax | Same | Pre-existing harness limitation |
| `sectorDashboardNormalizers.test.ts` | Fail: nested payload source assertion | Same | Pre-existing expectation |
| `themeProvenance.test.ts` | Fail: source-text provenance assertion | Same | Pre-existing brittle source assertion |
| `watchlistStore.test.ts` | Fail: Node runner cannot transform React Native Flow syntax | Same | Pre-existing harness limitation |

## Manual validation still required

- Native simulator rendering.
- Rapid tab-switch cancellation behavior.
- Native screenshot capture for failure states.

These are existing manual requirements emitted by `validate:data-ui`; they are not specific regressions from this stage.
