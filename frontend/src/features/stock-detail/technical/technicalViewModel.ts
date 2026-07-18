import type {
  DetectedPattern,
  SupportResistanceResponse,
  TrendlineResponse,
  VolumeAnalysis,
  WatchlistItem,
} from '@/types/market';
import type { CurrentPriceSelection } from '@/features/stock-detail/currentPrice';

export type TechnicalSourceStatus =
  | 'live'
  | 'test'
  | 'historical'
  | 'cached'
  | 'stale'
  | 'fallback'
  | 'mock'
  | 'unavailable';

export type PatternTrustState =
  | 'live_compatible'
  | 'historical_compatible'
  | 'historical_incompatible'
  | 'cached_compatible'
  | 'stale'
  | 'fallback'
  | 'mock'
  | 'unavailable';

export type PatternTrustAssessment = {
  explanation: string | null;
  isCompatibleWithCurrentLevels: boolean;
  isCurrent: boolean;
  shouldLeadTechnicalTab: boolean;
  shouldShowScoreProminently: boolean;
  shouldShowTradeLevels: boolean;
  state: PatternTrustState;
  userLabel: string;
};

export type TechnicalChecklistStatus = 'met' | 'pending' | 'watch' | 'failed' | 'unavailable';
export type TechnicalInvalidationStatus = 'active' | 'watch' | 'triggered' | 'unavailable';
export type TechnicalStance = 'bullish' | 'constructive' | 'neutral' | 'weakening' | 'bearish' | 'unavailable';

export type TechnicalDataProvenance = {
  detailedMismatchReason?: string | null;
  historyStatus: TechnicalSourceStatus;
  lastUpdated?: string | null;
  levelsStatus: TechnicalSourceStatus;
  mismatchReason?: string | null;
  patternStatus: TechnicalSourceStatus;
  quoteStatus: TechnicalSourceStatus;
  sourcesCompatible: boolean;
};

export type TechnicalChecklistItem = {
  explanation?: string | null;
  key: string;
  label: string;
  status: TechnicalChecklistStatus;
};

export type TechnicalInvalidationItem = {
  explanation?: string | null;
  key: string;
  label: string;
  status: TechnicalInvalidationStatus;
};

export type TechnicalPriceLevel = {
  key: string;
  kinds?: TechnicalPriceLevel['kind'][];
  kind: 'resistance' | 'confirmation' | 'current' | 'support' | 'invalidation' | 'ema';
  label: string;
  sourceStatus: TechnicalSourceStatus;
  value: number;
  zoneHigh?: number | null;
  zoneLow?: number | null;
};

export type StockTechnicalViewModel = {
  confirmations: TechnicalChecklistItem[];
  invalidations: TechnicalInvalidationItem[];
  pattern: {
    detectedAt: string | null;
    description: string | null;
    direction: string | null;
    name: string | null;
    score: number | null;
    scoreLabel: string | null;
    sourceStatus: TechnicalSourceStatus;
    stage: string | null;
  };
  patternTrust: PatternTrustAssessment;
  priceLevels: TechnicalPriceLevel[];
  provenance: TechnicalDataProvenance;
  setup: {
    confirmationLevel: number | null;
    confirmationZoneHigh: number | null;
    confirmationZoneLow: number | null;
    invalidationLevel: number | null;
    primaryResistance: number | null;
    primarySupport: number | null;
    relativeVolume: number | null;
    trendState: string | null;
    volumeState: string | null;
  };
  summary: {
    body: string;
    headline: string;
    stance: TechnicalStance;
    subtitle: string;
  };
  symbol: string;
  trend: {
    distancePercent: number | null;
    explanation: string | null;
    fallingResistanceDetected: boolean | null;
    risingSupportDetected: boolean | null;
    supportStatus: string | null;
    touchCount: number | null;
  };
  volume: {
    explanation: string | null;
    quality: string | null;
    relativeVolume: number | null;
    signal: string | null;
  };
};

type BuildTechnicalInput = {
  currentPrice?: CurrentPriceSelection | null;
  pattern?: DetectedPattern | null;
  stock: WatchlistItem;
  supportResistance?: SupportResistanceResponse | null;
  trendline?: TrendlineResponse | null;
  volumeAnalysis?: VolumeAnalysis | null;
};

const MATERIAL_LEVEL_MISMATCH_PERCENT = 8;

