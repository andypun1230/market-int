import type { ClassifiedWatchlistItem, WatchlistGroup, WatchlistSeverity, WatchlistSortMode } from './types';

const GROUP_ORDER: Record<WatchlistGroup, number> = {
  needs_attention: 0,
  high_priority: 1,
  momentum: 2,
  watching: 3,
  data_unavailable: 4,
};

const SEVERITY_ORDER: Record<WatchlistSeverity, number> = {
  critical: 0,
  warning: 1,
  positive: 2,
  neutral: 3,
};

export const WATCHLIST_SORT_OPTIONS: { key: WatchlistSortMode; label: string }[] = [
  { key: 'smartPriority', label: 'Smart Priority' },
  { key: 'dailyGain', label: 'Daily Gain' },
  { key: 'dailyLoss', label: 'Daily Loss' },
  { key: 'momentum', label: 'Momentum' },
  { key: 'relativeStrength', label: 'Relative Strength' },
  { key: 'volume', label: 'Volume' },
  { key: 'nearHigh', label: 'Near High' },
  { key: 'earningsDate', label: 'Earnings Date' },
  { key: 'manualOrder', label: 'Manual Order' },
  { key: 'alphabetical', label: 'Alphabetical' },
];

export function sortWatchlistItems(items: ClassifiedWatchlistItem[], sortMode: WatchlistSortMode) {
  return [...items].sort((a, b) => {
    const comparison = compareByMode(a, b, sortMode);
    if (comparison !== 0) {
      return comparison;
    }
    return a.item.ticker.localeCompare(b.item.ticker) || a.originalIndex - b.originalIndex;
  });
}

export function groupSortedWatchlistItems(items: ClassifiedWatchlistItem[]) {
  return items.reduce<Record<WatchlistGroup, ClassifiedWatchlistItem[]>>(
    (groups, item) => {
      groups[item.classification.group].push(item);
      return groups;
    },
    {
      data_unavailable: [],
      high_priority: [],
      momentum: [],
      needs_attention: [],
      watching: [],
    },
  );
}

export function getSortLabel(sortMode: WatchlistSortMode) {
  return WATCHLIST_SORT_OPTIONS.find((option) => option.key === sortMode)?.label ?? 'Smart Priority';
}

function compareByMode(a: ClassifiedWatchlistItem, b: ClassifiedWatchlistItem, sortMode: WatchlistSortMode) {
  switch (sortMode) {
    case 'dailyGain':
      return compareNumbersDesc(a.item.change_percent, b.item.change_percent);
    case 'dailyLoss':
      return compareNumbersAsc(a.item.change_percent, b.item.change_percent);
    case 'momentum':
      return compareNumbersDesc(a.item.overall_score, b.item.overall_score);
    case 'relativeStrength':
      return compareNumbersAsc(a.item.rs_rank, b.item.rs_rank);
    case 'volume':
      return compareNumbersDesc(a.item.pattern_confidence, b.item.pattern_confidence);
    case 'nearHigh':
      return compareNumbersDesc(a.item.pattern_confidence, b.item.pattern_confidence);
    case 'earningsDate':
      return compareStrings(a.item.ticker, b.item.ticker);
    case 'manualOrder':
      return a.originalIndex - b.originalIndex;
    case 'alphabetical':
      return compareStrings(a.item.ticker, b.item.ticker);
    case 'smartPriority':
    default:
      return (
        GROUP_ORDER[a.classification.group] - GROUP_ORDER[b.classification.group] ||
        compareNumbersDesc(a.classification.score, b.classification.score) ||
        SEVERITY_ORDER[a.classification.severity] - SEVERITY_ORDER[b.classification.severity] ||
        compareNumbersDesc(Math.abs(a.item.change_percent ?? 0), Math.abs(b.item.change_percent ?? 0))
      );
  }
}

function compareNumbersDesc(a?: number | null, b?: number | null) {
  if (typeof a !== 'number' && typeof b !== 'number') {
    return 0;
  }
  if (typeof a !== 'number') {
    return 1;
  }
  if (typeof b !== 'number') {
    return -1;
  }
  return b - a;
}

function compareNumbersAsc(a?: number | null, b?: number | null) {
  if (typeof a !== 'number' && typeof b !== 'number') {
    return 0;
  }
  if (typeof a !== 'number') {
    return 1;
  }
  if (typeof b !== 'number') {
    return -1;
  }
  return a - b;
}

function compareStrings(a: string, b: string) {
  return a.localeCompare(b);
}
