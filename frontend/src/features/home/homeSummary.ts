import type { HomeDashboardResponse, IndexSnapshot } from '@/types/market';

export type HomeSourceState = 'live' | 'cached' | 'mock' | 'unavailable';

export type HomeIndexSnapshot = {
  changePercent: number | null;
  direction: 'up' | 'down' | 'flat' | 'unavailable';
  symbol: string;
  trendLabel: string | null;
};

export type HomeMetric = {
  label: string;
  tone: 'positive' | 'warning' | 'negative' | 'neutral';
  value: string;
};

export type HomeLeadershipItem = {
  label: string;
  kind: 'sector' | 'theme';
  tone: 'positive' | 'warning' | 'negative' | 'neutral';
};

export type HomeStockIdea = {
  changePercent: number | null;
  symbol: string;
};

export type HomeDailyInsight = {
  headline: string;
  sourceLabel: 'Rules-based' | 'AI-generated';
  summary: string;
};

export type HomeSummary = {
  breadth: HomeMetric | null;
  dailyInsight: HomeDailyInsight | null;
  healthLabel: string;
  healthScore: number | null;
  indexes: HomeIndexSnapshot[];
  laggards: HomeLeadershipItem[];
  laggardState: 'canonical' | 'evaluated_empty' | 'unavailable';
  leaders: HomeLeadershipItem[];
  positioningLabel: string;
  positioningScore: number | null;
  recommendation: string;
  riskDriver: string | null;
  riskLabel: string;
  riskScore: number | null;
  sourceState: HomeSourceState;
  stockIdeas: HomeStockIdea[];
  summary: string;
  upcomingEvents: { label: string; when: string }[];
  volatility: HomeMetric | null;
  yield10Y: HomeMetric | null;
};

const DISPLAY_INDEXES = ['SPY', 'QQQ', 'IWM', 'DIA'];

export function buildHomeSummary(dashboard: HomeDashboardResponse | null): HomeSummary {
  const core = dashboard?.core ?? null;
  const health = core?.market_health ?? null;
  const playbook = core?.decision_summary.playbook ?? null;
  const aggressiveness = core?.decision_summary.aggressiveness ?? null;
  const riskSummary = dashboard?.risk_summary ?? null;
  const recommendation = normalizeRecommendation(
    playbook?.headline
    ?? playbook?.suggested_aggressiveness
    ?? aggressiveness?.status
    ?? health?.status
    ?? null,
  );
  const healthScore = validNumber(health?.overall_score);
  const riskScore = validNumber(riskSummary?.score);
  const positioningScore = validNumber(aggressiveness?.score);
  const leaders = buildLeadership(core);
  const laggards = buildLaggards(core);
  const breadth = buildBreadthMetric(core);
  const volatility = buildVolatilityMetric(health);
  const rawRiskDriver = riskSummary?.summary ?? riskSummary?.top_contributors?.[0]?.explanation ?? core?.decision_summary.main_risk ?? null;
  const riskDriver = derivePrimaryRiskDriver({
    breadth,
    healthLabel: health?.status ?? scoreLabel(healthScore, 'Health'),
    healthScore,
    leaders,
    rawRiskDriver,
    riskLabel: riskSummary?.status ?? riskLabel(riskScore),
    volatility,
  });
  const summary = formatCompactPlaybookSummary({
    breadth,
    healthScore,
    leaders,
    recommendation,
    riskLabel: riskSummary?.status ?? riskLabel(riskScore),
    volatility,
  });
  return {
    breadth,
    dailyInsight: buildDailyInsight({
      breadth,
      leaders,
      playbookSummary: playbook?.summary ?? null,
      recommendation,
      riskDriver,
      summary,
      volatility,
    }),
    healthLabel: health?.status ?? scoreLabel(healthScore, 'Health'),
    healthScore,
    indexes: buildIndexSnapshots(core?.indexes ?? []),
    laggards,
    laggardState: laggards.length ? 'canonical' : leaders.length ? 'evaluated_empty' : 'unavailable',
    leaders,
    positioningLabel: aggressiveness?.status ?? playbook?.suggested_aggressiveness ?? scoreLabel(positioningScore, 'Positioning'),
    positioningScore,
    recommendation,
    riskDriver: formatCompactRiskDriver(riskDriver),
    riskLabel: riskSummary?.status ?? riskLabel(riskScore),
    riskScore,
    sourceState: deriveSourceState(dashboard),
    stockIdeas: (dashboard?.watchlist_summary.items ?? []).slice(0, 3).map((item) => ({
      changePercent: validNumber(item.change_percent),
      symbol: item.symbol,
    })),
    summary,
    upcomingEvents: [],
    volatility: buildVolatilityMetric(health),
    yield10Y: null,
  };
}

