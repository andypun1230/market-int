import {
  DEFAULT_CANONICAL_GROUP_FILTERS,
  comparisonSelectionLimit,
  countCanonicalGroupFilters,
  filterCanonicalGroups,
  type CanonicalGroupItem,
} from '../src/features/sectors/groupIntelligence';

function assert(condition: unknown, message: string) {
  if (!condition) throw new Error(message);
}

function item(id: string, patch: Partial<CanonicalGroupItem> = {}): CanonicalGroupItem {
  return {
    availability: { reason: null, source_state: 'test', state: 'available' },
    breadth: { above_20: 70, above_50: 65, above_200: 58, advance_decline_ratio: 1.4, advancing: 7, declining: 3, highs_minus_lows: 3, new_highs: 4, new_lows: 1 },
    canonical_destination: { route: '/sectors', params: { entityId: id, entityKind: 'sector' } },
    concentration: 35,
    confidence: { data: { label: 'High', reason: null, score: 90 }, signal: { label: 'Moderate', reason: null, score: 70 } },
    evidence: { input_hash: id, snapshot_id: 'snapshot-1' },
    freshness: { as_of: '2026-07-22', generated_at: '2026-07-22T21:00:00Z', state: 'current' },
    id,
    movement: { direction: 'gaining', previous_state: 'improving', recent_transition: true },
    name: id,
    parent: null,
    performance: { '1D': 1, '1W': 2, '1M': 4, '3M': 7, '6M': 10, '1Y': 18 },
    persistence: { available: true, snapshot_count: 2, state: 'leading' },
    quadrant: 'leading',
    rank: 1,
    rank_change: 2,
    relative_momentum: 102,
    relative_strength: 65,
    state: 'leading',
    type: 'sector',
    ...patch,
  };
}

const items = [
  item('technology'),
  item('financials', { quadrant: 'improving', rank: 4, rank_change: 0, movement: { direction: 'stable', previous_state: 'improving', recent_transition: false } }),
  item('utilities', { availability: { reason: 'missing history', source_state: 'test', state: 'partial' }, breadth: { above_20: null, above_50: null, above_200: null, advance_decline_ratio: null, advancing: null, declining: null, highs_minus_lows: null, new_highs: null, new_lows: null }, quadrant: 'lagging', rank: null, rank_change: null, relative_momentum: null }),
];

const combinedFilters = {
  ...DEFAULT_CANONICAL_GROUP_FILTERS,
  breadthMinimum: 60,
  quadrant: 'leading' as const,
  rankMaximum: 3,
  recentTransition: true,
  savedOnly: true,
  strongMovement: true,
};
const combined = filterCanonicalGroups(items, combinedFilters, new Set(['sector:technology']));
assert(combined.length === 1 && combined[0].id === 'technology', 'combined canonical filters use backend-owned fields');
assert(countCanonicalGroupFilters(combinedFilters) === 6, 'active filter count includes every active canonical filter');
assert(filterCanonicalGroups(items, DEFAULT_CANONICAL_GROUP_FILTERS, new Set()).length === items.length, 'reset restores all canonical entities');
assert(filterCanonicalGroups(items, { ...DEFAULT_CANONICAL_GROUP_FILTERS, breadthMinimum: 99 }, new Set()).length === 0, 'impossible filter combination produces an explicit empty result');
assert(comparisonSelectionLimit(390) === 3 && comparisonSelectionLimit(1280) === 5, 'comparison adapts to mobile and desktop limits');
assert(items[2].breadth.above_50 === null, 'unavailable metrics remain null and are not converted to zero');

const saved = new Set(['sector:technology']);
assert(filterCanonicalGroups(items, { ...DEFAULT_CANONICAL_GROUP_FILTERS, quadrant: 'improving' }, saved)[0]?.id === 'financials', 'improving filter is independent');
assert(filterCanonicalGroups(items, { ...DEFAULT_CANONICAL_GROUP_FILTERS, quadrant: 'lagging' }, saved)[0]?.id === 'utilities', 'weak/lagging filter preserves unavailable entity identity');
assert(filterCanonicalGroups(items, { ...DEFAULT_CANONICAL_GROUP_FILTERS, rankMaximum: 3 }, saved).length === 1, 'rank filter is independent');
assert(filterCanonicalGroups(items, { ...DEFAULT_CANONICAL_GROUP_FILTERS, breadthMinimum: 60 }, saved).length === 2, 'breadth band is independent');
assert(filterCanonicalGroups(items, { ...DEFAULT_CANONICAL_GROUP_FILTERS, momentumMinimum: 100 }, saved).length === 2, 'momentum band is independent and excludes null');
assert(filterCanonicalGroups(items, { ...DEFAULT_CANONICAL_GROUP_FILTERS, savedOnly: true }, saved).length === 1, 'saved-only filter uses canonical identity');
assert(filterCanonicalGroups(items, { ...DEFAULT_CANONICAL_GROUP_FILTERS, availability: 'partial' }, saved)[0]?.id === 'utilities', 'availability filter is independent');
assert(filterCanonicalGroups(items, { ...DEFAULT_CANONICAL_GROUP_FILTERS, movement: 'stable' }, saved)[0]?.id === 'financials', 'movement filter is independent');
assert(filterCanonicalGroups(items, { ...DEFAULT_CANONICAL_GROUP_FILTERS, strongMovement: true }, saved)[0]?.id === 'technology', 'strong movement filter uses rank change');
assert(filterCanonicalGroups(items, { ...DEFAULT_CANONICAL_GROUP_FILTERS, recentTransition: true }, saved)[0]?.id === 'technology', 'recent transition filter uses canonical snapshot change');

console.log('PASS canonical group filters, adaptive comparison limits, and unavailable states');
