import type { DecisionConfidenceResponse, MarketHealthComponents, MarketHealthResponse } from '@/types/market';

export type HealthComponentKey =
  | 'momentum'
  | 'breadth'
  | 'trend'
  | 'volume'
  | 'institutional'
  | 'volatility'
  | 'sectorStrength';

export type HealthScoreTone =
  | 'excellent'
  | 'strong'
  | 'constructive'
  | 'mixed'
  | 'weak'
  | 'unavailable';

export type HealthDirection =
  | 'improving'
  | 'stable'
  | 'weakening'
  | 'unavailable';

export type HealthHistoryStatus =
  | 'available'
  | 'collecting'
  | 'unavailable';

export type HealthDriverKind =
  | 'supporting'
  | 'monitor';

export type HealthComponentViewModel = {
  contribution: number | null;
  direction: HealthDirection;
  explanation: string;
  key: HealthComponentKey;
  label: string;
  rawExplanation?: string | null;
  score: number | null;
  status: string;
  tone: HealthScoreTone;
  weight: number;
};

export type HealthDriver = {
  component?: HealthComponentKey;
  kind: HealthDriverKind;
  label: string;
  priority: number;
  tone: 'supportive' | 'warning' | 'negative' | 'neutral';
};

export type HealthContributionViewModel = {
  component: HealthComponentKey;
  displayedPoints: number;
  label: string;
  rawContribution: number;
  score: number;
  weight: number;
};

export type HealthTrendPoint = {
  label: string;
  score: number;
};

export type HealthRadarDatum = {
  key: HealthComponentKey;
  label: string;
  score: number | null;
};

export type HealthRadarPoint = HealthRadarDatum & {
  displayScore: number;
  x: number;
  y: number;
};

export type HealthSnapshot = {
  score: number;
  source?: 'live' | 'cached' | 'mock' | 'local';
  timestamp: string;
};

export type HealthTrendRange = '1W' | '1M' | '3M';

export type HealthTrendSummary = {
  change: number | null;
  direction: HealthDirection;
  endScore: number | null;
  range: HealthTrendRange;
  startScore: number | null;
};

const HEALTH_COMPONENTS: {
  apiKey: keyof MarketHealthComponents;
  key: HealthComponentKey;
  label: string;
  shortLabel: string;
  weight: number;
}[] = [
  { apiKey: 'momentum', key: 'momentum', label: 'Momentum', shortLabel: 'Momentum', weight: 0.2 },
  { apiKey: 'breadth', key: 'breadth', label: 'Breadth', shortLabel: 'Breadth', weight: 0.2 },
  { apiKey: 'trend', key: 'trend', label: 'Trend', shortLabel: 'Trend', weight: 0.15 },
  { apiKey: 'volume', key: 'volume', label: 'Volume', shortLabel: 'Volume', weight: 0.1 },
  { apiKey: 'institutional', key: 'institutional', label: 'Institutional', shortLabel: 'Institutional', weight: 0.15 },
  { apiKey: 'volatility', key: 'volatility', label: 'Volatility', shortLabel: 'Volatility', weight: 0.1 },
  { apiKey: 'sector_strength', key: 'sectorStrength', label: 'Sector Strength', shortLabel: 'Sector Strength', weight: 0.1 },
];

export function buildHealthComponents(health: MarketHealthResponse | null): HealthComponentViewModel[] {
  if (!health) {
    return [];
  }
  return HEALTH_COMPONENTS.map((component) => {
    const score = normalizeScore(health.components[component.apiKey]);
    return {
      contribution: score === null ? null : score * component.weight,
      direction: 'unavailable' as HealthDirection,
      explanation: buildHealthComponentExplanation(component.key, score),
      key: component.key,
      label: component.label,
      rawExplanation: health.component_explanations[component.apiKey] ?? null,
      score,
      status: classifyHealthScore(score).label,
      tone: classifyHealthScore(score).tone,
      weight: component.weight,
    };
  }).filter((component) => component.score !== null);
}

