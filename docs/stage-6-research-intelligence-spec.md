# Stage 6 Research Intelligence Specification

## Product contract

Stage 6 turns Report V7 into a question-led research product without redesigning Report V7. The section sequence, immutable report input, evidence registry, candidate-selection policy, storage path, and PDF format remain the V7 architecture. Stage 6 adds research depth, typed relationships, evidence classification, continuity, annotated charts, and selected-security mini reports to that architecture.

The governing rule is: explain why the observed evidence matters and what would change the conclusion. Stage 6 does not add pages to meet a length target, invent a subject when none qualifies, or turn missing data into narrative confidence.

The serialized `ReportDocument` remains authoritative for the PDF and frontend preview. Renderers present its questions, answers, evidence, diagrams, and limitations; they do not select a different focus or regenerate analytical claims.

## Architecture invariants

Every newly built Stage 6 document retains all twelve V7 sections in this order:

1. Cover and Current Thesis
2. Executive Summary
3. Major Index Structure
4. Breadth and Participation
5. Leadership and Rotation
6. Research Question
7. Cross-Asset and Macro Confirmation
8. Risk, Volatility, Credit and Sentiment
9. Scenario Framework and Events
10. Personalized Watchlist and Security Research
11. Next-Session Operating Plan
12. Methodology, Sources and Limitations

Each section has a question ending in `?`. Section 6 is always present. It contains either a qualified Research Focus or an explicit no-focus inquiry; it is never silently removed or filled with a substitute topic.

Stage 6 does not change the fixed V7 research weights, materiality thresholds, completeness gate, constituent gate, figure-readiness gate, freshness policy, or deterministic tie-breaking. Positive and negative candidates continue to use the same selection policy.

## Versioning and compatibility

Stage 6 is an additive document-contract revision, not a new PDF architecture:

| Layer | Stage 6 value | Compatibility behavior |
| --- | --- | --- |
| Report schema | `daily-report-v23` | Existing report creation and immutable identity remain in place. |
| PDF format | `daily-report-pdf-v7` | V7 dispatch is preserved. The V7 entry point selects the Stage 6 composition path. |
| Document contract | `report-document-v2` | New documents require Stage 6 questions and inquiry state. Older `report-document-v1` JSON remains parseable through optional additive fields. |

`backend/app/reports/pdf_v7.py` invokes the shared ReportLab renderer with Stage 6 composition enabled. The V6 entry point retains its established composition path. This isolates the new page composition while continuing to share figure, style, and document primitives.

## Processing flow

1. The report service freezes market, breadth, sector, theme, watchlist, stock-chart, taxonomy, personalization, and compatible prior-report inputs.
2. `ResearchCandidateEngine` constructs and ranks candidates without provider calls or language-model topic selection.
3. `DocumentBuilder` registers exact evidence, creates the research inquiry, builds a qualified focus or no-focus state, adds continuity, relationships, figures, and selected-security research, then emits `report-document-v2`.
4. Model validation rejects unknown evidence references, invalid graph edges, unsupported Stage 6 annotations, out-of-range annotation points, and annotations after a figure's as-of date.
5. The PDF and frontend render the same stored document.
6. After the document is built, the selected focus subject, or `null` for no focus, is persisted into the current report-history snapshot for future continuity.

No stage in this flow may fetch a replacement subject, infer a catalyst, or fill a missing relationship.

## Research inquiry contract

Every Stage 6 document includes `research_inquiry`:

- `status`: `qualified` or `no_focus`;
- `question`: a material question ending in `?`;
- `executive_answer`: the direct answer or the reason coverage was withheld;
- `evidence_ids`: exact references into the document evidence registry.

A qualified focus repeats the same question and executive answer inside `research_focus`, so a consumer can render the focus independently without reconstructing the inquiry.

Question construction is deterministic and direction-aware. Examples of implemented patterns include:

