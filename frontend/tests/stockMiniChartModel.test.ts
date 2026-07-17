import {
  buildStockMiniChartModel,
  calculateChartStats,
  formatCurrency,
  formatPercent,
  getChartDirection,
  getPaddedPriceDomain,
  getProvenanceLabel,
  getXAxisLabels,
  getYAxisLabels,
  normalizeHistoryPoints,
  stockMiniChartRangeDays,
  stockMiniChartRanges,
} from '../src/features/stock-detail/stockMiniChartModel';
import type { CandleData, HistoryData } from '../src/types/market';

function assert(condition: unknown, message: string) {
  if (!condition) {
    throw new Error(message);
  }
}

function candle(timestamp: string, close: number, volume = 1000): CandleData {
  return {
    close,
    high: close + 1,
    low: close - 1,
    open: close - 0.5,
    timestamp,
    volume,
  };
}

function history(overrides: Partial<HistoryData> = {}): HistoryData {
  return {
    adjusted: true,
    as_of: '2026-07-10T20:00:00Z',
    candles: [
      candle('2026-07-03T20:00:00Z', 100, 10_000),
      candle('2026-07-01T20:00:00Z', 90, 12_000),
      candle('2026-07-02T20:00:00Z', 95, 11_000),
      candle('2026-07-02T20:00:00Z', 96, 13_000),
      candle('2026-07-04T20:00:00Z', 0, 14_000),
      candle('', 110, 14_000),
    ],
    fallback_used: false,
    is_live: true,
    is_stale: false,
    source: 'polygon',
    symbol: 'NVDA',
    timeframe: 'D',
    ...overrides,
  };
}

function longHistory(days: number): HistoryData {
  return history({
    candles: Array.from({ length: days }, (_, index) => candle(
      new Date(Date.UTC(2025, 0, index + 1, 20)).toISOString(),
      80 + index * 0.25,
      10_000 + index,
    )),
    requested_days: days,
    returned_candles: days,
  });
}

function run() {
  assert(JSON.stringify(stockMiniChartRanges) === JSON.stringify(['1D', '1W', '1M', '6M', '1Y']), 'chart ranges use requested intervals');
  assert(stockMiniChartRangeDays['1D'] === 2, '1D range requests enough daily points to draw a one-day change');
  assert(stockMiniChartRangeDays['1W'] === 7, '1W range requests one week of daily history');

  const points = normalizeHistoryPoints(history().candles);
  assert(points.length === 3, 'invalid and duplicate history points are removed');
  assert(points[0].timestamp === '2026-07-01T20:00:00Z', 'points sort chronologically');
  assert(points[1].close === 96, 'latest duplicate timestamp wins');
  assert(points.every((point) => point.close > 0), 'missing values do not become zero');

  const stats = calculateChartStats(points);
  assert(stats.startPrice === 90, 'start price calculates from valid history');
  assert(stats.endPrice === 100, 'end price calculates from valid history');
  assert(stats.high === 100, 'high calculates correctly');
  assert(stats.low === 90, 'low calculates correctly');
  assert(Math.round((stats.changePercent ?? 0) * 100) / 100 === 11.11, 'change percent calculates correctly');
  assert(getChartDirection(stats.changePercent) === 'positive', 'positive period maps correctly');
  assert(getChartDirection(-3) === 'negative', 'negative period maps correctly');
  assert(getChartDirection(0.01) === 'neutral', 'neutral period maps correctly');

  const model = buildStockMiniChartModel({
    history: history(),
    quote: {
      price: 210.96,
      source: 'finnhub',
      timestamp: '2026-07-12T20:00:00Z',
    },
    range: '1M',
    symbol: 'NVDA',
  });
  assert(model.points.length === 3, 'model uses normalized points');
  assert(model.provenance.dataStatus === 'live', 'live history status is preserved');
  assert(model.provenance.historyEndsBeforeQuote, 'history/quote time gap is detected');
  assert(model.provenance.quoteHistoryPriceMismatch, 'material quote/history price mismatch is detected');
  assert(model.provenance.warning === 'History ends before the latest quote.', 'mismatch notice renders');
  assert(model.currentQuote.price === 210.96, 'quote is retained separately');
  assert(model.stats.endPrice === 100, 'historical final point is not replaced by current quote');

  const fallbackModel = buildStockMiniChartModel({
    history: history({ fallback_used: true, is_live: false, source: 'mock-fallback' }),
    quote: { price: 210.96, source: 'finnhub', timestamp: '2026-07-10T21:00:00Z' },
    range: '1W',
    symbol: 'NVDA',
  });
  assert(fallbackModel.provenance.dataStatus === 'mixed', 'fallback history with live quote is mixed');
  assert(getProvenanceLabel(fallbackModel.provenance.dataStatus) === 'Mixed sources', 'mixed label is explicit');
  assert(fallbackModel.stats.endPrice === 100, 'fallback quote is not appended');

  const priceMismatchModel = buildStockMiniChartModel({
    history: history(),
    quote: { price: 140, source: 'finnhub', timestamp: '2026-07-03T21:00:00Z' },
    range: '1D',
    symbol: 'NVDA',
  });
  assert(priceMismatchModel.provenance.warning === 'Latest quote differs materially from the final history close.', 'material price mismatch warning renders');

  const mockModel = buildStockMiniChartModel({
    history: history({ fallback_used: false, is_live: false, source: 'mock' }),
    quote: { price: null, source: 'mock', timestamp: null },
    range: '6M',
    symbol: 'NVDA',
  });
  assert(mockModel.provenance.dataStatus === 'mock', 'mock history is labelled mock');

  const sixMonthModel = buildStockMiniChartModel({
    history: longHistory(365),
    quote: { price: 171, source: 'mock', timestamp: null },
    range: '6M',
    symbol: 'NVDA',
  });
  const oneYearModel = buildStockMiniChartModel({
    history: longHistory(365),
    quote: { price: 171, source: 'mock', timestamp: null },
    range: '1Y',
    symbol: 'NVDA',
  });
  assert(sixMonthModel.points.length === 180, '6M chart uses 180 daily points');
  assert(oneYearModel.points.length === 365, '1Y chart uses 365 daily points');
  assert(sixMonthModel.stats.startPrice !== oneYearModel.stats.startPrice, '6M and 1Y chart windows start at different prices');

  const staleModel = buildStockMiniChartModel({
    history: history({ is_live: false, is_stale: true, source: 'polygon' }),
    quote: { price: 101, source: 'finnhub', timestamp: '2026-07-10T21:00:00Z' },
    range: '1Y',
    symbol: 'NVDA',
  });
  assert(staleModel.provenance.dataStatus === 'stale', 'stale history is labelled stale');

  assert(getYAxisLabels(90, 100).length === 4, 'y-axis labels render');
  assert(getXAxisLabels(model.points, '1M').length >= 2, 'x-axis labels render');
  const domain = getPaddedPriceDomain(90, 100);
  assert(domain.min < 90 && domain.max > 100, 'domain adds top and bottom padding');
  assert(formatCurrency(126.4) === '$126.40', 'currency formats');
  assert(formatPercent(18.4) === '+18.40%', 'percent formats positive');
  assert(formatPercent(-2.3) === '-2.30%', 'percent formats negative');

  const emptyModel = buildStockMiniChartModel({
    history: null,
    quote: null,
    range: '1D',
    symbol: 'BAD',
  });
  assert(emptyModel.provenance.dataStatus === 'unavailable', 'missing history is unavailable');
  assert(emptyModel.points.length === 0, 'missing history has no points');
}

run();
