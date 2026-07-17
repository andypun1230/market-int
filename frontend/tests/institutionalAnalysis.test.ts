import {
  buildAccumulationDistribution,
  buildInstitutionalDashboardViewModel,
} from '../src/features/market/institutionalAnalysis';
import type {
  InstitutionalActivityResponse,
  InstitutionalIntelligenceResponse,
} from '../src/types/market';

function assert(condition: unknown, message: string) {
  if (!condition) {
    throw new Error(message);
  }
}

function activity(overrides: Partial<InstitutionalActivityResponse['bias']> = {}): InstitutionalActivityResponse {
  return {
    bias: {
      accumulation_count: 9,
      bias: 'Bullish',
      churning_count: 1,
      distribution_count: 2,
      follow_through_day: {
        date: '2026-07-14',
        gain_percent: 1.8,
        index: 'QQQ',
        triggered: true,
      },
      stall_count: 1,
      summary: 'Institutional activity is constructive.',
      ...overrides,
    },
    indexes: [],
  };
}

function intelligence(overrides: Partial<InstitutionalIntelligenceResponse> = {}): InstitutionalIntelligenceResponse {
  return {
    liquidity: {
      depth_condition: 'Healthy',
      funding_condition: 'Stable',
      score: 72,
      spread_condition: 'Tight',
      status: 'Healthy',
      summary: 'Liquidity remains supportive.',
      volume_condition: 'Normal',
      warnings: [],
    },
    money_flow: {
      inflow_leaders: [],
      items: [
        { area: 'Technology', change_1d: 1, change_1w: 4, flow: 'Inflow', score: 82, status: 'Strong', summary: 'Buying pressure is broad.' },
        { area: 'Utilities', change_1d: -0.2, change_1w: -1.4, flow: 'Outflow', score: 35, status: 'Weak', summary: 'Selling pressure appears.' },
      ],
      methodology: 'Proxy from sector returns and volume.',
      outflow_leaders: [],
      score: 75,
      status: 'Buying Bias',
      summary: 'Money flow leans toward risk assets.',
    },
    institutional: {
      accumulation_distribution: 'Accumulation',
      block_trade_bias: 'Bullish',
      block_trade_candidates: [
        { reason: 'Bullish accumulation candidate', side: 'buy', symbol: 'NVDA' },
        { reason: 'Bearish distribution candidate', side: 'sell', symbol: 'XLE' },
        { reason: 'Neutral rebalance candidate', side: 'neutral', symbol: 'SPY' },
      ],
      confidence: 78,
      dark_pool_bias: 'Neutral',
      limitations: ['Block-trade identity is estimated.'],
      program_trading: 'Normal',
      risks: [],
      score: 81,
      signals: ['Accumulation pressure remains constructive.'],
      status: 'Bullish',
      summary: 'Institutional dashboard is constructive.',
    },
    options: {
      confidence: 76,
      implied_volatility_rank: 42,
      options_flow_bias: 'Call leaning',
      put_call_ratio: 0.72,
      score: 68,
      skew: 'Neutral',
      status: 'Constructive',
      summary: 'Options positioning is constructive.',
      unusual_activity: [],
    },
    sentiment: {
      confidence: 76,
      methodology: 'Market proxy',
      official_index: false,
      opportunities: [],
      overall_mode: 'mixed',
      risks: [],
      score: 74,
      signals: [],
      status: 'Constructive',
      summary: 'Market sentiment is constructive.',
    },
    summary: 'Institutional intelligence is constructive.',
    ...overrides,
  };
}

