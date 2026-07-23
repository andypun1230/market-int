# Stage 11.2A Shared Card Inventory

## Result

**PASS**

## Shared surface

`CARD_SURFACE` in `DashboardCard.tsx` is the authoritative owner of the standard card background, border, radius, and border width.

| Consumer | Use |
|---|---|
| `DashboardCard` | General shared information and intelligence surface |
| `EmptyState` | Empty-result surface |
| `ErrorState` | Error surface with danger border override |
| `LoadingState` | Loading and placeholder surface |
| `SkeletonCard` | Skeleton surface |

Each consumer retains only its behavioral spacing and state-specific overrides. This removes identical shell declarations without changing component structure or appearance.

## Existing shared families retained

- Intelligence: `DashboardCard`, `DecisionCard`, `HeroDecisionCard`, `DecisionSummaryCard`
- Evidence: `ExpandableSection`, `DashboardCard`
- Summary: `CompactSummaryCard`, `SummaryTile`, `MetricTile`, `DataStateSummary`
- Status: `StatusBadge`, `AlertList`, `ConfidenceIndicator`

## Intentional non-consolidation

Specialized analytical cards were not rewritten. Heatmaps, rotation charts, institutional charts, technical evidence panels, report document cards, and entity comparison cards keep their domain-specific behavior and geometry. Consolidation was limited to behaviorally identical surfaces, as required.
