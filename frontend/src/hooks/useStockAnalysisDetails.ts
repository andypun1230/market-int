import { useCallback, useEffect, useRef } from 'react';

import {
  getStockAnalysis,
  getSymbolThemeMappings,
  getLiveQuote,
} from '@/services/api';
import { clearRequestCache } from '@/services/requestCache';
import {
  normalizeStockAnalysisDetails,
  type StockAnalysisDetails,
} from '@/features/stock-detail/stockAnalysisDetailsNormalizer';

import { useAsyncData } from './useAsyncData';
import type { SymbolThemeMappingsResponse } from '@/types/market';

export type StockAnalysisDetailsWithThemes = StockAnalysisDetails & {
  themeMappings: SymbolThemeMappingsResponse | null;
};

export function useStockAnalysisDetails(symbol: string, enabled: boolean) {
  const fetchDetails = useCallback(async (): Promise<StockAnalysisDetailsWithThemes> => {
    const [aggregate, liveQuote, themeMappings] = await Promise.all([
      getStockAnalysis(symbol),
      getLiveQuote(symbol).catch(() => null),
      getSymbolThemeMappings(symbol).catch(() => null),
    ]);
    return { ...normalizeStockAnalysisDetails(aggregate, liveQuote), themeMappings };
  }, [symbol]);

  const state = useAsyncData(fetchDetails, { enabled });
  const { data, refetch } = state;
  const refreshScheduledForRef = useRef<string | null>(null);

  useEffect(() => {
    if (!enabled || !data?.snapshotRefreshing) {
      refreshScheduledForRef.current = null;
      return undefined;
    }
    const refreshKey = `${symbol.toUpperCase()}:${data.snapshotStatus ?? 'initializing'}:${data.currentPrice.price ?? 'none'}`;
    if (refreshScheduledForRef.current === refreshKey) {
      return undefined;
    }
    refreshScheduledForRef.current = refreshKey;
    const timeout = setTimeout(async () => {
      clearRequestCache(`stock-analysis:v3:${symbol.toUpperCase()}`);
      refetch();
    }, 1250);
    return () => clearTimeout(timeout);
  }, [data?.currentPrice.price, data?.snapshotRefreshing, data?.snapshotStatus, enabled, refetch, symbol]);

  return state;
}
