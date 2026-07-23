# Stage 9.2B — Canonical Filter Registry

Owner: normalized group contract (`group-intelligence-v1`).  
Frontend responsibility: selection only; no authoritative intelligence derivation.

| Filter | Canonical field | Values / threshold | Empty/missing behavior |
|---|---|---|---|
| State/quadrant | `quadrant` | all, leading, improving, weakening, lagging | unavailable does not match a governed quadrant |
| Rank range | `rank` | top 3, 5, 10 | null rank is excluded |
| Breadth | `breadth.above_50` | ≥50%, ≥65% | null is excluded |
| Momentum | `relative_momentum` | ≥50, ≥100 | null is excluded |
| Saved only | canonical `type:id` | local saved identity set | unsaved is excluded |
| Availability | `availability.state` | available, partial, unavailable | exact state match |
| Movement | `movement.direction` | gaining, losing, stable | unavailable is excluded |
| Strong movement | `rank_change` | absolute change ≥2 | null/0 is excluded |
| Recent transition | `movement.recent_transition` | true | requires different consecutive snapshot states |

Filters combine with AND semantics. The panel reports `resultCount of totalCount`, displays an explicit empty heatmap, and provides one reset action. Filter state is intentionally scoped to the active task section and session; it is not persisted because stale cross-session analytical filters would conceal newly published entities without clear user benefit.

Backend `filter_groups` implements the same registry for API consumers. Frontend focused tests cover combinations, reset, empty results, saved identities, strong movement, unavailable metrics, and adaptive comparison limits.

