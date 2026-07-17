import type { EconomicIndicatorSnapshot, MacroEvent } from '@/features/market/macroAnalysis';

export type MacroMockScenarioId =
  | 'soft_landing'
  | 'inflation_reacceleration'
  | 'growth_slowdown'
  | 'labor_weakness'
  | 'fed_easing'
  | 'restrictive_hold'
  | 'mixed_economy'
  | 'partial_data'
  | 'no_events'
  | 'post_release';

export type MacroMockScenario = {
  asOfDate: string;
  description: string;
  economicIndicators: EconomicIndicatorSnapshot[];
  id: MacroMockScenarioId;
  label: string;
  macroEvents: MacroEvent[];
  source: 'test';
};

export const MACRO_TEST_ANCHOR_DATE = '2026-07-16T12:00:00-04:00';
const SOURCE_TIMEZONE = 'America/New_York';

export const MACRO_MOCK_SCENARIO_OPTIONS: { id: MacroMockScenarioId; label: string }[] = [
  { id: 'soft_landing', label: 'Soft Landing' },
  { id: 'inflation_reacceleration', label: 'Inflation Reacceleration' },
  { id: 'growth_slowdown', label: 'Growth Slowdown' },
  { id: 'labor_weakness', label: 'Labor Weakness' },
  { id: 'fed_easing', label: 'Fed Easing' },
  { id: 'restrictive_hold', label: 'Restrictive Hold' },
  { id: 'mixed_economy', label: 'Mixed Economy' },
  { id: 'partial_data', label: 'Partial Data' },
  { id: 'no_events', label: 'No Events' },
  { id: 'post_release', label: 'Post Release' },
];

export function buildMacroMockScenario(id: MacroMockScenarioId): MacroMockScenario {
  const indicators = scenarioIndicators(id);
  return {
    asOfDate: MACRO_TEST_ANCHOR_DATE,
    description: scenarioDescription(id),
    economicIndicators: indicators,
    id,
    label: MACRO_MOCK_SCENARIO_OPTIONS.find((item) => item.id === id)?.label ?? 'Macro Test Scenario',
    macroEvents: id === 'no_events'
      ? []
      : id === 'post_release'
        ? postReleaseEvents()
        : upcomingEvents(),
    source: 'test',
  };
}

export function validateMacroMockScenario(scenario: MacroMockScenario) {
  const asOf = Date.parse(scenario.asOfDate);
  const indicatorsValid = scenario.economicIndicators.every((indicator) => Date.parse(indicator.releaseDate) <= asOf);
  const eventsValid = scenario.macroEvents.every((event) => {
    const time = Date.parse(event.date);
    if (event.status === 'Released' || event.status === 'Revised') {
      return time <= asOf;
    }
    return time > asOf;
  });
  return {
    eventsValid,
    indicatorsValid,
    valid: indicatorsValid && eventsValid,
  };
}

function scenarioIndicators(id: MacroMockScenarioId): EconomicIndicatorSnapshot[] {
  switch (id) {
    case 'inflation_reacceleration':
      return baseIndicators({
        cpiYoY: [3.4, 3.0],
        coreCpiYoY: [3.5, 3.2],
        fedFunds: [4.5, 4.5],
        gdp: [2.7, 2.2],
        payrolls: [225, 190],
        ppiYoY: [3.8, 2.9],
        tenYear: [4.65, 4.25],
        thirtyYear: [4.92, 4.55],
        unemployment: [3.9, 4.0],
      });
    case 'growth_slowdown':
      return baseIndicators({
        cpiYoY: [2.3, 2.6],
        coreCpiYoY: [2.7, 2.9],
        fedFunds: [4.25, 4.25],
        gdp: [0.8, 1.9],
        payrolls: [95, 170],
        retailSales: [-0.6, 0.2],
        tenYear: [3.72, 4.08],
        thirtyYear: [4.18, 4.5],
        unemployment: [4.5, 4.2],
      });
    case 'labor_weakness':
      return baseIndicators({
        averageHourlyEarnings: [0.1, 0.3],
        cpiYoY: [2.4, 2.6],
        coreCpiYoY: [2.8, 2.9],
        fedFunds: [4.25, 4.25],
        gdp: [1.2, 1.7],
        payrolls: [45, 155],
        tenYear: [3.9, 4.1],
        unemployment: [4.8, 4.4],
      });
    case 'fed_easing':
      return baseIndicators({
        cpiYoY: [2.4, 2.6],
        coreCpiYoY: [2.7, 2.9],
        fedFunds: [3.75, 4.0],
        gdp: [1.6, 1.8],
        payrolls: [135, 160],
        tenYear: [3.65, 3.95],
        thirtyYear: [4.1, 4.32],
        unemployment: [4.3, 4.2],
      });
    case 'restrictive_hold':
      return baseIndicators({
        cpiYoY: [3.0, 3.0],
        coreCpiYoY: [3.3, 3.4],
        fedFunds: [4.75, 4.75],
        gdp: [2.0, 1.9],
        payrolls: [175, 180],
        ppiYoY: [2.8, 2.7],
        unemployment: [4.0, 4.0],
      });
    case 'mixed_economy':
      return baseIndicators({
        cpiYoY: [2.6, 2.9],
        coreCpiYoY: [3.0, 3.1],
        fedFunds: [4.5, 4.5],
        gdp: [1.9, 1.8],
        payrolls: [230, 165],
        ppiYoY: [3.0, 2.5],
        retailSales: [0.1, 0.4],
        tenYear: [4.4, 4.12],
        unemployment: [4.2, 4.0],
      });
    case 'partial_data':
      return baseIndicators({
        cpiYoY: [2.6, 2.8],
        fedFunds: [4.25, 4.25],
        tenYear: [4.05, 4.18],
        unemployment: [4.1, 4.1],
      }, ['fedFunds', 'tenYear', 'cpiYoY', 'unemployment']);
    case 'no_events':
    case 'post_release':
    case 'soft_landing':
    default:
      return baseIndicators({
        averageHourlyEarnings: [0.3, 0.3],
        coreCpiYoY: [2.9, 3.1],
        corePceYoY: [2.7, 2.8],
        cpiMom: [0.2, 0.3],
        cpiYoY: [2.6, 2.8],
        fedFunds: [4.25, 4.25],
        gdp: [2.2, 1.8],
        payrolls: [185, 172],
        ppiYoY: [2.3, 2.5],
        retailSales: [0.3, 0.2],
        tenYear: [4.05, 4.18],
        thirtyYear: [4.55, 4.63],
        unemployment: [4.1, 4.1],
      });
  }
}

