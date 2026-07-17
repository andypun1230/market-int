import { useCallback, useMemo } from 'react';

import {
  getWatchlistSummary,
} from '@/services/api';
import type {
  DetectedPattern,
  MultiTimeframeItem,
  RelativeStrengthItem,
  RiskPlan,
  StockRatingItem,
  SupportResistanceResponse,
  TrendlineResponse,
  VolumeAnalysis,
  WatchlistResponse,
  WatchlistSummaryItem,
} from '@/types/market';

import { useAsyncData } from './useAsyncData';

const EMPTY_PATTERNS: DetectedPattern[] = [];
const EMPTY_RELATIVE_STRENGTH: RelativeStrengthItem[] = [];
const EMPTY_STOCK_RATINGS: StockRatingItem[] = [];
const EMPTY_SUPPORT_RESISTANCE: Record<string, SupportResistanceResponse> = {};
const EMPTY_TRENDLINES_BY_SYMBOL: Record<string, TrendlineResponse> = {};
const EMPTY_VOLUME_BY_SYMBOL: Record<string, VolumeAnalysis> = {};
const EMPTY_RISK_PLANS_BY_SYMBOL: Record<string, RiskPlan> = {};
const EMPTY_MULTI_TIMEFRAMES_BY_SYMBOL: Record<string, MultiTimeframeItem> = {};

type WatchlistDashboardData = {
  watchlist: WatchlistResponse | null;
  patterns: DetectedPattern[];
  relativeStrength: RelativeStrengthItem[];
  stockRatings: StockRatingItem[];
  error: string | null;
  patternsError: string | null;
  relativeStrengthError: string | null;
  stockRatingsError: string | null;
};

export function useWatchlistDashboard(enabled = true) {
  const fetchWatchlistDashboard = useCallback(async (): Promise<WatchlistDashboardData> => {
    const summary = await getWatchlistSummary();
    const items = summary.items ?? [];

    return {
      watchlist: { items },
      patterns: buildPatternSummaries(items),
      relativeStrength: buildRelativeStrengthSummaries(items),
      stockRatings: buildRatingSummaries(items),
      error: null,
      patternsError: null,
      relativeStrengthError: null,
      stockRatingsError: null,
    };
  }, []);

  const { data, loading, error, refetch } = useAsyncData(fetchWatchlistDashboard, { enabled });
  const relativeStrength = data?.relativeStrength ?? EMPTY_RELATIVE_STRENGTH;
  const stockRatings = data?.stockRatings ?? EMPTY_STOCK_RATINGS;
  const patterns = data?.patterns ?? EMPTY_PATTERNS;

  const relativeStrengthBySymbol = useMemo(() => mapBySymbol(relativeStrength), [relativeStrength]);
  const stockRatingsBySymbol = useMemo(() => mapBySymbol(stockRatings), [stockRatings]);
  const patternsBySymbol = useMemo(() => groupPatternsBySymbol(patterns), [patterns]);
  const topRatedSymbol = useMemo(() => stockRatings[0]?.symbol, [stockRatings]);

  return {
    watchlist: data?.watchlist ?? null,
    patterns,
    relativeStrength,
    stockRatings,
    supportResistance: EMPTY_SUPPORT_RESISTANCE,
    trendlines: [],
    volumeAnalyses: [],
    riskPlans: [],
    multiTimeframes: [],
    relativeStrengthBySymbol,
    stockRatingsBySymbol,
    trendlinesBySymbol: EMPTY_TRENDLINES_BY_SYMBOL,
    volumeBySymbol: EMPTY_VOLUME_BY_SYMBOL,
    riskPlansBySymbol: EMPTY_RISK_PLANS_BY_SYMBOL,
    multiTimeframesBySymbol: EMPTY_MULTI_TIMEFRAMES_BY_SYMBOL,
    patternsBySymbol,
    topRatedSymbol,
    loading,
    patternsLoading: loading,
    relativeStrengthLoading: loading,
    stockRatingsLoading: loading,
    error: data?.error ?? error,
    patternsError: data?.patternsError ?? null,
    relativeStrengthError: data?.relativeStrengthError ?? null,
    stockRatingsError: data?.stockRatingsError ?? null,
    refetch,
  };
}

function mapBySymbol<T extends { symbol: string }>(items: T[]) {
  return items.reduce<Record<string, T>>((lookup, item) => {
    lookup[item.symbol] = item;
    return lookup;
  }, {});
}

function groupPatternsBySymbol(items: DetectedPattern[]) {
  return items.reduce<Record<string, DetectedPattern[]>>((lookup, item) => {
    lookup[item.symbol] = [...(lookup[item.symbol] ?? []), item];
    return lookup;
  }, {});
}

function buildPatternSummaries(items: WatchlistSummaryItem[]): DetectedPattern[] {
  return items
    .filter((item) => item.pattern_name)
    .map((item) => ({
      id: `${item.ticker}-summary-pattern`,
      symbol: item.ticker,
      name: item.pattern_name ?? 'Setup',
      type: 'summary',
      direction: 'Bullish',
      status: item.setup ?? 'Setup',
      confidence: item.pattern_confidence ?? 0,
      timeframe: 'Daily',
      description: item.setup ?? 'Compact setup summary.',
      key_levels: {
        breakout: null,
        support: null,
        resistance: null,
        stop_reference: null,
      },
      chart_data: [],
      markers: [],
      data_source: item.data_source,
      is_live: item.is_live,
    }));
}

function buildRelativeStrengthSummaries(items: WatchlistSummaryItem[]): RelativeStrengthItem[] {
  return items
    .filter((item) => item.rs_rank || item.rs_status)
    .map((item) => ({
      symbol: item.ticker,
      sector: 'N/A',
      rs_vs_spy: 0,
      rs_vs_qqq: 0,
      rs_vs_sector: 0,
      return_5d: 0,
      return_20d: 0,
      return_60d: 0,
      benchmark_return_20d: 0,
      sector_return_20d: 0,
      overall_rs_score: 0,
      rank: item.rs_rank ?? 0,
      status: item.rs_status ?? 'N/A',
      explanation: 'Compact relative-strength summary. Open analysis for full detail.',
      data_source: item.data_source,
      analysis_is_live: item.is_live,
      fallback_used: item.fallback_used,
      as_of: item.as_of,
    }));
}

function buildRatingSummaries(items: WatchlistSummaryItem[]): StockRatingItem[] {
  return items
    .filter((item) => item.rating || item.overall_score)
    .map((item) => ({
      symbol: item.ticker,
      overall_score: item.overall_score ?? 0,
      rating: item.rating ?? 'N/A',
      status: item.trend ?? 'Watchlist',
      components: {
        relative_strength: 0,
        pattern_quality: 0,
        sector_strength: 0,
        market_alignment: 0,
        institutional_support: 0,
        risk_control: 0,
      },
      risk_level: item.risk_flag ?? 'N/A',
      strengths: [item.setup ?? 'Compact setup summary'],
      warnings: [],
      explanation: 'Compact rating summary. Open analysis for full detail.',
      data_quality: {
        overall_mode: item.is_live ? 'live' : item.fallback_used ? 'mixed' : 'mock',
        live_components: item.is_live ? ['quote'] : [],
        fallback_components: item.fallback_used ? ['quote'] : [],
        mock_components: item.is_live ? [] : ['quote'],
      },
    }));
}
