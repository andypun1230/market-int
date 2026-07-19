import type {
  DecisionDashboardResponse,
  InstitutionalActivityResponse,
  InstitutionalIntelligenceResponse,
  MarketBreadth,
  MarketBreadthResponse,
  SectorBreadthItem,
} from '@/types/market';

type UnknownRecord = Record<string, unknown>;

export function normalizeBreadthResponse(raw: unknown): MarketBreadthResponse | null {
  const payload = firstRecord(
    getPath(raw, ['breadth']),
    getPath(raw, ['marketBreadth']),
    getPath(raw, ['data', 'breadth']),
    getPath(raw, ['market', 'breadth']),
    getPath(raw, ['result', 'breadth']),
    getPath(raw, ['payload', 'breadth']),
    hasAnyKey(raw, ['market', 'sectors']) ? raw : null,
  );

  if (!payload) {
    logNormalizer('breadth', raw, null, ['No breadth payload found']);
    return null;
  }

  const marketPayload = firstRecord(
    payload.market,
    payload.breadth,
    payload.metrics,
    hasAnyKey(payload, ['total_stocks', 'totalStocks', 'advancing_stocks', 'advancing']) ? payload : null,
  );
  const sectorsPayload = firstArray(
    payload.sectors,
    payload.sectorBreadth,
    payload.sector_breadth,
    getPath(payload, ['market', 'sectors']),
  );

  if (!marketPayload) {
    logNormalizer('breadth', raw, null, ['No market breadth object found']);
    return null;
  }

  const reportedStatus = extractText(getByKeys(marketPayload, ['breadth_status', 'breadthStatus', 'status']), '').toLowerCase();
  const reportedSnapshotId = primitiveToText(getByKeys(marketPayload, ['snapshot_id', 'snapshotId']));
  if (reportedStatus === 'unavailable' && !reportedSnapshotId) {
    logNormalizer('breadth', raw, null, ['Unavailable embedded breadth has no published snapshot']);
    return null;
  }

  const market = normalizeMarketBreadth(marketPayload);
  const sectors = sectorsPayload
    .map(normalizeSectorBreadthItem)
    .filter((item): item is SectorBreadthItem => item !== null);
  const normalized = { market, sectors };

  logNormalizer('breadth', raw, normalized);
  return normalized;
}

export function normalizeDecisionIntelligenceResponse(raw: unknown): DecisionDashboardResponse | null {
  const payload = firstRecord(
    getPath(raw, ['decisionDashboard']),
    getPath(raw, ['decision_dashboard']),
    getPath(raw, ['decisionIntelligence']),
    getPath(raw, ['decision_intelligence']),
    getPath(raw, ['decision', 'dashboard']),
    getPath(raw, ['data', 'decisionDashboard']),
    getPath(raw, ['data', 'decision_dashboard']),
    getPath(raw, ['payload', 'decisionDashboard']),
    hasAnyKey(raw, ['playbook', 'aggressiveness', 'trading_styles']) ? raw : null,
  );

  if (!payload) {
    logNormalizer('decision intelligence', raw, null, ['No decision dashboard payload found']);
    return null;
  }

  logNormalizer('decision intelligence', raw, payload);
  return payload as unknown as DecisionDashboardResponse;
}

export function normalizeInstitutionalActivityResponse(raw: unknown): InstitutionalActivityResponse | null {
  const payload = firstRecord(
    getPath(raw, ['institutionalActivity']),
    getPath(raw, ['institutional_activity']),
    getPath(raw, ['activity']),
    getPath(raw, ['data', 'institutionalActivity']),
    getPath(raw, ['data', 'institutional_activity']),
    hasAnyKey(raw, ['bias', 'indexes']) ? raw : null,
  );

  if (!payload) {
    logNormalizer('institutional activity', raw, null, ['No institutional activity payload found']);
    return null;
  }

  const biasPayload = firstRecord(payload.bias, payload.institutional_bias, payload.institutionalBias, payload);
  const bias = {
    bias: extractText(getByKeys(biasPayload, ['bias', 'institutional_bias', 'institutionalBias', 'status']), 'N/A'),
    summary: extractText(getByKeys(biasPayload, ['summary', 'description', 'overview']), 'Institutional activity unavailable.'),
    distribution_count: extractNumber(getByKeys(biasPayload, ['distribution_count', 'distribution_days', 'distribution', 'distributionCount'])) ?? 0,
    accumulation_count: extractNumber(getByKeys(biasPayload, ['accumulation_count', 'accumulation_days', 'accumulation', 'accumulationCount'])) ?? 0,
    stall_count: extractNumber(getByKeys(biasPayload, ['stall_count', 'stall_days', 'stall', 'stallCount'])) ?? 0,
    churning_count: extractNumber(getByKeys(biasPayload, ['churning_count', 'churning_days', 'churning', 'churningCount'])) ?? 0,
    follow_through_day: normalizeFollowThroughDay(
      getByKeys(biasPayload, ['follow_through_day', 'followThroughDay', 'follow_through', 'followThrough']),
    ),
  };

  const indexesPayload = firstArray(payload.indexes, payload.indices);
  const normalized = { bias, indexes: indexesPayload as InstitutionalActivityResponse['indexes'] };

  logNormalizer('institutional activity', raw, normalized);
  return normalized;
}

