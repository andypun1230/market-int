import type {
  DetectedPattern,
  MultiTimeframeItem,
  MultiTimeframeTechnicalSignals,
  RelativeStrengthItem,
  RiskPlan,
  StockAnalysisAggregate,
  HistoryData,
  StockLeadershipSignal,
  StockRatingItem,
  SupportResistanceResponse,
  TimeframeSignalDataStatus,
  TimeframeSignalEvidence,
  TimeframeSignalInput,
  TimeframeSignalName,
  TimeframeSignalStrength,
  TimeframeTechnicalSignal,
  LeadershipSignalName,
  TrendlineResponse,
  VolumeAnalysis,
} from '@/types/market';

export type StockAnalysisDetails = {
  leadershipSignal?: StockLeadershipSignal;
  multiTimeframe?: MultiTimeframeItem;
  multiTimeframeSignals?: MultiTimeframeTechnicalSignals;
  patterns?: DetectedPattern[];
  relativeStrength?: RelativeStrengthItem;
  riskPlan?: RiskPlan;
  stockRating?: StockRatingItem;
  supportResistance?: SupportResistanceResponse;
  trendline?: TrendlineResponse;
  volumeAnalysis?: VolumeAnalysis;
  chartHistory?: HistoryData;
  snapshotStatus?: string | null;
  snapshotRefreshing?: boolean;
  snapshotDataMode?: string | null;
  snapshotTestData?: boolean;
  snapshotMockData?: boolean;
};

type StockAnalysisAggregateWithLegacySignals = StockAnalysisAggregate & {
  data?: unknown;
  leadership_signal?: unknown;
  leadershipSignal?: unknown;
  multi_timeframe_signals?: unknown;
  multiTimeframeSignals?: unknown;
  result?: unknown;
};

export function normalizeStockAnalysisDetails(aggregate: StockAnalysisAggregateWithLegacySignals): StockAnalysisDetails {
  const multiTimeframeSignals = normalizeMultiTimeframeSignals(extractMultiTimeframeSignals(aggregate));
  const leadershipSignal = normalizeLeadershipSignal(extractLeadershipSignal(aggregate));
  return {
    leadershipSignal,
    supportResistance: aggregate.supportResistance ?? undefined,
    trendline: aggregate.trendline ?? undefined,
    volumeAnalysis: aggregate.volumeAnalysis ?? undefined,
    riskPlan: aggregate.riskPlan ?? undefined,
    multiTimeframe: aggregate.multiTimeframe ?? undefined,
    multiTimeframeSignals,
    patterns: aggregate.patterns?.patterns ?? undefined,
    relativeStrength: aggregate.relativeStrength ?? undefined,
    stockRating: aggregate.stockRating ?? undefined,
    chartHistory: isUnsafeSnapshotChart(aggregate) ? undefined : aggregate.chartHistory ?? aggregate.chart?.history ?? undefined,
    snapshotStatus: aggregate.snapshot_status ?? null,
    snapshotRefreshing: Boolean(aggregate.snapshot_refreshing || aggregate.snapshot_status === 'initializing'),
    snapshotDataMode: aggregate.snapshot_data_mode ?? null,
    snapshotTestData: Boolean(aggregate.snapshot_test_data),
    snapshotMockData: Boolean(aggregate.snapshot_mock_data),
  };
}

function isUnsafeSnapshotChart(aggregate: StockAnalysisAggregateWithLegacySignals): boolean {
  const mode = (aggregate.snapshot_data_mode ?? '').toLowerCase();
  return aggregate.snapshot_test_data === true || aggregate.snapshot_mock_data === true || mode === 'test' || mode === 'mock';
}

