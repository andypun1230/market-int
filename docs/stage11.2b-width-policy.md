# Stage 11.2B Width Policy

Owner: `frontend/src/architecture/layoutPolicy.ts`.

| Policy | Maximum | Intended consumers |
|---|---:|---|
| `full_width_analytical` | 1440px | Market and Sectors dashboards, heatmaps, rotations, comparisons, wide tables |
| `constrained_analytical` | 1100px | Home, Watchlist, reports, Copilot, analytical detail narratives |
| `constrained_settings` | 800px | More, Settings, About, Data Sources, Privacy, Disclaimer, Profile, recovery states |
| `modal_content` | 760px | Search, entity detail, comparison, report preview, alerts, filters |

`AppScreen` resolves the route policy centrally. Full-width means analytically wide, not unbounded. Chart internals may use fixed plotting geometry or horizontal scrolling; these are registered analytical exceptions, not page-width owners.

New route-level `maxWidth` values in app screens are prohibited by the Stage 11.2B source validator. Component-local icon, label, chart, and table widths are outside this rule.
