import type {
  RotationQuadrant,
  SectorBreadthSnapshot,
  SectorThemeTestItem,
  TestHeatmapInterval,
} from '@/data/sectorTabTestData';

import { calculateLeadershipConcentration } from './concentration';

export type FavouriteKey = `${'sector' | 'theme'}:${string}`;
export type FavouriteMode = 'all' | 'only' | 'first';
export type PerformanceFilter = 'all' | 'positive' | 'negative' | 'nearZero';
export type SortMode =
  | 'highestReturn'
  | 'lowestReturn'
  | 'strongestRelativeStrength'
  | 'strongestRelativeMomentum'
  | 'bestBreadth'
  | 'highestConcentration'
  | 'lowestConcentration'
  | 'alphabetical';

export type SectorThemeFilters = {
  breadth: SectorBreadthSnapshot['participationLabel'] | 'all';
  favouriteMode: FavouriteMode;
  performance: PerformanceFilter;
  quadrant: RotationQuadrant | 'all';
  sortMode: SortMode;
};

export const DEFAULT_SECTOR_THEME_FILTERS: SectorThemeFilters = {
  breadth: 'all',
  favouriteMode: 'all',
  performance: 'all',
  quadrant: 'all',
  sortMode: 'highestReturn',
};

export function getFavouriteKey(item: SectorThemeTestItem): FavouriteKey {
  return `${item.type}:${item.id}`;
}

export function filterSectorThemeItems(
  items: SectorThemeTestItem[],
  filters: SectorThemeFilters,
  interval: TestHeatmapInterval,
  favouriteKeys: Set<string>,
) {
  const filtered = items.filter((item) => {
    const value = item.returns[interval];
    const isFavourite = favouriteKeys.has(getFavouriteKey(item));
    if (filters.favouriteMode === 'only' && !isFavourite) {
      return false;
    }
    if (filters.quadrant !== 'all' && item.quadrant !== filters.quadrant) {
      return false;
    }
    if (filters.breadth !== 'all' && item.breadth.participationLabel !== filters.breadth) {
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
    return true;
  });

  return sortSectorThemeItems(filtered, filters.sortMode, interval, favouriteKeys, filters.favouriteMode === 'first');
}

export function sortSectorThemeItems(
  items: SectorThemeTestItem[],
  sortMode: SortMode,
  interval: TestHeatmapInterval,
  favouriteKeys: Set<string>,
  favouritesFirst = false,
) {
  return [...items].sort((a, b) => {
    if (favouritesFirst) {
      const favCompare = Number(favouriteKeys.has(getFavouriteKey(b))) - Number(favouriteKeys.has(getFavouriteKey(a)));
      if (favCompare !== 0) {
        return favCompare;
      }
    }
    switch (sortMode) {
      case 'lowestReturn':
        return a.returns[interval] - b.returns[interval];
      case 'strongestRelativeStrength':
        return b.relativeStrength - a.relativeStrength;
      case 'strongestRelativeMomentum':
        return b.relativeMomentum - a.relativeMomentum;
      case 'bestBreadth':
        return b.breadth.percentAbove50Ema - a.breadth.percentAbove50Ema;
      case 'highestConcentration':
        return calculateLeadershipConcentration(b).concentrationScore - calculateLeadershipConcentration(a).concentrationScore;
      case 'lowestConcentration':
        return calculateLeadershipConcentration(a).concentrationScore - calculateLeadershipConcentration(b).concentrationScore;
      case 'alphabetical':
        return a.name.localeCompare(b.name);
      case 'highestReturn':
      default:
        return b.returns[interval] - a.returns[interval];
    }
  });
}

export function countActiveFilters(filters: SectorThemeFilters) {
  return [
    filters.breadth !== 'all',
    filters.favouriteMode !== 'all',
    filters.performance !== 'all',
    filters.quadrant !== 'all',
    filters.sortMode !== DEFAULT_SECTOR_THEME_FILTERS.sortMode,
  ].filter(Boolean).length;
}
