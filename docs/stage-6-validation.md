# Stage 6 Research Intelligence Validation

## Release decision

**PASS — Stage 6 is complete for the Report V7 research-intelligence scope.**

The implementation preserves the twelve-section V7 architecture and adds question-led research, evidence quality, a typed relationship engine, Research Chain and continuity graphics, an Evidence Matrix, a ten-report timeline, evidence-linked annotations, and selected-security mini reports. No-focus, weekend, mixed-source, and personalized fallbacks remain explicit and evidence bounded.

The release decision carries one repository-level note: four pre-existing standalone frontend scripts outside the report feature remain red. This is the same debt recorded in `docs/report-v7-validation.md`; the canonical TypeScript, lint, data-contract, report-feature, and backend gates are green.

## Final reference artifacts

All PDFs were generated through the V7 entry point from their serialized `report-document-v2` JSON, rendered at 190 DPI, and reviewed page by page.

| Required case | Focus result | Pages actual / estimate | Figures | Graph edges | Selected securities | Verdict |
| --- | --- | ---: | ---: | ---: | --- | --- |
| Leading Theme | Cybersecurity · Leading | 15 / 15 | 13 | 7 | None | PASS |
| Lagging Theme | Memory & Storage · Lagging | 15 / 15 | 13 | 7 | None | PASS |
| No Focus | Explicit no-focus inquiry | 12 / 12 | 9 | 0 | None | PASS |
| Weekend | Cybersecurity · Leading | 19 / 19 | 16 | 10 | CRWD, PANW, FTNT | PASS |
| Mixed | Cybersecurity · Leading | 19 / 19 | 16 | 10 | CRWD, PANW, FTNT | PASS |
| Personalized | Cybersecurity · Leading | 19 / 19 | 16 | 10 | CRWD, PANW, FTNT | PASS |

The machine-readable manifest is `output/pdf/stage-6/stage-6-sample-manifest.json`. It records artifact paths, page counts, figure counts, focus status, evidence quality, graph topology, timeline coverage, and selected-security coverage for every case.

## Functional validation

Validated behavior includes:

- all twelve sections retain their V7 order and begin with a question;
- section 6 always contains a qualified inquiry or an explicit no-focus answer;
- fixed V7 weights and qualification gates remain unchanged;
- breadth and distinct participation remain separate evidence dimensions;
- missing evidence remains neutral or omitted and never becomes confirmation;
- every focus includes an executive answer, supporting and counter evidence, Evidence Quality, Evidence Matrix, relationships, leaders, laggards, execution implications, and a conclusion-change rule;
- relationship graphs use only registered benchmark, hierarchy, taxonomy, membership, saved-overlap, or fully validated structured edges;
- every relationship edge references registered evidence, and every rendered edge has a visible arrowhead;
- supply-chain edges are absent unless the structured-data gate is satisfied;
- ten compatible report observations populate the Research Timeline without synthesized dates or fields;
- prior focus may come only from an explicit compatible historical `researchFocus` field, never from prose;
- weekend output retains the latest durable market observation and does not imply a new trading session;
- chart annotations are supported, evidence linked, in range, and non-future;
- no speculative future arrows, projected price paths, unsupported chart fallbacks, or fabricated levels appear;
- selected-security coverage is limited to deterministic fresh candidates and keeps entry eligibility separate from group research priority;
- CRWD, PANW, and FTNT use distinct histories, setup states, relative-strength values, volume conditions, confirmation levels, and invalidation levels;
- the frontend preview consumes the same Stage 6 document contract and supports the Stage 6 figure aliases.

## Automated checks

| Check | Result |
| --- | --- |
| Full backend discovery, `python -m unittest discover -s tests` | PASS — 284 tests |
| Final Stage 6 and visual-PDF subset | PASS — 21 tests |
| Broader report-focused backend subset | PASS — 42 tests |
| Frontend `npx tsc --noEmit` | PASS |
| Frontend `npm run lint` | PASS |
| Frontend `npm run validate:data-ui` | PASS |
| Report preview/library standalone scripts | PASS — 3 of 3 |
| All standalone frontend scripts | 37 of 41 pass; four inherited non-report failures listed below |
| Sample manifest actual-versus-estimated page counts | PASS — 6 of 6 exact |
| Serialized source, question, and annotation integrity audit | PASS — 6 of 6 |
| Extracted-page blank/near-blank audit | PASS — all 99 pages |
| Figure-number continuity audit | PASS — 1–13 or 1–16 as applicable |
| Stage 6 file trailing-whitespace scan | PASS |

The four inherited standalone-script failures are:

- `macroAnalysis.test.ts`: existing inflation-scenario expectation;
- `sectorDashboardNormalizers.test.ts`: existing nested-payload expectation;
- `sectorAnalysisFeatures.test.ts`: raw `tsx` cannot transform the React Native entry point;
- `watchlistStore.test.ts`: the same raw `tsx` React Native transform limitation.

None imports or exercises the Stage 6 report builder, document model, PDF renderer, sample generator, research preview model, or report library model. The project does not define a canonical `npm test` script; its canonical frontend gates pass.

## Visual review

All 99 final 190-DPI page renders were reviewed through the six contact sheets and page-level inspections. The final review specifically checked:

- complete rotation labels without collisions or ellipses;
- readable negative relative-strength bars and labels;
- all declared Research Chain nodes, typed edges, and arrowheads;
- Evidence Matrix stance readability;
- distinct Yesterday, Today, Next test, Execution, and Change conclusion content;
- ten timeline cells with readable regime, breadth, risk, volatility, focus, and leader/laggard fields;
- selected-security headings, charts, source timestamps, setup annotations, and non-duplicated `Current thesis` labels;
- acceptable density on the enlarged relative-strength, risk-history, scenario, and operating-plan pages;
- no clipping, overlap, orphan headings, duplicated conclusion blocks, missing footers, or blank pages.

The scenario page intentionally retains some lower-page breathing room after the complete conditional-path table. Adding another graphic forced the empty-watchlist state onto a separate page, so it was rejected as length without incremental research value.

## Data limitations retained by design

Stage 6 does not manufacture unavailable group-volume history, direct rates or credit spreads, volatility term structure, supplier/customer mappings, causal transmission, portfolio holdings, catalysts, or future price paths. Partial source coverage is disclosed in each report and is catalogued in `docs/stage-6-data-gap.md`.

## Reproduction

From `backend/`:

```bash
venv/bin/python scripts/generate_stage6_samples.py
venv/bin/python -m unittest discover -s tests
```

From `frontend/`:

```bash
npx tsc --noEmit
npm run lint
npm run validate:data-ui
npx tsx tests/researchPreviewModel.test.ts
npx tsx tests/reportLibraryModel.test.ts
npx tsx tests/dailyBriefingModel.test.ts
```

