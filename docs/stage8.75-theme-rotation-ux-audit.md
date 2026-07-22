# Stage 8.75 Theme Rotation UX audit

## Existing implementation

- Screen: `frontend/src/app/(tabs)/sectors.tsx`, live `themesRotation` section.
- Query: `useThemeRotation` reads the reviewed `ThemeSnapshot` identity and fetches one canonical profile response. Its cache identity is taxonomy + snapshot + model + profile.
- Transformation: `adaptThemeRotation` validates the governed model version and maps eligible API points into `CanonicalThemeRotationPoint` rows.
- Chart: every mode uses `RotationQuadrantChart`; there is no second Theme chart implementation.
- Filters before this patch: the shared chart owned or accepted only current-quadrant and label-mode state.
- Labels before this patch: Smart, All, or None. Smart ranked canonical label priority plus selected/watchlisted state.
- Tails before this patch: all backend observations were plotted in live mode; test mode passed a fixed length of 10.
- Selection before this patch: tapping a node/label selected the chart inspector. Opening details was a second action, but the Theme screen did not expose a first-class Focus mode.
- Saved themes: the unified watchlist already stores canonical `theme` entries. No second store is required.
- Taxonomy: the reviewed ThemeSnapshot carries definition metadata, including canonical aliases and parent-sector IDs. The frontend previously retained only a formatted parent-sector label.
- Detail navigation: the screen already opens `ThemeDetailContent` in the shared `DetailModal` and supports Theme deep links.
- Search/modal patterns: `SectorThemeSearchModal`, `DetailModal`, `SegmentedControl`, and compact chips are reusable responsive patterns.
- Memoization: the hook cache prevents duplicate requests; the screen and chart memoize response rows, chart items, filters, label candidates, and layout.
- Tooltip: `RotationQuadrantChart` has a textual point inspector with quadrant, coordinates, movement summary, benchmark, save, and open-detail actions.

## State flow before this patch

```text
canonical rotation response
-> adaptThemeRotation
-> all eligible canonical points
-> chart-owned quadrant filter
-> optional chart tail slice
-> chart-owned label selection/collision placement
-> chart visibility summary
-> node/label selection and point inspector
```

The API already returned governed `direction`, `speed`, `distance_travelled`, `net_displacement`, `recent_acceleration`, and transition-count fields. The adapter discarded them. This patch may expose those existing fields and a canonical latest transition descriptor, but must not reproduce or change their calculations.

## Target state flow

```text
canonical response + reviewed taxonomy metadata + unified watchlist IDs
-> buildVisibleRotationView(source, viewState)
   1. canonical row eligibility
   2. taxonomy/saved/custom universe
   3. explicit selection
   4. Overview / Compare / Focus constraint
   5. current-endpoint quadrant
   6. governed movement metrics
   7. canonical latest transition
   8. genuine-tail projection
   9. label candidate selection
-> one shared RotationQuadrantChart
-> collision placement, counts, Focus/Compare details, and interactions
```

All filters are presentation-only. Source points and histories remain immutable, label choices never change point visibility, and filter changes do not alter the query identity or trigger a backend request.
