import { useCallback } from 'react';

import { getThemeStatus } from '@/services/api';
import type { ThemeStatusResponse } from '@/types/market';
import { useAsyncData } from './useAsyncData';

export function useThemeStatus(enabled = true) {
  const fetchStatus = useCallback(() => getThemeStatus(), []);
  const result = useAsyncData(fetchStatus, { enabled });
  return { ...result, status: result.data as ThemeStatusResponse | null };
}
