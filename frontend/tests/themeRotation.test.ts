import { calculateRotationDomain, classifyQuadrant } from '../src/data/sectorTabTestData';
import {
  buildRotationVisibilitySummary,
  filterRotationItemsByQuadrant,
  getSmartRotationLabelLimit,
  selectSmartLabelKeys,
  type RotationLabelCandidate,
} from '../src/features/sectors/analysis/rotationLabels';
import {
  adaptThemeRotation,
  themeRotationCacheKey,
} from '../src/features/themes/themeRotation';
import { getThemeRotation } from '../src/services/api';
import { clearRequestCache } from '../src/services/requestCache';

function assert(condition: unknown, message: string) {
  if (!condition) throw new Error(message);
}

const THEME_IDS = [
  'artificial_intelligence', 'semiconductors', 'memory_storage', 'data_centers', 'cloud_computing',
  'enterprise_software', 'cybersecurity', 'networking_infrastructure', 'robotics_automation',
  'digital_advertising', 'ecommerce', 'digital_payments', 'online_travel', 'gaming_interactive_media',
  'streaming_digital_entertainment', 'aerospace_defense', 'space_economy', 'drones_autonomous_systems',
  'nuclear_energy', 'grid_modernization', 'clean_energy', 'electric_vehicles_batteries', 'biotechnology',
  'obesity_metabolic_health', 'medical_technology', 'cryptocurrency_infrastructure',
] as const;

function payload(timeframe: '1W' | '1M' | '3M', snapshotId = 'theme-live-26') {
  const profile = timeframe === '1W' ? 'short' : timeframe === '1M' ? 'medium' : 'long';
  return {
    snapshot_id: snapshotId,
    taxonomy_version: '2026.07.1',
    as_of: '2026-07-22T21:00:00Z',
    timeframe,
    profile,
    rotation_model_version: 'theme-relative-trend-momentum-v1',
    status: 'available',
    snapshot_status: 'partial',
    benchmark: 'SPY',
    eligible_count: 26,
    excluded_count: 0,
    exclusions: [],
    latest_common_date: '2026-07-22',
    timeframe_definition: { fast_trend_ema: timeframe === '1W' ? 10 : timeframe === '1M' ? 20 : 10 },
    points: THEME_IDS.map((themeId, index) => {
      const x = 96 + (index % 8) + (timeframe === '3M' ? 0.5 : timeframe === '1W' ? -0.5 : 0);
      const y = 96 + (index % 7);
      return {
        theme_id: themeId,
        display_name: `Theme ${index + 1}`,
        taxonomy_version: '2026.07.1',
        snapshot_id: snapshotId,
        as_of: '2026-07-22',
        timeframe,
        profile,
        model_version: 'theme-relative-trend-momentum-v1',
        status: 'available',
        confidence: { label: 'moderate' },
        relative_trend: x,
        relative_momentum: y,
        previous_relative_trend: x - 0.25,
        previous_momentum_normalized: y - 0.25,
        quadrant: classifyQuadrant(x, y),
        trajectory: 'improving',
        direction: 'north-east',
        speed: index + 1,
        distance_travelled: index + 2,
        net_displacement: index + 0.5,
        recent_acceleration: 0.25,
        quadrant_transitions: 1,
        previous_quadrant: classifyQuadrant(x - 0.25, y - 0.25),
        latest_quadrant_transition: {
          from: classifyQuadrant(x - 0.25, y - 0.25),
          to: classifyQuadrant(x, y),
          changed: classifyQuadrant(x - 0.25, y - 0.25) !== classifyQuadrant(x, y),
          as_of: '2026-07-22',
        },
        coverage_ratio: index < 6 ? 0.8 : 1,
        evidence_references: [`theme:${index + 1}:evidence`],
        missing_data: [],
        ranking_eligible: true,
        rank: index + 1,
        label_priority: 10_000 - index,
        partial_coverage_disclosure: index < 6 ? 'Available with partial coverage disclosure.' : null,
        trail_points: [
          { market_date: '2026-07-21', relative_trend: x - 0.25, relative_momentum: y - 0.25, is_synthetic: false },
          { market_date: '2026-07-22', relative_trend: x, relative_momentum: y, is_synthetic: false },
        ],
      };
    }),
  };
}

