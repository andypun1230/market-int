# Stage 9.2A Settings Consumer Registry

Runtime owner: `frontend/src/architecture/settingsConsumerRegistry.ts`.

| Persisted preference | Owner | Downstream consumers | Status |
|---|---|---|---|
| `appearance.theme` | Appearance | Root Expo Router `ThemeProvider` | Active |
| `appearance.reduceMotion` | Appearance / Accessibility | `AppScreen` transitions; `AnimatedSplashOverlay` | Active |
| `profile.displayName` | Profile | More profile-destination summary | Active |

## Retired inert controls

The following values were storage-only and had no runtime consumer: accent color, text size, region, market-time display, currency, refresh cadence, low-data mode, Wi-Fi-only mode, background refresh, automatic chart/report download, push-alert preferences, investor style, experience level, report focus, default market, and preferred watchlist.

They were removed from the active preference schema and controls. Migration to schema version 2 whitelists only active keys, so legacy inert values cannot survive invisibly.

Operational cache status and cache clearing remain on Data Usage because they call the backend directly. Notifications remains reachable but truthfully reports that delivery is unavailable; it persists no false-active preference.
