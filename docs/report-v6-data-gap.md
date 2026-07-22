# Report V6 Data Capability Audit

## Supported now

| Dataset or analysis | Durable source | Notes |
| --- | --- | --- |
| Immutable report identity and history | Report SQLite storage | Market date, generation time, prior report, JSON and PDF blobs are preserved. |
| Daily OHLCV | `DailyBarStorage` and frozen stock histories | Adjusted bars carry provider, timestamp, quality, and canonical identity. |
| Stock moving averages and levels | Stock snapshots and frozen histories | 20/50/200-day averages, support, resistance, breakout and volume are available when coverage qualifies. |
| Breadth point-in-time | `BreadthSnapshot` | Coverage, A/D metrics, MA breadth, highs/lows, sector breadth, divergences and provenance. |
| Breadth histories | Breadth snapshot storage | 20/50/200-day participation, A/D ratio, net advances and highs-minus-lows through immutable snapshots. |
| Sector point-in-time analytics | `SectorSnapshot` | Returns, relative strength, momentum, breadth, classification, concentration, rank and coverage. |
| Sector rotation tails | Durable adjusted sector ETF/SPY bars | 1W/1M/3M trails with provider provenance and no endpoint rebasing. |
| Theme point-in-time analytics | `ThemeSnapshot` | Reviewed-basket returns, breadth, rankings, overlap, coverage and provenance. |
| Theme rotation tails | Frozen theme rotation series | 1W/1M/3M when constituent/basket history qualifies. |
| Watchlist quote/status matrix | Frozen watchlist summary | Price/change, rating, setup, RS, signal, source state, freshness and missing-section metadata. |
| Deep stock analysis | Durable stock snapshots | Trend, support/resistance, volume, risk plan, multi-timeframe, patterns, RS, rating and provenance. |
| Prior-report comparison | Immutable report history | Compatible metric comparisons only; first report is labelled baseline once. |
| Risk/health evolution | Frozen report evolution | Limited history of market health, risk, breadth, sentiment and leadership. |

## Supported with transformation

| Desired figure | Transformation | Guardrail |
| --- | --- | --- |
| Index price/volume with moving averages | Convert durable OHLCV to aligned price, volume and 20/50/200-day series. | Omit averages without sufficient observations. |
| QQQ/SPY and IWM/SPY relative-strength ratios | Join daily bars by market date and divide adjusted closes. | Omit gaps; disclose internal calculation. |
| Normalized cross-asset performance | Rebase supported ETF proxy histories to 100 on the first shared date. | Label Treasury, credit and commodity instruments as price proxies. |
| Multi-period sector heatmap | Transform sector snapshot return fields to a common matrix. | Preserve missing cells; no zero substitution. |
| Breadth history panels | Convert breadth snapshots to date/value series. | Do not infer dates between snapshots. |
| Risk history | Convert prior frozen report metrics to aligned series. | Label shallow histories and avoid trend claims below minimum length. |
| Security setup chart | Combine frozen OHLCV with snapshot levels, averages, volume and RS context. | Stale/partial inputs remain monitoring-only. |
| Previous-report marker | Align prior report market date to an actual chart session. | Omit when the date is outside or absent from the series. |

## Partially supported

| Desired dataset or figure | Available evidence | Missing element / V6 behavior |
| --- | --- | --- |
| Treasury rates | IEF and TLT ETF price histories | No direct yield level or curve. Use explicitly named bond-price proxies only. |
| Credit conditions | HYG ETF price history | No high-yield or investment-grade option-adjusted spread. Describe proxy confirmation only. |
| Volatility | Current regime/risk observations may exist | No dependable durable VIX history or term structure. Current point may be cited; history figure omitted. |
| Sentiment history | Current Fear & Greed and limited prior report values | No long, independently sourced series. Use current value and report-history changes only. |
| A/D line versus benchmark | Net advances/A-D ratio snapshots and benchmark bars | A true cumulative exchange A/D line may not exist. Label the supported metric precisely. |
| Equal-weight confirmation | Some index/ETF histories may include proxies | RSP is not guaranteed in the frozen report. Include only if durable bars exist. |
| Sector/theme membership history | Current reviewed universes and snapshot versions | Historical results may use current baskets; disclose survivorship limitation. |
| Existing positions | Watchlist stores monitored securities | No verified portfolio lots, cost basis or position sizing. Do not characterize names as holdings. |
| Earnings/events | Unsourced strings currently exist in risk payloads | V6 excludes them unless a source record with date/time/timestamp exists. |

## Unsupported

| Desired dataset or analysis | V6 behavior |
| --- | --- |
| Direct Treasury yield and yield-curve histories | Omit; record limitation. |
| High-yield and investment-grade spread histories | Omit; HYG may appear only as a price proxy. |
| VIX term structure | Omit. |
| Authoritative economic/earnings calendar with consensus and prior values | Omit all unsourced events. |
| External news or research references and URLs | Omit unless a real source registry entry is supplied. |
| Validated causal attribution | Use non-causal observational language. |
| Historical analogues | Omit. |
| Invented scenario probabilities | Use qualitative scenario labels unless a validated frozen model qualifies. |
| Personalized portfolio exposure or recommendations | Present monitoring conditions and product-supported risk posture only. |
| BTC risk-proxy history | Omit unless a durable, provider-attributed series is present in the report input. |

## Pipeline findings

- V5 uses ReportLab and mixes aggregation, prose, figures, and page composition in `services/report.py`.
- `capture_daily_report_inputs()` correctly freezes service reads and prohibits report-time provider fan-out.
- Existing `index_histories` are close-only; V6 should use durable OHLCV transformations without changing provider routing.
- The existing economic calendar is generated from unsourced risk strings. It is not admissible evidence for V6.
- The current frontend rebuilds a V5 briefing model independently. V6 must consume the backend document directly while keeping that path for V5 compatibility.
- Immutable report and PDF storage already supports safe historical compatibility and prior-report lookup.

## Required future data integrations

Potential future work, outside Stage 5.7, includes authoritative yield/curve data, credit spread data, VIX and term structure histories, a sourced events calendar, external reference ingestion, and versioned historical sector/theme membership. None is required to ship an honest V6 report.
