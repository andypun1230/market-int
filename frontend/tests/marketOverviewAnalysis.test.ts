import type { BreadthDashboardViewModel } from '../src/features/market/breadthAnalysis';
import type { DecisionDashboardViewModel } from '../src/features/market/decisionAnalysis';
import type { IndexAnalysis } from '../src/features/market/indexAnalysis';
import type { InstitutionalDashboardViewModel } from '../src/features/market/institutionalAnalysis';
import type { MacroDashboardViewModel } from '../src/features/market/macroAnalysis';
import {
  buildMarketOverviewDashboard,
  buildOverviewBreadthSnapshot,
  buildOverviewKeySignals,
  deriveMarketContradictions,
} from '../src/features/market/marketOverviewAnalysis';
import type { MarketCoreSnapshot, MarketHealthResponse } from '../src/types/market';

function assert(condition: unknown, message: string) {
  if (!condition) {
    throw new Error(message);
  }
}

function health(score = 86): MarketHealthResponse {
  return {
    component_explanations: {},
    components: {
      breadth: 82,
      institutional: 80,
      momentum: 86,
      sector_strength: 78,
      trend: 88,
      volatility: 76,
      volume: 70,
    },
    improving_factors: ['Indexes remain constructive'],
    overall_score: score,
    status: score >= 75 ? 'Very Healthy' : 'Mixed',
    summary: 'Market health remains constructive.',
    weakening_factors: [],
  };
}

function indexes(): IndexAnalysis[] {
  return [
    {
      periodReturn: 4.2,
      relativeStrengthLabel: 'Leading',
      symbol: 'QQQ',
      trend: { tone: 'positive' },
      volume: { tone: 'positive' },
    },
    {
      periodReturn: 2.1,
      relativeStrengthLabel: 'Neutral RS',
      symbol: 'SPY',
      trend: { tone: 'positive' },
      volume: { tone: 'warning' },
    },
    {
      periodReturn: -0.5,
      relativeStrengthLabel: 'Lagging',
      symbol: 'DJI',
      trend: { tone: 'warning' },
      volume: { tone: 'warning' },
    },
  ] as unknown as IndexAnalysis[];
}

function neutralIwmIndexes(): IndexAnalysis[] {
  return [
    { periodReturn: 1.5, relativeStrengthLabel: 'Leading', symbol: 'IWM', trend: { label: 'Range', state: 'range', tone: 'warning' }, volume: { tone: 'warning' } },
    { periodReturn: 0.8, relativeStrengthLabel: 'Neutral RS', symbol: 'SPY', trend: { label: 'Range', state: 'range', tone: 'warning' }, volume: { tone: 'warning' } },
  ] as unknown as IndexAnalysis[];
}

function breadth(tone: 'positive' | 'warning' | 'negative' = 'warning'): BreadthDashboardViewModel {
  return {
    advanceDecline: {
      tone: tone === 'negative' ? 'negative' : 'warning',
    },
    divergence: {
      confirmationLabel: tone === 'negative' ? 'Diverging' : 'Mixed confirmation',
      stateLabel: tone === 'negative' ? 'Bearish divergence' : 'Mixed',
      tone,
    },
    movingAverageProfile: {
      state: tone === 'negative' ? 'Weak Structure' : 'Strong Structure',
      summary: tone === 'negative'
        ? 'Moving-average breadth is weakening'
        : 'Moving-average breadth remains healthy',
    },
    overview: {
      score: tone === 'negative' ? 45 : 72,
      tone,
    },
    quality: {
      confidence: tone === 'negative' ? 'moderate' : 'high',
    },
  } as unknown as BreadthDashboardViewModel;
}