export function buildStockTechnicalViewModel({
  currentPrice,
  pattern,
  stock,
  supportResistance,
  trendline,
  volumeAnalysis,
}: BuildTechnicalInput): StockTechnicalViewModel {
  const patternStatus = getPatternStatus(pattern);
  const levelsStatus = getSourceStatus(supportResistance);
  const quoteStatus = getQuoteStatus(stock, currentPrice);
  const detailedMismatchReason = getLevelMismatchReason(pattern, supportResistance);
  const sourcesCompatible = isSourceCompatible(patternStatus, levelsStatus) && !detailedMismatchReason;
  const patternTrust = assessPatternTrust(pattern, patternStatus, sourcesCompatible, detailedMismatchReason);
  const confirmationLevel = supportResistance?.breakout_level ?? null;
  const invalidationLevel = supportResistance?.stop_reference ?? null;
  const primarySupport = getPrimarySupport(supportResistance);
  const primaryResistance = getPrimaryResistance(supportResistance);
  const priceLevels = buildPriceLevels(stock, supportResistance, levelsStatus, currentPrice);
  const confirmations = buildConfirmations({ confirmationLevel, pattern: patternTrust.isCurrent ? pattern : null, primarySupport, trendline, volumeAnalysis });
  const invalidations = buildInvalidations({ invalidationLevel, trendline, volumeAnalysis });
  const stance = getTechnicalStance(pattern, trendline, volumeAnalysis, supportResistance);
  const score = toNumber(pattern?.confidence);

  return {
    confirmations,
    invalidations,
    pattern: {
      detectedAt: getPatternDate(pattern),
      description: sanitizeText(pattern?.description),
      direction: normalizeLabel(pattern?.direction),
      name: sanitizeText(pattern?.name),
      score,
      scoreLabel: score == null ? null : getScoreLabel(score),
      sourceStatus: patternStatus,
      stage: normalizeLabel(pattern?.status),
    },
    patternTrust,
    priceLevels,
    provenance: {
      detailedMismatchReason,
      historyStatus: patternStatus === 'mock' ? 'mock' : levelsStatus,
      lastUpdated: supportResistance?.as_of ?? trendline?.as_of ?? null,
      levelsStatus,
      mismatchReason: patternTrust.explanation,
      patternStatus,
      quoteStatus,
      sourcesCompatible,
    },
    setup: {
      confirmationLevel,
      confirmationZoneHigh: primaryResistance,
      confirmationZoneLow: confirmationLevel,
      invalidationLevel,
      primaryResistance,
      primarySupport,
      relativeVolume: toNumber(volumeAnalysis?.relative_volume),
      trendState: trendline?.rising_support?.status ?? null,
      volumeState: volumeAnalysis?.volume_quality ?? null,
    },
    summary: buildTechnicalSummary({
      confirmationLevel,
      invalidationLevel,
      pattern,
      patternStatus,
      patternTrust,
      primarySupport,
      sourcesCompatible,
      stance,
      trendline,
      volumeAnalysis,
    }),
    symbol: stock.ticker,
    trend: {
      distancePercent: toNumber(trendline?.rising_support?.distance_percent),
      explanation: buildTrendExplanation(trendline),
      fallingResistanceDetected: trendline?.falling_resistance?.detected ?? null,
      risingSupportDetected: trendline?.rising_support?.detected ?? null,
      supportStatus: trendline?.rising_support?.status ?? null,
      touchCount: toNumber(trendline?.rising_support?.touch_count),
    },
    volume: {
      explanation: buildVolumeExplanation(volumeAnalysis),
      quality: volumeAnalysis?.volume_quality ?? null,
      relativeVolume: toNumber(volumeAnalysis?.relative_volume),
      signal: volumeAnalysis?.signals?.[0] ?? volumeAnalysis?.status ?? null,
    },
  };
}

