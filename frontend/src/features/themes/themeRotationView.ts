import type { RotationLabelMode } from '@/features/sectors/analysis/rotationLabels';
import type {
  CanonicalThemeRotationPoint,
  ThemeRotationModel,
  ThemeRotationQuadrant,
} from '@/features/themes/themeRotation';
import type { ThemeOverlap } from '@/features/themes/themeSnapshot';

export type ThemeRotationViewMode = 'overview' | 'compare' | 'focus';
export type ThemeRotationUniverse =
  | 'all'
  | 'technology_ai'
  | 'consumer_digital'
  | 'industrials_strategic_growth'
  | 'healthcare'
  | 'finance_crypto'
  | 'saved'
  | 'custom';
export type ThemeRotationMovementFilter = 'all' | 'meaningful' | 'fast' | 'stable';
export type ThemeRotationTransitionFilter =
  | 'all'
  | 'entered_leading'
  | 'entered_improving'
  | 'lost_leading'
  | 'quadrant_changed'
  | 'no_recent_change';
export type ThemeRotationTailLength = 'current' | '3' | '5' | '8' | 'full';
export type ThemeRotationFocusContext = 'faint' | 'hidden';
export type ThemeRotationQuadrantFilter = ThemeRotationQuadrant | 'all';

export type ThemeRotationThemeMetadata = {
  aliases: string[];
  id: string;
  name: string;
  parentSectorIds: string[];
  rank: number | null;
  status: string;
  taxonomyStatus: string;
};

export type ThemeRotationViewState = {
  focusContext: ThemeRotationFocusContext;
  focusedThemeId: string | null;
  labelMode: RotationLabelMode;
  mode: ThemeRotationViewMode;
  movement: ThemeRotationMovementFilter;
  quadrant: ThemeRotationQuadrantFilter;
  selectedThemeIds: string[];
  showRelatedThemes: boolean;
  smartLabelLimit: number;
  tailLength: ThemeRotationTailLength;
  transition: ThemeRotationTransitionFilter;
  universe: ThemeRotationUniverse;
};

export type ThemeRotationViewSource = {
  metadata: ThemeRotationThemeMetadata[];
  overlap: ThemeOverlap[];
  rotation: ThemeRotationModel;
  savedThemeIds: ReadonlySet<string>;
};

export type VisibleThemeRotationPoint = CanonicalThemeRotationPoint & {
  isFocused: boolean;
  isRelated: boolean;
  isSelected: boolean;
  viewOpacity: number;
};

export type ThemeRotationViewExclusion = {
  reason: string;
  themeId: string;
};

export type VisibleThemeRotationView = {
  activeFilterSummary: string[];
  counts: {
    eligible: number;
    hiddenByFilters: number;
    historicalNodes: number;
    labels: number;
    plotted: number;
    selected: number;
    unavailableByEvidence: number;
  };
  exclusions: ThemeRotationViewExclusion[];
  focusedTheme: VisibleThemeRotationPoint | null;
  movementSets: {
    fast: ReadonlySet<string>;
    meaningful: ReadonlySet<string>;
    stable: ReadonlySet<string>;
  };
  relatedThemeIds: string[];
  renderedLabels: string[];
  visibleCurrentPoints: VisibleThemeRotationPoint[];
  visibleTails: { history: CanonicalThemeRotationPoint['history']; themeId: string }[];
  visibleThemes: VisibleThemeRotationPoint[];
};

export const THEME_ROTATION_VIEW_POLICY = Object.freeze({
  fastMoverFraction: 0.2,
  meaningfulNetDisplacementPercentile: 0.5,
  meaningfulSpeedPercentile: 0.5,
  stableFraction: 0.2,
  version: 'theme-rotation-view-policy-v1',
});

