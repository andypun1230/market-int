import { buildHomeSummary } from '../src/features/home/homeSummary';
import type { HomeDashboardResponse } from '../src/types/market';

function assert(condition: unknown, message: string) {
  if (!condition) throw new Error(message);
}

const dashboard = {
  core: {
    indexes: [],
    decision_summary: {},
    theme_intelligence: {
      available: true,
      snapshot_id: 'theme-live-1',
      market_date: '2026-07-18',
      leaders: [{ theme_id: 'memory-storage', display_name: 'Memory & Storage', rank: 1, composite_score: 77.1, classification: 'Improving' }],
    },
    top_industry_group: { name: 'Static Memory Preference', score: 99 },
  },
  risk_summary: { top_contributors: [] },
  watchlist_summary: { items: [] },
} as unknown as HomeDashboardResponse;

const summary = buildHomeSummary(dashboard);
assert(summary.leadership.length === 1, 'Home consumes a ThemeSnapshot leader when one is published');
assert(summary.leadership[0].label === 'Memory & Storage', 'Home shows the reviewed theme name without implementation metadata');
assert(summary.leadership[0].id === 'memory-storage', 'Home preserves the canonical live theme id for detail navigation');
