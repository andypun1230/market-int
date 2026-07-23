import {
  buildMacroDashboardViewModel,
  calculateEconomicSurprise,
  calculateRiskAppetite,
  classifyEconomicSurprise,
  calculateTreasurySpreads,
  deriveEconomicReleaseTone,
  formatEconomicChange,
  formatEconomicValue,
  formatMacroEventForTimezone,
  macroAssetDefinitions,
  normalizeMacroSeries,
  type MacroAssetPerformance,
} from '../src/features/market/macroAnalysis';
import {
  buildMacroMockScenario,
  MACRO_MOCK_SCENARIO_OPTIONS,
  validateMacroMockScenario,
} from '../src/features/market/mock/macroScenarios';
import type { CandleData, HistoryData } from '../src/types/market';

function assert(condition: unknown, message: string) {
  if (!condition) {
    throw new Error(message);
  }
}

function history(symbol: string, returnPercent: number, source = 'generated_test_data'): HistoryData {
  const sessions = 66;
  const start = 100;
  const end = start * (1 + returnPercent / 100);
  const candles: CandleData[] = Array.from({ length: sessions }, (_, index) => {
    const ratio = index / Math.max(1, sessions - 1);
    const close = start + (end - start) * ratio;
    const date = new Date(Date.UTC(2026, 0, 2 + index));
    return {
      close,
      high: close + 0.8,
      low: close - 0.8,
      open: close - 0.2,
      timestamp: date.toISOString(),
      volume: 1_000_000 + index * 5_000,
    };
  });
  return {
    adjusted: true,
    as_of: '2026-07-16T00:00:00.000Z',
    candles,
    fallback_used: false,
    is_live: false,
    is_stale: false,
    source,
    symbol,
    timeframe: 'D',
  };
}

function histories(returns: Record<string, number>) {
  return Object.fromEntries(
    Object.entries(returns).map(([symbol, returnPercent]) => [symbol, history(symbol, returnPercent)]),
  );
}

function asset(symbol: string, periodReturn: number): MacroAssetPerformance {
  const definition = macroAssetDefinitions.find((item) => item.symbol === symbol);
  if (!definition) {
    throw new Error(`Missing macro definition for ${symbol}`);
  }
  return {
    ...definition,
    chartPoints: [
      { dateLabel: 'Jan 1', timestamp: '2026-01-01T00:00:00.000Z', value: 0 },
      { dateLabel: 'Mar 31', timestamp: '2026-03-31T00:00:00.000Z', value: periodReturn },
    ],
    isLive: true,
    isMock: false,
    isStale: false,
    periodReturn,
    source: 'test',
  };
}

