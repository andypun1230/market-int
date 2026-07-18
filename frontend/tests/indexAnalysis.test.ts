import {
  analyzeIndexes,
  buildIndexTrendSummary,
  calculateAverageVolume,
  calculatePeriodReturn,
  classifyIndexTrend,
  classifyVolumeConfirmation,
  deriveLeadershipRead,
  deriveMarketLeadershipTrend,
  normalizeIndexSeries,
} from '../src/features/market/indexAnalysis';
import type { CandleData, HistoryData, IndexSnapshot } from '../src/types/market';

function assert(condition: unknown, message: string) {
  if (!condition) {
    throw new Error(message);
  }
}

function candle(index: number, close: number, volume = 1_000_000): CandleData {
  return {
    close,
    high: close + 1,
    low: close - 1,
    open: close - 0.5,
    timestamp: new Date(Date.UTC(2026, 0, index + 1, 20)).toISOString(),
    volume,
  };
}

function history(symbol: string, closes: number[], volume = 1_000_000): HistoryData {
  return {
    as_of: '2026-07-14T20:00:00Z',
    candles: closes.map((close, index) => candle(index, close, volume + index * 1_000)),
    fallback_used: false,
    is_live: true,
    is_stale: false,
    source: 'test',
    symbol,
    timeframe: 'D',
  };
}

function snapshot(overrides: Partial<IndexSnapshot> = {}): IndexSnapshot {
  return {
    change: 1,
    change_percent: 1,
    ema_20: 105,
    ema_50: 100,
    ema_200: 90,
    price: 110,
    rsi_14: 62,
    sma_50: 100,
    symbol: 'SPY',
    volume: 1_200_000,
    ...overrides,
  };
}

function run() {
  const spyHistory = history('SPY', [100, 102, 104, 106, 108]);
  const normalized = normalizeIndexSeries(spyHistory.candles, '1W');
  assert(normalized[0]?.value === 0, 'normalized series starts at zero');
  assert(Math.round((normalized.at(-1)?.value ?? 0) * 10) / 10 === 8, 'normalized series calculates return');
  assert(Math.round((calculatePeriodReturn(spyHistory.candles, '1W') ?? 0) * 10) / 10 === 8, 'period return calculates');
  assert(calculateAverageVolume(spyHistory.candles) !== null, 'average volume calculates with partial history');

  const strongTrend = classifyIndexTrend(snapshot(), 3);
  assert(strongTrend.state === 'strong_uptrend', 'strong EMA stack maps to strong uptrend');

  const pullbackTrend = classifyIndexTrend(snapshot({ price: 102, ema_20: 104, ema_50: 100, ema_200: 90 }), -1);
  assert(pullbackTrend.state === 'pullback_in_uptrend', 'short-term weakness in broader uptrend maps to pullback');

  const downtrend = classifyIndexTrend(snapshot({ price: 80, ema_20: 85, ema_50: 90, ema_200: 100 }), -4);
  assert(downtrend.state === 'downtrend', 'price below 50 and 200 EMA maps to downtrend');

  const confirmedBuying = classifyVolumeConfirmation(snapshot({ change_percent: 1.5, volume: 1_400_000 }), spyHistory.candles);
  assert(confirmedBuying.state === 'confirmed_buying', 'up day on above-average volume confirms buying');

  const distribution = classifyVolumeConfirmation(snapshot({ change_percent: -1.5, volume: 1_400_000 }), spyHistory.candles);
  assert(distribution.state === 'distribution', 'down day on above-average volume maps to distribution');

  const orderlyPullback = classifyVolumeConfirmation(snapshot({ change_percent: -1.5, volume: 700_000 }), spyHistory.candles);
  assert(orderlyPullback.state === 'orderly_pullback', 'down day on light volume maps to orderly pullback');

  const invalidDjiVolume = classifyVolumeConfirmation(
    snapshot({ change_percent: 1.5, symbol: 'DIA', volume: 7_000_000 }),
    [
      candle(0, 100, 200_000_000),
      candle(1, 101, 210_000_000),
      candle(2, 102, 1_000_000),
    ],
    'DIA',
  );
  assert(invalidDjiVolume.state === 'unavailable', 'incompatible DIA volume ratio is rejected');
  assert(invalidDjiVolume.sourceStatus === 'incompatible', 'invalid DIA volume is marked incompatible');

  const diaProxyVolume = classifyVolumeConfirmation(
    snapshot({ change_percent: 1.5, symbol: 'DIA', volume: 7_000_000 }),
    history('DIA', [100, 101, 102], 8_000_000).candles,
    'DIA',
  );
  assert(diaProxyVolume.sourceStatus === 'proxy', 'DIA volume uses a disclosed proxy when compatible');
  assert(diaProxyVolume.sourceLabel === 'Dow Jones ETF proxy volume', 'DIA proxy is labelled');

  const analyses = analyzeIndexes(
    [
      snapshot({ symbol: 'SPY', price: 108 }),
      snapshot({ symbol: 'QQQ', price: 130 }),
      snapshot({ symbol: 'DIA', price: 39000, ema_20: 38000, ema_50: 37000, ema_200: 36000 }),
      snapshot({ symbol: 'IWM', price: 210 }),
    ],
    {
      DIA: history('DIA', [100, 100.5, 101]),
      IWM: history('IWM', [100, 99, 98]),
      QQQ: history('QQQ', [100, 103, 106]),
      SPY: history('SPY', [100, 101, 102]),
    },
    '1W',
  );
  assert(analyses.length === 4, 'core display analysis includes SPY, QQQ, IWM, and DIA');
  assert(deriveLeadershipRead(analyses).title === 'Growth Leadership', 'QQQ leadership is detected');
  assert(deriveMarketLeadershipTrend(analyses).title === 'Growth Leadership', 'merged leadership/trend keeps leadership label');
  assert(buildIndexTrendSummary(analyses).length > 0, 'trend summary handles valid analyses');
  assert(analyses.every((analysis) => analysis.setup.label), 'setup classification returns display labels');
  assert(analyses.every((analysis) => analysis.setup.rows.length <= 6), 'setup rows remain concise');
  assert(analyses.every((analysis) => analysis.setup.rows.every((row) => !row.value.includes('undefined'))), 'setup rows avoid malformed text');
}

run();