export function classifyHealthScore(score: number | null | undefined) {
  if (score === null || score === undefined || !Number.isFinite(score)) {
    return { label: 'Unavailable', tone: 'unavailable' as HealthScoreTone };
  }
  if (score >= 90) {
    return { label: 'Excellent', tone: 'excellent' as HealthScoreTone };
  }
  if (score >= 75) {
    return { label: 'Strong', tone: 'strong' as HealthScoreTone };
  }
  if (score >= 60) {
    return { label: 'Constructive', tone: 'constructive' as HealthScoreTone };
  }
  if (score >= 40) {
    return { label: 'Mixed', tone: 'mixed' as HealthScoreTone };
  }
  return { label: 'Weak', tone: 'weak' as HealthScoreTone };
}

export function formatHealthScore(score: number | null | undefined) {
  return score === null || score === undefined || !Number.isFinite(score)
    ? 'N/A'
    : String(Math.round(score));
}

export function classifyHealthDirection(history: HealthTrendPoint[]) {
  if (history.length < 2) {
    return 'unavailable' as HealthDirection;
  }
  const first = history[0].score;
  const latest = history.at(-1)?.score ?? first;
  const change = latest - first;
  if (change >= 3) {
    return 'improving' as HealthDirection;
  }
  if (change <= -3) {
    return 'weakening' as HealthDirection;
  }
  return 'stable' as HealthDirection;
}

export function formatHealthDirection(direction: HealthDirection) {
  switch (direction) {
    case 'improving':
      return 'Improving';
    case 'stable':
      return 'Stable';
    case 'weakening':
      return 'Weakening';
    default:
      return 'Unavailable';
  }
}

export function getHealthHistoryBadgeLabel(status: HealthHistoryStatus) {
  switch (status) {
    case 'available':
      return 'History available';
    case 'collecting':
      return 'History collecting';
    default:
      return 'Trend history unavailable';
  }
}

export function getHealthSourceBadgeLabel(mode: string | null | undefined) {
  if (!mode) {
    return null;
  }
  const normalized = mode.toLowerCase();
  if (normalized === 'mock') {
    return 'Mock data';
  }
  if (normalized === 'live') {
    return 'Live data';
  }
  if (normalized === 'mixed') {
    return 'Mixed data';
  }
  if (normalized === 'cached') {
    return 'Cached data';
  }
  return `${normalized.charAt(0).toUpperCase()}${normalized.slice(1)} data`;
}

export function buildHealthRadarData(health: MarketHealthResponse | null): HealthRadarDatum[] {
  if (!health) {
    return [];
  }
  return HEALTH_COMPONENTS.map((component) => ({
    key: component.key,
    label: component.shortLabel,
    score: validateHealthComponentScore(health.components[component.apiKey]),
  }));
}

export function validateHealthComponentScore(value: number | null | undefined) {
  return value === null || value === undefined || !Number.isFinite(value) ? null : value;
}

export function clampHealthScoreForDisplay(value: number) {
  if (!Number.isFinite(value)) {
    return null;
  }
  return Math.max(0, Math.min(100, value));
}

export function calculateRadarPoints(
  data: HealthRadarDatum[],
  centerX: number,
  centerY: number,
  radius: number,
): HealthRadarPoint[] {
  const valid = data.filter((item) => item.score !== null);
  if (valid.length < 3 || radius <= 0) {
    return [];
  }
  return valid
    .map((item, index) => {
      const displayScore = clampHealthScoreForDisplay(item.score ?? NaN);
      if (displayScore === null) {
        return null;
      }
      const angle = -Math.PI / 2 + (index / valid.length) * Math.PI * 2;
      const distance = radius * (displayScore / 100);
      return {
        ...item,
        displayScore,
        x: centerX + Math.cos(angle) * distance,
        y: centerY + Math.sin(angle) * distance,
      };
    })
    .filter((point): point is HealthRadarPoint => Boolean(point));
}

