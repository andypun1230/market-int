# Stage 11.2A Confidence and Freshness Standard

## Result

**PASS**

Presentation ownership is split cleanly between a pure formatter and shared UI:

- `confidenceFreshnessPresentation.ts`: authoritative wording and casing
- `ConfidenceFreshness.tsx`: shared rendered freshness presentation
- `DecisionSummaryCard`: canonical decision-summary placement
- `DataStateSummary`: canonical data-state placement
- `ConfidenceIndicator`: canonical score/provider presentation

## Wording contract

| Data | Standard output |
|---|---|
| Numeric confidence | `N/100 confidence` |
| Evidence confidence | `N/100 evidence confidence` |
| Evidence quality | `N/100 evidence quality` |
| Missing confidence | `Confidence unavailable` |
| Timestamp | `Updated <localized medium date/time>` |
| Missing timestamp | `Last update unavailable` |
| Provider | Canonical product casing, including `Finnhub`, `Polygon`, and `OpenAI` |
| Availability enum | Title-cased words, such as `Partial Data` |
| Evidence source state | `Live evidence`, `Cached evidence`, `Stale evidence`, `Test evidence`, `Partial evidence`, `Delayed evidence`, or `Evidence unavailable` |

## Placement contract

- Confidence and availability remain beside the primary decision state.
- Freshness remains below decision content, before methodology/evidence disclosure.
- Data-state freshness remains in the shared data-state header row.
- Provider identity remains within evidence/source context; it is not promoted above the decision.

## Preserved boundaries

No confidence value, freshness threshold, evidence classification, availability calculation, report content, or provider selection changed. Report-specific qualitative confidence labels and relative-age logic remain domain outputs because changing them would change report/business content; shared components normalize how those outputs are displayed.

The focused contract test covers numeric rounding, qualifier preservation, missing-data wording, availability casing, provider casing, and evidence-freshness wording.