export function assessPatternTrust(
  pattern: DetectedPattern | null | undefined,
  patternStatus: TechnicalSourceStatus,
  sourcesCompatible: boolean,
  detailedMismatchReason?: string | null,
): PatternTrustAssessment {
  if (!pattern || patternStatus === 'unavailable') {
    return {
      explanation: null,
      isCompatibleWithCurrentLevels: false,
      isCurrent: false,
      shouldLeadTechnicalTab: false,
      shouldShowScoreProminently: false,
      shouldShowTradeLevels: false,
      state: 'unavailable',
      userLabel: 'Pattern unavailable',
    };
  }

  // Precedence is intentionally conservative: mock, stale, fallback, and mismatched
  // patterns never lead the current Technical tab even if they have high scores.
  if (patternStatus === 'mock') {
    return {
      explanation: 'This pattern comes from demo history and does not match the latest live price levels.',
      isCompatibleWithCurrentLevels: false,
      isCurrent: false,
      shouldLeadTechnicalTab: false,
      shouldShowScoreProminently: false,
      shouldShowTradeLevels: false,
      state: 'mock',
      userLabel: 'Mock pattern context',
    };
  }
  if (patternStatus === 'fallback') {
    return {
      explanation: 'This pattern comes from fallback history. Current confirmation, support, and invalidation levels are shown separately.',
      isCompatibleWithCurrentLevels: false,
      isCurrent: false,
      shouldLeadTechnicalTab: false,
      shouldShowScoreProminently: false,
      shouldShowTradeLevels: false,
      state: 'fallback',
      userLabel: 'Fallback pattern context',
    };
  }
  if (patternStatus === 'stale') {
    return {
      explanation: 'This pattern is stale. Current confirmation, support, and invalidation levels are shown below.',
      isCompatibleWithCurrentLevels: false,
      isCurrent: false,
      shouldLeadTechnicalTab: false,
      shouldShowScoreProminently: false,
      shouldShowTradeLevels: false,
      state: 'stale',
      userLabel: 'Stale pattern context',
    };
  }
  if (!sourcesCompatible || detailedMismatchReason) {
    return {
      explanation: 'Pattern data is from a different price period. Current confirmation, support, and invalidation levels are shown below.',
      isCompatibleWithCurrentLevels: false,
      isCurrent: false,
      shouldLeadTechnicalTab: false,
      shouldShowScoreProminently: false,
      shouldShowTradeLevels: false,
      state: patternStatus === 'historical' ? 'historical_incompatible' : 'historical_incompatible',
      userLabel: 'Historical pattern context',
    };
  }
  if (patternStatus === 'cached') {
    return {
      explanation: null,
      isCompatibleWithCurrentLevels: true,
      isCurrent: true,
      shouldLeadTechnicalTab: true,
      shouldShowScoreProminently: true,
      shouldShowTradeLevels: true,
      state: 'cached_compatible',
      userLabel: 'Cached pattern',
    };
  }
  if (patternStatus === 'historical') {
    return {
      explanation: 'This pattern is historical but remains compatible with current calculated levels.',
      isCompatibleWithCurrentLevels: true,
      isCurrent: false,
      shouldLeadTechnicalTab: false,
      shouldShowScoreProminently: false,
      shouldShowTradeLevels: false,
      state: 'historical_compatible',
      userLabel: 'Historical pattern context',
    };
  }
  return {
    explanation: null,
    isCompatibleWithCurrentLevels: true,
    isCurrent: true,
    shouldLeadTechnicalTab: true,
    shouldShowScoreProminently: true,
    shouldShowTradeLevels: true,
    state: 'live_compatible',
    userLabel: 'Current pattern',
  };
}

export function getLevelMismatchReason(
  pattern?: DetectedPattern | null,
  supportResistance?: SupportResistanceResponse | null,
): string | null {
  if (!pattern || !supportResistance) {
    return null;
  }
  const checks = [
    ['breakout', pattern.key_levels?.breakout, supportResistance.breakout_level],
    ['stop reference', pattern.key_levels?.stop_reference, supportResistance.stop_reference],
    ['support', pattern.key_levels?.support, getPrimarySupport(supportResistance)],
  ] as const;
  const mismatch = checks.find(([, patternValue, liveValue]) => hasMaterialMismatch(patternValue, liveValue));
  return mismatch
    ? `Pattern ${mismatch[0]} differs materially from current calculated levels.`
    : null;
}