function baseIndicators(
  values: Partial<Record<IndicatorKey, [number, number]>>,
  includeKeys?: IndicatorKey[],
): EconomicIndicatorSnapshot[] {
  const definitions: Record<IndicatorKey, Omit<EconomicIndicatorSnapshot, 'latest' | 'prior'>> = {
    averageHourlyEarnings: indicator('average_hourly_earnings_mom', 'Avg Hourly Earnings', 'percent', 'month_over_month', '2026-07-03T08:30:00-04:00'),
    coreCpiMom: indicator('core_cpi_mom', 'Core CPI', 'percent', 'month_over_month', '2026-07-15T08:30:00-04:00'),
    coreCpiYoY: indicator('core_cpi_yoy', 'Core CPI', 'percent', 'year_over_year', '2026-07-15T08:30:00-04:00'),
    corePceYoY: indicator('core_pce_yoy', 'Core PCE', 'percent', 'year_over_year', '2026-06-27T08:30:00-04:00'),
    cpiMom: indicator('cpi_mom', 'CPI', 'percent', 'month_over_month', '2026-07-15T08:30:00-04:00'),
    cpiYoY: indicator('cpi_yoy', 'CPI', 'percent', 'year_over_year', '2026-07-15T08:30:00-04:00'),
    fedFunds: indicator('fed_funds', 'Fed Funds', 'percent', 'level', '2026-06-17T14:00:00-04:00'),
    gdp: indicator('gdp_qoq', 'GDP', 'annualized_percent', 'quarter_over_quarter_annualized', '2026-06-26T08:30:00-04:00'),
    payrolls: indicator('nonfarm_payrolls', 'Payrolls', 'thousands', 'level', '2026-07-03T08:30:00-04:00'),
    ppiMom: indicator('ppi_mom', 'PPI', 'percent', 'month_over_month', '2026-07-16T08:30:00-04:00'),
    ppiYoY: indicator('ppi_yoy', 'PPI', 'percent', 'year_over_year', '2026-07-16T08:30:00-04:00'),
    retailSales: indicator('retail_sales_mom', 'Retail Sales', 'percent', 'month_over_month', '2026-07-15T08:30:00-04:00'),
    tenYear: indicator('ten_year_yield', '10Y Yield', 'percent', 'level', '2026-07-15T16:00:00-04:00'),
    thirtyYear: indicator('thirty_year_yield', '30Y Yield', 'percent', 'level', '2026-07-15T16:00:00-04:00'),
    unemployment: indicator('unemployment_rate', 'Unemployment', 'percent', 'level', '2026-07-03T08:30:00-04:00'),
  };
  const consensusByKey: Partial<Record<IndicatorKey, number>> = {
    averageHourlyEarnings: 0.3,
    coreCpiMom: 0.3,
    coreCpiYoY: 3.2,
    corePceYoY: 2.7,
    cpiMom: 0.2,
    cpiYoY: 3.1,
    gdp: 1.8,
    payrolls: 165,
    ppiMom: 0.2,
    ppiYoY: 2.7,
    retailSales: 0.2,
    unemployment: 4.1,
  };
  const keys = includeKeys ?? Object.keys(values) as IndicatorKey[];
  return keys
    .map((key): EconomicIndicatorSnapshot | null => {
      const pair = values[key];
      const definition = definitions[key];
      const consensus = key === 'fedFunds'
        ? pair?.[0] ?? null
        : key === 'tenYear' || key === 'thirtyYear'
          ? null
          : consensusByKey[key] ?? null;
      const revised_prior_from = key === 'ppiYoY' && pair ? pair[1] - 0.1 : null;
      return pair && definition
        ? { ...definition, consensus, latest: pair[0], prior: pair[1], revised_prior_from }
        : null;
    })
    .filter((item): item is EconomicIndicatorSnapshot => item !== null);
}

