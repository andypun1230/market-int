import type { SectorId, SectorRow } from '@/features/sectors/sectorSnapshot';
import type { LiveThemeItem } from '@/features/themes/themeSnapshot';

import { getWatchlistDecisionGroup } from './watchlistDecision';
import type { ClassifiedWatchlistItem, WatchlistDataStatus } from './types';

export type WatchlistCategory = 'stocks' | 'sectors' | 'themes';
export type WatchlistViewMode = 'compact' | 'detailed';

export type StockListSort = 'priority' | 'opportunity' | 'biggest_gain' | 'biggest_loss' | 'alphabetical';
export type SectorListSort = 'leadership_rank' | 'highest_score' | 'strongest_momentum' | 'weakest' | 'alphabetical';
export type ThemeListSort = 'theme_rank' | 'relative_strength' | 'one_month_return' | 'momentum' | 'alphabetical';
export type WatchlistListSort = StockListSort | SectorListSort | ThemeListSort;

export type StockListFilter =
  | 'decision_action' | 'decision_watching' | 'decision_stable'
  | 'setup_strong' | 'setup_confirmation' | 'setup_weak' | 'setup_preparing' | 'setup_partial'
  | 'risk_high' | 'risk_moderate' | 'risk_low'
  | 'data_live' | 'data_cached' | 'data_stale' | 'data_unavailable'
  | 'movement_gainer' | 'movement_decliner' | 'movement_unchanged';
export type SectorListFilter = 'state_leading' | 'state_improving' | 'state_neutral' | 'state_weakening' | 'state_lagging';
export type ThemeListFilter = SectorListFilter | 'return_positive' | 'return_negative' | 'rs_above' | 'rs_below';
export type WatchlistListFilter = StockListFilter | SectorListFilter | ThemeListFilter;

export type ListControlPreferences = {
  filters: WatchlistListFilter[];
  sort: WatchlistListSort;
  viewMode: WatchlistViewMode;
};

export type ListControlOption = {
  dimension?: string;
  key: string;
  label: string;
};

export type SavedSectorEntry<TStored = unknown> = {
  row: SectorRow | null;
  sectorId: SectorId;
  stored: TStored;
};

export type SavedThemeEntry<TStored = unknown> = {
  row: LiveThemeItem | null;
  stored: TStored;
};

export const DEFAULT_LIST_CONTROL_PREFERENCES: Record<WatchlistCategory, ListControlPreferences> = {
  sectors: { filters: [], sort: 'leadership_rank', viewMode: 'detailed' },
  stocks: { filters: [], sort: 'priority', viewMode: 'detailed' },
  themes: { filters: [], sort: 'theme_rank', viewMode: 'detailed' },
};

export const STOCK_SORT_OPTIONS: ListControlOption[] = [
  { key: 'priority', label: 'Priority' },
  { key: 'opportunity', label: 'Highest Opportunity' },
  { key: 'biggest_gain', label: 'Biggest Gain' },
  { key: 'biggest_loss', label: 'Biggest Loss' },
  { key: 'alphabetical', label: 'Alphabetical' },
];

export const STOCK_FILTER_OPTIONS: ListControlOption[] = [
  { dimension: 'decision', key: 'decision_action', label: 'Action Required' },
  { dimension: 'decision', key: 'decision_watching', label: 'Watching Closely' },
  { dimension: 'decision', key: 'decision_stable', label: 'Stable / Waiting' },
  { dimension: 'setup', key: 'setup_strong', label: 'Strong Setup' },
  { dimension: 'setup', key: 'setup_confirmation', label: 'Needs Confirmation' },
  { dimension: 'setup', key: 'setup_weak', label: 'Weak / Broken Setup' },
  { dimension: 'setup', key: 'setup_preparing', label: 'Preparing Analysis' },
  { dimension: 'setup', key: 'setup_partial', label: 'Partial Analysis' },
  { dimension: 'risk', key: 'risk_high', label: 'High Risk' },
  { dimension: 'risk', key: 'risk_moderate', label: 'Moderate Risk' },
  { dimension: 'risk', key: 'risk_low', label: 'Low Risk' },
  { dimension: 'data', key: 'data_live', label: 'Live' },
  { dimension: 'data', key: 'data_cached', label: 'Cached' },
  { dimension: 'data', key: 'data_stale', label: 'Stale' },
  { dimension: 'data', key: 'data_unavailable', label: 'Unavailable' },
  { dimension: 'movement', key: 'movement_gainer', label: 'Gainers' },
  { dimension: 'movement', key: 'movement_decliner', label: 'Decliners' },
  { dimension: 'movement', key: 'movement_unchanged', label: 'Unchanged' },
];

