import type { BreadthDashboardViewModel } from '@/features/market/breadthAnalysis';
import type { DecisionDashboardViewModel } from '@/features/market/decisionAnalysis';
import type { IndexAnalysis } from '@/features/market/indexAnalysis';
import type { InstitutionalDashboardViewModel } from '@/features/market/institutionalAnalysis';
import type { MacroDashboardViewModel } from '@/features/market/macroAnalysis';
import type { MarketHealthResponse, MarketCoreSnapshot } from '@/types/market';

export type MarketOverviewTone = 'positive' | 'neutral' | 'warning' | 'negative' | 'unavailable';
export type MarketAlignmentGroup = 'supportive' | 'mixed' | 'caution' | 'unavailable';
export type MarketSnapshotDimension = 'indexes' | 'breadth' | 'institutions' | 'macro' | 'leadership' | 'volatility';
export type MarketSubTabKey = 'overview' | 'indexes' | 'health' | 'breadth' | 'decision' | 'institutions' | 'macro';

export type MarketSnapshotTile = {
  key: MarketSnapshotDimension;
  label: string;
  primary: string;
  secondary: string | null;
  sourceTab: MarketSubTabKey;
  tone: MarketOverviewTone;
};

export type MarketAlignmentItem = {
  group: MarketAlignmentGroup;
  key: MarketSnapshotDimension | 'health' | 'decision';
  label: string;
  reason: string;
  weight: number;
};

export type MarketContradiction = {
  explanation: string;
  severity: 'low' | 'moderate' | 'high';
  type: 'health_macro' | 'indexes_breadth' | 'decision_risk' | 'institutions_price' | 'leadership_breadth';
};

export type MarketOverviewSignal = {
  key: string;
  label: string;
  priority: number;
  sourceTab: MarketSubTabKey;
  tone: MarketOverviewTone;
};

type OverviewConcentrationSignal = {
  state: string;
  status: string;
  summary: string;
  value: number | null;
} | null;

export type MarketOverviewDashboardViewModel = {
  alignment: {
    caution: MarketAlignmentItem[];
    mixed: MarketAlignmentItem[];
    summary: string;
    supportive: MarketAlignmentItem[];
    unavailable: MarketAlignmentItem[];
  };
  contradictions: MarketContradiction[];
  dataQuality: {
    label: string;
    tone: MarketOverviewTone;
  };
  decisionPosture: {
    avoid: string | null;
    confidence: number | null;
    implication: string;
    monitor: string | null;
    posture: string;
    prefer: string | null;
    tone: MarketOverviewTone;
  };
  insight: string;
  keySignals: MarketOverviewSignal[];
  regime: {
    confidence: string;
    healthScore: number | null;
    label: string;
    sourceLabel: string | null;
    summary: string;
    tone: MarketOverviewTone;
  };
  snapshot: MarketSnapshotTile[];
};

export function buildMarketOverviewDashboard({
  breadth,
  core,
  decision,
  health,
  indexes,
  institutional,
  macro,
  weightConcentration = null,
}: {
  breadth: BreadthDashboardViewModel | null;
  core: MarketCoreSnapshot | null;
  decision: DecisionDashboardViewModel | null;
  health: MarketHealthResponse | null;
  indexes: IndexAnalysis[];
  institutional: InstitutionalDashboardViewModel | null;
  macro: MacroDashboardViewModel | null;
  weightConcentration?: OverviewConcentrationSignal;
}): MarketOverviewDashboardViewModel {
  const snapshot = [
    buildOverviewIndexesSnapshot(indexes, weightConcentration),
    buildOverviewBreadthSnapshot(breadth, core),
    buildOverviewInstitutionsSnapshot(institutional),
    buildOverviewMacroSnapshot(macro),
    buildOverviewLeadershipSnapshot(core, breadth),
    buildOverviewVolatilitySnapshot(health),
  ].filter((tile): tile is MarketSnapshotTile => tile !== null);
  const contradictions = deriveMarketContradictions({ breadth, core, decision, health, indexes, institutional, macro });
  const alignment = classifyMarketAlignment(snapshot, health, decision);
  return {
    alignment: {
      ...alignment,
      summary: buildMarketAlignmentSummary(alignment, contradictions),
    },
    contradictions,
    dataQuality: deriveMarketOverviewDataQuality(core, macro),
    decisionPosture: buildOverviewDecisionPosture(decision, contradictions, core),
    insight: buildWholeMarketInsight(snapshot, contradictions, decision, core),
    keySignals: buildOverviewKeySignals(snapshot, contradictions),
    regime: buildMarketRegimeOverview(health, core, snapshot, contradictions),
    snapshot,
  };
}

