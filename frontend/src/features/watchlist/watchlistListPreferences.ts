import {
  DEFAULT_LIST_CONTROL_PREFERENCES,
  SECTOR_FILTER_OPTIONS,
  SECTOR_SORT_OPTIONS,
  STOCK_FILTER_OPTIONS,
  STOCK_SORT_OPTIONS,
  THEME_FILTER_OPTIONS,
  THEME_SORT_OPTIONS,
  type ListControlPreferences,
  type WatchlistCategory,
  type WatchlistListFilter,
  type WatchlistListSort,
  type WatchlistViewMode,
} from './watchlistListControls';

export function normalizeListControlPreferences(value: unknown): Record<WatchlistCategory, ListControlPreferences> {
  const controls = isRecord(value) ? value : {};
  return {
    sectors: normalizeCategoryControl(controls.sectors, 'sectors'),
    stocks: normalizeCategoryControl(controls.stocks, 'stocks'),
    themes: normalizeCategoryControl(controls.themes, 'themes'),
  };
}

export function resetListControlCategory(
  preferences: Record<WatchlistCategory, ListControlPreferences>,
  category: WatchlistCategory,
) {
  return {
    ...preferences,
    [category]: { ...DEFAULT_LIST_CONTROL_PREFERENCES[category], filters: [] },
  };
}

function normalizeCategoryControl(value: unknown, category: WatchlistCategory): ListControlPreferences {
  const control = isRecord(value) ? value : {};
  const defaults = DEFAULT_LIST_CONTROL_PREFERENCES[category];
  return {
    filters: Array.isArray(control.filters)
      ? control.filters.filter((filter): filter is WatchlistListFilter => isCategoryFilter(filter, category))
      : [],
    sort: isCategorySort(control.sort, category) ? control.sort : defaults.sort,
    viewMode: isViewMode(control.viewMode) ? control.viewMode : defaults.viewMode,
  };
}

function isCategoryFilter(value: unknown, category: WatchlistCategory): value is WatchlistListFilter {
  if (typeof value !== 'string') return false;
  const options = category === 'stocks'
    ? STOCK_FILTER_OPTIONS
    : category === 'sectors'
      ? SECTOR_FILTER_OPTIONS
      : THEME_FILTER_OPTIONS;
  return options.some((option) => option.key === value);
}

function isCategorySort(value: unknown, category: WatchlistCategory): value is WatchlistListSort {
  if (typeof value !== 'string') return false;
  const options = category === 'stocks'
    ? STOCK_SORT_OPTIONS
    : category === 'sectors'
      ? SECTOR_SORT_OPTIONS
      : THEME_SORT_OPTIONS;
  return options.some((option) => option.key === value);
}

function isViewMode(value: unknown): value is WatchlistViewMode {
  return value === 'compact' || value === 'detailed';
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}
