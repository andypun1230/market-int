import {
  buildChanges,
  buildDecisionDashboardViewModel,
  buildFearGreed,
  buildMarketCapRotation,
  buildPosture,
  buildPreferredSetups,
  buildScenarios,
  fearGreedStatus,
  gaugeMarkerPercent,
} from '../src/features/market/decisionAnalysis';
import type { DecisionDashboardResponse, FearGreedResponse, MarketCapRotationResponse } from '../src/types/market';

function assert(condition: unknown, message: string) {
  if (!condition) {
    throw new Error(message);
  }
}

function dashboard(overrides: Partial<DecisionDashboardResponse> = {}): DecisionDashboardResponse {
  return {
    aggressiveness: {
      score: 88,
      status: 'Highly Aggressive',
      suggested_exposure: { cash: 10, margin: 'Moderate acceptable', options: 'Suitable for high-quality breakouts', stocks: 90 },
      summary: 'Market is constructive with strong participation.',
      reasons: ['Market Health is Healthy'],
      cautions: ['Avoid chasing extended moves'],
    },
    checklist: {
      grade: 'Healthy',
      items: [
        { label: 'Market health above 70', passed: true, value: '82 / 100' },
        { label: 'Breadth above 50EMA >= 60', passed: true, value: '68%' },
        { label: 'Top sector strength >= 75', passed: false, value: '71 / 100' },
        { label: 'Fear & Greed not Extreme Greed', passed: false, value: 'Greed' },
      ],
      max_score: 4,
      score: 2,
      summary: '2 of 4 checklist items are positive.',
    },
    comparison: {
      items: [
        { metric: 'Breadth', today: 68, yesterday: 62, change: 6 },
        { metric: 'Sector Strength', today: 64, yesterday: 70, change: -6 },
        { metric: 'Volatility', today: 20, yesterday: 20, change: 0 },
      ],
      summary: 'Breadth improved while sector participation weakened.',
    },
    decision_confidence: {
      contributors: [],
      disagreements: [],
      score: 79,
      status: 'High',
      summary: 'Inputs mostly agree.',
    },
    industry_rotation: { sectors: [], summary: 'Themes mixed.' },
    institutional_intelligence: {} as DecisionDashboardResponse['institutional_intelligence'],
    leadership: { categories: [], summary: 'Leadership is concentrated.' },
    playbook: {
      action_guidelines: ['Prioritize high-RS stocks.'],
      avoid: ['Extended entries'],
      cap_rotation_leader: 'Mega Cap',
      disclaimer: 'Educational only.',
      headline: 'Selectively Aggressive',
      main_risk: 'Sector concentration',
      preferred_strategy: 'Pullback Buying',
      suggested_aggressiveness: 'Highly Aggressive',
      summary: 'Focus on leading stocks in leading themes.',
      top_industry_group: 'Memory',
      top_sector: 'Technology',
    },
    probabilities: {
      items: [
        { confidence: 80, explanation: 'Trend support remains constructive.', probability: 58, strategy: 'Trend Continuation' },
        { confidence: 65, explanation: 'Some breadth is mixed.', probability: 27, strategy: 'Mean Reversion' },
        { confidence: 50, explanation: 'Pullback risk remains.', probability: 15, strategy: 'Short Selling' },
      ],
      summary: 'Trend continuation is preferred.',
    },
    risk_dashboard: {
      contributors: [{ explanation: 'Concentration is elevated.', impact: 'warning', label: 'Sector concentration' }],
      score: 22,
      summary: 'Risk is low but concentration should be monitored.',
      upcoming_events: [],
      warnings: ['Sector concentration'],
    },
    trading_styles: {
      items: [
        { rating: 5, reason: 'Healthy trend supports pullbacks.', score: 84, status: 'Preferred', style: 'Pullback Buying' },
        { rating: 4, reason: 'Trend remains constructive.', score: 78, status: 'Favorable', style: 'Trend Following' },
        { rating: 3, reason: 'Breadth is not perfect.', score: 62, status: 'Selective', style: 'Momentum Breakouts' },
        { rating: 1, reason: 'Not favored in constructive tape.', score: 25, status: 'Avoid', style: 'Short Selling' },
      ],
      preferred_style: 'Pullback Buying',
      summary: 'Pullbacks and trend continuation are preferred.',
    },
    ...overrides,
  };
}

