import type { CanonicalThemeRotationPoint, ThemeRotationModel, ThemeRotationQuadrant } from '../src/features/themes/themeRotation';
import {
  DEFAULT_THEME_ROTATION_VIEW_STATE,
  THEME_ROTATION_UNIVERSE_OPTIONS,
  THEME_ROTATION_VIEW_POLICY,
  buildVisibleRotationView,
  removeThemeFromComparison,
  resolveRelatedThemeIds,
  searchThemeOptions,
  selectAllThemeOptions,
  selectionReadabilityWarning,
  toggleThemeSelection,
  type ThemeRotationThemeMetadata,
  type ThemeRotationViewState,
} from '../src/features/themes/themeRotationView';

function assert(condition: unknown, message: string) {
  if (!condition) throw new Error(message);
}

const PARENTS = [
  'information_technology',
  'consumer_discretionary',
  'industrials',
  'health_care',
  'financials',
] as const;
const QUADRANTS: ThemeRotationQuadrant[] = ['leading', 'improving', 'weakening', 'lagging'];

function canonicalPoint(index: number): CanonicalThemeRotationPoint {
  const quadrant = QUADRANTS[index % QUADRANTS.length];
  const previousQuadrant = index === 9
    ? null
    : index === 0
      ? 'improving'
      : index === 1
        ? 'lagging'
        : index === 2
          ? 'leading'
          : index === 3
            ? 'improving'
            : quadrant;
  const transition = previousQuadrant === null ? null : {
    asOf: '2026-07-22',
    changed: previousQuadrant !== quadrant,
    from: previousQuadrant,
    to: quadrant,
  };
  const history = Array.from({ length: 10 }, (_, pointIndex) => ({
    date: `2026-07-${String(13 + pointIndex).padStart(2, '0')}`,
    dateLabel: `2026-07-${String(13 + pointIndex).padStart(2, '0')}`,
    isSynthetic: false,
    relativeMomentum: 96 + index + pointIndex / 10,
    relativeStrength: 97 + index + pointIndex / 10,
  }));
  return {
    asOf: '2026-07-22',
    confidence: { label: index < 5 ? 'high' : 'moderate' },
    coverageRatio: 1,
    direction: index % 2 ? 'north-east' : 'east',
    displayName: `Theme ${index}`,
    distanceTravelled: index + 2,
    evidenceReferences: [`evidence-${index}`],
    history,
    labelPriority: 100 - index,
    latestQuadrantTransition: transition,
    missingData: [],
    modelVersion: 'theme-relative-trend-momentum-v1',
    netDisplacement: index + 1,
    partialCoverageDisclosure: null,
    previousQuadrant,
    previousRelativeMomentum: history.at(-2)?.relativeMomentum ?? null,
    previousRelativeTrend: history.at(-2)?.relativeStrength ?? null,
    profile: 'medium',
    quadrant,
    quadrantTransitions: transition?.changed ? 1 : 0,
    rank: index + 1,
    rankingEligible: true,
    recentAcceleration: index / 10,
    relativeMomentum: history.at(-1)!.relativeMomentum,
    relativeTrend: history.at(-1)!.relativeStrength,
    snapshotId: 'snapshot-view-test',
    speed: index + 1,
    status: 'available',
    taxonomyVersion: '2026.07.1',
    themeId: `theme_${index}`,
    timeframe: '1M',
    trajectory: index % 3 === 0 ? 'improving' : 'stable',
  };
}

