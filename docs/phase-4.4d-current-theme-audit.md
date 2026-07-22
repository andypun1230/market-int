# Phase 4.4D Current Theme Audit

Generated/test and static values are not eligible for live migration.

| Classification | Paths | Live use |
| --- | --- | --- |
| `test_fixture` | `frontend/src/data/sectorTabTestData.ts` | no |
| `static_strategy_preference` | `backend/app/services/theme_provenance.py`, `frontend/src/features/market/marketOverviewAnalysis.ts`, `frontend/src/app/report.tsx` | no |
| `unavailable` | `frontend/src/app/(tabs)/sectors.tsx`, `backend/app/services/sector_dashboard.py` | no |
| `live_verified` | `backend/app/themes/`, `backend/app/theme_snapshots/` | only immutable ThemeSnapshot readers |

## Findings

- `sectorTabTestData.ts` contains generated fixture trails and stays behind the explicit test-scenario flag.
- Static strategy preferences remain provenance-labelled and are not live rankings.
- Production Themes currently returns an explicit unavailable state until reviewed active definitions and a ThemeSnapshot exist.
- Unknown or reconstructed legacy data was not migrated.
