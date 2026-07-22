# Report V7 Figure and Annotation Catalog

V7 preserves every V6 figure family and adds research selection, subject, and timeline figures. A figure is emitted only when its data contract qualifies. Final numbering is assigned after omissions.

## Research figures

| Figure | Question answered | Required inputs | V7 status / fallback |
| --- | --- | --- | --- |
| Research Priority Comparison | Why did the subject outrank competitors? | At least one scored candidate, fixed weights, threshold evidence | Always emitted for a selected focus; threshold line uses exact evidence. |
| Subject versus SPY relative strength | Is the move distinct from broad-market beta? | Aligned subject and SPY history or canonical snapshot RS history | Supported when series exists; current RS still appears in evidence if history does not. |
| Subject versus parent sector | Does the subject outperform its parent? | Aligned subject and parent total-return histories | Conditional; omitted when only membership exists. |
| Multi-period return profile | Is direction recent or persistent? | At least two of 1W/1M/3M/6M/1Y returns | Supported for qualified group candidates. |
| Peer return heatmap | Does the subject stand out among comparable candidates? | At least two same-category candidates with supported returns | Supported; missing periods stay blank. |
| Constituent breadth history | Is participation broadening or deteriorating? | Version-compatible breadth history | Conditional; current breadth remains evidence when history is shallow. |
| Constituent leadership matrix | Which members confirm or diverge? | Validated members plus comparable member metrics | Conditional on member metrics. |
| Industry/theme chain | How do validated memberships connect? | Security master and/or versioned theme definitions | Membership only. Unsupported nodes and supply-chain claims are omitted. |
| Constituent contribution | Which members contribute to the current group result? | Validated contribution fields | Conditional; never relabeled as capital flow. |
| Saved-security overlap | Which saved securities have validated membership? | Current saved universe plus validated mapping | Represented in focus/affected-security blocks; diagram only when enough distinct nodes exist. |
| Leader/laggard comparison | Is leadership uniform? | Qualified opposing candidates with comparable metrics | Conditional; secondary note may provide the comparison. |
| Rank history | Is the ranking stable? | At least three compatible immutable rank points | Conditional; otherwise rank change or baseline only. |
| Rotation trajectory | Is the subject moving between classifications? | Durable version-compatible rotation history | Existing sector/theme rotation tails remain available. |
| Confirmation/invalidation framework | What upgrades or downgrades the thesis? | Exact supported conditions and levels | Rendered in focus prose and figure captions; diagram optional. |
| Security small multiples | Which saved names confirm or diverge? | Current complete stock histories and levels | Three to six complete deep dives preferred; stale names are monitoring-only. |
| Research evidence summary | What evidence and limitations support selection? | Evidence registry plus machine-readable decision | Rendered as score breakdown/selection appendix rather than decorative art. |
| Individual-security price structure | Does a major saved-security status change persist in price? | At least 30 frozen price observations and a material status change | Supported for qualified individual-security focus. |

## Market Evolution

The compact timeline can show market regime, market health, breadth, leadership concentration, risk, volatility state, primary leader, and primary laggard for the last 5–10 available reports. It requires at least three reliable observations. Missing dimensions remain blank; fewer than three rows omit the figure entirely.

## Annotation contract

| Annotation | Evidence contract | Placement/fallback |
| --- | --- | --- |
| Support / invalidation | Current supported numeric level and evidence ID | Horizontal line; omit if stale/unavailable. |
| Resistance / breakout / confirmation | Current supported numeric level and evidence ID | Horizontal line or confirmation arrow; no predicted path. |
| MA20 / MA50 / MA200 | Full-window moving average observation | Label only when enough history exists. |
| Previous-report marker | Prior market date aligned to an actual series point | Vertical marker; omit outside domain. |
| Recent high / recent low | Exact maximum/minimum from the defined frozen window | Point or line label; evidence records the window. |
| Gap marker | Algorithmically detected gap with both adjacent bars | Omit without OHLC bars. |
| Relative-strength turning point | Algorithmically identified series point | Omit when only current RS exists. |
| Volume-expansion marker | Exact volume observation versus supported baseline | Point marker; omit when volume history/baseline is absent. |
| Trend-line break | Validated algorithm and exact break observation | Currently omitted unless an upstream supported field exists. |
| Risk / monitoring zone | Supported numeric bounds and evidence IDs | Shaded only within chart scale; no speculative future region. |

Labels are collision-spread inside the plot bounds while their reference lines remain at exact data coordinates. Tests cover minimum spacing, plot bounds, reference-value/evidence equality, and suppression of stale annotations.

## Shared caption contract

PDF and frontend render the same `FigureSpec` fields:

1. contiguous figure number and title;
2. subtitle, timeframe, and as-of value;
3. the question answered;
4. observation and interpretation;
5. confirmation and risk conditions;
6. source IDs, transformation, freshness, completeness, and warnings.

No caption is generated from pixels or renderer-specific state. Figures carry substantive data series and are omitted rather than replaced with decorative diagrams.
