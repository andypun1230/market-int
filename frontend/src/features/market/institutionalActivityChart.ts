import type { CandleData, FollowThroughDay, HistoryData } from '@/types/market';

export const institutionalChartIndexes = ['SPX', 'NDX'] as const;
export const institutionalChartTimeframes = ['1M', '3M', '6M', '1Y'] as const;
export const institutionalEventFilters = ['all', 'accumulation', 'distribution', 'follow_through', 'stall', 'churning'] as const;

export type InstitutionalChartIndex = (typeof institutionalChartIndexes)[number];
export type InstitutionalChartTimeframe = (typeof institutionalChartTimeframes)[number];
export type InstitutionalEventFilter = (typeof institutionalEventFilters)[number];
export type InstitutionalEventType = 'accumulation' | 'distribution' | 'follow_through' | 'stall' | 'churning';
export type InstitutionalEventStrength = 'high' | 'medium' | 'low';
export type InstitutionalBias = 'Accumulation' | 'Distribution' | 'Mixed' | 'Quiet' | 'Unavailable';
export type InstitutionalConfidence = 'high' | 'moderate' | 'low' | 'unavailable';
export type InstitutionalSourceKind = 'live' | 'cached' | 'mock' | 'test' | 'fallback' | 'mixed' | 'unavailable';
export type InstitutionalChartPriceMode = 'cash_index' | 'etf_fallback' | 'normalized_test';

export type InstitutionalChartSource = {
  displayIndex: InstitutionalChartIndex;
  priceLabel: string;
  priceSymbol: string;
  sourceKind: InstitutionalSourceKind;
  sourceLabel: string;
  usesEtfPriceFallback: boolean;
  usesVolumeProxy: boolean;
  volumeLabel: string;
  volumeSymbol: string;
};

export type InstitutionalPriceScale = {
  label: string;
  mode: InstitutionalChartPriceMode;
  symbol: string;
};

export type InstitutionalCandleViewModel = {
  close: number;
  dateKey: string;
  ema20: number | null;
  ema50: number | null;
  high: number;
  low: number;
  open: number;
  priceChangePct: number | null;
  proxyVolume: number | null;
  timestamp: string;
  volumeAverage20: number | null;
  volumeChangePct: number | null;
  volumeRatio20: number | null;
};

export type InstitutionalChartEvent = {
  date: string;
  priceChangePct: number | null;
  reason: string;
  score?: number | null;
  source: 'rules_based' | 'shared_engine';
  strength: InstitutionalEventStrength;
  type: InstitutionalEventType;
  volumeChangePct: number | null;
};

export type InstitutionalGroupedMarker = {
  count: number;
  dateKey: string;
  events: InstitutionalChartEvent[];
  position: 'above' | 'below';
  type: InstitutionalEventType;
};

export type VolumeAveragePoint = {
  date: string;
  value: number;
};

export type InstitutionalActivitySummary = {
  accumulationCount: number;
  bias: InstitutionalBias;
  churningCount: number;
  confidence: InstitutionalConfidence;
  distributionCount: number;
  followThroughCount: number;
  interpretation: string;
  netActivity: number | null;
  stallCount: number;
  totalClassifiedSignals: number;
  totalDisplayedMarkers: number;
};

export type InstitutionalChartDataQuality = {
  hasPrice: boolean;
  hasVolumeProxy: boolean;
  message: string;
  sourceLabel: string;
};

export type InstitutionalActivityChartViewModel = {
  allEvents: InstitutionalChartEvent[];
  candles: InstitutionalCandleViewModel[];
  chartWindow: {
    endDate: string | null;
    startDate: string | null;
  };
  dataQuality: InstitutionalChartDataQuality;
  displayedEvents: InstitutionalChartEvent[];
  events: InstitutionalChartEvent[];
  filters: InstitutionalEventFilter[];
  groupedMarkers: InstitutionalGroupedMarker[];
  hiddenEventCount: number;
  priceScale: InstitutionalPriceScale;
  priceTicks: number[];
  selectedIndex: InstitutionalChartIndex;
  source: InstitutionalChartSource;
  summary: InstitutionalActivitySummary;
  timeframe: InstitutionalChartTimeframe;
  visibleEvents: InstitutionalChartEvent[];
  volumeAverageSeries: VolumeAveragePoint[];
};

