# Report V7 Data Capability and Gap Audit

## Supported for V7

| Capability | Frozen source | V7 behavior |
| --- | --- | --- |
| Theme candidates | ThemeSnapshot intelligence | Rank, classification, returns, SPY-relative strength, breadth, participation, concentration, members, coverage, and snapshot identity. |
| Sector candidates | SectorSnapshot dashboard | Rank, classification, returns, rotation, SPY-relative strength, breadth, eligible members, coverage, and snapshot identity. |
| Individual saved-security candidates | Frozen watchlist plus stock chart snapshots | Status, score, daily change, trend, RS rank, freshness, prior status, and price history. |
| Saved stocks/sectors/themes | Frontend watchlist store passed in the report request | Normalized into the immutable report identity and Research Priority Score. |
| Security taxonomy | Security master | Validated ticker-to-sector and ticker-to-industry membership. |
| Theme membership | Versioned theme definitions/snapshots | Validated theme members and parent-sector IDs. |
| Previous-report comparison | Immutable report storage | Compatible theme rank/classification/RS/breadth and watchlist status comparisons. |
| Research score audit | V7 evidence registry | Dimension values, fixed weights, contributions, threshold, completeness, constituent and figure counts. |
| Price levels and annotations | Frozen charts and durable bars | Exact support, resistance, breakout, averages, recent extremes, previous marker, and volume event when current. |
| Market Evolution | Prior frozen report metrics | Regime, health, breadth, risk, primary leader/laggard; requires at least three reliable points. |

## Supported with constraints

| Capability | Constraint | Honest fallback |
| --- | --- | --- |
| Theme/sector persistence | Point-in-time rows have multi-period returns, but long rank history may be shallow. | Use multi-horizon profile; omit unsupported long rank trajectories. |
| Constituent leadership | Current members and member returns are available for reviewed themes. | Call them membership, participation, contribution, outperformance, or underperformance only. |
| Volume confirmation | Security charts have volume; group snapshots do not expose a canonical comparable group-volume field. | Score group volume as missing/zero and state the limitation. |
| Parent-sector comparison | Parent IDs are available but a fully aligned subject/parent total-return series is not always frozen. | Use supported peer/return matrices; omit a falsely precise parent-series chart. |
| Saved-security change | Compatible prior report may have only score, signal, and setup. | Describe supported status changes; do not invent historical price levels. |
| Deep-dive moving averages | Requires adequate frozen history. | Omit MA20/50/200 independently when the window is incomplete. |
| Leadership concentration history | Some current theme concentration fields exist; durable history is incomplete. | Show current concentration in text/quality notes, not a fabricated timeline. |
| Weekend report | Last completed market session remains the market date. | Label report type Weekend/Holiday and avoid implying weekend trading observations. |
| Mixed sources | Source status can differ across theme, sector, macro, and bars. | Preserve per-figure quality and surface a mixed report state. |

## Not yet supported

The following are intentionally omitted rather than inferred:

- validated supplier/customer or direct supply-chain relationships;
- direct capital-flow or fund-flow attribution;
- authoritative news, earnings, or fundamental catalysts attached to a research subject;
- industry-group and security-cluster candidate engines with their own versioned snapshots;
- market-divergence and cross-asset-divergence candidates with a dedicated immutable divergence contract;
- canonical group-volume history and volume-on-decline/advance decomposition;
- long, version-consistent rank and breadth histories for every theme;
- direct Treasury-yield curves, credit spreads, VIX term structure, and authoritative events calendar;
- portfolio holdings, cost basis, quantity, exposure, risk budget, or personalized trade advice;
- predicted price paths or manually drawn trend lines;
- causal claims about why market participants bought or sold.

## Implications

Current V7 can select and explain leading, weakening, lagging, and individual-security subjects using market structure, relative strength, breadth, returns, status changes, and saved-item relevance. It cannot yet claim a fundamental catalyst, group-level volume confirmation for most theme/sector subjects, direct flow, or supply-chain transmission. These limitations are surfaced in the score, focus prose, figures, and methodology instead of being hidden by synthetic data.

The expected complete-report figure target may not be reached when breadth histories, macro proxy series, risk histories, or deep stock histories are absent from the frozen fixture. Shorter reports are the specified fallback and are not padded.
