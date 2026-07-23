import type {
  ConstituentTestItem,
  TestHeatmapInterval,
} from '@/data/sectorTabTestData';
import { buildWatchlistKey } from '@/features/watchlist/domain';

export type RelevantStockPerformanceFilter = 'all' | 'positive' | 'negative' | 'nearZero';
export type RelevantStockTrendFilter = 'all' | 'above20' | 'below20' | 'above50' | 'below50';
export type RelevantStockMomentumFilter = 'all' | ConstituentTestItem['momentumLabel'];
export type RelevantStockRelativeStrengthFilter = 'all' | 'above100' | 'below100';
export type RelevantStockMarketCapFilter = 'all' | ConstituentTestItem['marketCapCategory'];
export type RelevantStockWatchlistFilter = 'all' | 'saved' | 'notSaved';
export type RelevantStockSortMode =
  | 'highestReturn'
  | 'lowestReturn'
  | 'highestRelativeStrength'
  | 'lowestRelativeStrength'
  | 'largestWeight'
  | 'smallestWeight'
  | 'alphabetical'
  | 'watchlistedFirst';

export type RelevantStockFilters = {
  marketCap: RelevantStockMarketCapFilter;
  momentum: RelevantStockMomentumFilter;
  performance: RelevantStockPerformanceFilter;
  relativeStrength: RelevantStockRelativeStrengthFilter;
  sortMode: RelevantStockSortMode;
  trend: RelevantStockTrendFilter;
  watchlist: RelevantStockWatchlistFilter;
};

export type RelevantStockFilterKey =
  | 'marketCap'
  | 'momentum'
  | 'performance'
  | 'relativeStrength'
  | 'trend'
  | 'watchlist';

export type RelevantStockActiveFilterChip = {
  key: RelevantStockFilterKey;
  label: string;
};

export const DEFAULT_RELEVANT_STOCK_FILTERS: RelevantStockFilters = {
  marketCap: 'all',
  momentum: 'all',
  performance: 'all',
  relativeStrength: 'all',
  sortMode: 'highestReturn',
  trend: 'all',
  watchlist: 'all',
};

export const RELEVANT_STOCK_SORT_OPTIONS: { key: RelevantStockSortMode; label: string }[] = [
  { key: 'highestReturn', label: 'Highest Return' },
  { key: 'lowestReturn', label: 'Lowest Return' },
  { key: 'highestRelativeStrength', label: 'Highest Relative Strength' },
  { key: 'largestWeight', label: 'Largest Weight' },
  { key: 'alphabetical', label: 'Alphabetical' },
  { key: 'watchlistedFirst', label: 'Saved First' },
];

export function filterRelevantStocks(
  items: ConstituentTestItem[],
  query: string,
  filters: RelevantStockFilters,
  interval: TestHeatmapInterval,
  stockWatchlistKeys: Set<string>,
) {
  const normalized = query.trim().toLowerCase();
  return items.filter((item) => {
    const value = item.returns[interval];
    const isSaved = stockWatchlistKeys.has(buildWatchlistKey('stock', item.ticker));
    if (normalized && !item.ticker.toLowerCase().includes(normalized) && !(item.companyName ?? '').toLowerCase().includes(normalized)) {
      return false;
    }
    if (filters.performance === 'positive' && value <= 0.5) {
      return false;
    }
    if (filters.performance === 'negative' && value >= -0.5) {
      return false;
    }
    if (filters.performance === 'nearZero' && Math.abs(value) > 0.75) {
      return false;
    }
    if (filters.trend === 'above20' && !item.above20Ema) {
      return false;
    }
    if (filters.trend === 'below20' && item.above20Ema) {
      return false;
    }
    if (filters.trend === 'above50' && !item.above50Ema) {
      return false;
    }
    if (filters.trend === 'below50' && item.above50Ema) {
      return false;
    }
    if (filters.momentum !== 'all' && item.momentumLabel !== filters.momentum) {
      return false;
    }
    if (filters.relativeStrength === 'above100' && item.relativeStrength < 100) {
      return false;
    }
    if (filters.relativeStrength === 'below100' && item.relativeStrength >= 100) {
      return false;
    }
    if (filters.marketCap !== 'all' && item.marketCapCategory !== filters.marketCap) {
      return false;
    }
    if (filters.watchlist === 'saved' && !isSaved) {
      return false;
    }
    if (filters.watchlist === 'notSaved' && isSaved) {
      return false;
    }
    return true;
  });
}

export function sortRelevantStocks(
  items: ConstituentTestItem[],
  sortMode: RelevantStockSortMode,
  interval: TestHeatmapInterval,
  stockWatchlistKeys: Set<string>,
) {
  return [...items].sort((a, b) => {
    switch (sortMode) {
      case 'lowestReturn':
        return a.returns[interval] - b.returns[interval];
      case 'highestRelativeStrength':
        return b.relativeStrength - a.relativeStrength;
      case 'lowestRelativeStrength':
        return a.relativeStrength - b.relativeStrength;
      case 'largestWeight':
        return b.weight - a.weight;
      case 'smallestWeight':
        return a.weight - b.weight;
      case 'alphabetical':
        return a.ticker.localeCompare(b.ticker);
      case 'watchlistedFirst': {
        const savedCompare =
          Number(stockWatchlistKeys.has(buildWatchlistKey('stock', b.ticker))) -
          Number(stockWatchlistKeys.has(buildWatchlistKey('stock', a.ticker)));
        return savedCompare || a.ticker.localeCompare(b.ticker);
      }
      case 'highestReturn':
      default:
        return b.returns[interval] - a.returns[interval];
    }
  });
}

