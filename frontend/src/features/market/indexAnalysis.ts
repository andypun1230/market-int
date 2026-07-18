import type { CandleData, HistoryData, IndexSnapshot } from '@/types/market';

export const indexSymbols = ['SPY', 'QQQ', 'IWM', 'DIA'] as const;

export type IndexSymbol = typeof indexSymbols[number];
export type IndexTimeframe = '1D' | '1W' | '1M' | '6M' | '1Y';
export type SignalTone = 'positive' | 'warning' | 'negative' | 'neutral';

export type IndexTrendState =
  | 'strong_uptrend'
  | 'uptrend'
  | 'pullback_in_uptrend'
  | 'range'
  | 'recovery_attempt'
  | 'downtrend'
  | 'trend_weakening'
  | 'unavailable';

export type VolumeConfirmation =
  | 'confirmed_buying'
  | 'weak_advance'
  | 'distribution'
  | 'orderly_pullback'
  | 'neutral'
  | 'unavailable';

export type VolumeSourceStatus = 'valid' | 'proxy' | 'unavailable' | 'incompatible';

export type IndexSetup =
  | 'bullish_continuation'
  | 'pullback_to_support'
  | 'breakout_attempt'
  | 'range_consolidation'
  | 'recovery_attempt'
  | 'trend_weakening'
  | 'distribution'
  | 'downtrend_continuation'
  | 'no_clear_setup'
  | 'unavailable';

export type IndexChartPoint = {
  dateLabel: string;
  timestamp: string;
  value: number;
};

export type CompactSetupRow = {
  label: string;
  tone?: SignalTone;
  value: string;
};

export type IndexAnalysis = {
  averageVolume20: number | null;
  candles: CandleData[];
  chartPoints: IndexChartPoint[];
  latestCandle: CandleData | null;
  periodReturn: number | null;
  recentHigh20: number | null;
  recentLow20: number | null;
  relativeStrengthLabel: string;
  setup: {
    explanation: string;
    label: string;
    rows: CompactSetupRow[];
    state: IndexSetup;
    technicalRows: CompactSetupRow[];
    tone: SignalTone;
  };
  snapshot: IndexSnapshot;
  symbol: IndexSymbol;
  trend: {
    detail: string;
    explanation: string;
    label: string;
    state: IndexTrendState;
    tone: SignalTone;
  };
  volume: {
    averageVolume: number | null;
    label: string;
    latestVolume: number | null;
    ratio: number | null;
    sourceLabel: string;
    sourceStatus: VolumeSourceStatus;
    state: VolumeConfirmation;
    tone: SignalTone;
  };
};

export const indexTimeframes: IndexTimeframe[] = ['1D', '1W', '1M', '6M', '1Y'];

export const indexTimeframeSessions: Record<IndexTimeframe, number> = {
  '1D': 2,
  '1W': 6,
  '1M': 22,
  '6M': 132,
  '1Y': 252,
};

export function filterDisplayIndexes(indexes: IndexSnapshot[]) {
  return indexSymbols
    .map((symbol) => indexes.find((index) => normalizeIndexSymbol(index.symbol) === symbol))
    .filter((index): index is IndexSnapshot => Boolean(index));
}

export function normalizeIndexSymbol(symbol: string): IndexSymbol | null {
  const upper = symbol.toUpperCase();
  return indexSymbols.includes(upper as IndexSymbol) ? upper as IndexSymbol : null;
}

export function analyzeIndexes(
  indexes: IndexSnapshot[],
  histories: Partial<Record<IndexSymbol, HistoryData>>,
  timeframe: IndexTimeframe,
): IndexAnalysis[] {
  const analyses = filterDisplayIndexes(indexes).map((snapshot) => analyzeIndex(snapshot, histories, timeframe));
  const returns = analyses
    .map((analysis) => analysis.periodReturn)
    .filter((value): value is number => Number.isFinite(value));

  if (!returns.length) {
    return analyses.map((analysis) => ({ ...analysis, relativeStrengthLabel: 'RS unavailable' }));
  }

  const sortedReturns = [...returns].sort((a, b) => b - a);
  const medianReturn = sortedReturns[Math.floor(sortedReturns.length / 2)] ?? 0;
  return analyses.map((analysis) => {
    if (analysis.periodReturn === null) {
      return { ...analysis, relativeStrengthLabel: 'RS unavailable' };
    }
    const spread = analysis.periodReturn - medianReturn;
    const relativeStrengthLabel = spread >= 1
      ? 'Leading'
      : spread <= -1
        ? 'Lagging'
        : 'Neutral RS';
    return { ...analysis, relativeStrengthLabel };
  });
}

