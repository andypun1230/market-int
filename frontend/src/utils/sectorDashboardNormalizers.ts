import type {
  PerformanceIntervals,
  RotationIntervalData,
  RotationPoint,
  RotationQuadrant,
  SectorDashboardItem,
  SectorDashboardResponse,
} from '@/types/market';

type UnknownRecord = Record<string, unknown>;

export type HeatmapInterval = '1D' | '1W' | '1M' | '3M' | '6M' | '1Y';
export type RotationInterval = '1W' | '1M' | '3M';

export const HEATMAP_INTERVALS: HeatmapInterval[] = ['1D', '1W', '1M', '3M', '6M', '1Y'];
export const ROTATION_INTERVALS: RotationInterval[] = ['1W', '1M', '3M'];

export function normalizeSectorDashboardResponse(raw: unknown): SectorDashboardResponse {
  const payload = firstRecord(
    getPath(raw, ['data']),
    getPath(raw, ['payload']),
    getPath(raw, ['result']),
    getPath(raw, ['market']),
    raw,
  );
  const sectors = firstArray(
    getPath(payload, ['sectors']),
    getPath(payload, ['sector_performance']),
    getPath(payload, ['sectorPerformance']),
  ).map((item) => normalizeDashboardItem(item, 'sector')).filter(isSectorDashboardItem);
  const themes = firstArray(
    getPath(payload, ['themes']),
    getPath(payload, ['theme_performance']),
    getPath(payload, ['themePerformance']),
    getPath(payload, ['industry_groups']),
    getPath(payload, ['industryGroups']),
  ).map((item) => normalizeDashboardItem(item, 'theme')).filter(isSectorDashboardItem);

  const normalized = {
    as_of: primitiveToText(getByKeys(payload, ['as_of', 'asOf'])),
    benchmark: primitiveToText(getByKeys(payload, ['benchmark'])) ?? 'SPY',
    cache_status: primitiveToText(getByKeys(payload, ['cache_status', 'cacheStatus'])),
    partial: Boolean(getByKeys(payload, ['partial']) ?? false),
    snapshot_id: primitiveToText(getByKeys(payload, ['snapshot_id', 'snapshotId'])),
    universe_version: primitiveToText(getByKeys(payload, ['universe_version', 'universeVersion'])),
    market_date: primitiveToText(getByKeys(payload, ['market_date', 'marketDate'])),
    coverage: firstRecord(getByKeys(payload, ['coverage'])),
    refreshing: Boolean(getByKeys(payload, ['refreshing']) ?? false),
    sectors,
    source: primitiveToText(getByKeys(payload, ['source', 'overall_mode', 'overallMode'])) ?? 'partial',
    status: primitiveToText(getByKeys(payload, ['status'])) ?? 'success',
    summary: primitiveToText(getByKeys(payload, ['summary'])),
    theme_legacy_source: primitiveToText(getByKeys(payload, ['theme_legacy_source', 'themeLegacySource'])),
    themes,
  } satisfies SectorDashboardResponse;

  logSectorNormalizer('dashboard', normalized, {
    benchmark: normalized.benchmark,
    sectors: sectors.length,
    source: normalized.source,
    themes: themes.length,
  });
  return normalized;
}

export function getHeatmapValue(item: SectorDashboardItem, interval: HeatmapInterval): number | null {
  switch (interval) {
    case '1D':
      return item.returns.oneDay;
    case '1W':
      return item.returns.oneWeek;
    case '1M':
      return item.returns.oneMonth;
    case '3M':
      return item.returns.threeMonths;
    case '6M':
      return item.returns.sixMonths;
    case '1Y':
      return item.returns.oneYear;
    default:
      return null;
  }
}

export function getRotationData(item: SectorDashboardItem, interval: RotationInterval): RotationIntervalData | null {
  switch (interval) {
    case '1W':
      return item.rotation.oneWeek ?? null;
    case '1M':
      return item.rotation.oneMonth ?? null;
    case '3M':
      return item.rotation.threeMonths ?? null;
    default:
      return null;
  }
}

function normalizeDashboardItem(value: unknown, kind: 'sector' | 'theme'): SectorDashboardItem | null {
  if (!isRecord(value)) {
    return null;
  }
  const name = primitiveToText(getByKeys(value, ['name', 'sector', 'theme']));
  if (!name) {
    return null;
  }
  return {
    id: primitiveToText(getByKeys(value, ['id'])) ?? slugify(name),
    metadata: firstRecord(value.metadata) ?? {
      as_of: primitiveToText(getByKeys(value, ['as_of', 'asOf'])),
      coverage_percent: extractNumber(getByKeys(value, ['coverage_percent', 'coveragePercent'])),
      fallback_used: Boolean(getByKeys(value, ['fallback_used', 'fallbackUsed']) ?? false),
      history_quality_score: extractNumber(getByKeys(value, ['history_quality_score', 'historyQualityScore'])),
      status: primitiveToText(getByKeys(value, ['status'])),
      successful_symbols: extractNumber(getByKeys(value, ['successful_symbols', 'successfulSymbols'])),
    },
    name,
    parentSector: primitiveToText(getByKeys(value, ['parent_sector', 'parentSector'])),
    returns: normalizeReturns(firstRecord(value.returns) ?? value),
    rotation: normalizeRotation(value.rotation, value),
    source: primitiveToText(getByKeys(value, ['source', 'overall_mode', 'overallMode', 'data_source', 'dataSource'])) ?? (kind === 'theme' ? 'partial' : 'partial'),
    symbol: primitiveToText(getByKeys(value, ['symbol', 'etf_symbol', 'etfSymbol'])),
  };
}

