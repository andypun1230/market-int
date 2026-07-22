import type { DailyReport } from '@/types/market';

export type BriefingChange = {
  current: string;
  direction: string;
  label: string;
  previous: string;
  reason: string | null;
};

export type BriefingScenario = {
  conditions: string;
  expectation: string;
  invalidation: string;
  name: string;
  probability: string | null;
  response: string;
};

export type BriefingWatchItem = {
  category: string;
  detail: string;
  symbol: string;
};

export type DailyBriefingViewModel = {
  appendix: {
    notes: string[];
    sourceState: string;
  };
  changes: {
    available: boolean;
    items: BriefingChange[];
    summary: string;
  };
  checklist: { label: string; status: string; value: string | null }[];
  confidence: { label: string; reason: string | null; score: number | null };
  crossMarket: string[];
  drivers: string[];
  highestConviction: string;
  leadership: {
    current: string[];
    emerging: string[];
    monitor: string[];
    weakening: string[];
  };
  majorRisk: string;
  narrative: string;
  primaryTheme: string;
  regime: string;
  risks: {
    confirmations: string[];
    invalidation: string[];
    warnings: string[];
  };
  scenarios: BriefingScenario[];
  tomorrow: string[];
  watchlist: BriefingWatchItem[];
};

export function buildDailyBriefing(report: DailyReport): DailyBriefingViewModel {
  const narrative = asRecord(report.report_narrative);
  const confidence = asRecord(report.recommendation_confidence);
  const changes = asRecord(report.report_changes);
  const checklist = asRecord(report.decision_checklist);
  const conviction = asRecord(report.market_conviction);
  const playbook = report.decision_dashboard?.playbook;
  const relationships = stringArray(narrative.relationships).length
    ? stringArray(narrative.relationships)
    : stringArray(report.signal_relationships);
  const themes = getThemeRows(report);
  const sectors = getSectorRows(report);
  const invalidation = stringArray(narrative.invalidation);

  return {
    appendix: {
      notes: uniqueStrings([
        ...stringArray(report.theme_report?.warnings),
        ...stringArray(asRecord(report.market_health?.data_quality).warnings),
        ...dependencyNotes(report),
      ]),
      sourceState: getSourceState(report),
    },
    changes: {
      available: changes.available === true,
      items: recordArray(changes.items).map((item) => ({
        current: displayValue(item.current),
        direction: text(item.direction) ?? 'changed',
        label: text(item.label) ?? 'Market signal',
        previous: displayValue(item.previous),
        reason: text(item.reason),
      })),
      summary: changes.available === true
        ? text(changes.summary) ?? 'No meaningful changes since the previous report.'
        : 'Baseline report established.',
    },
    checklist: recordArray(checklist.items).map((item) => ({
      label: text(item.label) ?? 'Market condition',
      status: text(item.status) ?? 'Watch',
      value: item.value === null || item.value === undefined ? null : displayValue(item.value),
    })),
    confidence: {
      label: text(confidence.rating) ?? confidenceLabel(number(confidence.score)),
      reason: text(confidence.reason),
      score: number(confidence.score),
    },
    crossMarket: uniqueStrings([
      ...relationships,
      text(narrative.crossTabNarrative),
    ]),
    drivers: buildPrimaryDrivers(conviction, narrative, report.key_drivers),
    highestConviction: text(narrative.primaryOpportunity)
      ?? playbook?.preferred_strategy
      ?? report.sector_leaders?.[0]
      ?? 'No highest-conviction opportunity is available.',
    leadership: {
      current: leadershipNames(sectors, ['leading', 'strong', 'leader']).slice(0, 4),
      emerging: uniqueStrings([
        ...leadershipNames(sectors, ['improving', 'emerging']),
        ...leadershipNames(themes, ['improving', 'emerging']),
      ]).slice(0, 4),
      monitor: uniqueStrings([
        ...stringArray(report.sector_leaders),
        ...themes.slice(0, 2).map((item) => text(item.display_name) ?? text(item.name)),
      ]).slice(0, 4),
      weakening: leadershipNames(sectors, ['weakening', 'lagging', 'at risk']).slice(0, 4),
    },
    majorRisk: text(narrative.primaryRisk)
      ?? playbook?.main_risk
      ?? report.main_risks?.[0]
      ?? 'No major risk is available.',
    narrative: text(narrative.marketNarrative)
      ?? text(narrative.thesis)
      ?? report.executive_summary
      ?? 'A connected market narrative is unavailable for this report.',
    primaryTheme: topTheme(themes)
      ?? report.sector_leaders?.[0]
      ?? 'No qualified theme',
    regime: report.market_regime || report.market_health?.status || 'Unavailable',
    risks: {
      confirmations: meaningfulSignals(report.hidden_confirmations, 'No significant').slice(0, 4),
      invalidation: invalidation.length ? invalidation.slice(0, 4) : stringArray(report.main_risks).slice(0, 4),
      warnings: meaningfulSignals(report.hidden_warnings, 'No significant').length
        ? meaningfulSignals(report.hidden_warnings, 'No significant').slice(0, 4)
        : stringArray(report.main_risks).slice(0, 4),
    },
    scenarios: buildScenarios(report),
    tomorrow: uniqueStrings([
      ...stringArray(report.tomorrow_watch),
      ...recordArray(report.economic_calendar).map((item) => text(item.event) ?? text(item.title) ?? text(item.name)),
      ...invalidation,
    ]).slice(0, 8),
    watchlist: buildWatchlistBrief(report),
  };
}

