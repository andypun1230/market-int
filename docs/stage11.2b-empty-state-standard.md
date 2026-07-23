# Stage 11.2B Non-loaded State Standard

Owner: `frontend/src/architecture/statePresentationRegistry.ts`; renderer: `EmptyState` and `ErrorState`.

| State | Meaning | Typical action |
|---|---|---|
| `empty` | Valid collection with no entries | Optional contextual action |
| `no_search_results` | Query completed with no match | Preserve query; adjust/clear search |
| `unavailable` | Source or destination cannot currently supply content | Safe destination or explanation |
| `partial` | Some authoritative inputs are present | Evidence/diagnostic disclosure |
| `failed` | Attempt ended in error | Retry |
| `maintenance` | Operational work, not a trading alert | Status explanation |
| `permission_restricted` | Access policy prevents content | Access guidance |
| `not_generated` | Valid artifact has not been created | Generate |
| `no_saved_entities` | User has saved none | Direct browse action |
| `no_qualifying_results` | Filters exclude all entries | Clear/adjust filters |

Each state has an accessibility prefix, semantic icon, and tone. Failed and empty are intentionally distinct; maintenance does not use trading-urgency danger semantics. Search results include the query, reports lead to generation, and saved sector/theme states lead to browse.