export function buildPriceLevels(
  stock: WatchlistItem,
  supportResistance?: SupportResistanceResponse | null,
  status: TechnicalSourceStatus = 'unavailable',
  currentPrice?: CurrentPriceSelection | null,
): TechnicalPriceLevel[] {
  const levels: TechnicalPriceLevel[] = [];
  const resistance = getPrimaryResistance(supportResistance);
  const support = getPrimarySupport(supportResistance);
  addLevel(levels, 'resistance', 'Resistance', resistance, 'resistance', status);
  addLevel(levels, 'confirmation', 'Confirmation', supportResistance?.breakout_level, 'confirmation', status);
  const selectedPrice = currentPrice?.price ?? stock.price ?? supportResistance?.current_price;
  addLevel(levels, 'current', 'Current price', selectedPrice, 'current', getQuoteStatus(stock, currentPrice));
  addLevel(levels, 'support', 'Near support', support, 'support', status);
  addLevel(levels, 'invalidation', 'Invalidation', supportResistance?.stop_reference, 'invalidation', status);
  addLevel(levels, 'ema50', 'EMA50', supportResistance?.moving_average_support?.ema_50, 'ema', status);
  addLevel(levels, 'ema20', 'EMA20', supportResistance?.moving_average_support?.ema_20, 'ema', status);
  return mergeCloseLevels(levels, selectedPrice ?? null).sort((a, b) => b.value - a.value);
}

function buildTechnicalSummary({
  confirmationLevel,
  invalidationLevel,
  pattern,
  patternStatus,
  patternTrust,
  primarySupport,
  sourcesCompatible,
  stance,
  trendline,
  volumeAnalysis,
}: {
  confirmationLevel: number | null;
  invalidationLevel: number | null;
  pattern?: DetectedPattern | null;
  patternStatus: TechnicalSourceStatus;
  patternTrust: PatternTrustAssessment;
  primarySupport: number | null;
  sourcesCompatible: boolean;
  stance: TechnicalStance;
  trendline?: TrendlineResponse | null;
  volumeAnalysis?: VolumeAnalysis | null;
}): StockTechnicalViewModel['summary'] {
  const patternName = sanitizeText(pattern?.name);
  const patternStage = normalizeLabel(pattern?.status);
  const score = toNumber(pattern?.confidence);
  const headline = patternTrust.shouldLeadTechnicalTab && patternName
    ? `${patternName}${patternStage ? ` · ${patternStage}` : ''}`
    : confirmationLevel != null || invalidationLevel != null
      ? 'Current setup needs confirmation.'
      : trendline?.rising_support?.detected
        ? 'Trend structure is the primary signal.'
        : 'No reliable current pattern.';
  const subtitle = patternTrust.shouldLeadTechnicalTab && patternName && score != null
    ? `${normalizeLabel(pattern?.direction) ?? 'Technical'} structure · Pattern score ${Math.round(score)} / 100`
    : `${capitalize(stance)} technical view`;
  const confirmation = confirmationLevel != null
    ? `A move above ${formatCurrency(confirmationLevel)} would provide current confirmation.`
    : primarySupport != null
      ? `Holding above ${formatCurrency(primarySupport)} keeps the structure intact.`
      : 'Current confirmation levels are unavailable.';
  const invalidation = invalidationLevel != null
    ? `A close below ${formatCurrency(invalidationLevel)} would weaken the setup.`
    : volumeAnalysis?.volume_quality
      ? `${volumeAnalysis.volume_quality} volume is the main participation read.`
      : 'Volume and invalidation data are limited.';
  const patternSentence = patternName && patternTrust.shouldLeadTechnicalTab
    ? `${patternName} is ${patternStage?.toLowerCase() ?? 'developing'} with ${volumeAnalysis?.volume_quality?.toLowerCase() ?? 'available'} volume context.`
    : patternName
      ? `${patternName} is secondary context and is not used for current levels.`
      : `Current zones and trend structure drive this technical view.`;

  return {
    body: capWords(`${patternSentence} ${confirmation} ${invalidation}`, 62),
    headline,
    stance,
    subtitle,
  };
}

