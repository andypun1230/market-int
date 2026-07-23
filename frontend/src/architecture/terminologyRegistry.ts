export const TERMINOLOGY = {
  actions: {
    clear: 'Clear',
    compare: 'Compare',
    generateReport: 'Generate report',
    refresh: 'Refresh',
    remove: 'Remove',
    resetFilters: 'Reset filters',
    retry: 'Retry',
    save: 'Save',
    viewDetails: 'View details',
  },
  availability: {
    available: 'Available',
    failed: 'Failed',
    live: 'Live',
    liveCached: 'Live with cached data',
    partial: 'Partial',
    stale: 'Stale',
    unavailable: 'Unavailable',
  },
  empty: {
    noAlerts: 'No alerts',
    noMatchingResults: 'No matching results',
    noSavedSectors: 'No saved sectors',
    noSavedStocks: 'No saved stocks',
    noSavedThemes: 'No saved themes',
    reportNotGenerated: 'Report not generated',
  },
} as const;

export function availabilityTerm(value?: string | null) {
  const normalized = value?.trim().toLowerCase().replace(/[_-]+/g, ' ');
  if (!normalized) return TERMINOLOGY.availability.unavailable;
  if (normalized === 'live') return TERMINOLOGY.availability.live;
  if (normalized === 'live with cached data' || normalized === 'cached') return TERMINOLOGY.availability.liveCached;
  if (normalized === 'available' || normalized === 'ready') return TERMINOLOGY.availability.available;
  if (normalized === 'partial' || normalized === 'partial data' || normalized === 'mixed') return TERMINOLOGY.availability.partial;
  if (normalized === 'stale' || normalized === 'delayed') return TERMINOLOGY.availability.stale;
  if (normalized === 'failed' || normalized === 'error') return TERMINOLOGY.availability.failed;
  if (normalized === 'unavailable' || normalized === 'n/a' || normalized === 'not available') {
    return TERMINOLOGY.availability.unavailable;
  }
  return normalized.split(' ').map((part) => part ? part[0].toUpperCase() + part.slice(1) : part).join(' ');
}