export function normalizeIndexSeries(candles: CandleData[], timeframe: IndexTimeframe): IndexChartPoint[] {
  const selected = selectTimeframeCandles(candles, timeframe);
  const firstClose = selected.find((candle) => candle.close > 0)?.close;
  if (!firstClose) {
    return [];
  }
  return selected
    .filter((candle) => candle.close > 0)
    .map((candle) => ({
      dateLabel: formatDateLabel(candle.timestamp),
      timestamp: candle.timestamp,
      value: ((candle.close / firstClose) - 1) * 100,
    }));
}

export function calculatePeriodReturn(candles: CandleData[], timeframe: IndexTimeframe): number | null {
  const selected = selectTimeframeCandles(candles, timeframe);
  const first = selected.find((candle) => candle.close > 0);
  const latest = [...selected].reverse().find((candle) => candle.close > 0);
  if (!first || !latest || first.close <= 0) {
    return null;
  }
  return ((latest.close / first.close) - 1) * 100;
}

export function calculateAverageVolume(candles: CandleData[], sessions = 20): number | null {
  const volumes = candles
    .slice(-sessions)
    .map((candle) => candle.volume)
    .filter((volume) => Number.isFinite(volume) && volume > 0);
  if (!volumes.length) {
    return null;
  }
  return volumes.reduce((sum, volume) => sum + volume, 0) / volumes.length;
}

export function classifyIndexTrend(snapshot: IndexSnapshot, periodReturn: number | null) {
  const price = snapshot.price;
  const { ema_20: ema20, ema_50: ema50, ema_200: ema200, rsi_14: rsi } = snapshot;
  if (!isFiniteNumber(price) || !isFiniteNumber(ema20) || !isFiniteNumber(ema50) || !isFiniteNumber(ema200)) {
    return {
      detail: 'Inputs incomplete',
      explanation: 'Trend classification needs price and moving-average data.',
      label: 'Unavailable',
      state: 'unavailable' as IndexTrendState,
      tone: 'neutral' as SignalTone,
    };
  }

  const ret = periodReturn ?? 0;
  const clusteredAverages = Math.abs((ema20 - ema50) / price) < 0.015 && Math.abs((ema50 - ema200) / price) < 0.025;
  // Broad deterministic thresholds: trend is driven by price versus 20/50/200 EMA structure,
  // while selected-period return and RSI adjust pullback/range states.
  if (price > ema20 && ema20 > ema50 && ema50 > ema200 && ret > 0) {
    return {
      detail: 'Above EMA20/50/200',
      explanation: 'Price is above the 20, 50, and 200-day averages with positive period performance.',
      label: 'Strong Uptrend',
      state: 'strong_uptrend' as IndexTrendState,
      tone: 'positive' as SignalTone,
    };
  }
  if (price > ema50 && price > ema200 && (ret < -0.25 || price < ema20)) {
    return {
      detail: 'Medium trend intact',
      explanation: 'Medium-term trend remains intact, but short-term price action is pulling back.',
      label: 'Pullback in Uptrend',
      state: 'pullback_in_uptrend' as IndexTrendState,
      tone: 'warning' as SignalTone,
    };
  }
  if (price > ema50 && price > ema200 && ema50 >= ema200) {
    return {
      detail: 'Above EMA50/200',
      explanation: 'Price remains above the key intermediate and long-term averages.',
      label: 'Uptrend',
      state: 'uptrend' as IndexTrendState,
      tone: 'positive' as SignalTone,
    };
  }
  if (price < ema50 && price < ema200) {
    return {
      detail: 'Below EMA50/200',
      explanation: 'Price is below both the 50 and 200-day averages.',
      label: 'Downtrend',
      state: 'downtrend' as IndexTrendState,
      tone: 'negative' as SignalTone,
    };
  }
  if (price > ema20 && price < ema200 && ret > 0) {
    return {
      detail: 'Improving from weak base',
      explanation: 'Price is improving from below longer-term trend levels.',
      label: 'Recovery Attempt',
      state: 'recovery_attempt' as IndexTrendState,
      tone: 'warning' as SignalTone,
    };
  }
  if (price < ema20 && ret < 0) {
    return {
      detail: 'Below short-term trend',
      explanation: 'Short-term price action is weakening versus the 20-day average.',
      label: 'Trend Weakening',
      state: 'trend_weakening' as IndexTrendState,
      tone: 'warning' as SignalTone,
    };
  }
  if (clusteredAverages || (rsi != null && rsi >= 45 && rsi <= 55 && Math.abs(ret) < 1.5)) {
    return {
      detail: 'Neutral structure',
      explanation: 'Moving averages and momentum are clustered near neutral levels.',
      label: 'Range',
      state: 'range' as IndexTrendState,
      tone: 'neutral' as SignalTone,
    };
  }
  return {
    detail: 'Mixed signals',
    explanation: 'Signals are mixed without a clear directional trend.',
    label: 'Range',
    state: 'range' as IndexTrendState,
    tone: 'neutral' as SignalTone,
  };
}

