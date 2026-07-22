# Stage 5.8 — Report V7 Validation and Evidence Report

## Final classification

**PASS WITH CONDITIONS**

The V7 product path passes its implementation, deterministic selection, evidence, PDF, frontend, fixture, and visual gates. The condition is limited to repository-wide frontend test debt outside Report V7: the project has no canonical `npm test` script, and an exploratory run of all 41 standalone scripts exposed existing failures in macro-analysis and sector-normalizer expectations plus raw `tsx` incompatibility in React Native-dependent scripts. V7 TypeScript, Expo lint, report tests, and the full 264-test backend suite pass.

Known upstream data limitations remain explicit and do not block honest V7 output: canonical group-volume history, direct yield/credit/volatility series, authoritative catalysts/events, validated supplier/customer relationships, and long version-consistent rank/breadth histories are not available.

## Architecture delivered

Report generation now freezes saved research preferences with the market snapshots, includes a personalization hash in immutable report identity, builds deterministic sector/theme/individual-security candidates, applies fixed score and evidence gates, registers all selection numbers as evidence, writes an optional primary/secondary research package, and serializes one `ReportDocument` for both PDF and frontend preview.

New reports use `daily-report-v23` and `daily-report-pdf-v7`. V5 still uses its original renderer. V6 still uses the document renderer and can rebuild an old V6 record without relabeling it V7.

## Files created

- `backend/app/reports/research.py`
- `backend/app/reports/pdf_v7.py`
- `backend/tests/fixtures/report_v7.py`
- `backend/tests/test_report_v7_research.py`
- `backend/scripts/generate_report_v7_samples.py`
- `frontend/src/features/reports/researchPreviewModel.ts`
- `frontend/tests/researchPreviewModel.test.ts`
- `docs/report-v7-spec.md`
- `docs/report-v7-research-selection.md`
- `docs/report-v7-data-gap.md`
- `docs/report-v7-figure-catalog.md`
- `docs/report-v7-validation.md`

## Files modified for V7

- `backend/app/reports/document.py`
- `backend/app/reports/document_builder.py`
- `backend/app/reports/pdf_v6.py`
- `backend/app/services/report.py`
- `backend/app/services/report_intelligence.py`
- `backend/app/api/report.py`
- `backend/app/models/market.py`
- `backend/tests/test_visual_report_pdf.py`
- `backend/tests/test_sector_snapshot.py`
- `frontend/src/services/api.ts`
- `frontend/src/features/reports/useDailyReportLibrary.ts`
- `frontend/src/features/reports/components/DailyBriefingPreview.tsx`
- `frontend/src/features/reports/components/ReportDocumentPreview.tsx`
- `frontend/src/features/reports/components/ReportLandingCard.tsx`
- `frontend/src/types/market.ts`

## Selection algorithm and policy

Dimensions are normalized to 0–100, missing values contribute zero, and weighted contributions sum to the Research Priority Score:

| Dimension | Weight |
| --- | ---: |
| Market significance | 15% |
| Leadership/weakness magnitude | 15% |
| Change or acceleration | 15% |
| Persistence | 10% |
| Breadth confirmation | 10% |
| Volume confirmation | 5% |
| Relative divergence | 10% |
| User relevance | 15% |
| Data completeness | 3% |
| Freshness | 2% |

Primary threshold is 60. Secondary threshold is 65. Separate gates require current/non-stale subject data, at least 60% completeness, two supportable and rendered research figures, and either three qualifying group constituents or one materially changed saved security. Stable tie-breaking uses qualification, score, market-significance contribution, change contribution, then candidate ID.

Personal relevance scores 100 for an exact saved group, three fresh saved members, or a materially changed individual saved security; 60 for one or two fresh saved members or a saved validated parent; and 0 without overlap. Its contribution is capped at 15 points and cannot bypass any evidence gate. Stale overlap scores zero.

## Research Focus, figures, and annotations

The primary package contains subject/classification, score, relevance, rank/change, thesis/counter-thesis, key evidence, seven labeled analytical prose blocks, confirmation/invalidation, affected saved securities, validated taxonomy membership, figure IDs, evidence IDs, and limitations. The rendered focus normally spans four pages in the complete fixtures and contains 667–679 grounded words.

Core research figures are Research Priority Comparison, multi-period subject return profile or individual-security price structure, and a comparable peer-return matrix. Market Evolution requires at least three reliable points. The expanded saved-security section uses the requested 12-column matrix and complete deep dives.

