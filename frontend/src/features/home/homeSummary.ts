import type { HistoryData, HomeDashboardResponse, IndexSnapshot } from '@/types/market';
import {
  buildMarketPostureProjection,
  type MarketPostureLabel,
  type MarketPostureProjection,
} from '@/features/market/marketPostureProjection';

export type HomeSourceState = 'live' | 'cached' | 'mock' | 'unavailable';
export type HomeTone = 'positive' | 'warning' | 'negative' | 'neutral';
export type MarketPulseLabel = MarketPostureLabel;

export type HomeIndexSnapshot = {
  changePercent: number | null;
  direction: 'up' | 'down' | 'flat' | 'unavailable';
  sparkline: number[];
  symbol: string;
  trendLabel: string | null;
};

export type HomeMetric = {
  direction: string | null;
  label: string;
  score: number | null;
  tone: HomeTone;
  value: string;
};

export type HomeLeadershipItem = {
  direction: string | null;
  id: string | null;
  kind: 'sector' | 'theme';
  label: string;
  role: 'Leading Sector' | 'Leading Theme' | 'Lagging Sector';
  tone: HomeTone;
};

export type HomeStockIdea = {
  changePercent: number | null;
  symbol: string;
};

export type HomeDailyInsight = {
  category: string;
  headline: string;
  summary: string;
};

export type HomeMarketPulse = MarketPostureProjection;

export type HomeSummary = {
  breadth: HomeMetric | null;
  dailyInsight: HomeDailyInsight | null;
  healthLabel: string;
  healthScore: number | null;
  indexes: HomeIndexSnapshot[];
  leadership: HomeLeadershipItem[];
  marketEvents: string[];
  marketPulse: HomeMarketPulse;
  positioningLabel: string;
  positioningScore: number | null;
  recommendation: string;
  riskDrivers: string[];
  riskLabel: string;
  riskScore: number | null;
  sourceState: HomeSourceState;
  stockIdeas: HomeStockIdea[];
  todaysBias: string;
  updatedAt: string | null;
  volatility: HomeMetric | null;
};

const DISPLAY_INDEXES = ['SPY', 'QQQ', 'IWM', 'DIA'];

export function buildHomeSummary(
  dashboard: HomeDashboardResponse | null,
  histories: Partial<Record<string, HistoryData | null>> = {},
): HomeSummary {
  const core = dashboard?.core ?? null;
  const health = core?.market_health ?? null;
  const playbook = core?.decision_summary.playbook ?? null;
  const aggressiveness = core?.decision_summary.aggressiveness ?? null;
  const riskSummary = dashboard?.risk_summary ?? null;
  const healthScore = validNumber(health?.overall_score);
  const riskScore = validNumber(riskSummary?.score);
  const positioningScore = validNumber(aggressiveness?.score);
  const breadth = buildBreadthMetric(core);
  const volatility = buildVolatilityMetric(health);
  const indexes = buildIndexSnapshots(core?.indexes ?? [], histories);
  const leadership = buildLeadership(core);
  const recommendation = normalizeRecommendation(
    playbook?.headline
    ?? playbook?.suggested_aggressiveness
    ?? aggressiveness?.status
    ?? health?.status
    ?? null,
  );
  const riskLabelValue = riskSummary?.status ?? labelForRiskScore(riskScore);
  const positioningLabel = aggressiveness?.status
    ?? playbook?.suggested_aggressiveness
    ?? scoreLabel(positioningScore, 'Positioning');
  const stockIdeas = (dashboard?.watchlist_summary.items ?? []).slice(0, 5).map((item) => ({
    changePercent: validNumber(item.change_percent),
    symbol: item.symbol,
  }));
  const marketPulse = buildMarketPostureProjection({ breadth, healthScore, leadership, riskScore, volatility });
  const marketEvents = buildMarketEvents({
    breadth,
    healthLabel: health?.status ?? scoreLabel(healthScore, 'Health'),
    indexes,
    leadership,
    positioningLabel,
    stockIdeas,
  });
  const riskDrivers = buildRiskDrivers(dashboard);

  return {
    breadth,
    dailyInsight: buildDailyInsight({ indexes, volatility }),
    healthLabel: health?.status ?? scoreLabel(healthScore, 'Health'),
    healthScore,
    indexes,
    leadership,
    marketEvents,
    marketPulse,
    positioningLabel,
    positioningScore,
    recommendation,
    riskDrivers,
    riskLabel: riskLabelValue,
    riskScore,
    sourceState: deriveSourceState(dashboard),
    stockIdeas,
    todaysBias: buildTodaysBias(marketPulse.label, recommendation),
    updatedAt: dashboard?.generated_at ?? core?.generated_at ?? core?.as_of ?? null,
    volatility,
  };
}