function defensiveMacro(): MacroDashboardViewModel {
  return {
    dataQuality: {
      confidence: 'moderate',
      missingAssets: [],
      sourceKind: 'mixed',
      sourceLabel: 'Mixed sources',
    },
    interpretation: {
      confidence: 'moderate',
      implication: 'Cross-asset confirmation is defensive.',
      mainRisk: 'Treasury proxies and gold are leading equities.',
      stance: 'Defensive Rotation',
      supportiveFactor: 'Equity trend remains positive.',
    },
    riskAppetite: {
      confidence: 'moderate',
      defensiveFactors: ['Treasury proxies and gold are leading equities.'],
      explanation: 'Defensive assets are outperforming equities.',
      score: 35,
      state: 'defensive_rotation',
      supportingFactors: [],
    },
  } as unknown as MacroDashboardViewModel;
}

function institutional(): InstitutionalDashboardViewModel {
  return {
    accumulationDistribution: {
      interpretation: 'Accumulation exceeds distribution.',
    },
    overview: {
      bias: 'Bullish Bias',
      confidence: 'moderate',
      tone: 'positive',
    },
  } as unknown as InstitutionalDashboardViewModel;
}

function decision(): DecisionDashboardViewModel {
  return {
    posture: {
      actionFramework: 'Stay selectively aggressive and require confirmation.',
      confidence: 79,
      mainRisk: 'Chasing extended moves',
      monitor: 'Defensive macro rotation',
      posture: 'aggressive',
      postureLabel: 'Highly Aggressive',
      prefer: 'Pullbacks in leading groups',
      tone: 'positive',
    },
  } as unknown as DecisionDashboardViewModel;
}

function core(): MarketCoreSnapshot {
  return {
    breadth_summary: {
      breadth_score: 72,
      breadth_status: 'Constructive',
      coverage_percent: 88,
      overall_mode: 'mixed',
      percent_above_50ema: 61,
      universe: 'core',
    },
    cache_status: 'fresh',
    decision_summary: {
      aggressiveness: {
        cautions: ['Macro confirmation is defensive'],
        reasons: ['Market health is constructive'],
        score: 78,
        status: 'Moderately Aggressive',
        suggested_exposure: {
          cash: 22,
          margin: 'Light / selective',
          options: 'Suitable for strong setups only',
          stocks: 78,
        },
        summary: 'Stay selectively aggressive while confirmation is mixed.',
      },
      main_risk: 'Defensive macro rotation',
      playbook: {
        action_guidelines: ['Prioritize leading groups'],
        avoid: ['Chasing extended moves'],
        cap_rotation_leader: 'Mega Cap',
        disclaimer: 'Educational market decision support only, not financial advice.',
        headline: 'Stay selectively aggressive',
        main_risk: 'Defensive macro rotation',
        preferred_strategy: 'Momentum Breakouts',
        suggested_aggressiveness: 'Moderately Aggressive',
        summary: 'Focus on leading groups while macro confirmation is mixed.',
        top_industry_group: 'Memory',
        top_sector: 'Technology',
      },
      preferred_style: 'Momentum Breakouts',
    },
    indexes: [],
    overall_mode: 'mixed',
    top_industry_group: {
      breadth_above_50ema: 80,
      name: 'Memory',
      parent_sector: 'Technology',
      rank: 1,
      relative_strength_score: 91,
      return_1d: 1,
      return_1w: 4,
      return_mtd: 6,
      return_ytd: 42,
      score: 94,
      status: 'Leading',
    },
    top_sector: {
      change: '+1.2%',
      name: 'Technology',
      rank: 1,
      relative_strength_score: 88,
      status: 'Leading',
    },
  };
}