export const THEME_ROTATION_UNIVERSE_OPTIONS: {
  key: ThemeRotationUniverse;
  label: string;
  parentSectorIds: string[];
}[] = [
  { key: 'all', label: 'All Themes', parentSectorIds: [] },
  { key: 'technology_ai', label: 'Technology & AI', parentSectorIds: ['information_technology'] },
  { key: 'consumer_digital', label: 'Consumer & Digital', parentSectorIds: ['consumer_discretionary', 'communication_services'] },
  { key: 'industrials_strategic_growth', label: 'Industrials & Strategic Growth', parentSectorIds: ['industrials', 'energy', 'utilities', 'materials', 'real_estate'] },
  { key: 'healthcare', label: 'Healthcare', parentSectorIds: ['health_care'] },
  { key: 'finance_crypto', label: 'Finance & Crypto', parentSectorIds: ['financials'] },
  { key: 'saved', label: 'Saved Themes', parentSectorIds: [] },
  { key: 'custom', label: 'Custom Selection', parentSectorIds: [] },
];

export const DEFAULT_THEME_ROTATION_VIEW_STATE: ThemeRotationViewState = {
  focusContext: 'faint',
  focusedThemeId: null,
  labelMode: 'smart',
  mode: 'overview',
  movement: 'meaningful',
  quadrant: 'all',
  selectedThemeIds: [],
  showRelatedThemes: false,
  smartLabelLimit: 6,
  tailLength: '3',
  transition: 'all',
  universe: 'all',
};

const UNIVERSE_BY_KEY = new Map(THEME_ROTATION_UNIVERSE_OPTIONS.map((option) => [option.key, option]));

export function buildVisibleRotationView(
  source: ThemeRotationViewSource,
  viewState: ThemeRotationViewState,
): VisibleThemeRotationView {
  const metadataById = new Map(source.metadata.map((item) => [item.id, item]));
  const selectedSet = new Set(viewState.selectedThemeIds);
  const relatedThemeIds = viewState.focusedThemeId
    ? resolveRelatedThemeIds(viewState.focusedThemeId, source.metadata, source.overlap)
    : [];
  const relatedSet = new Set(relatedThemeIds);
  const exclusions: ThemeRotationViewExclusion[] = source.rotation.exclusions.map((item) => ({ ...item }));
  const excludedIds = new Set(exclusions.map((item) => item.themeId));
  const exclude = (themeId: string, reason: string) => {
    if (excludedIds.has(themeId)) return;
    excludedIds.add(themeId);
    exclusions.push({ reason, themeId });
  };

  // 1. Canonical row-level eligibility. The response is already governed, but
  // this defensive gate refuses invalid or unavailable rows without coercion.
  let visible = source.rotation.points.filter((point) => {
    const eligible = point.rankingEligible
      && point.status === 'available'
      && Number.isFinite(point.relativeTrend)
      && Number.isFinite(point.relativeMomentum);
    if (!eligible) exclude(point.themeId, 'canonical_row_not_plot_eligible');
    return eligible;
  });
  const eligibleCount = visible.length;
  const movementSets = buildMovementSets(visible);

  // 2. Taxonomy, saved, or custom universe.
  visible = visible.filter((point) => {
    const included = isThemeInUniverse(point.themeId, viewState.universe, metadataById, source.savedThemeIds);
    if (!included) exclude(point.themeId, `universe:${viewState.universe}`);
    return included;
  });

  // 3. Explicit selection. A selection filters points only for Custom or Compare.
  if (viewState.universe === 'custom' || viewState.mode === 'compare') {
    visible = visible.filter((point) => {
      const included = selectedSet.has(point.themeId);
      if (!included) exclude(point.themeId, 'explicit_selection');
      return included;
    });
  }

  // 4. Mode constraint. Focus can retain faint context or hide it. The focused
  // point itself is restored from the eligible universe so inspection cannot be
  // defeated by a stale presentation filter.
  if (viewState.mode === 'focus' && viewState.focusedThemeId) {
    const focused = source.rotation.points.find((point) => point.themeId === viewState.focusedThemeId);
    if (focused && !visible.some((point) => point.themeId === focused.themeId)) visible = [focused, ...visible];
    if (viewState.focusContext === 'hidden') {
      visible = visible.filter((point) => point.themeId === viewState.focusedThemeId || (viewState.showRelatedThemes && relatedSet.has(point.themeId)));
    }
  }

  // Focus explicitly overrides quadrant, movement, and transition constraints.
  const appliesAnalyticalPresentationFilters = viewState.mode !== 'focus';

  // 5. Current endpoint quadrant.
  if (appliesAnalyticalPresentationFilters && viewState.quadrant !== 'all') {
    visible = visible.filter((point) => {
      const included = point.quadrant === viewState.quadrant;
      if (!included) exclude(point.themeId, `quadrant:${viewState.quadrant}`);
      return included;
    });
  }

  // 6. Governed movement fields; no coordinates or analytical class are recalculated.
  if (appliesAnalyticalPresentationFilters && viewState.movement !== 'all') {
    const allowed = movementSets[viewState.movement];
    visible = visible.filter((point) => {
      const included = allowed.has(point.themeId);
      if (!included) exclude(point.themeId, `movement:${viewState.movement}`);
      return included;
    });
  }

  // 7. Canonical latest transition descriptor.
  if (appliesAnalyticalPresentationFilters && viewState.transition !== 'all') {
    visible = visible.filter((point) => {
      const included = matchesTransition(point, viewState.transition);
      if (!included) exclude(point.themeId, point.latestQuadrantTransition ? `transition:${viewState.transition}` : 'transition:insufficient_history');
      return included;
    });
  }

  // 8. Tail projection. Histories are sliced, never extended or interpolated.
  const tailCount = tailLengthToCount(viewState.tailLength);
  const projected: VisibleThemeRotationPoint[] = visible.map((point) => {
    const isFocused = point.themeId === viewState.focusedThemeId;
    const isRelated = relatedSet.has(point.themeId);
    const isSelected = selectedSet.has(point.themeId);
    const projectedHistory = viewState.mode === 'focus' && !isFocused
      ? point.history.slice(-1)
      : tailCount === null
        ? point.history.slice()
        : point.history.slice(-tailCount);
    return {
      ...point,
      history: projectedHistory,
      isFocused,
      isRelated,
      isSelected,
      viewOpacity: focusOpacity(viewState, isFocused, isRelated),
    };
  });

  // 9. Labels are selected after point visibility and cannot affect it.
  const renderedLabels = selectLabelThemeIds(projected, viewState, source.savedThemeIds, movementSets.fast);
  const activeFilterSummary = buildActiveFilterSummary(viewState, projected.length, eligibleCount);
  const focusedTheme = projected.find((point) => point.themeId === viewState.focusedThemeId) ?? null;

  return {
    activeFilterSummary,
    counts: {
      eligible: eligibleCount,
      hiddenByFilters: Math.max(0, eligibleCount - projected.length),
      historicalNodes: projected.reduce((total, point) => total + point.history.length, 0),
      labels: renderedLabels.length,
      plotted: projected.length,
      selected: viewState.selectedThemeIds.length,
      unavailableByEvidence: source.rotation.excludedCount,
    },
    exclusions,
    focusedTheme,
    movementSets,
    relatedThemeIds,
    renderedLabels,
    visibleCurrentPoints: projected,
    visibleTails: projected.map((point) => ({ history: point.history, themeId: point.themeId })),
    visibleThemes: projected,
  };
}