function buildConfirmations({
  confirmationLevel,
  pattern,
  primarySupport,
  trendline,
  volumeAnalysis,
}: {
  confirmationLevel: number | null;
  pattern?: DetectedPattern | null;
  primarySupport: number | null;
  trendline?: TrendlineResponse | null;
  volumeAnalysis?: VolumeAnalysis | null;
}): TechnicalChecklistItem[] {
  const items: TechnicalChecklistItem[] = [];
  if (trendline?.rising_support?.detected) {
    items.push({
      explanation: formatTouches(trendline.rising_support.touch_count),
      key: 'rising-support',
      label: 'Rising support is holding',
      status: trendline.trendline_break?.broken ? 'failed' : 'met',
    });
  }
  if (confirmationLevel != null) {
    items.push({
      key: 'breakout',
      label: `Close above ${formatCurrency(confirmationLevel)}`,
      status: 'pending',
    });
  }
  if (volumeAnalysis?.relative_volume != null) {
    items.push({
      explanation: `${formatRelativeVolume(volumeAnalysis.relative_volume)} normal`,
      key: 'volume',
      label: 'Relative volume expands',
      status: volumeAnalysis.relative_volume >= 1.2 ? 'met' : 'pending',
    });
  }
  if (primarySupport != null) {
    items.push({
      key: 'support-hold',
      label: `Price holds near ${formatCurrency(primarySupport)}`,
      status: 'pending',
    });
  }
  if (pattern?.status) {
    items.push({
      key: 'pattern-stage',
      label: `${normalizeLabel(pattern.status)} pattern remains intact`,
      status: pattern.status.toLowerCase().includes('fail') ? 'failed' : 'pending',
    });
  }
  return items.slice(0, 4);
}

function buildInvalidations({
  invalidationLevel,
  trendline,
  volumeAnalysis,
}: {
  invalidationLevel: number | null;
  trendline?: TrendlineResponse | null;
  volumeAnalysis?: VolumeAnalysis | null;
}): TechnicalInvalidationItem[] {
  const items: TechnicalInvalidationItem[] = [];
  if (invalidationLevel != null) {
    items.push({
      key: 'close-below-stop',
      label: `Close below ${formatCurrency(invalidationLevel)}`,
      status: 'watch',
    });
  }
  if (trendline?.rising_support?.detected) {
    items.push({
      explanation: trendline.rising_support.status,
      key: 'rising-support-break',
      label: 'Rising support breaks',
      status: trendline.trendline_break?.broken ? 'triggered' : 'watch',
    });
  }
  if (volumeAnalysis?.distribution_volume) {
    items.push({
      key: 'distribution-volume',
      label: 'Distribution volume expands',
      status: 'active',
    });
  }
  if (volumeAnalysis?.breakout_volume === false && volumeAnalysis?.relative_volume != null) {
    items.push({
      key: 'breakout-without-volume',
      label: 'Breakout occurs without volume expansion',
      status: 'watch',
    });
  }
  return items.slice(0, 4);
}

function buildVolumeExplanation(volumeAnalysis?: VolumeAnalysis | null): string | null {
  if (!volumeAnalysis) {
    return null;
  }
  const quality = volumeAnalysis.volume_quality?.toLowerCase() ?? 'unavailable';
  const hasAccumulation = volumeAnalysis.accumulation_volume || volumeAnalysis.signals?.some((signal) => signal.toLowerCase().includes('accumulation'));
  const hasDistribution = volumeAnalysis.distribution_volume || volumeAnalysis.signals?.some((signal) => signal.toLowerCase().includes('distribution'));
  if ((quality.includes('excellent') || quality.includes('strong')) && hasAccumulation) {
    return 'Volume expansion and accumulation support the setup.';
  }
  if (quality.includes('average') && hasAccumulation) {
    return 'Accumulation signs are present, but participation remains near normal.';
  }
  if (quality.includes('weak') || quality.includes('poor')) {
    return 'Participation is below normal and does not confirm the setup.';
  }
  if (hasDistribution) {
    return 'Distribution signs are present and should be monitored.';
  }
  return `${capitalize(quality)} participation.`;
}

function buildTrendExplanation(trendline?: TrendlineResponse | null): string | null {
  if (!trendline) {
    return null;
  }
  if (trendline.rising_support?.detected) {
    const touches = trendline.rising_support.touch_count > 0
      ? ` with ${trendline.rising_support.touch_count} confirmed touches`
      : '';
    const distance = trendline.rising_support.distance_percent != null
      ? ` Price is currently ${formatPercent(Math.abs(trendline.rising_support.distance_percent))} above the trendline.`
      : '';
    return `The medium-term uptrend remains intact${touches}.${distance}`;
  }
  if (trendline.falling_resistance?.detected) {
    return `Falling resistance is active with ${trendline.falling_resistance.touch_count} touches.`;
  }
  return trendline.summary ?? 'Trendline diagnostics are unavailable.';
}

