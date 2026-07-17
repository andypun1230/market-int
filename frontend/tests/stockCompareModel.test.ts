import {
  buildEqualWeightComposite,
  buildStockComparisonDashboard,
  buildThemeBenchmark,
  calculatePeerRank,
  classifyStockRelativeStrength,
  deduplicateDailyHistory,
  formatDataSourceLabel,
  getComparisonAsOfDate,
  isRenderableComparisonSeries,
  normalizeHistorySeries,
  normalizeHistoryTimestamp,
  resolveStockThemeContext,
  selectComparisonWindow,
  type PeerComparisonViewModel,
  type StockPerformanceSummary,
} from '../src/features/stock-detail/compare/stockCompareModel';
import type { CandleData, HistoryData } from '../src/types/market';

function assert(condition: unknown, message: string) {
  if (!condition) {
    throw new Error(message);
  }
}

function assertNear(actual: number | null | undefined, expected: number, message: string, tolerance = 0.001) {
  assert(typeof actual === 'number' && Math.abs(actual - expected) <= tolerance, message);
}

function history(symbol: string, closes: number[]): HistoryData {
  return {
    as_of: '2026-07-15T00:00:00Z',
    candles: closes.map((close, index) => ({
      close,
      high: close + 1,
      low: close - 1,
      open: close - 0.5,
      timestamp: new Date(Date.UTC(2026, 6, index + 1)).toISOString(),
      volume: 1_000_000 + index * 1000,
    })),
    fallback_used: false,
    is_live: false,
    is_stale: false,
    source: 'mock',
    symbol,
    timeframe: 'D',
  };
}

function historyWithTimestamps(symbol: string, candles: Array<Partial<CandleData> & { close: number; timestamp: string | number }>): HistoryData {
  return {
    as_of: '2026-07-15T00:00:00Z',
    candles: candles.map((candle, index) => ({
      close: candle.close,
      high: candle.high ?? candle.close + 1,
      low: candle.low ?? candle.close - 1,
      open: candle.open ?? candle.close - 0.5,
      timestamp: candle.timestamp as string,
      volume: candle.volume ?? 1_000_000 + index * 1000,
    })),
    fallback_used: false,
    is_live: false,
    is_stale: false,
    source: 'generated_test_data',
    symbol,
    timeframe: 'D',
  };
}

function dashboardHistories() {
  return {
    MU: history('MU', [100, 106, 112, 120]),
    SNDK: history('SNDK', [100, 104, 108, 110]),
    SPY: history('SPY', [100, 101, 103, 105]),
    STX: history('STX', [100, 102, 104, 106]),
    WDC: history('WDC', [100, 103, 106, 108]),
  };
}

