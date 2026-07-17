import { useCallback } from 'react';

import {
  getStockAnalysis,
} from '@/services/api';
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

  return useAsyncData(fetchDetails, { enabled });
}