function normalizeReturns(value: UnknownRecord): PerformanceIntervals {
  return {
    oneDay: extractNumber(getByKeys(value, ['1d', 'oneDay', 'return_1d', 'return1d', 'daily_change_percent'])),
    oneWeek: extractNumber(getByKeys(value, ['1w', 'oneWeek', 'return_1w', 'return1w', 'weekly_change_percent'])),
    oneMonth: extractNumber(getByKeys(value, ['1m', 'oneMonth', 'return_1m', 'return1m', 'return_mtd', 'monthly_change_percent'])),
    threeMonths: extractNumber(getByKeys(value, ['3m', 'threeMonths', 'return_3m', 'return3m'])),
    sixMonths: extractNumber(getByKeys(value, ['6m', 'sixMonths', 'return_6m', 'return6m'])),
    oneYear: extractNumber(getByKeys(value, ['1y', 'oneYear', 'return_1y', 'return1y', 'return_ytd'])),
  };
}

function normalizeRotation(rotation: unknown, fallback: UnknownRecord): SectorDashboardItem['rotation'] {
  const source = firstRecord(rotation);
  return {
    oneMonth: normalizeRotationInterval(firstRecord(getByKeys(source, ['1m', 'oneMonth'])) ?? fallback),
    oneWeek: normalizeRotationInterval(firstRecord(getByKeys(source, ['1w', 'oneWeek'])) ?? fallback),
    threeMonths: normalizeRotationInterval(firstRecord(getByKeys(source, ['3m', 'threeMonths'])) ?? fallback),
  };
}

function normalizeRotationInterval(value: UnknownRecord): RotationIntervalData | null {
  const relativeStrength = extractNumber(getByKeys(value, ['relative_strength', 'relativeStrength', 'rs']));
  const relativeMomentum = extractNumber(getByKeys(value, ['relative_momentum', 'relativeMomentum', 'momentum']));
  if (relativeStrength === null || relativeMomentum === null) {
    return null;
  }
  return {
    history: firstArray(value.history).map(normalizeRotationPoint).filter(isRotationPoint),
    quadrant: normalizeQuadrant(getByKeys(value, ['quadrant']), relativeStrength, relativeMomentum),
    relativeMomentum,
    relativeStrength,
  };
}

function normalizeRotationPoint(value: unknown): RotationPoint | null {
  if (!isRecord(value)) {
    return null;
  }
  const relativeStrength = extractNumber(getByKeys(value, ['relative_strength', 'relativeStrength']));
  const relativeMomentum = extractNumber(getByKeys(value, ['relative_momentum', 'relativeMomentum']));
  if (relativeStrength === null || relativeMomentum === null) {
    return null;
  }
  return {
    date: primitiveToText(value.date),
    relativeMomentum,
    relativeStrength,
  };
}

function normalizeQuadrant(value: unknown, relativeStrength: number, relativeMomentum: number): RotationQuadrant {
  const text = primitiveToText(value)?.toLowerCase();
  if (text === 'leading' || text === 'weakening' || text === 'lagging' || text === 'improving') {
    return text;
  }
  if (relativeStrength >= 100 && relativeMomentum >= 100) {
    return 'leading';
  }
  if (relativeStrength >= 100) {
    return 'weakening';
  }
  if (relativeMomentum >= 100) {
    return 'improving';
  }
  return 'lagging';
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

function isRecord(value: unknown): value is UnknownRecord {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function isSectorDashboardItem(value: SectorDashboardItem | null): value is SectorDashboardItem {
  return value !== null;
}

function isRotationPoint(value: RotationPoint | null): value is RotationPoint {
  return value !== null;
}

function extractNumber(value: unknown): number | null {
  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : null;
  }
  if (typeof value === 'string') {
    const parsed = Number(value.replace(/[%,$,]/g, '').trim());
    return Number.isFinite(parsed) ? parsed : null;
  }
  if (isRecord(value)) {
    return extractNumber(value.value) ?? extractNumber(value.count) ?? extractNumber(value.percentage) ?? extractNumber(value.label);
  }
  return null;
}

function primitiveToText(value: unknown): string | undefined {
  if (typeof value === 'string') {
    return value;
  }
  if (typeof value === 'number') {
    return String(value);
  }
  return undefined;
}

function slugify(value: string): string {
  return value.toLowerCase().replace(/&/g, 'and').replace(/[ /]+/g, '-');
}

function logSectorNormalizer(label: string, normalized: unknown, meta: Record<string, unknown>) {
  if (process.env.EXPO_PUBLIC_SECTOR_DEBUG !== 'true') {
    return;
  }
  console.log(`[SECTOR TAB] ${label}`, meta, normalized);
}
