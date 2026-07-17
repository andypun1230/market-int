import type { CandleData, HistoryData } from '@/types/market';

export type StockMiniChartRange = '1D' | '1W' | '1M' | '6M' | '1Y';

export type StockMiniChartDataStatus =
  | 'live'
  | 'test'
  | 'cached'
  | 'stale'
  | 'fallback'
  | 'mock'
  | 'mixed'
  | 'unavailable';

export type StockMiniChartPoint = {
  timestamp: string;
  close: number;
  volume?: number | null;
};

export type StockMiniChartModel = {
  symbol: string;
  range: StockMiniChartRange;
  points: StockMiniChartPoint[];
  currentQuote: {
    price: number | null;
    source?: string | null;
    timestamp: string | null;
  };
  stats: {
    change: number | null;
    changePercent: number | null;
    endPrice: number | null;
    high: number | null;
    low: number | null;
    startPrice: number | null;
  };
  provenance: {
    dataStatus: StockMiniChartDataStatus;
    historyEndsBeforeQuote: boolean;
    quoteHistoryPriceMismatch: boolean;
    lastUpdated?: string | null;
    provider?: string | null;
    warning?: string | null;
  };
};

export type StockMiniChartQuoteInput = {
  price?: number | null;
  source?: string | null;
  timestamp?: string | null;
};

export const stockMiniChartRangeDays: Record<StockMiniChartRange, number> = {
  '1D': 2,
  '1W': 7,
  '1M': 30,
  '6M': 180,
  '1Y': 365,
};

export const stockMiniChartRanges = Object.keys(stockMiniChartRangeDays) as StockMiniChartRange[];

const HISTORY_QUOTE_GAP_WARNING_HOURS: Record<StockMiniChartRange, number> = {
  '1D': 36,
  '1W': 48,
  '1M': 72,
  '6M': 120,
  '1Y': 144,
};

export function buildStockMiniChartModel({
  history,
  quote,
  range,
  symbol,
}: {
  history?: HistoryData | null;
  quote?: StockMiniChartQuoteInput | null;
  range: StockMiniChartRange;
  symbol: string;
}): StockMiniChartModel {
  const points = normalizeHistoryPoints(history?.candles ?? []).slice(-stockMiniChartRangeDays[range]);
  const stats = calculateChartStats(points);
  const dataStatus = getDataStatus(history, quote);
  const historyEndsBeforeQuote = getHistoryEndsBeforeQuote(points, quote, range);
  const quoteHistoryPriceMismatch = getQuoteHistoryPriceMismatch(stats.endPrice, quote?.price);
  const warning = getProvenanceWarning(dataStatus, historyEndsBeforeQuote, quoteHistoryPriceMismatch);

  return {
    symbol,
    range,
    points,
    currentQuote: {
      price: toFiniteNumber(quote?.price),
      source: quote?.source ?? null,
      timestamp: quote?.timestamp ?? null,
    },
    stats,
    provenance: {
      dataStatus,
      historyEndsBeforeQuote,
      quoteHistoryPriceMismatch,
      lastUpdated: history?.as_of ?? null,
      provider: history?.source ?? null,
      warning,
    },
  };
}

export function normalizeHistoryPoints(candles: CandleData[]): StockMiniChartPoint[] {
  const byTimestamp = new Map<string, StockMiniChartPoint>();

  for (const candle of candles) {
    const close = toFiniteNumber(candle.close);
    if (!candle.timestamp || close == null || close <= 0) {
      continue;
    }
    byTimestamp.set(candle.timestamp, {
      close,
      timestamp: candle.timestamp,
      volume: toFiniteNumber(candle.volume),
    });
  }

  return [...byTimestamp.values()].sort((a, b) => Date.parse(a.timestamp) - Date.parse(b.timestamp));
}

export function calculateChartStats(points: StockMiniChartPoint[]): StockMiniChartModel['stats'] {
  if (!points.length) {
    return {
      change: null,
      changePercent: null,
      endPrice: null,
      high: null,
      low: null,
      startPrice: null,
    };
  }
  const closes = points.map((point) => point.close);
  const startPrice = closes[0];
  const endPrice = closes[closes.length - 1];
  const change = endPrice - startPrice;
  return {
    change,
    changePercent: startPrice > 0 ? (change / startPrice) * 100 : null,
    endPrice,
    high: Math.max(...closes),
    low: Math.min(...closes),
    startPrice,
  };
}

export function getChartDirection(changePercent?: number | null): 'positive' | 'negative' | 'neutral' {
  if (changePercent == null || Math.abs(changePercent) < 0.05) {
    return 'neutral';
  }
  return changePercent > 0 ? 'positive' : 'negative';
}

export function getXAxisLabels(points: StockMiniChartPoint[], range: StockMiniChartRange): { index: number; label: string }[] {
  if (points.length < 2) {
    return [];
  }
  const labelCount = range === '1D' ? 2 : range === '1W' ? 3 : 4;
  const indexes = new Set<number>();
  for (let i = 0; i < labelCount; i += 1) {
    indexes.add(Math.round((i / (labelCount - 1)) * (points.length - 1)));
  }
  return [...indexes].sort((a, b) => a - b).map((index) => ({
    index,
    label: formatDateLabel(points[index].timestamp, range),
  }));
}

