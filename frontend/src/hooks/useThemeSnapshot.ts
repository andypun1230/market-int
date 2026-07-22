import { useCallback } from 'react';

import { adaptThemeSnapshot, type ThemeSnapshotModel } from '@/features/themes/themeSnapshot';
import { getThemeSnapshot } from '@/services/api';
import { useAsyncData } from './useAsyncData';

export function useThemeSnapshot(enabled = true) {
  const fetchSnapshot = useCallback(async () => adaptThemeSnapshot(await getThemeSnapshot()), []);
  const result = useAsyncData(fetchSnapshot, { enabled });
  return { ...result, snapshot: result.data as ThemeSnapshotModel | null };
}
