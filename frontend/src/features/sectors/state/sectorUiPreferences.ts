import { useCallback, useState } from 'react';

import type { SectorUiPreferences } from '@/features/sectors/types';

const DEFAULT_SECTOR_UI_PREFERENCES: SectorUiPreferences = {
  activeSection: 'sectorHeatmap',
  detailBreadthInterval: '1M',
  detailRotationInterval: '3M',
  sectorHeatmapInterval: '1W',
  sectorRotationInterval: '1M',
  sectorRotationLabelMode: 'smart',
  sectorRotationQuadrant: 'all',
  themeHeatmapInterval: '1W',
  themeRotationInterval: '1M',
  themeRotationLabelMode: 'smart',
  themeRotationMovement: 'meaningful',
  themeRotationQuadrant: 'all',
  themeRotationTailLength: '5',
  themeRotationUniverse: 'all',
};

let sessionPreferences: SectorUiPreferences = DEFAULT_SECTOR_UI_PREFERENCES;

export function useSectorUiPreferences() {
  const [preferences, setPreferences] = useState(sessionPreferences);
  const updatePreferences = useCallback((patch: Partial<SectorUiPreferences>) => {
    sessionPreferences = { ...sessionPreferences, ...patch };
    setPreferences(sessionPreferences);
  }, []);

  return [preferences, updatePreferences] as const;
}

export function resetSectorUiPreferencesForTests() {
  sessionPreferences = DEFAULT_SECTOR_UI_PREFERENCES;
}
