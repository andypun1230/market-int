import type { HistoryData, VolumeAnalysis, WatchlistItem } from '@/types/market';

export const stockCompareTimeframes = ['1W', '1M', '3M', '6M', '1Y'] as const;

export type StockCompareTimeframe = (typeof stockCompareTimeframes)[number];

export type ComparisonUnavailableReason =
  | 'stock_history_missing'
  | 'spy_history_missing'
  | 'theme_history_missing'
  | 'no_overlapping_dates'
  | 'insufficient_points'
  | 'invalid_values'
  | 'unavailable';

export type ComparisonAlignmentSummary = {
  alignedPointCount: number;
  asOfDate: string | null;
  constituentCount: number;
  minimumConstituentsPerPoint: number;
  spyPointCount: number;
  stockPointCount: number;
  themePointCount: number;
};

export type NormalizedSeriesPoint = {
  timestamp: string;
  value: number;
};

type DailyHistoryPoint = {
  close: number;
  dateKey: string;
  timestamp: string;
};

export type StockThemeContext = {
  memberships: ThemeMembership[];
  peerSymbols: string[];
  primaryThemeId: string | null;
  primaryThemeName: string | null;
  sectorId: string | null;
  sectorName: string | null;
};

export type ThemeBenchmarkKind =
  | 'theme_index'
  | 'theme_etf'
  | 'equal_weight_composite'
  | 'peer_median'
  | 'sector'
  | 'unavailable';

export type ThemeBenchmark = {
  constituentCount?: number;
  includedSelectedStock?: boolean;
  kind: ThemeBenchmarkKind;
  label: string;
  minimumConstituentsPerPoint?: number;
  missingPeerSymbols?: string[];
  series: NormalizedSeriesPoint[];
  staticReturn?: number | null;
  symbol?: string;
};

export type StockComparisonChartSeries = {
  colorKey: 'stock' | 'spy' | 'theme';
  label: string;
  points: NormalizedSeriesPoint[];
};

export type StockPerformanceSummary = {
  edgeVsSpy: number | null;
  edgeVsTheme: number | null;
  spyReturn: number | null;
  stockReturn: number | null;
  themeReturn: number | null;
  timeframe: StockCompareTimeframe;
};

export type StockRelativeStrengthState =
  | 'leading_market_and_theme'
  | 'leading_theme'
  | 'following_theme'
  | 'leader_weakening'
  | 'lagging_theme'
  | 'lagging_market_and_peers'
  | 'mixed'
  | 'unavailable';

export type StockRelativeStrengthViewModel = {
  confidence: 'high' | 'moderate' | 'low' | 'unavailable';
  interpretation: string;
  label: string;
  state: StockRelativeStrengthState;
};

export type PeerLeadershipState = 'leader' | 'strong' | 'neutral' | 'lagging' | 'weak' | 'unavailable';

export type PeerComparisonViewModel = {
  distanceFromHigh: number | null;
  isSelectedStock: boolean;
  momentum: string;
  periodReturn: number | null;
  relativeStrength: PeerLeadershipState;
  setup: string;
  symbol: string;
  trend: string;
  volume: string;
};

export type PeerRankingViewModel = {
  aboveMedian: number | null;
  confidence: 'high' | 'moderate' | 'low' | 'unavailable';
  items: PeerComparisonViewModel[];
  percentile: number | null;
  rank: number | null;
  rankedCount: number;
  themeMedian: number | null;
  topPeerEdge: number | null;
};

export type LeadershipReadViewModel = {
  classification: string;
  mainRisk: string;
  mainStrength: string;
  summary: string;
};

export type StockComparisonDataQualityViewModel = {
  alignment: ComparisonAlignmentSummary;
  benchmarkLabel: string;
  benchmarkMethod: string;
  dataSource: string;
  dataSourceLabel: string;
  includedPeerCount: number;
  partialNotice: string | null;
  peerUniverseLabel: string;
  unavailableReason: ComparisonUnavailableReason | null;
  warnings: string[];
};

export type StockComparisonDashboardViewModel = {
  chart: {
    series: StockComparisonChartSeries[];
    timeframe: StockCompareTimeframe;
  };
  dataQuality: StockComparisonDataQualityViewModel;
  leadership: LeadershipReadViewModel;
  peers: PeerComparisonViewModel[];
  peerRanking: PeerRankingViewModel;
  performance: StockPerformanceSummary;
  relativeStrength: StockRelativeStrengthViewModel;
  symbol: string;
  themeBenchmark: ThemeBenchmark | null;
  themeContext: StockThemeContext;
  timeframe: StockCompareTimeframe;
};

export type ThemeMembership = {
  benchmark?: string;
  id: string;
  name: string;
  parentSector: string;
  symbols: string[];
};

