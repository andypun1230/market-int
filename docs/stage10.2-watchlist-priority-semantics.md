# Stage 10.2 Watchlist Priority Semantics

## Trading states

| State | Meaning |
|---|---|
| Action Now | A current actionable trading trigger exists |
| Improving | Trading evidence is strengthening |
| Weakening | Trading evidence or support is deteriorating |
| Monitor | No current trigger; continue monitoring |

## Maintenance states

| State | Meaning |
|---|---|
| Data Needs Refresh | Analysis is stale and should be refreshed |
| Partial Data | Some required analysis is missing |
| Unavailable | No usable analytical record exists |

Trading and maintenance classifications are independent. Staleness alone never creates Action Now and never replaces a valid trading state. Partial/unavailable records cannot be promoted into Action Now.

## Count authority

`frontend/src/features/watchlist/watchlistCounts.ts` owns `locallySaved`, `displayed`, `eligible`, `analyzed`, `catalystRequested`, `partial`, and `unavailable`. The summary and catalyst panel use the same count object. When backend defaults or a deep link widen the displayed set beyond local saves, the catalyst panel explicitly explains the narrower request scope.

Stocks, sectors, and themes retain the canonical routes and use the same semantic split even when the available evidence differs.