export function getYAxisLabels(low: number | null, high: number | null): number[] {
  if (low == null || high == null) {
    return [];
  }
  const range = Math.max(high - low, 0.01);
  const paddedLow = low - range * 0.08;
  const paddedHigh = high + range * 0.08;
  return [
    paddedHigh,
    paddedLow + (paddedHigh - paddedLow) * 0.66,
    paddedLow + (paddedHigh - paddedLow) * 0.33,
    paddedLow,
  ];
}

export function getPaddedPriceDomain(low: number | null, high: number | null) {
  if (low == null || high == null) {
    return { max: 1, min: 0 };
  }
  const range = Math.max(high - low, Math.max(high * 0.01, 0.01));
  return {
    max: high + range * 0.1,
    min: Math.max(0, low - range * 0.1),
  };
}

export function formatCurrency(value?: number | null): string {
  if (value == null || !Number.isFinite(value)) {
    return 'N/A';
  }
  return `$${value.toFixed(value >= 100 ? 2 : 2)}`;
}

export function formatVolume(value?: number | null): string {
  if (value == null || !Number.isFinite(value)) {
    return 'N/A';
  }
  if (value >= 1_000_000_000) {
    return `${(value / 1_000_000_000).toFixed(1)}B`;
  }
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)}M`;
  }
  if (value >= 1_000) {
    return `${(value / 1_000).toFixed(1)}K`;
  }
  return value.toFixed(0);
}

export function formatPercent(value?: number | null): string {
  if (value == null || !Number.isFinite(value)) {
    return 'N/A';
  }
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
}

export function getProvenanceLabel(status: StockMiniChartDataStatus): string {
  switch (status) {
    case 'live':
      return 'Live history';
    case 'test':
      return 'Test Data';
    case 'cached':
      return 'Cached history';
    case 'stale':
      return 'Stale history';
    case 'fallback':
      return 'Fallback history';
    case 'mock':
      return 'Mock history';
    case 'mixed':
      return 'Mixed sources';
    default:
      return 'History unavailable';
  }
}

function getDataStatus(history?: HistoryData | null, quote?: StockMiniChartQuoteInput | null): StockMiniChartDataStatus {
  if (!history) {
    return 'unavailable';
  }
  const historySource = (history.source ?? '').toLowerCase();
  const quoteSource = (quote?.source ?? '').toLowerCase();
  if (historySource.includes('generated_test_data') || quoteSource.includes('generated_test_data')) {
    return 'test';
  }
  if (history.is_stale) {
    return 'stale';
  }
  if (history.fallback_used || historySource.includes('fallback')) {
    return quoteSource && !quoteSource.includes('fallback') ? 'mixed' : 'fallback';
  }
  if (historySource.includes('mock')) {
    return quoteSource && !quoteSource.includes('mock') ? 'mixed' : 'mock';
  }
  if (history.is_live) {
    return 'live';
  }
  if (history.source) {
    return 'cached';
  }
  return 'unavailable';
}

function getHistoryEndsBeforeQuote(
  points: StockMiniChartPoint[],
  quote?: StockMiniChartQuoteInput | null,
  range?: StockMiniChartRange,
): boolean {
  const quoteTime = quote?.timestamp ? Date.parse(quote.timestamp) : NaN;
  const historyTime = points.at(-1)?.timestamp ? Date.parse(points.at(-1)?.timestamp ?? '') : NaN;
  if (!Number.isFinite(quoteTime) || !Number.isFinite(historyTime) || quoteTime <= historyTime) {
    return false;
  }
  const gapHours = (quoteTime - historyTime) / 3_600_000;
  return gapHours > HISTORY_QUOTE_GAP_WARNING_HOURS[range ?? '1M'];
}

function getQuoteHistoryPriceMismatch(historyEnd?: number | null, quotePrice?: number | null): boolean {
  if (historyEnd == null || quotePrice == null || historyEnd <= 0 || quotePrice <= 0) {
    return false;
  }
  return Math.abs((quotePrice - historyEnd) / historyEnd) >= 0.08;
}

function getProvenanceWarning(
  status: StockMiniChartDataStatus,
  historyEndsBeforeQuote: boolean,
  quoteHistoryPriceMismatch: boolean,
): string | null {
  if (status === 'mixed') {
    return 'Mixed quote and history sources. The history line is not connected to the latest quote.';
  }
  if (status === 'fallback') {
    return 'Fallback history may not align with the latest quote.';
  }
  if (status === 'stale') {
    return 'Historical data is stale.';
  }
  if (historyEndsBeforeQuote) {
    return 'History ends before the latest quote.';
  }
  if (quoteHistoryPriceMismatch) {
    return 'Latest quote differs materially from the final history close.';
  }
  return null;
}

function formatDateLabel(timestamp: string, range: StockMiniChartRange): string {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return '';
  }
  if (range === '1D' || range === '1W') {
    return date.toLocaleDateString('en-US', { weekday: 'short' });
  }
  if (range === '1M') {
    return date.toLocaleDateString('en-US', { day: 'numeric', month: 'short' });
  }
  return date.toLocaleDateString('en-US', { month: 'short' });
}

function toFiniteNumber(value?: number | string | null): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string' && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}
