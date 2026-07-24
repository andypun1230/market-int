import { normalizeThemeId } from './themeIds';
import type { ThemeRotationInterval, ThemeRotationPoint } from './themeSnapshot';

export type ThemeRotationQuadrant = 'leading' | 'improving' | 'weakening' | 'lagging';
export type ThemeRotationTrajectory = 'improving' | 'deteriorating' | 'stable' | null;
export type ThemeRotationProfile = 'short' | 'medium' | 'long';
export const THEME_ROTATION_MODEL_VERSION = 'theme-relative-trend-momentum-v1';

export type CanonicalThemeRotationPoint = {
  aliases?: string[];
  themeId: string;
  displayName: string;
  taxonomyVersion: string;
  snapshotId: string;
  asOf: string;
  timeframe: ThemeRotationInterval;
  profile: ThemeRotationProfile;
  modelVersion: string;
  status: string;
  confidence: Record<string, unknown>;
  relativeTrend: number;
  relativeMomentum: number;
  previousRelativeTrend: number | null;
  previousRelativeMomentum: number | null;
  quadrant: ThemeRotationQuadrant;
  trajectory: ThemeRotationTrajectory;
  direction: string;
  speed: number;
  distanceTravelled: number;
  netDisplacement: number;
  recentAcceleration: number;
  quadrantTransitions: number;
  previousQuadrant: ThemeRotationQuadrant | null;
  latestQuadrantTransition: {
    asOf: string;
    changed: boolean;
    from: ThemeRotationQuadrant;
    to: ThemeRotationQuadrant;
  } | null;
  coverageRatio: number | null;
  evidenceReferences: string[];
  missingData: unknown[];
  parentSectorIds?: string[];
  rankingEligible: boolean;
  rank: number | null;
  labelPriority: number;
  partialCoverageDisclosure: string | null;
  taxonomyStatus?: string;
  history: ThemeRotationPoint[];
};

export type ThemeRotationExclusion = { themeId: string; reason: string };
export type ThemeRotationModel = {
  snapshotId: string;
  taxonomyVersion: string;
  asOf: string;
  timeframe: ThemeRotationInterval;
  profile: ThemeRotationProfile;
  modelVersion: string;
  status: string;
  snapshotStatus: string;
  benchmark: string;
  eligibleCount: number;
  excludedCount: number;
  latestCommonDate: string | null;
  points: CanonicalThemeRotationPoint[];
  exclusions: ThemeRotationExclusion[];
  timeframeDefinition: Record<string, unknown>;
};

type RecordValue = Record<string, unknown>;

export function adaptThemeRotation(value: unknown): ThemeRotationModel | null {
  if (!isRecord(value)) return null;
  const snapshotId = text(value.snapshot_id);
  const taxonomyVersion = text(value.taxonomy_version);
  const timeframe = rotationInterval(value.timeframe ?? value.interval);
  const profile = rotationProfile(value.profile);
  const modelVersion = text(value.rotation_model_version);
  if (!snapshotId || !taxonomyVersion || !timeframe || !profile || modelVersion !== THEME_ROTATION_MODEL_VERSION) return null;
  const points = list(value.points).flatMap(adaptPoint);
  const exclusions = list(value.exclusions).flatMap((item) => {
    if (!isRecord(item)) return [];
    const themeId = normalizeThemeId(text(item.theme_id));
    const reason = text(item.reason);
    return themeId && reason ? [{ themeId, reason }] : [];
  });
  return {
    snapshotId,
    taxonomyVersion,
    asOf: text(value.as_of) ?? '',
    timeframe,
    profile,
    modelVersion,
    status: text(value.status) ?? 'unavailable',
    snapshotStatus: text(value.snapshot_status) ?? 'unavailable',
    benchmark: text(value.benchmark) ?? 'SPY',
    eligibleCount: integer(value.eligible_count) ?? points.length,
    excludedCount: integer(value.excluded_count) ?? exclusions.length,
    latestCommonDate: text(value.latest_common_date),
    points,
    exclusions,
    timeframeDefinition: isRecord(value.timeframe_definition) ? value.timeframe_definition : {},
  };
}

export function themeRotationCacheKey(
  timeframe: ThemeRotationInterval,
  identity: { snapshotId: string; taxonomyVersion: string },
  modelVersion = THEME_ROTATION_MODEL_VERSION,
) {
  return `theme-rotation:${identity.taxonomyVersion}:${identity.snapshotId}:${modelVersion}:${timeframe}`;
}

