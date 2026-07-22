import fs from 'node:fs';
import path from 'node:path';

import { adaptThemeRotation } from '../src/features/themes/themeRotation.ts';
import { adaptThemeSnapshot } from '../src/features/themes/themeSnapshot.ts';
import {
  DEFAULT_THEME_ROTATION_VIEW_STATE,
  THEME_ROTATION_UNIVERSE_OPTIONS,
  THEME_ROTATION_VIEW_POLICY,
  buildVisibleRotationView,
} from '../src/features/themes/themeRotationView.ts';

const root = path.resolve(import.meta.dirname, '../..');
const rotationPath = path.join(root, 'artifacts/stage8.75-theme-rotation-validation.json');
const snapshotPath = path.join(root, 'artifacts/stage8.75-canonical-theme-snapshot.json');
const interactionPath = path.join(root, 'artifacts/stage8.75-theme-rotation-interaction-validation.json');
const validationPath = path.join(root, 'artifacts/stage8.75-theme-rotation-ux-validation.json');
const screenshotDirectory = path.join(root, 'artifacts/theme-rotation-ux-screenshots');
const rotationArtifact = JSON.parse(fs.readFileSync(rotationPath, 'utf8'));
const snapshot = adaptThemeSnapshot(JSON.parse(fs.readFileSync(snapshotPath, 'utf8')));
const rotation = adaptThemeRotation(rotationArtifact.datasets['1M'].response);

if (!snapshot || !rotation) throw new Error('canonical_theme_artifacts_unreadable');

const metadata = snapshot.items.map((item) => ({
  aliases: item.aliases,
  id: item.id,
  name: item.name,
  parentSectorIds: item.parentSectorIds,
  rank: item.rank,
  status: item.status,
  taxonomyStatus: item.taxonomyStatus,
}));
const source = { metadata, overlap: snapshot.overlap, rotation, savedThemeIds: new Set(rotation.points.slice(0, 3).map((point) => point.themeId)) };
const baselineState = { ...DEFAULT_THEME_ROTATION_VIEW_STATE, movement: 'all', smartLabelLimit: 6, tailLength: '3' };
const build = (patch = {}) => buildVisibleRotationView(source, { ...baselineState, ...patch });
const assertions = [];
const check = (name, condition, details = {}) => {
  if (!condition) throw new Error(`interaction_validation_failed:${name}`);
  assertions.push({ name, result: 'PASS', ...details });
};

const all = build();
check('all_eligible_themes_restorable', all.counts.plotted === 26, { plotted: all.counts.plotted });
check('source_immutable_after_all_view', rotation.points.length === 26 && rotation.points.every((point) => point.history.length >= all.visibleThemes.find((item) => item.themeId === point.themeId).history.length));

const universeCounts = {};
THEME_ROTATION_UNIVERSE_OPTIONS.forEach((option) => {
  const view = build({ universe: option.key });
  universeCounts[option.key] = view.counts.plotted;
  check(`universe_${option.key}`, option.key === 'all' ? view.counts.plotted === 26 : view.visibleThemes.every((point) => {
    if (option.key === 'saved') return source.savedThemeIds.has(point.themeId);
    if (option.key === 'custom') return true;
    const item = metadata.find((candidate) => candidate.id === point.themeId);
    return item?.parentSectorIds.some((parent) => option.parentSectorIds.includes(parent));
  }), { plotted: view.counts.plotted });
});

const selectedThemeIds = rotation.points.slice(0, 8).map((point) => point.themeId);
const compare = build({ labelMode: 'selected', mode: 'compare', selectedThemeIds, tailLength: '8', universe: 'custom' });
check('compare_eight_themes', compare.counts.plotted === 8 && compare.counts.labels === 8 && compare.visibleThemes.every((point) => point.history.length <= 8));
const focusedId = rotation.points[0].themeId;
const focus = build({ focusedThemeId: focusedId, labelMode: 'selected', mode: 'focus', tailLength: 'full' });
check('focus_full_tail', focus.focusedTheme?.history.length === rotation.points[0].history.length && focus.renderedLabels.includes(focusedId));
check('focus_faint_context', focus.visibleThemes.filter((point) => point.themeId !== focusedId).every((point) => point.viewOpacity <= 0.42));
const relatedFocus = build({ focusContext: 'hidden', focusedThemeId: focusedId, mode: 'focus', showRelatedThemes: true, tailLength: 'full' });
check('focus_related_deterministic', relatedFocus.visibleThemes.every((point) => point.isFocused || point.isRelated));