export function searchThemeOptions(metadata: ThemeRotationThemeMetadata[], query: string) {
  const normalized = normalizeSearch(query);
  const seen = new Set<string>();
  return metadata.filter((item) => {
    if (item.taxonomyStatus === 'retired' || seen.has(item.id)) return false;
    seen.add(item.id);
    if (!normalized) return true;
    return [item.name, item.id, ...item.aliases].some((value) => normalizeSearch(value).includes(normalized));
  });
}

export function toggleThemeSelection(selection: string[], themeId: string) {
  return selection.includes(themeId)
    ? selection.filter((item) => item !== themeId)
    : [...selection, themeId];
}

export function selectAllThemeOptions(selection: string[], themeIds: string[]) {
  const result = [...selection];
  const seen = new Set(result);
  themeIds.forEach((themeId) => {
    if (!seen.has(themeId)) {
      seen.add(themeId);
      result.push(themeId);
    }
  });
  return result;
}

export function selectionReadabilityWarning(selectionCount: number, compact: boolean) {
  const limit = compact ? 8 : 12;
  return selectionCount > limit
    ? `${selectionCount} themes selected. More than ${limit} may be difficult to read; selection remains available.`
    : null;
}

export function removeThemeFromComparison(
  state: ThemeRotationViewState,
  themeId: string,
  compact: boolean,
): ThemeRotationViewState {
  const selectedThemeIds = state.selectedThemeIds.filter((id) => id !== themeId);
  return selectedThemeIds.length < 2
    ? {
        ...state,
        labelMode: 'smart',
        mode: 'overview',
        selectedThemeIds,
        tailLength: compact ? '3' : '5',
      }
    : { ...state, selectedThemeIds };
}