export function normalizeInstitutionalIntelligenceResponse(raw: unknown): InstitutionalIntelligenceResponse | null {
  const payload = firstRecord(
    getPath(raw, ['institutional_intelligence']),
    getPath(raw, ['institutionalIntelligence']),
    getPath(raw, ['intelligence', 'institutional']),
    getPath(raw, ['data', 'institutional_intelligence']),
    getPath(raw, ['data', 'institutionalIntelligence']),
    hasAnyKey(raw, ['sentiment', 'moneyFlow', 'money_flow', 'institutional', 'options', 'liquidity']) ? raw : null,
  );

  if (!payload) {
    logNormalizer('institutional intelligence', raw, null, ['No institutional intelligence payload found']);
    return null;
  }

  const sentiment = firstRecord(payload.sentiment, payload.market_sentiment);
  const moneyFlow = firstRecord(payload.money_flow, payload.moneyFlow);
  const institutional = firstRecord(payload.institutional, payload.institutional_dashboard);
  const options = firstRecord(payload.options, payload.options_intelligence);
  const liquidity = firstRecord(payload.liquidity, payload.liquidity_dashboard);

  if (!sentiment || !moneyFlow || !institutional || !options || !liquidity) {
    logNormalizer('institutional intelligence', raw, null, ['Missing one or more institutional sub-dashboards']);
    return null;
  }

  const normalized = {
    sentiment,
    money_flow: moneyFlow,
    institutional,
    options,
    liquidity,
    summary: extractText(payload.summary, 'Institutional intelligence details loaded on demand.'),
  } as unknown as InstitutionalIntelligenceResponse;

  logNormalizer('institutional intelligence', raw, normalized);
  return normalized;
}

export function extractNumber(value: unknown): number | null {
  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : null;
  }
  if (typeof value === 'string') {
    const normalized = value.replace(/[%,$,]/g, '').trim();
    if (!normalized) {
      return null;
    }
    const parsed = Number(normalized);
    return Number.isFinite(parsed) ? parsed : null;
  }
  if (isRecord(value)) {
    return (
      extractNumber(value.value) ??
      extractNumber(value.count) ??
      extractNumber(value.percentage) ??
      extractNumber(value.percent) ??
      extractNumber(value.label)
    );
  }
  return null;
}

export function extractText(value: unknown, fallback = 'N/A'): string {
  if (typeof value === 'string') {
    return value;
  }
  if (typeof value === 'number') {
    return String(value);
  }
  if (typeof value === 'boolean') {
    return value ? 'Yes' : 'No';
  }
  if (isRecord(value)) {
    return (
      primitiveToText(value.label) ??
      primitiveToText(value.status) ??
      primitiveToText(value.text) ??
      primitiveToText(value.value) ??
      primitiveToText(value.description) ??
      fallback
    );
  }
  return fallback;
}

