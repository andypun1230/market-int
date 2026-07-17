import type {
  DashboardComparisonItem,
  DecisionDashboardResponse,
  FearGreedResponse,
  MarketCapRotationItem,
  MarketCapRotationResponse,
  ProbabilityItem,
} from '@/types/market';

export type DecisionPosture =
  | 'aggressive'
  | 'selectively_aggressive'
  | 'constructive'
  | 'defensive'
  | 'capital_preservation'
  | 'unavailable';

export type SetupSuitability = 'best_fit' | 'favorable' | 'selective' | 'weak_fit' | 'avoid';
export type ChecklistStatus = 'pass' | 'monitor' | 'fail' | 'unavailable';
export type DecisionChangeDirection = 'improving' | 'weakening' | 'stable' | 'unavailable';
export type DecisionTone = 'positive' | 'warning' | 'negative' | 'neutral';

export type DecisionPostureViewModel = {
  actionFramework: string;
  aggressivenessScore: number | null;
  confidence: number | null;
  focus: string | null;
  mainRisk: string | null;
  monitor: string | null;
  riskBadgeLabel: string | null;
  posture: DecisionPosture;
  postureLabel: string;
  prefer: string | null;
  riskLabel: string;
  riskScore: number | null;
  tone: DecisionTone;
  why: string[];
};

export type PreferredSetupViewModel = {
  label: string;
  rationale: string;
  score: number;
  suitability: SetupSuitability;
  suitabilityLabel: string;
  tone: DecisionTone;
};

export type DecisionChecklistItemViewModel = {
  label: string;
  status: ChecklistStatus;
  statusLabel: string;
  tone: DecisionTone;
  value: string;
};

export type DecisionChecklistViewModel = {
  confirmed: number;
  fail: number;
  grade: string;
  items: DecisionChecklistItemViewModel[];
  monitor: number;
  pass: number;
  summary: string;
  total: number;
};

export type MarketScenarioViewModel = {
  label: string;
  value: number;
  explanation: string;
  tone: DecisionTone;
};

export type DecisionScenarioViewModel = {
  invalidation: string;
  label: string;
  summary: string;
  scenarios: MarketScenarioViewModel[];
};

export type MarketCapRotationViewModel = {
  items: MarketCapRotationItem[];
  laggard: string | null;
  leader: string | null;
  read: string;
  stateLabel: string;
};

export type FearGreedViewModel = {
  components: string[];
  confidence: number | null;
  coverageLabel: string | null;
  interpretation: string;
  score: number | null;
  sourceLabel: string;
  status: string;
  subtitle: string;
  title: string;
  tone: DecisionTone;
  updatedLabel: string | null;
};

export type DecisionChangeViewModel = {
  groups: {
    direction: DecisionChangeDirection;
    items: string[];
    label: string;
    tone: DecisionTone;
  }[];
  implication: string;
  unavailable: boolean;
};

export type DecisionDashboardViewModel = {
  capRotation: MarketCapRotationViewModel;
  changes: DecisionChangeViewModel;
  checklist: DecisionChecklistViewModel;
  leadershipFocus: string[];
  posture: DecisionPostureViewModel;
  preferredSetups: PreferredSetupViewModel[];
  scenarios: DecisionScenarioViewModel;
  sentiment: FearGreedViewModel;
};

export function buildDecisionDashboardViewModel(
  decisionDashboard: DecisionDashboardResponse | null,
  capRotation: MarketCapRotationResponse | null,
  fearGreed: FearGreedResponse | null,
): DecisionDashboardViewModel | null {
  if (!decisionDashboard) {
    return null;
  }
  const posture = buildPosture(decisionDashboard, capRotation);
  return {
    capRotation: buildMarketCapRotation(capRotation),
    changes: buildChanges(decisionDashboard.comparison?.items ?? []),
    checklist: buildChecklist(decisionDashboard),
    leadershipFocus: buildLeadershipFocus(decisionDashboard),
    posture,
    preferredSetups: buildPreferredSetups(decisionDashboard),
    scenarios: buildScenarios(decisionDashboard.probabilities?.items ?? [], posture),
    sentiment: buildFearGreed(fearGreed),
  };
}

