# Stage 8.75 Theme Intelligence Validation Report

Result: **PASS**

Baseline/tag commit: `534c345fc5a31349a7594e8300eccf5b3bac2d54`; HEAD: `534c345fc5a31349a7594e8300eccf5b3bac2d54`.

Taxonomy version: `2026.07.1` (26 active themes, 227 active mapping records, 3 retired ticker-lineage records).

This report distinguishes the original taxonomy completion, the registry-driven snapshot continuation, and this final provider-backed security-master coverage pass.

The final patch also closes the Theme Rotation integration defect without changing taxonomy, mappings, or governed thresholds.

The Sector follow-on uses `sector-relative-trend-momentum-v1` with exact Theme-kernel parameter parity, 11 eligible sectors, and 286 canonical coordinates across three profiles. The former Sector model remains only in the explicitly named downstream compatibility field.

## Theme Rotation final patch

Root cause: The legacy Theme axes were raw fixed-window entity-minus-SPY returns and the lagged change of those returns, each shifted by 100. Five sparse overlapping-window points had no continuous relative-price trend, smoothing, volatility scaling, or robust normalization, producing straight, abrupt, clustered paths.

Before: **26** endpoints with **5** sparse raw-return tail observations. After: **26** endpoints with canonical profile tails; Smart/All/None labels: **6 / 26 / 0**.

Canonical flow: governed adjusted constituent histories → equal-weight theme index → continuous theme/SPY relative-price line → causal Relative Trend → momentum of Relative Trend → immutable versioned ThemeSnapshot tails → `/market/themes/rotation?profile=…` → model-versioned frontend adapter/hook → Theme Rotation Map.

Point eligibility uses row-level availability, selected-timeframe finite canonical metrics, usable governed confidence, active/live provenance, and evidence references. It does not require complete coverage, high confidence, every timeframe, or label selection.

| Profile | Frequency | Trend EMA fast/slow | Momentum lag/smoothing | Tail | Eligible | Excluded | Leading | Improving | Weakening | Lagging | Common date |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1W | daily | 10/30 | 3/5 | 8 | 26 | 0 | 2 | 5 | 6 | 13 | 2026-07-21 |
| 1M | daily | 20/50 | 5/10 | 10 | 26 | 0 | 5 | 5 | 8 | 8 | 2026-07-21 |
| 3M | weekly_last_complete_session | 10/26 | 4/4 | 8 | 26 | 0 | 4 | 6 | 10 | 6 | 2026-07-17 |

All three timeframes have zero exclusions in the validated snapshot. Six rows retain explicit partial-coverage disclosure and remain eligible under the unchanged 75% gate.

Smart labels render six names on the default 300px card; All renders 26 and None renders zero. The point array remains 26 in every label mode. Quadrant filters derive both point and label counts from filtered candidates and do not mutate cached data.

## Final coverage result

The approved-provider audit covered all **138** baseline-unregistered symbols. It added **132** canonical records and three deterministic aliases. Strict-live refresh inserted **69362** bars, updated **121**, failed **0**, and recorded **0** rate-limit events.

Production-capable: **26/26**; available/ranked: **26/26**; partial: **0**; unavailable: **0**.

## Full 26-theme coverage matrix

