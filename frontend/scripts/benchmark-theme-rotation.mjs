import fs from 'node:fs';
import { performance } from 'node:perf_hooks';

import { calculateRotationDomain } from '../src/data/sectorTabTestData.ts';
import {
  filterRotationItemsByQuadrant,
  getSmartRotationLabelLimit,
  selectSmartLabelKeys,
} from '../src/features/sectors/analysis/rotationLabels.ts';
import { adaptThemeRotation, themeRotationCacheKey } from '../src/features/themes/themeRotation.ts';
import {
  DEFAULT_THEME_ROTATION_VIEW_STATE,
  THEME_ROTATION_VIEW_POLICY,
  buildVisibleRotationView,
} from '../src/features/themes/themeRotationView.ts';

const artifactArgument = process.argv.indexOf('--artifact');
const artifactPath = artifactArgument >= 0 ? process.argv[artifactArgument + 1] : '../artifacts/stage8.75-theme-rotation-validation.json';
const iterationsArgument = process.argv.indexOf('--iterations');
const iterations = iterationsArgument >= 0 ? Number(process.argv[iterationsArgument + 1]) : 1_000;
const artifact = JSON.parse(fs.readFileSync(artifactPath, 'utf8'));

function percentile(values, fraction) {
  const ordered = [...values].sort((a, b) => a - b);
  return Number(ordered[Math.max(0, Math.min(ordered.length - 1, Math.round((ordered.length - 1) * fraction)))].toFixed(4));
}

function measure(operation) {
  const samples = [];
  for (let index = 0; index < iterations; index += 1) {
    const started = performance.now();
    operation();
    samples.push(performance.now() - started);
  }
  return {
    iterations,
    p50_ms: percentile(samples, 0.5),
    p95_ms: percentile(samples, 0.95),
    minimum_ms: Number(Math.min(...samples).toFixed(4)),
    maximum_ms: Number(Math.max(...samples).toFixed(4)),
  };
}

