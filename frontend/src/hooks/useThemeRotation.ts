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
  const fetchRotation = useCallback(async (signal?: AbortSignal) => {
    const identity = snapshotId && taxonomyVersion ? { snapshotId, taxonomyVersion } : undefined;
    return adaptThemeRotation(await getThemeRotation(timeframe, identity, signal));
  }, [snapshotId, taxonomyVersion, timeframe]);
  const result = useAsyncData(fetchRotation, { enabled });
  const identityMatches = !snapshotId || !taxonomyVersion || (
    result.data?.snapshotId === snapshotId && result.data?.taxonomyVersion === taxonomyVersion
  );
  const current = identityMatches && result.data?.timeframe === timeframe && result.data?.modelVersion === THEME_ROTATION_MODEL_VERSION
    ? result.data as ThemeRotationModel
    : null;
  const waitingForCurrentIdentity = enabled && current === null && result.error === null;
  return { ...result, data: current, loading: result.loading || waitingForCurrentIdentity, rotation: current };
}
