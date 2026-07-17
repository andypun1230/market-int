import { useCallback } from 'react';

import { getDailyReport } from '@/services/api';
import type { DailyReport, InstitutionalActivityBias } from '@/types/market';

import { useAsyncData } from './useAsyncData';

export type DailyReportWithInstitutionalActivity = DailyReport & {
  institutional_activity?: InstitutionalActivityBias;
};

export function useReportDashboard(enabled = true) {
  const fetchReport = useCallback(() => getDailyReport() as Promise<DailyReportWithInstitutionalActivity>, []);
  const { data, loading, error, refetch } = useAsyncData(fetchReport, { enabled });

  return {
    report: data,
    loading,
    error: error ? 'Unable to load daily report. Check that the backend is running.' : null,
    refetch,
  };
}
