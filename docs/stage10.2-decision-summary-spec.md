# Stage 10.2 Decision-Summary Specification

## Contract and owner

`frontend/src/features/trust/decisionSummary.ts` defines the structural contract. Existing domain presenters/services own all financial wording and values; the shared layer only validates and presents them. `DecisionSummaryCard` owns presentation, disclosure, accessibility labelling, and measured-width responsive stacking.

Structural order:

1. current state
2. what changed
3. preferred posture/action
4. main risk
5. invalidation
6. optional “what would change this view”
7. freshness, confidence, and availability
8. evidence/methodology disclosure

The contract supports partial, stale, cached, unavailable, and conflicting evidence. Null domain fields stay absent rather than being invented. Technical provenance and evidence-class limitations live in disclosure. The card does not imply personalized advice.

## Applied surfaces

Home, Market Overview, Market Health, Breadth, Decision, Institutions, Macro, Sector Detail, Theme Detail, Stock Overview, Watchlist Summary, and Report preview/summary.

## Accessibility and responsive behavior

The primary content has a complete accessible state label. Optional navigation is a separate button from the evidence disclosure—nested interactive controls are prohibited. At narrow measured widths, header badges and evidence fields stack vertically with full-width values.