export function classifyVolumeConfirmation(
  snapshot: IndexSnapshot,
  candles: CandleData[],
  symbol: IndexSymbol = normalizeIndexSymbol(snapshot.symbol) ?? 'SPY',
) {
  const averageVolume = calculateAverageVolume(candles);
  const latestCandle = candles.at(-1) ?? null;
  const latestVolume = symbol === 'DIA'
    ? latestCandle?.volume ?? null
    : snapshot.volume ?? latestCandle?.volume ?? null;
  const sourceStatus: VolumeSourceStatus = symbol === 'DIA' ? 'proxy' : 'valid';
  const sourceLabel = symbol === 'DIA' ? 'Dow Jones ETF proxy volume' : 'ETF volume';

  if (!latestVolume || !averageVolume) {
    return buildVolume('Volume unavailable', null, latestVolume, averageVolume, 'Volume unavailable', 'unavailable', 'unavailable', 'neutral');
  }

  const ratio = latestVolume / averageVolume;
  if (!Number.isFinite(ratio) || ratio <= 0 || ratio > 6 || ratio < 0.08) {
    return buildVolume(
      'Volume unavailable',
      null,
      latestVolume,
      averageVolume,
      symbol === 'DIA' ? 'Dow Jones proxy volume unavailable' : 'Volume unavailable',
      'incompatible',
      'unavailable',
      'neutral',
    );
  }

  const dailyMove = snapshot.change_percent;
  if (Math.abs(dailyMove) < 0.15) {
    return buildVolume('Neutral participation', ratio, latestVolume, averageVolume, sourceLabel, sourceStatus, 'neutral', 'neutral');
  }
  if (dailyMove > 0 && ratio >= 1.1) {
    return buildVolume('Confirmed buying', ratio, latestVolume, averageVolume, sourceLabel, sourceStatus, 'confirmed_buying', 'positive');
  }
  if (dailyMove > 0 && ratio < 0.9) {
    return buildVolume('Advance lacks confirmation', ratio, latestVolume, averageVolume, sourceLabel, sourceStatus, 'weak_advance', 'warning');
  }
  if (dailyMove < 0 && ratio >= 1.1) {
    return buildVolume('Distribution pressure', ratio, latestVolume, averageVolume, sourceLabel, sourceStatus, 'distribution', 'negative');
  }
  if (dailyMove < 0 && ratio < 0.9) {
    return buildVolume('Orderly pullback', ratio, latestVolume, averageVolume, sourceLabel, sourceStatus, 'orderly_pullback', 'neutral');
  }
  return buildVolume('Neutral participation', ratio, latestVolume, averageVolume, sourceLabel, sourceStatus, 'neutral', 'neutral');
}