function normalizeMarketBreadth(payload: UnknownRecord): MarketBreadth {
  const advancing = extractNumber(getByKeys(payload, ['advancing_stocks', 'advancingStocks', 'advancing']));
  const declining = extractNumber(getByKeys(payload, ['declining_stocks', 'decliningStocks', 'declining']));
  const total = extractNumber(getByKeys(payload, ['total_stocks', 'totalStocks', 'total', 'count', 'universe_size', 'universeSize']));
  const unchanged = extractNumber(getByKeys(payload, ['unchanged_stocks', 'unchangedStocks', 'unchanged']));
  const adRatio =
    extractNumber(getByKeys(payload, ['advance_decline_ratio', 'advanceDeclineRatio', 'ad_ratio', 'adRatio'])) ??
    deriveAdvanceDeclineRatio(advancing, declining);

  return {
    total_stocks: total ?? 0,
    advancing_stocks: advancing ?? 0,
    declining_stocks: declining ?? 0,
    unchanged_stocks: unchanged ?? 0,
    advance_decline_ratio: adRatio,
    advance_decline_ratio_display: primitiveToText(getByKeys(payload, ['advance_decline_ratio_display', 'advanceDeclineRatioDisplay'])),
    advance_decline_ratio_smoothed: extractNumber(getByKeys(payload, ['advance_decline_ratio_smoothed', 'advanceDeclineRatioSmoothed'])),
    ratio_method: primitiveToText(getByKeys(payload, ['ratio_method', 'ratioMethod'])),
    percent_above_20ema: extractNumber(getByKeys(payload, ['percent_above_20ema', 'percentAbove20Ema', 'above_20ema', 'above20ema'])) ?? 0,
    percent_above_50ema: extractNumber(getByKeys(payload, ['percent_above_50ema', 'percentAbove50Ema', 'above_50ema', 'above50ema'])) ?? 0,
    percent_above_200ema: extractNumber(getByKeys(payload, ['percent_above_200ema', 'percentAbove200Ema', 'above_200ema', 'above200ema'])) ?? 0,
    new_52w_highs: extractNumber(getByKeys(payload, ['new_52w_highs', 'new52WeekHighs', 'new_highs', 'newHighs'])) ?? 0,
    new_52w_lows: extractNumber(getByKeys(payload, ['new_52w_lows', 'new52WeekLows', 'new_lows', 'newLows'])) ?? 0,
    breadth_score: extractNumber(getByKeys(payload, ['breadth_score', 'breadthScore', 'score'])),
    breadth_status: extractText(getByKeys(payload, ['breadth_status', 'breadthStatus', 'status']), 'N/A'),
    snapshot_id: primitiveToText(getByKeys(payload, ['snapshot_id', 'snapshotId'])),
    universe_version: primitiveToText(getByKeys(payload, ['universe_version', 'universeVersion'])),
    market_date: primitiveToText(getByKeys(payload, ['market_date', 'marketDate'])),
    coverage_status: primitiveToText(getByKeys(payload, ['coverage_status', 'coverageStatus'])),
    trend: primitiveToText(getByKeys(payload, ['trend'])),
    confidence: primitiveToText(getByKeys(payload, ['confidence'])),
    source_state: primitiveToText(getByKeys(payload, ['source_state', 'sourceState'])),
    coverage_dimensions: normalizeCoverageDimensions(getByKeys(payload, ['coverage_dimensions', 'coverageDimensions'])),
    data_confidence: normalizeConfidence(getByKeys(payload, ['data_confidence', 'dataConfidence'])),
    signal_confidence: normalizeConfidence(getByKeys(payload, ['signal_confidence', 'signalConfidence'])),
    coverage_percent: extractNumber(getByKeys(payload, ['coverage_percent', 'coveragePercent', 'coverage'])),
    overall_mode: extractText(getByKeys(payload, ['overall_mode', 'overallMode', 'mode', 'breadthMode']), 'mock'),
    universe: primitiveToText(getByKeys(payload, ['universe', 'breadth_universe', 'breadthUniverse'])),
    universe_size: extractNumber(getByKeys(payload, ['universe_size', 'universeSize'])),
    successful_symbols: extractNumber(getByKeys(payload, ['successful_symbols', 'successfulSymbols'])),
    data_source: primitiveToText(getByKeys(payload, ['data_source', 'dataSource', 'source'])),
    as_of: primitiveToText(getByKeys(payload, ['as_of', 'asOf'])),
    fallback_used: Boolean(getByKeys(payload, ['fallback_used', 'fallbackUsed']) ?? false),
    history_quality_score: extractNumber(getByKeys(payload, ['history_quality_score', 'historyQualityScore'])),
  };
}

function normalizeSectorBreadthItem(value: unknown): SectorBreadthItem | null {
  if (!isRecord(value)) {
    return null;
  }
  const sector = extractText(getByKeys(value, ['sector', 'name']), '');
  if (!sector) {
    return null;
  }
  return {
    sector,
    total_stocks: extractNumber(getByKeys(value, ['total_stocks', 'totalStocks', 'total', 'count'])) ?? 0,
    advancing_stocks: extractNumber(getByKeys(value, ['advancing_stocks', 'advancingStocks', 'advancing'])) ?? 0,
    declining_stocks: extractNumber(getByKeys(value, ['declining_stocks', 'decliningStocks', 'declining'])) ?? 0,
    percent_above_50ema: extractNumber(getByKeys(value, ['percent_above_50ema', 'percentAbove50Ema', 'above_50ema', 'above50ema'])) ?? 0,
    overall_mode: extractText(getByKeys(value, ['overall_mode', 'overallMode', 'mode']), 'mock'),
    coverage_percent: extractNumber(getByKeys(value, ['coverage_percent', 'coveragePercent', 'coverage'])),
    successful_symbols: extractNumber(getByKeys(value, ['successful_symbols', 'successfulSymbols'])),
    universe_size: extractNumber(getByKeys(value, ['universe_size', 'universeSize'])),
    as_of: primitiveToText(getByKeys(value, ['as_of', 'asOf'])),
    history_quality_score: extractNumber(getByKeys(value, ['history_quality_score', 'historyQualityScore'])),
  };
}