export function buildPosture(
  dashboard: DecisionDashboardResponse,
  capRotation: MarketCapRotationResponse | null,
): DecisionPostureViewModel {
  const confidence = validNumber(dashboard.decision_confidence?.score);
  const aggressiveness = validNumber(dashboard.aggressiveness?.score);
  const riskScore = validNumber(dashboard.risk_dashboard?.score);
  const checklistRatio = dashboard.checklist.max_score > 0 ? dashboard.checklist.score / dashboard.checklist.max_score : null;
  const weakChecklist = checklistRatio !== null && checklistRatio < 0.62;
  const highRisk = riskScore !== null && riskScore >= 55;
  const rawPosture = classifyPosture(aggressiveness, confidence, riskScore);
  const posture = rawPosture === 'aggressive' && (weakChecklist || highRisk)
    ? 'selectively_aggressive'
    : rawPosture;
  const focus = buildFocus(dashboard);
  const prefer = dashboard.playbook?.preferred_strategy ?? dashboard.trading_styles?.preferred_style ?? null;
  const mainRisk = dashboard.playbook?.main_risk ?? null;
  const avoid = buildAvoid(dashboard, mainRisk);
  const monitor = buildMonitor(dashboard, mainRisk, avoid);
  return {
    actionFramework: dashboard.playbook?.summary ?? dashboard.aggressiveness?.summary ?? 'Decision guidance unavailable.',
    aggressivenessScore: aggressiveness,
    confidence,
    focus,
    mainRisk: avoid,
    monitor,
    posture,
    postureLabel: postureLabel(posture, dashboard.playbook?.headline),
    prefer,
    riskLabel: riskLabel(riskScore),
    riskBadgeLabel: riskScore === null ? null : `${riskLabel(riskScore)} Risk`,
    riskScore,
    tone: postureTone(posture, riskScore),
    why: [
      dashboard.aggressiveness?.summary,
      dashboard.decision_confidence?.summary,
      dashboard.risk_dashboard?.summary,
    ].filter((item): item is string => Boolean(item)),
  };
}

export function buildPreferredSetups(dashboard: DecisionDashboardResponse): PreferredSetupViewModel[] {
  const items = dashboard.trading_styles?.items ?? [];
  return items
    .map((item): PreferredSetupViewModel => {
      const label = setupLabel(item.style);
      const suitability = suitabilityForScore(item.score);
      return {
        label,
        rationale: item.reason,
        score: item.score,
        suitability,
        suitabilityLabel: suitabilityLabel(suitability),
        tone: suitabilityTone(suitability),
      };
    })
    .sort((a, b) => b.score - a.score || a.label.localeCompare(b.label))
    .slice(0, 5);
}

export function buildChecklist(dashboard: DecisionDashboardResponse): DecisionChecklistViewModel {
  const items = (dashboard.checklist?.items ?? []).map((item): DecisionChecklistItemViewModel => {
    const status = item.passed ? 'pass' : checklistFallbackStatus(item.label, item.value);
    return {
      label: compactChecklistLabel(item.label),
      status,
      statusLabel: checklistStatusLabel(status),
      tone: checklistTone(status),
      value: item.value,
    };
  });
  const pass = items.filter((item) => item.status === 'pass').length;
  const monitor = items.filter((item) => item.status === 'monitor').length;
  const fail = items.filter((item) => item.status === 'fail').length;
  return {
    confirmed: pass,
    fail,
    grade: dashboard.checklist?.grade ?? 'Unavailable',
    items,
    monitor,
    pass,
    summary: dashboard.checklist?.summary ?? 'Checklist unavailable.',
    total: dashboard.checklist?.max_score ?? items.length,
  };
}

export function buildScenarios(
  probabilities: ProbabilityItem[],
  posture: DecisionPostureViewModel,
): DecisionScenarioViewModel {
  const top = probabilities
    .filter((item) => Number.isFinite(item.probability) && item.probability > 0)
    .sort((a, b) => b.probability - a.probability)
    .slice(0, 4);
  const total = top.reduce((sum, item) => sum + item.probability, 0);
  const scenarioMap = new Map<string, MarketScenarioViewModel>();
  if (total > 0) {
    for (const item of top) {
      const label = scenarioLabel(item.strategy);
      const current = scenarioMap.get(label);
      const nextValue = Math.round((item.probability / total) * 100);
      scenarioMap.set(label, {
        explanation: current?.explanation ?? item.explanation,
        label,
        tone: scenarioTone(label),
        value: (current?.value ?? 0) + nextValue,
      });
    }
  }
  const scenarios = normalizeScenarioTotal([...scenarioMap.values()]
    .sort((a, b) => b.value - a.value)
    .slice(0, 4));
  return {
    invalidation: buildInvalidation(posture),
    label: 'Scenario Weights',
    summary: scenarioSummary(scenarios),
    scenarios,
  };
}