export function buildMarketRegimeOverview(
  health: MarketHealthResponse | null,
  core: MarketCoreSnapshot | null,
  snapshot: MarketSnapshotTile[],
  contradictions: MarketContradiction[],
): MarketOverviewDashboardViewModel['regime'] {
  const healthScore = finiteNumber(health?.overall_score) ?? null;
  const label = health?.status ?? core?.market_health?.status ?? 'Unavailable';
  const caution = contradictions[0]?.explanation;
  const supportive = snapshot.find((tile) => tile.tone === 'positive')?.secondary;
  const summary = [
    health?.summary ?? core?.market_health?.summary ?? 'Market regime inputs are still loading.',
    caution ? `Key conflict: ${caution}` : supportive,
  ].filter(Boolean).join(' ');
  return {
    confidence: classifyConviction(snapshot, contradictions),
    healthScore,
    label,
    sourceLabel: core?.cache_status ? capitalize(String(core.cache_status)) : health?.data_quality?.overall_mode ?? null,
    summary,
    tone: healthScore === null ? 'unavailable' : healthScore >= 75 ? 'positive' : healthScore >= 55 ? 'warning' : 'negative',
  };
}

export function buildOverviewIndexesSnapshot(
  indexes: IndexAnalysis[],
  weightConcentration: OverviewConcentrationSignal = null,
): MarketSnapshotTile | null {
  const valid = indexes.filter((index) => index.periodReturn !== null);
  if (!valid.length) {
    return null;
  }
  const leader = [...valid].sort((a, b) => (b.periodReturn ?? -Infinity) - (a.periodReturn ?? -Infinity))[0];
  const uptrends = valid.filter((index) => index.trend.tone === 'positive').length;
  const volumeWarnings = valid.filter((index) => index.volume.tone === 'warning' || index.volume.tone === 'negative').length;
  const concentrationCaution = weightConcentration?.state === 'mega_cap_concentration' || weightConcentration?.state === 'mild_concentration';
  const tone: MarketOverviewTone = uptrends >= 2 && volumeWarnings === 0 && !concentrationCaution
    ? 'positive'
    : uptrends >= 1
      ? 'warning'
      : 'negative';
  const participation = weightConcentration && weightConcentration.state !== 'unavailable'
    ? weightConcentration.summary
    : volumeWarnings
      ? 'Volume participation is mixed.'
      : 'Volume participation is confirming.';
  return {
    key: 'indexes',
    label: 'Indexes',
    primary: leader ? `${leader.symbol} Leading` : 'Index Trend Available',
    secondary: `${uptrends} of ${valid.length} tracked indexes in constructive trends. ${participation}`,
    sourceTab: 'indexes',
    tone,
  };
}

export function buildOverviewBreadthSnapshot(
  breadth: BreadthDashboardViewModel | null,
  core: MarketCoreSnapshot | null = null,
): MarketSnapshotTile | null {
  if (!breadth || isUnavailableBreadthDashboard(breadth)) {
    return buildCoreBreadthSnapshot(core);
  }
  const caution = [
    breadth.advanceDecline.tone === 'negative' ? 'daily participation is negative' : null,
    breadth.quality.confidence === 'low' ? 'coverage confidence is low' : null,
    breadth.divergence.tone === 'negative' ? breadth.divergence.stateLabel.toLowerCase() : null,
  ].filter(Boolean).join(', ');
  return {
    key: 'breadth',
    label: 'Breadth',
    primary: breadth.movingAverageProfile.state,
    secondary: caution
      ? `${breadth.movingAverageProfile.summary}, but ${caution}.`
      : `${breadth.movingAverageProfile.summary}; ${breadth.divergence.confirmationLabel.toLowerCase()}.`,
    sourceTab: 'breadth',
    tone: mapTone(breadth.overview.tone),
  };
}

