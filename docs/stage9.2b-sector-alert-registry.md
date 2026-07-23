# Stage 9.2B — Sector Alert Registry

Endpoint: `GET /market/groups/sector-alerts`  
Owner: `backend/app/group_intelligence.py::build_sector_alerts`  
Version: `sector-alerts-v1`

| Type | Group | Source |
|---|---|---|
| `entered_leading` | leadership | canonical state transition into Leading |
| `exited_leading` | leadership | canonical state transition into Weakening/Lagging |
| `entered_improving` | leadership | canonical state transition into Improving |
| `breadth_deterioration` | breadth | price/breadth, A/D, or highs/lows deterioration |
| `momentum_reversal` | momentum | fading rotation or neutral reversal |
| `relative_strength_breakout` | momentum | relative strength >5 with rank improvement ≥2 |
| `persistence_loss` | risk | rank improvement lacks two-snapshot persistence |
| `rotation_acceleration` | momentum | positive breadth/rotation confirmation |
| `concentration_warning` | risk | concentrated leadership rule (additional governed type) |

Alerts are grouped by leadership, momentum, breadth, and risk; sorted by severity then stable identity; and deduplicated by stable ID. Sector Alerts renders typed cards through the shared `AlertList`, never raw JSON. Selecting a card opens an evidence drill-down, and its only exit opens the canonical Sector detail destination.

No-alert is an explicit empty state. Insufficient history does not create transition or divergence alerts.
