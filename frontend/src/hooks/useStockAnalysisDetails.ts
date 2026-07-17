import { useCallback, useEffect } from 'react';

import {
  getStockAnalysis,
} from '@/services/api';
import { clearRequestCache } from '@/services/requestCache';
import {
  normalizeStockAnalysisDetails,
  type StockAnalysisDetails,
} from '@/features/stock-detail/stockAnalysisDetailsNormalizer';

import { useAsyncData } from './useAsyncData';

export function useStockAnalysisDetails(symbol: string, enabled: boolean) {
  const fetchDetails = useCallback(async (): Promise<StockAnalysisDetails> => {
    const aggregate = await getStockAnalysis(symbol);
    return normalizeStockAnalysisDetails(aggregate);
  }, [symbol]);

  const state = useAsyncData(fetchDetails, { enabled });

  useEffect(() => {
    if (!enabled || !state.data?.snapshotRefreshing) {
      return undefined;
    }
    const timeout = setTimeout(async () => {
      clearRequestCache(`stock-analysis:v3:${symbol.toUpperCase()}`);
      const aggregate = await getStockAnalysis(symbol, { bypassCache: true });
      state.refetch();
      return normalizeStockAnalysisDetails(aggregate);
    }, 1250);
    return () => clearTimeout(timeout);
  }, [enabled, state, state.data?.snapshotRefreshing, symbol]);

  return state;
}