export const institutionalChartTimeframeSessions: Record<InstitutionalChartTimeframe, number> = {
  '1M': 22,
  '3M': 66,
  '6M': 132,
  '1Y': 252,
};

export const institutionalChartHistoryDays: Record<InstitutionalChartTimeframe, number> = {
  '1M': 45,
  '3M': 110,
  '6M': 220,
  '1Y': 365,
};

export const institutionalEventThresholds = {
  accumulationCloseLocationMin: 0.55,
  accumulationGainPct: 0.3,
  accumulationMinScore: 45,
  accumulationVolumeAverageRatio: 0.95,
  churningMaxAbsReturnPct: 0.45,
  churningVolumeRatio: 1.25,
  distributionDeclinePct: -0.2,
  followThroughGainPct: 1.2,
  followThroughMinDay: 4,
  stallCloseLocationMax: 0.55,
  stallMaxReturnPct: 0.45,
  stallMinReturnPct: -0.1,
  stallRecentHighPct: -3,
  stallVolumeRatio: 1.18,
};

const eventWeights: Record<InstitutionalEventType, number> = {
  accumulation: 1,
  churning: -0.5,
  distribution: -1,
  follow_through: 2,
  stall: -0.5,
};

export function getInstitutionalSourceMapping(index: InstitutionalChartIndex, priceAvailable: boolean): InstitutionalChartSource {
  const etf = index === 'SPX' ? 'SPY' : 'QQQ';
  const cash = index;
  const priceSymbol = priceAvailable ? cash : etf;
  return {
    displayIndex: index,
    priceLabel: priceAvailable ? index : etf,
    priceSymbol,
    sourceKind: 'unavailable',
    sourceLabel: priceAvailable ? `${index} price · ${etf} volume proxy` : `${etf} price and volume proxy`,
    usesEtfPriceFallback: !priceAvailable,
    usesVolumeProxy: true,
    volumeLabel: etf,
    volumeSymbol: etf,
  };
}

export function buildInstitutionalActivityChartViewModel({
  filter,
  followThroughDay,
  index,
  priceHistory,
  timeframe,
  volumeHistory,
}: {
  filter: InstitutionalEventFilter;
  followThroughDay?: FollowThroughDay | null;
  index: InstitutionalChartIndex;
  priceHistory?: HistoryData | null;
  timeframe: InstitutionalChartTimeframe;
  volumeHistory?: HistoryData | null;
}): InstitutionalActivityChartViewModel {
  const volumeSymbol = index === 'SPX' ? 'SPY' : 'QQQ';
  const pricePoints = normalizeInstitutionalCandles(priceHistory);
  const volumePoints = normalizeInstitutionalCandles(volumeHistory);
  const priceAvailable = pricePoints.length >= 2;
  const fallbackPricePoints = priceAvailable ? pricePoints : volumePoints;
  const source = {
    ...getInstitutionalSourceMapping(index, priceAvailable),
    sourceKind: deriveSourceKind(priceHistory, volumeHistory),
  };
  source.sourceLabel = source.usesEtfPriceFallback
    ? `${source.priceLabel} price and volume proxy`
    : `${source.priceLabel} price · ${volumeSymbol} volume proxy`;

  const merged = mergePriceAndProxyVolume(fallbackPricePoints, volumePoints);
  const candles = attachDerivedFields(merged)
    .slice(-institutionalChartTimeframeSessions[timeframe]);
  const allEvents = detectInstitutionalEvents(candles, followThroughDay, index);
  const visibility = selectVisibleInstitutionalEvents(allEvents, timeframe, filter);
  const summary = buildInstitutionalActivitySummary(
    allEvents,
    Boolean(candles.length),
    candles.some((candle) => candle.proxyVolume !== null),
    visibility.displayedEvents.length,
  );
  const priceScale = buildInstitutionalPriceScale(source);
  const priceTicks = calculateInstitutionalPriceTicks(candles);
  const volumeAverageSeries = candles
    .filter((candle) => candle.volumeAverage20 !== null)
    .map((candle) => ({ date: candle.dateKey, value: candle.volumeAverage20 ?? 0 }));
  return {
    allEvents,
    candles,
    chartWindow: {
      endDate: candles.at(-1)?.dateKey ?? null,
      startDate: candles[0]?.dateKey ?? null,
    },
    dataQuality: {
      hasPrice: candles.length >= 2,
      hasVolumeProxy: candles.some((candle) => candle.proxyVolume !== null),
      message: buildQualityMessage(candles.length >= 2, candles.some((candle) => candle.proxyVolume !== null), source),
      sourceLabel: formatInstitutionalChartSourceKind(source.sourceKind),
    },
    displayedEvents: visibility.displayedEvents,
    events: allEvents,
    filters: [...institutionalEventFilters],
    groupedMarkers: visibility.groupedMarkers,
    hiddenEventCount: visibility.hiddenEventCount,
    priceScale,
    priceTicks,
    selectedIndex: index,
    source,
    summary,
    timeframe,
    visibleEvents: visibility.displayedEvents,
    volumeAverageSeries,
  };
}