const MIN_EDGE_POINTS = 2;
const STRONG_EDGE_POINTS = 6;

const THEME_MEMBERSHIPS: ThemeMembership[] = [
  { benchmark: 'XLK', id: 'semiconductors', name: 'Semiconductors', parentSector: 'Technology', symbols: ['NVDA', 'AVGO', 'AMD', 'INTC', 'ARM'] },
  { benchmark: 'XLK', id: 'memory', name: 'Memory', parentSector: 'Technology', symbols: ['MU', 'SNDK', 'WDC', 'STX'] },
  { benchmark: 'XLK', id: 'ai-infrastructure', name: 'AI Infrastructure', parentSector: 'Technology', symbols: ['NVDA', 'AVGO', 'ANET', 'VRT', 'DELL'] },
  { benchmark: 'XLK', id: 'optical-networking', name: 'Optical Networking', parentSector: 'Technology', symbols: ['LITE', 'COHR', 'AAOI', 'CIEN'] },
  { benchmark: 'XLK', id: 'software', name: 'Software', parentSector: 'Technology', symbols: ['MSFT', 'ORCL', 'CRM', 'NOW', 'ADBE'] },
  { benchmark: 'XLK', id: 'cybersecurity', name: 'Cybersecurity', parentSector: 'Technology', symbols: ['CRWD', 'PANW', 'FTNT', 'ZS', 'OKTA'] },
  { benchmark: 'XLK', id: 'cloud', name: 'Cloud', parentSector: 'Technology', symbols: ['AMZN', 'MSFT', 'GOOGL', 'ORCL', 'SNOW'] },
  { benchmark: 'XLI', id: 'defense-technology', name: 'Defense Technology', parentSector: 'Industrials', symbols: ['LMT', 'RTX', 'NOC', 'GD', 'PLTR'] },
  { benchmark: 'XLF', id: 'banks', name: 'Banks', parentSector: 'Financials', symbols: ['JPM', 'BAC', 'WFC', 'C', 'GS'] },
  { benchmark: 'XLF', id: 'payments', name: 'Payments', parentSector: 'Financials', symbols: ['V', 'MA', 'PYPL', 'COF', 'AXP'] },
  { benchmark: 'XLV', id: 'biotechnology', name: 'Biotechnology', parentSector: 'Healthcare', symbols: ['AMGN', 'GILD', 'REGN', 'VRTX', 'BIIB'] },
  { benchmark: 'XLV', id: 'medical-devices', name: 'Medical Devices', parentSector: 'Healthcare', symbols: ['ISRG', 'MDT', 'SYK', 'BSX', 'EW'] },
  { benchmark: 'XLE', id: 'oil-gas', name: 'Oil & Gas', parentSector: 'Energy', symbols: ['XOM', 'CVX', 'COP', 'EOG', 'OXY'] },
  { benchmark: 'XLU', id: 'utilities', name: 'Utilities', parentSector: 'Utilities', symbols: ['NEE', 'SO', 'DUK', 'AEP', 'EXC'] },
  { benchmark: 'XLC', id: 'consumer-internet', name: 'Consumer Internet', parentSector: 'Communication Services', symbols: ['AMZN', 'META', 'GOOGL', 'NFLX', 'RDDT'] },
];

export const stockCompareTimeframeDays: Record<StockCompareTimeframe, number> = {
  '1W': 10,
  '1M': 30,
  '3M': 90,
  '6M': 180,
  '1Y': 365,
};

export const stockCompareTimeframeSessions: Record<StockCompareTimeframe, number> = {
  '1W': 5,
  '1M': 21,
  '3M': 63,
  '6M': 126,
  '1Y': 252,
};

export function resolveStockThemeContext(symbol: string): StockThemeContext {
  const normalized = symbol.toUpperCase();
  const memberships = THEME_MEMBERSHIPS.filter((theme) => theme.symbols.includes(normalized));
  const primary = memberships[0] ?? null;
  return {
    memberships,
    peerSymbols: primary ? primary.symbols.filter((peer) => peer !== normalized) : [],
    primaryThemeId: primary?.id ?? null,
    primaryThemeName: primary?.name ?? null,
    sectorId: primary ? slugify(primary.parentSector) : null,
    sectorName: primary?.parentSector ?? null,
  };
}

