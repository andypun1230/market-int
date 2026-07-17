import {
  buildInstitutionalActivityChartViewModel,
  calculateInstitutionalPriceTicks,
  detectInstitutionalEvents,
  formatInstitutionalChartWindow,
  formatInstitutionalChartSourceKind,
  getInstitutionalSourceMapping,
  normalizeInstitutionalCandles,
  type InstitutionalCandleViewModel,
} from '../src/features/market/institutionalActivityChart';
import type { HistoryData } from '../src/types/market';

function assert(condition: unknown, message: string) {
  if (!condition) {
    throw new Error(message);
  }
}

function history(symbol: string, rows: Array<{ close: number; high?: number; low?: number; open?: number; timestamp: string; volume?: number }>, source = 'generated_test_data'): HistoryData {
  return {
    adjusted: true,
    as_of: '2026-07-16T00:00:00.000Z',
    candles: rows.map((row, index) => ({
      close: row.close,
      high: row.high ?? Math.max(row.open ?? row.close, row.close) + 1,
      low: row.low ?? Math.min(row.open ?? row.close, row.close) - 1,
      open: row.open ?? row.close,
      timestamp: row.timestamp,
      volume: row.volume ?? 1_000_000 + index * 10_000,
    })),
    fallback_used: false,
    is_live: false,
    is_stale: false,
    source,
    symbol,
    timeframe: 'D',
  };
}

function candle(date: string, close: number, volume: number, open = close - 1, high = close + 1, low = close - 1) {
  return { close, high, low, open, timestamp: date, volume };
}

