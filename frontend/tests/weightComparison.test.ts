import {
  buildConcentrationBreadthSignal,
  buildWeightComparisonPair,
  classifyConcentrationState,
  concentrationStateLabel,
  getAvailableWeightPairs,
} from '../src/features/market/weightComparison';
import type { CandleData, HistoryData } from '../src/types/market';

function assert(condition: unknown, message: string) {
  if (!condition) {
    throw new Error(message);
  }
}

function history(symbol: string, closes: number[]): HistoryData {
  return {
    as_of: '2026-07-15T00:00:00Z',
    candles: closes.map((close, index): CandleData => ({
      close,
      high: close + 1,
      low: close - 1,
      open: close,
      timestamp: new Date(Date.UTC(2026, 0, index + 1)).toISOString(),
      volume: 1_000_000,
    })),
    fallback_used: false,
    is_live: false,
    is_stale: false,
    source: 'test',
    symbol,
    timeframe: 'D',
  };
}

function series(start: number, end: number, length = 24) {
  return Array.from({ length }, (_, index) => start + ((end - start) * index) / (length - 1));
}

function run() {
  assert(classifyConcentrationState(0.2) === 'broad_participation', 'tiny spread returns broad participation');
  assert(classifyConcentrationState(1.8) === 'mild_concentration', 'mild spread returns mild concentration');
  assert(classifyConcentrationState(4.2) === 'mega_cap_concentration', 'large weighted spread returns mega-cap concentration');
  assert(classifyConcentrationState(-1.4) === 'equal_weight_leadership', 'equal-weight outperformance classifies');
  assert(classifyConcentrationState(null) === 'unavailable', 'missing spread is unavailable');
  assert(concentrationStateLabel('mega_cap_concentration') === 'Mega-Cap Concentration', 'state labels are user-facing');

  const histories = {
    SPY: history('SPY', series(100, 104)),
    RSP: history('RSP', series(100, 101)),
    QQQ: history('QQQ', series(100, 105)),
    QQEW: history('QQEW', series(100, 101)),
  };
  const model = buildWeightComparisonPair('sp500', histories, '1M');
  assert(Math.abs((model.weightedPeriodReturn ?? 0) - 3.64) < 0.1, 'weighted return calculates');
  assert(Math.abs((model.equalWeightPeriodReturn ?? 0) - 0.91) < 0.1, 'equal-weight return calculates');
  assert(Math.abs((model.spreadPoints ?? 0) - 2.73) < 0.1, 'spread is percentage points');
  assert(model.points[0].weightedReturn === 0 && model.points[0].equalWeightReturn === 0, 'series normalize to the same starting point');
  assert(model.state === 'mild_concentration', 'spread state derives from data');
  assert(buildConcentrationBreadthSignal(model)?.status === model.stateLabel, 'breadth signal reuses indexes state');
  assert(getAvailableWeightPairs(histories).includes('nasdaq100'), 'QQQ vs QQEW appears when both histories exist');
  assert(!getAvailableWeightPairs({ SPY: histories.SPY, RSP: histories.RSP, QQQ: histories.QQQ }).includes('nasdaq100'), 'missing QQEW hides Nasdaq pair');

  const partial = buildWeightComparisonPair('sp500', { SPY: history('SPY', [100]), RSP: history('RSP', [100]) }, '1M');
  assert(partial.confidence === 'unavailable', 'partial history lowers confidence to unavailable');
  assert(partial.state === 'unavailable', 'partial history does not produce a contradictory label');
}

run();
