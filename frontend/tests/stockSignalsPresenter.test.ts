import {
  buildSignalSummary,
  classifyComparison,
  comparisonLabel,
  getActiveVolumeSignals,
  getVolumeParticipationState,
  leadershipPreview,
  relativeStrengthInterpretation,
  volumeInterpretation,
} from '../src/features/stock-detail/signals/signalPresenter';
import type {
  MultiTimeframeTechnicalSignals,
  RelativeStrengthItem,
  StockLeadershipSignal,
  VolumeAnalysis,
} from '../src/types/market';

function assert(condition: unknown, message: string) {
  if (!condition) {
    throw new Error(message);
  }
}

const relativeStrength: RelativeStrengthItem = {
  as_of: '2026-07-14T00:00:00Z',
  benchmark_return_20d: 2,
  data_source: 'polygon',
  fallback_used: false,
  history_quality_score: 90,
  overall_rs_score: 52,
  rank: 3,
  return_5d: 1,
  return_20d: 4.3,
  return_60d: 20.3,
  rs_vs_qqq: 42,
  rs_vs_sector: 57,
  rs_vs_spy: 51,
  sector: 'Technology',
  sector_return_20d: 3,
  status: 'Neutral',
  symbol: 'NVDA',
  explanation: 'Relative strength is close to average.',
};

const volume: VolumeAnalysis = {
  accumulation_volume: true,
  analysis_is_live: true,
  as_of: '2026-07-14T00:00:00Z',
  average_volume_20: 1000000,
  breakout_volume: true,
  climax_run: false,
  data_source: 'polygon',
  distribution_volume: false,
  dry_up: false,
  fallback_used: false,
  history_quality_score: 90,
  relative_volume: 1.8,
  signals: ['Volume Surge', 'Breakout Volume', 'Accumulation Volume'],
  status: 'High Volume',
  summary: 'Volume supports the move.',
  symbol: 'NVDA',
  volume_quality: 'Strong',
  volume_quality_score: 82,
};

const leadership: StockLeadershipSignal = {
  asOf: '2026-07-14T00:00:00Z',
  availableInputs: 5,
  dataStatus: 'mixed',
  explanation: 'Sector-relative strength is improving, but QQQ confirmation remains incomplete.',
  limitingEvidence: ['SPY/QQQ-relative strength remains unconfirmed'],
  methodologyVersion: '1',
  positiveEvidence: ['Strong sector-relative performance', 'Strong participation supports the move'],
  requiredInputs: 6,
  score: 72,
  signal: 'emerging_leader',
  strength: 'moderate',
};

const timeframes: MultiTimeframeTechnicalSignals = {
  generatedAt: '2026-07-14T00:00:00Z',
  long: {
    asOf: null,
    availableInputs: 2,
    dataStatus: 'unavailable',
    explanation: 'Unavailable.',
    headline: 'Unavailable.',
    horizonLabel: '3–12 months',
    negativeEvidence: [],
    positiveEvidence: [],
    requiredInputs: 10,
    score: null,
    signal: 'unavailable',
    strength: 'unavailable',
    timeframe: 'long',
  },
  medium: {
    asOf: '2026-07-14T00:00:00Z',
    availableInputs: 8,
    dataStatus: 'mixed',
    explanation: 'Bullish.',
    headline: 'Bullish.',
    horizonLabel: '2–8 weeks',
    negativeEvidence: [],
    positiveEvidence: [],
    requiredInputs: 9,
    score: 90,
    signal: 'strong_bullish',
    strength: 'strong',
    timeframe: 'medium',
  },
  methodologyVersion: '1',
  overallDataStatus: 'mixed',
  short: {
    asOf: '2026-07-14T00:00:00Z',
    availableInputs: 7,
    dataStatus: 'mixed',
    explanation: 'Bullish.',
    headline: 'Bullish.',
    horizonLabel: '1–10 trading days',
    negativeEvidence: [],
    positiveEvidence: [],
    requiredInputs: 8,
    score: 87,
    signal: 'strong_bullish',
    strength: 'strong',
    timeframe: 'short',
  },
};

function run() {
  const summary = buildSignalSummary({
    leadership,
    relativeStrength,
    timeframeSignals: timeframes,
    volume,
  });
  assert(summary.headline.includes('Momentum is constructive'), 'summary uses momentum condition');
  assert(summary.body.includes('emerging leader'), 'summary includes leadership condition');
  assert(summary.body.includes('QQQ'), 'summary identifies missing confirmation');

  assert(comparisonLabel(classifyComparison(52)) === 'In line', 'neutral RS is labelled in line');
  assert(comparisonLabel(classifyComparison(57)) === 'Stronger', 'sector RS is labelled stronger');
  assert(relativeStrengthInterpretation(relativeStrength).includes('Sector performance is stronger'), 'RS interpretation explains mixed comparisons concisely');

  assert(getVolumeParticipationState(volume) === 'strong', 'relative volume produces strong participation');
  assert(getActiveVolumeSignals(volume).includes('Accumulation present'), 'active volume flags are visible');
  assert(volumeInterpretation(volume).includes('Above-normal buying'), 'volume interpretation is concise');

  assert(leadershipPreview(leadership).includes('Emerging Leader'), 'leadership preview labels signal');
}

run();