function runTests() {
  const spx = getInstitutionalSourceMapping('SPX', true);
  assert(spx.priceSymbol === 'SPX' && spx.volumeSymbol === 'SPY', 'SPX maps to SPY volume proxy');
  const ndx = getInstitutionalSourceMapping('NDX', true);
  assert(ndx.priceSymbol === 'NDX' && ndx.volumeSymbol === 'QQQ', 'NDX maps to QQQ volume proxy');
  const fallback = getInstitutionalSourceMapping('SPX', false);
  assert(fallback.priceSymbol === 'SPY' && fallback.usesEtfPriceFallback, 'ETF fallback is disclosed');

  const normalized = normalizeInstitutionalCandles(history('T', [
    candle('2026-07-01', 100, 1_000_000, 99, 101, 98),
    candle('2026-07-01T20:00:00Z', 101, 1_100_000, 100, 102, 99),
    candle('bad', 102, 1_200_000),
    candle('2026-07-02', 100, 1_000_000, 105, 104, 99),
    candle('2026-07-03', 103, 1_300_000),
  ]));
  assert(normalized.length === 2, 'invalid timestamps and invalid OHLC are omitted');
  assert(normalized[0]?.close === 101, 'duplicate dates keep the latest valid candle');

  const accumulationCandles = buildCandles([
    ...baselineCandles(),
    candle('2026-07-21', 103, 1_450_000, 101.8, 103.2, 101.7),
  ]);
  assert(detectInstitutionalEvents(accumulationCandles, null, 'SPX').some((event) => event.type === 'accumulation'), 'strong accumulation event qualifies');

  const ordinaryUpDay = buildCandles([
    ...baselineCandles(),
    candle('2026-07-21', 101.2, 1_060_000, 101.0, 101.3, 100.8),
  ]);
  assert(!detectInstitutionalEvents(ordinaryUpDay, null, 'SPX').some((event) => event.type === 'accumulation'), 'ordinary up day does not classify as accumulation');

  const lowVolumeUp = buildCandles([
    ...baselineCandles(),
    candle('2026-07-21', 103, 900_000, 101.8, 103.2, 101.7),
  ]);
  assert(!detectInstitutionalEvents(lowVolumeUp, null, 'SPX').some((event) => event.type === 'accumulation'), 'positive low-volume day is not accumulation');

  const weakCloseUp = buildCandles([
    ...baselineCandles(),
    candle('2026-07-21', 102.2, 1_450_000, 101, 103.8, 101.8),
  ]);
  assert(!detectInstitutionalEvents(weakCloseUp, null, 'SPX').some((event) => event.type === 'accumulation'), 'weak close up day is not accumulation');

  const distributionCandles = buildCandles([
    candle('2026-07-01', 100, 1_000_000),
    candle('2026-07-02', 99.5, 1_200_000),
  ]);
  assert(detectInstitutionalEvents(distributionCandles, null, 'SPX').some((event) => event.type === 'distribution'), 'negative higher-volume day classifies as distribution');

  const lowVolumeDown = buildCandles([
    candle('2026-07-01', 100, 1_000_000),
    candle('2026-07-02', 99, 900_000),
  ]);
  assert(!detectInstitutionalEvents(lowVolumeDown, null, 'SPX').some((event) => event.type === 'distribution'), 'negative low-volume day is not distribution');

  const followThrough = buildCandles([
    candle('2026-07-01', 100, 1_000_000),
    candle('2026-07-02', 99, 900_000),
    candle('2026-07-03', 100, 950_000),
    candle('2026-07-06', 101, 1_000_000),
    candle('2026-07-07', 102.5, 1_300_000),
  ]);
  assert(detectInstitutionalEvents(followThrough, null, 'SPX').some((event) => event.type === 'follow_through'), 'strong higher-volume rally after several sessions marks FTD proxy');

  const stall = buildCandles([
    candle('2026-07-01', 100, 1_000_000),
    candle('2026-07-02', 104, 1_050_000),
    candle('2026-07-03', 105.1, 1_100_000),
    candle('2026-07-06', 105.2, 1_400_000, 105, 106, 104.8),
  ]);
  assert(detectInstitutionalEvents(stall, null, 'SPX').some((event) => event.type === 'stall'), 'weak close on elevated volume near highs marks stall');

  const churning = buildCandles([
    candle('2026-07-01', 100, 1_000_000),
    candle('2026-07-02', 100.2, 1_400_000, 100, 105, 99),
  ]);
  assert(detectInstitutionalEvents(churning, null, 'SPX').some((event) => event.type === 'churning'), 'elevated volume with limited progress marks churning');

  const model = buildInstitutionalActivityChartViewModel({
    filter: 'all',
    followThroughDay: { date: '2026-07-07', gain_percent: 1.4, index: 'SPX', triggered: true },
    index: 'SPX',
    priceHistory: history('SPX', [
      candle('2026-07-01', 100, 1_000_000),
      candle('2026-07-02', 101, 1_100_000),
      candle('2026-07-03', 100.5, 1_200_000),
      candle('2026-07-06', 100.8, 1_100_000),
      candle('2026-07-07', 102.4, 1_400_000),
    ]),
    timeframe: '1M',
    volumeHistory: history('SPY', [
      candle('2026-07-01', 100, 1_000_000),
      candle('2026-07-02', 101, 1_150_000),
      candle('2026-07-03', 100.5, 1_100_000),
      candle('2026-07-06', 100.8, 1_000_000),
      candle('2026-07-07', 102.4, 1_450_000),
    ]),
  });
  assert(model.candles.length === 5, 'view model keeps visible candles');
  assert(model.summary.followThroughCount >= 1, 'summary counts follow-through events');
  assert(model.summary.netActivity !== null, 'summary calculates net activity');
  assert(model.summary.totalClassifiedSignals === model.allEvents.length, 'summary exposes classified signal count');
  assert(model.summary.totalDisplayedMarkers === model.displayedEvents.length, 'summary exposes displayed marker count');
  assert(model.chartWindow.startDate === '2026-07-01' && model.chartWindow.endDate === '2026-07-07', 'chart window uses visible candles');
  assert(model.priceTicks.length >= 3, 'price ticks are generated');
  assert(model.priceScale.mode === 'normalized_test', 'test source uses normalized test price label');
  assert(model.dataQuality.sourceLabel === 'Test data', 'source label maps generated test data');

  const filtered = buildInstitutionalActivityChartViewModel({
    filter: 'distribution',
    index: 'SPX',
    priceHistory: history('SPX', [candle('2026-07-01', 100, 1_000_000), candle('2026-07-02', 99, 1_300_000)]),
    timeframe: '1M',
    volumeHistory: history('SPY', [candle('2026-07-01', 100, 1_000_000), candle('2026-07-02', 99, 1_300_000)]),
  });
  assert(filtered.visibleEvents.every((event) => event.type === 'distribution'), 'event filter controls visible events');

  const noVolume = buildInstitutionalActivityChartViewModel({
    filter: 'all',
    index: 'SPX',
    priceHistory: history('SPX', [candle('2026-07-01', 100, 0), candle('2026-07-02', 101, 0)]),
    timeframe: '1M',
    volumeHistory: history('SPY', [candle('2026-07-01', 100, 0), candle('2026-07-02', 101, 0)]),
  });
  assert(noVolume.candles.length === 2, 'candles render without volume');
  assert(noVolume.events.length === 0, 'volume-dependent events are omitted without volume proxy');

  const denseRows = denseAccumulationRows();
  const denseAll = buildInstitutionalActivityChartViewModel({
    filter: 'all',
    index: 'SPX',
    priceHistory: history('SPX', denseRows),
    timeframe: '1M',
    volumeHistory: history('SPY', denseRows),
  });
  const denseAccumulationTotal = denseAll.allEvents.filter((event) => event.type === 'accumulation').length;
  const denseAccumulationDisplayed = denseAll.displayedEvents.filter((event) => event.type === 'accumulation').length;
  assert(denseAccumulationTotal > denseAccumulationDisplayed, 'All view limits accumulation marker density');
  assert(denseAccumulationDisplayed <= 6, '1M All view respects accumulation marker limit');
  assert(denseAll.hiddenEventCount > 0, 'hidden event count tracks density reduction');

  const denseFilter = buildInstitutionalActivityChartViewModel({
    filter: 'accumulation',
    index: 'SPX',
    priceHistory: history('SPX', denseRows),
    timeframe: '1M',
    volumeHistory: history('SPY', denseRows),
  });
  assert(
    denseFilter.displayedEvents.filter((event) => event.type === 'accumulation').length === denseAccumulationTotal,
    'Accumulation filter reveals all accumulation events',
  );

  assert(calculateInstitutionalPriceTicks(model.candles).length >= 3, 'tick helper returns readable y-axis ticks');
  assert(formatInstitutionalChartWindow('2026-06-25', '2026-07-16') === 'Jun 25-Jul 16', 'window formatter is compact');

  assert(formatInstitutionalChartSourceKind('test') === 'Test data', 'test source label is user-facing');
  assert(formatInstitutionalChartSourceKind('mock') === 'Mock data', 'mock source label is user-facing');
}

function baselineCandles() {
  return Array.from({ length: 20 }, (_, index) => {
    const day = String(index + 1).padStart(2, '0');
    const close = 100 + index * 0.05;
    return candle(`2026-07-${day}`, close, 1_000_000 + (index % 4) * 15_000, close - 0.2, close + 0.35, close - 0.35);
  });
}

function denseAccumulationRows() {
  return Array.from({ length: 32 }, (_, index) => {
    const day = String(index + 1).padStart(2, '0');
    const close = index < 20 ? 100 + index * 0.04 : 101 + (index - 19) * 2.2;
    const volume = index < 20 ? 1_000_000 + (index % 3) * 10_000 : 1_350_000 + (index - 20) * 120_000;
    return candle(`2026-07-${day}`, close, volume, close - 0.8, close + 0.18, close - 0.9);
  });
}

function buildCandles(rows: ReturnType<typeof candle>[]): InstitutionalCandleViewModel[] {
  return buildInstitutionalActivityChartViewModel({
    filter: 'all',
    index: 'SPX',
    priceHistory: history('SPX', rows),
    timeframe: '1M',
    volumeHistory: history('SPY', rows),
  }).candles;
}

runTests();