function buildCoreBreadthSnapshot(core: MarketCoreSnapshot | null): MarketSnapshotTile | null {
  const summary = core?.breadth_summary;
  if (!summary) {
    return null;
  }
  const score = finiteNumber(summary.breadth_score);
  const above50 = finiteNumber(summary.percent_above_50ema);
  const coverage = finiteNumber(summary.coverage_percent);
  const status = summary.breadth_status ?? (score === null ? 'Breadth Available' : score >= 70 ? 'Strong Breadth' : score >= 55 ? 'Constructive Breadth' : score >= 40 ? 'Mixed Breadth' : 'Weak Breadth');
  const details = [
    above50 !== null ? `${formatPercent(above50)} above 50 EMA` : null,
    coverage !== null ? `${formatPercent(coverage)} coverage` : null,
    summary.universe ? `${summary.universe} universe` : null,
    summary.overall_mode ? `${summary.overall_mode} mode` : null,
  ].filter(Boolean).join(' · ');
  return {
    key: 'breadth',
    label: 'Breadth',
    primary: status,
    secondary: details || 'Breadth summary is available from the core market snapshot.',
    sourceTab: 'breadth',
    tone: score === null ? 'neutral' : score >= 70 ? 'positive' : score >= 50 ? 'warning' : 'negative',
  };
}

function isUnavailableBreadthDashboard(breadth: BreadthDashboardViewModel) {
  return breadth.overview.score === null
    && breadth.movingAverageProfile.state === 'Unavailable'
    && breadth.quality.confidence === 'unavailable';
}

export function buildOverviewInstitutionsSnapshot(institutional: InstitutionalDashboardViewModel | null): MarketSnapshotTile | null {
  if (!institutional) {
    return null;
  }
  return {
    key: 'institutions',
    label: 'Institutions',
    primary: institutional.overview.bias,
    secondary: `${institutional.accumulationDistribution.interpretation} Confidence is ${institutional.overview.confidence}.`,
    sourceTab: 'institutions',
    tone: mapTone(institutional.overview.tone),
  };
}

export function buildOverviewMacroSnapshot(macro: MacroDashboardViewModel | null): MarketSnapshotTile | null {
  if (!macro || macro.riskAppetite.state === 'unavailable') {
    return null;
  }
  return {
    key: 'macro',
    label: 'Macro',
    primary: macro.interpretation.stance,
    secondary: macro.interpretation.mainRisk,
    sourceTab: 'macro',
    tone: macro.riskAppetite.state === 'risk_off' || macro.riskAppetite.state === 'defensive_rotation'
      ? 'negative'
      : macro.riskAppetite.state === 'balanced'
        ? 'neutral'
        : 'positive',
  };
}

export function buildOverviewLeadershipSnapshot(core: MarketCoreSnapshot | null, breadth: BreadthDashboardViewModel | null): MarketSnapshotTile | null {
  const sector = core?.top_sector?.name;
  const theme = core?.top_industry_group?.name;
  if (!sector && !theme) {
    return null;
  }
  const narrow = breadth?.quality.confidence === 'low' || (breadth?.overview.score !== null && (breadth?.overview.score ?? 100) < 55);
  return {
    key: 'leadership',
    label: 'Leadership',
    primary: sector ?? theme ?? 'Leadership Available',
    secondary: theme
      ? `${theme} leads themes${narrow ? ', but leadership remains concentrated.' : '.'}`
      : narrow ? 'Leadership exists, but breadth confirmation is limited.' : 'Sector leadership is constructive.',
    sourceTab: 'overview',
    tone: narrow ? 'warning' : 'positive',
  };
}

export function buildOverviewVolatilitySnapshot(health: MarketHealthResponse | null): MarketSnapshotTile | null {
  const volatility = finiteNumber(health?.components?.volatility);
  if (volatility === null) {
    return null;
  }
  return {
    key: 'volatility',
    label: 'Volatility',
    primary: volatility >= 70 ? 'Contained' : volatility >= 50 ? 'Manageable' : 'Rising',
    secondary: volatility >= 70
      ? 'Volatility remains supportive and is not disrupting the broader trend.'
      : volatility >= 50
        ? 'Volatility is manageable but should be monitored.'
        : 'Volatility is beginning to conflict with otherwise constructive internals.',
    sourceTab: 'health',
    tone: volatility >= 70 ? 'positive' : volatility >= 50 ? 'warning' : 'negative',
  };
}