export const SECTOR_SORT_OPTIONS: ListControlOption[] = [
  { key: 'leadership_rank', label: 'Leadership Rank' },
  { key: 'highest_score', label: 'Highest Score' },
  { key: 'strongest_momentum', label: 'Strongest Momentum' },
  { key: 'weakest', label: 'Weakest / Lagging' },
  { key: 'alphabetical', label: 'Alphabetical' },
];

export const SECTOR_FILTER_OPTIONS: ListControlOption[] = stateFilterOptions();

export const THEME_SORT_OPTIONS: ListControlOption[] = [
  { key: 'theme_rank', label: 'Theme Rank' },
  { key: 'relative_strength', label: 'Relative Strength' },
  { key: 'one_month_return', label: 'One-Month Return' },
  { key: 'momentum', label: 'Momentum' },
  { key: 'alphabetical', label: 'Alphabetical' },
];

export const THEME_FILTER_OPTIONS: ListControlOption[] = [
  ...stateFilterOptions(),
  { dimension: 'return', key: 'return_positive', label: 'Positive One-Month Return' },
  { dimension: 'return', key: 'return_negative', label: 'Negative One-Month Return' },
  { dimension: 'relative_strength', key: 'rs_above', label: 'Relative Strength Above Benchmark' },
  { dimension: 'relative_strength', key: 'rs_below', label: 'Relative Strength Below Benchmark' },
];

export function getStockSortOptions(items: ClassifiedWatchlistItem[]) {
  return items.some((item) => finite(item.item.overall_score) || finite(item.classification.score))
    ? STOCK_SORT_OPTIONS
    : STOCK_SORT_OPTIONS.filter((option) => option.key !== 'opportunity');
}

export function filterAndSortStocks(
  items: ClassifiedWatchlistItem[],
  preferences: ListControlPreferences,
) {
  const filtered = applyDimensionFilters(items, preferences.filters, STOCK_FILTER_OPTIONS, stockMatchesFilter);
  return [...filtered].sort((a, b) => compareStocks(a, b, preferences.sort as StockListSort));
}

export function filterAndSortSectors<TStored>(
  items: SavedSectorEntry<TStored>[],
  preferences: ListControlPreferences,
) {
  const filtered = applyDimensionFilters(items, preferences.filters, SECTOR_FILTER_OPTIONS, sectorMatchesFilter);
  return [...filtered].sort((a, b) => compareSectors(a, b, preferences.sort as SectorListSort));
}

export function filterAndSortThemes<TStored>(
  items: SavedThemeEntry<TStored>[],
  preferences: ListControlPreferences,
) {
  const filtered = applyDimensionFilters(items, preferences.filters, THEME_FILTER_OPTIONS, themeMatchesFilter);
  return [...filtered].sort((a, b) => compareThemes(a, b, preferences.sort as ThemeListSort));
}

export function isGroupedStockSort(sort: WatchlistListSort) {
  return sort === 'priority';
}

export function getFlatStockSortDescription(sort: WatchlistListSort) {
  switch (sort) {
    case 'opportunity': return 'Sorted across all saved stocks by opportunity score.';
    case 'biggest_gain': return 'Sorted across all saved stocks by daily gain.';
    case 'biggest_loss': return 'Sorted across all saved stocks by daily loss.';
    case 'alphabetical': return 'Sorted across all saved stocks by ticker.';
    default: return null;
  }
}