export function normalizeMultiTimeframeSignals(value: unknown): MultiTimeframeTechnicalSignals | undefined {
  const raw = asRecord(value);
  if (!raw) {
    return undefined;
  }

  const short = normalizeTimeframeSignal(read(raw, 'short'), 'short');
  const medium = normalizeTimeframeSignal(read(raw, 'medium'), 'medium');
  const long = normalizeTimeframeSignal(read(raw, 'long'), 'long');
  if (!short && !medium && !long) {
    return undefined;
  }

  return {
    generatedAt: readText(raw, 'generatedAt', 'generated_at') ?? null,
    long: long ?? buildUnavailableTimeframeSignal('long'),
    medium: medium ?? buildUnavailableTimeframeSignal('medium'),
    methodologyVersion: readText(raw, 'methodologyVersion', 'methodology_version') ?? 'unknown',
    overallDataStatus: normalizeDataStatus(read(raw, 'overallDataStatus', 'overall_data_status')) ?? 'partial',
    short: short ?? buildUnavailableTimeframeSignal('short'),
  };
}

function extractMultiTimeframeSignals(aggregate: StockAnalysisAggregateWithLegacySignals): unknown {
  const direct = aggregate.multiTimeframeSignals ?? aggregate.multi_timeframe_signals;
  if (direct != null) {
    return direct;
  }

  const data = asRecord(aggregate.data);
  const dataSignals = data ? read(data, 'multiTimeframeSignals', 'multi_timeframe_signals') : undefined;
  if (dataSignals != null) {
    return dataSignals;
  }

  const result = asRecord(aggregate.result);
  return result ? read(result, 'multiTimeframeSignals', 'multi_timeframe_signals') : undefined;
}

function extractLeadershipSignal(aggregate: StockAnalysisAggregateWithLegacySignals): unknown {
  const direct = aggregate.leadershipSignal ?? aggregate.leadership_signal;
  if (direct != null) {
    return direct;
  }

  const data = asRecord(aggregate.data);
  const dataLeadership = data ? read(data, 'leadershipSignal', 'leadership_signal') : undefined;
  if (dataLeadership != null) {
    return dataLeadership;
  }

  const result = asRecord(aggregate.result);
  return result ? read(result, 'leadershipSignal', 'leadership_signal') : undefined;
}

function normalizeLeadershipSignal(value: unknown): StockLeadershipSignal | undefined {
  const raw = asRecord(value);
  if (!raw) {
    return undefined;
  }
  const signal = normalizeLeadershipName(read(raw, 'signal'));
  return {
    asOf: readText(raw, 'asOf', 'as_of'),
    availableInputs: readNumber(raw, 'availableInputs', 'available_inputs') ?? 0,
    dataStatus: normalizeDataStatus(read(raw, 'dataStatus', 'data_status')) ?? 'unavailable',
    explanation: readText(raw, 'explanation') ?? 'Leadership signal is unavailable.',
    limitingEvidence: normalizeStringList(read(raw, 'limitingEvidence', 'limiting_evidence')),
    methodologyVersion: readText(raw, 'methodologyVersion', 'methodology_version') ?? 'unknown',
    positiveEvidence: normalizeStringList(read(raw, 'positiveEvidence', 'positive_evidence')),
    requiredInputs: readNumber(raw, 'requiredInputs', 'required_inputs') ?? 0,
    score: readNumber(raw, 'score'),
    signal,
    strength: normalizeStrength(read(raw, 'strength'), signal === 'unavailable' ? 'unavailable' : 'neutral'),
  };
}

