# Stage 11.2C Terminology Registry

## Owner

`frontend/src/architecture/terminologyRegistry.ts`

## Canonical availability

- Live
- Live with cached data
- Available
- Partial
- Stale
- Unavailable
- Failed

## Canonical empty states

- No saved stocks
- No saved sectors
- No saved themes
- No matching results
- No alerts
- Report not generated

## Canonical actions

- Generate report
- Refresh
- Retry
- View details
- Compare
- Save
- Remove
- Clear
- Reset filters

State adapters map raw enums into this registry before presentation. Provider names retain canonical capitalization, confidence uses `value/100 confidence`, and helper copy uses concise sentence case.

Documented exceptions: diagnostics may use `N/A` for an individual missing metric, and the frozen Stage 11.2B unmatched-route action remains “Return Home.”