function runTests() {
  const dashboard = buildInstitutionalDashboardViewModel(intelligence(), activity());
  assert(dashboard !== null, 'dashboard is created with intelligence and activity');
  if (!dashboard) {
    return;
  }
  assert(dashboard.overview.bias === 'Bullish', 'raw institutional activity bias is preserved');
  assert(dashboard.overview.subtitle === 'Current institutional activity', 'overview uses approved subtitle');
  assert(dashboard.overview.directionalBiasScore === 81, 'overview keeps directional bias score separate');
  assert(dashboard.overview.confidence === 'moderate', 'mixed/proxy-heavy inputs cap confidence below high');
  assert(dashboard.overview.source === 'mixed', 'source comes from overall mode');
  assert(dashboard.bias.bias === 'Accumulation Bias', 'bias card uses evidence label instead of repeating directional bias');
  assert(!('score' in dashboard.bias), 'bias evidence does not repeat overview score');
  assert(dashboard.moneyFlow.state === 'Strong Buying', 'money flow detects buying pressure');
  assert(dashboard.moneyFlow.netFlow !== null && dashboard.moneyFlow.netFlow > 0, 'net flow is positive');
  assert(Math.round((dashboard.moneyFlow.buyingPressure ?? 0) + (dashboard.moneyFlow.sellingPressure ?? 0)) === 100, 'paired money-flow percentages sum to 100');
  assert(!dashboard.moneyFlow.interpretation.toLowerCase().includes('large-print'), 'money-flow copy does not repeat large-print caveat');
  assert(dashboard.largePrints.bullish === 1, 'bullish print candidates are counted');
  assert(dashboard.largePrints.bearish === 1, 'bearish print candidates are counted');
  assert(dashboard.largePrints.neutral === 1, 'neutral print candidates are counted');
  assert(dashboard.largePrints.state === 'Neutral Candidate Bias', 'large-print terminology stays candidate-based');
  assert(!dashboard.largePrints.state.includes('Print Bias'), 'large-print terminology avoids verified identity language');
  assert(dashboard.options.callActivity !== null && dashboard.options.callActivity > dashboard.options.putActivity!, 'put/call ratio derives call activity');
  assert(Math.round((dashboard.options.callActivity ?? 0) + (dashboard.options.putActivity ?? 0)) === 100, 'options activity bars sum to 100');
  assert(dashboard.liquidity.rows.some((row) => row.label === 'Execution Risk'), 'liquidity includes execution risk row');
  assert(dashboard.liquidity.rows.some((row) => row.label === 'Classification' && row.value === 'Healthy'), 'liquidity uses value rows');
  assert(dashboard.accumulationDistribution.state === 'Accumulation Bias', 'accumulation/distribution state is derived from counts');
  assert(dashboard.accumulationDistribution.maxCount >= 9, 'accumulation/distribution exposes shared bar scale');
  assert(dashboard.followThroughDay.state === 'Detected', 'follow-through day is detected');
  assert(!dashboard.followThroughDay.interpretation.toLowerCase().includes('guaranteed rally'), 'follow-through wording avoids guarantee language');
  assert(dashboard.trend.historyAvailable === false, 'smart money trend does not fabricate history');
  assert(dashboard.dataQuality.limitations.some((item) => item.toLowerCase().includes('identity')), 'limitations include institutional identity caveat');
  assert(dashboard.dataQuality.limitations.some((item) => item.toLowerCase().includes('fallback')), 'fallback disclosure is centralized in data quality');

  const liveHighConfidence = buildInstitutionalDashboardViewModel(
    intelligence({ sentiment: { ...intelligence().sentiment, overall_mode: 'live' } }),
    activity(),
  );
  assert(liveHighConfidence?.overview.confidence === 'high', 'live high-confidence inputs may remain high confidence');

  const moderateDirection = buildInstitutionalDashboardViewModel(
    intelligence({
      institutional: { ...intelligence().institutional, score: 60 },
      sentiment: { ...intelligence().sentiment, overall_mode: 'live' },
    }),
    activity({ bias: 'N/A' }),
  );
  assert(moderateDirection?.overview.bias === 'Constructive', 'moderate directional score maps to constructive');

  const distribution = buildInstitutionalDashboardViewModel(
    intelligence({ institutional: { ...intelligence().institutional, block_trade_candidates: [] } }),
    activity({ accumulation_count: 1, bias: 'Bearish', distribution_count: 9, follow_through_day: { date: null, gain_percent: null, index: null, triggered: false } }),
  );
  assert(distribution?.accumulationDistribution.state === 'Heavy Distribution', 'distribution pressure is detected');
  assert(distribution?.largePrints.state === 'No Signal', 'empty large-print candidates do not become unavailable');
  assert(distribution?.largePrints.hasSignal === false, 'zero large prints hide visual signal bars');
  assert(distribution?.followThroughDay.state === 'No recent follow-through day', 'missing follow-through is explicit');

  const balanced = buildAccumulationDistribution(activity({ accumulation_count: 3, distribution_count: 3 }));
  assert(balanced.state === 'Balanced', 'balanced accumulation/distribution state is supported');

  const strongAccumulation = buildAccumulationDistribution(activity({ accumulation_count: 12, churning_count: 2, distribution_count: 1, stall_count: 2 }));
  assert(strongAccumulation.state === 'Strong Accumulation', 'strong accumulation requires clear net accumulation without elevated friction');

  const frictionLimited = buildAccumulationDistribution(activity({ accumulation_count: 12, churning_count: 13, distribution_count: 1, stall_count: 13 }));
  assert(frictionLimited.state === 'Accumulation Bias', 'high stall/churning prevents overstated strong accumulation');

  const defensiveOptions = buildInstitutionalDashboardViewModel(
    intelligence({ options: { ...intelligence().options, put_call_ratio: 1.4 } }),
    activity(),
  );
  assert(defensiveOptions?.options.state === 'Defensive', 'high put/call ratio maps to defensive options tone');

  const unavailable = buildInstitutionalDashboardViewModel(null, null);
  assert(unavailable === null, 'dashboard is null when all institutional data is missing');
}

runTests();