const points = Array.from({ length: 10 }, (_, index) => canonicalPoint(index));
const metadata: ThemeRotationThemeMetadata[] = points.map((point, index) => ({
  aliases: [`alias-${index}`, index === 0 ? 'zero alias' : `theme alias ${index}`],
  id: point.themeId,
  name: point.displayName,
  parentSectorIds: [PARENTS[index % PARENTS.length]],
  rank: point.rank,
  status: 'available',
  taxonomyStatus: 'active',
}));
const rotation: ThemeRotationModel = {
  asOf: '2026-07-22T21:00:00Z',
  benchmark: 'SPY',
  eligibleCount: 10,
  excludedCount: 1,
  exclusions: [{ reason: 'evidence_validation_failed', themeId: 'theme_unavailable' }],
  latestCommonDate: '2026-07-22',
  modelVersion: 'theme-relative-trend-momentum-v1',
  points,
  profile: 'medium',
  snapshotId: 'snapshot-view-test',
  snapshotStatus: 'partial',
  status: 'partial',
  taxonomyVersion: '2026.07.1',
  timeframe: '1M',
  timeframeDefinition: {},
};
const source = {
  metadata,
  overlap: [{ commonMembers: ['ABC'], jaccardOverlap: 0.4, leftThemeId: 'theme_0', rightThemeId: 'theme_4', weightedOverlap: 0.5 }],
  rotation,
  savedThemeIds: new Set(['theme_1', 'theme_6']),
};

function state(patch: Partial<ThemeRotationViewState> = {}): ThemeRotationViewState {
  return { ...DEFAULT_THEME_ROTATION_VIEW_STATE, movement: 'all', tailLength: 'full', ...patch };
}

