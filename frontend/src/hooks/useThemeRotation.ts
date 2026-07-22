import { useCallback } from 'react';

import { adaptThemeRotation, THEME_ROTATION_MODEL_VERSION, type ThemeRotationModel } from '@/features/themes/themeRotation';
import type { ThemeRotationInterval, ThemeSnapshotModel } from '@/features/themes/themeSnapshot';
import { getThemeRotation } from '@/services/api';
import { useAsyncData } from './useAsyncData';

export function useThemeRotation(
  timeframe: ThemeRotationInterval,
  snapshot: ThemeSnapshotModel | null,
  enabled = true,
) {
  const snapshotId = snapshot?.snapshotId ?? '';
  const taxonomyVersion = snapshot?.taxonomyVersion ?? '';
  const fetchRotation = useCallback(async () => {
    if (!snapshotId || !taxonomyVersion) return null;
    return adaptThemeRotation(await getThemeRotation(timeframe, { snapshotId, taxonomyVersion }));
  }, [snapshotId, taxonomyVersion, timeframe]);
  const result = useAsyncData(fetchRotation, { enabled: enabled && Boolean(snapshotId && taxonomyVersion) });
  const current = result.data?.snapshotId === snapshotId && result.data?.taxonomyVersion === taxonomyVersion && result.data?.timeframe === timeframe && result.data?.modelVersion === THEME_ROTATION_MODEL_VERSION
    ? result.data as ThemeRotationModel
    : null;
  const waitingForCurrentIdentity = enabled && Boolean(snapshotId && taxonomyVersion) && current === null && result.error === null;
  return { ...result, data: current, loading: result.loading || waitingForCurrentIdentity, rotation: current };
}