function normalizeTimeframeSignal(value: unknown, fallbackTimeframe: 'short' | 'medium' | 'long'): TimeframeTechnicalSignal | undefined {
  const raw = asRecord(value);
  if (!raw) {
    return undefined;
  }

  const signal = normalizeSignalName(read(raw, 'signal'));
  const score = readNumber(raw, 'score');
  return {
    asOf: readText(raw, 'asOf', 'as_of') ?? null,
    availableInputs: readNumber(raw, 'availableInputs', 'available_inputs') ?? 0,
    dataStatus: normalizeKnownDataStatus(read(raw, 'dataStatus', 'data_status')),
    explanation: readText(raw, 'explanation') ?? (signal === 'unavailable' ? 'Not enough technical inputs are available for a reliable signal.' : ''),
    headline: readText(raw, 'headline') ?? `${displayTimeframeLabel(fallbackTimeframe)} signal`,
    horizonLabel: readText(raw, 'horizonLabel', 'horizon_label') ?? defaultHorizonLabel(fallbackTimeframe),
    inputs: normalizeInputs(read(raw, 'inputs')),
    negativeEvidence: normalizeEvidence(read(raw, 'negativeEvidence', 'negative_evidence')),
    positiveEvidence: normalizeEvidence(read(raw, 'positiveEvidence', 'positive_evidence')),
    requiredInputs: readNumber(raw, 'requiredInputs', 'required_inputs') ?? 0,
    score,
    signal,
    strength: normalizeStrength(read(raw, 'strength'), signal),
    timeframe: normalizeTimeframe(read(raw, 'timeframe')) ?? fallbackTimeframe,
  };
}

function buildUnavailableTimeframeSignal(timeframe: 'short' | 'medium' | 'long'): TimeframeTechnicalSignal {
  return {
    asOf: null,
    availableInputs: 0,
    dataStatus: 'unavailable',
    explanation: 'Not enough technical inputs are available for a reliable signal.',
    headline: `${displayTimeframeLabel(timeframe)} signal unavailable.`,
    horizonLabel: defaultHorizonLabel(timeframe),
    inputs: [],
    negativeEvidence: [],
    positiveEvidence: [],
    requiredInputs: 0,
    score: null,
    signal: 'unavailable',
    strength: 'unavailable',
    timeframe,
  };
}

function normalizeEvidence(value: unknown): TimeframeSignalEvidence[] {
  if (!Array.isArray(value)) {
    return [];
  }
  const items: TimeframeSignalEvidence[] = [];
  value.forEach((item, index) => {
    const raw = asRecord(item);
    if (!raw) {
      return;
    }
    items.push({
      key: readText(raw, 'key') ?? `evidence_${index}`,
      label: readText(raw, 'label') ?? 'Evidence',
      sourceStatus: normalizeDataStatus(read(raw, 'sourceStatus', 'source_status')) ?? null,
      value: normalizeMetricValue(read(raw, 'value')),
    });
  });
  return items;
}

function normalizeInputs(value: unknown): TimeframeSignalInput[] {
  if (!Array.isArray(value)) {
    return [];
  }
  const items: TimeframeSignalInput[] = [];
  value.forEach((item, index) => {
    const raw = asRecord(item);
    if (!raw) {
      return;
    }
    items.push({
      available: readBoolean(raw, 'available') ?? false,
      contribution: readNumber(raw, 'contribution'),
      key: readText(raw, 'key') ?? `input_${index}`,
      label: readText(raw, 'label') ?? 'Input',
      sourceStatus: normalizeDataStatus(read(raw, 'sourceStatus', 'source_status')) ?? 'unavailable',
      timeframe: normalizeTimeframe(read(raw, 'timeframe')) ?? 'short',
      value: normalizeMetricValue(read(raw, 'value')),
      weight: readNumber(raw, 'weight') ?? 0,
    });
  });
  return items;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value != null && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null;
}

function read(record: Record<string, unknown>, ...keys: string[]): unknown {
  for (const key of keys) {
    if (Object.prototype.hasOwnProperty.call(record, key)) {
      return record[key];
    }
  }
  return undefined;
}