function run() {
  const all = buildVisibleRotationView(source, state());
  assert(all.counts.plotted === 10 && all.counts.hiddenByFilters === 0, 'All Themes restores every eligible canonical point');
  assert(all.counts.unavailableByEvidence === 1, 'data exclusions remain separate from user-hidden themes');
  assert(all.counts.historicalNodes === 100, 'Full tails preserve all genuine backend observations');

  const groupExpected: Record<string, number> = {
    consumer_digital: 2,
    finance_crypto: 2,
    healthcare: 2,
    industrials_strategic_growth: 2,
    technology_ai: 2,
  };
  THEME_ROTATION_UNIVERSE_OPTIONS.filter((option) => option.parentSectorIds.length).forEach((option) => {
    const view = buildVisibleRotationView(source, state({ universe: option.key }));
    assert(view.counts.plotted === groupExpected[option.key], `${option.label} uses canonical parent-sector membership`);
  });
  const saved = buildVisibleRotationView(source, state({ universe: 'saved' }));
  assert(saved.visibleThemes.map((point) => point.themeId).join(',') === 'theme_1,theme_6', 'Saved Themes uses the unified watchlist IDs');
  const emptySaved = buildVisibleRotationView({ ...source, savedThemeIds: new Set() }, state({ universe: 'saved' }));
  assert(emptySaved.counts.plotted === 0, 'empty saved state is valid');
  const custom = buildVisibleRotationView(source, state({ selectedThemeIds: ['theme_4', 'theme_2'], universe: 'custom' }));
  assert(custom.visibleThemes.map((point) => point.themeId).join(',') === 'theme_2,theme_4', 'Custom Selection filters source rows without mutating source order');

  const search = searchThemeOptions([...metadata, metadata[0], { ...metadata[1], id: 'retired', taxonomyStatus: 'retired' }], 'zero-alias');
  assert(search.length === 1 && search[0].id === 'theme_0', 'search resolves aliases, normalizes punctuation, deduplicates IDs, and excludes retired themes');
  assert(toggleThemeSelection(['theme_2'], 'theme_4').join(',') === 'theme_2,theme_4', 'multi-select preserves stable insertion order');
  assert(toggleThemeSelection(['theme_2', 'theme_4'], 'theme_2').join(',') === 'theme_4', 'multi-select removes one canonical ID without duplication');
  assert(selectAllThemeOptions(['theme_2'], ['theme_1', 'theme_2', 'theme_3']).join(',') === 'theme_2,theme_1,theme_3', 'Select all visible preserves existing order and deduplicates');
  assert(Boolean(selectionReadabilityWarning(9, true)) && !selectionReadabilityWarning(8, true), 'mobile selection soft warning starts above 8 without hard failure');

  const compare = buildVisibleRotationView(source, state({ labelMode: 'selected', mode: 'compare', selectedThemeIds: ['theme_2', 'theme_4'], tailLength: '8' }));
  assert(compare.counts.plotted === 2 && compare.counts.labels === 2, 'Compare shows and labels only explicitly selected themes');
  assert(compare.visibleThemes.every((point) => point.history.length === 8), 'Compare supports longer genuine tails');
  const compareEight = buildVisibleRotationView(source, state({ labelMode: 'selected', mode: 'compare', selectedThemeIds: points.slice(0, 8).map((point) => point.themeId), tailLength: 'full' }));
  assert(compareEight.counts.plotted === 8 && compareEight.renderedLabels.length === 8, 'Compare supports the recommended 8-theme set');
  const compareAfterOneRemoval = removeThemeFromComparison(state({ mode: 'compare', selectedThemeIds: ['theme_0', 'theme_1', 'theme_2'], tailLength: '8' }), 'theme_0', true);
  assert(compareAfterOneRemoval.mode === 'compare' && compareAfterOneRemoval.selectedThemeIds.length === 2, 'Compare remains active after removing one of three selected themes');
  const compareExit = removeThemeFromComparison(compareAfterOneRemoval, 'theme_1', true);
  assert(compareExit.mode === 'overview' && compareExit.tailLength === '3' && compareExit.selectedThemeIds.length === 1, 'Compare exits cleanly when fewer than two themes remain');

  const related = resolveRelatedThemeIds('theme_0', metadata, source.overlap);
  assert(related.includes('theme_5') && related.includes('theme_4'), 'related themes use shared canonical parents and transparent constituent overlap');
  const focus = buildVisibleRotationView(source, state({ focusedThemeId: 'theme_0', labelMode: 'selected', mode: 'focus', movement: 'stable', quadrant: 'lagging', tailLength: 'full' }));
  assert(focus.focusedTheme?.themeId === 'theme_0' && focus.focusedTheme.history.length === 10, 'Focus restores and emphasizes one full canonical tail');
  assert(focus.visibleThemes.find((point) => point.themeId === 'theme_1')?.viewOpacity === 0.15, 'Focus default retains faint non-color context');
  assert(focus.visibleThemes.filter((point) => !point.isFocused).every((point) => point.history.length === 1), 'Focus context uses faint current points rather than competing full tails');
  assert(focus.counts.labels === 1, 'Selected labels include the focused theme only when no comparison set exists');
  const focusFromCompare = buildVisibleRotationView(source, state({ focusedThemeId: 'theme_0', labelMode: 'selected', mode: 'focus', selectedThemeIds: ['theme_0', 'theme_1', 'theme_2'] }));
  assert(focusFromCompare.renderedLabels.join(',') === 'theme_0', 'Focus Selected labels keep the inspected theme readable while preserving the comparison selection');
  const hiddenFocus = buildVisibleRotationView(source, state({ focusContext: 'hidden', focusedThemeId: 'theme_0', mode: 'focus', showRelatedThemes: false }));
  assert(hiddenFocus.counts.plotted === 1, 'Focus hidden-context setting removes other presentation points');
  const relatedFocus = buildVisibleRotationView(source, state({ focusContext: 'hidden', focusedThemeId: 'theme_0', mode: 'focus', showRelatedThemes: true }));
  assert(relatedFocus.counts.plotted > 1 && relatedFocus.visibleThemes.every((point) => point.isFocused || point.isRelated), 'Show related themes restores only deterministic related context when context is hidden');

  (['all', 'leading', 'improving', 'weakening', 'lagging'] as const).forEach((quadrant) => {
    const view = buildVisibleRotationView(source, state({ quadrant }));
    assert(quadrant === 'all' ? view.counts.plotted === 10 : view.visibleThemes.every((point) => point.quadrant === quadrant), `${quadrant} filters whole tails by current endpoint`);
  });
  const trailCounts = { current: 1, '3': 3, '5': 5, '8': 8, full: 10 } as const;
  Object.entries(trailCounts).forEach(([tailLength, count]) => {
    const view = buildVisibleRotationView(source, state({ tailLength: tailLength as ThemeRotationViewState['tailLength'] }));
    assert(view.visibleThemes.every((point) => point.history.length === count), `${tailLength} tail slices genuine observations without interpolation`);
  });
  const shortSource = { ...source, rotation: { ...rotation, points: [{ ...points[0], history: points[0].history.slice(-2) }] } };
  assert(buildVisibleRotationView(shortSource, state({ tailLength: '8' })).visibleThemes[0].history.length === 2, 'insufficient tails are not invented');

  const meaningful = buildVisibleRotationView(source, state({ movement: 'meaningful' }));
  const fast = buildVisibleRotationView(source, state({ movement: 'fast' }));
  const stable = buildVisibleRotationView(source, state({ movement: 'stable' }));
  assert(meaningful.counts.plotted > 0 && meaningful.counts.plotted < 10, 'Meaningful uses governed speed/displacement medians or a canonical transition');
  assert(fast.visibleThemes.map((point) => point.themeId).join(',') === 'theme_8,theme_9', 'Fast Movers is the deterministic top 20% by canonical speed');
  assert(stable.visibleThemes.every((point) => point.latestQuadrantTransition?.changed === false), 'Stable is the deterministic bottom 20% with no recent transition');
  assert(THEME_ROTATION_VIEW_POLICY.version === 'theme-rotation-view-policy-v1', 'movement policy thresholds are versioned');

  const transitionCases = [
    ['entered_leading', (point: CanonicalThemeRotationPoint) => point.quadrant === 'leading' && point.previousQuadrant !== 'leading'],
    ['entered_improving', (point: CanonicalThemeRotationPoint) => point.quadrant === 'improving' && point.previousQuadrant !== 'improving'],
    ['lost_leading', (point: CanonicalThemeRotationPoint) => point.previousQuadrant === 'leading' && point.quadrant !== 'leading'],
    ['quadrant_changed', (point: CanonicalThemeRotationPoint) => point.latestQuadrantTransition?.changed === true],
    ['no_recent_change', (point: CanonicalThemeRotationPoint) => point.latestQuadrantTransition?.changed === false],
  ] as const;
  transitionCases.forEach(([transition, predicate]) => {
    const view = buildVisibleRotationView(source, state({ transition }));
    assert(view.visibleThemes.every(predicate), `${transition} uses the canonical latest transition`);
    assert(!view.visibleThemes.some((point) => point.themeId === 'theme_9'), `${transition} excludes insufficient previous history`);
  });

  const pointCount = buildVisibleRotationView(source, state({ labelMode: 'smart' })).counts.plotted;
  (['smart', 'selected', 'all', 'none'] as const).forEach((labelMode) => {
    const view = buildVisibleRotationView(source, state({ focusedThemeId: 'theme_0', labelMode, selectedThemeIds: ['theme_1'] }));
    assert(view.counts.plotted === pointCount, `${labelMode} label mode does not change point count`);
  });
  const smart = buildVisibleRotationView(source, state({ labelMode: 'smart', smartLabelLimit: 3 }));
  assert(smart.renderedLabels.includes('theme_1'), 'Smart label ranking prioritizes saved themes');
  const focusedSmart = buildVisibleRotationView(source, state({ focusedThemeId: 'theme_9', labelMode: 'smart', mode: 'focus', smartLabelLimit: 1 }));
  assert(focusedSmart.renderedLabels[0] === 'theme_9', 'Smart label ranking prioritizes the focused theme');

  const unavailableMetadata = [...metadata, { aliases: ['not available'], id: 'theme_unavailable', name: 'Unavailable Theme', parentSectorIds: ['information_technology'], rank: null, status: 'unavailable', taxonomyStatus: 'active' }];
  const unavailableSelected = buildVisibleRotationView({ ...source, metadata: unavailableMetadata }, state({ selectedThemeIds: ['theme_unavailable'], universe: 'custom' }));
  assert(unavailableSelected.counts.selected === 1 && unavailableSelected.counts.plotted === 0 && unavailableSelected.counts.unavailableByEvidence === 1, 'selected unavailable themes remain explicit but never plot invalid coordinates');

  assert(rotation.points[0].history.length === 10 && rotation.points.length === 10, 'selector leaves the canonical source immutable');
}

run();