- leading or emerging group: why is the subject leading, and is participation broad enough to persist;
- leading group with narrow breadth: why is it outperforming despite narrow breadth;
- weakening, lagging, or breakdown subject: is the weakness temporary or structural;
- divergence: why is the subject diverging from its benchmark and peers;
- individual security: why a supported status change deserves standalone research.

## Qualified Research Focus

A qualified `research_focus` contains the established V7 selection audit plus the following Stage 6 structures:

1. Question
2. Executive answer
3. Evidence and explicit counter-thesis
4. Evidence matrix
5. Research figures
6. Typed relationship graph
7. Relative leading securities
8. Relative lagging securities
9. Execution implications
10. Conditions that change the conclusion
11. Research evolution from the previous compatible report to the next evidence test

The document validator requires a question, non-empty executive answer, evidence quality, non-empty evidence matrix, relationship graph, execution implications, conclusion-change conditions, and research evolution whenever a focus exists. Every structured evidence row, graph edge, security signal, quality assessment, and continuity object must reference known evidence.

The concise prose remains conditional. It distinguishes observation, interpretation, counter-evidence, execution, confirmation, and invalidation; it does not duplicate the selected-security mini reports.

## Evidence Quality

`ResearchEvidenceQuality` is a categorical evidence assessment, not a forecast probability and not an estimate of investment success. It reports `High`, `Medium`, or `Low` for:

- freshness;
- breadth;
- distinct participation;
- completeness;
- directional consistency.

For each component, a missing or sub-45 normalized reading is `Low`, 45 through below 75 is `Medium`, and 75 or above is `High`. The overall label is `High` when at least four components are high and none is low, `Low` when at least two components are low, and `Medium` otherwise.

Direction matters. A low constituent-participation value can confirm a lagging thesis but contradict a leading thesis. Consistency tests agreement across supported 1W, 1M, and 3M returns, benchmark-relative performance for group candidates, breadth, and distinct participation. Missing observations remain missing and therefore cannot improve the grade.

The label must never be rendered as a percentage, likelihood, confidence interval, price target, or probability of the thesis being correct.

## Evidence Matrix

The evidence matrix converts major thesis dimensions into one of three stances:

- `supports`: normalized directional score of at least 60;
- `neutral`: missing evidence or a score from 40 through below 60;
- `contradicts`: normalized directional score below 40.

Implemented rows cover relative performance, persistence, breadth, change and acceleration, volume participation, and user relevance. Every row includes a finding, implication, and one or more evidence IDs. Missing group-volume evidence is neutral and contributes zero to the Research Priority Score. User relevance is neutral to the market thesis: it changes review priority, not the underlying market conclusion.

## Research figures

Stage 6 supplies explicit renderers for its research graphics rather than treating unknown chart types as generic line charts:

| Figure | Question answered |
| --- | --- |
| Research Priority Tree | Why did the subject outrank other candidates, or why did none qualify? |
| Relative Strength Flow | Is the direction recent, persistent, and distinct from the benchmark? |
| Research Chain | How do validated benchmark, hierarchy, membership, and saved-list links connect? |
| Evidence Matrix | Which evidence supports, is neutral to, or contradicts the answer? |
| Research Evolution and Decision Framework | What changed, what is next, and what changes the conclusion? |
| Research Timeline | How did regime, breadth, leadership, risk, volatility, and focus evolve across compatible reports? |

Group focuses receive a relative-strength flow when at least two supported horizons exist. Individual-security price structure is rendered once in the selected-security mini report, not duplicated inside Research Focus. An unknown Stage 6 chart type is surfaced as unsupported instead of being silently misrepresented.

## Knowledge continuity

`ResearchEvolution` records:

- the previous compatible report date;
- yesterday's supported state or a clear baseline statement;
- today's evidence state;
- the next evidence test, not a price forecast;
- supported changes in rank, relative strength, and breadth;
- previous and current focus;
- `New baseline`, `Follow-up`, or `Focus changed` status;
- the follow-up rule for the next compatible snapshot.

Weekend and holiday reports do not imply a new market observation. They retain the latest durable session evidence and label the current state accordingly.