| Theme | Mapped | Valid | Registered | Provider | 21d | 50d | 200d | Coverage | Benchmarks | Common date | Status | Coverage status | Confidence | Rank | Missing/unsupported |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|---|---:|---|
| artificial_intelligence | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 100.0% | yes | 2026-07-21 | available | complete | moderate | 14 | none |
| semiconductors | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 100.0% | yes | 2026-07-21 | available | complete | moderate | 21 | none |
| memory_storage | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 100.0% | yes | 2026-07-21 | available | complete | limited | 7 | none |
| data_centers | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 100.0% | yes | 2026-07-22 | available | complete | moderate | 18 | none |
| cloud_computing | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 100.0% | yes | 2026-07-21 | available | complete | moderate | 12 | none |
| enterprise_software | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 100.0% | yes | 2026-07-21 | available | complete | moderate | 8 | none |
| cybersecurity | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 100.0% | yes | 2026-07-21 | available | complete | limited | 1 | none |
| networking_infrastructure | 9 | 8 | 8 | 8 | 8 | 8 | 8 | 88.9% | yes | 2026-07-21 | available | partial | moderate | 24 | JNPR |
| robotics_automation | 9 | 8 | 7 | 8 | 7 | 7 | 7 | 77.8% | yes | 2026-07-21 | available | partial | moderate | 17 | ABB, FANUY |
| digital_advertising | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 100.0% | yes | 2026-07-21 | available | complete | moderate | 10 | none |
| ecommerce | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 100.0% | yes | 2026-07-21 | available | complete | moderate | 4 | none |
| digital_payments | 9 | 9 | 8 | 9 | 8 | 8 | 8 | 88.9% | yes | 2026-07-21 | available | partial | moderate | 3 | ADYEY |
| online_travel | 7 | 6 | 6 | 6 | 6 | 6 | 6 | 85.7% | yes | 2026-07-21 | available | partial | moderate | 5 | DESP |
| gaming_interactive_media | 8 | 8 | 7 | 8 | 7 | 7 | 7 | 87.5% | yes | 2026-07-21 | available | partial | moderate | 6 | NTDOY |
| streaming_digital_entertainment | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 100.0% | yes | 2026-07-21 | available | complete | moderate | 16 | none |
| aerospace_defense | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 100.0% | yes | 2026-07-21 | available | complete | moderate | 19 | none |
| space_economy | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 100.0% | yes | 2026-07-22 | available | complete | moderate | 22 | none |
| drones_autonomous_systems | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 100.0% | yes | 2026-07-21 | available | complete | moderate | 26 | none |
| nuclear_energy | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 100.0% | yes | 2026-07-22 | available | complete | moderate | 23 | none |
| grid_modernization | 9 | 8 | 8 | 8 | 8 | 8 | 8 | 88.9% | yes | 2026-07-21 | available | partial | moderate | 15 | ABB |
| clean_energy | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 100.0% | yes | 2026-07-21 | available | complete | moderate | 25 | none |
| electric_vehicles_batteries | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 100.0% | yes | 2026-07-21 | available | complete | moderate | 13 | none |
| biotechnology | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 100.0% | yes | 2026-07-21 | available | complete | moderate | 11 | none |
| obesity_metabolic_health | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 100.0% | yes | 2026-07-21 | available | complete | moderate | 2 | none |
| medical_technology | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 100.0% | yes | 2026-07-21 | available | complete | moderate | 9 | none |
| cryptocurrency_infrastructure | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 100.0% | yes | 2026-07-22 | available | complete | moderate | 20 | none |

## Symbol classifications

- Category 2: 129
- Category 4: 2
- Category 6: 2
- Category 7: 1
- Category 8: 4

Manual review/unsupported list: ABB, ADYEY, DESP, FANUY, JNPR, NTDOY.

## Mapping corrections

- digital_payments: `SQ` → `XYZ` (core); same CIK and composite FIGI; contiguous adjusted provider history. Boundary: 2025-01-17/2025-01-21.
- digital_payments: `FI` → `FISV` (significant); same CIK and composite FIGI; contiguous adjusted provider history. Boundary: 2025-11-10/2025-11-11.
- streaming_digital_entertainment: `PARA` → `PSKY` (significant); provider-verified merger successor with contiguous adjusted history; entity identifiers intentionally differ. Boundary: 2025-08-06/2025-08-07.

## Release gates

- focused tests: passed
- symbol audit integrity: passed
- theme coverage matrix: passed
- stage7 frozen corpus: passed
- stage7 runtime: passed
- stage7 reference: passed
- stage7 5 semantic equivalence: passed
- stage8 regression: passed
- full backend: passed
- frontend typecheck: passed
- frontend lint: passed
- frontend data ui: passed
- frontend consumer regressions: passed
- frontend route export: passed
- agent registry: passed
- report regressions: passed
- copilot regressions: passed
- hermetic benchmark: passed
- theme rotation backend contract: passed
- theme rotation frontend contract: passed
- theme rotation filters and counts: passed
- theme rotation mathematics: passed
- theme rotation synthetic mechanics: passed
- theme rotation sensitivity: passed
- theme rotation visual acceptance: passed
- sector rotation mathematics: passed
- sector rotation theme kernel parity: passed
- sector rotation downstream compatibility: passed
- sector rotation visual acceptance: passed

## Performance

Hermetic local measurements only; zero network calls and zero model calls. These are not production latency claims.

