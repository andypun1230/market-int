import { useCallback, useMemo } from 'react';

import { contextIntelligenceClient } from '@/features/context-intelligence/client';
import { useAsyncData } from '@/hooks/useAsyncData';
import { normalizeIntelligenceSymbols } from '@/services/api';

export function useMarketNewsIntelligence(enabled: boolean, limit = 5) {
  const load = useCallback(
    () => contextIntelligenceClient.marketNews(limit),
    [limit],
  );
  return useAsyncData(load, { enabled });
}

export function useMarketSessionNarrative(enabled: boolean, interval: '5m' | '15m' = '5m') {
  const load = useCallback(
    () => contextIntelligenceClient.marketSession(interval),
    [interval],
  );
  return useAsyncData(load, { enabled });
}

export function useSecurityNewsIntelligence(symbol: string, enabled: boolean, limit = 5) {
  const normalizedSymbol = symbol.trim().toUpperCase();
  const load = useCallback(
    () => contextIntelligenceClient.securityNews(normalizedSymbol, limit),
    [limit, normalizedSymbol],
  );
  return useAsyncData(load, { enabled: enabled && Boolean(normalizedSymbol) });
}

export function useEntityNewsIntelligence(
  kind: 'sector' | 'theme',
  entityId: string,
  enabled: boolean,
  limit = 5,
) {
  const normalizedId = entityId.trim().toLowerCase();
  const load = useCallback(
    () => kind === 'sector'
      ? contextIntelligenceClient.sectorNews(normalizedId, limit)
      : contextIntelligenceClient.themeNews(normalizedId, limit),
    [kind, limit, normalizedId],
  );
  return useAsyncData(load, { enabled: enabled && Boolean(normalizedId) });
}

export function useWatchlistNewsIntelligence(symbols: string[], enabled: boolean, limit = 10) {
  const symbolKey = normalizeIntelligenceSymbols(symbols).join(',');
  const normalizedSymbols = useMemo(
    () => symbolKey ? symbolKey.split(',') : [],
    [symbolKey],
  );
  const load = useCallback(
    () => contextIntelligenceClient.watchlistNews(normalizedSymbols, limit),
    [limit, normalizedSymbols],
  );
  return useAsyncData(load, { enabled: enabled && normalizedSymbols.length > 0 });
}