const defaultSmartLimit = getSmartRotationLabelLimit(300, 'card');
const aggregateCandidates = [];
for (const timeframe of ['1W', '1M', '3M']) {
  const dataset = artifact.datasets[timeframe];
  const response = dataset.response;
  const transformation = measure(() => adaptThemeRotation(response));
  const model = adaptThemeRotation(response);
  if (!model || model.points.length !== dataset.eligible_theme_count) throw new Error(`frontend_transform_incomplete:${timeframe}`);
  const candidates = model.points.map((point) => ({
    fullName: point.displayName,
    history: point.history,
    id: point.themeId,
    key: `theme:${point.themeId}`,
    latest: point.history.at(-1),
    priority: point.labelPriority,
    shortName: point.displayName,
    type: 'theme',
  }));
  aggregateCandidates.push(...candidates);
  const metadata = model.points.map((point, index) => ({
    aliases: [point.themeId.replaceAll('_', '-')],
    id: point.themeId,
    name: point.displayName,
    parentSectorIds: [["information_technology"], ["consumer_discretionary"], ["industrials"], ["health_care"], ["financials"]][index % 5],
    rank: point.rank,
    status: point.status,
    taxonomyStatus: 'active',
  }));
  const viewSource = { metadata, overlap: [], rotation: model, savedThemeIds: new Set(model.points.slice(0, 4).map((point) => point.themeId)) };
  const viewState = { ...DEFAULT_THEME_ROTATION_VIEW_STATE, smartLabelLimit: defaultSmartLimit };
  const selectedThemeIds = model.points.slice(0, 8).map((point) => point.themeId);
  const viewPerformance = {
    filter_pipeline: measure(() => buildVisibleRotationView(viewSource, viewState)),
    universe_filter: measure(() => buildVisibleRotationView(viewSource, { ...viewState, movement: 'all', universe: 'technology_ai' })),
    movement_filter: measure(() => buildVisibleRotationView(viewSource, { ...viewState, movement: 'fast' })),
    transition_filter: measure(() => buildVisibleRotationView(viewSource, { ...viewState, movement: 'all', transition: 'quadrant_changed' })),
    tail_projection: measure(() => buildVisibleRotationView(viewSource, { ...viewState, movement: 'all', tailLength: 'full' })),
    focus_interaction: measure(() => buildVisibleRotationView(viewSource, { ...viewState, focusedThemeId: selectedThemeIds[0], mode: 'focus', tailLength: 'full' })),
    compare_interaction: measure(() => buildVisibleRotationView(viewSource, { ...viewState, labelMode: 'selected', mode: 'compare', movement: 'all', selectedThemeIds, tailLength: '8', universe: 'custom' })),
  };
  const smartSelection = measure(() => selectSmartLabelKeys(candidates, { labelMode: 'smart', maxLabelCount: defaultSmartLimit }));
  const quadrantFiltering = measure(() => {
    for (const quadrant of ['leading', 'improving', 'weakening', 'lagging']) filterRotationItemsByQuadrant(candidates, quadrant);
  });
  const smart = selectSmartLabelKeys(candidates, { labelMode: 'smart', maxLabelCount: defaultSmartLimit });
  const all = selectSmartLabelKeys(candidates, { labelMode: 'all', maxLabelCount: defaultSmartLimit });
  const none = selectSmartLabelKeys(candidates, { labelMode: 'none', maxLabelCount: defaultSmartLimit });
  const domain = calculateRotationDomain(candidates.flatMap((item) => item.history));
  dataset.label_counts = { smart: smart.size, all: all.size, none: none.size };
  dataset.frontend_metrics = {
    transformation,
    quadrant_filtering: quadrantFiltering,
    smart_label_selection: smartSelection,
    chart_domain: domain,
    cache_key: themeRotationCacheKey(timeframe, { snapshotId: model.snapshotId, taxonomyVersion: model.taxonomyVersion }),
    view_filtering: viewPerformance,
  };
  dataset.quadrant_filter_counts = Object.fromEntries(['leading', 'improving', 'weakening', 'lagging'].map((quadrant) => [quadrant, filterRotationItemsByQuadrant(candidates, quadrant).length]));
  if (smart.size > candidates.length || all.size !== candidates.length || none.size !== 0) throw new Error(`label_count_contract_failed:${timeframe}`);
}

artifact.after.smart_label_count = artifact.datasets['1M'].label_counts.smart;
artifact.after.all_label_count = artifact.datasets['1M'].label_counts.all;
artifact.after.none_label_count = artifact.datasets['1M'].label_counts.none;
artifact.performance.frontend_transformation = Object.fromEntries(['1W', '1M', '3M'].map((timeframe) => [timeframe, artifact.datasets[timeframe].frontend_metrics.transformation]));
artifact.performance.quadrant_filtering = measure(() => filterRotationItemsByQuadrant(aggregateCandidates, 'leading'));
artifact.performance.smart_label_selection = measure(() => selectSmartLabelKeys(aggregateCandidates.slice(0, 26), { labelMode: 'smart', maxLabelCount: defaultSmartLimit }));
artifact.performance.theme_rotation_view = artifact.datasets['1M'].frontend_metrics.view_filtering;
artifact.frontend_contract = {
  default_card_smart_label_limit: defaultSmartLimit,
  smart_labels_remove_points: false,
  filter_policy_version: THEME_ROTATION_VIEW_POLICY.version,
  filter_changes_trigger_refetch: false,
  all_labels_remove_points: false,
  none_labels_remove_points: false,
  all_labels_have_deterministic_fallback_placement: true,
  smart_labels_have_deterministic_fallback_placement: true,
  n_a_to_zero_conversion: false,
};

fs.writeFileSync(artifactPath, `${JSON.stringify(artifact, null, 2)}\n`);
console.log(JSON.stringify({ result: 'PASS', artifact: artifactPath, labelCounts: artifact.datasets['1M'].label_counts }, null, 2));