export function normalizeInstitutionalCandles(history?: HistoryData | null): InstitutionalCandleViewModel[] {
  const byDate = new Map<string, CandleData>();
  (history?.candles ?? []).forEach((candle) => {
    const dateKey = toTradingDateKey(candle.timestamp);
    if (!dateKey || !isValidOhlc(candle)) {
      return;
    }
    byDate.set(dateKey, candle);
  });
  return Array.from(byDate.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([dateKey, candle]) => ({
      close: candle.close,
      dateKey,
      ema20: null,
      ema50: null,
      high: candle.high,
      low: candle.low,
      open: candle.open,
      priceChangePct: null,
      proxyVolume: Number.isFinite(candle.volume) && candle.volume > 0 ? candle.volume : null,
      timestamp: `${dateKey}T00:00:00.000Z`,
      volumeAverage20: null,
      volumeChangePct: null,
      volumeRatio20: null,
    }));
}

export function detectInstitutionalEvents(
  candles: InstitutionalCandleViewModel[],
  followThroughDay: FollowThroughDay | null | undefined,
  index: InstitutionalChartIndex,
): InstitutionalChartEvent[] {
  const eventsByDate = new Map<string, InstitutionalChartEvent[]>();
  candles.forEach((candle, indexPosition) => {
    const prior = candles[indexPosition - 1] ?? null;
    const recent = candles.slice(Math.max(0, indexPosition - 20), indexPosition + 1);
    const detected = detectEventsForCandle(candle, prior, recent, indexPosition);
    detected.forEach((event) => {
      const list = eventsByDate.get(event.date) ?? [];
      list.push(event);
      eventsByDate.set(event.date, list);
    });
  });

  if (followThroughDay?.triggered && followThroughDay.date && (!followThroughDay.index || followThroughDay.index === index)) {
    const date = toTradingDateKey(followThroughDay.date);
    const candle = date ? candles.find((item) => item.dateKey === date) : null;
    if (date && candle) {
      const list = eventsByDate.get(date) ?? [];
      list.push({
        date,
        priceChangePct: candle.priceChangePct,
        reason: 'Shared follow-through day engine detected a confirming price-volume rally attempt.',
        score: 2,
        source: 'shared_engine',
        strength: 'high',
        type: 'follow_through',
        volumeChangePct: candle.volumeChangePct,
      });
      eventsByDate.set(date, list);
    }
  }

  return Array.from(eventsByDate.values())
    .flatMap((events) => applyEventPrecedence(events))
    .sort((a, b) => a.date.localeCompare(b.date));
}

