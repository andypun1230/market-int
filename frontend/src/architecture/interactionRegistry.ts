export type InteractionOutcome = 'expand' | 'filter' | 'navigate' | 'static' | 'update';

export const INTERACTION_REGISTRY = [
  { id: 'home.cards', outcome: 'navigate', owner: 'Home' },
  { id: 'market.section-tabs', outcome: 'filter', owner: 'Market' },
  { id: 'sector.category-and-section-tabs', outcome: 'filter', owner: 'Sectors' },
  { id: 'sector.heatmap-items', outcome: 'navigate', owner: 'Sectors canonical entity detail' },
  { id: 'sector.utility-search', outcome: 'filter', owner: 'Sectors entity repository' },
  { id: 'sector.utility-compare', outcome: 'expand', owner: 'Sectors comparison model' },
  { id: 'sector.utility-filter', outcome: 'filter', owner: 'Sectors filter model' },
  { id: 'watchlist.stock-cards', outcome: 'expand', owner: 'Canonical stock detail' },
  { id: 'watchlist.sector-theme-cards', outcome: 'navigate', owner: 'Canonical entity routing registry' },
  { id: 'report.history', outcome: 'expand', owner: 'Report library' },
  { id: 'copilot.actions', outcome: 'navigate', owner: 'Navigation registry' },
  { id: 'context-intelligence.rows', outcome: 'static', owner: 'Context intelligence consumer policy' },
  { id: 'settings.rows', outcome: 'navigate', owner: 'Settings' },
] as const satisfies readonly { id: string; outcome: InteractionOutcome; owner: string }[];

export function duplicateInteractionIds() {
  const ids = INTERACTION_REGISTRY.map((item) => item.id);
  return ids.filter((id, index) => ids.indexOf(id) !== index);
}