export function classifyIndexSetup(
  snapshot: IndexSnapshot,
  trend: IndexAnalysis['trend'],
  volume: IndexAnalysis['volume'],
  candles: CandleData[],
) {
  const recentHigh20 = getRecentHigh(candles, 20);
  const recentLow20 = getRecentLow(candles, 20);
  const nearHigh = recentHigh20 != null && Math.abs(snapshot.price - recentHigh20) / recentHigh20 <= 0.01;
  const nearEma20 = snapshot.ema_20 != null && Math.abs(snapshot.price - snapshot.ema_20) / snapshot.price <= 0.015;
  const rsi = snapshot.rsi_14;

  if (trend.state === 'unavailable') {
    return buildSetup('unavailable', 'Unavailable', 'Setup analysis needs more data.', [
      { label: 'Trend', value: 'Unavailable' },
      { label: 'Momentum', value: 'RSI N/A' },
      { label: 'Volume', value: 'Volume N/A' },
      { label: 'Risk', value: 'Wait for complete data', tone: 'neutral' },
    ], snapshot, volume);
  }

  if (trend.state === 'strong_uptrend' && nearHigh && volume.state !== 'distribution') {
    return buildSetup('breakout_attempt', 'Breakout Attempt', trend.explanation, compactRows(
      trend,
      rsi,
      volume,
      buildRecentHighText(recentHigh20),
      buildSupportText(snapshot.ema_20, snapshot.ema_50, recentLow20),
      buildRiskText(snapshot.ema_20, 'Sustained break below'),
    ), snapshot, volume);
  }
  if ((trend.state === 'strong_uptrend' || trend.state === 'uptrend') && volume.state === 'confirmed_buying') {
    return buildSetup('bullish_continuation', 'Bullish Continuation', trend.explanation, compactRows(
      trend,
      rsi,
      volume,
      'Continuation above short-term trend',
      buildSupportText(snapshot.ema_20, snapshot.ema_50, recentLow20),
      buildRiskText(snapshot.ema_20, 'Sustained break below'),
    ), snapshot, volume);
  }
  if (trend.state === 'pullback_in_uptrend' || nearEma20) {
    return buildSetup('pullback_to_support', 'Pullback to Support', trend.explanation, compactRows(
      trend,
      rsi,
      volume,
      'Stabilize near support',
      buildSupportText(snapshot.ema_20, snapshot.ema_50, recentLow20),
      buildRiskText(snapshot.ema_50, 'Break below'),
    ), snapshot, volume);
  }
  if (volume.state === 'distribution') {
    return buildSetup('distribution', 'Distribution', trend.explanation, compactRows(
      trend,
      rsi,
      volume,
      'Reclaim short-term trend',
      buildSupportText(snapshot.ema_20, snapshot.ema_50, recentLow20),
      buildRiskText(snapshot.ema_20, 'Failure below'),
    ), snapshot, volume);
  }
  if (trend.state === 'downtrend') {
    return buildSetup('downtrend_continuation', 'Downtrend Continuation', trend.explanation, compactRows(
      trend,
      rsi,
      volume,
      'Failed rallies remain risk',
      buildSupportText(null, snapshot.ema_50, recentLow20),
      buildRiskText(snapshot.ema_50, 'Recovery above'),
    ), snapshot, volume);
  }
  if (trend.state === 'recovery_attempt') {
    return buildSetup('recovery_attempt', 'Recovery Attempt', trend.explanation, compactRows(
      trend,
      rsi,
      volume,
      buildRecentHighText(recentHigh20),
      buildSupportText(null, snapshot.ema_50, recentLow20),
      buildRecentLowRiskText(recentLow20),
    ), snapshot, volume);
  }
  if (trend.state === 'trend_weakening') {
    return buildSetup('trend_weakening', 'Trend Weakening', trend.explanation, compactRows(
      trend,
      rsi,
      volume,
      'Reclaim EMA20',
      buildSupportText(snapshot.ema_20, snapshot.ema_50, recentLow20),
      buildRiskText(snapshot.ema_20, 'Failure below'),
    ), snapshot, volume);
  }
  if (trend.state === 'range') {
    return buildSetup('range_consolidation', 'Range Consolidation', trend.explanation, compactRows(
      trend,
      rsi,
      volume,
      buildRangeText(recentLow20, recentHigh20),
      buildSupportText(snapshot.ema_20, snapshot.ema_50, recentLow20),
      buildRecentLowRiskText(recentLow20),
    ), snapshot, volume);
  }
  return buildSetup('no_clear_setup', 'No Clear Setup', trend.explanation, compactRows(
    trend,
    rsi,
    volume,
    'No clear trigger',
    buildSupportText(snapshot.ema_20, snapshot.ema_50, recentLow20),
    'Needs clearer directional move',
  ), snapshot, volume);
}

