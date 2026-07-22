import { useCallback, useState } from 'react';

import type { TestHeatmapInterval } from '@/data/sectorTabTestData';

import type {
  SectorThemeGroup,
  SectorThemeSortMode,
  SectorThemeTypeFilter,
  WatchlistGroup,
  WatchlistSortMode,
} from './types';
import {
  DEFAULT_LIST_CONTROL_PREFERENCES,
  type ListControlPreferences,
  type WatchlistCategory,
} from './watchlistListControls';
import { normalizeListControlPreferences, resetListControlCategory } from './watchlistListPreferences';

export type WatchlistUiPreferences = {
  collapsedGroups: Partial<Record<WatchlistGroup, boolean>>;
  sectorThemeCollapsedGroups: Partial<Record<SectorThemeGroup, boolean>>;
  sectorThemePeriod: TestHeatmapInterval;
  sectorThemeSortMode: SectorThemeSortMode;
  sectorThemeTypeFilter: SectorThemeTypeFilter;
  sortMode: WatchlistSortMode;
  listControls: Record<WatchlistCategory, ListControlPreferences>;
};
type WatchlistUiPreferencesPatch = Omit<Partial<WatchlistUiPreferences>, 'listControls'> & {
  listControls?: Partial<Record<WatchlistCategory, ListControlPreferences>>;
};

const STORAGE_KEY = 'market-intelligence:watchlist-ui:v2';
export const DEFAULT_WATCHLIST_UI_PREFERENCES: WatchlistUiPreferences = {
  collapsedGroups: {},
  sectorThemeCollapsedGroups: {},
  sectorThemePeriod: '1M',
  sectorThemeSortMode: 'smartPriority',
  sectorThemeTypeFilter: 'all',
  sortMode: 'smartPriority',
  listControls: DEFAULT_LIST_CONTROL_PREFERENCES,
};

let memoryPreferences = loadStoredPreferences();

export function useWatchlistUiPreferences() {
  const [preferences, setPreferences] = useState(memoryPreferences);

  const updatePreferences = useCallback((patch: WatchlistUiPreferencesPatch) => {
    memoryPreferences = {
      ...memoryPreferences,
      ...patch,
      collapsedGroups: {
        ...memoryPreferences.collapsedGroups,
        ...patch.collapsedGroups,
      },
      sectorThemeCollapsedGroups: {
        ...memoryPreferences.sectorThemeCollapsedGroups,
        ...patch.sectorThemeCollapsedGroups,
      },
      listControls: mergeListControlPreferences(memoryPreferences.listControls, patch.listControls),
    };
    savePreferences(memoryPreferences);
    setPreferences(memoryPreferences);
  }, []);

  return [preferences, updatePreferences] as const;
}

export function resetWatchlistUiPreferencesForTests() {
  memoryPreferences = DEFAULT_WATCHLIST_UI_PREFERENCES;
}

export function resetCategoryListPreferences(
  preferences: WatchlistUiPreferences,
  category: WatchlistCategory,
): WatchlistUiPreferences {
  return {
    ...preferences,
    listControls: resetListControlCategory(preferences.listControls, category),
  };
}

export function normalizeWatchlistUiPreferences(value: unknown): WatchlistUiPreferences {
  const parsed = isRecord(value) ? value as Partial<WatchlistUiPreferences> : {};
  return {
    collapsedGroups: parsed.collapsedGroups ?? {},
    listControls: normalizeListControlPreferences(parsed.listControls),
    sectorThemeCollapsedGroups: parsed.sectorThemeCollapsedGroups ?? {},
    sectorThemePeriod: isHeatmapInterval(parsed.sectorThemePeriod) ? parsed.sectorThemePeriod : '1M',
    sectorThemeSortMode: isSectorThemeSortMode(parsed.sectorThemeSortMode) ? parsed.sectorThemeSortMode : 'smartPriority',
    sectorThemeTypeFilter: isSectorThemeTypeFilter(parsed.sectorThemeTypeFilter) ? parsed.sectorThemeTypeFilter : 'all',
    sortMode: isSortMode(parsed.sortMode) ? parsed.sortMode : 'smartPriority',
  };
}

function loadStoredPreferences(): WatchlistUiPreferences {
  try {
    const storage = getLocalStorage();
    const raw = storage?.getItem(STORAGE_KEY);
    if (!raw) {
      return DEFAULT_WATCHLIST_UI_PREFERENCES;
    }
    return normalizeWatchlistUiPreferences(JSON.parse(raw));
  } catch {
    return DEFAULT_WATCHLIST_UI_PREFERENCES;
  }
}

function mergeListControlPreferences(
  current: Record<WatchlistCategory, ListControlPreferences>,
  patch?: Partial<Record<WatchlistCategory, ListControlPreferences>>,
) {
  if (!patch) return current;
  return (['stocks', 'sectors', 'themes'] as const).reduce<Record<WatchlistCategory, ListControlPreferences>>(
    (next, category) => {
      next[category] = patch[category]
        ? { ...current[category], ...patch[category], filters: [...patch[category]!.filters] }
        : current[category];
      return next;
    },
    { ...current },
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}


function isHeatmapInterval(value: unknown): value is TestHeatmapInterval {
  return value === '1D' || value === '1W' || value === '1M' || value === '3M' || value === '6M' || value === '1Y';
}

function isSectorThemeTypeFilter(value: unknown): value is SectorThemeTypeFilter {
  return value === 'all' || value === 'sector' || value === 'theme';
}

function isSectorThemeSortMode(value: unknown): value is SectorThemeSortMode {
  return (
    value === 'smartPriority' ||
    value === 'recent' ||
    value === 'topReturn' ||
    value === 'weakest' ||
    value === 'momentum' ||
    value === 'alphabetical'
  );
}

function savePreferences(preferences: WatchlistUiPreferences) {
  try {
    getLocalStorage()?.setItem(STORAGE_KEY, JSON.stringify(preferences));
  } catch {
    // Preference persistence is best-effort; session memory still works.
  }
}

function getLocalStorage(): Storage | null {
  if (typeof globalThis === 'undefined' || !('localStorage' in globalThis)) {
    return null;
  }
  return globalThis.localStorage;
}

function isSortMode(value: unknown): value is WatchlistSortMode {
  return (
    value === 'smartPriority' ||
    value === 'dailyGain' ||
    value === 'dailyLoss' ||
    value === 'momentum' ||
    value === 'relativeStrength' ||
    value === 'volume' ||
    value === 'nearHigh' ||
    value === 'earningsDate' ||
    value === 'manualOrder' ||
    value === 'alphabetical'
  );
}
