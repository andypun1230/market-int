# Phase 4.4C Sector Intelligence

Sector intelligence is calculated only from durable adjusted Polygon daily bars. The reviewed S&P 100 security master is the constituent universe, not a full-market breadth claim.

The canonical taxonomy has eleven stable identifiers: Communication Services/XLC, Consumer Discretionary/XLY, Consumer Staples/XLP, Energy/XLE, Financials/XLF, Health Care/XLV, Industrials/XLI, Information Technology/XLK, Materials/XLB, Real Estate/XLRE, and Utilities/XLU. `SPY` is the benchmark. Import-boundary aliases normalize to these identifiers; snapshots retain only the canonical ID and display name.

`SectorSnapshotBuilder` reads persisted constituent, ETF, and SPY bars without a provider dependency. Each immutable snapshot records coverage, price returns and EMAs, relative strength versus SPY, constituent breadth, participation/concentration, bounded component scores, classifications, warnings, provenance, rankings, and deterministic transition alerts. Complete requires all ETF histories, valid classifications, and at least 95% eligible constituent coverage; partial requires at least 50% constituent coverage and some ready ETF data.

Public sector routes and legacy compatibility adapters read the same latest snapshot. Background market-structure refresh builds it after breadth. No user-facing sector route fetches ETF or constituent history.