export function buildIndexTrendSummary(analyses: IndexAnalysis[]) {
  const valid = analyses.filter((analysis) => analysis.periodReturn !== null && analysis.trend.state !== 'unavailable');
  if (!valid.length) {
    return 'Index trend data is unavailable for SPY, QQQ, IWM, and DIA.';
  }
  const leader = getLeader(valid);
  const laggard = getLaggard(valid);
  const constructive = valid.filter((analysis) => ['strong_uptrend', 'uptrend', 'pullback_in_uptrend'].includes(analysis.trend.state));
  const spread = getReturnSpread(valid);
  const aligned = constructive.length === valid.length && spread < 1.5;
  if (aligned) {
    return `${valid.map((analysis) => analysis.symbol).join(', ')} are moving in broadly constructive alignment. ${leader.symbol} has a small relative edge over the selected period.`;
  }
  const divergence = spread >= 2 ? 'creating moderate index divergence' : 'with only mild index divergence';
  return `${leader.symbol} is leading while ${laggard.symbol} is lagging over the selected period, ${divergence}. ${constructive.length >= 2 ? 'The medium-term trend remains mostly intact.' : 'Trend confirmation is uneven across the major indexes.'}`;
}

export function deriveLeadershipRead(analyses: IndexAnalysis[]) {
  const valid = analyses.filter((analysis) => analysis.periodReturn !== null);
  if (!valid.length) {
    return {
      explanation: 'Leadership cannot be determined until index history is available.',
      title: 'Leadership Unavailable',
      tone: 'neutral' as SignalTone,
    };
  }
  const leader = getLeader(valid);
  const laggard = getLaggard(valid);
  const spread = getReturnSpread(valid);
  const allWeak = valid.every((analysis) => (analysis.periodReturn ?? 0) < -0.5);
  if (allWeak) {
    return {
      explanation: 'All four core indexes are negative over the selected period, indicating broad market pressure.',
      title: 'Broad Market Pressure',
      tone: 'negative' as SignalTone,
    };
  }
  if (spread < 1) {
    return {
      explanation: 'SPY, QQQ, IWM, and DIA are moving closely together, which is consistent with broad participation.',
      title: 'Broad Participation',
      tone: 'positive' as SignalTone,
    };
  }
  if (leader.symbol === 'QQQ') {
    return {
      explanation: 'QQQ is outperforming the other core indexes over the selected period, suggesting stronger growth and technology participation.',
      title: 'Growth Leadership',
      tone: 'positive' as SignalTone,
    };
  }
  if (leader.symbol === 'DIA') {
    return {
      explanation: 'Dow Jones proxy DIA is outperforming SPY and QQQ, which is consistent with rotation toward value-oriented or industrial leadership.',
      title: 'Value-Oriented Leadership',
      tone: 'positive' as SignalTone,
    };
  }
  return {
    explanation: `SPY is leading while ${laggard.symbol} is lagging, suggesting balanced but selective broad-market leadership.`,
    title: 'Balanced Broad-Market Leadership',
    tone: 'positive' as SignalTone,
  };
}

export function deriveMarketLeadershipTrend(analyses: IndexAnalysis[]) {
  const leadership = deriveLeadershipRead(analyses);
  const trend = buildIndexTrendSummary(analyses);
  return {
    explanation: `${leadership.explanation} ${trend}`,
    title: leadership.title,
    tone: leadership.tone,
  };
}

export function getIndexSourceLabel(indexes: IndexSnapshot[], histories: Partial<Record<IndexSymbol, HistoryData>>) {
  const displayIndexes = filterDisplayIndexes(indexes);
  const historyItems = indexSymbols.map((symbol) => histories[symbol]).filter(Boolean);
  const fallback = displayIndexes.some((index) => index.fallback_used) || historyItems.some((history) => history?.fallback_used);
  const stale = displayIndexes.some((index) => index.is_stale) || historyItems.some((history) => history?.is_stale);
  const live = displayIndexes.some((index) => index.is_live || index.quote_is_live) || historyItems.some((history) => history?.is_live);
  const mock = displayIndexes.some((index) => String(index.data_source ?? '').includes('mock')) || historyItems.some((history) => String(history?.source ?? '').includes('mock'));

  if (fallback) {
    return 'Mixed sources';
  }
  if (mock) {
    return 'Mock data';
  }
  if (stale) {
    return 'Cached data';
  }
  if (live) {
    return 'Live';
  }
  return 'Data source unavailable';
}