export function resolveRelatedThemeIds(
  focusedThemeId: string,
  metadata: ThemeRotationThemeMetadata[],
  overlap: ThemeOverlap[],
  limit = 8,
) {
  const focused = metadata.find((item) => item.id === focusedThemeId);
  if (!focused) return [];
  const overlapById = new Map<string, number>();
  overlap.forEach((item) => {
    if (item.leftThemeId !== focusedThemeId && item.rightThemeId !== focusedThemeId) return;
    const otherId = item.leftThemeId === focusedThemeId ? item.rightThemeId : item.leftThemeId;
    overlapById.set(otherId, Math.max(item.jaccardOverlap ?? 0, item.weightedOverlap ?? 0));
  });
  const parentSet = new Set(focused.parentSectorIds);
  return metadata
    .filter((item) => item.id !== focusedThemeId && item.taxonomyStatus !== 'retired')
    .map((item) => {
      const sharedParents = item.parentSectorIds.filter((parent) => parentSet.has(parent)).length;
      const overlapScore = overlapById.get(item.id) ?? 0;
      return { id: item.id, name: item.name, rank: item.rank ?? Number.MAX_SAFE_INTEGER, score: sharedParents * 100 + overlapScore * 10 };
    })
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score || a.rank - b.rank || a.name.localeCompare(b.name) || a.id.localeCompare(b.id))
    .slice(0, limit)
    .map((item) => item.id);
}

function buildMovementSets(points: CanonicalThemeRotationPoint[]) {
  const bySpeed = [...points].sort((a, b) => b.speed - a.speed || a.themeId.localeCompare(b.themeId));
  const byDisplacement = [...points].sort((a, b) => b.netDisplacement - a.netDisplacement || a.themeId.localeCompare(b.themeId));
  const fastCount = Math.ceil(points.length * THEME_ROTATION_VIEW_POLICY.fastMoverFraction);
  const stableCount = Math.ceil(points.length * THEME_ROTATION_VIEW_POLICY.stableFraction);
  const speedMedian = percentile(points.map((point) => point.speed), THEME_ROTATION_VIEW_POLICY.meaningfulSpeedPercentile);
  const displacementMedian = percentile(points.map((point) => point.netDisplacement), THEME_ROTATION_VIEW_POLICY.meaningfulNetDisplacementPercentile);
  const meaningful = new Set(points.filter((point) => (
    point.speed > speedMedian
    || point.netDisplacement > displacementMedian
    || point.latestQuadrantTransition?.changed === true
  )).map((point) => point.themeId));
  const fast = new Set(bySpeed.slice(0, fastCount).map((point) => point.themeId));
  const stable = new Set(
    [...bySpeed]
      .reverse()
      .filter((point) => point.latestQuadrantTransition?.changed === false)
      .slice(0, stableCount)
      .map((point) => point.themeId),
  );
  // The displacement ordering is evaluated here to make deterministic ties part
  // of the policy contract, even though the threshold itself is percentile based.
  void byDisplacement;
  return { fast, meaningful, stable };
}

function isThemeInUniverse(
  themeId: string,
  universe: ThemeRotationUniverse,
  metadataById: Map<string, ThemeRotationThemeMetadata>,
  savedThemeIds: ReadonlySet<string>,
) {
  if (universe === 'all' || universe === 'custom') return true;
  if (universe === 'saved') return savedThemeIds.has(themeId);
  const option = UNIVERSE_BY_KEY.get(universe);
  const metadata = metadataById.get(themeId);
  return Boolean(option && metadata && metadata.parentSectorIds.some((parent) => option.parentSectorIds.includes(parent)));
}