| Operation | p50 ms | p95 ms |
|---|---:|---:|
| api symbol mapping | 0.737 | 0.8281 |
| api theme detail | 1.9749 | 2.116 |
| api theme directory | 51.9863 | 54.1433 |
| copilot theme retrieval | 0.5179 | 0.53 |
| direct symbol lookup | 0.5132 | 1.0795 |
| full theme ranking | 0.2691 | 0.2903 |
| history batch retrieval | 460.8215 | 475.8553 |
| report theme candidate retrieval | 1.1907 | 1.203 |
| security master batch resolution | 1.9585 | 4.8478 |
| single theme detail | 0.2654 | 0.2765 |
| snapshot batch build | 3802.738 | 3848.5898 |
| symbol to theme lookup | 0.0063 | 0.0065 |
| taxonomy retrieval | 0.2959 | 0.3025 |
| theme rotation rotation api 1M | 17.452 | 18.1748 |
| theme rotation rotation api 1W | 14.7672 | 23.0111 |
| theme rotation rotation api 3M | 14.6407 | 15.04 |
| theme rotation rotation dataset 1M | 0.4454 | 1.2627 |
| theme rotation rotation dataset 1W | 0.4045 | 1.0297 |
| theme rotation rotation dataset 3M | 0.4021 | 0.8163 |
| theme rotation rotation service retrieval | 0.0002 | 0.0002 |
| theme rotation frontend transformation 1W | 0.0172 | 0.0478 |
| theme rotation frontend transformation 1M | 0.0185 | 0.0472 |
| theme rotation frontend transformation 3M | 0.0169 | 0.0311 |
| theme rotation quadrant filtering | 0.0008 | 0.0009 |
| theme rotation smart label selection | 0.0108 | 0.0146 |
| theme rotation theme rotation view filter_pipeline | 0.015 | 0.0222 |
| theme rotation theme rotation view universe_filter | 0.0116 | 0.0124 |
| theme rotation theme rotation view movement_filter | 0.0112 | 0.0127 |
| theme rotation theme rotation view transition_filter | 0.0113 | 0.0353 |
| theme rotation theme rotation view tail_projection | 0.0156 | 0.0279 |
| theme rotation theme rotation view focus_interaction | 0.0168 | 0.0192 |
| theme rotation theme rotation view compare_interaction | 0.0112 | 0.0179 |
| sector rotation persisted retrieval long | 23.35625 | 28.337709 |
| sector rotation persisted retrieval medium | 23.392292 | 28.497292 |
| sector rotation persisted retrieval short | 23.420625 | 29.380583 |

## Browser visual acceptance

Result: **PASS** in the Codex in-app browser against snapshot `theme-2026-07-22-c8d9a44cdd` and model `theme-relative-trend-momentum-v1`.

Loaded artifact: `/Users/andypun/Downloads/market-intelligence-app/artifacts/stage8.75-theme-rotation-frontend-visual-acceptance.json`.
Authoritative service snapshot: `theme-2026-07-22-c8d9a44cdd`.
Failed checks: `{}`.

- all eligible themes plotted: PASS — Show all themes rendered footer: 26 themes plotted.
- all labels preserve points: PASS — Browser label switch preserved 19 points while rendering 19 labels; all 26 remain restorable.
- axis names: PASS — Relative Trend horizontal axis and Relative Momentum vertical axis rendered.
- browser console errors: PASS — count=0.
- chronological tails: PASS — Multiple fading connected observations and emphasized arrow endpoints rendered per theme.
- compare mode: PASS — 8 selected themes, 8 labels, 8-point tails, stable full-source chart domain, and governed comparison summary.
- current point inspector: PASS — Inspector used Relative Trend, Relative Momentum, profile, direction, and SPY benchmark terminology.
- focus mode: PASS — One 10-node full tail plus 25 faint current points; 35 genuine nodes and one selected label.
- indicator explanation: PASS — Relative Trend and momentum-of-relative-trend explanation rendered.
- long leading filter: PASS — 4 points shown / 4 labels shown / Leading filter / 22 filtered.
- long profile retrieval: PASS — Long profile explanation became visible after control selection.
- mobile render: PASS — 390x844 viewport displayed readable Overview, All, Focus, Compare, labels, counts, and fixed navigation without horizontal overflow.
- n a at zero: PASS — No unavailable coordinate rendered at an axis zero.
- none labels preserve points: PASS — Browser label switch preserved 19 points while rendering 0 labels.
- profile controls are explicit: PASS — Short, Medium, Long controls and not-simple-return-windows disclosure rendered.
- progressive mobile default: PASS — 19 of 26 meaningful movers, 3-point trails, Smart labels, and visible Show all themes action.
- proprietary claims absent: PASS — No prohibited proprietary indicator name or third-party equivalence claim rendered.
- smart labels preserve points: PASS — Mobile Overview rendered 19 meaningful points with Smart labels; selector invariant proves labels never filter points.
- tail and transition controls: PASS — Current/3/5/8/Full produced 19/57/95/152/190 nodes; Entered Leading empty state and 2 Lost Leading themes rendered.
- universe and alias search: PASS — Technology & AI, Healthcare, and adtech alias search exercised in the browser.
- web render: PASS — Desktop viewport displayed Overview and 8-theme Compare chart geometry, tails, filters, axes, counts, and summaries.

