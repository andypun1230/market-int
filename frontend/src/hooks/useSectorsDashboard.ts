import { useCallback, useMemo } from 'react';

import { getSectorDashboard } from '@/services/api';
import type { SectorDashboardResponse } from '@/types/market';
import { normalizeSectorDashboardResponse } from '@/utils/sectorDashboardNormalizers';

import { useAsyncData } from './useAsyncData';

type SectorsDashboardData = {
  dashboard: SectorDashboardResponse;
  error: string | null;
};

export function useSectorsDashboard(enabled = true) {
  const fetchDashboard = useCallback(async (): Promise<SectorsDashboardData> => {
    try {
      return {
        dashboard: normalizeSectorDashboardResponse(await getSectorDashboard()),
        error: null,
      };
    } catch (error) {
      console.error('Sector dashboard API error:', error);
      throw error;
    }
  }, []);

  const { data, loading, error, refetch } = useAsyncData(fetchDashboard, { enabled });
  const dashboard = data?.dashboard ?? null;
  const sectors = useMemo(() => dashboard?.sectors ?? [], [dashboard]);
  const themes = useMemo(() => dashboard?.themes ?? [], [dashboard]);

  return {
    benchmark: dashboard?.benchmark ?? 'SPY',
    dashboard,
    error: data?.error ?? error,
    loading,
    refetch,
    sectors,
    source: dashboard?.source ?? null,
    themes,
  };
}
