# Stage 10.2 User-Facing Data-State Specification

## Authority

`frontend/src/features/trust/userFacingDataState.ts` is the single presentation authority. `UserFacingDataStateProvider` resolves provider/test status once at the app root; screens consume the resulting contract through `DataStateSummary`. Provider state takes precedence over the mere presence of scenario controls.

## Contract

Every result supplies `state`, `headline`, `explanation`, `providerSummary`, `freshness`, `availabilitySummary`, `limitations`, `recommendedAction`, `provenance`, diagnostic `technicalDetail`, and machine-readable `reasonCodes`.

| State | Required meaning | Default headline |
|---|---|---|
| `live` | Verified quote and history routes are ready | Live market data |
| `live_cached` | A retained successful live response is shown | Live source unavailable; showing cached data |
| `partial` | Some live domains are usable and others are limited | Live data partially available |
| `scenario` | A selected deterministic scenario drives outputs | Scenario data active |
| `test` | Generated/test data drives outputs | Test data active |
| `stale` | Data is outside its active freshness window | Market data is stale |
| `unavailable` | No verified usable provider state | Live market data unavailable |
| `failed` | Status lookup itself failed | Data status check failed |
| `loading` | Status lookup is unresolved | Checking data source |

`partial` is never collapsed into unavailable. `live_cached` is never labelled live without qualification. Scenario controls are described separately from current provider state. Raw enums are restricted to diagnostic detail.

## Consumers

The shared summary is mounted for Home, Market, Sectors (including modal Sector and Theme detail), Watchlist, More, Reports, Copilot, Settings, About, and Data Sources. Stock detail inherits the shared root/screen authority through its canonical route shell. Diagnostic surfaces may add reason codes and configured mode, but cannot change the plain-language headline.

## Freshness

`formatFreshness` owns relative wording: “Updated just now”, “Updated N minutes ago”, “Data is N hours old”, and “Last successful update yesterday/N days ago”. Invalid or absent dates remain “Last update unavailable”.

## Invariants

- Same inputs produce identical plain-language output for every consumer.
- Test controls do not downgrade an active live provider.
- Provider mismatch is resolved by capability/health evidence, not screen-local copy.
- Unavailable values are never represented as zero.
- Diagnostic wording cannot contradict the shared headline.