Desktop screenshot: `artifacts/theme-rotation-ux-screenshots/desktop-overview.png`.
Mobile screenshot: `artifacts/theme-rotation-ux-screenshots/mobile-overview-default.png`.

## Sector Rotation browser acceptance

Result: **PASS** in the Codex in-app browser against snapshot `sector-sp100-v20260718-2026-07-21-67cb07c4fe` and model `sector-relative-trend-momentum-v1`.

- all eligible sectors plotted: PASS — Rendered footer: 11 points shown.
- smart labels preserve points: PASS — 11 points shown / 6 labels shown.
- all labels preserve points: PASS — 11 points shown / 11 labels shown.
- none labels preserve points: PASS — 11 points shown / 0 labels shown.
- long profile retrieval: PASS — Long profile rendered 11 sector endpoints with eight observations per eligible tail.
- long leading filter: PASS — 1 point shown / 1 label shown / Leading filter / 10 filtered.
- short profile retrieval: PASS — Short profile explanation and 11 sector endpoints rendered.
- profile controls are explicit: PASS — Short, Medium, Long controls and not-simple-return-windows disclosure rendered.
- axis names: PASS — Relative Trend horizontal axis and Relative Momentum vertical axis rendered.
- indicator explanation: PASS — Benchmark-relative trend and momentum-of-relative-trend explanation rendered.
- chronological tails: PASS — Eight or ten fading connected observations and emphasized endpoints rendered per sector according to profile policy.
- current point inspector: PASS — Inspector used Relative Trend, Relative Momentum, Medium profile, direction, and SPY benchmark terminology.
- web render: PASS — 1280 x 720 viewport displayed chart geometry, tails, filters, axes, and counts without horizontal overflow.
- n a at zero: PASS — No unavailable coordinate rendered at an axis zero.
- proprietary claims absent: PASS — No prohibited proprietary indicator name or third-party equivalence claim rendered.
- visible runtime errors: PASS — No loading, failed, or error state was visible across profile and filter interactions.

Desktop screenshot: `artifacts/screenshots/stage8.75-sector-rotation-web.png`.
Mobile constraint: The managed in-app browser for this acceptance session exposed a fixed 1280 x 720 viewport and no viewport-resize control; no mobile claim is made.

## Remaining conditions

- Six active mapped symbols remain explicit unsupported/unregistered gaps: ABB, ADYEY, DESP, FANUY, JNPR, and NTDOY.
- Six affected themes are available at 77.78%-88.89% governed mapped coverage under the unchanged 75% availability threshold.
- Historical analytics use current membership; historical membership reconstruction remains future work.
- In-app browser acceptance passed at desktop and 390px mobile viewports; this is local visual evidence, not production monitoring or physical-device certification.
- Sector Rotation in-app browser acceptance passed at the managed 1280x720 desktop viewport; the session exposed no mobile viewport control, so no mobile claim is made.

## Maintenance

Future ticker changes must rerun the approved reference/history audit, preserve canonical entity IDs and date-bounded aliases, refresh through the existing strict-live updater, rebuild the existing registry snapshot, and rerun the hermetic release gate. Unsupported instruments remain unregistered until an explicit policy decision is recorded.

## Reproduction

`make validate-stage8-75 PYTHON=python3`