function runTests() {
  const normalized = normalizeMacroSeries(history('SPY', 5).candles, '3M');
  assert(normalized.length === 66, '3M uses the expected trading-session window');
  assert(normalized[0]?.value === 0, 'normalized series starts at 0%');
  assert(Math.abs((normalized.at(-1)?.value ?? 0) - 5) < 0.001, 'normalized series preserves selected-period return');

  const strongRiskOn = buildMacroDashboardViewModel(histories({
    GLD: 0,
    HYG: 5,
    IEF: -1,
    SPY: 8,
    TLT: -3,
    UUP: -1,
    USO: 2,
  }), '3M');
  assert(strongRiskOn.riskAppetite.state === 'strong_risk_on', 'strong risk-on scenario classifies correctly');
  assert(strongRiskOn.assetRotation.items[0]?.symbol === 'SPY', 'asset rotation ranks the strongest asset first');
  assert(strongRiskOn.crossAsset.series.every((series) => series.chartPoints[0]?.value === 0), 'all cross-asset series normalize to 0%');
  assert(strongRiskOn.overview.keyRisk === 'No dominant current macro risk is identified.', 'current macro risk does not fabricate a future condition');
  assert(strongRiskOn.overview.invalidationConditions.includes('renewed rise'), 'future invalidation remains separately labelled');
  assert(!strongRiskOn.overview.currentRisks.some((risk) => risk.toLowerCase().includes('renewed rise')), 'future invalidation is not mixed into current-risk evidence');

  const riskOff = buildMacroDashboardViewModel(histories({
    GLD: 6,
    HYG: -2,
    IEF: 4,
    SPY: -6,
    TLT: 7,
    UUP: 4,
    USO: -3,
  }), '3M');
  assert(riskOff.riskAppetite.state === 'risk_off' || riskOff.riskAppetite.state === 'defensive_rotation', 'risk-off scenario is defensive');
  assert(riskOff.riskAppetite.defensiveFactors.length > 0, 'defensive scenario produces defensive factors');

  const oilOnly = calculateRiskAppetite([asset('SPY', 0), asset('USO', 12)]);
  assert(oilOnly.state !== 'risk_on' && oilOnly.state !== 'strong_risk_on', 'oil strength alone does not create a risk-on state');
  assert(oilOnly.confidence === 'low', 'partial data reduces confidence');

  const spreads = calculateTreasurySpreads([asset('SPY', 6), asset('IEF', -1), asset('TLT', -4)]);
  assert(spreads.spyVs10Y === 7, 'SPY versus 10Y bond proxy spread uses percentage points');
  assert(spreads.spyVs30Y === 10, 'SPY versus 30Y bond proxy spread uses percentage points');

  const partial = buildMacroDashboardViewModel(histories({ SPY: 2, GLD: 1 }), '3M');
  assert(partial.dataQuality.missingAssets.length > 0, 'partial data reports missing proxies');
  assert(partial.economicDashboard.metrics.length === 0, 'economic dashboard does not fabricate metrics');
  assert(partial.eventTimeline.events.length === 0, 'event timeline does not fabricate events');
  assert(partial.eventTimeline.message.includes('unavailable'), 'event timeline explains unavailable state');

  assert(formatEconomicValue(185, 'thousands') === '+185K', 'payroll thousands format with sign');
  assert(formatEconomicValue(2.6, 'percent') === '2.6%', 'CPI percentage formatting');
  assert(formatEconomicChange({
    key: 'ten_year_yield',
    label: '10Y Yield',
    latest: 4.05,
    periodType: 'level',
    prior: 4.18,
    releaseDate: '2026-07-15T16:00:00-04:00',
    source: 'test',
    unit: 'percent',
  }) === '-13 bps', 'yield changes display in basis points');

  const cpiSurprise = calculateEconomicSurprise({
    consensus: 3.1,
    key: 'cpi_yoy',
    label: 'CPI',
    latest: 3.0,
    periodType: 'year_over_year',
    prior: 3.0,
    releaseDate: '2026-07-15T08:30:00-04:00',
    source: 'test',
    unit: 'percent',
  });
  assert(cpiSurprise.formattedValue === '-0.1 pts', 'CPI surprise displays percentage points');
  assert(cpiSurprise.direction === 'below', 'CPI below consensus is below expectations');

  const payrollSurprise = calculateEconomicSurprise({
    consensus: 165,
    key: 'nonfarm_payrolls',
    label: 'Payrolls',
    latest: 175,
    periodType: 'level',
    prior: 180,
    releaseDate: '2026-07-03T08:30:00-04:00',
    source: 'test',
    unit: 'thousands',
  });
  assert(payrollSurprise.formattedValue === '+10K', 'payroll surprise displays thousands');
  assert(classifyEconomicSurprise({
    consensus: 165,
    key: 'nonfarm_payrolls',
    label: 'Payrolls',
    latest: 174,
    periodType: 'level',
    prior: 180,
    releaseDate: '2026-07-03T08:30:00-04:00',
    source: 'test',
    unit: 'thousands',
  }, 9) === 'in_line', 'payroll surprise inside 10K tolerance is in line');

  const fedSurprise = calculateEconomicSurprise({
    consensus: 4.5,
    key: 'fed_funds',
    label: 'Fed Funds',
    latest: 4.75,
    periodType: 'level',
    prior: 4.5,
    releaseDate: '2026-06-17T14:00:00-04:00',
    source: 'test',
    unit: 'percent',
  });
  assert(fedSurprise.formattedValue === '+25 bps', 'Fed Funds surprise displays basis points');
  assert(deriveEconomicReleaseTone({
    consensus: 4.5,
    key: 'fed_funds',
    label: 'Fed Funds',
    latest: 4.75,
    periodType: 'level',
    prior: 4.5,
    releaseDate: '2026-06-17T14:00:00-04:00',
    source: 'test',
    unit: 'percent',
  }, 'above_expectations') === 'warning', 'Fed above expectations is restrictive warning');

  assert(classifyEconomicSurprise({
    consensus: 3.04,
    key: 'cpi_yoy',
    label: 'CPI',
    latest: 3.0,
    periodType: 'year_over_year',
    prior: 3.0,
    releaseDate: '2026-07-15T08:30:00-04:00',
    source: 'test',
    unit: 'percent',
  }, -0.04) === 'in_line', 'CPI surprise inside tolerance is in line');

  assert(deriveEconomicReleaseTone({
    consensus: 4.1,
    key: 'unemployment_rate',
    label: 'Unemployment',
    latest: 4.3,
    periodType: 'level',
    prior: 4.1,
    releaseDate: '2026-07-03T08:30:00-04:00',
    source: 'test',
    unit: 'percent',
  }, 'above_expectations') === 'warning', 'unemployment above expectations is labor-market warning');

  const hkEvent = formatMacroEventForTimezone('2026-07-22T08:30:00-04:00', 'Asia/Hong_Kong');
  assert(hkEvent.date.includes('Jul 22') && hkEvent.time?.includes('PM'), 'New York event converts to Hong Kong evening');
  const dstEvent = formatMacroEventForTimezone('2026-03-10T14:00:00-04:00', 'Asia/Hong_Kong');
  assert(dstEvent.date.includes('Mar 11'), 'DST conversion handles date rollover');

  assert(MACRO_MOCK_SCENARIO_OPTIONS.length === 10, 'all macro mock scenarios are available');
  for (const option of MACRO_MOCK_SCENARIO_OPTIONS) {
    const scenario = buildMacroMockScenario(option.id);
    const validation = validateMacroMockScenario(scenario);
    assert(validation.valid, `${option.label} scenario dates are internally valid`);
  }

  const softLanding = buildMacroMockScenario('soft_landing');
  const softModel = buildMacroDashboardViewModel(histories({
    GLD: 1,
    HYG: 3,
    IEF: 0,
    SPY: 5,
    TLT: -1,
    UUP: -1,
    USO: 2,
  }), '3M', 'Asia/Hong_Kong', softLanding);
  assert(softModel.economicDashboard.sourceLabel === 'Test data', 'economic dashboard maps test source to Test data');
  assert(softModel.economicDashboard.metrics.some((metric) => metric.label === 'CPI' && metric.trend.includes('Cooling')), 'soft landing CPI cools');
  assert(softModel.economicDashboard.metrics.some((metric) => metric.label === 'Payrolls' && metric.latestValue === '+185K'), 'soft landing payrolls render');
  const cpiCard = softModel.economicDashboard.metrics.find((metric) => metric.key === 'cpi_yoy');
  assert(cpiCard?.mode === 'release_surprise', 'CPI uses release surprise card mode');
  assert(cpiCard?.expected?.formattedValue === '3.1%', 'CPI card displays expected value');
  assert(cpiCard?.previous?.formattedValue === '2.8%', 'CPI card displays previous value');
  assert(cpiCard?.surpriseLabel === 'Below Expectations', 'CPI card classifies below expectations');
  assert(cpiCard?.comment === 'Inflation cooling', 'CPI card uses short market comment');
  assert((cpiCard?.comment.length ?? 99) <= 24, 'economic comment remains short');
  const fedCard = softModel.economicDashboard.metrics.find((metric) => metric.key === 'fed_funds');
  assert(fedCard?.mode === 'policy_decision', 'Fed Funds uses policy decision card mode');
  assert(fedCard?.surpriseLabel === 'In Line', 'Fed Funds can render in-line policy decision');
  const yieldCard = softModel.economicDashboard.metrics.find((metric) => metric.key === 'ten_year_yield');
  assert(yieldCard?.mode === 'market_level', '10Y yield uses market-level card mode');
  assert(yieldCard?.expected === null, '10Y yield does not fabricate consensus');
  assert(yieldCard?.surpriseClassification === 'consensus_unavailable', 'yield surprise is unavailable without consensus');
  assert(yieldCard?.comment === 'Yields easing', 'yield card uses change-based short comment');
  const ppiCard = softModel.economicDashboard.metrics.find((metric) => metric.key === 'ppi_yoy');
  assert(ppiCard?.revisedPrevious?.formattedValue === '2.4%', 'revised previous value is preserved when available');
  assert(softModel.economicDashboard.metrics[0]?.key === 'cpi_mom' || softModel.economicDashboard.metrics[0]?.key === 'cpi_yoy', 'economic cards sort by market relevance');
  assert(softModel.eventTimeline.events.length > 0, 'soft landing has upcoming events');
  assert(softModel.eventTimeline.events[0]?.time?.includes('HKT') || softModel.eventTimeline.events[0]?.time?.includes('GMT+8'), 'event timeline displays local timezone');
  assert(softModel.interpretation.implication.toLowerCase().includes('disinflation') || softModel.overview.summary.toLowerCase().includes('cooling'), 'soft landing updates macro interpretation');

  const inflation = buildMacroDashboardViewModel(histories({ SPY: 0, IEF: -2, TLT: -4, GLD: 2, USO: 6 }), '3M', 'Asia/Hong_Kong', buildMacroMockScenario('inflation_reacceleration'));
  assert(inflation.overview.regime === 'inflationary', 'inflation scenario derives inflationary regime');
  assert(
    inflation.interpretation.implication.toLowerCase().includes('inflation') &&
      inflation.overview.currentRisks.some((risk) => risk.toLowerCase().includes('inflation')),
    'inflation scenario exposes inflation risk without assuming it must replace the leading cross-asset risk',
  );

  const growthSlowdown = buildMacroDashboardViewModel(histories({ SPY: -3, IEF: 3, TLT: 5, GLD: 2, USO: -4 }), '3M', 'Asia/Hong_Kong', buildMacroMockScenario('growth_slowdown'));
  assert(growthSlowdown.overview.regime === 'growth_slowdown', 'growth slowdown derives defensive economic regime');

  const partialEconomic = buildMacroDashboardViewModel(histories({ SPY: 1, GLD: 1 }), '3M', 'Asia/Hong_Kong', buildMacroMockScenario('partial_data'));
  assert(partialEconomic.economicDashboard.metrics.length === 4, 'partial data only renders valid available indicators');
  assert(partialEconomic.interpretation.confidence === 'low', 'partial economic data lowers confidence');

  const noEvents = buildMacroDashboardViewModel(histories({ SPY: 1, GLD: 1 }), '3M', 'Asia/Hong_Kong', buildMacroMockScenario('no_events'));
  assert(noEvents.economicDashboard.metrics.length > 0, 'no-events scenario keeps economic dashboard data');
  assert(noEvents.eventTimeline.events.length === 0, 'no-events scenario has no timeline cards');
  assert(noEvents.eventTimeline.message.includes('No major US macro events'), 'no-events state is compact and valid');

  const postRelease = buildMacroDashboardViewModel(histories({ SPY: 1, GLD: 1 }), '3M', 'Asia/Hong_Kong', buildMacroMockScenario('post_release'));
  assert(postRelease.eventTimeline.events.some((event) => event.actual && event.surprise === 'Below expectations'), 'post-release scenario shows actual and surprise');
}

runTests();
