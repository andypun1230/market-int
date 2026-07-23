# Stage 11.3 — Beta Settings Classification

## Classification rules

- **Complete:** implemented, truthful, and connected to a real consumer.
- **Partially implemented but useful:** produces a real limited effect and states that limitation.
- **Planned for later:** disabled and labelled “Not available in beta,” or absent from beta when development-only.
- **Obsolete:** removed from the beta-visible surface.

## Classification matrix

| Setting / related surface | Classification | Visible | Enabled | Reason |
|---|---|---:|---:|---|
| Dark appearance | Complete | Yes | No choice required | It is the supported selected beta presentation; the row is informational rather than a no-op button. |
| System appearance | Planned for later | Yes | No | Complete light-mode support is unavailable; exact beta label shown. |
| Reduce Motion | Complete | Yes | Yes | Persists and is consumed by the shared animation policy. |
| Color Meaning disclosure | Complete | Yes | No | Describes the existing text-plus-color status contract; it is not presented as editable. |
| English | Complete | Yes | No choice required | It is the sole fully supported application language. |
| Traditional Chinese | Planned for later | Yes | No | Translation coverage is unavailable; exact beta label shown. |
| Push notifications | Planned for later | Yes | No | Delivery service is not connected; no preference is saved. |
| Local display name | Partially implemented but useful | Yes | Yes | Persists and updates More; account sync limitation is explicit. |
| Clear Cached Market Data | Complete | Yes | Yes | Clears frontend and backend market-data caches and reports success/failure/consequence. |
| Data Sources status | Complete | Yes | Yes (navigation) | Opens the canonical status route and uses the shared data-state owner. |
| About system information | Complete | Yes | Yes (navigation) | Opens the canonical About route with shared system state. |
| Privacy disclosure | Complete | Yes | Yes (navigation) | Describes actual local storage, Copilot and report-download behavior. |
| Scenario/test controls | Partially implemented but useful (development only) | No in beta | No in beta | Available only behind the explicit development flag and labelled development-only. |
| Push alerts “Coming Next” | Planned for later | Yes | No | Exact beta label; no active behavior. |
| User accounts | Planned for later | Yes | No | Exact beta label; no active behavior. |
| Premium subscription | Planned for later | Yes | No | Exact beta label; no active behavior. |

## Obsolete findings

No obsolete setting remains beta-visible. No source capability was removed. The previously selectable unfinished System theme was reclassified as planned and disabled rather than deleted.

## Enabled-control proof

| Enabled control | Persistence | Downstream proof |
|---|---|---|
| Reduce Motion | Local | `useReducedMotion` resolves app + platform preferences and feeds shared animated surfaces. |
| Display Name | Local | More renders the stored name in the Profile destination summary. |
| Clear Cached Market Data | Action | Invokes backend invalidation and clears the frontend request cache. |
| Settings navigation rows | None | Each navigates to an existing canonical route. |

There are no enabled notification, locale, theme-choice, account, subscription, or beta scenario controls.