export function buildInstitutionalActivitySummary(
  events: InstitutionalChartEvent[],
  hasPrice: boolean,
  hasVolume: boolean,
  displayedMarkerCount = events.length,
): InstitutionalActivitySummary {
  if (!hasPrice) {
    return {
      accumulationCount: 0,
      bias: 'Unavailable',
      churningCount: 0,
      confidence: 'unavailable',
      distributionCount: 0,
      followThroughCount: 0,
      interpretation: 'Institutional price-volume proxy data is unavailable.',
      netActivity: null,
      stallCount: 0,
      totalClassifiedSignals: 0,
      totalDisplayedMarkers: 0,
    };
  }
  const counts = {
    accumulation: countEvents(events, 'accumulation'),
    churning: countEvents(events, 'churning'),
    distribution: countEvents(events, 'distribution'),
    followThrough: countEvents(events, 'follow_through'),
    stall: countEvents(events, 'stall'),
  };
  const netActivity = events.reduce((sum, event) => sum + eventWeights[event.type], 0);
  const bias: InstitutionalBias = counts.followThrough > 0 || netActivity >= 2
    ? 'Accumulation'
    : netActivity <= -2
      ? 'Distribution'
      : events.length === 0
        ? 'Quiet'
        : 'Mixed';
  const confidence: InstitutionalConfidence = hasVolume ? (events.length >= 3 ? 'high' : 'moderate') : 'low';
  return {
    accumulationCount: counts.accumulation,
    bias,
    churningCount: counts.churning,
    confidence,
    distributionCount: counts.distribution,
    followThroughCount: counts.followThrough,
    interpretation: buildSummaryInterpretation(bias, netActivity, counts.followThrough, hasVolume),
    netActivity,
    stallCount: counts.stall,
    totalClassifiedSignals: events.length,
    totalDisplayedMarkers: displayedMarkerCount,
  };
}

export function selectVisibleInstitutionalEvents(
  allEvents: InstitutionalChartEvent[],
  timeframe: InstitutionalChartTimeframe,
  filter: InstitutionalEventFilter,
): {
  displayedEvents: InstitutionalChartEvent[];
  groupedMarkers: InstitutionalGroupedMarker[];
  hiddenEventCount: number;
} {
  const scoped = filter === 'all' ? allEvents : allEvents.filter((event) => event.type === filter);
  if (filter !== 'all') {
    return {
      displayedEvents: scoped,
      groupedMarkers: groupInstitutionalMarkers(scoped),
      hiddenEventCount: 0,
    };
  }

  const accumulation = scoped.filter((event) => event.type === 'accumulation');
  const alwaysVisible = scoped.filter((event) => event.type === 'follow_through' || event.type === 'distribution');
  const materialCaution = scoped.filter((event) => (event.type === 'stall' || event.type === 'churning') && event.strength !== 'low');
  const maxAccumulation = maxVisibleAccumulationMarkers(timeframe);
  const selectedAccumulation = [...accumulation]
    .sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
    .filter((event, index) => event.strength === 'high' || index < maxAccumulation)
    .slice(0, maxAccumulation);
  const displayed = [...alwaysVisible, ...selectedAccumulation, ...materialCaution]
    .sort((a, b) => a.date.localeCompare(b.date) || eventPriority(a.type) - eventPriority(b.type));
  return {
    displayedEvents: displayed,
    groupedMarkers: groupInstitutionalMarkers(displayed),
    hiddenEventCount: Math.max(0, scoped.length - displayed.length),
  };
}