export function classifyMarketAlignment(
  snapshot: MarketSnapshotTile[],
  health: MarketHealthResponse | null,
  decision: DecisionDashboardViewModel | null,
) {
  const items: MarketAlignmentItem[] = [];
  const healthScore = finiteNumber(health?.overall_score);
  if (healthScore !== null) {
    items.push({
      group: healthScore >= 70 ? 'supportive' : healthScore >= 50 ? 'mixed' : 'caution',
      key: 'health',
      label: 'Health',
      reason: `${Math.round(healthScore)} / 100 health score`,
      weight: 3,
    });
  }
  snapshot.forEach((tile) => {
    items.push({
      group: tile.tone === 'positive' ? 'supportive' : tile.tone === 'negative' ? 'caution' : tile.tone === 'unavailable' ? 'unavailable' : 'mixed',
      key: tile.key,
      label: tile.label,
      reason: tile.primary,
      weight: tile.key === 'macro' || tile.key === 'breadth' ? 2 : 1,
    });
  });
  if (decision) {
    items.push({
      group: decision.posture.tone === 'positive' ? 'supportive' : decision.posture.tone === 'negative' ? 'caution' : 'mixed',
      key: 'decision',
      label: 'Decision',
      reason: decision.posture.postureLabel,
      weight: 2,
    });
  }
  return {
    caution: items.filter((item) => item.group === 'caution'),
    mixed: items.filter((item) => item.group === 'mixed'),
    supportive: items.filter((item) => item.group === 'supportive'),
    unavailable: items.filter((item) => item.group === 'unavailable'),
  };
}

export function deriveMarketContradictions({
  breadth,
  core,
  decision,
  health,
  indexes,
  institutional,
  macro,
}: {
  breadth: BreadthDashboardViewModel | null;
  core: MarketCoreSnapshot | null;
  decision: DecisionDashboardViewModel | null;
  health: MarketHealthResponse | null;
  indexes: IndexAnalysis[];
  institutional: InstitutionalDashboardViewModel | null;
  macro: MacroDashboardViewModel | null;
}): MarketContradiction[] {
  const contradictions: MarketContradiction[] = [];
  const healthScore = finiteNumber(health?.overall_score);
  if (healthScore !== null && healthScore >= 75 && macro && (macro.riskAppetite.state === 'defensive_rotation' || macro.riskAppetite.state === 'risk_off')) {
    contradictions.push({
      explanation: 'Healthy equity internals are not fully confirmed by cross-asset macro signals.',
      severity: macro.riskAppetite.confidence === 'low' ? 'low' : 'moderate',
      type: 'health_macro',
    });
  }
  const indexStrength = indexes.some((index) => (index.periodReturn ?? 0) > 0.5);
  if (indexStrength && breadth?.advanceDecline.tone === 'negative') {
    contradictions.push({
      explanation: 'Headline index strength is running ahead of daily breadth participation.',
      severity: 'moderate',
      type: 'indexes_breadth',
    });
  }
  if (decision?.posture.posture === 'aggressive' && macro && (macro.riskAppetite.state === 'defensive_rotation' || macro.riskAppetite.state === 'risk_off')) {
    contradictions.push({
      explanation: 'Decision posture is aggressive while macro confirmation is defensive.',
      severity: 'high',
      type: 'decision_risk',
    });
  }
  const weakPrice = indexes.length > 0 && indexes.every((index) => index.trend.tone !== 'positive');
  if (institutional && institutional.overview.tone === 'positive' && weakPrice) {
    contradictions.push({
      explanation: 'Institutional accumulation evidence exists, but price trend confirmation is incomplete.',
      severity: 'moderate',
      type: 'institutions_price',
    });
  }
  const leadershipStrong = Boolean(core?.top_sector?.name || core?.top_industry_group?.name);
  if (leadershipStrong && breadth && (breadth.quality.confidence === 'low' || breadth.overview.tone === 'negative')) {
    contradictions.push({
      explanation: 'Leadership is concentrated while broad participation remains limited.',
      severity: breadth.quality.confidence === 'low' ? 'low' : 'moderate',
      type: 'leadership_breadth',
    });
  }
  return contradictions;
}

