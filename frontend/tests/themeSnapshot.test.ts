import { getThemeSnapshot } from '../src/services/api';
import { adaptThemeSnapshot } from '../src/features/themes/themeSnapshot';
import { clearRequestCache } from '../src/services/requestCache';

function assert(condition: unknown, message: string) {
  if (!condition) throw new Error(message);
}

async function run() {
  const snapshot = adaptThemeSnapshot({
    snapshot_id: 'theme-live-1', market_date: '2026-07-18', source_state: 'live', status: 'complete',
    items: [{ theme_id: 'memory-storage', display_name: 'Memory & Storage', rank: 1, composite_score: 77.1, coverage_ratio: 1,
      definition: { parent_sector_ids: ['information_technology'] }, performance: { '1d': 1, '1w': 2, '1m': 3, '3m': 4, '6m': 5, '1y': 6 },
      participation: { positive_return_member_count: 6, negative_return_member_count: 1, positive_return_participation_pct: 85.7, positive_contribution_share_pct: 92.2, participation_horizon: '1m', participation_score: 80, formula_version: 'positive-return-and-contribution-v1' }, concentration: { top_one_absolute_contribution_share_pct: 42.1, top_three_absolute_contribution_share_pct: 77.3, concentration_hhi: .25, classification: 'moderate', concentration_quality_score: 75 }, score_semantics: { score_type: 'absolute_weighted_composite', display_label: 'Absolute composite score', scale: '0-100' }, classification: 'Improving',
      provenance: { source_state: 'live' }, warnings: [], rotation_series: { '1W': { current_point: { market_date: '2026-07-18', plotted_x: 103, plotted_y: 102, is_synthetic: false }, trail_points: [{ market_date: '2026-07-14', plotted_x: 100, plotted_y: 101, is_synthetic: false }, { market_date: '2026-07-18', plotted_x: 103, plotted_y: 102, is_synthetic: false }] }, '1M': { current_point: { market_date: '2026-07-18', plotted_x: 103, plotted_y: 102, is_synthetic: false }, trail_points: [{ market_date: '2026-07-18', plotted_x: 103, plotted_y: 102, is_synthetic: false }] }, '3M': { current_point: { market_date: '2026-07-18', plotted_x: 103, plotted_y: 102, is_synthetic: false }, trail_points: [{ market_date: '2026-07-18', plotted_x: 103, plotted_y: 102, is_synthetic: false }] } },
    }], alerts: [], warnings: [],
  });
  assert(snapshot?.items[0].returns['6M'] === 5 && snapshot.items[0].returns['1Y'] === 6, 'theme adapter preserves every heatmap interval');
  assert(snapshot?.items[0].id === 'memory_storage', 'legacy kebab-case snapshot IDs normalize to the canonical snake_case ID');
  assert(snapshot?.items[0].rotation['1W'].history.length === 2 && snapshot.items[0].rotation['1W'].history.every((point) => !point.isSynthetic), 'theme rotation uses published durable basket tails');
  assert(snapshot?.items[0].participation.score === 80 && snapshot.items[0].participation.positiveReturnParticipationPct === 85.7, 'Theme adapter keeps participation raw metrics distinct from score');
  assert(snapshot?.items[0].concentration.hhi === .25 && snapshot.items[0].concentration.qualityScore === 75, 'Theme adapter keeps concentration raw metrics distinct from quality score');
  assert(snapshot?.items[0].scoreSemantics.label === 'Absolute composite score', 'Theme adapter preserves honest absolute score semantics');

  const originalFetch = globalThis.fetch; let calls = 0;
  globalThis.fetch = (async () => { calls += 1; return new Response(JSON.stringify(snapshot), { status: 200 }); }) as typeof fetch;
  try {
    clearRequestCache('theme-snapshot:');
    await Promise.all([getThemeSnapshot(), getThemeSnapshot()]);
    assert(calls === 1, 'repeated ThemeSnapshot mounts dedupe the request');
  } finally {
    clearRequestCache('theme-snapshot:'); globalThis.fetch = originalFetch;
  }
}

void run();