export function buildMarketCapRotation(capRotation: MarketCapRotationResponse | null): MarketCapRotationViewModel {
  if (!capRotation || !capRotation.items.length) {
    return {
      items: [],
      laggard: null,
      leader: null,
      read: 'Market-cap rotation unavailable.',
      stateLabel: 'Unavailable',
    };
  }
  const sorted = [...capRotation.items].sort((a, b) => b.score - a.score);
  const leader = sorted[0]?.category ?? capRotation.leader;
  const laggard = sorted.at(-1)?.category ?? capRotation.laggard;
  const spread = (sorted[0]?.score ?? 0) - (sorted.at(-1)?.score ?? 0);
  const stateLabel = spread < 15
    ? 'Balanced'
    : leader.toLowerCase().includes('mega')
      ? 'Mega-Cap Concentration'
      : leader.toLowerCase().includes('small')
        ? 'Small-Cap Recovery'
        : `${leader} Leading`;
  return {
    items: capRotation.items,
    laggard,
    leader,
    read: capRotation.summary || `${leader} is leading while ${laggard} is lagging.`,
    stateLabel,
  };
}

export function buildFearGreed(fearGreed: FearGreedResponse | null): FearGreedViewModel {
  const score = validNumber(fearGreed?.score);
  const sourceType = fearGreed?.source_type ?? null;
  const title = fearGreed?.title ?? (sourceType === 'official' ? 'CNN Fear & Greed Index' : sourceType === 'estimated' ? 'Fear & Greed Estimate' : 'Fear & Greed unavailable');
  const subtitle = fearGreed?.subtitle ?? (sourceType === 'official' ? 'Source: CNN' : sourceType === 'estimated' ? 'Based on CNN methodology' : 'Latest verified reading could not be retrieved');
  const coverage = validNumber(fearGreed?.coverage_components);
  const required = validNumber(fearGreed?.required_components) ?? 7;
  const components = (fearGreed?.components ?? []).map((component) => {
    const state = component.missing ? 'missing' : component.data_state ?? 'unknown';
    const confidence = validNumber(component.confidence);
    return `${component.label}: ${component.missing ? 'Unavailable' : `${component.score} · ${component.status}`} · ${state}${component.source ? ` · ${component.source}` : ''}${confidence !== null ? ` · confidence ${confidence}%` : ''}`;
  });
  if (score === null) {
    return {
      components,
      confidence: validNumber(fearGreed?.confidence),
      coverageLabel: coverage !== null ? `${coverage}/${required}` : null,
      interpretation: 'Fear & Greed data unavailable.',
      score: null,
      sourceLabel: sourceType === 'estimated' ? 'Estimate unavailable' : 'Latest verified reading could not be retrieved',
      status: 'Unavailable',
      subtitle,
      title,
      tone: 'neutral',
      updatedLabel: formatTimestampLabel(fearGreed?.source_timestamp ?? fearGreed?.fetched_at ?? null),
    };
  }
  const status = fearGreed?.status ?? 'Unavailable';
  return {
    components,
    confidence: validNumber(fearGreed?.confidence),
    coverageLabel: coverage !== null ? `${coverage}/${required}` : null,
    interpretation: fearGreedInterpretation(status),
    score,
    sourceLabel: sourceType === 'official' ? 'Source: CNN' : sourceType === 'estimated' ? 'Based on CNN methodology' : 'Source unavailable',
    status,
    subtitle,
    title,
    tone: fearGreedTone(status),
    updatedLabel: formatTimestampLabel(fearGreed?.source_timestamp ?? fearGreed?.fetched_at ?? null),
  };
}

