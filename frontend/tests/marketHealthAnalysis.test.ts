import {
  buildDecisionLayerSummary,
  buildHealthComponents,
  buildHealthContributions,
  buildHealthOverviewSummary,
  buildHealthRadarData,
  calculateHealthChartTicks,
  calculateHealthTrendSummary,
  calculateRadarGridPoints,
  calculateRadarPoints,
  clampHealthScoreForDisplay,
  filterHealthHistoryByRange,
  calculateScoreContributions,
  classifyHealthDirection,
  classifyHealthScore,
  deriveHealthDrivers,
  formatHealthDirection,
  formatHealthScore,
  getHealthHistoryBadgeLabel,
  getHealthSourceBadgeLabel,
  getContributionTotal,
  getSupportedHealthTrendRanges,
  normalizeHealthHistory,
  validateHealthComponentScore,
  reconcileRoundedContributions,
} from '../src/features/market/healthAnalysis';
import type { MarketHealthResponse } from '../src/types/market';

function assert(condition: unknown, message: string) {
  if (!condition) {
    throw new Error(message);
  }
}

function marketHealth(overrides: Partial<MarketHealthResponse> = {}): MarketHealthResponse {
  return {
    component_explanations: {
      breadth: 'Breadth remains mixed.',
      institutional: 'Institutional activity is supportive.',
      momentum: 'Indexes are above key averages.',
      sector_strength: 'Sector leadership remains strong.',
      trend: 'Trend is constructive.',
      volatility: 'Volatility is normal.',
      volume: 'Volume quality is strong.',
    },
    components: {
      breadth: 58,
      institutional: 84,
      momentum: 90,
      sector_strength: 91,
      trend: 88,
      volatility: 76,
      volume: 82,
    },
    improving_factors: ['Sector leadership remains strong'],
    overall_score: 81,
    status: 'Healthy',
    summary: 'Market health remains healthy.',
    weakening_factors: ['Breadth remains mixed'],
    ...overrides,
  };
}