function buildLaggards(core: HomeDashboardResponse['core'] | null): HomeLeadershipItem[] {
  const sector = core?.lagging_sector;
  if (!sector?.name) {
    return [];
  }
  return [{
    kind: 'sector',
    label: `${sector.name} · #${sector.rank} overall · ${sector.status}${typeof sector.composite_score === 'number' ? ` · Composite ${sector.composite_score.toFixed(1)}` : ''}${typeof sector.total_members === 'number' && sector.total_members <= 3 ? ` · limited breadth sample (${sector.total_members})` : typeof sector.percent_above_50ema === 'number' ? ` · ${Math.round(sector.percent_above_50ema)}% above EMA50` : ''}`,
    tone: 'negative',
  }];
}

function buildIndexSnapshots(indexes: IndexSnapshot[]): HomeIndexSnapshot[] {
  return DISPLAY_INDEXES.map((symbol) => indexes.find((index) => normalizeIndexSymbol(index.symbol) === symbol))
    .filter((index): index is IndexSnapshot => Boolean(index))
    .map((index) => {
      const changePercent = validNumber(index.change_percent);
      return {
        changePercent,
        direction: changePercent === null ? 'unavailable' : changePercent > 0.05 ? 'up' : changePercent < -0.05 ? 'down' : 'flat',
        symbol: normalizeIndexSymbol(index.symbol) ?? index.symbol,
        trendLabel: trendLabel(index),
      };
    });
}

function buildBreadthMetric(core: HomeDashboardResponse['core'] | null): HomeMetric | null {
  const summary = core?.breadth_summary;
  if (!summary) {
    return null;
  }
  const score = validNumber(summary.breadth_score);
  const above50 = validNumber(summary.percent_above_50ema);
  return {
    label: 'Breadth',
    tone: toneForScore(score ?? above50),
    value: summary.breadth_status ?? (above50 === null ? 'Updating' : `${formatPercent(above50)} >50 EMA`),
  };
}

function buildVolatilityMetric(health: HomeDashboardResponse['core']['market_health'] | null | undefined): HomeMetric | null {
  const volatility = validNumber(health?.components?.volatility);
  if (volatility === null) {
    return null;
  }
  return {
    label: 'Volatility',
    tone: volatility >= 70 ? 'positive' : volatility >= 50 ? 'warning' : 'negative',
    value: volatility >= 70 ? 'Contained' : volatility >= 50 ? 'Manageable' : 'Rising',
  };
}

function buildLeadership(core: HomeDashboardResponse['core'] | null): HomeLeadershipItem[] {
  return [
    core?.top_sector?.name ? {
      kind: 'sector' as const,
      label: `${core.top_sector.name} · #${core.top_sector.rank} overall · ${core.top_sector.status}${typeof core.top_sector.composite_score === 'number' ? ` · Composite ${core.top_sector.composite_score.toFixed(1)}` : ''}${typeof core.top_sector.percent_above_50ema === 'number' ? ` · ${Math.round(core.top_sector.percent_above_50ema)}% above EMA50` : ''}`,
      tone: toneForScore(validNumber(core.top_sector.relative_strength_score)),
    } : null,
    core?.top_industry_group?.name ? {
      kind: 'theme' as const,
      label: core.top_industry_group.name,
      tone: toneForScore(validNumber(core.top_industry_group.relative_strength_score ?? core.top_industry_group.score)),
    } : null,
  ].filter((item): item is HomeLeadershipItem => item !== null).slice(0, 3);
}

function buildDailyInsight({
  breadth,
  leaders,
  playbookSummary,
  recommendation,
  riskDriver,
  summary,
  volatility,
}: {
  breadth: HomeMetric | null;
  leaders: HomeLeadershipItem[];
  playbookSummary: string | null;
  recommendation: string;
  riskDriver: string | null;
  summary: string;
  volatility: HomeMetric | null;
}): HomeDailyInsight | null {
  const insight = formatCompactDailyInsight({ breadth, leaders, playbookSummary, recommendation, riskDriver, summary, volatility });
  if (!insight) {
    return null;
  }
  const headline = dedupeInsightHeadline(buildInsightHeadline(leaders, recommendation), recommendation, insight);
  return {
    headline,
    sourceLabel: 'Rules-based',
    summary: isMaterialDuplicate(insight, summary)
      ? formatCompactDailyInsight({ breadth, leaders, playbookSummary: null, recommendation, riskDriver, summary: '', volatility })
      : insight,
  };
}

function normalizeRecommendation(value: string | null) {
  const text = value?.trim();
  if (!text) {
    return 'Market Dashboard Updating';
  }
  if (text.toLowerCase().includes('selectively aggressive')) {
    return 'Stay Selectively Aggressive';
  }
  return capitalizeWords(text);
}