export function buildChanges(items: DashboardComparisonItem[]): DecisionChangeViewModel {
  if (!items.length) {
    return {
      groups: [],
      implication: 'Recent changes unavailable.',
      unavailable: true,
    };
  }
  const groups = [
    { direction: 'improving' as const, label: 'Improving', tone: 'positive' as const, items: [] as string[] },
    { direction: 'weakening' as const, label: 'Weakening', tone: 'warning' as const, items: [] as string[] },
    { direction: 'stable' as const, label: 'Stable', tone: 'neutral' as const, items: [] as string[] },
  ];
  for (const item of items) {
    const direction = changeDirection(item.change);
    const group = groups.find((candidate) => candidate.direction === direction);
    if (group && group.items.length < 4) {
        group.items.push(`${userFacingMetricLabel(item.metric)} ${formatDelta(item.change)}`);
    }
  }
  const visibleGroups = groups.filter((group) => group.items.length);
  return {
    groups: visibleGroups,
    implication: visibleGroups.length
      ? 'Recent inputs are mixed; keep the playbook tied to confirmed conditions.'
      : 'Recent changes unavailable.',
    unavailable: !visibleGroups.length,
  };
}

export function fearGreedStatus(score: number) {
  if (score <= 24) {
    return 'Extreme Fear';
  }
  if (score <= 44) {
    return 'Fear';
  }
  if (score <= 55) {
    return 'Neutral';
  }
  if (score <= 75) {
    return 'Greed';
  }
  return 'Extreme Greed';
}