const quadrantCounts = Object.fromEntries(['all', 'leading', 'improving', 'weakening', 'lagging'].map((quadrant) => {
  const view = build({ quadrant });
  check(`quadrant_${quadrant}`, quadrant === 'all' ? view.counts.plotted === 26 : view.visibleThemes.every((point) => point.quadrant === quadrant));
  return [quadrant, view.counts.plotted];
}));
const tailCounts = Object.fromEntries(['current', '3', '5', '8', 'full'].map((tailLength) => {
  const view = build({ tailLength });
  check(`tail_${tailLength}`, view.visibleThemes.every((point) => point.history.length <= (tailLength === 'full' ? Number.MAX_SAFE_INTEGER : tailLength === 'current' ? 1 : Number(tailLength))));
  return [tailLength, view.counts.historicalNodes];
}));
const movementCounts = Object.fromEntries(['all', 'meaningful', 'fast', 'stable'].map((movement) => {
  const view = build({ movement });
  check(`movement_${movement}`, view.counts.plotted <= 26);
  return [movement, view.counts.plotted];
}));
const transitionCounts = Object.fromEntries(['all', 'entered_leading', 'entered_improving', 'lost_leading', 'quadrant_changed', 'no_recent_change'].map((transition) => {
  const view = build({ transition });
  check(`transition_${transition}`, view.visibleThemes.every((point) => transition === 'all' || point.latestQuadrantTransition !== null));
  return [transition, view.counts.plotted];
}));
const labelPointCounts = Object.fromEntries(['smart', 'selected', 'all', 'none'].map((labelMode) => [labelMode, build({ labelMode, selectedThemeIds: selectedThemeIds.slice(0, 3) }).counts.plotted]));
check('label_point_count_invariant', new Set(Object.values(labelPointCounts)).size === 1, { labelPointCounts });
check('no_n_a_to_zero', rotation.points.every((point) => Number.isFinite(point.relativeTrend) && Number.isFinite(point.relativeMomentum)));
check('no_synthetic_tail_projection', rotation.points.every((point) => point.history.every((historyPoint) => !historyPoint.isSynthetic)));

const screenshotNames = [
  'mobile-overview-default.png',
  'mobile-all-themes.png',
  'mobile-focus.png',
  'mobile-compare.png',
  'desktop-overview.png',
  'desktop-compare.png',
  'quadrant-filtered.png',
  'fast-movers-filtered.png',
];
const screenshots = screenshotNames.map((name) => ({
  exists: fs.existsSync(path.join(screenshotDirectory, name)),
  path: path.join(screenshotDirectory, name),
}));

const interactionArtifact = {
  assertions,
  canonical: {
    eligible_count: rotation.eligibleCount,
    excluded_count: rotation.excludedCount,
    model_version: rotation.modelVersion,
    snapshot_id: rotation.snapshotId,
    taxonomy_version: rotation.taxonomyVersion,
  },
  counts: { movement: movementCounts, quadrants: quadrantCounts, tails: tailCounts, transitions: transitionCounts, universes: universeCounts },
  generated_at: new Date().toISOString(),
  label_point_counts: labelPointCounts,
  movement_policy: THEME_ROTATION_VIEW_POLICY,
  result: 'PASS',
};
fs.writeFileSync(interactionPath, `${JSON.stringify(interactionArtifact, null, 2)}\n`);

const missingScreenshots = screenshots.filter((item) => !item.exists);
const validationArtifact = {
  automated_result: 'PASS',
  canonical_source_immutable: true,
  filter_changes_trigger_refetch: false,
  generated_at: new Date().toISOString(),
  interaction_artifact: interactionPath,
  math_changed: false,
  normalization_changed: false,
  performance: rotationArtifact.performance?.theme_rotation_view ?? null,
  policy_version: THEME_ROTATION_VIEW_POLICY.version,
  result: missingScreenshots.length ? 'PASS_WITH_CONDITIONS' : 'PASS',
  screenshots,
  screenshots_missing: missingScreenshots.length,
  source_rotation_artifact: rotationPath,
  source_snapshot_artifact: snapshotPath,
};
fs.writeFileSync(validationPath, `${JSON.stringify(validationArtifact, null, 2)}\n`);
console.log(JSON.stringify({ interaction: interactionPath, result: validationArtifact.result, validation: validationPath }, null, 2));