function analyzeIndex(
  snapshot: IndexSnapshot,
  histories: Partial<Record<IndexSymbol, HistoryData>>,
  timeframe: IndexTimeframe,
): IndexAnalysis {
  const symbol = normalizeIndexSymbol(snapshot.symbol) ?? 'SPY';
  const candles = normalizeCandles(histories[symbol]?.candles ?? []);
  const periodReturn = calculatePeriodReturn(candles, timeframe);
  const trend = classifyIndexTrend(snapshot, periodReturn);
  const volume = classifyVolumeConfirmation(snapshot, candles, symbol);
  const setup = classifyIndexSetup(snapshot, trend, volume, candles);
  return {
    averageVolume20: calculateAverageVolume(candles),
    candles,
    chartPoints: normalizeIndexSeries(candles, timeframe),
    latestCandle: candles.at(-1) ?? null,
    periodReturn,
    recentHigh20: getRecentHigh(candles, 20),
    recentLow20: getRecentLow(candles, 20),
    relativeStrengthLabel: 'RS unavailable',
    setup,
    snapshot,
    symbol,
    trend,
    volume,
  };
}

function buildVolume(
  label: string,
  ratio: number | null,
  latestVolume: number | null,
  averageVolume: number | null,
  sourceLabel: string,
  sourceStatus: VolumeSourceStatus,
  state: VolumeConfirmation,
  tone: SignalTone,
) {
  return {
    averageVolume,
    label,
    latestVolume,
    ratio,
    sourceLabel,
    sourceStatus,
    state,
    tone,
  };
}

function normalizeCandles(candles: CandleData[]) {
  const byTimestamp = new Map<string, CandleData>();
  candles.forEach((candle) => {
    if (!candle.timestamp || !isFiniteNumber(candle.close) || candle.close <= 0) {
      return;
    }
    byTimestamp.set(candle.timestamp, candle);
  });
  return [...byTimestamp.values()].sort((a, b) => Date.parse(a.timestamp) - Date.parse(b.timestamp));
}

function selectTimeframeCandles(candles: CandleData[], timeframe: IndexTimeframe) {
  return normalizeCandles(candles).slice(-indexTimeframeSessions[timeframe]);
}

function getRecentHigh(candles: CandleData[], sessions: number) {
  const highs = candles.slice(-sessions).map((candle) => candle.high).filter(isFiniteNumber);
  return highs.length ? Math.max(...highs) : null;
}

function getRecentLow(candles: CandleData[], sessions: number) {
  const lows = candles.slice(-sessions).map((candle) => candle.low).filter(isFiniteNumber);
  return lows.length ? Math.min(...lows) : null;
}

function getLeader(analyses: IndexAnalysis[]) {
  return [...analyses].sort((a, b) => (b.periodReturn ?? Number.NEGATIVE_INFINITY) - (a.periodReturn ?? Number.NEGATIVE_INFINITY))[0];
}

function getLaggard(analyses: IndexAnalysis[]) {
  return [...analyses].sort((a, b) => (a.periodReturn ?? Number.POSITIVE_INFINITY) - (b.periodReturn ?? Number.POSITIVE_INFINITY))[0];
}

function getReturnSpread(analyses: IndexAnalysis[]) {
  const returns = analyses.map((analysis) => analysis.periodReturn).filter((value): value is number => value !== null);
  return returns.length < 2 ? 0 : Math.max(...returns) - Math.min(...returns);
}

