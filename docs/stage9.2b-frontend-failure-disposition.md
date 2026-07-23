# Stage 9.2B — Frontend Failure Disposition

Untouched baseline: 53 standalone files; 48 passed and 5 failed.

| File | Baseline category | Evidence | Resolution | Final |
|---|---|---|---|---|
| `macroAnalysis.test.ts` | fixture expectation drift | Inflation was present in authoritative implication/current risks, while the test required it to replace the leading cross-asset `mainRisk`. | Assert the actual semantic contract without forcing ownership into the wrong field. | PASS |
| `sectorAnalysisFeatures.test.ts` | environment-specific architecture defect | A pure domain test reached React Native Flow syntax because `relevantStocks` imported identity logic from the UI store. | Move watchlist identity/migration/toggle logic to pure `watchlist/domain.ts`; consumers reuse it. | PASS |
| `sectorDashboardNormalizers.test.ts` | real product defect | `firstRecord(raw, nested...)` always selected the wrapper before `payload`, losing nested source/partial fields. | Prefer known nested payloads before the wrapper. | PASS |
| `themeProvenance.test.ts` | obsolete expectation | Test asserted the retired two-pilot ThemeSnapshot copy after Stage 8.75 introduced the canonical 26-theme directory contract. | Assert canonical taxonomy, availability, mapped-constituent, and unavailable provenance. | PASS |
| `watchlistStore.test.ts` | environment-specific architecture defect | Pure watchlist tests imported the React/Expo persistence provider and failed in the Node runner. | Test the authoritative pure domain module; UI store imports and re-exports that owner. | PASS |

No assertion was deleted merely to obtain a green result. Each revised assertion continues to validate the intended product contract.

