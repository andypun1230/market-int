export type IntelligenceOwnership = {
  consumers: readonly string[];
  inputs: readonly string[];
  output: string;
  owner: string;
  purpose: string;
};

export const INTELLIGENCE_OWNERSHIP_REGISTRY = [
  ownership('market.snapshot', 'Backend MarketSnapshot service', ['provider histories', 'breadth snapshot', 'sector snapshot', 'theme snapshot'], ['Home', 'Market', 'Copilot', 'Report'], 'Canonical current-market evidence bundle'),
  ownership('market.decision', 'Backend decision summary service', ['market.snapshot'], ['Home summary', 'Market Decision', 'Market Overview', 'Report'], 'Canonical posture, playbook, risk, and aggressiveness conclusion'),
  ownership('market.overview.presentation', 'marketOverviewAnalysis', ['market.snapshot', 'market.decision'], ['Market Overview'], 'Presentation-only cross-market projection; does not replace decision truth'),
  ownership('home.summary.presentation', 'homeSummary', ['market.snapshot', 'market.decision', 'watchlist snapshot'], ['Home'], 'Home projection of canonical market conclusions'),
  ownership('home.market_posture.presentation', 'marketPostureProjection', ['market.health', 'market.breadth', 'market.decision'], ['homeSummary'], 'Single owner of the Home risk-on/selective/risk-off projection'),
  ownership('market.health', 'Backend market-health engine', ['market.snapshot'], ['Market Health', 'Home', 'Report', 'Copilot'], 'Canonical health score and component conclusions'),
  ownership('market.breadth', 'Backend BreadthSnapshot service', ['market histories'], ['Market Breadth', 'Home', 'Report', 'Copilot'], 'Canonical breadth state and evidence'),
  ownership('sector.snapshot', 'Backend SectorSnapshot service', ['security histories', 'breadth ownership'], ['Sectors', 'Watchlist', 'Report', 'Copilot'], 'Canonical sector ranking, classification, and metrics'),
  ownership('theme.snapshot', 'Backend ThemeSnapshot service', ['governed theme definitions', 'security histories'], ['Themes', 'Watchlist', 'Report', 'Copilot'], 'Canonical theme ranking, classification, and metrics'),
  ownership('sector.rotation', 'Backend sector rotation engine', ['sector ETF histories'], ['Sector Rotation'], 'Canonical sector rotation coordinates and movement'),
  ownership('theme.rotation', 'Backend theme rotation engine', ['theme basket histories'], ['Theme Rotation'], 'Canonical theme rotation coordinates and movement'),
  ownership('stock.snapshot', 'Backend StockAnalysisSnapshot service', ['security histories', 'sector/theme context'], ['Stock Detail', 'Watchlist', 'Report', 'Copilot'], 'Canonical stock analysis evidence and conclusions'),
  ownership('watchlist.classification', 'watchlistClassifier', ['stock.snapshot'], ['Watchlist'], 'Saved-stock UI classification'),
  ownership('watchlist.decision', 'watchlistDecision', ['watchlist.classification'], ['Watchlist Summary'], 'Watchlist-level decision projection'),
  ownership('watchlist.maintenance.presentation', 'watchlistDecision', ['watchlist.classification data status'], ['Watchlist Summary', 'Watchlist cards'], 'Maintenance state kept separate from trading priority'),
  ownership('trust.user_facing_data_state', 'userFacingDataState', ['provider status', 'test status', 'freshness context'], ['Home', 'Market', 'Sectors', 'Watchlist', 'Report', 'Copilot', 'Settings', 'About', 'Data Sources', 'More'], 'One plain-language provider-state classification'),
  ownership('trust.evidence_class.presentation', 'evidenceClasses', ['existing domain evidence outputs'], ['DecisionSummaryCard', 'Institutions'], 'Evidence availability and completeness projection without cross-class inference'),
  ownership('trust.decision_summary.presentation', 'decisionSummary', ['existing authoritative domain conclusions'], ['Analytical screens'], 'Shared decision hierarchy without replacement conclusions'),
  ownership('trust.atomic_screen_state', 'atomicScreenState', ['request lifecycle', 'last valid payload'], ['useAsyncData', 'analytical surfaces'], 'Mutually exclusive loading, content, empty, unavailable, stale, and failed states'),
  ownership('report.document', 'Backend report document builder', ['versioned intelligence snapshots'], ['Report', 'Copilot'], 'Immutable report content and evidence lineage'),
  ownership('context.news', 'Backend news intelligence service', ['normalized source events'], ['Home', 'Market', 'Sector/Theme Detail', 'Stock Detail', 'Watchlist', 'Copilot'], 'Canonical material-event interpretation'),
  ownership('context.session', 'Backend session narrative service', ['market session evidence'], ['Market', 'Copilot'], 'Canonical session narrative'),
] as const satisfies readonly IntelligenceOwnership[];

export function duplicateIntelligenceOutputs(registry: readonly IntelligenceOwnership[] = INTELLIGENCE_OWNERSHIP_REGISTRY) {
  const counts = new Map<string, number>();
  registry.forEach((item) => counts.set(item.output, (counts.get(item.output) ?? 0) + 1));
  return [...counts.entries()].filter(([, count]) => count > 1).map(([output]) => output);
}

function ownership(
  output: string,
  owner: string,
  inputs: readonly string[],
  consumers: readonly string[],
  purpose: string,
): IntelligenceOwnership {
  return { consumers, inputs, output, owner, purpose };
}