function buildSetup(
  state: IndexSetup,
  label: string,
  explanation: string,
  rows: CompactSetupRow[],
  snapshot: IndexSnapshot,
  volume: IndexAnalysis['volume'],
) {
  return {
    explanation,
    label,
    rows: rows.filter((row) => row.value && row.value !== 'N/A'),
    state,
    technicalRows: [
      { label: 'EMA20', value: formatLevelOrNa(snapshot.ema_20) },
      { label: 'EMA50', value: formatLevelOrNa(snapshot.ema_50) },
      { label: 'EMA200', value: formatLevelOrNa(snapshot.ema_200) },
      { label: 'RSI14', value: snapshot.rsi_14 == null ? 'N/A' : snapshot.rsi_14.toFixed(1) },
      { label: 'Vol Ratio', value: volume.ratio == null ? 'N/A' : `${volume.ratio.toFixed(2)}×` },
    ].filter((row) => row.value !== 'N/A'),
    tone: setupTone(state),
  };
}

function compactRows(
  trend: IndexAnalysis['trend'],
  rsi: number | null | undefined,
  volume: IndexAnalysis['volume'],
  trigger: string,
  support: string,
  risk: string,
): CompactSetupRow[] {
  return [
    { label: 'Trend', tone: trend.tone, value: `${trend.label} · ${trend.detail}` },
    { label: 'Momentum', tone: getRsiTone(rsi), value: formatRsiShort(rsi) },
    { label: 'Volume', tone: volume.tone, value: formatVolumeShort(volume) },
    { label: 'Trigger', value: trigger },
    { label: 'Support', value: support },
    { label: 'Risk', tone: 'warning', value: risk },
  ];
}

function setupTone(state: IndexSetup): SignalTone {
  switch (state) {
    case 'bullish_continuation':
    case 'breakout_attempt':
      return 'positive';
    case 'pullback_to_support':
    case 'recovery_attempt':
    case 'trend_weakening':
      return 'warning';
    case 'distribution':
    case 'downtrend_continuation':
      return 'negative';
    default:
      return 'neutral';
  }
}

function getRsiTone(rsi: number | null | undefined): SignalTone {
  if (rsi == null) {
    return 'neutral';
  }
  if (rsi >= 55 && rsi < 70) {
    return 'positive';
  }
  if (rsi >= 70 || rsi < 45) {
    return 'warning';
  }
  return 'neutral';
}

function formatRsiShort(rsi: number | null | undefined) {
  if (rsi == null) {
    return 'RSI N/A';
  }
  if (rsi >= 70) {
    return `RSI ${rsi.toFixed(1)} · Extended`;
  }
  if (rsi >= 55) {
    return `RSI ${rsi.toFixed(1)} · Healthy`;
  }
  if (rsi >= 45) {
    return `RSI ${rsi.toFixed(1)} · Neutral`;
  }
  return `RSI ${rsi.toFixed(1)} · Weak`;
}

function formatVolumeShort(volume: IndexAnalysis['volume']) {
  return volume.ratio == null ? 'Volume N/A' : `${volume.ratio.toFixed(2)}× avg · ${volume.label}`;
}

function buildRecentHighText(level: number | null) {
  return level == null ? 'Above recent high' : `Above recent high · ${formatLevel(level)}`;
}

function buildRecentLowRiskText(level: number | null) {
  return level == null ? 'Loss of recent range low' : `Break below ${formatLevel(level)}`;
}

function buildSupportText(ema20: number | null | undefined, ema50: number | null | undefined, recentLow: number | null) {
  if (ema20 != null) {
    return `EMA20 · ${formatLevel(ema20)}`;
  }
  if (ema50 != null) {
    return `EMA50 · ${formatLevel(ema50)}`;
  }
  if (recentLow != null) {
    return `Recent low · ${formatLevel(recentLow)}`;
  }
  return 'Support N/A';
}

function buildRiskText(level: number | null | undefined, prefix: string) {
  return level == null ? prefix : `${prefix} ${formatLevel(level)}`;
}

function buildRangeText(low: number | null, high: number | null) {
  if (low != null && high != null) {
    return `${formatLevel(low)} to ${formatLevel(high)}`;
  }
  return 'Range boundaries N/A';
}

function formatLevelOrNa(value: number | null | undefined) {
  return value == null ? 'N/A' : formatLevel(value);
}

function formatLevel(value: number) {
  return value.toLocaleString('en-US', {
    maximumFractionDigits: value >= 1000 ? 0 : 2,
    minimumFractionDigits: value >= 1000 ? 0 : 2,
  });
}

function formatDateLabel(timestamp: string) {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return 'N/A';
  }
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}