function runTests() {
  const context = resolveStockThemeContext('MU');
  assert(context.primaryThemeName === 'Memory', 'MU resolves to Memory theme');
  assert(context.peerSymbols.join(',') === 'SNDK,WDC,STX', 'primary theme peers exclude selected stock');

  const noTheme = resolveStockThemeContext('TSLA');
  assert(noTheme.primaryThemeName === null, 'unmapped symbol keeps no-theme state');

  assert(normalizeHistoryTimestamp('2026-07-15') === '2026-07-15T00:00:00.000Z', 'ISO dates normalize to UTC midnight');
  assert(normalizeHistoryTimestamp('2026-07-15T13:30:00+08:00')?.startsWith('2026-07-15T05:30:00'), 'ISO datetimes normalize');
  const july2026Milliseconds = Date.UTC(2026, 6, 15);
  assert(normalizeHistoryTimestamp(july2026Milliseconds / 1000)?.startsWith('2026-07-15'), 'Unix seconds normalize');
  assert(normalizeHistoryTimestamp(july2026Milliseconds)?.startsWith('2026-07-15'), 'Unix milliseconds normalize');

  const deduped = deduplicateDailyHistory(historyWithTimestamps('DUP', [
    { close: 10, timestamp: '2026-07-01' },
    { close: 11, timestamp: '2026-07-01T20:00:00Z' },
    { close: 12, timestamp: 'bad-date' },
    { close: 13, timestamp: '2026-07-02' },
  ]));
  assert(deduped.length === 2, 'invalid timestamps are omitted and same-day candles are deduplicated');
  assert(deduped[0]?.close === 11, 'same-day duplicate keeps the last valid point');

  const series = normalizeHistorySeries(history('TEST', [50, 55, 60]));
  assert(series[0]?.value === 0, 'normalized series starts at 0');
  assert(Math.round(series.at(-1)?.value ?? 0) === 20, 'normalized series calculates period return');

  const composite = buildEqualWeightComposite([
    normalizeHistorySeries(history('A', [100, 110])),
    normalizeHistorySeries(history('B', [100, 120])),
  ]);
  assert(composite[0]?.value === 0, 'equal-weight composite starts at 0');
  assertNear(composite.at(-1)?.value, 15, 'equal-weight composite averages aligned normalized returns');
  assert(isRenderableComparisonSeries(composite), 'two-point finite composite is renderable');

  const partialComposite = buildEqualWeightComposite([
    normalizeHistorySeries(historyWithTimestamps('A', [
      { close: 100, timestamp: '2026-07-01' },
      { close: 105, timestamp: '2026-07-02' },
      { close: 110, timestamp: '2026-07-03' },
    ])),
    normalizeHistorySeries(historyWithTimestamps('B', [
      { close: 100, timestamp: '2026-07-01' },
      { close: 106, timestamp: '2026-07-03' },
    ])),
    normalizeHistorySeries(historyWithTimestamps('C', [
      { close: 100, timestamp: '2026-07-02' },
      { close: 104, timestamp: '2026-07-03' },
    ])),
  ], 2);
  assert(partialComposite.length === 3, 'equal-weight composite keeps dates with enough partial peers');

  const benchmark = buildThemeBenchmark(context, dashboardHistories(), 'MU');
  assert(benchmark?.kind === 'equal_weight_composite', 'theme benchmark uses equal-weight composite first');
  assert(benchmark?.constituentCount === 3, 'selected stock is excluded from composite when enough peers remain');

  const model = buildStockComparisonDashboard({
    histories: dashboardHistories(),
    symbol: 'MU',
    timeframe: '1M',
  });
  assert(model.chart.series.length === 3, 'chart includes stock, SPY, and theme when available');
  assertNear(model.performance.stockReturn, 20, 'stock period return is calculated');
  assertNear(model.performance.spyReturn, 5, 'SPY period return is calculated');
  assertNear(model.performance.themeReturn, 8, 'theme return comes from peer composite', 0.5);
  assertNear(model.performance.edgeVsSpy, 15, 'edge versus SPY uses percentage points');
  assertNear(model.performance.edgeVsTheme, 12, 'edge versus theme uses percentage points', 0.5);
  assert(model.relativeStrength.state === 'leading_market_and_theme', 'strong stock classifies as leading market and theme');
  assert(model.peerRanking.rank === 1, 'selected stock ranks first');
  assert(model.peerRanking.rankedCount === 4, 'ranking includes selected stock and valid peers');
  assert(model.peerRanking.percentile === 100, 'top peer receives 100th percentile');
  assert(model.leadership.classification === 'Theme Leader', 'leadership read matches ranking and relative strength');
  assert(model.dataQuality.benchmarkMethod.includes('Equal-weight'), 'data quality discloses benchmark method');
  assert(model.dataQuality.dataSource === 'mock', 'mock data source is preserved');
  assert(model.dataQuality.dataSourceLabel === 'Mock data', 'mock source gets a user-facing label');
  assert(model.dataQuality.unavailableReason === null, 'valid chart does not carry unavailable reason');
  assert(model.dataQuality.alignment.asOfDate === '2026-07-04', 'comparison as-of uses latest shared timestamp');

  const fixedMockDateModel = buildStockComparisonDashboard({
    histories: {
      ARM: historyWithTimestamps('ARM', [
        { close: 100, timestamp: '2024-01-01' },
        { close: 105, timestamp: '2024-01-05' },
        { close: 112, timestamp: '2024-01-08' },
      ]),
      AVGO: historyWithTimestamps('AVGO', [
        { close: 100, timestamp: '2024-01-01T16:00:00-05:00' },
        { close: 104, timestamp: '2024-01-05T16:00:00-05:00' },
        { close: 108, timestamp: '2024-01-08T16:00:00-05:00' },
      ]),
      NVDA: historyWithTimestamps('NVDA', [
        { close: 100, timestamp: '2024-01-01' },
        { close: 103, timestamp: '2024-01-08' },
      ]),
      AMD: historyWithTimestamps('AMD', [
        { close: 100, timestamp: '2024-01-01' },
        { close: 101, timestamp: '2024-01-05' },
        { close: 103, timestamp: '2024-01-08' },
      ]),
      INTC: historyWithTimestamps('INTC', [
        { close: 100, timestamp: '2024-01-01' },
        { close: 99, timestamp: '2024-01-05' },
        { close: 102, timestamp: '2024-01-08' },
      ]),
      SPY: historyWithTimestamps('SPY', [
        { close: 100, timestamp: '2024-01-01T00:00:00Z' },
        { close: 101, timestamp: '2024-01-05T00:00:00Z' },
        { close: 103, timestamp: '2024-01-08T00:00:00Z' },
      ]),
    },
    symbol: 'ARM',
    timeframe: '1M',
  });
  assert(fixedMockDateModel.chart.series.length === 3, 'ARM + SPY + semiconductor theme renders from fixed mock dates');
  assert(fixedMockDateModel.themeBenchmark?.kind === 'equal_weight_composite', 'ARM theme benchmark is derived from semiconductor peers');
  assert(fixedMockDateModel.dataQuality.dataSourceLabel === 'Test data', 'generated_test_data displays as Test data');

  const partialThemeModel = buildStockComparisonDashboard({
    histories: { SPY: history('SPY', [100, 105]), MU: history('MU', [100, 112]) },
    symbol: 'MU',
    timeframe: '1M',
  });
  assert(partialThemeModel.chart.series.length === 2, 'stock and SPY still render when theme peers are missing');
  assert(partialThemeModel.dataQuality.partialNotice?.includes('Theme benchmark unavailable'), 'missing theme peers become a partial notice');

  const following = buildStockComparisonDashboard({
    histories: {
      MU: history('MU', [100, 103, 106, 109]),
      SNDK: history('SNDK', [100, 104, 108, 110]),
      SPY: history('SPY', [100, 101, 103, 105]),
      STX: history('STX', [100, 102, 105, 108]),
      WDC: history('WDC', [100, 103, 106, 109]),
    },
    symbol: 'MU',
    timeframe: '1M',
  });
  assert(following.relativeStrength.state === 'following_theme', 'stock near theme return classifies as following theme');

  const lagging = buildStockComparisonDashboard({
    histories: {
      MU: history('MU', [100, 98, 96, 94]),
      SNDK: history('SNDK', [100, 104, 108, 110]),
      SPY: history('SPY', [100, 101, 103, 105]),
      STX: history('STX', [100, 102, 105, 108]),
      WDC: history('WDC', [100, 103, 106, 109]),
    },
    symbol: 'MU',
    timeframe: '1M',
  });
  assert(lagging.relativeStrength.state === 'lagging_market_and_peers', 'weak stock classifies as lagging market and peers');

  const performance: StockPerformanceSummary = {
    edgeVsSpy: 0.7,
    edgeVsTheme: 0.4,
    spyReturn: 4,
    stockReturn: 4.7,
    themeReturn: 4.3,
    timeframe: '1M',
  };
  const ranking = calculatePeerRank([
    peer('AAA', 4.7, true),
    peer('BBB', 4.6, false),
    peer('CCC', 4.4, false),
  ], 'AAA');
  const mixed = classifyStockRelativeStrength(performance, ranking, normalizeHistorySeries(history('AAA', [100, 102, 103, 104.7])));
  assert(mixed.state === 'mixed', 'tiny differences return mixed');

  const missingTheme = buildStockComparisonDashboard({
    histories: { SPY: history('SPY', [100, 105]), TSLA: history('TSLA', [100, 112]) },
    symbol: 'TSLA',
    timeframe: '1M',
  });
  assert(missingTheme.themeBenchmark === null, 'missing theme does not fabricate benchmark');
  assert(missingTheme.chart.series.length === 2, 'missing theme still allows stock versus SPY chart');
  assert(missingTheme.dataQuality.warnings.length > 0, 'missing theme emits compact warning');

  const unavailable = buildStockComparisonDashboard({
    histories: { SPY: history('SPY', [100, 105]) },
    symbol: 'MU',
    timeframe: '1M',
  });
  assert(unavailable.chart.series.length === 0, 'full unavailable state has no renderable series');
  assert(unavailable.dataQuality.unavailableReason === 'stock_history_missing', 'missing stock history has typed reason');

  const onePoint = buildStockComparisonDashboard({
    histories: { MU: history('MU', [100]), SPY: history('SPY', [100]) },
    symbol: 'MU',
    timeframe: '1W',
  });
  assert(onePoint.chart.series.length === 0, 'one-point series is rejected');
  assert(onePoint.dataQuality.unavailableReason === 'insufficient_points', 'one-point data reports insufficient points');

  assert(getComparisonAsOfDate({
    AAA: historyWithTimestamps('AAA', [{ close: 10, timestamp: '2024-01-01' }, { close: 11, timestamp: '2024-01-03' }]),
    BBB: historyWithTimestamps('BBB', [{ close: 10, timestamp: '2024-01-02' }, { close: 11, timestamp: '2024-01-03' }]),
  }, ['AAA', 'BBB']) === '2024-01-03', 'as-of date uses latest shared date');

  const fiveSessions = selectComparisonWindow(deduplicateDailyHistory(history('RANGE', [1, 2, 3, 4, 5, 6, 7])), '1W');
  assert(fiveSessions.length === 5, '1W timeframe selects five sessions');
  assert(formatDataSourceLabel('generated_test_data') === 'Test data', 'generated_test_data label is user-facing');
  assert(formatDataSourceLabel('mock') === 'Mock data', 'mock label is user-facing');
  assert(formatDataSourceLabel('mixed') === 'Mixed sources', 'mixed label is user-facing');
  assert(!formatDataSourceLabel('generated_test_data').includes('_'), 'raw source enum is not displayed');
}

function peer(symbol: string, periodReturn: number, isSelectedStock: boolean): PeerComparisonViewModel {
  return {
    distanceFromHigh: null,
    isSelectedStock,
    momentum: 'Healthy',
    periodReturn,
    relativeStrength: 'neutral',
    setup: 'N/A',
    symbol,
    trend: 'Constructive',
    volume: 'N/A',
  };
}

runTests();