export function calculateRadarGridPoints(
  count: number,
  centerX: number,
  centerY: number,
  radius: number,
  ringPercent: number,
) {
  if (count < 3 || radius <= 0) {
    return [];
  }
  const ringRadius = radius * (Math.max(0, Math.min(100, ringPercent)) / 100);
  return Array.from({ length: count }, (_, index) => {
    const angle = -Math.PI / 2 + (index / count) * Math.PI * 2;
    return {
      x: centerX + Math.cos(angle) * ringRadius,
      y: centerY + Math.sin(angle) * ringRadius,
    };
  });
}

export function normalizeHealthHistory(history: HealthSnapshot[]) {
  const byTimestamp = new Map<string, HealthSnapshot>();
  history.forEach((snapshot) => {
    const time = Date.parse(snapshot.timestamp);
    const score = validateHealthComponentScore(snapshot.score);
    if (!Number.isFinite(time) || score === null) {
      return;
    }
    byTimestamp.set(new Date(time).toISOString(), {
      ...snapshot,
      score,
      timestamp: new Date(time).toISOString(),
    });
  });
  return Array.from(byTimestamp.values()).sort((a, b) => Date.parse(a.timestamp) - Date.parse(b.timestamp));
}

export function filterHealthHistoryByRange(history: HealthSnapshot[], range: HealthTrendRange) {
  const normalized = normalizeHealthHistory(history);
  const latest = normalized.at(-1);
  if (!latest) {
    return [];
  }
  const cutoff = Date.parse(latest.timestamp) - getHealthTrendRangeDays(range) * 24 * 60 * 60 * 1000;
  return normalized.filter((snapshot) => Date.parse(snapshot.timestamp) >= cutoff);
}

export function calculateHealthTrendSummary(history: HealthSnapshot[], range: HealthTrendRange): HealthTrendSummary {
  const selected = filterHealthHistoryByRange(history, range);
  if (selected.length < 2) {
    return {
      change: null,
      direction: 'unavailable',
      endScore: selected.at(-1)?.score ?? null,
      range,
      startScore: selected[0]?.score ?? null,
    };
  }
  const startScore = selected[0].score;
  const endScore = selected.at(-1)?.score ?? startScore;
  const change = endScore - startScore;
  return {
    change,
    direction: classifyHealthDirection(selected.map((snapshot) => ({
      label: snapshot.timestamp,
      score: snapshot.score,
    }))),
    endScore,
    range,
    startScore,
  };
}

export function getSupportedHealthTrendRanges(history: HealthSnapshot[]) {
  const normalized = normalizeHealthHistory(history);
  return (['1W', '1M', '3M'] as const).filter((range) => filterHealthHistoryByRange(normalized, range).length >= 2);
}

export function calculateHealthChartTicks() {
  return [40, 60, 75, 90] as const;
}

