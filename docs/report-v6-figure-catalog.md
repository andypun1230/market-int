# Report V6 Figure Catalog

Figures are emitted only when their minimum data contract is satisfied. Numbering is assigned after omission so it remains contiguous.

| Family | Default question | Required inputs | Status | Minimum / fallback |
| --- | --- | --- | --- | --- |
| Benchmark price and volume | Is the primary trend intact? | SPY OHLCV, provider, as-of | Supported with transformation | 40 sessions; omit MA200 below 200 observations. |
| Index structure | Which indexes confirm or diverge? | SPY, QQQ, IWM, DIA OHLCV | Supported with transformation | Emit per qualifying symbol; no blank panel. |
| Relative-strength ratio | Is growth or small-cap leadership improving? | Date-aligned numerator/denominator closes | Supported with transformation | 20 shared sessions. |
| MA breadth | Is participation broadening across horizons? | Breadth snapshot history, above-20/50/200 values | Supported now | Two observations; shallow-history label below 10. |
| Net advances | Is daily participation confirming price? | Breadth history net advances | Supported now | Two observations; precisely label as net advances. |
| New highs minus new lows | Is internal momentum expanding? | Breadth history highs-minus-lows | Supported now | Two observations. |
| Sector breadth | Which sectors have internal participation? | Sector breadth rows, coverage | Supported now | Omit sectors below their own eligibility policy. |
| Sector return heatmap | Where is multi-horizon leadership? | 1D/1W/1M/3M/6M/1Y sector returns | Supported with transformation | Preserve missing periods. |
| Sector rotation with tails | Which groups are gaining or losing relative momentum? | Durable sector ETF/SPY rotation series | Supported now | Current point plus trail; current-only rows may appear but are qualified. |
| Theme rotation with tails | Which reviewed baskets are emerging or weakening? | Theme rotation series and basket versions | Supported now | Same qualification as sectors; disclose current-basket history. |
| Normalized proxy performance | Do cross-asset proxies confirm risk appetite? | SPY, IEF, TLT, GLD, USO, UUP, HYG histories | Supported with transformation | At least two eligible series and 20 shared sessions. |
| Direct yield chart | Are yields easing or tightening? | Direct maturity yield series | Unsupported | No proxy substitution under a yield title. |
| Credit-spread history | Does credit confirm equities? | HY/IG spread observations | Unsupported | HYG price proxy may be a separately titled figure. |
| VIX history / term structure | Does volatility confirm risk? | Spot and futures-tenor histories | Unsupported | Current sourced point may appear in scorecard only. |
| Risk and health history | Is risk rising or improving? | Prior immutable report snapshots | Partially supported | Require two points; label limited depth. |
| Sentiment history | Is sentiment stretched and changing? | Sourced time series | Partially supported | Current plus compatible prior reports only. |
| Candidate matrix | Which watchlist names deserve attention? | Frozen watchlist statuses and freshness | Supported now | Stale/partial entries cannot be actionable. |
| Stock setup chart | What confirms or invalidates this setup? | Frozen OHLCV, levels, volume, stock snapshot provenance | Supported now | 40 sessions; monitoring-only when stale/partial. |
| Scenario condition table | What market evidence selects each path? | Grounded claims and monitoring conditions | Supported now | Qualitative likelihood unless validated probability model. |
| Prior-report change strip | What changed since the last briefing? | Prior compatible report and evidence IDs | Supported now | Omit; say “Baseline established” once when absent. |
| Event timeline | What scheduled catalysts matter? | Sourced date/time/event/source records | Unsupported currently | Entire figure omitted. |
| Operating-plan table | What should be monitored next session? | Evidence-linked thresholds/conditions | Supported now | Generic “watch” items are rejected. |

## Standard FigureSpec

Each emitted figure contains:

- stable ID and contiguous display number;
- title, subtitle, question answered, chart family and timeframe;
- typed data series with units and transformation method;
- annotations/reference lines constrained to the plotted domain;
- provider-backed source IDs and as-of timestamp;
- live/cached/stale/test/mixed quality, freshness and completeness;
- observation, interpretation, confirmation and risk text;
- explicit unavailable reason when it is catalogued but not emitted.

## Scale policy

- Price charts use the observed range plus restrained padding; comparable index panels do not imply equal absolute units.
- Ratio and normalized-return comparisons use common transforms and units.
- Rotation charts use the engine’s canonical midpoint-100 normalization and common axes across sector/theme peers for a selected interval.
- Percentage breadth panels use 0-100 when cross-panel comparison is the objective.
- Heatmaps use one symmetric return scale per figure and show values as text so color is not the only encoding.
- Missing points create gaps; they are never interpolated or replaced with zero.

## Caption policy

Captions are generated from evidence IDs, not chart pixels or renderer state. The preview and PDF display the same title, period, as-of timestamp, observation, interpretation, confirmation, risk, source IDs, and quality label.
