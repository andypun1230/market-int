import { useCallback, useMemo } from 'react';

import {
  getHomeDashboard,
} from '@/services/api';
import type {
  DecisionDashboardResponse,
  FearGreedResponse,
  HomeDashboardResponse,
  MarketAISummary,
  MarketBrief,
  MarketCapRotationResponse,
  RiskResponse,
  StockRatingItem,
} from '@/types/market';

import { useAsyncData } from './useAsyncData';

type HomeDashboardData = {
  dashboard: HomeDashboardResponse;
  error: string | null;
};

const EMPTY_COMPONENTS = {
  relative_strength: 0,
  pattern_quality: 0,
  sector_strength: 0,
  market_alignment: 0,
  institutional_support: 0,
  risk_control: 0,
};

export function useHomeDashboard(enabled = true) {
  const fetchHomeDashboard = useCallback(async (): Promise<HomeDashboardData> => {
    try {
      return {
        dashboard: await getHomeDashboard(),
        error: null,
      };
    } catch (error) {
      console.log('Home dashboard API error:', error);
      throw error;
    }
  }, []);

  const { data, loading, error, refetch } = useAsyncData(fetchHomeDashboard, { enabled });
  const dashboard = data?.dashboard ?? null;

  const brief = useMemo(() => buildBrief(dashboard), [dashboard]);
  const risk = useMemo(() => buildRisk(dashboard), [dashboard]);
  const stockRatings = useMemo(() => buildStockRatings(dashboard), [dashboard]);
  const stockRatingsSummary = stockRatings.length
    ? 'Compact watchlist summary from the fast Home dashboard.'
    : null;

  return {
    brief,
    risk,
    aiSummary: null as MarketAISummary | null,
    decisionDashboard: null as DecisionDashboardResponse | null,
    homeDashboard: dashboard,
    marketHealth: dashboard?.core.market_health ?? null,
    capRotation: null as MarketCapRotationResponse | null,
    fearGreed: null as FearGreedResponse | null,
    stockRatings,
    stockRatingsSummary,
    loading,
    stockRatingsLoading: loading,
    error: data?.error ?? error,
    stockRatingsError: stockRatings.length ? null : 'Stock ratings unavailable',
    refetch,
  };
}

function buildBrief(dashboard: HomeDashboardResponse | null): MarketBrief | null {
  if (!dashboard) {
    return null;
  }

  const core = dashboard.core;
  const topSector = core.top_sector?.name;
  const topGroup = core.top_industry_group?.name;
  const playbook = core.decision_summary.playbook;
  const marketHealth = core.market_health;

  return {
    regime: marketHealth?.status ?? 'Unavailable',
    drivers: [
      topSector ? `${topSector} sector leadership` : null,
      topGroup ? `${topGroup} industry group leadership` : null,
      core.decision_summary.preferred_style,
    ].filter((item): item is string => Boolean(item)),
    risks: [core.decision_summary.main_risk].filter((item): item is string => Boolean(item)),
    top_sectors: [topSector, topGroup].filter((item): item is string => Boolean(item)),
    summary: playbook?.summary ?? marketHealth?.summary ?? 'Market dashboard is updating.',
  };
}

function buildRisk(dashboard: HomeDashboardResponse | null): RiskResponse | null {
  if (!dashboard) {
    return null;
  }

  return {
    risk_level: dashboard.risk_summary.status ?? 'N/A',
    main_risks: [
      dashboard.risk_summary.summary,
      ...dashboard.risk_summary.top_contributors.map((item) => item.explanation),
    ].filter((item): item is string => Boolean(item)),
    suggested_positioning:
      dashboard.core.decision_summary.playbook?.summary ?? 'Positioning guidance is updating.',
  };
}

function buildStockRatings(dashboard: HomeDashboardResponse | null): StockRatingItem[] {
  return (dashboard?.watchlist_summary.items ?? []).map((item, index) => ({
    symbol: item.symbol,
    overall_score: item.score ?? 0,
    rating: item.rating ?? 'N/A',
    status: item.main_setup ?? 'Watchlist Candidate',
    components: EMPTY_COMPONENTS,
    risk_level: 'N/A',
    strengths: [item.main_setup ?? 'Compact setup summary'],
    warnings: [],
    explanation: `${item.symbol} compact Home summary from ${item.source ?? 'backend'}.`,
    data_quality: {
      overall_mode: item.is_live ? 'live' : item.fallback_used ? 'mixed' : 'mock',
      live_components: item.is_live ? ['quote'] : [],
      fallback_components: item.fallback_used ? ['quote'] : [],
      mock_components: item.is_live ? [] : ['quote'],
    },
  })).sort((a, b) => (b.overall_score - a.overall_score) || a.symbol.localeCompare(b.symbol));
}