export function buildWholeMarketInsight(
  snapshot: MarketSnapshotTile[],
  contradictions: MarketContradiction[],
  decision: DecisionDashboardViewModel | null,
  core: MarketCoreSnapshot | null = null,
) {
  const supportive = snapshot.find((tile) => tile.tone === 'positive');
  const caution = contradictions[0]?.explanation ?? snapshot.find((tile) => tile.tone === 'negative')?.secondary;
  const posture = decision?.posture.postureLabel
    ?? core?.decision_summary?.aggressiveness?.status
    ?? core?.decision_summary?.playbook?.suggested_aggressiveness
    ?? 'selective posture';
  const sentences = [
    supportive ? `${supportive.label} remains constructive: ${supportive.primary}.` : null,
    caution ? `However, ${lowercaseFirst(caution)}` : null,
    `Resulting posture: ${posture}.`,
  ].filter(Boolean);
  return sentences.join(' ');
}

export function buildOverviewDecisionPosture(
  decision: DecisionDashboardViewModel | null,
  contradictions: MarketContradiction[],
  core: MarketCoreSnapshot | null = null,
): MarketOverviewDashboardViewModel['decisionPosture'] {
  if (!decision) {
    const fallback = buildCoreDecisionPosture(core);
    if (fallback) {
      return fallback;
    }
    return {
      avoid: null,
      confidence: null,
      implication: 'Decision posture unavailable.',
      monitor: null,
      posture: 'Unavailable',
      prefer: null,
      tone: 'unavailable',
    };
  }
  const conflict = contradictions.find((item) => item.type === 'decision_risk' || item.type === 'health_macro');
  return {
    avoid: decision.posture.mainRisk,
    confidence: decision.posture.confidence,
    implication: conflict ? `${decision.posture.actionFramework} Monitor conflict: ${conflict.explanation}` : decision.posture.actionFramework,
    monitor: conflict?.explanation ?? decision.posture.monitor,
    posture: decision.posture.postureLabel,
    prefer: decision.posture.prefer,
    tone: mapTone(decision.posture.tone),
  };
}

function buildCoreDecisionPosture(core: MarketCoreSnapshot | null): MarketOverviewDashboardViewModel['decisionPosture'] | null {
  const summary = core?.decision_summary;
  if (!summary) {
    return null;
  }
  const posture = summary.aggressiveness?.status
    ?? summary.playbook?.suggested_aggressiveness
    ?? summary.playbook?.headline
    ?? null;
  const prefer = summary.playbook?.preferred_strategy
    ?? summary.preferred_style
    ?? null;
  const avoid = summary.playbook?.avoid?.[0]
    ?? summary.main_risk
    ?? summary.playbook?.main_risk
    ?? null;
  const monitor = summary.main_risk
    ?? summary.playbook?.main_risk
    ?? null;
  if (!posture && !prefer && !avoid && !monitor && !summary.playbook?.summary) {
    return null;
  }
  return {
    avoid,
    confidence: null,
    implication: summary.playbook?.summary
      ?? summary.aggressiveness?.summary
      ?? 'Decision posture is available from the core market snapshot while full Decision details load.',
    monitor,
    posture: posture ?? 'Decision Summary',
    prefer,
    tone: postureToneFromLabel(posture),
  };
}

export function buildOverviewKeySignals(snapshot: MarketSnapshotTile[], contradictions: MarketContradiction[]): MarketOverviewSignal[] {
  const signals = snapshot
    .map((tile): MarketOverviewSignal => ({
      key: tile.key,
      label: tile.secondary ? `${tile.primary}: ${tile.secondary}` : tile.primary,
      priority: tile.key === 'macro' || tile.key === 'breadth' ? 10 : tile.key === 'indexes' ? 9 : 7,
      sourceTab: tile.sourceTab,
      tone: tile.tone,
    }))
    .filter((signal) => signal.tone !== 'unavailable');
  const contradictionSignals = contradictions.map((item): MarketOverviewSignal => ({
    key: item.type,
    label: item.explanation,
    priority: item.severity === 'high' ? 12 : 11,
    sourceTab: 'overview',
    tone: item.severity === 'high' ? 'negative' : 'warning',
  }));
  const usedTabs = new Set<MarketSubTabKey>();
  return [...contradictionSignals, ...signals]
    .sort((a, b) => b.priority - a.priority)
    .filter((signal) => {
      if (usedTabs.has(signal.sourceTab) && signal.sourceTab !== 'overview') {
        return false;
      }
      usedTabs.add(signal.sourceTab);
      return true;
    })
    .slice(0, 5);
}