function run() {
  assert(classifyHealthScore(92).label === 'Excellent', 'excellent score maps correctly');
  assert(classifyHealthScore(78).tone === 'strong', 'strong score tone maps correctly');
  assert(classifyHealthScore(62).label === 'Constructive', 'constructive score maps correctly');
  assert(classifyHealthScore(45).tone === 'mixed', 'mixed score tone maps correctly');
  assert(classifyHealthScore(25).label === 'Weak', 'weak score maps correctly');
  assert(formatHealthScore(null) === 'N/A', 'null score formats safely');
  assert(formatHealthScore(81.4) === '81', 'score rounds for display');

  assert(classifyHealthDirection([]) === 'unavailable', 'missing trend history is unavailable');
  assert(classifyHealthDirection([{ label: 'A', score: 70 }, { label: 'B', score: 76 }]) === 'improving', 'positive score change improves');
  assert(classifyHealthDirection([{ label: 'A', score: 76 }, { label: 'B', score: 70 }]) === 'weakening', 'negative score change weakens');
  assert(formatHealthDirection('stable') === 'Stable', 'direction label formats');

  const health = marketHealth();
  const components = buildHealthComponents(health);
  assert(components.length === 7, 'builds all health components');
  assert(components.some((component) => component.key === 'sectorStrength'), 'maps sector_strength to sectorStrength view key');
  assert(components.map((component) => component.key).join(',') === 'momentum,breadth,trend,volume,institutional,volatility,sectorStrength', 'component ordering is stable');

  const radarData = buildHealthRadarData(health);
  assert(radarData.length === 7, 'radar data includes every component');
  assert(radarData[4]?.label === 'Institutional', 'radar uses consistent label');
  assert(validateHealthComponentScore(undefined) === null, 'undefined score validates to null');
  assert(validateHealthComponentScore(Number.NaN) === null, 'NaN score validates to null');
  assert(clampHealthScoreForDisplay(120) === 100, 'display score clamps above 100');
  assert(clampHealthScoreForDisplay(-20) === 0, 'display score clamps below 0');
  assert(validateHealthComponentScore(120) === 120, 'raw score is not clamped during validation');
  const partialRadar = buildHealthRadarData(marketHealth({ components: { ...health.components, breadth: Number.NaN } }));
  assert(partialRadar.find((item) => item.key === 'breadth')?.score === null, 'missing radar score is not converted to zero');
  const radarPoints = calculateRadarPoints(radarData, 100, 100, 70);
  assert(radarPoints.length === 7, 'radar points calculate for full data');
  assert(radarPoints.every((point) => Number.isFinite(point.x) && Number.isFinite(point.y)), 'radar chart coordinates are finite');
  assert(calculateRadarPoints(partialRadar, 100, 100, 70).length === 6, 'radar points handle partial input');
  assert(calculateRadarGridPoints(7, 100, 100, 70, 75).every((point) => Number.isFinite(point.x) && Number.isFinite(point.y)), 'radar grid coordinates are finite');

  const drivers = deriveHealthDrivers(components, health);
  assert(drivers.supporting.some((driver) => driver.label.includes('Sector leadership')), 'supporting drivers include leadership');
  assert(drivers.monitor.some((driver) => driver.label.includes('Trend') || driver.label.includes('Sector')), 'monitor drivers include incomplete areas');
  assert(!drivers.monitor.some((driver) => driver.label.toLowerCase().includes('narrowing participation')), 'strong breadth does not produce narrowing participation');

  const contributions = calculateScoreContributions(components);
  assert(contributions[0]?.contribution !== null, 'contributions calculate');
  assert(getContributionTotal(contributions) === 80, 'contributions match weighted component formula');
  const displayContributions = buildHealthContributions(components, health.overall_score);
  assert(displayContributions.every((component) => Number.isFinite(component.rawContribution)), 'full precision contributions remain finite');
  assert(displayContributions.reduce((sum, component) => sum + component.displayedPoints, 0) === 81, 'displayed contribution points reconcile to composite score');
  assert(reconcileRoundedContributions([1.2, 1.2, 1.2], 4).reduce((sum, value) => sum + value, 0) === 4, 'rounding deficit reconciles');
  assert(reconcileRoundedContributions([1.9, 1.9, 1.9], 5).reduce((sum, value) => sum + value, 0) === 5, 'rounding surplus reconciles');
  assert(reconcileRoundedContributions([0, Number.NaN, 2.4], 2).reduce((sum, value) => sum + value, 0) === 2, 'missing and zero contribution handling is safe');

  const overview = buildHealthOverviewSummary(components, health);
  assert(overview.includes('supported by'), 'overview describes strongest support');
  assert(!overview.includes('supported by breadth remains'), 'overview grammar is natural');
  assert(getHealthHistoryBadgeLabel('unavailable') === 'Trend history unavailable', 'history badge identifies the missing dependency');
  assert(getHealthSourceBadgeLabel('mock') === 'Mock data', 'mock source badge is explicit');
  assert(getHealthSourceBadgeLabel(undefined) === null, 'missing source badge is hidden');

  const decision = buildDecisionLayerSummary(
    { contributors: [], disagreements: [], score: 72, status: 'High Confidence', summary: 'Agreement is strong.' },
    components,
    health,
  );
  assert(decision.stance === 'High Confidence', 'decision layer uses confidence status');
  assert(decision.implication.includes('Market conditions'), 'decision layer implication is market-environment language');
  assert(!decision.implication.includes('supporting measured decision-making'), 'decision layer avoids vague decision wording');
  assert(!decision.monitor.toLowerCase().includes('narrowing participation'), 'decision monitor does not contradict strong breadth');

  const unavailableDecision = buildDecisionLayerSummary(null, components, health);
  assert(unavailableDecision.stance === 'Healthy', 'decision fallback uses health status');

  const history = [
    { timestamp: '2026-07-10T00:00:00Z', score: 78, source: 'cached' as const },
    { timestamp: 'invalid', score: 80, source: 'cached' as const },
    { timestamp: '2026-06-20T00:00:00Z', score: 70, source: 'cached' as const },
    { timestamp: '2026-07-10T00:00:00Z', score: 82, source: 'cached' as const },
    { timestamp: '2026-05-01T00:00:00Z', score: 60, source: 'cached' as const },
    { timestamp: '2026-04-01T00:00:00Z', score: Number.NaN, source: 'cached' as const },
  ];
  const normalized = normalizeHealthHistory(history);
  assert(normalized.length === 3, 'history omits invalid rows and dedupes timestamps');
  assert(normalized[0]?.timestamp === '2026-05-01T00:00:00.000Z', 'history sorts chronologically');
  assert(normalized.at(-1)?.score === 82, 'duplicate timestamp keeps latest value');
  assert(filterHealthHistoryByRange(history, '1W').length === 1, '1W filtering works');
  assert(filterHealthHistoryByRange(history, '1M').length === 2, '1M filtering works');
  assert(filterHealthHistoryByRange(history, '3M').length === 3, '3M filtering works');
  assert(getSupportedHealthTrendRanges(history).join(',') === '1M,3M', 'supported ranges require at least two points');
  const summary = calculateHealthTrendSummary(history, '1M');
  assert(summary.startScore === 70 && summary.endScore === 82, 'trend summary start and end scores are correct');
  assert(summary.change === 12 && summary.direction === 'improving', 'trend summary classifies improving');
  assert(calculateHealthTrendSummary([], '1M').direction === 'unavailable', 'missing history does not fabricate direction');
  assert(calculateHealthTrendSummary([{ timestamp: '2026-07-10T00:00:00Z', score: 70 }], '1M').change === null, 'single-point history omits change');
  assert(calculateHealthChartTicks().every((tick) => tick >= 0 && tick <= 100), 'health chart ticks stay within score bounds');
}

run();