async function run() {
  const rotation = adaptThemeRotation(payload('1M'));
  assert(rotation?.points.length === 26, 'canonical adapter preserves all 26 eligible themes');
  assert(rotation?.eligibleCount === 26 && rotation.excludedCount === 0, 'canonical response counts are preserved');
  assert(rotation?.snapshotStatus === 'partial' && rotation.status === 'available', 'global partial status does not hide available rows');
  assert(rotation?.points.filter((point) => point.partialCoverageDisclosure).length === 6, 'partial coverage disclosure does not exclude points');
  assert(new Set(rotation?.points.map((point) => point.themeId)).size === 26, 'canonical IDs do not collapse or duplicate rows');
  assert(rotation?.points.every((point) => point.relativeTrend !== 0 && point.relativeMomentum !== 0), 'valid normalized values are not zero-filled');
  assert(rotation?.points[4].speed === 5 && rotation.points[4].distanceTravelled === 6 && rotation.points[4].latestQuadrantTransition?.asOf === '2026-07-22', 'adapter preserves governed movement and latest transition metrics without recalculation');
  const invalid = payload('1M');
  invalid.points[0].relative_trend = Number.NaN;
  const withoutInvalid = adaptThemeRotation(invalid);
  assert(withoutInvalid?.points.length === 25, 'N/A metrics are omitted rather than converted to zero');

  const candidates: RotationLabelCandidate[] = (rotation?.points ?? []).map((point) => ({
    fullName: point.displayName,
    history: point.history,
    id: point.themeId,
    key: `theme:${point.themeId}`,
    latest: point.history[point.history.length - 1],
    priority: point.labelPriority,
    shortName: point.displayName,
    type: 'theme',
  }));
  const smartLimit = getSmartRotationLabelLimit(300, 'card');
  const smart = selectSmartLabelKeys(candidates, { labelMode: 'smart', maxLabelCount: smartLimit });
  const all = selectSmartLabelKeys(candidates, { labelMode: 'all', maxLabelCount: 8 });
  const none = selectSmartLabelKeys(candidates, { labelMode: 'none', maxLabelCount: 8 });
  assert(candidates.length === 26 && smart.size === 6, 'Smart selects six labels without changing the 26 point candidates');
  assert(smartLimit === 6, 'default Theme Rotation card renders six deterministic Smart labels');
  assert(all.size === 26 && candidates.length === 26, 'All attempts all labels without changing points');
  assert(none.size === 0 && candidates.length === 26, 'None hides labels without changing points');
  assert(buildRotationVisibilitySummary({ filtered: 26, labels: smart.size, mode: 'smart', quadrantFilter: 'all', total: 26 }) === '26 points shown · 6 labels shown', 'Smart footer count is accurate');
  assert(buildRotationVisibilitySummary({ filtered: 26, labels: 26, mode: 'all', quadrantFilter: 'all', total: 26 }) === '26 points shown · 26 labels shown', 'All footer count is accurate');
  assert(buildRotationVisibilitySummary({ filtered: 26, labels: 0, mode: 'none', quadrantFilter: 'all', total: 26 }) === '26 points shown · 0 labels shown', 'None footer count is accurate');
  (['leading', 'improving', 'weakening', 'lagging'] as const).forEach((quadrant) => {
    const filtered = filterRotationItemsByQuadrant(candidates, quadrant);
    assert(filtered.every((item) => classifyQuadrant(item.latest.relativeStrength, item.latest.relativeMomentum) === quadrant), `${quadrant} filter contains only matching points`);
  });
  assert(filterRotationItemsByQuadrant(candidates, 'all').length === 26, 'All quadrant restores all canonical points');
  const robustDomain = calculateRotationDomain([
    ...candidates.flatMap((item) => item.history),
    { dateLabel: 'Extreme', relativeStrength: 240, relativeMomentum: -40 },
  ]);
  assert(robustDomain.scalePolicy === 'all-valid-centered-100-padded-v1', 'rotation domain exposes deterministic all-point metadata');
  assert(robustDomain.xMax > 240 && robustDomain.yMin < -40, 'all valid outliers remain inside the plotted domain without silent clipping');

  const oneMonth = adaptThemeRotation(payload('1M'));
  const threeMonth = adaptThemeRotation(payload('3M'));
  assert(oneMonth?.timeframe === '1M' && threeMonth?.timeframe === '3M', 'timeframe changes retain independent response identities');
  assert(oneMonth?.points[0].relativeTrend !== threeMonth?.points[0].relativeTrend, 'profile change does not reuse stale metrics');
  assert(themeRotationCacheKey('1M', { snapshotId: 'snapshot-a', taxonomyVersion: '2026.07.1' }) === 'theme-rotation:2026.07.1:snapshot-a:theme-relative-trend-momentum-v1:1M', 'cache key includes taxonomy, snapshot, model, and profile alias');

  const originalFetch = globalThis.fetch;
  const urls: string[] = [];
  globalThis.fetch = (async (input) => {
    const url = String(input);
    urls.push(url);
    const timeframe = url.includes('profile=long') ? '3M' : '1M';
    const snapshotId = urls.length === 3 ? 'snapshot-b' : 'snapshot-a';
    return new Response(JSON.stringify(payload(timeframe, snapshotId)), { status: 200 });
  }) as typeof fetch;
  try {
    clearRequestCache('theme-rotation:');
    const firstIdentity = { snapshotId: 'snapshot-a', taxonomyVersion: '2026.07.1' };
    await Promise.all([getThemeRotation('1M', firstIdentity), getThemeRotation('1M', firstIdentity)]);
    await getThemeRotation('3M', firstIdentity);
    await getThemeRotation('1M', { ...firstIdentity, snapshotId: 'snapshot-b' });
    assert(urls.length === 3, 'identical canonical requests dedupe while timeframe and snapshot changes fetch independently');
    assert(urls.some((url) => url.includes('profile=medium')) && urls.some((url) => url.includes('profile=long')), 'retrieval seam requests the selected canonical profile');
  } finally {
    clearRequestCache('theme-rotation:');
    globalThis.fetch = originalFetch;
  }
}

void run();
