import type { SectorThemeTestItem } from '@/data/sectorTabTestData';
import type { GroupWatchlistItem } from '@/features/watchlist/store';

import type { SectorThemeClassification, SectorThemeGroup, SectorThemeSortMode } from './types';

export type ClassifiedSectorThemeItem = {
  classification: SectorThemeClassification;
  item: SectorThemeTestItem | null;
  originalIndex: number;
  stored: GroupWatchlistItem;
};

const SMART_GROUP_ORDER: Record<SectorThemeGroup, number> = {
  leading: 0,
  improving: 1,
  watching: 2,
  weakening: 3,
  data_unavailable: 4,
};

export const SECTOR_THEME_SORT_OPTIONS: { key: SectorThemeSortMode; label: string }[] = [
  { key: 'smartPriority', label: 'Smart Priority' },
  { key: 'recent', label: 'Recent' },
  { key: 'topReturn', label: 'Top Return' },
  { key: 'weakest', label: 'Weakest' },
  { key: 'momentum', label: 'Momentum' },
  { key: 'alphabetical', label: 'Alphabetical' },
];

export function sortSectorThemeItems(
  items: ClassifiedSectorThemeItem[],
  sortMode: SectorThemeSortMode,
) {
  return [...items].sort((a, b) => {
    const comparison = compareByMode(a, b, sortMode);
    if (comparison !== 0) {
      return comparison;
    }
    return a.stored.name.localeCompare(b.stored.name) || a.originalIndex - b.originalIndex;
  });
}

export function groupSectorThemeItems(items: ClassifiedSectorThemeItem[]) {
  return items.reduce<Record<SectorThemeGroup, ClassifiedSectorThemeItem[]>>(
    (groups, item) => {
      groups[item.classification.group].push(item);
      return groups;
    },
    {
      data_unavailable: [],
      improving: [],
      leading: [],
      watching: [],
      weakening: [],
    },
  );
}

export function getSectorThemeSortLabel(sortMode: SectorThemeSortMode) {
  return SECTOR_THEME_SORT_OPTIONS.find((option) => option.key === sortMode)?.label ?? 'Smart Priority';
}

function compareByMode(
  a: ClassifiedSectorThemeItem,
  b: ClassifiedSectorThemeItem,
  sortMode: SectorThemeSortMode,
) {
  switch (sortMode) {
    case 'topReturn':
      return compareNumbersDesc(a.classification.returnPercent, b.classification.returnPercent);
    case 'weakest':
      return compareNumbersAsc(a.classification.returnPercent, b.classification.returnPercent);
    case 'momentum':
      return compareNumbersDesc(a.item?.relativeMomentum, b.item?.relativeMomentum);
    case 'alphabetical':
      return a.stored.name.localeCompare(b.stored.name);
    case 'recent':
      return new Date(b.stored.addedAt).getTime() - new Date(a.stored.addedAt).getTime() || a.originalIndex - b.originalIndex;
    case 'smartPriority':
    default:
      return (
        SMART_GROUP_ORDER[a.classification.group] - SMART_GROUP_ORDER[b.classification.group] ||
        compareNumbersDesc(a.classification.score, b.classification.score) ||
        compareNumbersDesc(a.classification.returnPercent, b.classification.returnPercent) ||
        a.originalIndex - b.originalIndex
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
