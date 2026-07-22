# Stage 6 Data Capability and Gap Audit

## Scope

This document separates what the Stage 6 contract can represent from what current production inputs can reliably supply. A field existing in `report-document-v2` does not make the underlying observation available. The builder must omit or downgrade unsupported evidence rather than populate the contract synthetically.

Validation outcomes and sample-render results are recorded separately; this file describes source capability and honest fallback behavior only.

## Supported now

| Capability | Frozen source | Stage 6 behavior |
| --- | --- | --- |
| Theme and sector research candidates | ThemeSnapshot and SectorSnapshot report payloads | Deterministic direction, rank, returns, benchmark-relative evidence, breadth, completeness, membership, and fixed-weight priority scoring. |
| Individual saved-security candidates | Frozen watchlist and stock-chart payloads | Material status, score, or price change; RS rank; setup; freshness; prior compatible status; chart readiness. |
| Question-led inquiry | Selected candidate and selection audit | Direction-aware research question plus a concise evidence-based answer, or an explicit no-focus inquiry. |
| Research Evidence Quality | Registered candidate evidence | High/Medium/Low assessment for freshness, breadth, distinct participation, completeness, and consistency. It is never a probability. |
| Evidence Matrix | Fixed research dimensions | Supports/neutral/contradicts stance with exact evidence references and missing evidence held neutral. |
| Benchmark relationships | Frozen group-relative metric | Explicit SPY comparison for supported theme and sector candidates. |
| Taxonomy and membership relationships | Security master, reviewed theme definitions, and frozen saved preferences | Typed sector, theme, industry, security, and saved-watchlist edges with mapping evidence. |
| Relative security leaders and laggards | Constituent 1M return or matching frozen watchlist RS rank | Up to three relative leaders and laggards, each with metric, timeframe, saved flag, and evidence IDs. |
| Research continuity | Compatible previous report snapshot | Prior state, current state, supported changes, next evidence test, focus-change status, and follow-up instruction. |
| Market timeline | Compatible immutable report metrics | Up to ten dated observations for regime, health, breadth, leadership, risk, optional volatility, leader/laggard, and Research Focus. |
| Selected-security mini reports | Frozen watchlist, chart history, taxonomy, theme membership, and prior report status | At most four selected deep dives with why-here, context, group, chart, setup, RS, volume, risk, confirmation, invalidation, change, and execution consideration. |
| Evidence-linked chart annotations | Frozen levels, price history, computed EMA, prior price, and explicit validated annotation payloads | Only allowed, in-range, non-future annotations whose evidence is registered. |
| No-focus research | Candidate selection audit | Permanent section 6 with failed-gate explanation and priority comparison when candidates exist; no replacement topic is invented. |

## Supported with constraints