function normalizeFollowThroughDay(value: unknown) {
  if (!isRecord(value)) {
    return {
      date: null,
      gain_percent: null,
      index: null,
      triggered: false,
    };
  }
  return {
    triggered: Boolean(getByKeys(value, ['triggered', 'is_triggered', 'isTriggered']) ?? false),
    date: primitiveToText(getByKeys(value, ['date'])) ?? null,
    index: primitiveToText(getByKeys(value, ['index', 'symbol'])) ?? null,
    gain_percent: extractNumber(getByKeys(value, ['gain_percent', 'gainPercent', 'gain'])),
  };
}

function deriveAdvanceDeclineRatio(advancing: number | null, declining: number | null): number | null {
  if (advancing === null || declining === null) {
    return null;
  }
  if (declining === 0) {
    return null;
  }
  return Number((advancing / declining).toFixed(2));
}

function normalizeCoverageDimensions(value: unknown): NonNullable<MarketBreadth['coverage_dimensions']> | null {
  if (!isRecord(value)) {
    return null;
  }
  const dimensions = Object.entries(value).reduce<NonNullable<MarketBreadth['coverage_dimensions']>>((result, [key, item]) => {
    if (!isRecord(item)) {
      return result;
    }
    const eligible = extractNumber(getByKeys(item, ['eligible']));
    const total = extractNumber(getByKeys(item, ['total']));
    const ratio = extractNumber(getByKeys(item, ['ratio']));
    const display = primitiveToText(getByKeys(item, ['display']))
      ?? (eligible !== null && total !== null ? `${eligible}/${total}` : undefined);
    if (eligible !== null || total !== null || ratio !== null || display) {
      result[key] = {
        eligible: eligible ?? undefined,
        total: total ?? undefined,
        ratio: ratio ?? undefined,
        display,
      };
    }
    return result;
  }, {});
  return Object.keys(dimensions).length ? dimensions : null;
}

function normalizeConfidence(value: unknown): NonNullable<MarketBreadth['data_confidence']> | null {
  if (!isRecord(value)) {
    return null;
  }
  const score = extractNumber(getByKeys(value, ['score']));
  const label = primitiveToText(getByKeys(value, ['label']));
  const reason = primitiveToText(getByKeys(value, ['reason']));
  const sourceSnapshotId = primitiveToText(getByKeys(value, ['source_snapshot_id', 'sourceSnapshotId']));
  const calculatedAt = primitiveToText(getByKeys(value, ['calculated_at', 'calculatedAt']));
  if (score === null && !label && !reason && !sourceSnapshotId && !calculatedAt) {
    return null;
  }
  return {
    score,
    label,
    reason,
    source_snapshot_id: sourceSnapshotId,
    calculated_at: calculatedAt,
  };
}

function getByKeys(record: UnknownRecord | null, keys: string[]): unknown {
  if (!record) {
    return undefined;
  }
  for (const key of keys) {
    if (Object.prototype.hasOwnProperty.call(record, key)) {
      return record[key];
    }
  }
  return undefined;
}

function getPath(value: unknown, path: string[]): unknown {
  let current = value;
  for (const key of path) {
    if (!isRecord(current)) {
      return undefined;
    }
    current = current[key];
  }
  return current;
}

function firstRecord(...values: unknown[]): UnknownRecord | null {
  for (const value of values) {
    if (isRecord(value)) {
      return value;
    }
  }
  return null;
}

function firstArray(...values: unknown[]): unknown[] {
  for (const value of values) {
    if (Array.isArray(value)) {
      return value;
    }
  }
  return [];
}

function hasAnyKey(value: unknown, keys: string[]): boolean {
  return isRecord(value) && keys.some((key) => Object.prototype.hasOwnProperty.call(value, key));
}

function isRecord(value: unknown): value is UnknownRecord {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function primitiveToText(value: unknown): string | undefined {
  if (typeof value === 'string') {
    return value;
  }
  if (typeof value === 'number') {
    return String(value);
  }
  if (typeof value === 'boolean') {
    return value ? 'Yes' : 'No';
  }
  return undefined;
}

function logNormalizer(name: string, raw: unknown, normalized: unknown, warnings: string[] = []) {
  if (process.env.EXPO_PUBLIC_MARKET_DATA_DEBUG !== 'true') {
    return;
  }
  const keys = isRecord(raw) ? Object.keys(raw) : [];
  console.log(`[MARKET DATA] ${name} raw keys:`, keys);
  if (warnings.length) {
    console.log(`[MARKET DATA] ${name} warnings:`, warnings);
  }
  console.log(`[MARKET DATA] ${name} normalized:`, normalized);
}