export function buildStockComparisonDashboard({
  histories,
  spySymbol = 'SPY',
  stock,
  symbol,
  timeframe,
  volumeAnalysis,
}: {
  histories: Record<string, HistoryData | null | undefined>;
  spySymbol?: string;
  stock?: WatchlistItem | null;
  symbol: string;
  timeframe: StockCompareTimeframe;
  volumeAnalysis?: VolumeAnalysis | null;
}): StockComparisonDashboardViewModel {
  const normalizedSymbol = symbol.toUpperCase();
  const themeContext = resolveStockThemeContext(normalizedSymbol);
  const peerSymbols = themeContext.peerSymbols.slice(0, 6);
  const asOfDate = getComparisonAsOfDate(histories, [normalizedSymbol, spySymbol])
    ?? getComparisonAsOfDate(histories, [normalizedSymbol, ...peerSymbols]);
  const stockPoints = selectComparisonWindow(deduplicateDailyHistory(histories[normalizedSymbol]), timeframe, asOfDate);
  const spyPoints = selectComparisonWindow(deduplicateDailyHistory(histories[spySymbol]), timeframe, asOfDate);
  const stockSeries = normalizeDailyPoints(stockPoints);
  const spySeries = normalizeDailyPoints(spyPoints);
  const themeBenchmark = buildThemeBenchmark(contextWithLimitedPeers(themeContext, peerSymbols), histories, normalizedSymbol, timeframe, asOfDate);
  const stockReturn = getPointsReturn(stockPoints);
  const spyReturn = getPointsReturn(spyPoints);
  const themeReturn = themeBenchmark?.staticReturn ?? getSeriesReturn(themeBenchmark?.series ?? []);
  const performance: StockPerformanceSummary = {
    edgeVsSpy: calculateRelativeEdge(stockReturn, spyReturn),
    edgeVsTheme: calculateRelativeEdge(stockReturn, themeReturn),
    spyReturn,
    stockReturn,
    themeReturn,
    timeframe,
  };
  const peers = buildPeerComparisons({
    asOfDate,
    histories,
    peerSymbols,
    selectedSymbol: normalizedSymbol,
    stock,
    stockReturn,
    timeframe,
    volumeAnalysis,
  });
  const peerRanking = calculatePeerRank(peers, normalizedSymbol);
  const relativeStrength = classifyStockRelativeStrength(performance, peerRanking, stockSeries);
  const leadership = buildLeadershipRead(relativeStrength, peerRanking, performance, normalizedSymbol, themeContext.primaryThemeName);
  const renderableStockSeries = isRenderableComparisonSeries(stockSeries) ? stockSeries : [];
  const renderableSpySeries = isRenderableComparisonSeries(spySeries) ? spySeries : [];
  const renderableThemeSeries = isRenderableComparisonSeries(themeBenchmark?.series ?? []) ? themeBenchmark?.series ?? [] : [];
  const hasMeaningfulComparison = Boolean(renderableStockSeries.length && (renderableSpySeries.length || renderableThemeSeries.length));
  const series: StockComparisonChartSeries[] = hasMeaningfulComparison
    ? [
        { colorKey: 'stock', label: normalizedSymbol, points: renderableStockSeries },
        renderableSpySeries.length ? { colorKey: 'spy', label: spySymbol, points: renderableSpySeries } : null,
        renderableThemeSeries.length ? { colorKey: 'theme', label: themeContext.primaryThemeName ?? 'Theme', points: renderableThemeSeries } : null,
      ].filter((item): item is StockComparisonChartSeries => Boolean(item))
    : [];
  const alignment = buildAlignmentSummary({
    asOfDate,
    spySeries,
    stockSeries,
    themeBenchmark,
    themeSeries: themeBenchmark?.series ?? [],
  });

  return {
    chart: { series, timeframe },
    dataQuality: buildDataQuality({
      alignment,
      histories,
      peerSymbols,
      rawStockSeries: stockSeries,
      renderedSeriesCount: series.length,
      spySeries: renderableSpySeries,
      spySymbol,
      stockSeries: renderableStockSeries,
      symbol: normalizedSymbol,
      themeBenchmark,
      themeContext,
      themeSeries: renderableThemeSeries,
    }),
    leadership,
    peers,
    peerRanking,
    performance,
    relativeStrength,
    symbol: normalizedSymbol,
    themeBenchmark,
    themeContext,
    timeframe,
  };
}