| Capability | Production constraint | Honest fallback |
| --- | --- | --- |
| Distinct group participation | The candidate engine expects `participation.positive_return_participation_pct` for themes and `metadata.participation_percent` or the same nested participation field for sectors, but these fields are not guaranteed in every snapshot. | Grade participation `Low`, disclose that it is unavailable, and do not substitute breadth. |
| Group breadth | Theme breadth is currently percent above EMA50; sector breadth is percent above 50EMA. It is a trend-participation measure, not the same observation as positive-return participation. | Keep the supported breadth field and its definition; do not relabel it as daily participation. |
| Group volume confirmation | Current theme and sector candidate inputs do not expose a canonical comparable group-volume series. | Leave volume missing, classify it neutral in the matrix, and contribute zero to priority scoring. |
| Constituent leader/laggard ranking | Theme member returns may be present, but security-master-only sector members commonly lack a frozen 1M return. A matching saved-security RS rank is only available for watched names. | Use the supported metric and label its timeframe; omit the leader/laggard row when neither return nor RS rank exists. |
| Previous-candidate comparison | Compatible history can include prior theme or sector rank, classification, RS, and breadth, but older snapshots are not uniformly populated. | Report only supported changes; otherwise state that the current observation is a baseline. |
| Research Focus history | `researchFocus` is now persisted after document construction, but older stored snapshots predate this field. | Prefer the immediately previous compatible snapshot. If it lacks the field, use only the latest earlier compatible timeline point that carries an explicit `researchFocus`; otherwise show no prior focus. Never infer a focus from prose. |
| Ten-report timeline | The renderer supports ten reports, but the builder requires only three and historical optional fields can be sparse. | Render the available compatible observations, disclose the count below ten, and leave missing fields blank. |
| Volatility continuity | `volatilityState` is optional in historical metrics and may not exist in the current snapshot path. | Leave the timeline's volatility label blank; do not derive a volatility regime from unrelated risk scores. |
| Weekend and holiday reports | No new completed session exists even though a report may be generated on a later calendar date. | Retain the latest durable market date and explicitly state that there is no new market session. |
| Theme parent sectors | Versioned theme definitions can provide parent sector IDs or labels, but older or partial definitions may omit them. | Build from supported member taxonomy or omit the parent layer. |
| Industry relationships | Security-master coverage can be partial or absent for a member. | Omit unsupported industry nodes and preserve explicit direct membership only. |
| Selected-security stock history | Deep charts require at least 30 frozen closes; EMA20/EMA50, comparable volume, support, resistance, breakout, and prior-report price each have independent requirements. | Keep the name in compact triage or render only supported fields; never synthesize a level or moving average. |
| Validated chart events | Failed breakout, gap, pivot, and trendline require explicit `validated_annotations` records. | Omit the event annotation. Ordinary price shape is not enough to infer the event. |
| Macro and cross-asset confirmation | Current report uses adjusted ETF proxies such as IEF and HYG rather than direct rates or credit-spread series. | Label the instruments as proxies and treat their relationships as observational, not causal. |
| Events | Only events already present in the frozen report can be shown. | Omit an unsourced catalyst or calendar item. |
| Personal relevance | Saved stocks, sectors, and themes are available; portfolio holdings and intent are not. | Describe saved/watchlist overlap only and keep it neutral to the market thesis. |

## Breadth is not participation

Stage 6 intentionally stores two separate candidate fields:

- `breadth`: the supported constituent trend breadth, currently percent above a 50-session EMA for theme and sector candidates;
- `participation`: a distinct positive-return participation percentage when the frozen group snapshot provides it.

The values can disagree and answer different questions. Breadth asks how many members support a trend horizon; positive-return participation asks how many members took part in the measured positive-return window. Reusing breadth as participation would manufacture agreement, overstate consistency, and inflate Evidence Quality.

Therefore:

- participation remains `None` when its dedicated field is absent;
- participation evidence is registered separately when present;
- the participation grade is `Low` when unavailable;
- the Evidence Quality rationale explicitly says breadth was not reused;
- conclusion-change conditions may require both measures to align, but absence does not count as alignment.

This separation is a hard analytical constraint, not a display preference.

## Not yet supported as a dependable production capability

The following remain intentionally absent or conditional on a new structured source:

- a broadly populated, version-consistent positive-return participation series for every theme and sector;
- canonical group-volume history, relative group volume, and advancing-versus-declining volume decomposition;
- a default supplier/customer, value-chain, or direct supply-chain dataset;
- economic exposure weights or transmission coefficients between sectors, themes, industries, and companies;
- direct capital-flow, fund-flow, positioning, or institutional-ownership attribution;
- authoritative catalysts tying a focus to news, earnings, filings, or fundamentals;
- industry-group and security-cluster candidate engines with their own immutable versioned snapshots;
- market-divergence and cross-asset-divergence candidate engines with dedicated frozen contracts;
- a fully aligned subject-versus-parent total-return history for every focus;
- uniform constituent return history for security-master-derived sector members;
- a complete ten-report history containing Research Focus and volatility for reports created before Stage 6;
- direct Treasury-yield curves, credit spreads, volatility term structure, options skew, and a canonical events calendar;
- automated technical-event detection with a validated provenance record for failed breakouts, gaps, pivots, or trendlines;
- portfolio holdings, quantity, cost basis, exposure, tax state, liquidity needs, risk budget, or suitability;
- predicted price paths, price targets, speculative future arrows, or causal claims about why participants bought or sold.

## Supply-chain status