function compactSentence(value: string) {
  return value.replace(/\s+/g, ' ').trim().split(/(?<=[.!?])\s+/).slice(0, 2).join(' ');
}

function formatCompactPlaybookSummary({
  breadth,
  healthScore,
  leaders,
  recommendation,
  riskLabel,
  volatility,
}: {
  breadth: HomeMetric | null;
  healthScore: number | null;
  leaders: HomeLeadershipItem[];
  recommendation: string;
  riskLabel: string;
  volatility: HomeMetric | null;
}) {
  const lowerRecommendation = recommendation.toLowerCase();
  const lowerRisk = riskLabel.toLowerCase();
  const breadthValue = breadth?.value.toLowerCase() ?? '';
  const volatilityValue = volatility?.value.toLowerCase() ?? '';

  if (lowerRecommendation.includes('defensive') || lowerRisk.includes('high') || (healthScore !== null && healthScore < 50)) {
    return 'Risk is elevated and trend support is weaker. Keep exposure selective until conditions improve.';
  }
  if (breadthValue.includes('weak') || volatilityValue.includes('rising')) {
    return 'Market conditions are mixed. Favor confirmed leaders and keep weaker groups on watch.';
  }
  if ((healthScore ?? 0) >= 70 && leaders.length) {
    return 'Trend and leadership remain constructive. Stay with leaders, but avoid chasing extended names.';
  }
  return 'The market backdrop is still forming. Focus on confirmed strength and avoid low-quality setups.';
}

function formatCompactRiskDriver(value: string | null) {
  const compact = stripTrailingPunctuation(value ?? '');
  return compact ? `Main driver: ${compact}.` : null;
}

function derivePrimaryRiskDriver({
  breadth,
  healthLabel,
  healthScore,
  leaders,
  rawRiskDriver,
  riskLabel,
  volatility,
}: {
  breadth: HomeMetric | null;
  healthLabel: string;
  healthScore: number | null;
  leaders: HomeLeadershipItem[];
  rawRiskDriver: string | null;
  riskLabel: string;
  volatility: HomeMetric | null;
}) {
  const factors: string[] = [];
  const raw = (rawRiskDriver ?? '').toLowerCase();
  const breadthText = `${breadth?.value ?? ''} ${breadth?.label ?? ''}`.toLowerCase();
  const volatilityText = `${volatility?.value ?? ''} ${volatility?.label ?? ''}`.toLowerCase();
  const healthText = `${healthLabel} ${healthScore ?? ''}`.toLowerCase();

  if (volatilityText.includes('rising') || volatilityText.includes('elevated')) {
    factors.push('rising volatility');
  }
  if (breadthText.includes('weak') || breadthText.includes('deteriorat')) {
    factors.push('weak breadth');
  }
  if (healthText.includes('weak') || (healthScore !== null && healthScore < 50)) {
    factors.push('deteriorating index trend');
  }
  if (leaders.length >= 2) {
    factors.push('concentrated leadership');
  }
  if (raw.includes('sentiment') || raw.includes('greed') || raw.includes('elevated')) {
    factors.unshift('elevated sentiment');
  }
  if (riskLabel.toLowerCase().includes('low') && factors.length === 0) {
    return 'No material risk driver detected';
  }
  return capitalizeSentence(formatList(dedupe(factors).slice(0, 2))) || 'No material risk driver detected';
}

function formatCompactDailyInsight({
  breadth,
  leaders,
  playbookSummary,
  recommendation,
  riskDriver,
  summary,
  volatility,
}: {
  breadth: HomeMetric | null;
  leaders: HomeLeadershipItem[];
  playbookSummary: string | null;
  recommendation: string;
  riskDriver: string | null;
  summary: string;
  volatility: HomeMetric | null;
}) {
  const leaderText = formatList(leaders.map((item) => item.label));
  const breadthText = breadth?.value.toLowerCase() ?? '';
  const volatilityText = volatility?.value.toLowerCase() ?? '';

  if (leaders.length >= 2) {
    const participation = breadthText.includes('healthy') || breadthText.includes('strong')
      ? 'participation supports the trend'
      : 'participation remains selective';
    return `${leaderText} are leading, but ${participation}. New exposure should focus on confirmed leaders rather than broad market chasing.`;
  }
  if (volatilityText.includes('contained')) {
    return 'Volatility remains contained, which supports the current market plan. Keep new exposure focused on groups with confirmed relative strength.';
  }
  if (riskDriver && !riskDriver.toLowerCase().includes('no material')) {
    return `${riskDriver}. Keep the dashboard bias in mind, but avoid extending into weaker groups.`;
  }
  const fallback = compactSentence(playbookSummary || summary || recommendation);
  return isMaterialDuplicate(fallback, recommendation)
    ? 'The dashboard is constructive, but confirmation still matters. Favor leaders and avoid forcing trades in weaker groups.'
    : ensureCompleteSentence(fallback);
}

