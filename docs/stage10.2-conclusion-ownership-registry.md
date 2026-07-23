# Stage 10.2 Conclusion Ownership Registry

## New structural owners

| Output | Single owner | Consumers |
|---|---|---|
| User-facing provider state and wording | `trust/userFacingDataState.ts` | all relevant screens |
| Evidence-class aggregation/conflict | `trust/evidenceClasses.ts` | domain presenters and summaries |
| Atomic analytical state | `trust/atomicScreenState.ts` | async hooks and analytical screens |
| Decision-summary structure | `trust/decisionSummary.ts` | shared card and domain adapters |
| Watchlist maintenance classification | `watchlistClassifier.ts` | Watchlist summary/list |
| Watchlist count reconciliation | `watchlistCounts.ts` | Watchlist summary/catalysts |

## Before/after duplicate registry

| Domain | Authoritative primary conclusion | Demoted/removed surface | Classification after |
|---|---|---|---|
| Home | Home decision summary | former Market Pulse conclusion card | obsolete duplicate removed |
| Market Overview | Market decision summary | regime hero/posture repetition | supporting snapshot/signals retained |
| Market Health | Market health decision summary | health overview/decision-layer repetition | supporting breakdown, drivers and contributions retained |
| Breadth | Breadth decision summary | separate takeaway conclusion | breadth measures retained as evidence |
| Macro | Macro decision summary | repeated regime overview conclusion | assets and interpretation retained |
| Decision | Decision summary | repeated playbook conclusion | scenarios and changes retained |
| Institutions | Institutional decision summary | unsupported overall directional headline | price-volume evidence retained; direct classes separated |
| Sector Detail | Sector decision summary | legacy Breadth History/no-history branch | one published Breadth History retained |
| Theme Detail | Theme decision summary | repeated status interpretation | performance/evidence retained |
| Stock Overview | Stock decision summary | grade/score/posture dashboard repetition | trade plan and evidence retained |
| Watchlist | Watchlist decision summary | brief/priority conclusion overlap | item groups remain execution detail |
| Reports | Report decision summary | none; report document unchanged | preview context only |

The machine-readable companion is `frontend/src/architecture/conclusionOwnershipRegistry.ts`; architecture tests reject duplicate owner IDs and duplicate screen summary ownership.

