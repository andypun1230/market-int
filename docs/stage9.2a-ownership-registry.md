# Stage 9.2A Ownership Registry

This registry is enforced in `frontend/src/architecture/ownershipRegistry.ts`. An output key may occur once only; consumers may project it but must not redefine its conclusion.

| Output | Authoritative owner | Inputs | Consumers | Contract |
|---|---|---|---|---|
| `market.snapshot` | Backend `MarketSnapshot` service | Provider histories; Breadth/Sector/Theme snapshots | Home; Market; Copilot; Report | Canonical current-market evidence bundle |
| `market.decision` | Backend decision-summary service | `market.snapshot` | Home; Market Decision; Market Overview; Report | Canonical posture, playbook, risk, aggressiveness |
| `market.health` | Backend market-health engine | `market.snapshot` | Home; Market Health; Report; Copilot | Canonical health score and component conclusions |
| `market.breadth` | Backend `BreadthSnapshot` service | Market histories | Home; Market Breadth; Report; Copilot | Canonical breadth state and evidence |
| `home.market_posture.presentation` | `marketPostureProjection` | Health; breadth; decision | `homeSummary` | Single owner of the existing Home posture thresholds |
| `home.summary.presentation` | `homeSummary` | Market snapshot; decision; watchlist snapshot | Home | Presentation projection only |
| `market.overview.presentation` | `marketOverviewAnalysis` | Market snapshot; decision | Market Overview | Cross-market presentation; cannot replace decision truth |
| `sector.snapshot` | Backend `SectorSnapshot` service | Security histories; breadth | Sectors; Watchlist; Report; Copilot | Ranking, classification, metrics, alerts |
| `sector.rotation` | Backend sector-rotation engine | Sector ETF histories | Sector Rotation | Coordinates, trails, movement |
| `theme.snapshot` | Backend `ThemeSnapshot` service | Governed definitions; histories | Themes; Watchlist; Report; Copilot | Ranking, classification, metrics, alerts |
| `theme.rotation` | Backend theme-rotation engine | Theme basket histories | Theme Rotation | Coordinates, trails, movement |
| `stock.snapshot` | Backend `StockAnalysisSnapshot` service | Security histories; group context | Stock Detail; Watchlist; Report; Copilot | Stock evidence and conclusions |
| `watchlist.classification` | `watchlistClassifier` | Stock snapshots | Watchlist | Saved-stock UI classification |
| `watchlist.decision` | `watchlistDecision` | Watchlist classifications | Watchlist Summary | Watchlist-level projection |
| `report.document` | Backend report-document builder | Versioned snapshots | Report; Copilot | Immutable report and lineage |
| `context.news` | Backend news-intelligence service | Normalized source events | Context cards; Copilot | Material-event interpretation |
| `context.session` | Backend session-narrative service | Session evidence | Market; Copilot | Canonical session narrative |

## Enforcement

- `duplicateIntelligenceOutputs()` fails the architecture test if two owners claim the same output.
- Home posture thresholds moved unchanged from the screen summary into `marketPostureProjection`.
- Canonical sector scanner qualification moved from the route into `analysis/scanners.ts`.
- Search and alert adapters present canonical snapshot outputs and do not calculate replacement intelligence.
