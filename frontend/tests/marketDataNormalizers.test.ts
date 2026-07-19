import {
  extractNumber,
  extractText,
  normalizeBreadthResponse,
  normalizeDecisionIntelligenceResponse,
  normalizeInstitutionalActivityResponse,
  normalizeInstitutionalIntelligenceResponse,
} from '../src/utils/marketDataNormalizers';

function assert(condition: unknown, message: string) {
  if (!condition) {
    throw new Error(message);
  }
}

function run() {
  const snakeCaseBreadth = normalizeBreadthResponse({
    breadth: {
      market: {
        total_stocks: 0,
        advancing_stocks: 0,
        declining_stocks: 0,
        advance_decline_ratio: 0,
        percent_above_20ema: 0,
        percent_above_50ema: '61.8',
        percent_above_200ema: { percentage: 42 },
        coverage_percent: { value: 88 },
        advance_decline_ratio_display: '0.35',
        advance_decline_ratio_smoothed: 0.351,
        ratio_method: 'raw=advancing/declining',
        coverage_dimensions: {
          universe: { eligible: 101, total: 101, ratio: 1, display: '101/101' },
          ema200: { eligible: 100, total: 101, ratio: 0.990099, display: '100/101' },
        },
        data_confidence: { score: 99, label: 'High', reason: 'Complete coverage.', source_snapshot_id: 'breadth-fixture', calculated_at: '2026-07-17T20:00:00+00:00' },
        signal_confidence: { score: 65, label: 'Moderate', reason: 'Mixed current breadth inputs.', source_snapshot_id: 'breadth-fixture', calculated_at: '2026-07-17T20:00:00+00:00' },
        overall_mode: 'mock',
      },
      sectors: [
        {
          sector: 'Technology',
          total_stocks: 10,
          advancing_stocks: 6,
          declining_stocks: 4,
          percent_above_50ema: { label: '60%' },
        },
      ],
    },
  });
  assert(snakeCaseBreadth?.market.total_stocks === 0, 'preserves zero total stocks');
  assert(snakeCaseBreadth?.market.percent_above_50ema === 61.8, 'parses numeric strings');
  assert(snakeCaseBreadth?.market.percent_above_200ema === 42, 'parses percentage object');
  assert(snakeCaseBreadth?.market.coverage_percent === 88, 'parses value object');
  assert(snakeCaseBreadth?.sectors[0]?.percent_above_50ema === 60, 'normalizes sector breadth');
  assert(snakeCaseBreadth?.market.signal_confidence?.score === 65, 'preserves canonical signal confidence through the compatibility normalizer');
  assert(snakeCaseBreadth?.market.signal_confidence?.source_snapshot_id === 'breadth-fixture', 'preserves signal confidence provenance');
  assert(snakeCaseBreadth?.market.data_confidence?.label === 'High', 'preserves distinct data confidence');
  assert(snakeCaseBreadth?.market.coverage_dimensions?.ema200?.display === '100/101', 'preserves long-indicator eligibility');
  assert(snakeCaseBreadth?.market.advance_decline_ratio_display === '0.35', 'preserves canonical A/D display semantics');

  const camelCaseBreadth = normalizeBreadthResponse({
    data: {
      breadth: {
        market: {
          totalStocks: 100,
          advancing: 80,
          declining: 20,
          percentAbove20Ema: 70,
          percentAbove50Ema: 65,
          percentAbove200Ema: 55,
          coveragePercent: 90,
          mode: 'mixed',
        },
        sectorBreadth: [],
      },
    },
  });
  assert(camelCaseBreadth?.market.advancing_stocks === 80, 'supports camelCase advancing');
  assert(camelCaseBreadth?.market.advance_decline_ratio === 4, 'derives A/D ratio');
  const zeroDecliners = normalizeBreadthResponse({
    market: {
      total_stocks: 10,
      advancing_stocks: 10,
      declining_stocks: 0,
      percent_above_20ema: 80,
      percent_above_50ema: 80,
      percent_above_200ema: 80,
    },
    sectors: [],
  });
  assert(zeroDecliners?.market.advance_decline_ratio === null, 'never fabricates an infinite A/D ratio for zero decliners');

  const decision = normalizeDecisionIntelligenceResponse({
    decision_dashboard: {
      playbook: { headline: 'Stay selective' },
      aggressiveness: { score: 70 },
      trading_styles: { preferred_style: 'Momentum' },
    },
  });
  assert(decision?.playbook.headline === 'Stay selective', 'normalizes decision dashboard');

  const activity = normalizeInstitutionalActivityResponse({
    institutionalActivity: {
      bias: {
        institutionalBias: 'Bullish',
        distribution: { count: 0 },
        accumulation: '14',
        stall: 2,
        churning: 3,
        followThroughDay: { triggered: true, date: '2026-07-02', index: 'SPY', gainPercent: '1.28' },
      },
      indexes: [],
    },
  });
  assert(activity?.bias.distribution_count === 0, 'preserves zero distribution');
  assert(activity?.bias.accumulation_count === 14, 'parses accumulation string');
  assert(activity?.bias.follow_through_day.gain_percent === 1.28, 'normalizes follow-through day');

  const intelligence = normalizeInstitutionalIntelligenceResponse({
    sentiment: { score: 65, status: 'Positive' },
    moneyFlow: { score: 58, status: 'Neutral' },
    institutional: { score: 92, status: 'Bullish' },
    options: { score: 60, status: 'Mixed' },
    liquidity: { score: 66, status: 'Adequate' },
    summary: { label: 'Constructive' },
  });
  assert(intelligence?.summary === 'Constructive', 'normalizes institutional intelligence summary object');

  assert(extractNumber({ label: '42%' }) === 42, 'extractNumber handles labels');
  assert(extractText({ value: 0 }) === '0', 'extractText preserves zero');
}

run();