function adaptPoint(value: unknown): CanonicalThemeRotationPoint[] {
  if (!isRecord(value)) return [];
  const themeId = normalizeThemeId(text(value.theme_id));
  const displayName = text(value.display_name);
  const taxonomyVersion = text(value.taxonomy_version);
  const snapshotId = text(value.snapshot_id);
  const timeframe = rotationInterval(value.timeframe);
  const profile = rotationProfile(value.profile);
  const modelVersion = text(value.model_version);
  const relativeTrend = finite(value.relative_trend);
  const relativeMomentum = finite(value.relative_momentum);
  const quadrant = rotationQuadrant(value.quadrant);
  if (!themeId || !displayName || !taxonomyVersion || !snapshotId || !timeframe || !profile || modelVersion !== THEME_ROTATION_MODEL_VERSION || relativeTrend === null || relativeMomentum === null || !quadrant) return [];
  return [{
    aliases: list(value.aliases).filter((item): item is string => typeof item === 'string'),
    themeId,
    displayName,
    taxonomyVersion,
    snapshotId,
    asOf: text(value.as_of) ?? '',
    timeframe,
    profile,
    modelVersion,
    status: text(value.status) ?? 'unavailable',
    confidence: isRecord(value.confidence) ? value.confidence : {},
    relativeTrend,
    relativeMomentum,
    previousRelativeTrend: finite(value.previous_relative_trend),
    previousRelativeMomentum: finite(value.previous_momentum_normalized),
    quadrant,
    trajectory: trajectory(value.trajectory),
    direction: text(value.direction) ?? 'stable',
    speed: finite(value.speed) ?? 0,
    distanceTravelled: finite(value.distance_travelled) ?? 0,
    netDisplacement: finite(value.net_displacement) ?? 0,
    recentAcceleration: finite(value.recent_acceleration) ?? 0,
    quadrantTransitions: integer(value.quadrant_transitions) ?? 0,
    previousQuadrant: rotationQuadrant(value.previous_quadrant),
    latestQuadrantTransition: adaptLatestTransition(value.latest_quadrant_transition),
    coverageRatio: finite(value.coverage_ratio),
    evidenceReferences: list(value.evidence_references).filter((item): item is string => typeof item === 'string'),
    missingData: list(value.missing_data),
    parentSectorIds: list(value.parent_sector_ids).filter((item): item is string => typeof item === 'string'),
    rankingEligible: value.ranking_eligible === true,
    rank: integer(value.rank),
    labelPriority: finite(value.label_priority) ?? 0,
    partialCoverageDisclosure: text(value.partial_coverage_disclosure),
    taxonomyStatus: text(value.taxonomy_status) ?? 'active',
    history: list(value.trail_points).flatMap(adaptHistoryPoint),
  }];
}

function adaptLatestTransition(value: unknown): CanonicalThemeRotationPoint['latestQuadrantTransition'] {
  if (!isRecord(value)) return null;
  const from = rotationQuadrant(value.from);
  const to = rotationQuadrant(value.to);
  const asOf = text(value.as_of);
  return from && to && asOf ? { asOf, changed: value.changed === true, from, to } : null;
}

function adaptHistoryPoint(value: unknown): ThemeRotationPoint[] {
  if (!isRecord(value)) return [];
  const date = text(value.market_date);
  const relativeStrength = finite(value.relative_trend);
  const relativeMomentum = finite(value.relative_momentum);
  return date && relativeStrength !== null && relativeMomentum !== null
    ? [{ date, dateLabel: date, relativeStrength, relativeMomentum, isSynthetic: value.is_synthetic === true }]
    : [];
}

function rotationInterval(value: unknown): ThemeRotationInterval | null {
  const normalized = typeof value === 'string' ? value.toUpperCase() : '';
  return normalized === '1W' || normalized === '1M' || normalized === '3M' ? normalized : null;
}
function rotationProfile(value: unknown): ThemeRotationProfile | null { return value === 'short' || value === 'medium' || value === 'long' ? value : null; }
function rotationQuadrant(value: unknown): ThemeRotationQuadrant | null { return value === 'leading' || value === 'improving' || value === 'weakening' || value === 'lagging' ? value : null; }
function trajectory(value: unknown): ThemeRotationTrajectory { return value === 'improving' || value === 'deteriorating' || value === 'stable' ? value : null; }
function isRecord(value: unknown): value is RecordValue { return Boolean(value) && typeof value === 'object' && !Array.isArray(value); }
function list(value: unknown): unknown[] { return Array.isArray(value) ? value : []; }
function text(value: unknown): string | null { return typeof value === 'string' ? value : null; }
function finite(value: unknown): number | null { return typeof value === 'number' && Number.isFinite(value) ? value : null; }
function integer(value: unknown): number | null { return typeof value === 'number' && Number.isInteger(value) ? value : null; }