export function deriveHealthDrivers(components: HealthComponentViewModel[], health?: MarketHealthResponse | null) {
  const strong = [...components]
    .filter((component) => (component.score ?? 0) >= 75)
    .sort((a, b) => (b.contribution ?? 0) - (a.contribution ?? 0))
    .slice(0, 4)
    .map((component) => ({
      component: component.key,
      kind: 'supporting' as const,
      label: buildSupportDriver(component),
      priority: Math.round((component.contribution ?? 0) * 10) / 10,
      tone: 'supportive' as const,
    }));

  const monitor = [...components]
    .filter((component) => component.score !== null)
    .filter((component) => (component.score ?? 100) < 75 || component.key === 'trend' || component.key === 'sectorStrength')
    .sort((a, b) => {
      const scoreDiff = (a.score ?? 100) - (b.score ?? 100);
      if (scoreDiff !== 0) {
        return scoreDiff;
      }
      return b.weight - a.weight;
    })
    .slice(0, 3)
    .map((component) => ({
      component: component.key,
      kind: 'monitor' as const,
      label: buildMonitorDriver(component),
      priority: 100 - (component.score ?? 100),
      tone: component.score !== null && component.score < 40 ? 'negative' as const : 'warning' as const,
    }));

  const backendSupport = (health?.improving_factors ?? [])
    .slice(0, Math.max(0, 4 - strong.length))
    .map((label, index) => ({
      kind: 'supporting' as const,
      label: rewriteDriverLabel(label),
      priority: 1 - index / 10,
      tone: 'supportive' as const,
    }));
  const backendWeak = (health?.weakening_factors ?? [])
    .filter((label) => !isNoWeakeningLabel(label))
    .slice(0, Math.max(0, 3 - monitor.length))
    .map((label, index) => ({
      kind: 'monitor' as const,
      label: rewriteDriverLabel(label),
      priority: 1 - index / 10,
      tone: 'warning' as const,
    }));

  return {
    supporting: [...strong, ...backendSupport].slice(0, 4),
    monitor: [...monitor, ...backendWeak].slice(0, 3),
    weakening: [...monitor, ...backendWeak].slice(0, 3),
  };
}

export function calculateScoreContributions(components: HealthComponentViewModel[]) {
  const valid = components.filter((component) => component.score !== null);
  const totalWeight = valid.reduce((sum, component) => sum + component.weight, 0);
  if (!totalWeight) {
    return [];
  }
  return valid
    .map((component) => ({
      ...component,
      contribution: ((component.score ?? 0) * component.weight) / totalWeight,
    }))
    .sort((a, b) => (b.contribution ?? 0) - (a.contribution ?? 0));
}

export function getContributionTotal(contributions: Pick<HealthComponentViewModel, 'contribution'>[]) {
  return Math.round(contributions.reduce((sum, component) => sum + (component.contribution ?? 0), 0));
}

export function buildHealthContributions(
  components: HealthComponentViewModel[],
  compositeScore: number | null | undefined,
): HealthContributionViewModel[] {
  const contributions = calculateScoreContributions(components)
    .filter((component) => component.score !== null && component.contribution !== null)
    .map((component) => ({
      component: component.key,
      label: component.label,
      rawContribution: component.contribution ?? 0,
      score: component.score ?? 0,
      weight: component.weight,
    }));
  const displayedPoints = reconcileRoundedContributions(
    contributions.map((component) => component.rawContribution),
    normalizeContributionTarget(compositeScore, contributions),
  );
  return contributions.map((component, index) => ({
    ...component,
    displayedPoints: displayedPoints[index] ?? Math.round(component.rawContribution),
  }));
}

export function reconcileRoundedContributions(values: number[], targetTotal: number) {
  const safeValues = values.map((value) => (Number.isFinite(value) && value > 0 ? value : 0));
  const floors = safeValues.map(Math.floor);
  let remaining = targetTotal - floors.reduce((sum, value) => sum + value, 0);
  const order = safeValues
    .map((value, index) => ({ fraction: value - Math.floor(value), index }))
    .sort((a, b) => {
      const diff = b.fraction - a.fraction;
      return diff !== 0 ? diff : a.index - b.index;
    });
  const reconciled = [...floors];
  let cursor = 0;
  while (remaining > 0 && order.length) {
    reconciled[order[cursor % order.length].index] += 1;
    remaining -= 1;
    cursor += 1;
  }
  while (remaining < 0 && order.length) {
    const reverseOrder = [...order].reverse();
    const target = reverseOrder[cursor % reverseOrder.length].index;
    if (reconciled[target] > 0) {
      reconciled[target] -= 1;
      remaining += 1;
    }
    cursor += 1;
    if (cursor > reverseOrder.length * 3 && remaining < 0) {
      break;
    }
  }
  return reconciled;
}

