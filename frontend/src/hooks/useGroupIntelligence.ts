import { useCallback } from "react";

import type {
  BreadthHistoryTimeframe,
  CanonicalGroupTimeframe,
  CanonicalGroupType,
} from "@/features/sectors/groupIntelligence";
import {
  getCanonicalBreadthHistory,
  getCanonicalDivergences,
  getCanonicalGroupComparison,
  getCanonicalGroupRegistry,
  getCanonicalSectorAlerts,
} from "@/services/api";
import { useAsyncData } from "@/hooks/useAsyncData";

export function useCanonicalGroupRegistry(entityType: CanonicalGroupType, enabled = true) {
  const fetcher = useCallback(() => getCanonicalGroupRegistry(entityType), [entityType]);
  return useAsyncData(fetcher, { enabled });
}

export function useCanonicalGroupComparison(
  entityType: CanonicalGroupType,
  ids: string[],
  timeframe: CanonicalGroupTimeframe,
  enabled = true,
) {
  const key = [...new Set(ids)].sort().join(",");
  const fetcher = useCallback(
    () => getCanonicalGroupComparison(entityType, key.split(",").filter(Boolean), timeframe),
    [entityType, key, timeframe],
  );
  return useAsyncData(fetcher, { enabled: enabled && ids.length >= 2 });
}

export function useCanonicalBreadthHistory(
  entityType: CanonicalGroupType,
  entityId: string,
  timeframe: BreadthHistoryTimeframe,
  enabled = true,
) {
  const fetcher = useCallback(
    () => getCanonicalBreadthHistory(entityType, entityId, timeframe),
    [entityId, entityType, timeframe],
  );
  return useAsyncData(fetcher, { enabled: enabled && Boolean(entityId) });
}

export function useCanonicalDivergences(
  entityType: CanonicalGroupType,
  entityId: string,
  timeframe: BreadthHistoryTimeframe,
  enabled = true,
) {
  const fetcher = useCallback(
    () => getCanonicalDivergences(entityType, entityId, timeframe),
    [entityId, entityType, timeframe],
  );
  return useAsyncData(fetcher, { enabled: enabled && Boolean(entityId) });
}

export function useCanonicalSectorAlerts(enabled = true) {
  const fetcher = useCallback(() => getCanonicalSectorAlerts(), []);
  return useAsyncData(fetcher, { enabled });
}