function buildIndexSnapshots(
  indexes: IndexSnapshot[],
  histories: Partial<Record<string, HistoryData | null>>,
): HomeIndexSnapshot[] {
  return DISPLAY_INDEXES.map((symbol) => indexes.find((index) => normalizeIndexSymbol(index.symbol) === symbol))
    .filter((index): index is IndexSnapshot => Boolean(index))
    .map((index) => {
      const symbol = normalizeIndexSymbol(index.symbol);
      const changePercent = validNumber(index.change_percent);
      const history = histories[symbol];
      const historyPoints = isIntradayHistory(history) ? (history?.candles ?? [])
        .map((candle) => validNumber(candle.close))
        .filter((value): value is number => value !== null)
        .slice(-24) : [];
      return {
        changePercent,
        direction: changePercent === null ? 'unavailable' : changePercent > 0.05 ? 'up' : changePercent < -0.05 ? 'down' : 'flat',
        sparkline: historyPoints.length >= 2 ? historyPoints : [],
        symbol,
        trendLabel: trendLabel(index),
      };
    });
}

function buildBreadthMetric(core: HomeDashboardResponse['core'] | null): HomeMetric | null {
  const summary = core?.breadth_summary;
  if (!summary) {
    return null;
  }
  const score = validNumber(summary.breadth_score) ?? validNumber(summary.percent_above_50ema);
  return {
    direction: breadthDirection(summary.trend),
    label: 'Breadth',
    score,
    tone: toneForScore(score),
    value: summary.breadth_status ?? (score === null ? 'Updating' : `${Math.round(score)}%`),
  };
}

function buildVolatilityMetric(health: HomeDashboardResponse['core']['market_health'] | null | undefined): HomeMetric | null {
  const score = validNumber(health?.components?.volatility);
  if (score === null) {
    return null;
  }
  return {
    direction: null,
    label: 'Volatility',
    score,
    tone: score >= 70 ? 'positive' : score >= 50 ? 'warning' : 'negative',
    value: score >= 70 ? 'Contained' : score >= 50 ? 'Manageable' : 'Rising',
  };
}

function buildLeadership(core: HomeDashboardResponse['core'] | null): HomeLeadershipItem[] {
  const liveTheme = core?.theme_intelligence?.available ? core.theme_intelligence.leaders?.[0] : null;
  const leadingSector: HomeLeadershipItem | null = core?.top_sector?.name ? {
    direction: leadershipDirection(core.top_sector.status),
    id: normalizeEntityId(core.top_sector.name),
    kind: 'sector' as const,
    label: core.top_sector.name,
    role: 'Leading Sector' as const,
    tone: 'positive' as const,
  } : null;
  const leadingTheme: HomeLeadershipItem | null = liveTheme?.display_name ? {
    direction: leadershipDirection(liveTheme.classification),
    id: liveTheme.theme_id ?? normalizeEntityId(liveTheme.display_name),
    kind: 'theme' as const,
    label: liveTheme.display_name,
    role: 'Leading Theme' as const,
    tone: 'positive' as const,
  } : core?.top_industry_group?.name ? {
    direction: leadershipDirection(core.top_industry_group.status),
    id: normalizeEntityId(core.top_industry_group.name),
    kind: 'theme' as const,
    label: core.top_industry_group.name,
    role: 'Leading Theme' as const,
    tone: 'positive' as const,
  } : null;
  const laggingSector: HomeLeadershipItem | null = core?.lagging_sector?.name ? {
    direction: leadershipDirection(core.lagging_sector.status),
    id: normalizeEntityId(core.lagging_sector.name),
    kind: 'sector' as const,
    label: core.lagging_sector.name,
    role: 'Lagging Sector' as const,
    tone: 'negative' as const,
  } : null;

  return [leadingSector, leadingTheme, laggingSector]
    .filter((item): item is HomeLeadershipItem => item !== null);
}