function getTechnicalStance(
  pattern?: DetectedPattern | null,
  trendline?: TrendlineResponse | null,
  volumeAnalysis?: VolumeAnalysis | null,
  supportResistance?: SupportResistanceResponse | null,
): TechnicalStance {
  const direction = pattern?.direction?.toLowerCase();
  if (trendline?.trendline_break?.broken || volumeAnalysis?.volume_quality?.toLowerCase() === 'poor') {
    return 'weakening';
  }
  if (direction === 'bearish') {
    return 'bearish';
  }
  if (direction === 'bullish' && supportResistance?.breakout_level != null) {
    return 'constructive';
  }
  if (trendline?.rising_support?.detected) {
    return 'constructive';
  }
  if (pattern) {
    return direction === 'bullish' ? 'bullish' : 'neutral';
  }
  return 'unavailable';
}

function getPatternStatus(pattern?: DetectedPattern | null): TechnicalSourceStatus {
  if (!pattern) {
    return 'unavailable';
  }
  const source = (pattern.data_source ?? '').toLowerCase();
  if (source.includes('generated_test_data') || source === 'test') {
    return 'test';
  }
  if (source.includes('stale')) {
    return 'stale';
  }
  if (source.includes('fallback')) {
    return 'fallback';
  }
  if (source.includes('mock') || pattern.is_live === false) {
    return 'mock';
  }
  if (pattern.is_live) {
    return 'live';
  }
  return 'historical';
}

function getSourceStatus(source?: { data_source?: string | null; fallback_used?: boolean | null; is_live?: boolean | null; as_of?: string | null } | null): TechnicalSourceStatus {
  if (!source) {
    return 'unavailable';
  }
  const dataSource = (source.data_source ?? '').toLowerCase();
  if (dataSource.includes('generated_test_data') || dataSource === 'test') {
    return 'test';
  }
  if (dataSource.includes('stale')) {
    return 'stale';
  }
  if (source.fallback_used || dataSource.includes('fallback')) {
    return 'fallback';
  }
  if (dataSource.includes('mock')) {
    return 'mock';
  }
  if (source.is_live || dataSource.includes('live')) {
    return 'live';
  }
  if (dataSource.includes('cached')) {
    return 'cached';
  }
  return source.as_of ? 'cached' : 'unavailable';
}

function getQuoteStatus(stock: WatchlistItem, currentPrice?: CurrentPriceSelection | null): TechnicalSourceStatus {
  switch (currentPrice?.source) {
    case 'live_quote':
      return 'live';
    case 'snapshot_quote':
    case 'snapshot_current_price':
      return 'cached';
    case 'history_close':
      return 'historical';
    case 'unavailable':
      return 'unavailable';
    default:
      break;
  }
  const dataSource = stock.data_source?.toLowerCase() ?? '';
  if (dataSource.includes('generated_test_data') || dataSource === 'test') {
    return 'test';
  }
  if (stock.is_stale) {
    return 'stale';
  }
  if (stock.fallback_used || dataSource.includes('fallback')) {
    return 'fallback';
  }
  if (dataSource.includes('mock')) {
    return 'mock';
  }
  if (stock.is_live || dataSource.includes('live')) {
    return 'live';
  }
  return stock.price != null ? 'cached' : 'unavailable';
}

function isSourceCompatible(patternStatus: TechnicalSourceStatus, levelsStatus: TechnicalSourceStatus): boolean {
  return ['live', 'cached', 'historical'].includes(patternStatus) && ['live', 'cached'].includes(levelsStatus);
}

function hasMaterialMismatch(first?: number | null, second?: number | null): boolean {
  if (first == null || second == null || first <= 0 || second <= 0) {
    return false;
  }
  return Math.abs((first - second) / second) * 100 >= MATERIAL_LEVEL_MISMATCH_PERCENT;
}

function getPrimarySupport(supportResistance?: SupportResistanceResponse | null): number | null {
  if (!supportResistance?.support_zones?.length) {
    return supportResistance?.moving_average_support?.ema_20 ?? supportResistance?.moving_average_support?.ema_50 ?? null;
  }
  return Math.max(...supportResistance.support_zones.map((zone) => zone.high));
}

function getPrimaryResistance(supportResistance?: SupportResistanceResponse | null): number | null {
  if (!supportResistance?.resistance_zones?.length) {
    return supportResistance?.breakout_level ?? null;
  }
  return Math.min(...supportResistance.resistance_zones.map((zone) => zone.low));
}