export function groupInstitutionalMarkers(events: InstitutionalChartEvent[]): InstitutionalGroupedMarker[] {
  const grouped = new Map<string, InstitutionalChartEvent[]>();
  events.forEach((event) => {
    const key = `${event.date}:${event.type}`;
    const list = grouped.get(key) ?? [];
    list.push(event);
    grouped.set(key, list);
  });
  return Array.from(grouped.values()).map((items) => {
    const event = items[0];
    return {
      count: items.length,
      dateKey: event.date,
      events: items,
      position: event.type === 'accumulation' || event.type === 'follow_through' ? 'below' : 'above',
      type: event.type,
    };
  });
}

export function calculateInstitutionalPriceTicks(candles: InstitutionalCandleViewModel[], target = 4): number[] {
  const prices = candles.flatMap((candle) => [candle.high, candle.low, candle.ema20, candle.ema50]).filter(isValidNumber);
  if (!prices.length) {
    return [];
  }
  const bounds = calculateInstitutionalChartBounds(prices);
  if (target <= 1 || bounds.max === bounds.min) {
    return [bounds.max];
  }
  return Array.from({ length: target }, (_, index) => bounds.max - ((bounds.max - bounds.min) / (target - 1)) * index);
}

export function calculateInstitutionalChartBounds(values: number[]) {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const padding = Math.max(0.5, (max - min) * 0.12);
  return { max: max + padding, min: min - padding };
}

export function buildInstitutionalPriceScale(source: InstitutionalChartSource): InstitutionalPriceScale {
  const isTest = source.sourceKind === 'test' || source.sourceKind === 'mock';
  const mode: InstitutionalChartPriceMode = isTest
    ? 'normalized_test'
    : source.usesEtfPriceFallback
      ? 'etf_fallback'
      : 'cash_index';
  return {
    label: mode === 'normalized_test'
      ? `${source.priceLabel} test price`
      : mode === 'etf_fallback'
        ? `${source.priceLabel} ETF fallback price`
        : `${source.priceLabel} cash-index price`,
    mode,
    symbol: source.priceLabel,
  };
}

export function formatInstitutionalChartWindow(startDate: string | null, endDate: string | null) {
  if (!startDate || !endDate || startDate === endDate) {
    return null;
  }
  return `${formatShortWindowDate(startDate)}-${formatShortWindowDate(endDate)}`;
}

function calculateAccumulationStrengthScore(
  priceChangePct: number,
  volumeRatio: number,
  volumeRatio20: number,
  closeLocation: number,
) {
  const priceScore = clamp((priceChangePct - institutionalEventThresholds.accumulationGainPct) * 24, 0, 30);
  const volumeScore = clamp((volumeRatio - 1) * 50, 0, 25);
  const averageVolumeScore = clamp((volumeRatio20 - institutionalEventThresholds.accumulationVolumeAverageRatio) * 42, 0, 25);
  const closeScore = clamp((closeLocation - institutionalEventThresholds.accumulationCloseLocationMin) * 50, 0, 20);
  return Math.round(priceScore + volumeScore + averageVolumeScore + closeScore);
}