function matchesTransition(point: CanonicalThemeRotationPoint, filter: ThemeRotationTransitionFilter) {
  if (filter === 'all') return true;
  const transition = point.latestQuadrantTransition;
  if (!transition) return false;
  if (filter === 'entered_leading') return transition.to === 'leading' && transition.from !== 'leading';
  if (filter === 'entered_improving') return transition.to === 'improving' && transition.from !== 'improving';
  if (filter === 'lost_leading') return transition.from === 'leading' && transition.to !== 'leading';
  if (filter === 'quadrant_changed') return transition.changed;
  return !transition.changed;
}

function tailLengthToCount(length: ThemeRotationTailLength) {
  if (length === 'full') return null;
  if (length === 'current') return 1;
  return Number(length);
}

function focusOpacity(viewState: ThemeRotationViewState, isFocused: boolean, isRelated: boolean) {
  if (viewState.mode !== 'focus') return 1;
  if (isFocused) return 1;
  if (isRelated && viewState.showRelatedThemes) return 0.42;
  return 0.15;
}

function selectLabelThemeIds(
  points: VisibleThemeRotationPoint[],
  viewState: ThemeRotationViewState,
  savedThemeIds: ReadonlySet<string>,
  fastThemeIds: ReadonlySet<string>,
) {
  if (viewState.labelMode === 'none') return [];
  if (viewState.labelMode === 'all') return points.map((point) => point.themeId);
  if (viewState.labelMode === 'selected') {
    return points
      .filter((point) => point.isFocused || (viewState.mode !== 'focus' && point.isSelected))
      .map((point) => point.themeId);
  }
  return [...points]
    .sort((a, b) => labelScore(b, savedThemeIds, fastThemeIds) - labelScore(a, savedThemeIds, fastThemeIds) || a.themeId.localeCompare(b.themeId))
    .slice(0, Math.max(0, viewState.smartLabelLimit))
    .map((point) => point.themeId);
}

function labelScore(
  point: VisibleThemeRotationPoint,
  savedThemeIds: ReadonlySet<string>,
  fastThemeIds: ReadonlySet<string>,
) {
  return point.labelPriority
    + (point.isFocused ? 1_000_000 : 0)
    + (point.isSelected ? 500_000 : 0)
    + (savedThemeIds.has(point.themeId) ? 100_000 : 0)
    + (point.latestQuadrantTransition?.changed ? 50_000 : 0)
    + (fastThemeIds.has(point.themeId) ? 25_000 : 0)
    + (point.quadrant === 'leading' ? 10_000 : point.quadrant === 'improving' ? 5_000 : 0);
}

function buildActiveFilterSummary(state: ThemeRotationViewState, plotted: number, eligible: number) {
  const universe = UNIVERSE_BY_KEY.get(state.universe)?.label ?? state.universe;
  const movement = state.movement === 'all' ? 'All movement' : state.movement === 'fast' ? 'Fast movers' : state.movement === 'stable' ? 'Stable themes' : 'Meaningful movers';
  const trail = state.tailLength === 'full' ? 'Full trails' : state.tailLength === 'current' ? 'Current points' : `${state.tailLength}-point trails`;
  const labels = `${state.labelMode[0].toUpperCase()}${state.labelMode.slice(1)} labels`;
  const summary = [`${plotted} of ${eligible} themes shown`, universe, movement, trail, labels];
  if (state.quadrant !== 'all') summary.push(`${title(state.quadrant)} quadrant`);
  if (state.transition !== 'all') summary.push(title(state.transition.replaceAll('_', ' ')));
  if (state.mode === 'focus') summary.push('Focus overrides movement, quadrant, and transition filters');
  return summary;
}

function percentile(values: number[], fraction: number) {
  if (!values.length) return Number.POSITIVE_INFINITY;
  const ordered = [...values].sort((a, b) => a - b);
  const index = Math.max(0, Math.min(ordered.length - 1, Math.floor((ordered.length - 1) * fraction)));
  return ordered[index];
}

function normalizeSearch(value: string) {
  return value.trim().toLocaleLowerCase().replace(/[_-]+/g, ' ').replace(/\s+/g, ' ');
}

function title(value: string) {
  return value.replace(/\b\w/g, (letter) => letter.toUpperCase());
}