export function getSortLabel(options: ListControlOption[], sort: string) {
  return options.find((option) => option.key === sort)?.label ?? options[0]?.label ?? 'Sort';
}

function applyDimensionFilters<T>(
  items: T[],
  filters: WatchlistListFilter[],
  options: ListControlOption[],
  matches: (item: T, filter: string) => boolean,
) {
  const dimensions = new Map<string, string[]>();
  filters.forEach((filter) => {
    const dimension = options.find((option) => option.key === filter)?.dimension;
    if (!dimension) return;
    dimensions.set(dimension, [...(dimensions.get(dimension) ?? []), filter]);
  });
  // Filters are OR-ed inside a dimension and AND-ed across dimensions.
  return items.filter((item) => [...dimensions.values()].every((dimensionFilters) => (
    dimensionFilters.some((filter) => matches(item, filter))
  )));
}

function stockMatchesFilter(item: ClassifiedWatchlistItem, filter: string) {
  const decision = getWatchlistDecisionGroup(item);
  const signal = item.classification.primarySignal;
  const setup = `${item.item.setup ?? ''} ${item.item.trend ?? ''} ${item.item.rating ?? ''}`.toLowerCase();
  const risk = (item.item.risk_flag ?? '').toLowerCase();
  const dataStatus = normalizeDataStatus(item.classification.dataStatus);
  switch (filter) {
    case 'decision_action': return decision === 'action_required';
    case 'decision_watching': return decision === 'watching_closely';
    case 'decision_stable': return decision === 'stable_waiting';
    case 'setup_strong': return item.classification.group === 'high_priority' || item.classification.group === 'momentum' || /strong|bullish|breakout/.test(setup);
    case 'setup_confirmation': return signal === 'near_breakout' || /confirm|watching|waiting/.test(setup);
    case 'setup_weak': return item.classification.group === 'needs_attention' || /weak|broken|below support|bearish/.test(setup);
    case 'setup_preparing': return item.item.overall_status === 'pending' || item.item.analysis_status === 'initializing' || signal === 'pending';
    case 'setup_partial': return item.item.overall_status === 'partial' || item.item.analysis_status === 'partial' || signal === 'partial';
    case 'risk_high': return /high|elevated|critical|severe/.test(risk);
    case 'risk_moderate': return /moderate|medium|balanced/.test(risk);
    case 'risk_low': return /low|controlled|normal/.test(risk);
    case 'data_live': return dataStatus === 'live';
    case 'data_cached': return dataStatus === 'cached';
    case 'data_stale': return dataStatus === 'stale';
    case 'data_unavailable': return dataStatus === 'unavailable';
    case 'movement_gainer': return finite(item.item.change_percent) && item.item.change_percent! > 0;
    case 'movement_decliner': return finite(item.item.change_percent) && item.item.change_percent! < 0;
    case 'movement_unchanged': return finite(item.item.change_percent) && item.item.change_percent === 0;
    default: return true;
  }
}

function sectorMatchesFilter(item: SavedSectorEntry, filter: string) {
  return stateMatches(item.row?.classification, filter);
}

function themeMatchesFilter(item: SavedThemeEntry, filter: string) {
  if (filter.startsWith('state_')) return stateMatches(item.row?.classification, filter);
  const oneMonth = item.row?.returns['1M'];
  const relativeStrength = item.row?.rotation['1M'].relativeStrength;
  if (filter === 'return_positive') return finite(oneMonth) && oneMonth! > 0;
  if (filter === 'return_negative') return finite(oneMonth) && oneMonth! < 0;
  if (filter === 'rs_above') return finite(relativeStrength) && relativeStrength! > 100;
  if (filter === 'rs_below') return finite(relativeStrength) && relativeStrength! < 100;
  return true;
}

function stateMatches(classification: string | null | undefined, filter: string) {
  return classification?.toLowerCase() === filter.replace('state_', '');
}