function run() {
  const contradictions = deriveMarketContradictions({
    breadth: breadth('negative'),
    core: core(),
    decision: decision(),
    health: health(86),
    indexes: indexes(),
    institutional: institutional(),
    macro: defensiveMacro(),
  });
  assert(contradictions.some((item) => item.type === 'health_macro'), 'strong health plus defensive macro creates a health/macro contradiction');
  assert(contradictions.some((item) => item.type === 'indexes_breadth'), 'index strength plus negative breadth creates an indexes/breadth contradiction');
  assert(contradictions.some((item) => item.type === 'decision_risk' && item.severity === 'high'), 'aggressive posture plus defensive macro creates high-severity decision risk');

  const overview = buildMarketOverviewDashboard({
    breadth: breadth('negative'),
    core: core(),
    decision: decision(),
    health: health(86),
    indexes: indexes(),
    institutional: institutional(),
    macro: defensiveMacro(),
  });
  assert(overview.snapshot.length === 6, 'overview includes the six available executive snapshot dimensions');
  assert(overview.snapshot.some((tile) => tile.key === 'macro' && tile.tone === 'negative'), 'macro tile carries defensive caution');
  assert(overview.alignment.caution.some((item) => item.label === 'Macro'), 'signal alignment places defensive macro in caution');
  assert(overview.regime.summary.includes('Key conflict'), 'regime hero explicitly acknowledges material conflicts');
  assert(overview.insight.includes('Resulting posture'), 'market insight includes the resulting operating posture');
  assert(overview.decisionPosture.posture === 'Highly Aggressive', 'decision posture uses the canonical Decision view model label');
  assert(overview.decisionPosture.monitor?.includes('Healthy equity internals'), 'decision posture discloses the contradiction instead of silently changing thresholds');
  assert(overview.keySignals.length <= 5, 'key signals are capped at five');
  assert(!overview.keySignals.some((signal) => signal.label.includes('No dominant weakening')), 'key signals do not show a false no-weakening message when caution exists');

  const coreFallbackBreadth = buildOverviewBreadthSnapshot(null, core());
  assert(coreFallbackBreadth?.primary === 'Constructive', 'breadth tile falls back to core breadth status before full breadth details load');
  assert(coreFallbackBreadth?.secondary?.includes('61% above 50 EMA'), 'core breadth fallback shows 50 EMA participation');

  const iwmOverview = buildMarketOverviewDashboard({
    breadth: breadth(), core: core(), decision: decision(), health: health(), indexes: neutralIwmIndexes(), institutional: institutional(), macro: defensiveMacro(),
  });
  const indexTile = iwmOverview.snapshot.find((item) => item.key === 'indexes');
  assert(indexTile?.primary === 'Relative leader: IWM', 'IWM is labelled as a relative leader');
  assert(indexTile?.secondary?.includes('trend remains Neutral'), 'IWM neutral trend remains visible');
  assert(!indexTile?.primary.includes('IWM Leading'), 'relative leadership does not imply an absolute bullish trend');

  const coreOnlyOverview = buildMarketOverviewDashboard({
    breadth: null,
    core: core(),
    decision: null,
    health: null,
    indexes: [],
    institutional: null,
    macro: null,
  });
  assert(coreOnlyOverview.decisionPosture.posture === 'Moderately Aggressive', 'decision posture falls back to core decision summary before full Decision details load');
  assert(coreOnlyOverview.decisionPosture.prefer === 'Momentum Breakouts', 'core decision fallback keeps preferred strategy');
  assert(coreOnlyOverview.decisionPosture.avoid === 'Chasing extended moves', 'core decision fallback keeps avoid guidance');

  const missing = buildMarketOverviewDashboard({
    breadth: null,
    core: null,
    decision: null,
    health: null,
    indexes: [],
    institutional: null,
    macro: null,
  });
  assert(missing.snapshot.length === 0, 'missing dimensions are omitted instead of treated as neutral');
  assert(missing.regime.label === 'Unavailable', 'missing overview uses an unavailable regime label');

  const signals = buildOverviewKeySignals(overview.snapshot, overview.contradictions);
  const nonOverviewTabs = signals
    .filter((signal) => signal.sourceTab !== 'overview')
    .map((signal) => signal.sourceTab);
  assert(new Set(nonOverviewTabs).size === nonOverviewTabs.length, 'key signals keep at most one fact per source tab');
}

run();