export function buildHealthOverviewSummary(components: HealthComponentViewModel[], health: MarketHealthResponse | null) {
  if (!health) {
    return 'Market health is unavailable until component data loads.';
  }
  const drivers = deriveHealthDrivers(components, health);
  const supportPhrase = formatDriverPhrase(drivers.supporting.slice(0, 3), 'support');
  const monitorPhrase = formatDriverPhrase(drivers.monitor.slice(0, 2), 'monitor');
  if (supportPhrase && monitorPhrase) {
    return `Overall health is supported by ${supportPhrase}. ${monitorPhrase} remain the main areas to monitor.`;
  }
  if (supportPhrase) {
    return `Overall health is supported by ${supportPhrase}. No material risk signal is currently dominant.`;
  }
  return health.summary || 'Overall health is mixed, with more confirmation needed from the major components.';
}

export function buildDecisionLayerSummary(
  confidence: DecisionConfidenceResponse | null | undefined,
  components: HealthComponentViewModel[],
  health: MarketHealthResponse | null,
) {
  if (!confidence) {
    return {
      implication: 'Decision confidence is unavailable until agreement data loads.',
      monitor: 'Component agreement',
      stance: health?.status ?? 'Unavailable',
      supports: 'Market health components',
    };
  }
  const drivers = deriveHealthDrivers(components, health);
  const supports = formatDriverPhrase(drivers.supporting.slice(0, 2), 'support') ?? 'component agreement';
  const monitor = formatDriverPhrase(drivers.monitor.slice(0, 2), 'monitor') ?? 'No material risk signal';
  return {
    implication: `Market conditions remain ${health?.status?.toLowerCase() ?? 'constructive'}, supported by ${supports}. ${monitor === 'No material risk signal' ? 'No material risk signal is currently dominant.' : `${monitor} remain the main areas to monitor.`}`,
    monitor,
    stance: confidence.status,
    supports,
  };
}

export function buildHealthComponentExplanation(key: HealthComponentKey, score: number | null) {
  const status = classifyHealthScore(score).label.toLowerCase();
  switch (key) {
    case 'momentum':
      return score !== null && score >= 75
        ? 'Core indexes remain above key intermediate moving averages, supporting positive momentum.'
        : 'Momentum needs more confirmation from the major indexes.';
    case 'breadth':
      return score !== null && score >= 75
        ? 'Participation is broad across the tracked universe.'
        : 'Participation is uneven and needs monitoring.';
    case 'trend':
      return score !== null && score >= 75
        ? 'The broader trend remains constructive and well supported.'
        : 'The broader trend is constructive but not fully confirmed.';
    case 'volume':
      return score !== null && score >= 75
        ? 'Volume behavior remains supportive, with buying activity generally confirming recent advances.'
        : 'Volume confirmation is mixed and should be watched.';
    case 'institutional':
      return score !== null && score >= 75
        ? 'Institutional positioning and liquidity remain supportive.'
        : 'Institutional participation is not providing a strong tailwind.';
    case 'volatility':
      return score !== null && score >= 75
        ? 'Volatility remains contained and is not currently disrupting the broader trend.'
        : 'Volatility is elevated enough to reduce confidence.';
    case 'sectorStrength':
      return score !== null && score >= 75
        ? 'Sector leadership is supportive across the strongest areas of the market.'
        : 'Leadership is positive but concentrated, with fewer sectors showing strong relative strength.';
    default:
      return `This component is ${status}.`;
  }
}

function normalizeScore(value: number | null | undefined) {
  return value === null || value === undefined || !Number.isFinite(value)
    ? null
    : Math.max(0, Math.min(100, value));
}

function normalizeContributionTarget(
  compositeScore: number | null | undefined,
  contributions: { rawContribution: number }[],
) {
  if (compositeScore !== null && compositeScore !== undefined && Number.isFinite(compositeScore)) {
    return Math.round(compositeScore);
  }
  return Math.round(contributions.reduce((sum, component) => sum + component.rawContribution, 0));
}