function buildMarketEvents({
  breadth,
  healthLabel,
  indexes,
  leadership,
  positioningLabel,
  stockIdeas,
}: {
  breadth: HomeMetric | null;
  healthLabel: string;
  indexes: HomeIndexSnapshot[];
  leadership: HomeLeadershipItem[];
  positioningLabel: string;
  stockIdeas: HomeStockIdea[];
}) {
  const availableIndexes = indexes.filter((item) => item.changePercent !== null);
  const rankedIndexes = [...availableIndexes].sort((left, right) => (right.changePercent ?? 0) - (left.changePercent ?? 0));
  const weakest = rankedIndexes[rankedIndexes.length - 1];
  const positiveCount = availableIndexes.filter((item) => (item.changePercent ?? 0) > 0.05).length;
  const negativeCount = availableIndexes.filter((item) => (item.changePercent ?? 0) < -0.05).length;
  const stockIdeasWithMove = stockIdeas.filter((item) => item.changePercent !== null);
  const stockGainers = stockIdeasWithMove.filter((item) => (item.changePercent ?? 0) > 0).length;
  const allHigher = availableIndexes.length > 0 && positiveCount === availableIndexes.length;
  const allLower = availableIndexes.length > 0 && negativeCount === availableIndexes.length;
  const events = [
    allHigher ? 'All four major indexes are higher.' : allLower ? 'All four major indexes are lower.' : availableIndexes.length ? `${positiveCount} of ${availableIndexes.length} major indexes are higher.` : 'Major indexes are updating.',
    weakest ? `${weakest.symbol} is the weakest major index at ${formatSignedPercent(weakest.changePercent)}.` : null,
    buildLeadershipObservation(leadership),
    breadth ? `Breadth remains ${breadth.value.toLowerCase()}${breadth.direction ? ` · ${breadth.direction}` : ''}.` : null,
    `Market health is ${healthLabel.toLowerCase()}.`,
    `Positioning is ${positioningLabel.toLowerCase()}.`,
    stockIdeasWithMove.length ? `${stockGainers} of ${stockIdeasWithMove.length} highlighted stocks are higher.` : 'Watchlist participation is updating.',
  ].filter((item): item is string => Boolean(item));
  return events.slice(0, 7);
}

function buildRiskDrivers(dashboard: HomeDashboardResponse | null) {
  const contributors = dashboard?.risk_summary.top_contributors ?? [];
  const health = dashboard?.core.market_health;
  const aggressiveness = dashboard?.core.decision_summary.aggressiveness;
  const candidates = [
    ...contributors.map((item) => item.explanation || item.label),
    dashboard?.core.decision_summary.main_risk,
    ...(health?.weakening_factors ?? []),
    ...(aggressiveness?.cautions ?? []),
  ];
  return dedupeObservations(candidates
    .map((item) => interpretRiskDriver(item))
    .filter((item): item is string => Boolean(item)))
    .slice(0, 3);
}