function buildMarketAlignmentSummary(
  alignment: Omit<MarketOverviewDashboardViewModel['alignment'], 'summary'>,
  contradictions: MarketContradiction[],
) {
  if (contradictions.length) {
    return `Most important conflict: ${contradictions[0].explanation}`;
  }
  if (alignment.supportive.length > alignment.caution.length && alignment.supportive.length > alignment.mixed.length) {
    return 'Most major market dimensions are supportive.';
  }
  if (alignment.caution.length > alignment.supportive.length) {
    return 'Caution signals outweigh supportive confirmation.';
  }
  return 'Market dimensions are mixed and require selective interpretation.';
}

function deriveMarketOverviewDataQuality(core: MarketCoreSnapshot | null, macro: MacroDashboardViewModel | null) {
  if (!core && !macro) {
    return { label: 'Data unavailable', tone: 'unavailable' as MarketOverviewTone };
  }
  if (macro?.dataQuality.sourceLabel === 'Test data' || macro?.dataQuality.sourceKind === 'mock') {
    return { label: 'Test data', tone: 'warning' as MarketOverviewTone };
  }
  if (macro?.dataQuality.sourceKind === 'mixed' || macro?.dataQuality.sourceKind === 'fallback' || core?.overall_mode === 'mixed') {
    return { label: 'Mixed sources', tone: 'warning' as MarketOverviewTone };
  }
  if (core?.cache_status === 'stale' || core?.is_stale) {
    return { label: 'Cached · updating', tone: 'warning' as MarketOverviewTone };
  }
  if (core?.cache_status) {
    return { label: 'Cached', tone: 'neutral' as MarketOverviewTone };
  }
  if (macro?.dataQuality.sourceKind === 'live') {
    return { label: '', tone: 'positive' as MarketOverviewTone };
  }
  return { label: '', tone: 'neutral' as MarketOverviewTone };
}

function classifyConviction(snapshot: MarketSnapshotTile[], contradictions: MarketContradiction[]) {
  if (!snapshot.length) {
    return 'Unavailable';
  }
  if (contradictions.some((item) => item.severity === 'high')) {
    return 'Cautious';
  }
  if (contradictions.length) {
    return 'Constructive';
  }
  const positives = snapshot.filter((tile) => tile.tone === 'positive').length;
  const negatives = snapshot.filter((tile) => tile.tone === 'negative').length;
  if (positives >= 4 && negatives === 0) {
    return 'High';
  }
  if (positives >= negatives) {
    return 'Constructive';
  }
  return 'Mixed';
}

function finiteNumber(value: unknown) {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function formatPercent(value: number) {
  const rounded = Math.round(value * 10) / 10;
  return `${Number.isInteger(rounded) ? rounded.toFixed(0) : rounded.toFixed(1)}%`;
}

function mapTone(tone: string): MarketOverviewTone {
  switch (tone) {
    case 'positive':
    case 'success':
      return 'positive';
    case 'negative':
    case 'danger':
      return 'negative';
    case 'warning':
      return 'warning';
    case 'neutral':
    case 'info':
      return 'neutral';
    default:
      return 'unavailable';
  }
}

function postureToneFromLabel(label: string | null): MarketOverviewTone {
  const normalized = label?.toLowerCase() ?? '';
  if (!normalized) {
    return 'neutral';
  }
  if (normalized.includes('risk-off') || normalized.includes('defensive')) {
    return 'negative';
  }
  if (normalized.includes('selective') || normalized.includes('moderately') || normalized.includes('aggressive')) {
    return 'warning';
  }
  if (normalized.includes('constructive') || normalized.includes('healthy')) {
    return 'positive';
  }
  return 'neutral';
}

function capitalize(value: string) {
  return value ? `${value.charAt(0).toUpperCase()}${value.slice(1)}` : value;
}

function lowercaseFirst(value: string) {
  return value ? `${value.charAt(0).toLowerCase()}${value.slice(1)}` : value;
}