function capRotation(overrides: Partial<MarketCapRotationResponse> = {}): MarketCapRotationResponse {
  return {
    items: [
      { category: 'Mega Cap', money_flow: 'Inflow', relative_strength: 92, return_1m: 7, return_1w: 2, score: 88, status: 'Leading', symbol: 'MGK' },
      { category: 'Large Cap', money_flow: 'Stable', relative_strength: 74, return_1m: 4, return_1w: 1, score: 74, status: 'Strong', symbol: 'SPY' },
      { category: 'Small Cap', money_flow: 'Outflow', relative_strength: 34, return_1m: -2, return_1w: -1, score: 34, status: 'Weak', symbol: 'IWM' },
    ],
    laggard: 'Small Cap',
    leader: 'Mega Cap',
    summary: 'Mega caps are leading while small caps remain weak.',
    ...overrides,
  };
}

function fearGreed(score: number, status = fearGreedStatus(score)): FearGreedResponse {
  return {
    components: [],
    score,
    status,
    summary: `${status} sentiment conditions.`,
  };
}

function run() {
  const base = dashboard();
  const posture = buildPosture(base, capRotation());
  assert(posture.posture === 'aggressive' || posture.posture === 'selectively_aggressive', 'aggressiveness merges into posture');
  assert(posture.riskScore === 22, 'risk dashboard score merges into posture');
  assert(posture.mainRisk !== posture.monitor, 'avoid and monitor are distinct');
  assert(posture.riskBadgeLabel === 'Low Risk', 'low risk badge is explicit');

  const weakBreadth = buildPosture(dashboard({ checklist: { ...base.checklist, max_score: 8, score: 4 } }), capRotation());
  assert(weakBreadth.posture !== 'aggressive', 'weak checklist prevents unjustified aggressive posture');
  assert(weakBreadth.riskLabel === 'Low', 'risk label stays internally consistent');

  const setups = buildPreferredSetups(base);
  assert(setups[0].label === 'Pullback to Support', 'pullback setup ranks highly in constructive conditions');
  assert(setups.some((item) => item.label === 'Breakout Attempt' && item.suitabilityLabel === 'Selective'), 'breakouts become selective when score is moderate');
  assert(setups.at(-1)?.suitabilityLabel === 'Avoid', 'defensive/short setup can rank as avoid');

  const viewModel = buildDecisionDashboardViewModel(base, capRotation(), fearGreed(70));
  assert(viewModel?.leadershipFocus.length === 3, 'leadership focus is compact');
  assert(viewModel?.checklist.confirmed === 2, 'checklist confirmed count is correct');
  assert(viewModel?.checklist.items.some((item) => item.statusLabel === 'Monitor'), 'failed checklist item becomes monitor when not severe');
  assert(viewModel?.scenarios.scenarios.reduce((sum, item) => sum + item.value, 0) === 100, 'scenario weights total 100');
  assert(viewModel?.scenarios.label === 'Scenario Weights', 'heuristic values are labelled scenario weights');
  assert(!viewModel?.scenarios.scenarios.some((item) => item.label === 'Breakout Attempt'), 'breakout attempt is removed from market paths');

  const cap = buildMarketCapRotation(capRotation());
  assert(cap.leader === 'Mega Cap', 'market cap leader selected');
  assert(cap.laggard === 'Small Cap', 'market cap laggard selected');
  assert(cap.stateLabel === 'Mega-Cap Concentration', 'market cap concentration state selected');

  assert(fearGreedStatus(10) === 'Extreme Fear', 'extreme fear threshold maps');
  assert(fearGreedStatus(70) === 'Greed', 'greed threshold maps');
  assert(gaugeMarkerPercent(120) === 100 && gaugeMarkerPercent(-10) === 0, 'gauge marker is bounded');
  assert(buildFearGreed(fearGreed(80)).status === 'Extreme Greed', 'fear greed model accepts dynamic score');

  const changes = buildChanges(base.comparison.items);
  assert(changes.groups.some((group) => group.direction === 'improving' && group.items.some((item) => item.startsWith('Breadth +6'))), 'improving factors are grouped with deltas');
  assert(changes.groups.some((group) => group.direction === 'weakening' && group.items.some((item) => item.startsWith('Sector participation -6'))), 'weakening factors are grouped with deltas');
  assert(changes.groups.some((group) => group.direction === 'stable'), 'stable factors are grouped');
  assert(buildChanges([]).unavailable, 'missing history returns unavailable');

  const scenarios = buildScenarios(base.probabilities.items, posture);
  assert(scenarios.invalidation.length > 0, 'main invalidation is derived');
}

run();