function buildDailyInsight({
  indexes,
  volatility,
}: {
  indexes: HomeIndexSnapshot[];
  volatility: HomeMetric | null;
}): HomeDailyInsight | null {
  const moves = indexes.map((item) => item.changePercent).filter((value): value is number => value !== null);
  if (!moves.length) {
    return null;
  }
  const positiveCount = moves.filter((move) => move > 0.05).length;
  const spread = Math.max(...moves) - Math.min(...moves);
  const participation = positiveCount === moves.length
    ? 'Major indexes are moving together'
    : positiveCount >= Math.ceil(moves.length / 2)
      ? 'Index participation is positive but uneven'
      : 'Index participation remains narrow';
  const volatilityContext = volatility?.value === 'Contained'
    ? 'contained volatility supports orderly price action'
    : volatility?.value === 'Rising'
      ? 'rising volatility raises the bar for new entries'
      : 'volatility is not yet providing a clean confirmation';
  return {
    category: 'Cross-Market',
    headline: positiveCount <= 1 ? 'Participation remains narrow' : positiveCount === moves.length ? 'Participation is broad' : 'Participation is uneven',
    summary: spread >= 0.75
      ? `${capitalizeSentence(volatilityContext)}, but the index spread still favors selective entries.`
      : `${capitalizeSentence(volatilityContext)}, while ${participation.toLowerCase()}.`,
  };
}

function buildTodaysBias(pulse: MarketPulseLabel, recommendation: string) {
  if (pulse === 'Risk Off') {
    return 'Protect capital and require stronger confirmation before adding exposure.';
  }
  if (pulse === 'Risk On') {
    return 'Stay constructive, prioritize liquid strength, and avoid chasing extended moves.';
  }
  const normalized = recommendation.toLowerCase();
  return normalized.includes('defensive')
    ? 'Keep exposure measured until participation and volatility improve.'
    : 'Stay selective and add exposure only where price and participation confirm.';
}

function trendLabel(index: IndexSnapshot) {
  const rawTrend = index.trend?.trim().toLowerCase();
  if (rawTrend?.includes('bull') || rawTrend?.includes('up')) {
    return 'Uptrend';
  }
  if (rawTrend?.includes('bear') || rawTrend?.includes('down')) {
    return 'Downtrend';
  }
  const price = validNumber(index.price);
  const ema50 = validNumber(index.ema_50 ?? index.sma_50);
  const ema200 = validNumber(index.ema_200);
  if (price === null || (ema50 === null && ema200 === null)) {
    return null;
  }
  if ((ema50 === null || price >= ema50) && (ema200 === null || price >= ema200)) {
    return 'Uptrend';
  }
  if ((ema50 === null || price < ema50) && (ema200 === null || price < ema200)) {
    return 'Downtrend';
  }
  return 'Mixed';
}

function deriveSourceState(dashboard: HomeDashboardResponse | null): HomeSourceState {
  if (!dashboard) {
    return 'unavailable';
  }
  if (dashboard.core.overall_mode === 'mock') {
    return 'mock';
  }
  if (dashboard.cache_status === 'stale' || dashboard.refreshing || dashboard.core.refreshing) {
    return 'cached';
  }
  return dashboard.core.overall_mode === 'live' ? 'live' : 'cached';
}

function normalizeRecommendation(value: string | null) {
  const compact = value?.replace(/\s+/g, ' ').trim();
  if (!compact) {
    return 'Market conditions are updating';
  }
  if (compact.toLowerCase().includes('selectively aggressive')) {
    return 'Stay selectively aggressive';
  }
  return `${compact.charAt(0).toUpperCase()}${compact.slice(1)}`;
}

function compactObservation(value: string | null | undefined) {
  const compact = value?.replace(/\s+/g, ' ').trim().split(/(?<=[.!?])\s+/)[0]?.replace(/[.!?]+$/, '');
  return compact ? `${compact}.` : null;
}

