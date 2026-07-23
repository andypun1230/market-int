# Stage 9.2A Shared Component Inventory

Runtime inventory: `frontend/src/architecture/sharedComponentRegistry.ts`.

| Family | Canonical shared components | Cleanup |
|---|---|---|
| Intelligence cards | `DashboardCard`, `DecisionCard`, `HeroDecisionCard` | Existing surfaces retained; domain content remains owned by feature presenters |
| Evidence panels | `ExpandableSection`, `DashboardCard` | Existing evidence containers retained; no new evidence calculation introduced |
| Confidence indicators | `ConfidenceIndicator`, `ScoreGauge`, `StatusBadge` | AI confidence presentation moved unchanged into shared `ConfidenceIndicator`; compatibility wrapper retained |
| Alert badges/lists | `StatusBadge`, `AlertList` | Sector and Theme snapshot alert rows consolidated |
| Summary components | `CompactSummaryCard`, `SummaryTile`, `MetricTile` | Existing primitives registered as canonical choices |

## Rules

- Shared components present values; they do not calculate intelligence.
- Domain-specific semantics stay in feature presenters and ownership modules.
- Compatibility wrappers may remain when they prevent call-site churn, but visual implementation has one owner.