The shared annotation layer supports evidence-linked levels and current markers. Reference lines remain at exact data coordinates while labels are collision-spread within bounds. Stale/unavailable annotations are omitted. Visual QA found and fixed a collision between breakout/resistance labels and recent-high markers by placing the two label families on opposite sides of the plot.

## Taxonomy and evidence governance

Sector, industry, theme, and representative-security chains are generated only from security-master and ThemeSnapshot membership. They explicitly do not assert supply-chain, supplier/customer, capital-flow, or causal relationships.

The evidence registry now includes candidate fields, current/prior values and changes, fixed weights, weighted contributions, materiality threshold, completeness, qualifying-constituent count, supported-figure count, saved-security key levels, and current annotation values. Model validation rejects unknown evidence/source references, stale V7 reference lines, missing selected candidates/figures, and selected focuses with fewer than two figures.

## Frontend integration

The report request carries saved stocks, sectors, and themes from the watchlist store. The compact landing card shows subject, classification, why selected, overlap count, figure count, and partial-data state. The shared document preview supports section navigation, the focus summary, research figures, timeline, saved-security impacts, tables, deep dives, evidence-linked captions, no-focus fallback, partial data, and V6 legacy documents without separate research prose.

## Automated validation

- Backend compileall: pass.
- Full backend discovery: **264 tests passed**.
- Final report-specific suite: **22 tests passed** across V7 research, V6 document behavior, and visual-report generation.
- All 16 required V7 fixtures build and validate.
- Frontend `npx tsc --noEmit`: pass.
- Frontend `expo lint`: pass.
- Report frontend scripts: `reportLibraryModel`, `dailyBriefingModel`, and `researchPreviewModel`: pass.
- V5 PDF rendering: pass.
- V6 document rendering and V6 no-document regeneration label: pass.
- Determinism, ties, positive/negative scoring, relevance cap, stale gating, no forced selection, evidence registry, exact levels, annotation spacing/bounds, taxonomy language, timeline omission, and no-focus fallback: pass.

## Final visual validation

Seven PDFs were rendered page-by-page at 190 DPI. All **109 pages** were inspected through final contact sheets, with full-page checks for the methodology appendix, mixed-source cover, security annotations, focus prose continuity, and the laggard appendix. Automated text extraction found no blank page; the least-dense page still contained 87 words. No clipped labels, orphan headings/disclaimers, blank pages, or detached captions remain.

| Sample | Selection | Pages | Figures | Grounded words | Focus words | Focus figures |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Personalized leading theme | Cybersecurity · Leading · 74.42 | 17 | 14 | 4,138 | 667 | 3 |
| Personalized weakening theme | Memory & Storage · Weakening · 83.55 | 17 | 14 | 4,341 | 679 | 3 |
| Market-led, no saved overlap | Cybersecurity · Leading · 63.46 | 14 | 11 | 3,569 | 667 | 3 |
| Explicit lagging sector | Information Technology · Lagging · 88.34 | 17 | 14 | 4,162 | 673 | 3 |
| No qualifying focus | None | 10 | 8 | 1,899 | 0 | 0 |
| Weekend | Cybersecurity · Leading · 74.42 | 17 | 14 | 4,138 | 667 | 3 |
| Mixed source | Cybersecurity · Leading · 74.42 | 17 | 14 | 4,138 | 667 | 3 |

The complete fixture reports meet the 16–22 page and 3,500–6,000 word targets. Their 11–14 figure counts are below the aspirational 20–30 range because the frozen fixtures intentionally lack qualifying breadth, direct macro, and longer historical series; the specification permits shorter output and prohibits padding.

## Omitted capabilities and data gaps

- No canonical group-level volume history; the dimension is zero when absent.
- No validated direct yield curve, credit spread, VIX term structure, or authoritative event/catalyst source.
- No validated supply-chain, supplier/customer, or direct capital-flow dataset.
- No industry-group/security-cluster candidate snapshot contract yet.
- No dedicated market-divergence/cross-asset-divergence candidate contract yet.
- Rank, breadth, participation, and concentration histories can be too shallow for historical figures.
- No portfolio ownership, cost basis, quantity, or personalized advice model.

These gaps are visible in score breakdowns and limitations and never replaced with invented data.