function interpretRiskDriver(value: string | null | undefined) {
  const compact = compactObservation(value);
  if (!compact) return null;
  const lower = compact.toLowerCase();
  if (lower.includes('fear & greed') || lower.includes('fear and greed') || lower.includes('sentiment')) {
    return lower.includes('changed -') || lower.includes('cool') ? 'Sentiment cooling' : 'Elevated sentiment';
  }
  if (lower.includes('market health') && lower.includes('mixed')) return 'Mixed market health';
  if (lower.includes('stocks are above') || lower.includes('participation')) {
    const percent = Number(lower.match(/([0-9]+(?:\.[0-9]+)?)%/)?.[1]);
    return Number.isFinite(percent) && percent < 65 ? 'Narrow participation' : 'Uneven participation';
  }
  if (lower.includes('breadth') && (lower.includes('changed -') || lower.includes('weak') || lower.includes('deteriorat'))) return 'Weakening breadth';
  if (lower.includes('leadership') && (lower.includes('concentrat') || lower.includes('narrow'))) return 'Concentrated leadership';
  if (lower.includes('volatility') && lower.includes('contained')) return 'Contained volatility';
  if (lower.includes('volatility') && (lower.includes('rising') || lower.includes('elevated'))) return 'Rising volatility';
  if (lower.includes('event') && (lower.includes('risk') || lower.includes('rising'))) return 'Rising event risk';
  if (lower.includes('defensive') || lower.includes('risk-off')) return 'Defensive rotation';
  if (/\bchanged\s+[+-]?\d/.test(lower) || compact.length > 56) return null;
  return compact.replace(/[.]$/, '');
}

function buildLeadershipObservation(leadership: HomeLeadershipItem[]) {
  const leader = leadership.find((item) => item.role === 'Leading Sector');
  const laggard = leadership.find((item) => item.role === 'Lagging Sector');
  if (leader && laggard) return `${leader.label} leads while ${laggard.label} lags.`;
  if (leader) return `${leader.label} leads sector performance.`;
  return null;
}

function breadthDirection(value: string | null | undefined) {
  const normalized = value?.trim().toLowerCase();
  if (normalized === 'improving' || normalized === 'broadening') return 'Broadening';
  if (normalized === 'deteriorating' || normalized === 'weakening' || normalized === 'narrowing') return 'Narrowing';
  if (normalized === 'stable') return 'Stable';
  return null;
}

function leadershipDirection(value: string | null | undefined) {
  const normalized = value?.trim().toLowerCase();
  if (normalized === 'improving') return 'Improving';
  if (normalized === 'weakening' || normalized === 'lagging') return 'Weakening';
  if (normalized === 'stable' || normalized === 'leading') return 'Stable';
  return null;
}

function isIntradayHistory(history: HistoryData | null | undefined) {
  if (!history) return false;
  const timeframe = history.timeframe.trim().toUpperCase();
  return !['D', '1D', 'DAY', 'DAILY'].includes(timeframe);
}

function capitalizeSentence(value: string) {
  const compact = value.trim();
  return compact ? `${compact.charAt(0).toUpperCase()}${compact.slice(1)}` : compact;
}

function labelForRiskScore(score: number | null) {
  if (score === null) return 'Updating';
  if (score >= 65) return 'High';
  if (score >= 35) return 'Moderate';
  return 'Low';
}

function scoreLabel(score: number | null, fallback: string) {
  if (score === null) return `${fallback} updating`;
  if (score >= 70) return 'Strong';
  if (score >= 50) return 'Mixed';
  return 'Weak';
}

function toneForScore(score: number | null): HomeTone {
  if (score === null) return 'neutral';
  if (score >= 70) return 'positive';
  if (score >= 50) return 'warning';
  return 'negative';
}

function normalizeIndexSymbol(symbol: string) {
  return symbol.trim().toUpperCase();
}

function normalizeEntityId(value: string) {
  return value.trim().toLowerCase().replace(/&/g, 'and').replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');
}

function formatSignedPercent(value: number | null) {
  if (value === null) return 'N/A';
  return `${value > 0 ? '+' : ''}${value.toFixed(1)}%`;
}

function validNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function dedupeObservations(values: string[]) {
  const seen = new Set<string>();
  return values.filter((value) => {
    const key = value.toLowerCase()
      .replace(/[^a-z0-9\s]/g, ' ')
      .split(/\s+/)
      .filter((word) => word && !['a', 'an', 'and', 'are', 'is', 'the'].includes(word))
      .sort()
      .join(' ');
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}