function readText(record: Record<string, unknown>, ...keys: string[]): string | null {
  const value = read(record, ...keys);
  if (typeof value === 'string') {
    return value;
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  return null;
}

function readNumber(record: Record<string, unknown>, ...keys: string[]): number | null {
  const value = read(record, ...keys);
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function readBoolean(record: Record<string, unknown>, ...keys: string[]): boolean | null {
  const value = read(record, ...keys);
  if (typeof value === 'boolean') {
    return value;
  }
  if (typeof value === 'string') {
    const normalized = value.toLowerCase();
    if (normalized === 'true') {
      return true;
    }
    if (normalized === 'false') {
      return false;
    }
  }
  return null;
}

function normalizeMetricValue(value: unknown): string | number | boolean | null {
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return value;
  }
  return null;
}

function normalizeStringList(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item) => {
      if (typeof item === 'string') {
        return item;
      }
      if (typeof item === 'number' || typeof item === 'boolean') {
        return String(item);
      }
      return null;
    })
    .filter((item): item is string => item != null && item.trim() !== '');
}

function normalizeLeadershipName(value: unknown): LeadershipSignalName {
  const normalized = typeof value === 'string' ? value.toLowerCase() : '';
  if (
    normalized === 'leader' ||
    normalized === 'emerging_leader' ||
    normalized === 'follower' ||
    normalized === 'lagging' ||
    normalized === 'unavailable'
  ) {
    return normalized;
  }
  return 'unavailable';
}

function normalizeSignalName(value: unknown): TimeframeSignalName {
  const normalized = typeof value === 'string' ? value.toLowerCase() : '';
  if (
    normalized === 'strong_bearish' ||
    normalized === 'bearish' ||
    normalized === 'neutral' ||
    normalized === 'bullish' ||
    normalized === 'strong_bullish' ||
    normalized === 'unavailable'
  ) {
    return normalized;
  }
  return 'unavailable';
}

function normalizeStrength(value: unknown, signal: TimeframeSignalName): TimeframeSignalStrength {
  const normalized = typeof value === 'string' ? value.toLowerCase() : '';
  if (normalized === 'weak' || normalized === 'moderate' || normalized === 'strong' || normalized === 'unavailable') {
    return normalized;
  }
  return signal === 'unavailable' ? 'unavailable' : 'moderate';
}

function normalizeDataStatus(value: unknown): TimeframeSignalDataStatus | string | null {
  if (typeof value !== 'string' || value.trim() === '') {
    return null;
  }
  const normalized = value.toLowerCase();
  if (
    normalized === 'live' ||
    normalized === 'test' ||
    normalized === 'cached' ||
    normalized === 'stale' ||
    normalized === 'fallback' ||
    normalized === 'mixed' ||
    normalized === 'partial' ||
    normalized === 'mock' ||
    normalized === 'unavailable'
  ) {
    return normalized;
  }
  return normalized;
}

function normalizeKnownDataStatus(value: unknown): TimeframeSignalDataStatus {
  const normalized = normalizeDataStatus(value);
  if (
    normalized === 'live' ||
    normalized === 'test' ||
    normalized === 'cached' ||
    normalized === 'stale' ||
    normalized === 'fallback' ||
    normalized === 'mixed' ||
    normalized === 'partial' ||
    normalized === 'mock' ||
    normalized === 'unavailable'
  ) {
    return normalized;
  }
  return 'unavailable';
}

function normalizeTimeframe(value: unknown): 'short' | 'medium' | 'long' | null {
  const normalized = typeof value === 'string' ? value.toLowerCase() : '';
  if (normalized === 'short' || normalized === 'medium' || normalized === 'long') {
    return normalized;
  }
  return null;
}

function displayTimeframeLabel(timeframe: 'short' | 'medium' | 'long'): string {
  if (timeframe === 'short') {
    return 'Short-term';
  }
  if (timeframe === 'medium') {
    return 'Medium-term';
  }
  return 'Long-term';
}

function defaultHorizonLabel(timeframe: 'short' | 'medium' | 'long'): string {
  if (timeframe === 'short') {
    return '1-10 trading days';
  }
  if (timeframe === 'medium') {
    return '2-8 weeks';
  }
  return '3-12 months';
}