export function buildThemeBenchmark(
  context: StockThemeContext,
  histories: Record<string, HistoryData | null | undefined>,
  selectedSymbol: string,
  timeframe: StockCompareTimeframe = '1M',
  asOfDate: string | null = getComparisonAsOfDate(histories, [selectedSymbol, ...context.peerSymbols]),
): ThemeBenchmark | null {
  if (!context.primaryThemeName) {
    return null;
  }
  const selected = selectedSymbol.toUpperCase();
  const excludedPeerSymbols = context.peerSymbols.filter((symbol) => symbol !== selected);
  const peerHistories = excludedPeerSymbols.map((symbol) => ({
    series: normalizeDailyPoints(selectComparisonWindow(deduplicateDailyHistory(histories[symbol]), timeframe, asOfDate)),
    symbol,
  }));
  const validPeerHistories = peerHistories.filter((item) => isRenderableComparisonSeries(item.series));

  if (validPeerHistories.length >= 2) {
    const minimumConstituentsPerPoint = Math.max(2, Math.ceil(excludedPeerSymbols.length * 0.5));
    const series = buildEqualWeightComposite(
      validPeerHistories.map((item) => item.series),
      minimumConstituentsPerPoint,
    );
    return {
      constituentCount: validPeerHistories.length,
      kind: 'equal_weight_composite',
      label: `Equal-weight ${context.primaryThemeName} composite`,
      minimumConstituentsPerPoint,
      missingPeerSymbols: peerHistories.filter((item) => !isRenderableComparisonSeries(item.series)).map((item) => item.symbol),
      series: isRenderableComparisonSeries(series) ? series : [],
    };
  }

  const peerReturns = context.peerSymbols
    .map((symbol) => getWindowedPeriodReturn(histories[symbol], timeframe, asOfDate))
    .filter(isValidNumber)
    .sort((a, b) => a - b);
  if (peerReturns.length >= 2) {
    const medianReturn = calculateMedian(peerReturns);
    return {
      constituentCount: peerReturns.length,
      kind: 'peer_median',
      label: `${context.primaryThemeName} peer median`,
      series: [],
      staticReturn: medianReturn,
    };
  }

  return {
    constituentCount: validPeerHistories.length,
    kind: 'unavailable',
    label: `${context.primaryThemeName} benchmark unavailable`,
    minimumConstituentsPerPoint: 2,
    series: [],
  };
}

export function buildEqualWeightComposite(
  seriesList: NormalizedSeriesPoint[][],
  minimumConstituentsPerPoint = Math.max(2, Math.ceil(seriesList.length * 0.5)),
): NormalizedSeriesPoint[] {
  const byDate = new Map<string, number[]>();
  seriesList.forEach((series) => {
    series.forEach((point) => {
      const key = toTradingDateKey(point.timestamp);
      if (!key) {
        return;
      }
      const values = byDate.get(key) ?? [];
      values.push(point.value);
      byDate.set(key, values);
    });
  });
  return Array.from(byDate.entries())
    .filter(([, values]) => values.length >= minimumConstituentsPerPoint)
    .map(([dateKey, values]) => ({
      timestamp: `${dateKey}T00:00:00.000Z`,
      value: average(values),
    }))
    .sort((a, b) => a.timestamp.localeCompare(b.timestamp));
}

export function normalizeHistorySeries(history?: HistoryData | null): NormalizedSeriesPoint[] {
  return normalizeDailyPoints(deduplicateDailyHistory(history));
}

export function getPeriodReturn(history?: HistoryData | null): number | null {
  return getPointsReturn(deduplicateDailyHistory(history));
}

export function getSeriesReturn(series: NormalizedSeriesPoint[]): number | null {
  return series.at(-1)?.value ?? null;
}

export function calculateRelativeEdge(stockReturn: number | null, benchmarkReturn: number | null) {
  return stockReturn === null || benchmarkReturn === null ? null : stockReturn - benchmarkReturn;
}