function detectEventsForCandle(
  candle: InstitutionalCandleViewModel,
  prior: InstitutionalCandleViewModel | null,
  recent: InstitutionalCandleViewModel[],
  indexPosition: number,
): InstitutionalChartEvent[] {
  if (!prior || candle.priceChangePct === null || candle.volumeChangePct === null || candle.proxyVolume === null || prior.proxyVolume === null) {
    return [];
  }
  const volumeHigher = candle.proxyVolume > prior.proxyVolume;
  const volumeRatio = prior.proxyVolume > 0 ? candle.proxyVolume / prior.proxyVolume : 0;
  const volumeRatio20 = candle.volumeRatio20 ?? 0;
  const closeLocation = candle.high > candle.low ? (candle.close - candle.low) / (candle.high - candle.low) : 0.5;
  const recentHigh = Math.max(...recent.map((item) => item.high));
  const distanceFromHigh = recentHigh > 0 ? (candle.close / recentHigh - 1) * 100 : 0;
  const rangePct = candle.close > 0 ? ((candle.high - candle.low) / candle.close) * 100 : 0;
  const accumulationScore = calculateAccumulationStrengthScore(candle.priceChangePct, volumeRatio, volumeRatio20, closeLocation);
  const recentBeforeCurrent = recent.slice(0, -1).slice(-5);
  const recentPullback = recentBeforeCurrent.some((item) => item.priceChangePct !== null && item.priceChangePct <= -0.4);

  const events: InstitutionalChartEvent[] = [];
  if (
    indexPosition >= institutionalEventThresholds.followThroughMinDay &&
    candle.priceChangePct >= institutionalEventThresholds.followThroughGainPct &&
    volumeHigher &&
    recentPullback
  ) {
    events.push({
      date: candle.dateKey,
      priceChangePct: candle.priceChangePct,
      reason: 'Strong price gain on higher proxy volume after several sessions in the window.',
      score: 2,
      source: 'rules_based',
      strength: 'high',
      type: 'follow_through',
      volumeChangePct: candle.volumeChangePct,
    });
  }
  if (candle.priceChangePct <= institutionalEventThresholds.distributionDeclinePct && volumeHigher) {
    events.push({
      date: candle.dateKey,
      priceChangePct: candle.priceChangePct,
      reason: 'Distribution Day proxy: price declined on higher proxy volume.',
      score: -1,
      source: 'rules_based',
      strength: Math.abs(candle.priceChangePct) > 0.9 || volumeRatio > 1.25 ? 'high' : 'medium',
      type: 'distribution',
      volumeChangePct: candle.volumeChangePct,
    });
  }
  if (
    candle.priceChangePct >= institutionalEventThresholds.accumulationGainPct &&
    volumeHigher &&
    volumeRatio20 >= institutionalEventThresholds.accumulationVolumeAverageRatio &&
    closeLocation >= institutionalEventThresholds.accumulationCloseLocationMin &&
    accumulationScore >= institutionalEventThresholds.accumulationMinScore
  ) {
    events.push({
      date: candle.dateKey,
      priceChangePct: candle.priceChangePct,
      reason: 'Accumulation Day proxy: higher close on stronger proxy volume with a constructive close.',
      score: accumulationScore,
      source: 'rules_based',
      strength: accumulationScore >= 75 ? 'high' : accumulationScore >= 58 ? 'medium' : 'low',
      type: 'accumulation',
      volumeChangePct: candle.volumeChangePct,
    });
  }
  if (
    candle.priceChangePct >= institutionalEventThresholds.stallMinReturnPct &&
    candle.priceChangePct <= institutionalEventThresholds.stallMaxReturnPct &&
    volumeRatio >= institutionalEventThresholds.stallVolumeRatio &&
    closeLocation <= institutionalEventThresholds.stallCloseLocationMax &&
    distanceFromHigh >= institutionalEventThresholds.stallRecentHighPct
  ) {
    events.push({
      date: candle.dateKey,
      priceChangePct: candle.priceChangePct,
      reason: 'Stall Day proxy: limited progress on elevated volume with a weaker close near recent highs.',
      score: -0.5,
      source: 'rules_based',
      strength: volumeRatio > 1.35 ? 'high' : 'medium',
      type: 'stall',
      volumeChangePct: candle.volumeChangePct,
    });
  }
  if (
    Math.abs(candle.priceChangePct) <= institutionalEventThresholds.churningMaxAbsReturnPct &&
    volumeRatio >= institutionalEventThresholds.churningVolumeRatio &&
    rangePct >= 0.8 &&
    closeLocation < 0.65
  ) {
    events.push({
      date: candle.dateKey,
      priceChangePct: candle.priceChangePct,
      reason: 'Churning Day proxy: elevated turnover without meaningful price progress.',
      score: -0.5,
      source: 'rules_based',
      strength: volumeRatio > 1.45 ? 'high' : 'medium',
      type: 'churning',
      volumeChangePct: candle.volumeChangePct,
    });
  }
  return events;
}

