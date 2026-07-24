import { useCallback } from 'react';

import { adaptThemeDetail, type ThemeSnapshotModel } from '@/features/themes/themeSnapshot';
import { getThemeDetail } from '@/services/api';

import { useAsyncData } from './useAsyncData';

export function useThemeDetail(
  themeId: string | null,
  snapshot: ThemeSnapshotModel | null,
  enabled = true,
) {
  const snapshotId = snapshot?.snapshotId ?? '';
  const taxonomyVersion = snapshot?.taxonomyVersion ?? '';
  const fetchDetail = useCallback(async (signal?: AbortSignal) => {
    if (!themeId || !snapshotId || !taxonomyVersion) return null;
    return adaptThemeDetail(await getThemeDetail(themeId, { snapshotId, taxonomyVersion }, signal));
  }, [snapshotId, taxonomyVersion, themeId]);
  const result = useAsyncData(fetchDetail, {
    enabled: enabled && Boolean(themeId && snapshotId && taxonomyVersion),
  });
  const detail = result.data?.snapshotId === snapshotId && result.data?.taxonomyVersion === taxonomyVersion
    ? result.data
    : null;
  return { ...result, detail };
}