function getPatternDate(pattern?: DetectedPattern | null): string | null {
  return pattern?.markers?.[0]?.date ?? pattern?.chart_data?.at(-1)?.date ?? null;
}

function addLevel(
  levels: TechnicalPriceLevel[],
  key: string,
  label: string,
  value: number | null | undefined,
  kind: TechnicalPriceLevel['kind'],
  sourceStatus: TechnicalSourceStatus,
) {
  if (typeof value === 'number' && Number.isFinite(value) && value > 0) {
    levels.push({ key, kind, label, sourceStatus, value });
  }
}

function mergeCloseLevels(levels: TechnicalPriceLevel[], currentPrice: number | null): TechnicalPriceLevel[] {
  const result: TechnicalPriceLevel[] = [];
  for (const level of levels) {
    const existing = result.find((candidate) => shouldMergeLevels(candidate, level, currentPrice));
    if (existing) {
      const kinds = new Set([...(existing.kinds ?? [existing.kind]), level.kind]);
      existing.kinds = [...kinds];
      existing.label = buildMergedLevelLabel(existing.kinds);
      existing.zoneLow = Math.min(existing.zoneLow ?? existing.value, level.value);
      existing.zoneHigh = Math.max(existing.zoneHigh ?? existing.value, level.value);
      existing.value = existing.zoneHigh;
    } else {
      result.push({ ...level, kinds: [level.kind] });
    }
  }
  return result;
}

function shouldMergeLevels(first: TechnicalPriceLevel, second: TechnicalPriceLevel, currentPrice: number | null): boolean {
  if (first.kind === 'current' || second.kind === 'current') {
    return false;
  }
  const compatiblePairs = new Set([
    'confirmation:resistance',
    'resistance:confirmation',
    'support:ema',
    'ema:support',
  ]);
  const pairKey = `${first.kind}:${second.kind}`;
  if (!compatiblePairs.has(pairKey) && first.kind !== second.kind) {
    return false;
  }
  const tolerance = Math.max(0.05, (currentPrice ?? second.value) * 0.003);
  return Math.abs(first.value - second.value) <= tolerance;
}

function buildMergedLevelLabel(kinds: TechnicalPriceLevel['kind'][]): string {
  if (kinds.includes('confirmation') && kinds.includes('resistance')) {
    return 'Confirmation / resistance zone';
  }
  if (kinds.includes('support') && kinds.includes('ema')) {
    return 'Support / EMA zone';
  }
  return kinds.map((kind) => kind.charAt(0).toUpperCase() + kind.slice(1)).join(' / ');
}

function getScoreLabel(score: number): string {
  if (score >= 80) {
    return 'Strong match';
  }
  if (score >= 65) {
    return 'Constructive match';
  }
  if (score >= 45) {
    return 'Developing match';
  }
  return 'Weak match';
}

function normalizeLabel(value?: string | null): string | null {
  if (!value) {
    return null;
  }
  return value
    .replace(/_/g, ' ')
    .split(' ')
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
}

function sanitizeText(value?: string | null): string | null {
  if (!value || ['n/a', 'unknown', 'setup updating'].includes(value.trim().toLowerCase())) {
    return null;
  }
  return value.trim();
}

function toNumber(value?: number | string | null): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string') {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

export function formatCurrency(value?: number | null): string {
  return typeof value === 'number' && Number.isFinite(value) ? `$${value.toFixed(2)}` : 'Unavailable';
}

export function formatRelativeVolume(value?: number | null): string {
  return typeof value === 'number' && Number.isFinite(value) ? `${value.toFixed(2)}x` : 'Unavailable';
}

export function formatPercent(value?: number | null): string {
  return typeof value === 'number' && Number.isFinite(value) ? `${value.toFixed(1)}%` : 'Unavailable';
}

function capitalize(value: string): string {
  return value ? value.charAt(0).toUpperCase() + value.slice(1) : value;
}

function formatTouches(value?: number | null): string | null {
  return typeof value === 'number' && value > 0 ? `${value} confirmed touches` : null;
}

function capWords(value: string, maxWords: number): string {
  const words = value.trim().split(/\s+/);
  return words.length > maxWords ? `${words.slice(0, maxWords).join(' ')}...` : value;
}