type IndicatorKey =
  | 'averageHourlyEarnings'
  | 'coreCpiMom'
  | 'coreCpiYoY'
  | 'corePceYoY'
  | 'cpiMom'
  | 'cpiYoY'
  | 'fedFunds'
  | 'gdp'
  | 'payrolls'
  | 'ppiMom'
  | 'ppiYoY'
  | 'retailSales'
  | 'tenYear'
  | 'thirtyYear'
  | 'unemployment';

function indicator(
  key: string,
  label: string,
  unit: EconomicIndicatorSnapshot['unit'],
  periodType: EconomicIndicatorSnapshot['periodType'],
  releaseDate: string,
): Omit<EconomicIndicatorSnapshot, 'latest' | 'prior'> {
  return {
    freshness: 'test',
    key,
    label,
    periodType,
    releaseDate,
    source: 'test',
    unit,
  };
}

function upcomingEvents(): MacroEvent[] {
  return [
    event('2026-07-22T08:30:00-04:00', 'CPI', 'Inflation', 'High Impact', '2.8%', '2.6%'),
    event('2026-07-22T08:30:00-04:00', 'Core CPI', 'Inflation', 'High Impact', '3.1%', '2.9%'),
    event('2026-07-23T08:30:00-04:00', 'PPI', 'Inflation', 'High Impact', '2.5%', '2.4%'),
    event('2026-07-28T08:30:00-04:00', 'Retail Sales', 'Growth', 'Medium Impact', '0.2%', '0.3%'),
    event('2026-07-29T14:00:00-04:00', 'FOMC Rate Decision', 'Rates', 'High Impact', '4.25%', '4.25%'),
    event('2026-08-07T08:30:00-04:00', 'Nonfarm Payrolls', 'Labor', 'High Impact', '+172K', '+180K'),
    event('2026-08-07T08:30:00-04:00', 'Unemployment Rate', 'Labor', 'High Impact', '4.1%', '4.1%'),
  ];
}

function postReleaseEvents(): MacroEvent[] {
  return [
    event('2026-07-15T08:30:00-04:00', 'CPI', 'Inflation', 'High Impact', '2.8%', '2.6%', '2.5%', 'Below expectations'),
    event('2026-07-15T08:30:00-04:00', 'Core CPI', 'Inflation', 'High Impact', '3.1%', '2.9%', '2.9%', 'In line'),
    event('2026-07-16T08:30:00-04:00', 'PPI', 'Inflation', 'High Impact', '2.5%', '2.4%', '2.9%', 'Above expectations'),
    event('2026-07-03T08:30:00-04:00', 'Nonfarm Payrolls', 'Labor', 'High Impact', '+172K', '+180K', '+225K', 'Above expectations'),
    event('2026-07-03T08:30:00-04:00', 'Unemployment Rate', 'Labor', 'High Impact', '4.1%', '4.1%', '4.0%', 'Below expectations'),
  ].map((item) => ({ ...item, status: 'Released' }));
}

function event(
  date: string,
  title: string,
  category: string,
  importance: MacroEvent['importance'],
  previous: string,
  consensus?: string,
  actual?: string,
  surprise?: string,
): MacroEvent {
  return {
    actual,
    category,
    consensus,
    date,
    event: title,
    importance,
    previous,
    source: 'test',
    sourceTimezone: SOURCE_TIMEZONE,
    status: actual ? 'Released' : 'Upcoming',
    surprise,
  };
}

function scenarioDescription(id: MacroMockScenarioId) {
  switch (id) {
    case 'inflation_reacceleration':
      return 'Inflation and yields reaccelerate while growth remains firm.';
    case 'growth_slowdown':
      return 'Growth and labor soften while yields fall.';
    case 'labor_weakness':
      return 'Employment data deteriorates with cooling wage pressure.';
    case 'fed_easing':
      return 'Policy rates and yields fall as inflation cools.';
    case 'restrictive_hold':
      return 'The Fed holds restrictive policy while inflation remains sticky.';
    case 'mixed_economy':
      return 'Inflation, rates, labor, and growth signals conflict.';
    case 'partial_data':
      return 'Only a small subset of economic indicators is available.';
    case 'no_events':
      return 'Economic data is available but no upcoming events are in the test window.';
    case 'post_release':
      return 'Recent releases include actual values and surprise labels.';
    default:
      return 'Inflation cools while employment and growth remain stable.';
  }
}