function getHealthTrendRangeDays(range: HealthTrendRange) {
  switch (range) {
    case '1W':
      return 7;
    case '3M':
      return 93;
    case '1M':
    default:
      return 31;
  }
}

function buildSupportDriver(component: HealthComponentViewModel) {
  switch (component.key) {
    case 'breadth':
      return 'Breadth remains broad';
    case 'institutional':
      return 'Institutional conditions are supportive';
    case 'volatility':
      return 'Volatility is contained';
    case 'momentum':
      return 'Momentum remains positive';
    case 'sectorStrength':
      return 'Sector leadership is supportive';
    case 'volume':
      return 'Volume confirms recent advances';
    case 'trend':
      return 'Trend structure remains constructive';
    default:
      return `${component.label} is supportive`;
  }
}

function buildMonitorDriver(component: HealthComponentViewModel) {
  switch (component.key) {
    case 'sectorStrength':
      return component.score !== null && component.score >= 75
        ? 'Sector leadership remains concentrated'
        : 'Sector leadership remains relatively narrow';
    case 'trend':
      return component.score !== null && component.score >= 75
        ? 'Trend confirmation remains worth monitoring'
        : 'Trend confirmation remains incomplete';
    case 'volume':
      return 'Volume confirmation remains mixed';
    case 'breadth':
      return component.score !== null && component.score >= 75
        ? 'Breadth participation should keep confirming'
        : 'Breadth participation remains mixed';
    case 'volatility':
      return 'Volatility could reduce confidence if it rises';
    case 'momentum':
      return 'Momentum needs continued index confirmation';
    case 'institutional':
      return 'Institutional support needs continued confirmation';
    default:
      return `${component.label} needs monitoring`;
  }
}

function formatDriverPhrase(drivers: HealthDriver[], mode: 'support' | 'monitor') {
  const labels = drivers
    .map((driver) => driver.component ? driverPhraseForComponent(driver.component, mode) : driver.label.toLowerCase())
    .filter(Boolean);
  const unique = Array.from(new Set(labels));
  if (!unique.length) {
    return null;
  }
  if (unique.length === 1) {
    return unique[0];
  }
  if (unique.length === 2) {
    return `${unique[0]} and ${unique[1]}`;
  }
  return `${unique.slice(0, -1).join(', ')}, and ${unique.at(-1)}`;
}

function driverPhraseForComponent(component: HealthComponentKey, mode: 'support' | 'monitor') {
  if (mode === 'support') {
    switch (component) {
      case 'breadth':
        return 'broad participation';
      case 'momentum':
        return 'positive momentum';
      case 'institutional':
        return 'supportive institutional conditions';
      case 'trend':
        return 'constructive trend structure';
      case 'volume':
        return 'supportive volume behavior';
      case 'volatility':
        return 'contained volatility';
      case 'sectorStrength':
        return 'sector leadership';
      default:
        return null;
    }
  }
  switch (component) {
    case 'sectorStrength':
      return 'sector concentration';
    case 'trend':
      return 'incomplete trend confirmation';
    case 'volume':
      return 'mixed volume confirmation';
    case 'breadth':
      return 'uneven participation';
    case 'volatility':
      return 'volatility risk';
    case 'momentum':
      return 'momentum confirmation';
    case 'institutional':
      return 'institutional confirmation';
    default:
      return null;
  }
}

function rewriteDriverLabel(label: string) {
  return label
    .replace(/50EMA/g, '50-day average')
    .replace(/sector leadership remains strong/i, 'Sector leadership remains strong')
    .replace(/institutional activity is supportive/i, 'Institutional activity is supportive');
}

function isNoWeakeningLabel(label: string) {
  const normalized = label.toLowerCase();
  return normalized.includes('no major') || normalized.includes('no dominant') || normalized.includes('none');
}
