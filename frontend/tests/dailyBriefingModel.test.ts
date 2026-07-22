import { buildDailyBriefing } from '../src/features/reports/dailyBriefingModel';
import type { DailyReport } from '../src/types/market';

function assert(condition: unknown, message: string) {
  if (!condition) throw new Error(message);
}

const baseReport = {
  date: '2026-07-20',
  executive_summary: 'Constructive conditions remain selective.',
  key_drivers: ['Trend remains intact.'],
  main_risks: ['Breadth remains narrow.'],
  market_regime: 'Selective Risk',
  report_changes: { available: false, items: [], summary: 'No previous report snapshot is available yet.' },
  report_narrative: {
    marketNarrative: 'Leadership remains constructive, but narrow breadth limits broad risk taking.',
    primaryOpportunity: 'Energy leadership.',
    primaryRisk: 'Breadth remains narrow.',
    invalidation: ['Breadth deterioration', 'Volatility expansion'],
    relationships: ['Trend strength is offset by narrow breadth.'],
  },
  recommendation_confidence: { rating: 'Medium', reason: 'signal agreement is mixed', score: 68 },
  scenario_plan: [
    {
      changesProbability: 'Rises if leadership broadens.',
      conditions: 'Breadth expands.',
      expectedBehaviour: 'Indexes grind higher.',
      name: 'Bull Case',
      probability: 45,
      suggestedResponse: 'Add selectively.',
    },
  ],
  sector_leaders: ['Energy'],
  strategy_note: 'Stay selective.',
  title: 'Daily Market Intelligence Briefing',
  tomorrow_watch: ['Monitor QQQ leadership.'],
  watchlist_summary: {
    items: [
      { change_percent: 2.1, main_setup: 'Awaiting breakout confirmation.', score: 82, symbol: 'ARM' },
      { change_percent: -2.4, main_setup: 'Below support.', rating: 'Weak', score: 41, symbol: 'SNDK' },
    ],
  },
} as unknown as DailyReport;

function run() {
  const briefing = buildDailyBriefing(baseReport);

  assert(briefing.changes.summary === 'Baseline report established.', 'first report uses the explicit baseline fallback');
  assert(briefing.narrative.includes('narrow breadth'), 'briefing preserves the connected market narrative');
  assert(briefing.confidence.score === 68 && briefing.confidence.label === 'Medium', 'confidence uses existing engine output');
  assert(briefing.crossMarket[0]?.includes('offset'), 'why-it-happened uses supported relationships');
  assert(briefing.scenarios[0]?.probability === '45%', 'scenario probability is shown only from existing scenario evidence');
  assert(briefing.watchlist.some((item) => item.category === 'Highest Opportunity' && item.symbol === 'ARM'), 'watchlist opportunity is personalized from captured scores');
  assert(briefing.watchlist.some((item) => item.category === 'Highest Risk' && item.symbol === 'SNDK'), 'explicit weak/risk evidence drives the highest-risk priority');

  const missing = buildDailyBriefing({ ...baseReport, report_narrative: {}, scenario_plan: [], watchlist_summary: null });
  assert(missing.scenarios.length === 0, 'missing scenario evidence is not fabricated');
  assert(missing.watchlist.length === 0, 'missing watchlist and fallback ideas remain unavailable');
}

run();
