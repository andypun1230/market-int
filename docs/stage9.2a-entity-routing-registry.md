# Stage 9.2A Entity Routing Registry

Runtime owner: `frontend/src/architecture/entityRoutingRegistry.ts`.

| Entity | Canonical owner | Route | Required identity | Detail selector |
|---|---|---|---|---|
| Stock | Watchlist Stock Detail | `/watchlist` | `symbol` | `detailTab=overview|technical|signals|risk` |
| Sector | Sectors Sector Detail | `/sectors` | `entityId` | `entityKind=sector`, `section=sectorHeatmap` |
| Theme | Sectors Theme Detail | `/sectors` | `entityId` | `entityKind=theme`, `section=themesHeatmap` |
| Report | Report Document | `/report` | optional `reportId` | optional `sectionId` |

## Removed duplicate ownership

- Watchlist no longer mounts its own Sector Detail modal. Saved-sector rows navigate to the Sectors-owned detail.
- Saved themes, Home leadership, ticker search, most-active results, and Copilot actions all use the canonical builder.
- No routes or visible detail layouts were added.
