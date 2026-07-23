# Stage 10.2 Evidence-Class Registry

## Authority

`frontend/src/features/trust/evidenceClasses.ts` owns the evidence-class contract and aggregate completeness/conflict rules. Existing domain services remain owners of financial conclusions.

| Class | Intended evidence | Current principal consumers |
|---|---|---|
| `price_volume` | Price/volume behavior and accumulation-distribution inference | Institutions, Stock |
| `breadth` | Participation, EMA coverage, A/D and highs/lows | Breadth, Market Health, Sector Detail |
| `relative_strength` | Benchmark-relative performance and trend | Sector/Theme detail and comparison |
| `money_flow` | Direct or proxy flow observations | Institutions |
| `options` | Options positioning | Institutions, Stock |
| `liquidity` | Execution/liquidity observations | Institutions, Stock |
| `large_prints` | Large-print evidence | Institutions |
| `macro` | Cross-asset and macro regime evidence | Macro, Market Overview |
| `news` | Licensed news/catalyst evidence | Home, Watchlist, Reports |
| `fundamentals` | Company fundamental evidence | Stock, Reports |
| `technical` | Trend, level, momentum, pattern evidence | Stock, Watchlist |
| `theme` | Published theme intelligence | Theme Detail, Watchlist |
| `sector` | Published sector intelligence | Sector Detail, Watchlist |
| `market_context` | Overall regime/health context | Home, Market, Reports |

Each class exposes availability, freshness, confidence, provenance, conclusion, limitations, direction, and supporting evidence identifiers. Aggregate confidence is the mean usable-class confidence multiplied by class completeness. Positive and negative usable classes preserve an explicit contradiction; they are never merged into false confirmation.

## Institutional enforcement

Price-volume inference is the primary visible evidence. Money flow, options, large prints, and liquidity remain independent direct-evidence classes. Proxy or absent direct evidence is grouped in a compact “Unavailable direct evidence” disclosure; proxy output cannot upgrade direct confirmation. The headline is “Partial institutional evidence”, “Institutional evidence available”, or “Institutional evidence unavailable”—never an unsupported overall “Bullish”.

