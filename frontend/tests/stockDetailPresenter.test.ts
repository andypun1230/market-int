import {
  buildStockDetailOverview,
  getAssessment,
  getFactorTone,
} from '../src/features/stock-detail/stockDetailPresenter';
import type { StockRatingItem, WatchlistItem } from '../src/types/market';

function assert(condition: unknown, message: string) {
  if (!condition) {
    throw new Error(message);
  }
}

function makeStock(overrides: Partial<WatchlistItem> = {}): WatchlistItem {
  return {
    change: 1.4,
    change_percent: 2.3,
    data_source: 'live',
    fallback_used: false,
    is_live: true,
    is_stale: false,
    price: 62.5,
    risk_flag: 'Medium',
    setup: 'near breakout',
    support_zone: '$58-$60',
    ticker: 'MU',
    trend: 'Constructive',
    ...overrides,
  };
}

function makeRating(overrides: Partial<StockRatingItem> = {}): StockRatingItem {
  return {
    components: {
      institutional_support: 60,
      market_alignment: 72,
      pattern_quality: 66,
      relative_strength: 88,
      risk_control: 58,
      sector_strength: 74,
    },
    data_quality: {
      history_source: 'polygon',
      overall_mode: 'mixed',
    },
    explanation: 'Rating is constructive with strong relative strength but mixed risk control.',
    overall_score: 78,
    rating: 'Buy Watch',
    risk_level: 'Medium',
    status: 'Constructive',
    strengths: ['Strong relative strength', 'Supportive sector action'],
    symbol: 'MU',
    warnings: ['Risk control is not perfect'],
    ...overrides,
  };
}

function run() {
  assert(getAssessment(91, 'A', 'Strong').label === 'High Conviction', 'high score maps to high conviction');
  assert(getAssessment(72, 'B', 'Constructive').tone === 'accent', 'constructive score maps to informational tone');
  assert(getAssessment(52, 'C', 'Mixed').tone === 'warning', 'mixed score maps to warning');
  assert(getAssessment(34, 'D', 'Weak').tone === 'danger', 'weak score maps to danger');
  assert(getAssessment(null, null, 'Unavailable').label === 'Unavailable', 'missing score preserves status');

  assert(getFactorTone(80) === 'success', 'strong factor tone');
  assert(getFactorTone(60) === 'accent', 'constructive factor tone');
  assert(getFactorTone(45) === 'warning', 'mixed factor tone');
  assert(getFactorTone(20) === 'danger', 'weak factor tone');
  assert(getFactorTone(null) === 'neutral', 'missing factor tone');

  const model = buildStockDetailOverview({
    relativeStrength: {
      as_of: '2026-07-12',
      benchmark_return_20d: 1,
      data_source: 'live',
      explanation: 'RS is strong.',
      fallback_used: false,
      history_quality_score: 95,
      overall_rs_score: 92,
      rank: 4,
      return_20d: 12.4,
      return_5d: 3.1,
      return_60d: 18.2,
      rs_vs_qqq: 105,
      rs_vs_sector: 103,
      rs_vs_spy: 108,
      sector: 'Technology',
      sector_return_20d: 4,
      status: 'Strong',
      symbol: 'MU',
    },
    riskPlan: {
      atr_14: 2.1,
      current_price: 62.5,
      entry: 63,
      position_size_note: 'Use normal sizing.',
      reward_percent_target_1: 8,
      reward_percent_target_2: 14,
      risk_level: 'Medium',
      risk_percent: 5,
      risk_reward_target_1: 1.6,
      risk_reward_target_2: 2.8,
      stop_loss: 59.4,
      summary: 'Risk is manageable.',
      symbol: 'MU',
      target_1: 67.5,
      target_2: 71.5,
      volatility_level: 'Normal',
    },
    stock: makeStock(),
    stockRating: makeRating(),
    supportResistance: {
      as_of: '2026-07-12',
      breakout_level: 64.2,
      current_price: 62.5,
      data_source: 'live',
      fallback_used: false,
      moving_average_support: { ema_20: 60.1, ema_50: 57.8 },
      resistance_zones: [],
      stop_reference: 58.8,
      support_zones: [],
      symbol: 'MU',
    },
    volumeAnalysis: {
      accumulation_volume: true,
      average_volume_20: 100,
      breakout_volume: false,
      climax_run: false,
      data_source: 'live',
      distribution_volume: false,
      dry_up: false,
      relative_volume: 1.2,
      signals: ['Accumulation'],
      status: 'Supportive',
      summary: 'Volume is supportive.',
      symbol: 'MU',
      volume_quality: 'Strong',
      volume_quality_score: 80,
    },
  });

  assert(model.symbol === 'MU', 'symbol is preserved');
  assert(model.assessmentLabel === 'Constructive', 'assessment derives from score');
  assert(model.factors.length === 6, 'six rating factors are shown');
  assert(model.watchItems.some((item) => item.label === 'Breakout level'), 'watch list includes breakout level');
  assert(model.supportingMetrics.some((metric) => metric.label === 'Target 1' && metric.value === '$67.50'), 'supporting metrics include risk target');
  assert(model.sourceLabel === 'Mixed data', 'mixed rating data is labelled honestly');
  assert(!model.executiveSummary.body.includes('undefined'), 'summary avoids undefined values');
  assert(model.executiveSummary.source === 'backend', 'specific rating explanation is preserved as backend summary');

  const mockModel = buildStockDetailOverview({
    stock: makeStock({ data_source: 'mock', is_live: false }),
    stockRating: makeRating({ data_quality: { overall_mode: 'mock' } }),
  });
  assert(mockModel.sourceLabel === 'Mock data', 'mock data is labelled');

  const placeholderModel = buildStockDetailOverview({
    stock: makeStock({ setup: 'Setup updating' }),
    stockRating: makeRating({
      explanation: 'NVDA screens as constructive with a 70/100 rating score; risk is currently moderate. The current setup is Setup updating.',
    }),
    supportResistance: {
      as_of: '2026-07-12',
      breakout_level: 64.2,
      current_price: 62.5,
      data_source: 'live',
      fallback_used: false,
      moving_average_support: { ema_20: 60.1, ema_50: 57.8 },
      resistance_zones: [],
      stop_reference: 58.8,
      support_zones: [],
      symbol: 'MU',
    },
  });
  assert(!placeholderModel.executiveSummary.body.toLowerCase().includes('setup updating'), 'placeholder setup text is removed');
  assert(!placeholderModel.executiveSummary.body.toLowerCase().includes('screens as'), 'generic screens-as wording is removed');
  assert(placeholderModel.executiveSummary.body.includes('$64.20'), 'real confirmation level is included');
  assert(placeholderModel.assessmentEvidence.length <= 3, 'assessment renders no more than three evidence rows');
}

run();
