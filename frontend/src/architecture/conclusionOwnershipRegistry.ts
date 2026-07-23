export type ConclusionSurfaceDisposition = 'primary_conclusion' | 'supporting_evidence' | 'advanced_methodology' | 'obsolete_duplicate_removed';

export const CONCLUSION_OWNERSHIP_REGISTRY = [
  { domain: 'market_overview', primary: 'DecisionSummaryCard', supporting: ['Market Snapshot', 'Signal Alignment', 'Key Signals'], removed: ['separate Decision Posture top-level card'] },
  { domain: 'market_health', primary: 'DecisionSummaryCard', supporting: ['Health Breakdown', 'Components', 'Drivers'], removed: ['separate Health Overview and Decision Layer conclusions'] },
  { domain: 'breadth', primary: 'DecisionSummaryCard', supporting: ['Breadth Profile', 'A/D', 'High/Low', 'EMA profile'], removed: ['Key Takeaway duplicate'] },
  { domain: 'macro', primary: 'DecisionSummaryCard', supporting: ['Cross-Asset', 'Risk Appetite', 'Economic Dashboard'], removed: ['duplicate overview interpretation'] },
  { domain: 'decision', primary: 'DecisionSummaryCard', supporting: ['Preferred Setups', 'Checklist', 'Scenarios'], removed: ['legacy Decision Overview layout'] },
  { domain: 'institutions', primary: 'DecisionSummaryCard', supporting: ['Price-Volume Evidence', 'class-level direct evidence'], removed: ['unsupported overall Bullish headline'] },
  { domain: 'sector_breadth_history', primary: 'CanonicalBreadthHistoryPanel', supporting: ['Divergence Alerts'], removed: ['legacy no-history placeholder'] },
  { domain: 'watchlist', primary: 'DecisionSummaryCard', supporting: ['Trading groups', 'Maintenance state', 'Catalyst scope'], removed: ['stale-as-trading-action conclusion'] },
] as const;

export function duplicatePrimaryConclusionDomains() {
  const counts = new Map<string, number>();
  CONCLUSION_OWNERSHIP_REGISTRY.forEach((entry) => counts.set(entry.domain, (counts.get(entry.domain) ?? 0) + 1));
  return [...counts].filter(([, count]) => count > 1).map(([domain]) => domain);
}