function formatTimestampLabel(value?: string | null) {
  if (!value) {
    return null;
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return `Updated ${date.toLocaleString()}`;
}

export function gaugeMarkerPercent(score: number | null) {
  return score === null ? 0 : Math.max(0, Math.min(100, score));
}

function classifyPosture(
  aggressiveness: number | null,
  confidence: number | null,
  riskScore: number | null,
): DecisionPosture {
  if (aggressiveness === null && confidence === null) {
    return 'unavailable';
  }
  if ((riskScore ?? 0) >= 70 || (aggressiveness ?? 0) < 40) {
    return 'capital_preservation';
  }
  if ((riskScore ?? 0) >= 55 || (aggressiveness ?? 0) < 55) {
    return 'defensive';
  }
  if ((aggressiveness ?? 0) >= 85 && (confidence ?? 0) >= 70 && (riskScore ?? 100) < 45) {
    return 'aggressive';
  }
  if ((aggressiveness ?? 0) >= 70) {
    return 'selectively_aggressive';
  }
  return 'constructive';
}

function postureLabel(posture: DecisionPosture, headline?: string | null) {
  if (headline && posture !== 'unavailable') {
    return headline;
  }
  switch (posture) {
    case 'aggressive':
      return 'Aggressive';
    case 'selectively_aggressive':
      return 'Selectively Aggressive';
    case 'constructive':
      return 'Constructive';
    case 'defensive':
      return 'Defensive';
    case 'capital_preservation':
      return 'Capital Preservation';
    default:
      return 'Unavailable';
  }
}

function postureTone(posture: DecisionPosture, riskScore: number | null): DecisionTone {
  if ((riskScore ?? 0) >= 60 || posture === 'capital_preservation') {
    return 'negative';
  }
  if (posture === 'defensive') {
    return 'warning';
  }
  if (posture === 'aggressive' || posture === 'selectively_aggressive') {
    return 'positive';
  }
  return 'neutral';
}

function setupLabel(style: string) {
  const normalized = style.toLowerCase();
  if (normalized.includes('momentum') || normalized.includes('breakout')) {
    return 'Breakout Attempt';
  }
  if (normalized.includes('trend')) {
    return 'Trend Continuation';
  }
  if (normalized.includes('pullback')) {
    return 'Pullback to Support';
  }
  if (normalized.includes('mean')) {
    return 'Mean Reversion';
  }
  if (normalized.includes('short')) {
    return 'Defensive Positioning';
  }
  return style;
}

function suitabilityForScore(score: number): SetupSuitability {
  if (score >= 82) {
    return 'best_fit';
  }
  if (score >= 70) {
    return 'favorable';
  }
  if (score >= 55) {
    return 'selective';
  }
  if (score >= 40) {
    return 'weak_fit';
  }
  return 'avoid';
}

function suitabilityLabel(value: SetupSuitability) {
  switch (value) {
    case 'best_fit':
      return 'Best Fit';
    case 'favorable':
      return 'Favorable';
    case 'selective':
      return 'Selective';
    case 'weak_fit':
      return 'Weak Fit';
    default:
      return 'Avoid';
  }
}

function suitabilityTone(value: SetupSuitability): DecisionTone {
  switch (value) {
    case 'best_fit':
    case 'favorable':
      return 'positive';
    case 'selective':
      return 'warning';
    case 'weak_fit':
      return 'neutral';
    default:
      return 'negative';
  }
}

function checklistFallbackStatus(label: string, value: string): ChecklistStatus {
  const text = `${label} ${value}`.toLowerCase();
  if (text.includes('high volatility') || text.includes('extreme greed') || text.includes('risk-off')) {
    return 'fail';
  }
  return 'monitor';
}

function checklistStatusLabel(status: ChecklistStatus) {
  switch (status) {
    case 'pass':
      return 'Pass';
    case 'monitor':
      return 'Monitor';
    case 'fail':
      return 'Fail';
    default:
      return 'Unavailable';
  }
}

function checklistTone(status: ChecklistStatus): DecisionTone {
  switch (status) {
    case 'pass':
      return 'positive';
    case 'monitor':
      return 'warning';
    case 'fail':
      return 'negative';
    default:
      return 'neutral';
  }
}

function compactChecklistLabel(label: string) {
  return label
    .replace('Market health above 70', 'Market Health')
    .replace('Breadth above 50EMA', 'Breadth')
    .replace('Institutional bias Bullish or Neutral', 'Institutions')
    .replace('Top sector strength', 'Sector Participation')
    .replace('Volatility not High', 'Volatility')
    .replace('Distribution days', 'Distribution Pressure')
    .replace('Fear & Greed not Extreme Greed', 'Sentiment')
    .replace('Mega or large cap leadership positive', 'Market-Cap Leadership');
}

function scenarioLabel(strategy: string) {
  const normalized = strategy.toLowerCase();
  if (normalized.includes('trend')) {
    return 'Trend Continuation';
  }
  if (normalized.includes('pullback')) {
    return 'Normal Pullback';
  }
  if (normalized.includes('mean')) {
    return 'Sideways Consolidation';
  }
  if (normalized.includes('short')) {
    return 'Correction';
  }
  if (normalized.includes('gap')) {
    return 'Trend Continuation';
  }
  if (normalized.includes('breakout') || normalized.includes('momentum')) {
    return 'Trend Continuation';
  }
  return strategy;
}

function scenarioTone(strategy: string): DecisionTone {
  const normalized = strategy.toLowerCase();
  if (normalized.includes('correction')) {
    return 'negative';
  }
  if (normalized.includes('sideways') || normalized.includes('pullback')) {
    return 'warning';
  }
  return 'positive';
}

function normalizeScenarioTotal(items: MarketScenarioViewModel[]) {
  const total = items.reduce((sum, item) => sum + item.value, 0);
  if (!items.length || total === 100) {
    return items;
  }
  const delta = 100 - total;
  return items.map((item, index) => index === 0 ? { ...item, value: Math.max(0, item.value + delta) } : item);
}

function buildInvalidation(posture: DecisionPostureViewModel) {
  if (posture.posture === 'defensive' || posture.posture === 'capital_preservation') {
    return 'Risk improves only if breadth and index trend stabilize together.';
  }
  return 'SPY loses EMA50 while breadth deteriorates.';
}

function buildMarketCapScore(items: MarketCapRotationItem[], category: string) {
  return items.find((item) => item.category.toLowerCase().includes(category))?.score ?? null;
}

function buildFocus(dashboard: DecisionDashboardResponse) {
  const hasSpecifics = Boolean(dashboard.playbook?.top_sector || dashboard.playbook?.top_industry_group || dashboard.playbook?.cap_rotation_leader);
  return hasSpecifics ? 'Leading sectors, themes, and stronger market-cap groups' : null;
}

function buildLeadershipFocus(dashboard: DecisionDashboardResponse) {
  const items = [
    dashboard.playbook?.top_sector,
    dashboard.playbook?.top_industry_group,
    dashboard.playbook?.cap_rotation_leader,
  ].filter((item): item is string => Boolean(item));
  return Array.from(new Set(items)).slice(0, 3);
}

function riskLabel(score: number | null) {
  if (score === null) {
    return 'Unavailable';
  }
  if (score >= 70) {
    return 'High';
  }
  if (score >= 45) {
    return 'Elevated';
  }
  if (score >= 25) {
    return 'Moderate';
  }
  return 'Low';
}

function fearGreedTone(status: string): DecisionTone {
  const normalized = status.toLowerCase();
  if (normalized.includes('extreme fear') || normalized.includes('extreme greed')) {
    return 'warning';
  }
  if (normalized === 'fear') {
    return 'negative';
  }
  if (normalized === 'greed') {
    return 'positive';
  }
  return 'neutral';
}

function fearGreedInterpretation(status: string) {
  if (status.includes('Extreme Greed')) {
    return 'Optimism is stretched. Risk appetite is strong, but chasing extended moves becomes less attractive.';
  }
  if (status.includes('Greed')) {
    return 'Optimism is elevated. Risk appetite remains supportive, but chasing extended moves becomes less attractive.';
  }
  if (status.includes('Extreme Fear')) {
    return 'Fear is elevated. Conditions may improve later, but confirmation matters before increasing risk.';
  }
  if (status.includes('Fear')) {
    return 'Sentiment is cautious; confirmation matters more than chasing strength.';
  }
  return 'Sentiment is neutral and should be weighed alongside trend and breadth.';
}

function changeDirection(change: number | string): DecisionChangeDirection {
  if (typeof change === 'number') {
    if (change > 1) {
      return 'improving';
    }
    if (change < -1) {
      return 'weakening';
    }
    return 'stable';
  }
  const text = change.toLowerCase();
  if (text.includes('up') || text.includes('improv') || text.startsWith('+')) {
    return 'improving';
  }
  if (text.includes('down') || text.includes('weak') || text.startsWith('-')) {
    return 'weakening';
  }
  return 'stable';
}

function userFacingMetricLabel(metric: string) {
  return metric
    .replace(/market health/gi, 'Market posture')
    .replace(/sector strength/gi, 'Sector participation')
    .replace(/fear.?greed/gi, 'Sentiment')
    .replace(/aggressiveness/gi, 'Exposure stance')
    .replace(/_/g, ' ');
}

function buildAvoid(dashboard: DecisionDashboardResponse, mainRisk: string | null) {
  const avoid = firstNonEmpty(dashboard.playbook?.avoid);
  if (avoid) {
    return avoid;
  }
  return mainRisk ? `Avoid chasing while ${mainRisk.toLowerCase()} remains active.` : null;
}

function buildMonitor(dashboard: DecisionDashboardResponse, mainRisk: string | null, avoid: string | null) {
  const candidates = [
    mainRisk,
    firstNonEmpty(dashboard.aggressiveness?.cautions),
    'Sector participation, breadth confirmation, and extreme sentiment',
  ].filter((item): item is string => Boolean(item));
  const distinct = candidates.find((item) => item.trim().toLowerCase() !== avoid?.trim().toLowerCase());
  return distinct ?? null;
}

function scenarioSummary(scenarios: MarketScenarioViewModel[]) {
  if (!scenarios.length) {
    return 'Market scenarios unavailable.';
  }
  const [first, second] = scenarios;
  if (second && Math.abs(first.value - second.value) <= 8) {
    return 'No dominant scenario; conditions remain balanced.';
  }
  return `${first.label} is favored, but scenario weights remain heuristic.`;
}

function formatDelta(change: number | string) {
  if (typeof change === 'number' && Number.isFinite(change)) {
    if (Math.abs(change) < 0.01) {
      return '0';
    }
    return `${change > 0 ? '+' : ''}${Math.round(change * 10) / 10}`;
  }
  return String(change);
}

function validNumber(value: number | null | undefined) {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function firstNonEmpty(items?: string[]) {
  return items?.find((item) => item.trim().length > 0) ?? null;
}

export const decisionInternalsForTests = {
  buildMarketCapScore,
  checklistFallbackStatus,
  classifyPosture,
  setupLabel,
  suitabilityForScore,
};
