import { useCallback, useState } from 'react';

import {
  getFearGreed,
  getInstitutionalActivity,
  getMarketCapRotation,
  getMarketCoreSnapshot,
  getMarketBreadth,
  getDecisionDashboard,
  getMarketDecisionDetails,
  getMarketInstitutionalDetails,
  getMarketRegime,
  getMarketStructureDetails,
} from '@/services/api';
import type {
  DecisionDashboardResponse,
  FearGreedResponse,
  IndexSnapshot,
  InstitutionalActivityResponse,
  InstitutionalIntelligenceResponse,
  MarketAISummary,
  MarketBreadthResponse,
  MarketCapRotationResponse,
  MarketCoreSnapshot,
  MarketHealthResponse,
  MarketRegime,
} from '@/types/market';
import { isRequestCancelled } from '@/services/requestCache';
import {
  normalizeBreadthResponse,
  normalizeDecisionIntelligenceResponse,
  normalizeInstitutionalActivityResponse,
  normalizeInstitutionalIntelligenceResponse,
} from '@/utils/marketDataNormalizers';

import { useAsyncData } from './useAsyncData';

type MarketDashboardData = {
  core: MarketCoreSnapshot;
  error: string | null;
};

type MarketDetailState = {
  breadth: MarketBreadthResponse | null;
  capRotation: MarketCapRotationResponse | null;
  decisionDashboard: DecisionDashboardResponse | null;
  fearGreed: FearGreedResponse | null;
  institutionalActivity: InstitutionalActivityResponse | null;
  institutionalIntelligence: InstitutionalIntelligenceResponse | null;
  regime: MarketRegime | null;
};

type DetailGroup = 'structure' | 'decision' | 'institutional';

const EMPTY_DETAILS: MarketDetailState = {
  breadth: null,
  capRotation: null,
  decisionDashboard: null,
  fearGreed: null,
  institutionalActivity: null,
  institutionalIntelligence: null,
  regime: null,
};

export function useMarketDashboard(enabled = true) {
  const [details, setDetails] = useState<MarketDetailState>(EMPTY_DETAILS);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [loadedDetailGroups, setLoadedDetailGroups] = useState<Record<DetailGroup, boolean>>({
    decision: false,
    institutional: false,
    structure: false,
  });
  const [detailsError, setDetailsError] = useState<string | null>(null);

  const fetchMarketCore = useCallback(async (): Promise<MarketDashboardData> => {
    try {
      return {
        core: await getMarketCoreSnapshot(),
        error: null,
      };
    } catch (error) {
      console.log('Market core snapshot API error:', error);
      throw error;
    }
  }, []);

  const { data, loading, error, refetch } = useAsyncData(fetchMarketCore, { enabled });
  const core = data?.core ?? null;

  const loadDetails = useCallback(async (group: DetailGroup) => {
    if (!enabled || loadedDetailGroups[group] || detailsLoading) {
      return;
    }

    setDetailsLoading(true);
    setDetailsError(null);
    let nextDetails: Partial<MarketDetailState> = {};
    let failed = false;
    if (group === 'structure') {
      const result = await getSettled(getMarketStructureDetails, 'Market structure details API error:');
      let normalizedBreadth = normalizeBreadthResponse(result);
      if (!normalizedBreadth) {
        normalizedBreadth = await getSettled(getMarketBreadth, 'Market breadth fallback API error:');
      }
      if (normalizedBreadth) {
        nextDetails = { breadth: normalizedBreadth };
      } else {
        failed = true;
      }
    } else if (group === 'decision') {
      const [decisionResult, regimeResult, capRotationResult, fearGreedResult] = await Promise.allSettled([
        getMarketDecisionDetails(),
        getMarketRegime(),
        getMarketCapRotation(),
        getFearGreed(),
      ]);
      logRejected('Market decision details API error:', decisionResult);
      logRejected('Market regime API error:', regimeResult);
      logRejected('Market cap rotation API error:', capRotationResult);
      logRejected('Fear & Greed API error:', fearGreedResult);
      let decisionDashboard =
        decisionResult.status === 'fulfilled'
          ? normalizeDecisionIntelligenceResponse(decisionResult.value)
          : null;
      if (!decisionDashboard) {
        decisionDashboard = await getSettled(getDecisionDashboard, 'Decision dashboard fallback API error:');
      }
      nextDetails = {
        decisionDashboard,
        regime: regimeResult.status === 'fulfilled' ? regimeResult.value : null,
        capRotation: capRotationResult.status === 'fulfilled' ? capRotationResult.value : null,
        fearGreed: fearGreedResult.status === 'fulfilled' ? fearGreedResult.value : null,
      };
      failed = !decisionDashboard;
    } else {
      const result = await getSettled(getMarketInstitutionalDetails, 'Market institutional details API error:');
      let institutionalActivity = normalizeInstitutionalActivityResponse(result);
      let institutionalIntelligence = normalizeInstitutionalIntelligenceResponse(result);
      if (!institutionalActivity) {
        institutionalActivity = await getSettled(getInstitutionalActivity, 'Institutional activity fallback API error:');
      }
      if (result) {
        nextDetails = {
          institutionalActivity,
          institutionalIntelligence,
        };
      }
      if (!institutionalActivity && !institutionalIntelligence) {
        failed = true;
      }
    }

    setDetails((previous) => ({ ...previous, ...nextDetails }));
    setLoadedDetailGroups((previous) => ({ ...previous, [group]: true }));
    setDetailsLoading(false);
    if (failed) {
      setDetailsError('Some market detail sections are unavailable.');
    }
  }, [detailsLoading, enabled, loadedDetailGroups]);

  const refresh = useCallback(async () => {
    setLoadedDetailGroups({ decision: false, institutional: false, structure: false });
    setDetails(EMPTY_DETAILS);
    await refetch();
  }, [refetch]);

  return {
    regime: details.regime,
    indexes: core?.indexes ?? ([] as IndexSnapshot[]),
    breadth: details.breadth,
    institutionalActivity: details.institutionalActivity,
    institutionalIntelligence: details.institutionalIntelligence,
    aiSummary: null as MarketAISummary | null,
    decisionDashboard: details.decisionDashboard,
    marketHealth: core?.market_health ?? (null as MarketHealthResponse | null),
    capRotation: details.capRotation,
    fearGreed: details.fearGreed,
    core,
    loading,
    detailsLoading,
    detailsError,
    loadDetails,
    error: data?.error ?? error,
    refetch: refresh,
  };
}

function logRejected<T>(label: string, result: PromiseSettledResult<T>) {
  if (result.status === 'rejected') {
    if (!isRequestCancelled(result.reason)) {
      console.error(label, result.reason);
    }
  }
}

async function getSettled<T>(fetcher: () => Promise<T>, label: string): Promise<T | null> {
  try {
    return await fetcher();
  } catch (error) {
    if (!isRequestCancelled(error)) {
      console.error(label, error);
    }
    return null;
  }
}
