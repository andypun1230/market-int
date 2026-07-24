# Stage 12.2 Bundle Optimization Report

## Outcome

Production-web route splitting reduced Home initial JavaScript gzip from 908,888 B to 587,699 B, a 35.34% reduction. Route-specific screens are deferred until navigation while paths and native routing behavior remain unchanged.

## Before and after

| Metric | Stage 12.1 | Stage 12.2 | Change | Result |
|---|---:|---:|---:|---|
| Home initial JS gzip | 908,888 B | 587,699 B | -35.34% | PASS |
| Home unused JS | 60.49% | 41.52% | -18.97 pp | improved |
| Exported JS files | 1 primary bundle | 24 JS files | route split | expected |
| Total all-route JS raw | 3,594,000 B approx. | 3,605,105 B | small split overhead | acceptable |
| Total all-route JS gzip | 912 KB approx. | 931,780 B | small split overhead | acceptable |

The total all-route bundle is slightly larger because independent chunks carry normal packaging overhead. The user-visible improvement is lower initial-route transfer and parse cost; route chunks are fetched only when needed.

## Deferred route chunks

Representative raw route chunks from the production export:

| Route | Deferred raw JavaScript |
|---|---:|
| Market | 383 KB |
| Watchlist | 352 KB |
| Sectors | 247 KB |
| Reports | 133 KB |
| Copilot | 70 KB |

## Contract and platform safeguards

- Async routes are enabled for production web through the supported Expo Router plugin configuration.
- The native route hierarchy and route names are unchanged.
- No screen, capability, font, icon, or image was removed.
- Route-open measurements show no material regression: Reports is 339 ms p50 (+12 ms from baseline) and Copilot is 237 ms p50.
- The 25-route production export completes successfully.

## Remaining opportunities

- Use a native bundle analyzer before changing shared imports; web chunks alone do not prove native startup savings.
- Treat the remaining 41.52% Home unused-code estimate as directional because Lighthouse coverage includes shared runtime code.
- Avoid duplicating shared dependencies across new route chunks; assess total-route gzip and initial-route gzip together.