export function summarizeRelevantStocks(items: ConstituentTestItem[], interval: TestHeatmapInterval) {
  const positives = items.filter((item) => item.returns[interval] > 0).length;
  const negatives = items.filter((item) => item.returns[interval] < 0).length;
  const sortedReturns = items.map((item) => item.returns[interval]).sort((a, b) => a - b);
  const middle = Math.floor(sortedReturns.length / 2);
  const medianReturn = sortedReturns.length
    ? sortedReturns.length % 2
      ? sortedReturns[middle]
      : (sortedReturns[middle - 1] + sortedReturns[middle]) / 2
    : 0;
  const topPerformer = items.reduce<ConstituentTestItem | null>(
    (best, item) => (!best || item.returns[interval] > best.returns[interval] ? item : best),
    null,
  );

  return {
    medianReturn,
    negatives,
    positives,
    topPerformer,
    total: items.length,
  };
}

export function applyRelevantStockQuickFilter(filters: RelevantStockFilters, quickFilter: 'leaders' | 'laggards' | 'above20' | 'highRs' | 'watchlisted') {
  switch (quickFilter) {
    case 'leaders':
      return { ...filters, performance: 'positive' as const, sortMode: 'highestReturn' as const };
    case 'laggards':
      return { ...filters, performance: 'negative' as const, sortMode: 'lowestReturn' as const };
    case 'above20':
      return { ...filters, trend: 'above20' as const };
    case 'highRs':
      return { ...filters, relativeStrength: 'above100' as const, sortMode: 'highestRelativeStrength' as const };
    case 'watchlisted':
      return { ...filters, watchlist: 'saved' as const };
  }
}

export function getRelevantStockSortLabel(sortMode: RelevantStockSortMode) {
  return RELEVANT_STOCK_SORT_OPTIONS.find((option) => option.key === sortMode)?.label ?? 'Highest Return';
}

export function countRelevantStockActiveFilters(filters: RelevantStockFilters) {
  return [
    filters.marketCap !== 'all',
    filters.momentum !== 'all',
    filters.performance !== 'all',
    filters.relativeStrength !== 'all',
    filters.trend !== 'all',
    filters.watchlist !== 'all',
  ].filter(Boolean).length;
}

export function resetRelevantStockFilters(filters: RelevantStockFilters): RelevantStockFilters {
  return {
    ...DEFAULT_RELEVANT_STOCK_FILTERS,
    sortMode: filters.sortMode,
  };
}

export function removeRelevantStockFilter(filters: RelevantStockFilters, key: RelevantStockFilterKey): RelevantStockFilters {
  return {
    ...filters,
    [key]: DEFAULT_RELEVANT_STOCK_FILTERS[key],
  };
}

export function buildRelevantStockActiveFilterChips(filters: RelevantStockFilters): RelevantStockActiveFilterChip[] {
  const chips: RelevantStockActiveFilterChip[] = [];
  if (filters.performance !== 'all') {
    chips.push({ key: 'performance', label: getPerformanceLabel(filters.performance) });
  }
  if (filters.trend !== 'all') {
    chips.push({ key: 'trend', label: getTrendLabel(filters.trend) });
  }
  if (filters.relativeStrength !== 'all') {
    chips.push({ key: 'relativeStrength', label: filters.relativeStrength === 'above100' ? 'RS above 100' : 'RS below 100' });
  }
  if (filters.momentum !== 'all') {
    chips.push({ key: 'momentum', label: getMomentumLabel(filters.momentum) });
  }
  if (filters.marketCap !== 'all') {
    chips.push({ key: 'marketCap', label: `${capitalize(filters.marketCap)} cap` });
  }
  if (filters.watchlist !== 'all') {
    chips.push({ key: 'watchlist', label: filters.watchlist === 'saved' ? 'Saved only' : 'Not saved' });
  }
  return chips;
}

export function countRelevantStockFilters(filters: RelevantStockFilters) {
  return [
    filters.marketCap !== 'all',
    filters.momentum !== 'all',
    filters.performance !== 'all',
    filters.relativeStrength !== 'all',
    filters.sortMode !== DEFAULT_RELEVANT_STOCK_FILTERS.sortMode,
    filters.trend !== 'all',
    filters.watchlist !== 'all',
  ].filter(Boolean).length;
}

function getPerformanceLabel(value: RelevantStockPerformanceFilter) {
  switch (value) {
    case 'positive':
      return 'Leaders';
    case 'negative':
      return 'Laggards';
    case 'nearZero':
      return 'Near zero';
    case 'all':
    default:
      return 'All performance';
  }
}

function getTrendLabel(value: RelevantStockTrendFilter) {
  switch (value) {
    case 'above20':
      return 'Above 20 EMA';
    case 'below20':
      return 'Below 20 EMA';
    case 'above50':
      return 'Above 50 EMA';
    case 'below50':
      return 'Below 50 EMA';
    case 'all':
    default:
      return 'All trends';
  }
}

function getMomentumLabel(value: RelevantStockMomentumFilter) {
  return value === 'all' ? 'All momentum' : capitalize(value);
}

function capitalize(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}