export function normalizeHistoryTimestamp(value: unknown): string | null {
  if (typeof value === 'number' && Number.isFinite(value)) {
    const milliseconds = Math.abs(value) < 10_000_000_000 ? value * 1000 : value;
    const date = new Date(milliseconds);
    return Number.isNaN(date.getTime()) ? null : date.toISOString();
  }
  if (typeof value !== 'string' || !value.trim()) {
    return null;
  }
  const trimmed = value.trim();
  const numeric = Number(trimmed);
  if (Number.isFinite(numeric) && /^\d{10,13}$/.test(trimmed)) {
    return normalizeHistoryTimestamp(numeric);
  }
  if (/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) {
    return `${trimmed}T00:00:00.000Z`;
  }
  const date = new Date(trimmed);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

export function toTradingDateKey(value: unknown): string | null {
  const normalized = normalizeHistoryTimestamp(value);
  return normalized ? normalized.slice(0, 10) : null;
}

export function deduplicateDailyHistory(history?: HistoryData | null): DailyHistoryPoint[] {
  const byDate = new Map<string, DailyHistoryPoint>();
  (history?.candles ?? []).forEach((candle) => {
    const dateKey = toTradingDateKey(candle.timestamp);
    if (!dateKey || !isValidNumber(candle.close) || candle.close <= 0) {
      return;
    }
    byDate.set(dateKey, {
      close: candle.close,
      dateKey,
      timestamp: `${dateKey}T00:00:00.000Z`,
    });
  });
  return Array.from(byDate.values()).sort((a, b) => a.dateKey.localeCompare(b.dateKey));
}

export function selectComparisonWindow(
  points: DailyHistoryPoint[],
  timeframe: StockCompareTimeframe,
  asOfDate: string | null = null,
): DailyHistoryPoint[] {
  const cutoff = asOfDate ?? points.at(-1)?.dateKey ?? null;
  const eligible = cutoff ? points.filter((point) => point.dateKey <= cutoff) : points;
  return eligible.slice(-stockCompareTimeframeSessions[timeframe]);
}

export function normalizeDailyPoints(points: DailyHistoryPoint[]): NormalizedSeriesPoint[] {
  const firstClose = points[0]?.close;
  if (!firstClose || firstClose <= 0) {
    return [];
  }
  return points
    .map((point) => ({
      timestamp: point.timestamp,
      value: (point.close / firstClose - 1) * 100,
    }))
    .filter((point) => isValidNumber(point.value));
}

export function getPointsReturn(points: DailyHistoryPoint[]): number | null {
  const first = points[0]?.close;
  const last = points.at(-1)?.close;
  return first && last ? (last / first - 1) * 100 : null;
}

export function getWindowedPeriodReturn(
  history: HistoryData | null | undefined,
  timeframe: StockCompareTimeframe,
  asOfDate: string | null,
) {
  return getPointsReturn(selectComparisonWindow(deduplicateDailyHistory(history), timeframe, asOfDate));
}

export function getComparisonAsOfDate(
  histories: Record<string, HistoryData | null | undefined>,
  symbols: string[],
): string | null {
  const uniqueSymbols = Array.from(new Set(symbols.map((symbol) => symbol.toUpperCase())));
  const dateSets = uniqueSymbols
    .map((symbol) => new Set(deduplicateDailyHistory(histories[symbol]).map((point) => point.dateKey)))
    .filter((set) => set.size > 0);
  if (!dateSets.length) {
    return null;
  }

  const commonDates = Array.from(dateSets[0]).filter((dateKey) => dateSets.every((set) => set.has(dateKey)));
  if (commonDates.length) {
    return commonDates.sort().at(-1) ?? null;
  }

  const latestDates = dateSets
    .map((set) => Array.from(set).sort().at(-1))
    .filter((dateKey): dateKey is string => Boolean(dateKey));
  return latestDates.length ? latestDates.sort()[Math.floor((latestDates.length - 1) / 2)] : null;
}

export function isRenderableComparisonSeries(series: NormalizedSeriesPoint[]) {
  return series.length >= 2 && series.every((point) => isValidNumber(point.value) && Boolean(toTradingDateKey(point.timestamp)));
}

export function formatDataSourceLabel(source?: string | null) {
  const normalized = (source ?? 'unavailable').toLowerCase();
  if (normalized === 'generated_test_data' || normalized.includes('generated_test_data') || normalized === 'test') {
    return 'Test data';
  }
  if (normalized.includes('mock')) {
    return 'Mock data';
  }
  if (normalized.includes('fallback')) {
    return 'Fallback data';
  }
  if (normalized.includes('mixed')) {
    return 'Mixed sources';
  }
  if (normalized.includes('cached')) {
    return 'Cached';
  }
  if (normalized.includes('live') || normalized === 'finnhub' || normalized === 'polygon' || normalized === 'twelve_data') {
    return 'Live';
  }
  return 'Data unavailable';
}

export function classifyStockRelativeStrength(
  performance: StockPerformanceSummary,
  peerRanking: PeerRankingViewModel,
  stockSeries: NormalizedSeriesPoint[],
): StockRelativeStrengthViewModel {
  const edgeVsSpy = performance.edgeVsSpy;
  const edgeVsTheme = performance.edgeVsTheme;
  if (performance.stockReturn === null || edgeVsSpy === null) {
    return {
      confidence: 'unavailable',
      interpretation: 'Relative strength is unavailable because stock or SPY history is incomplete.',
      label: 'Unavailable',
      state: 'unavailable',
    };
  }
  const slope = stockSeries.length >= 4 ? stockSeries.at(-1)!.value - stockSeries[Math.max(0, stockSeries.length - 4)].value : 0;
  const confidence = stockSeries.length >= 20 && peerRanking.rankedCount >= 3 ? 'high' : stockSeries.length >= 6 ? 'moderate' : 'low';
  const leadingMarket = edgeVsSpy > MIN_EDGE_POINTS;
  const laggingMarket = edgeVsSpy < -MIN_EDGE_POINTS;
  const leadingTheme = edgeVsTheme !== null && edgeVsTheme > MIN_EDGE_POINTS;
  const laggingTheme = edgeVsTheme !== null && edgeVsTheme < -MIN_EDGE_POINTS;
  const strongThemeEdge = edgeVsTheme !== null && edgeVsTheme > STRONG_EDGE_POINTS;

  if (leadingMarket && leadingTheme && peerRanking.rank === 1) {
    return {
      confidence,
      interpretation: 'The stock is outperforming both SPY and its theme benchmark, contributing leadership rather than merely following the group.',
      label: 'Leading Market and Theme',
      state: 'leading_market_and_theme',
    };
  }
  if (leadingTheme || strongThemeEdge) {
    return {
      confidence,
      interpretation: 'The stock is outperforming its theme benchmark, suggesting theme-level leadership.',
      label: 'Leading Theme',
      state: 'leading_theme',
    };
  }
  if (leadingMarket && edgeVsTheme !== null && Math.abs(edgeVsTheme) <= MIN_EDGE_POINTS) {
    return {
      confidence,
      interpretation: 'The stock is outperforming SPY but moving close to its theme benchmark, so leadership appears tied to the group.',
      label: 'Following Theme',
      state: 'following_theme',
    };
  }
  if (leadingMarket && laggingTheme && slope < 0) {
    return {
      confidence,
      interpretation: 'The stock still leads the market, but it is weakening versus its theme benchmark.',
      label: 'Theme Leader Weakening',
      state: 'leader_weakening',
    };
  }
  if (laggingMarket && laggingTheme) {
    return {
      confidence,
      interpretation: 'The stock is lagging both SPY and its peer group over the selected timeframe.',
      label: 'Lagging Market and Peers',
      state: 'lagging_market_and_peers',
    };
  }
  if (laggingTheme) {
    return {
      confidence,
      interpretation: 'The stock is trailing its theme benchmark, so recent movement looks more peer-led than stock-led.',
      label: 'Lagging Theme',
      state: 'lagging_theme',
    };
  }
  return {
    confidence,
    interpretation: 'Relative performance is mixed without a decisive edge versus the available benchmarks.',
    label: 'Mixed',
    state: 'mixed',
  };
}

export function calculatePeerRank(peers: PeerComparisonViewModel[], selectedSymbol: string): PeerRankingViewModel {
  const valid = peers
    .filter((peer) => peer.periodReturn !== null)
    .sort((a, b) => {
      const diff = (b.periodReturn ?? -Infinity) - (a.periodReturn ?? -Infinity);
      return Math.abs(diff) > 0.0001 ? diff : a.symbol.localeCompare(b.symbol);
    });
  const rank = valid.findIndex((peer) => peer.symbol === selectedSymbol) + 1;
  const rankedCount = valid.length;
  const selected = valid.find((peer) => peer.symbol === selectedSymbol);
  const themeMedian = calculateMedian(valid.filter((peer) => peer.symbol !== selectedSymbol).map((peer) => peer.periodReturn).filter(isValidNumber));
  const topPeer = valid.find((peer) => peer.symbol !== selectedSymbol);
  return {
    aboveMedian: calculateRelativeEdge(selected?.periodReturn ?? null, themeMedian),
    confidence: rankedCount >= 5 ? 'high' : rankedCount >= 3 ? 'moderate' : rankedCount >= 2 ? 'low' : 'unavailable',
    items: valid,
    percentile: rank > 0 && rankedCount > 2 ? ((rankedCount - rank) / Math.max(1, rankedCount - 1)) * 100 : null,
    rank: rank || null,
    rankedCount,
    themeMedian,
    topPeerEdge: calculateRelativeEdge(selected?.periodReturn ?? null, topPeer?.periodReturn ?? null),
  };
}

function buildPeerComparisons({
  asOfDate,
  histories,
  peerSymbols,
  selectedSymbol,
  stock,
  stockReturn,
  timeframe,
  volumeAnalysis,
}: {
  asOfDate: string | null;
  histories: Record<string, HistoryData | null | undefined>;
  peerSymbols: string[];
  selectedSymbol: string;
  stock?: WatchlistItem | null;
  stockReturn: number | null;
  timeframe: StockCompareTimeframe;
  volumeAnalysis?: VolumeAnalysis | null;
}): PeerComparisonViewModel[] {
  const symbols = [selectedSymbol, ...peerSymbols];
  return symbols.map((symbol) => {
    const window = selectComparisonWindow(deduplicateDailyHistory(histories[symbol]), timeframe, asOfDate);
    const periodReturn = symbol === selectedSymbol ? stockReturn : getPointsReturn(window);
    const closes = window.map((point) => point.close).filter(isValidNumber);
    const high = closes.length ? Math.max(...closes) : null;
    const last = closes.at(-1) ?? null;
    return {
      distanceFromHigh: high && last ? (last / high - 1) * 100 : null,
      isSelectedStock: symbol === selectedSymbol,
      momentum: classifyMomentum(periodReturn),
      periodReturn,
      relativeStrength: classifyPeerLeadership(periodReturn),
      setup: symbol === selectedSymbol ? stock?.setup ?? 'N/A' : classifySetup(periodReturn, high && last ? (last / high - 1) * 100 : null),
      symbol,
      trend: classifyTrend(closes),
      volume: symbol === selectedSymbol ? volumeAnalysis?.volume_quality ?? 'N/A' : 'N/A',
    };
  });
}

function buildLeadershipRead(
  relativeStrength: StockRelativeStrengthViewModel,
  ranking: PeerRankingViewModel,
  performance: StockPerformanceSummary,
  symbol: string,
  themeName: string | null,
): LeadershipReadViewModel {
  const rankText = ranking.rank && ranking.rankedCount ? `${ranking.rank} of ${ranking.rankedCount}` : 'Unavailable';
  const themeLabel = themeName ?? 'tracked peers';
  const classification = relativeStrength.state === 'leading_market_and_theme' || ranking.rank === 1
    ? 'Theme Leader'
    : relativeStrength.state === 'following_theme'
      ? 'Strong Follower'
      : relativeStrength.state.includes('lagging')
        ? 'Lagging Peer'
        : 'Mixed Leadership';
  return {
    classification,
    mainRisk: performance.edgeVsTheme !== null && performance.edgeVsTheme < 0
      ? 'Leadership would improve only if the stock recovers versus its theme median or benchmark.'
      : 'Leadership would weaken if the stock falls below the theme median or loses its medium-term trend.',
    mainStrength: performance.edgeVsSpy !== null && performance.edgeVsSpy > MIN_EDGE_POINTS
      ? 'Relative performance is ahead of SPY.'
      : 'Peer comparison is the main context until a stronger market edge appears.',
    summary: `${symbol} ranks ${rankText} among ${ranking.rankedCount || 'available'} tracked ${themeLabel} peers. ${relativeStrength.interpretation}`,
  };
}

function contextWithLimitedPeers(context: StockThemeContext, peerSymbols: string[]): StockThemeContext {
  return {
    ...context,
    peerSymbols,
  };
}

function buildAlignmentSummary({
  asOfDate,
  spySeries,
  stockSeries,
  themeBenchmark,
  themeSeries,
}: {
  asOfDate: string | null;
  spySeries: NormalizedSeriesPoint[];
  stockSeries: NormalizedSeriesPoint[];
  themeBenchmark: ThemeBenchmark | null;
  themeSeries: NormalizedSeriesPoint[];
}): ComparisonAlignmentSummary {
  const benchmarkDates = new Set([
    ...spySeries.map((point) => point.timestamp.slice(0, 10)),
    ...themeSeries.map((point) => point.timestamp.slice(0, 10)),
  ]);
  const alignedPointCount = stockSeries.filter((point) => benchmarkDates.has(point.timestamp.slice(0, 10))).length;
  return {
    alignedPointCount,
    asOfDate,
    constituentCount: themeBenchmark?.constituentCount ?? 0,
    minimumConstituentsPerPoint: themeBenchmark?.minimumConstituentsPerPoint ?? 0,
    spyPointCount: spySeries.length,
    stockPointCount: stockSeries.length,
    themePointCount: themeSeries.length,
  };
}

function getUnavailableReason({
  rawStockSeries,
  renderedSeriesCount,
  spySeries,
  stockSeries,
  themeContext,
  themeSeries,
}: {
  rawStockSeries: NormalizedSeriesPoint[];
  renderedSeriesCount: number;
  spySeries: NormalizedSeriesPoint[];
  stockSeries: NormalizedSeriesPoint[];
  themeContext: StockThemeContext;
  themeSeries: NormalizedSeriesPoint[];
}): ComparisonUnavailableReason | null {
  if (renderedSeriesCount >= 2) {
    return null;
  }
  if (!stockSeries.length) {
    if (rawStockSeries.length === 1) {
      return 'insufficient_points';
    }
    return 'stock_history_missing';
  }
  if (stockSeries.length === 1) {
    return 'insufficient_points';
  }
  if (!spySeries.length && !themeSeries.length) {
    return themeContext.primaryThemeName ? 'no_overlapping_dates' : 'spy_history_missing';
  }
  if (!spySeries.length) {
    return 'spy_history_missing';
  }
  if (themeContext.primaryThemeName && !themeSeries.length) {
    return 'theme_history_missing';
  }
  return 'unavailable';
}

function buildDataQuality({
  alignment,
  histories,
  peerSymbols,
  rawStockSeries,
  renderedSeriesCount,
  spySeries,
  spySymbol,
  stockSeries,
  symbol,
  themeBenchmark,
  themeContext,
  themeSeries,
}: {
  alignment: ComparisonAlignmentSummary;
  histories: Record<string, HistoryData | null | undefined>;
  peerSymbols: string[];
  rawStockSeries: NormalizedSeriesPoint[];
  renderedSeriesCount: number;
  spySeries: NormalizedSeriesPoint[];
  spySymbol: string;
  stockSeries: NormalizedSeriesPoint[];
  symbol: string;
  themeBenchmark: ThemeBenchmark | null;
  themeContext: StockThemeContext;
  themeSeries: NormalizedSeriesPoint[];
}): StockComparisonDataQualityViewModel {
  const includedPeerCount = themeBenchmark?.constituentCount
    ?? peerSymbols.filter((peer) => getPeriodReturn(histories[peer]) !== null).length;
  const source = histories[symbol]?.source ?? histories[spySymbol]?.source ?? 'unavailable';
  const unavailableReason = getUnavailableReason({
    rawStockSeries,
    renderedSeriesCount,
    spySeries,
    stockSeries,
    themeContext,
    themeSeries,
  });
  const partialNotice = renderedSeriesCount >= 2 && themeContext.primaryThemeName && !themeSeries.length
    ? 'Theme benchmark unavailable; rendering available stock and market history.'
    : renderedSeriesCount >= 2 && !spySeries.length
      ? 'SPY benchmark unavailable; rendering available comparison history.'
      : null;
  const warnings = [
    !themeContext.primaryThemeName ? 'No primary theme membership is configured for this stock.' : null,
    !themeBenchmark || themeBenchmark.kind === 'unavailable' ? 'Theme benchmark is unavailable; compare uses stock and SPY where possible.' : null,
    includedPeerCount < 2 ? 'Peer ranking confidence is limited by available peer histories.' : null,
  ].filter((item): item is string => Boolean(item));
  return {
    alignment,
    benchmarkLabel: themeBenchmark?.label ?? 'Theme benchmark unavailable',
    benchmarkMethod: themeBenchmark ? benchmarkMethodLabel(themeBenchmark) : 'Unavailable',
    dataSource: source,
    dataSourceLabel: formatDataSourceLabel(source),
    includedPeerCount,
    partialNotice,
    peerUniverseLabel: themeContext.primaryThemeName
      ? `${includedPeerCount} of ${peerSymbols.length} ${peerSymbols.length === 1 ? 'peer' : 'peers'} included`
      : 'No configured theme peer universe',
    unavailableReason,
    warnings,
  };
}

function benchmarkMethodLabel(benchmark: ThemeBenchmark) {
  switch (benchmark.kind) {
    case 'equal_weight_composite':
      return `Equal-weight composite from ${benchmark.constituentCount ?? 0} valid ${benchmark.constituentCount === 1 ? 'peer' : 'peers'}`;
    case 'peer_median':
      return 'Peer median fallback';
    case 'sector':
      return 'Sector fallback';
    case 'theme_etf':
      return `Theme ETF ${benchmark.symbol ?? ''}`.trim();
    case 'theme_index':
      return 'Configured theme index';
    default:
      return 'Unavailable';
  }
}

function classifyPeerLeadership(value: number | null): PeerLeadershipState {
  if (value === null) {
    return 'unavailable';
  }
  if (value >= 10) {
    return 'leader';
  }
  if (value >= 4) {
    return 'strong';
  }
  if (value <= -8) {
    return 'weak';
  }
  if (value < -2) {
    return 'lagging';
  }
  return 'neutral';
}

function classifyMomentum(value: number | null) {
  if (value === null) {
    return 'N/A';
  }
  if (value >= 8) {
    return 'Strong';
  }
  if (value >= 2) {
    return 'Healthy';
  }
  if (value <= -5) {
    return 'Weak';
  }
  return 'Neutral';
}

function classifyTrend(closes: number[]) {
  if (closes.length < 5) {
    return 'N/A';
  }
  const last = closes.at(-1)!;
  const short = average(closes.slice(-5));
  const medium = average(closes.slice(-20));
  if (last > short && short > medium) {
    return 'Strong';
  }
  if (last > medium) {
    return 'Constructive';
  }
  if (last < medium) {
    return 'Weakening';
  }
  return 'Neutral';
}

function classifySetup(periodReturn: number | null, distanceFromHigh: number | null) {
  if (periodReturn === null) {
    return 'N/A';
  }
  if (distanceFromHigh !== null && distanceFromHigh > -5) {
    return 'Near High';
  }
  if (periodReturn > 5) {
    return 'Momentum';
  }
  if (periodReturn < -4) {
    return 'Repairing';
  }
  return 'Base Building';
}

function slugify(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
}

function calculateMedian(values: number[]) {
  if (!values.length) {
    return null;
  }
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}

function average(values: number[]) {
  return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0;
}

function isValidNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}
