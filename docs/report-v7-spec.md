# Report V7 Specification

## Product contract

Report V7 extends the V6 institutional briefing with one optional, dynamically selected Research Focus. It preserves the immutable `ReportDocument`, evidence registry, chart-led report structure, storage model, and V5/V6 compatibility. New reports are versioned `daily-report-v23` and `daily-report-pdf-v7`.

The report and the user's saved research preferences are frozen together. The candidate engine performs no provider calls, has no rotating calendar of topics, and does not fill the section when the evidence gates fail. The serialized `ReportDocument` is authoritative for the PDF and frontend preview; neither surface rebuilds research prose.

The V7 sequence is:

1. Cover and Current Thesis
2. Executive Summary
3. Major Index Structure
4. Breadth and Participation
5. Leadership and Rotation
6. Dynamic Research Focus, when qualified
7. Cross-Asset and Macro Confirmation
8. Risk, Volatility, Credit, and Sentiment
9. Scenario Framework and Events
10. Personalized Watchlist and Security Research
11. Next-Session Operating Plan
12. Methodology, Sources, and Limitations

If no candidate qualifies, section 6 is omitted rather than rendered empty. The Executive Summary includes the exact fallback once: “No standalone research subject met the evidence and materiality threshold for this report.”

## Architecture

- `backend/app/reports/document.py` defines candidates, score breakdowns, selection decisions, saved-security impacts, figure annotations, the primary focus, secondary note, timeline entries, and expanded security research.
- `backend/app/reports/research.py` builds and ranks candidates only from the frozen report payload and a compatible previous-report snapshot.
- `backend/app/reports/document_builder.py` registers evidence, invokes selection, writes conditional research, constructs figures, enriches security deep dives, and produces the shared V7 document.
- `backend/app/reports/pdf_v7.py` validates the V7 format before using the shared document renderer.
- `backend/app/reports/pdf_v6.py` remains the shared ReportLab composition layer and retains the V6 entry point.
- `frontend/src/features/reports/components/ReportDocumentPreview.tsx` renders research sections, figures, saved overlap, timeline, tables, deep dives, and partial states from the shared document.
- `frontend/src/features/reports/researchPreviewModel.ts` supplies the compact landing-card state for V7 focus, no-focus, partial-data, and legacy documents.

Saved stocks, sectors, and themes are normalized before report identity is computed. A personalization hash is part of the immutable identity and cache key, preventing a report generated for one saved universe from being silently reused for another.

## Research Focus contract

A primary focus requires all of the following:

- score at or above 60;
- current, cached, test, mixed, or partial subject evidence, never stale/unavailable subject data;
- at least 60% research-input completeness;
- at least two supported figure types and two rendered research figures;
- at least three qualifying securities for a sector, theme, industry group, or cluster; or one saved security with a major supported status change;
- a supported classification and, for neutral/divergence subjects, material relative divergence.

The selected focus records the subject, category, direction, priority score, user-relevance evidence, thesis and counter-thesis, seven labeled prose blocks, evidence IDs, figure IDs, validated taxonomy membership, affected saved securities, confirmation and invalidation conditions, and explicit limitations. Normal primary prose targets 600–1,200 words. A distinct opposing candidate may become a 200–400 word secondary note only at or above 65, within 15 score points of the primary, and with a different direction.

## Grounding and writing rules

- Fixed score weights, dimension values, weighted contributions, threshold, completeness, rank, change, returns, relative strength, breadth, constituent count, and supported-figure count are registered as evidence.
- Research figures and current annotations reference exact evidence IDs. V7 validation rejects unknown reference-line evidence and stale reference lines.
- Saved-security key levels use the same registered values used in text and charts.
- Missing dimensions contribute zero; they are not imputed or assigned a neutral score.
- Research describes observation, evidence, interpretation, counter-evidence, confirmation, invalidation, and implication. It does not invent a news or fundamental catalyst.
- The report never infers that a saved security is owned and does not turn group evidence into personalized advice.
- A taxonomy chain means validated membership. Supplier/customer, capital-flow, or causal links require a separately validated structured source and are otherwise omitted.

## Research and security figures

Every qualified focus includes Research Priority Comparison plus at least one subject figure. Group candidates normally add a multi-period return profile and peer return matrix. Individual-security candidates use a frozen price-structure figure. Existing V6 figures remain available. The Market Evolution figure is emitted only with at least three reliable observations.

The annotation layer supports evidence-linked support, resistance, breakout, invalidation, moving-average, previous-report, recent-high, recent-low, volume-expansion, relative-strength turning-point, confirmation, and monitoring/risk labels when those inputs exist. Labels are spread inside plot bounds; stale/unavailable annotations are suppressed.

The saved-security matrix has 12 fields: ticker, group, setup, daily change, relative strength, trend, volume, confirmation, invalidation, freshness, research classification, and reason for inclusion. Three to six complete deep dives are preferred to shallow coverage.

## Compatibility

Stored V5 and V6 reports remain readable. PDF dispatch uses the stored `report_pdf_format_version`: V7 uses the V7 validator/renderer, V6 uses the legacy document entry point, and V5 uses the original renderer. Optional V7 fields keep historical JSON valid. The frontend dispatches V6/V7 documents to the shared document preview and leaves V5 on its established fallback.

## Validation targets

Complete reports target roughly 16–22 pages, 20–30 figures, and 3,500–6,000 grounded words, but no content is padded. Shorter output is correct when the frozen input lacks qualifying histories. The six required deterministic samples cover personalized leadership, personalized weakness, market-led selection, no focus, weekend behavior, and mixed sources; an additional lagging-sector sample validates the negative-selection path explicitly. Every page is rendered at 190 DPI and reviewed through contact sheets.