function compareStocks(a: ClassifiedWatchlistItem, b: ClassifiedWatchlistItem, sort: StockListSort) {
  let comparison = 0;
  if (sort === 'priority') {
    const order = { action_required: 0, watching_closely: 1, stable_waiting: 2 };
    comparison = order[getWatchlistDecisionGroup(a)] - order[getWatchlistDecisionGroup(b)]
      || compareNumberDesc(a.classification.score, b.classification.score);
  } else if (sort === 'opportunity') {
    comparison = compareNumberDesc(a.item.overall_score ?? a.classification.score, b.item.overall_score ?? b.classification.score);
  } else if (sort === 'biggest_gain') {
    comparison = compareNumberDesc(a.item.change_percent, b.item.change_percent);
  } else if (sort === 'biggest_loss') {
    comparison = compareNumberAsc(a.item.change_percent, b.item.change_percent);
  }
  return comparison || a.item.ticker.localeCompare(b.item.ticker) || a.originalIndex - b.originalIndex;
}

function compareSectors(a: SavedSectorEntry, b: SavedSectorEntry, sort: SectorListSort) {
  let comparison = 0;
  if (sort === 'leadership_rank') comparison = compareNumberAsc(a.row?.rank, b.row?.rank);
  if (sort === 'highest_score') comparison = compareNumberDesc(a.row?.compositeScore, b.row?.compositeScore);
  if (sort === 'strongest_momentum') comparison = compareNumberDesc(a.row?.scores.momentum, b.row?.scores.momentum);
  if (sort === 'weakest') comparison = compareNumberAsc(a.row?.compositeScore, b.row?.compositeScore);
  return comparison || sectorName(a).localeCompare(sectorName(b));
}

function compareThemes(a: SavedThemeEntry, b: SavedThemeEntry, sort: ThemeListSort) {
  let comparison = 0;
  if (sort === 'theme_rank') comparison = compareNumberAsc(a.row?.rank, b.row?.rank);
  if (sort === 'relative_strength') comparison = compareNumberDesc(a.row?.rotation['1M'].relativeStrength, b.row?.rotation['1M'].relativeStrength);
  if (sort === 'one_month_return') comparison = compareNumberDesc(a.row?.returns['1M'], b.row?.returns['1M']);
  if (sort === 'momentum') comparison = compareNumberDesc(a.row?.rotation['1M'].relativeMomentum, b.row?.rotation['1M'].relativeMomentum);
  return comparison || themeName(a).localeCompare(themeName(b));
}

function stateFilterOptions(): ListControlOption[] {
  return ['Leading', 'Improving', 'Neutral', 'Weakening', 'Lagging'].map((label) => ({
    dimension: 'state',
    key: `state_${label.toLowerCase()}`,
    label,
  }));
}

function normalizeDataStatus(status: WatchlistDataStatus): 'live' | 'cached' | 'stale' | 'unavailable' {
  if (status === 'live') return 'live';
  if (status === 'cached' || status === 'test' || status === 'mock') return 'cached';
  if (status === 'stale') return 'stale';
  return 'unavailable';
}

function sectorName(item: SavedSectorEntry) {
  const stored = item.stored as { name?: string };
  return item.row?.displayName ?? stored.name ?? item.sectorId;
}

function themeName(item: SavedThemeEntry) {
  const stored = item.stored as { name?: string };
  return item.row?.name ?? stored.name ?? '';
}

function finite(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

function compareNumberDesc(a: number | null | undefined, b: number | null | undefined) {
  return compareNullable(a, b, (left, right) => right - left);
}

function compareNumberAsc(a: number | null | undefined, b: number | null | undefined) {
  return compareNullable(a, b, (left, right) => left - right);
}

function compareNullable(
  a: number | null | undefined,
  b: number | null | undefined,
  compare: (left: number, right: number) => number,
) {
  if (!finite(a) && !finite(b)) return 0;
  if (!finite(a)) return 1;
  if (!finite(b)) return -1;
  return compare(a, b);
}
