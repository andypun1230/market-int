import type { HistoryData } from '@/types/market';
import { calculatePeriodReturn, normalizeIndexSeries, type IndexChartPoint, type IndexTimeframe } from './indexAnalysis';

export type WeightComparisonPairId = 'sp500' | 'nasdaq100';
export type ConcentrationState =
  | 'broad_participation'
  | 'mild_concentration'
  | 'mega_cap_concentration'
  | 'equal_weight_leadership'
  | 'mixed'
  | 'unavailable';

export type WeightComparisonPoint = {
  dateLabel: string;
  equalWeightReturn: number;
  spreadPoints: number;
  timestamp: string;
  weightedReturn: number;
};

export type WeightComparisonViewModel = {
  confidence: 'high' | 'moderate' | 'low' | 'unavailable';
  equalWeightPeriodReturn: number | null;
  equalWeightSeries: IndexChartPoint[];
  equalWeightSymbol: string;
  pairId: WeightComparisonPairId;
  pairLabel: string;
  points: WeightComparisonPoint[];
  spreadPoints: number | null;
  state: ConcentrationState;
  stateLabel: string;
  summary: string;
  weightedPeriodReturn: number | null;
  weightedSeries: IndexChartPoint[];
  weightedSymbol: string;
};

const PAIRS: Record<WeightComparisonPairId, { equal: string; label: string; weighted: string }> = {
  nasdaq100: { equal: 'QQEW', label: 'Nasdaq 100', weighted: 'QQQ' },
  sp500: { equal: 'RSP', label: 'S&P 500', weighted: 'SPY' },
};

export function buildWeightComparisonPair(
  pairId: WeightComparisonPairId,
  histories: Partial<Record<string, HistoryData>>,
  timeframe: IndexTimeframe,
): WeightComparisonViewModel {
  const pair = PAIRS[pairId];
  const weightedCandles = histories[pair.weighted]?.candles ?? [];
  const equalCandles = histories[pair.equal]?.candles ?? [];
  const weightedSeries = normalizeIndexSeries(weightedCandles, timeframe);
  const equalWeightSeries = normalizeIndexSeries(equalCandles, timeframe);
  const points = alignWeightSeries(weightedSeries, equalWeightSeries);
  const weightedPeriodReturn = calculatePeriodReturn(weightedCandles, timeframe);
  const equalWeightPeriodReturn = calculatePeriodReturn(equalCandles, timeframe);
  const spreadPoints = weightedPeriodReturn !== null && equalWeightPeriodReturn !== null
    ? weightedPeriodReturn - equalWeightPeriodReturn
    : null;
  const confidence = classifyWeightConfidence(points.length, timeframe);
  const state = classifyConcentrationState(spreadPoints, confidence);
  return {
    confidence,
    equalWeightPeriodReturn,
    equalWeightSeries,
    equalWeightSymbol: pair.equal,
    pairId,
    pairLabel: pair.label,
    points,
    spreadPoints,
    state,
    stateLabel: concentrationStateLabel(state),
    summary: buildWeightSummary(pair.label, pair.weighted, pair.equal, spreadPoints, state),
    weightedPeriodReturn,
    weightedSeries,
    weightedSymbol: pair.weighted,
  };
}

export function getAvailableWeightPairs(histories: Partial<Record<string, HistoryData>>) {
  return (Object.keys(PAIRS) as WeightComparisonPairId[])
    .filter((pairId) => {
      const pair = PAIRS[pairId];
      return Boolean(histories[pair.weighted]?.candles?.length && histories[pair.equal]?.candles?.length);
    });
}

export function classifyConcentrationState(
  spreadPoints: number | null,
  confidence: WeightComparisonViewModel['confidence'] = 'high',
): ConcentrationState {
  if (spreadPoints === null || confidence === 'unavailable') {
    return 'unavailable';
  }
  if (confidence === 'low') {
    return 'mixed';
  }
  if (spreadPoints > 3) {
    return 'mega_cap_concentration';
  }
  if (spreadPoints >= 1) {
    return 'mild_concentration';
  }
  if (spreadPoints <= -1) {
    return 'equal_weight_leadership';
  }
  if (Math.abs(spreadPoints) < 0.5) {
    return 'broad_participation';
  }
  return 'mixed';
}

export function concentrationStateLabel(state: ConcentrationState) {
  switch (state) {
    case 'broad_participation':
      return 'Broad Participation';
    case 'mild_concentration':
      return 'Mild Concentration';
    case 'mega_cap_concentration':
      return 'Mega-Cap Concentration';
    case 'equal_weight_leadership':
      return 'Equal-Weight Leadership';
    case 'mixed':
      return 'Mixed';
    default:
      return 'Unavailable';
  }
}

export function buildConcentrationBreadthSignal(model: WeightComparisonViewModel | null) {
  if (!model || model.state === 'unavailable') {
    return null;
  }
  return {
    label: 'Equal-Weight Confirmation',
    state: model.state,
    status: model.stateLabel,
    summary: model.summary,
    value: model.spreadPoints,
  };
}

function alignWeightSeries(weighted: IndexChartPoint[], equalWeight: IndexChartPoint[]): WeightComparisonPoint[] {
  const equalByTime = new Map(equalWeight.map((point) => [point.timestamp, point]));
  return weighted
    .map((point) => {
      const equal = equalByTime.get(point.timestamp);
      return equal ? {
        dateLabel: point.dateLabel,
        equalWeightReturn: equal.value,
        spreadPoints: point.value - equal.value,
        timestamp: point.timestamp,
        weightedReturn: point.value,
      } : null;
    })
    .filter((point): point is WeightComparisonPoint => Boolean(point));
}

function classifyWeightConfidence(points: number, timeframe: IndexTimeframe): WeightComparisonViewModel['confidence'] {
  const required = timeframe === '1D' ? 2 : timeframe === '1W' ? 4 : timeframe === '1M' ? 14 : timeframe === '6M' ? 70 : 140;
  if (points < 2) {
    return 'unavailable';
  }
  if (points >= required) {
    return 'high';
  }
  if (points >= Math.ceil(required * 0.55)) {
    return 'moderate';
  }
  return 'low';
}

function buildWeightSummary(
  label: string,
  weightedSymbol: string,
  equalSymbol: string,
  spreadPoints: number | null,
  state: ConcentrationState,
) {
  if (spreadPoints === null || state === 'unavailable') {
    return `${label} weighted versus equal-weight history is unavailable.`;
  }
  if (state === 'mega_cap_concentration' || state === 'mild_concentration') {
    return `${weightedSymbol} is outperforming ${equalSymbol}, suggesting the largest companies are contributing more heavily to the advance.`;
  }
  if (state === 'equal_weight_leadership') {
    return `${equalSymbol} is outperforming ${weightedSymbol}, suggesting broader participation beyond the largest constituents.`;
  }
  if (state === 'broad_participation') {
    return `${weightedSymbol} and ${equalSymbol} are moving together, consistent with broad participation.`;
  }
  return `${weightedSymbol} and ${equalSymbol} show a modest spread without a dominant concentration signal.`;
}