The v2 contract can represent `validated_supply_chain`, but the normal Stage 6 report inputs do not provide a general production supply-chain dataset. The builder will emit such an edge only from a `validated_relationships` record with:

- exact source and target symbols already in the graph;
- `relationship_type` equal to `validated_supply_chain`;
- `structured_data: true`;
- a non-empty mapping source.

Absent that complete record, the graph shows only benchmark, hierarchy, taxonomy, membership, and saved overlap. Theme membership is never relabeled as a supply-chain relationship.

## Continuity limitations

Research continuity is compatible-history continuity, not a reconstructed historical research archive.

- The current selected focus is persisted only after the current document has been built.
- Historical snapshots created before Stage 6 may lack `researchFocus`, `volatilityState`, or comparable candidate fields. An explicit `researchFocus` on an earlier compatible timeline point may supply the prior focus, but prose and nearby leadership labels never do.
- Previous theme, sector, and watchlist states are used only when their identifiers and fields are compatible.
- The timeline uses the last ten supplied compatible points, not ten synthetic business days.
- Fewer than three dated observations suppresses the Research Timeline.
- Three through nine observations are rendered with an explicit limitation; missing observations are not backfilled.
- A changed report date on a weekend does not create a market-data change.
- “Tomorrow” is always an evidence test for the next compatible observation, never a forecast of price direction.

These rules mean continuity quality will improve prospectively as more Stage 6 reports are stored.

## Annotation limitations

Stage 6 validates annotation semantics and placement, but validation cannot create source data. Current automatic construction reliably covers:

- support, resistance, and breakout only when frozen numeric levels exist;
- EMA20 and EMA50 only when sufficient observed closes exist;
- previous report only when a compatible previous price exists;
- current thesis, confirmation, invalidation, and risk only when their underlying close or level is registered;
- failed breakout, gap, pivot, and trendline only from explicit validated annotation payloads.

The contract retains selected legacy V7 annotation names for stored-document compatibility. That compatibility does not authorize the new builder to generate an unsupported legacy mark.

Annotations after the figure as-of date, point indices outside the observed series, unknown evidence IDs, unsupported types, and annotation types containing `future` are rejected. A clean chart with fewer labels is the required fallback.

## Security-research limitations

Only selected securities receive full mini reports. Selection is capped at four fresh records so the report can provide depth without duplicating the broad watchlist matrix. A selected name can still have partial fields when an otherwise fresh snapshot lacks a chart level, theme mapping, prior state, or comparable volume history.

Group linkage identifies why a saved security deserves review; it does not make the security actionable. Security-level price, volume, confirmation, invalidation, and freshness remain independent requirements. If those inputs are partial, the execution consideration must remain monitoring-only.

## Data required to close the highest-value gaps

The following source work would materially strengthen Stage 6 without changing the V7 architecture:

1. Add versioned, point-in-time positive-return participation to every ThemeSnapshot and SectorSnapshot, with an explicit window and eligible-member denominator.
2. Add canonical aggregate and constituent-volume fields with comparable transforms and coverage metadata.
3. Persist Research Focus, volatility state, leader/laggard, and compatible candidate metrics in every report snapshot going forward.
4. Freeze member-level multi-horizon returns inside sector and theme snapshots so leader/laggard evidence is independent of watchlist overlap.
5. Version security-master and theme-definition mappings together with effective dates and coverage ratios.
6. Introduce a separately governed relationship dataset for supplier/customer edges, including mapping source, effective date, confidence policy, and materiality semantics.
7. Add direct rates, spreads, volatility-structure, and sourced event contracts if the product must make claims beyond ETF proxies.
8. Store validated technical-event observations with detector version, observation date, point index, level, and evidence source.

Each addition should remain optional in the additive document contract until its production coverage and history are sufficient.

## Required fallback principles

Across every gap, Stage 6 follows the same policy:

- missing stays missing;
- neutral is not support;
- Evidence Quality is not probability;
- breadth is not substituted for participation;
- taxonomy is not supply chain;
- correlation is not causation;
- saved is not owned;
- a next test is not a forecast;
- a no-focus result is valid research output;
- shorter or simpler output is preferable to unsupported density.