function buildScenarios(report: DailyReport): BriefingScenario[] {
  return recordArray(report.scenario_plan).map((item) => ({
    conditions: text(item.conditions) ?? 'Conditions are unavailable.',
    expectation: text(item.expectedBehaviour) ?? text(item.expectation) ?? 'Market expectation is unavailable.',
    invalidation: text(item.changesProbability) ?? text(item.invalidation) ?? 'Invalidation is unavailable.',
    name: text(item.name) ?? 'Scenario',
    probability: typeof item.probability === 'number' ? `${Math.round(item.probability)}%` : text(item.probabilityBand),
    response: text(item.suggestedResponse) ?? 'Suggested response is unavailable.',
  }));
}

function buildPrimaryDrivers(conviction: Record<string, unknown>, narrative: Record<string, unknown>, fallback: string[]) {
  const contributors = recordArray(conviction.contributors)
    .filter((item) => number(item.score) !== null)
    .sort((left, right) => (number(right.score) ?? 0) - (number(left.score) ?? 0))
    .slice(0, 3)
    .map((item) => `${text(item.label) ?? 'Signal'} ${Math.round(number(item.score) ?? 0)}/100.`);
  return uniqueStrings([
    ...contributors,
    ...stringArray(narrative.hiddenConfirmations),
    ...fallback,
  ]).slice(0, 4);
}

function buildWatchlistBrief(report: DailyReport): BriefingWatchItem[] {
  const items = recordArray(asRecord(report.watchlist_summary).items);
  if (!items.length) {
    return recordArray(report.stock_charts).slice(0, 4).map((item) => ({
      category: 'Market Idea',
      detail: text(item.summary) ?? text(item.setup) ?? 'Highest-conviction market setup.',
      symbol: text(item.symbol) ?? text(item.ticker) ?? 'N/A',
    }));
  }

  const scored = [...items].sort((left, right) => (number(right.score) ?? -Infinity) - (number(left.score) ?? -Infinity));
  const improved = [...items].sort((left, right) => (number(right.change_percent) ?? -Infinity) - (number(left.change_percent) ?? -Infinity));
  const review = [...items].sort((left, right) => (number(left.score) ?? Infinity) - (number(right.score) ?? Infinity));
  const explicitRisk = items.find((item) => {
    const value = `${text(item.risk_flag) ?? ''} ${text(item.rating) ?? ''}`.toLowerCase();
    return /risk|weak|avoid|sell|below/.test(value);
  });
  const candidates: [string, Record<string, unknown> | undefined][] = [
    ['Highest Opportunity', scored[0]],
    ['Most Improved', improved.find((item) => (number(item.change_percent) ?? 0) > 0)],
    ['Needs Review', review[0]],
    ['Highest Risk', explicitRisk],
  ];
  const used = new Set<string>();
  return candidates.flatMap(([category, item]) => {
    if (!item) return [];
    const symbol = text(item.symbol) ?? text(item.ticker) ?? 'N/A';
    if (used.has(`${category}-${symbol}`)) return [];
    used.add(`${category}-${symbol}`);
    const change = number(item.change_percent);
    const context = text(item.main_setup) ?? text(item.rating) ?? text(item.risk_flag);
    return [{
      category,
      detail: [context, change === null ? null : `${change >= 0 ? '+' : ''}${change.toFixed(1)}% today`].filter(Boolean).join(' · ') || 'No additional setup detail is available.',
      symbol,
    }];
  });
}

function getSectorRows(report: DailyReport) {
  const dashboardRows = recordArray(asRecord(report.sector_dashboard).sectors);
  if (dashboardRows.length) return dashboardRows;
  return (report.sector_etfs?.items ?? []).map((item) => item as unknown as Record<string, unknown>);
}

function getThemeRows(report: DailyReport) {
  const reportRows = recordArray(report.theme_report?.leadership);
  if (reportRows.length) return reportRows;
  return (report.theme_intelligence?.leaders ?? []).map((item) => item as unknown as Record<string, unknown>);
}

function leadershipNames(items: Record<string, unknown>[], matches: string[]) {
  return uniqueStrings(items.flatMap((item) => {
    const metadata = asRecord(item.metadata);
    const classification = `${text(item.classification) ?? ''} ${text(item.status) ?? ''} ${text(metadata.status) ?? ''}`.toLowerCase();
    if (!matches.some((match) => classification.includes(match))) return [];
    return [text(item.display_name) ?? text(item.name) ?? text(item.sector)];
  }));
}

function topTheme(items: Record<string, unknown>[]) {
  const first = items[0];
  return first ? text(first.display_name) ?? text(first.name) ?? text(first.theme_id) : null;
}

function dependencyNotes(report: DailyReport) {
  const quality = asRecord(report.market_health?.data_quality);
  return uniqueStrings([
    ...stringArray(quality.missing_dependencies),
    ...stringArray(quality.warnings),
  ]).map((item) => `Data note: ${item}`);
}

function getSourceState(report: DailyReport) {
  const quality = asRecord(report.market_health?.data_quality);
  return text(quality.overall_mode) ?? 'Unavailable';
}

function meaningfulSignals(value: unknown, ignoredPrefix: string) {
  return stringArray(value).filter((item) => !item.startsWith(ignoredPrefix));
}

function confidenceLabel(value: number | null) {
  if (value === null) return 'Unavailable';
  if (value >= 80) return 'High';
  if (value >= 60) return 'Moderate';
  return 'Low';
}

function displayValue(value: unknown) {
  if (typeof value === 'number') return Number.isInteger(value) ? String(value) : value.toFixed(1);
  return text(value) ?? 'N/A';
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function recordArray(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value) ? value.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === 'object' && !Array.isArray(item)) : [];
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string' && Boolean(item.trim())) : [];
}

function uniqueStrings(values: (string | null | undefined)[]) {
  return [...new Set(values.filter((item): item is string => typeof item === 'string' && Boolean(item.trim())))];
}

function text(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value.trim() : null;
}

function number(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}