function applyEventPrecedence(events: InstitutionalChartEvent[]): InstitutionalChartEvent[] {
  const sorted = [...events].sort((a, b) => eventPriority(a.type) - eventPriority(b.type));
  const primary = sorted[0];
  if (!primary) {
    return [];
  }
  return sorted.filter((event) => {
    if (event.type === primary.type) {
      return true;
    }
    if ((primary.type === 'follow_through' && event.type === 'accumulation') || (primary.type === 'stall' && event.type === 'churning')) {
      return false;
    }
    if ((primary.type === 'distribution' && event.type === 'accumulation') || (primary.type === 'accumulation' && event.type === 'distribution')) {
      return false;
    }
    return true;
  });
}

function eventPriority(type: InstitutionalEventType) {
  switch (type) {
    case 'follow_through':
      return 1;
    case 'distribution':
      return 2;
    case 'accumulation':
      return 3;
    case 'stall':
      return 4;
    case 'churning':
      return 5;
  }
}

function mergePriceAndProxyVolume(price: InstitutionalCandleViewModel[], volume: InstitutionalCandleViewModel[]) {
  const volumeByDate = new Map(volume.map((candle) => [candle.dateKey, candle.proxyVolume]));
  return price.map((candle) => ({
    ...candle,
    proxyVolume: volumeByDate.get(candle.dateKey) ?? candle.proxyVolume ?? null,
  }));
}

function attachDerivedFields(candles: InstitutionalCandleViewModel[]) {
  const closes = candles.map((candle) => candle.close);
  const ema20 = calculateEma(closes, 20);
  const ema50 = calculateEma(closes, 50);
  const volumeAverage20 = calculateRollingAverage(candles.map((candle) => candle.proxyVolume), 20);
  return candles.map((candle, index) => {
    const prior = candles[index - 1] ?? null;
    const priceChangePct = prior && prior.close > 0 ? (candle.close / prior.close - 1) * 100 : null;
    const volumeChangePct = prior?.proxyVolume && candle.proxyVolume ? (candle.proxyVolume / prior.proxyVolume - 1) * 100 : null;
    const averageVolume = volumeAverage20[index];
    return {
      ...candle,
      ema20: ema20[index],
      ema50: ema50[index],
      priceChangePct,
      volumeAverage20: averageVolume,
      volumeChangePct,
      volumeRatio20: averageVolume && candle.proxyVolume ? candle.proxyVolume / averageVolume : null,
    };
  });
}

function calculateEma(values: number[], period: number): (number | null)[] {
  const multiplier = 2 / (period + 1);
  let previous: number | null = null;
  return values.map((value, index) => {
    if (index < period - 1) {
      return null;
    }
    if (previous === null) {
      previous = average(values.slice(index - period + 1, index + 1));
      return previous;
    }
    previous = value * multiplier + previous * (1 - multiplier);
    return previous;
  });
}

function calculateRollingAverage(values: (number | null)[], period: number): (number | null)[] {
  return values.map((_, index) => {
    if (index < period - 1) {
      return null;
    }
    const window = values.slice(index - period + 1, index + 1).filter(isValidNumber);
    return window.length === period ? average(window) : null;
  });
}

function deriveSourceKind(priceHistory?: HistoryData | null, volumeHistory?: HistoryData | null): InstitutionalSourceKind {
  const sources = [priceHistory?.source, volumeHistory?.source].filter((source): source is string => Boolean(source));
  if (!sources.length) {
    return 'unavailable';
  }
  const normalized = sources.join(' ').toLowerCase();
  if (normalized.includes('generated_test_data') || normalized.includes('test')) {
    return 'test';
  }
  if (normalized.includes('mock')) {
    return 'mock';
  }
  if (normalized.includes('fallback')) {
    return 'fallback';
  }
  if (sources.length > 1 && new Set(sources).size > 1) {
    return 'mixed';
  }
  if (priceHistory?.is_live || volumeHistory?.is_live) {
    return 'live';
  }
  return 'cached';
}

