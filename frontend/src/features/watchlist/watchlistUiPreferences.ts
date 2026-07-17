import { useCallback, useState } from 'react';

import type { TestHeatmapInterval } from '@/data/sectorTabTestData';

import type {
  SectorThemeGroup,
  SectorThemeSortMode,
  SectorThemeTypeFilter,
  WatchlistGroup,
  WatchlistSortMode,
} from './types';

type WatchlistUiPreferences = {
  collapsedGroups: Partial<Record<WatchlistGroup, boolean>>;
  sectorThemeCollapsedGroups: Partial<Record<SectorThemeGroup, boolean>>;
  sectorThemePeriod: TestHeatmapInterval;
  sectorThemeSortMode: SectorThemeSortMode;
  sectorThemeTypeFilter: SectorThemeTypeFilter;
  sortMode: WatchlistSortMode;
};

const STORAGE_KEY = 'market-intelligence:watchlist-ui:v2';
const DEFAULT_PREFERENCES: WatchlistUiPreferences = {
  collapsedGroups: {},
  sectorThemeCollapsedGroups: {},
  sectorThemePeriod: '1M',
  sectorThemeSortMode: 'smartPriority',
  sectorThemeTypeFilter: 'all',
  sortMode: 'smartPriority',
};

let memoryPreferences = loadStoredPreferences();

export function useWatchlistUiPreferences() {
  const [preferences, setPreferences] = useState(memoryPreferences);

  const updatePreferences = useCallback((patch: Partial<WatchlistUiPreferences>) => {
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
    };
    savePreferences(memoryPreferences);
    setPreferences(memoryPreferences);
  }, []);

  return [preferences, updatePreferences] as const;
}

export function resetWatchlistUiPreferencesForTests() {
  memoryPreferences = DEFAULT_PREFERENCES;
}

function loadStoredPreferences(): WatchlistUiPreferences {
  try {
    const storage = getLocalStorage();
    const raw = storage?.getItem(STORAGE_KEY);
    if (!raw) {
      return DEFAULT_PREFERENCES;
    }
    const parsed = JSON.parse(raw) as Partial<WatchlistUiPreferences>;
    return {
      collapsedGroups: parsed.collapsedGroups ?? {},
      sectorThemeCollapsedGroups: parsed.sectorThemeCollapsedGroups ?? {},
      sectorThemePeriod: isHeatmapInterval(parsed.sectorThemePeriod) ? parsed.sectorThemePeriod : '1M',
      sectorThemeSortMode: isSectorThemeSortMode(parsed.sectorThemeSortMode) ? parsed.sectorThemeSortMode : 'smartPriority',
      sectorThemeTypeFilter: isSectorThemeTypeFilter(parsed.sectorThemeTypeFilter) ? parsed.sectorThemeTypeFilter : 'all',
      sortMode: isSortMode(parsed.sortMode) ? parsed.sortMode : 'smartPriority',
    };
  } catch {
    return DEFAULT_PREFERENCES;
  }
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