The market timeline uses up to the last ten compatible, dated report observations and tracks regime, market health, breadth, leadership concentration when present, risk, volatility state, primary leader, primary laggard, and Research Focus. At least three observations are required. Missing fields and missing earlier reports remain blank; no history is backfilled or inferred.

## No-focus behavior

No focus is a first-class research conclusion. When no candidate clears every required gate:

- section 6 remains in the document;
- `research_inquiry.status` is `no_focus`;
- the question asks why no reviewed subject met the evidence threshold;
- the executive answer names the highest-ranked candidate and principal failed gates when available;
- a Research Priority Tree displays reviewed candidates and the materiality gate when candidate evidence exists;
- no `research_focus`, relationship chain, leader/laggard list, or execution recommendation is fabricated;
- the current history snapshot records no selected focus.

A candidate that clears the score threshold but cannot support at least two substantial figures is also withdrawn into the no-focus state.

## Annotated chart contract

Stage 6 supports evidence-linked annotations for support, resistance, breakout, failed breakout, gap, pivot, EMA, trendline, previous report, current thesis, risk, confirmation, and invalidation. Stored V7 documents may also retain the documented pre-Stage-6 annotation names in the compatibility allowlist.

Every annotation must:

- use an allowed type;
- reference a known evidence ID;
- point inside observed chart history when it has a point index;
- occur on or before the figure as-of date when it has a date;
- use current, supported observations rather than a speculative projection.

Annotation types containing `future` are rejected. No speculative future arrow, projected path, or unsupported hand-drawn level is permitted.

## Selected-security research

Broad watchlist triage remains compact. A deterministic priority rule selects at most four fresh securities for full Stage 6 mini reports. Focus-linked names rank first, followed by material price change, supported setup/risk signals, and distance of the stock score from neutral. Stale or unavailable securities are not selected for a deep dive.

Each selected security carries, when supported:

- why it is included;
- current setup and context;
- sector and theme membership;
- relative strength and trend;
- volume condition;
- supported confirmation and invalidation levels;
- risk considerations;
- change since the compatible prior report;
- execution consideration;
- a single frozen price/volume chart with evidence-linked annotations.

These are research and monitoring artifacts. They do not infer ownership, exposure, cost basis, or personal suitability, and they do not convert group membership into a trade recommendation.

## Composition and writing rules

The Stage 6 PDF uses question-led headings, content-aware page breaks, deduplicated figures, compact methodology, research diagrams, and paired security cards/charts. Information density is improved by grouping related evidence and replacing repetitive prose with diagrams and matrices, not by reducing legibility.

Writing must be concise, evidence-based, and professional:

- lead with the answer;
- identify counter-evidence and unavailable evidence;
- distinguish observed relationship from cause;
- state execution as a conditional research implication;
- express tomorrow as a test, never a predicted path;
- avoid filler, unsupported catalysts, duplicated conclusions, and AI-style meta-language.

Every page must answer its stated question or provide the evidence needed to answer it.

## Primary implementation surfaces

- `backend/app/reports/document.py`: additive v2 models and integrity validation.
- `backend/app/reports/research.py`: unchanged V7 scoring policy plus distinct participation capture and evidence registration.
- `backend/app/reports/document_builder.py`: inquiry, evidence quality, matrix, relationship graph, continuity, research figures, annotations, and selected-security reports.
- `backend/app/reports/pdf_v7.py`: V7 dispatch into the Stage 6 composition.
- `backend/app/reports/pdf_v6.py`: shared ReportLab primitives with isolated Stage 6 story composition and figure renderers.
- `backend/app/services/report.py`: immutable document build and current-focus history persistence.
- `backend/app/services/report_intelligence.py`: compatible historical metrics, including optional volatility and Research Focus.
- `frontend/src/features/reports/components/ReportDocumentPreview.tsx`: question-led document preview from the shared contract.
- `frontend/src/features/reports/researchPreviewModel.ts`: safe compact focus and no-focus projection.