export function formatInstitutionalChartSourceKind(source: InstitutionalSourceKind) {
  switch (source) {
    case 'live':
      return 'Live';
    case 'cached':
      return 'Cached';
    case 'mock':
      return 'Mock data';
    case 'test':
      return 'Test data';
    case 'fallback':
      return 'Fallback data';
    case 'mixed':
      return 'Mixed sources';
    default:
      return 'Unavailable';
  }
}

function buildQualityMessage(hasPrice: boolean, hasVolume: boolean, source: InstitutionalChartSource) {
  if (!hasPrice) {
    return 'Price history unavailable.';
  }
  if (!hasVolume) {
    return 'Volume proxy unavailable; volume-based institutional markers are hidden.';
  }
  return source.usesEtfPriceFallback
    ? `${source.priceLabel} candles are used because cash-index OHLC is unavailable.`
    : `${source.priceLabel} price is paired with ${source.volumeLabel} ETF volume proxy.`;
}

function buildSummaryInterpretation(bias: InstitutionalBias, netActivity: number, followThroughCount: number, hasVolume: boolean) {
  const proxyNote = hasVolume ? '' : ' Volume proxy is unavailable, so event confidence is limited.';
  if (bias === 'Accumulation') {
    return `${followThroughCount ? 'Follow-through and accumulation' : 'Accumulation'} signals outnumber distribution signals, supporting a constructive price-volume bias. Institutional identity is not directly confirmed.${proxyNote}`;
  }
  if (bias === 'Distribution') {
    return `Distribution signals outnumber accumulation signals, pointing to a cautious price-volume bias. Institutional identity is not directly confirmed.${proxyNote}`;
  }
  if (bias === 'Quiet') {
    return `No major institutional-day proxies are classified in this window.${proxyNote}`;
  }
  return `Accumulation and distribution signals are balanced, with net activity ${formatSigned(netActivity)}.${proxyNote}`;
}

function countEvents(events: InstitutionalChartEvent[], type: InstitutionalEventType) {
  return events.filter((event) => event.type === type).length;
}

function maxVisibleAccumulationMarkers(timeframe: InstitutionalChartTimeframe) {
  switch (timeframe) {
    case '1M':
      return 6;
    case '3M':
      return 10;
    case '6M':
      return 14;
    case '1Y':
      return 20;
  }
}

function formatShortWindowDate(dateKey: string) {
  const date = new Date(`${dateKey}T00:00:00.000Z`);
  return Number.isNaN(date.getTime()) ? dateKey.slice(5) : date.toLocaleDateString('en-US', { day: 'numeric', month: 'short' });
}

function isValidOhlc(candle: CandleData) {
  return [candle.open, candle.high, candle.low, candle.close].every((value) => Number.isFinite(value) && value > 0)
    && candle.high >= Math.max(candle.open, candle.close, candle.low)
    && candle.low <= Math.min(candle.open, candle.close, candle.high);
}

function toTradingDateKey(value: string | number | null | undefined) {
  const normalized = normalizeTimestamp(value);
  return normalized ? normalized.slice(0, 10) : null;
}

function normalizeTimestamp(value: string | number | null | undefined) {
  if (typeof value === 'number' && Number.isFinite(value)) {
    const date = new Date(Math.abs(value) < 10_000_000_000 ? value * 1000 : value);
    return Number.isNaN(date.getTime()) ? null : date.toISOString();
  }
  if (typeof value !== 'string' || !value.trim()) {
    return null;
  }
  const trimmed = value.trim();
  if (/^\\d{4}-\\d{2}-\\d{2}$/.test(trimmed)) {
    return `${trimmed}T00:00:00.000Z`;
  }
  const date = new Date(trimmed);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

function average(values: number[]) {
  return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0;
}

function formatSigned(value: number) {
  return `${value >= 0 ? '+' : ''}${value.toFixed(1)}`;
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

function isValidNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}