function buildInsightHeadline(leaders: HomeLeadershipItem[], recommendation: string) {
  if (leaders.length >= 2) {
    return 'Leadership Remains Concentrated';
  }
  if (leaders.length === 1) {
    return `${leaders[0].label} Leads`;
  }
  if (recommendation.toLowerCase().includes('defensive')) {
    return 'Risk Remains Elevated';
  }
  return 'Market Context';
}

function dedupeInsightHeadline(headline: string, recommendation: string, body: string) {
  if (!isMaterialDuplicate(headline, recommendation) && !isMaterialDuplicate(firstSentence(body), recommendation)) {
    return headline;
  }
  if (body.toLowerCase().includes('participation')) {
    return 'Participation Is Still Selective';
  }
  if (body.toLowerCase().includes('volatility')) {
    return 'Volatility Remains Contained';
  }
  return 'Leadership Remains Concentrated';
}

function isMaterialDuplicate(left: string, right: string) {
  const normalizedLeft = normalizeForComparison(left);
  const normalizedRight = normalizeForComparison(right);
  return Boolean(normalizedLeft && normalizedRight && (
    normalizedLeft === normalizedRight
    || normalizedLeft.includes(normalizedRight)
    || normalizedRight.includes(normalizedLeft)
  ));
}

function normalizeForComparison(value: string) {
  return value.toLowerCase().replace(/[^\w\s]/g, ' ').replace(/\s+/g, ' ').trim();
}

function firstSentence(value: string) {
  return value.split(/(?<=[.!?])\s+/)[0] ?? value;
}

function stripTrailingPunctuation(value: string) {
  return value.replace(/\s+/g, ' ').trim().replace(/[.!?]+$/, '');
}

function ensureCompleteSentence(value: string) {
  const compact = value.replace(/\s+/g, ' ').trim();
  if (!compact) {
    return compact;
  }
  return /[.!?]$/.test(compact) ? compact : `${compact}.`;
}

function dedupe(values: string[]) {
  return Array.from(new Set(values.filter(Boolean)));
}

function capitalizeSentence(value: string) {
  const compact = value.trim();
  if (!compact) {
    return compact;
  }
  return `${compact.charAt(0).toUpperCase()}${compact.slice(1)}`;
}

function deriveSourceState(dashboard: HomeDashboardResponse | null): HomeSourceState {
  if (!dashboard) {
    return 'unavailable';
  }
  if (dashboard.core.overall_mode === 'mock') {
    return 'mock';
  }
  if (dashboard.cache_status || dashboard.core.cache_status || dashboard.refreshing || dashboard.core.refreshing) {
    return 'cached';
  }
  return dashboard.core.overall_mode === 'live' ? 'live' : 'cached';
}

function normalizeIndexSymbol(symbol: string) {
  const upper = symbol.toUpperCase();
  return upper;
}

function trendLabel(index: IndexSnapshot) {
  if (index.price && index.ema_20 && index.ema_50 && index.price > index.ema_20 && index.ema_20 >= index.ema_50) {
    return 'Bullish';
  }
  if (index.price && index.ema_50 && index.price < index.ema_50) {
    return 'Weak';
  }
  return 'Neutral';
}

function toneForScore(score: number | null): HomeMetric['tone'] {
  if (score === null) {
    return 'neutral';
  }
  if (score >= 70) {
    return 'positive';
  }
  if (score >= 50) {
    return 'warning';
  }
  return 'negative';
}

function riskLabel(score: number | null) {
  if (score === null) {
    return 'Updating';
  }
  if (score < 35) {
    return 'Low';
  }
  if (score < 55) {
    return 'Moderate';
  }
  if (score < 75) {
    return 'Elevated';
  }
  return 'High';
}

function scoreLabel(score: number | null, fallback: string) {
  if (score === null) {
    return `${fallback} Updating`;
  }
  return score >= 70 ? 'Strong' : score >= 50 ? 'Mixed' : 'Weak';
}

function validNumber(value: unknown) {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function formatPercent(value: number) {
  const rounded = Math.round(value * 10) / 10;
  return `${Number.isInteger(rounded) ? rounded.toFixed(0) : rounded.toFixed(1)}%`;
}

function formatList(items: string[]) {
  if (items.length <= 1) {
    return items[0] ?? '';
  }
  return `${items.slice(0, -1).join(', ')} and ${items.at(-1)}`;
}

function capitalizeWords(value: string) {
  return value.replace(/\b\w/g, (letter) => letter.toUpperCase());
}
