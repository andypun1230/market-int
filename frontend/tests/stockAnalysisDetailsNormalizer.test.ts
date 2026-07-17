import { normalizeStockAnalysisDetails } from '../src/features/stock-detail/stockAnalysisDetailsNormalizer';
import type { MultiTimeframeTechnicalSignals, StockAnalysisAggregate } from '../src/types/market';

function assert(condition: unknown, message: string) {
  if (!condition) {
    throw new Error(message);
  }
}

function signal(score: number | null, state = 'bullish') {
  return {
    asOf: '2026-07-12T20:00:00Z',
    availableInputs: score == null ? 0 : 5,
    dataStatus: score == null ? 'unavailable' : 'mixed',
    explanation: score == null ? 'Not enough history.' : 'Price structure is constructive.',
    headline: score == null ? 'Signal unavailable.' : 'Trend is bullish.',
    horizonLabel: '1–10 trading days',
    negativeEvidence: [],
    positiveEvidence: score == null ? [] : [{ key: 'above_ema20', label: 'Price is above EMA20' }],
    requiredInputs: 6,
    score,
    signal: state,
    strength: score == null ? 'unavailable' : 'moderate',
    timeframe: 'short',
  };
}

function signals(overrides: Partial<MultiTimeframeTechnicalSignals> = {}): MultiTimeframeTechnicalSignals {
  return {
    generatedAt: '2026-07-12T20:00:00Z',
    long: { ...signal(null, 'unavailable'), horizonLabel: '3–12 months', timeframe: 'long' },
    medium: { ...signal(52, 'neutral'), horizonLabel: '2–8 weeks', timeframe: 'medium' },
    methodologyVersion: '1',
    overallDataStatus: 'mixed',
    short: { ...signal(0, 'strong_bearish'), timeframe: 'short' },
    ...overrides,
  } as MultiTimeframeTechnicalSignals;
}

function aggregate(overrides: Partial<StockAnalysisAggregate> = {}): StockAnalysisAggregate {
  return {
    symbol: 'NVDA',
    ...overrides,
  };
}

function run() {
  const camel = normalizeStockAnalysisDetails(aggregate({ multiTimeframeSignals: signals() }));
  assert(camel.multiTimeframeSignals?.short.score === 0, 'camelCase signals preserve zero score');
  assert(camel.multiTimeframeSignals?.medium.signal === 'neutral', 'camelCase signals keep medium result');
  assert(camel.multiTimeframeSignals?.long.signal === 'unavailable', 'unavailable long does not remove the object');

  const snake = normalizeStockAnalysisDetails({
    ...aggregate(),
    multi_timeframe_signals: signals({ overallDataStatus: 'cached' }),
  });
  assert(snake.multiTimeframeSignals?.overallDataStatus === 'cached', 'snake_case response is normalized');

  const nestedSnake = normalizeStockAnalysisDetails({
    ...aggregate(),
    data: {
      leadership_signal: {
        available_inputs: 5,
        data_status: 'mixed',
        explanation: 'Sector-relative strength is improving.',
        limiting_evidence: ['QQQ-relative strength remains unconfirmed'],
        methodology_version: '1',
        positive_evidence: ['Strong sector-relative performance'],
        required_inputs: 6,
        score: '72',
        signal: 'emerging_leader',
        strength: 'moderate',
      },
      multi_timeframe_signals: {
        generated_at: '2026-07-12T20:00:00Z',
        methodology_version: '2',
        overall_data_status: 'mixed',
        short: {
          as_of: '2026-07-12T20:00:00Z',
          available_inputs: 7,
          data_status: 'mixed',
          explanation: 'Short-term trend is strongly bullish.',
          headline: 'Short-term trend is strongly bullish.',
          horizon_label: '1–10 trading days',
          negative_evidence: [],
          positive_evidence: [{ key: 'above_ema20', label: 'Price is above EMA20', source_status: 'live', value: 'above' }],
          required_inputs: 8,
          score: '87',
          signal: 'strong_bullish',
          strength: 'strong',
          timeframe: 'short',
        },
        medium: {
          available_inputs: 8,
          data_status: 'mixed',
          explanation: 'Medium-term trend is strongly bullish.',
          headline: 'Medium-term trend is strongly bullish.',
          horizon_label: '2–8 weeks',
          required_inputs: 9,
          score: 90,
          signal: 'strong_bullish',
          strength: 'strong',
          timeframe: 'medium',
        },
        long: {
          available_inputs: 2,
          data_status: 'unavailable',
          explanation: 'Not enough long-term inputs are available.',
          headline: 'Long-term signal unavailable.',
          horizon_label: '3–12 months',
          required_inputs: 10,
          score: null,
          signal: 'unavailable',
          strength: 'unavailable',
          timeframe: 'long',
        },
      },
    },
  });
  assert(nestedSnake.multiTimeframeSignals?.short.signal === 'strong_bullish', 'nested snake_case short signal is normalized');
  assert(nestedSnake.multiTimeframeSignals?.short.score === 87, 'numeric string score is parsed');
  assert(nestedSnake.multiTimeframeSignals?.short.positiveEvidence[0]?.sourceStatus === 'live', 'snake_case evidence source is normalized');
  assert(nestedSnake.multiTimeframeSignals?.medium.score === 90, 'medium signal survives normalization');
  assert(nestedSnake.multiTimeframeSignals?.long.signal === 'unavailable', 'long unavailable renders independently');
  assert(nestedSnake.leadershipSignal?.signal === 'emerging_leader', 'nested snake_case leadership signal is normalized');
  assert(nestedSnake.leadershipSignal?.score === 72, 'leadership numeric string score is parsed');

  const missing = normalizeStockAnalysisDetails(aggregate());
  assert(missing.multiTimeframeSignals === undefined, 'missing signal field stays safely absent');
}

run();
