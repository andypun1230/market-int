import type { CandleData, HistoryData } from '@/types/market';

export const macroTimeframes = ['1M', '3M', '6M', '1Y'] as const;

export type MacroTimeframe = (typeof macroTimeframes)[number];
export type MacroConfidence = 'high' | 'moderate' | 'low' | 'unavailable';
export type MacroSourceKind = 'live' | 'cached' | 'mock' | 'fallback' | 'mixed' | 'unavailable';
export type EconomicUnit = 'percent' | 'basis_points' | 'thousands' | 'annualized_percent' | 'index' | 'currency';
export type EconomicPeriodType = 'level' | 'month_over_month' | 'year_over_year' | 'quarter_over_quarter_annualized';
export type EconomicTrend =
  | 'cooling'
  | 'heating'
  | 'sticky'
  | 'stable'
  | 'easing'
  | 'falling'
  | 'rising'
  | 'holding'
  | 'expanding'
  | 'slowing'
  | 'weakening'
  | 'strong'
  | 'unavailable';
export type MacroRegime =
  | 'strong_risk_on'
  | 'risk_on'
  | 'balanced'
  | 'defensive_rotation'
  | 'risk_off'
  | 'inflationary'
  | 'disinflationary'
  | 'growth_slowdown'
  | 'mixed'
  | 'unavailable';
export type RiskAppetiteState =
  | 'strong_risk_on'
  | 'risk_on'
  | 'balanced'
  | 'defensive_rotation'
  | 'risk_off'
  | 'unavailable';
export type MacroAssetClass =
  | 'equities'
  | 'treasury_10y'
  | 'treasury_30y'
  | 'gold'
  | 'oil'
  | 'dollar'
  | 'credit';

export type MacroAssetDefinition = {
  assetClass: MacroAssetClass;
  label: string;
  symbol: string;
  kind: 'fund' | 'index' | 'yield' | 'economic_series';
};

export type MacroChartPoint = {
  dateLabel: string;
  timestamp: string;
  value: number;
};

export type MacroAssetPerformance = MacroAssetDefinition & {
  chartPoints: MacroChartPoint[];
  isLive: boolean;
  isMock: boolean;
  isStale: boolean;
  periodReturn: number | null;
  source: string;
};

export type RiskAppetiteResult = {
  confidence: MacroConfidence;
  defensiveFactors: string[];
  explanation: string;
  score: number | null;
  state: RiskAppetiteState;
  supportingFactors: string[];
};

export type MacroDashboardViewModel = {
  assetRotation: {
    interpretation: string;
    items: MacroAssetPerformance[];
  };
  commodities: {
    gold: CommodityRead | null;
    interpretation: string;
    oil: CommodityRead | null;
  };
  crossAsset: {
    benchmark: string;
    series: MacroAssetPerformance[];
    sourceLabel: string;
  };
  dataQuality: {
    confidence: MacroConfidence;
    missingAssets: string[];
    sourceLabel: string;
    sourceKind: MacroSourceKind;
  };
  economicDashboard: {
    message: string;
    metrics: EconomicMetric[];
    sourceLabel: string;
  };
  eventTimeline: {
    events: MacroEvent[];
    message: string;
    timezone: string;
  };
  interpretation: {
    confidence: MacroConfidence;
    implication: string;
    invalidationConditions: string;
    mainRisk: string;
    stance: string;
    supportiveFactor: string;
  };
  overview: {
    confidence: MacroConfidence;
    currentRisks: string[];
    supportingEvidence: string[];
    invalidationConditions: string;
    keyRisk: string;
    lagging: string[];
    leading: string[];
    regime: MacroRegime;
    summary: string;
  };
  riskAppetite: RiskAppetiteResult;
  timeframe: MacroTimeframe;
  treasuryEquity: {
    interpretation: string;
    spyVs10Y: number | null;
    spyVs30Y: number | null;
    series: MacroAssetPerformance[];
    yieldSummary: string;
  };
};

export type CommodityRead = {
  interpretation: string;
  label: string;
  relativeToSpy: number | null;
  returnValue: number | null;
  sourceLabel: string;
  trend: string;
};

export type EconomicSurpriseClassification =
  | 'above_expectations'
  | 'below_expectations'
  | 'in_line'
  | 'consensus_unavailable';

export type EconomicIndicatorSemantics =
  | 'lower_is_cooler'
  | 'higher_is_stronger'
  | 'lower_is_stronger'
  | 'policy_rate'
  | 'market_level'
  | 'neutral';

export type EconomicCardMode =
  | 'release_surprise'
  | 'policy_decision'
  | 'market_level';

export type EconomicSurprise = {
  direction: 'above' | 'below' | 'in_line' | 'unavailable';
  formattedValue: string | null;
  rawValue: number | null;
};

export type EconomicDisplayValue = {
  formattedValue: string;
  rawValue: number;
};

export type EconomicMetric = {
  actual: EconomicDisplayValue;
  change: string | null;
  comment: string;
  expected: EconomicDisplayValue | null;
  interpretation: string;
  key: string;
  label: string;
  latestDate: string | null;
  latestValue: string | null;
  mode: EconomicCardMode;
  periodLabel: string;
  previous: EconomicDisplayValue | null;
  priorValue: string | null;
  revisedPrevious: EconomicDisplayValue | null;
  sourceLabel: string | null;
  surprise: EconomicSurprise;
  surpriseClassification: EconomicSurpriseClassification;
  surpriseLabel: string;
  tone: 'positive' | 'warning' | 'negative' | 'neutral';
  trend: string;
  unit: string;
};

export type EconomicIndicatorSnapshot = {
  consensus?: number | null;
  freshness?: 'fresh' | 'stale' | 'test';
  key: string;
  label: string;
  latest: number | null;
  periodType: EconomicPeriodType;
  prior: number | null;
  revised_prior_from?: number | null;
  releaseDate: string;
  source: 'test' | 'live' | 'cached' | 'unavailable';
  trend?: string | null;
  unit: EconomicUnit;
};

export type MacroEvent = {
  actual?: string | null;
  category?: string;
  consensus?: string | null;
  date: string;
  event: string;
  importance: 'High Impact' | 'Medium Impact' | 'Low Impact';
  previous?: string | null;
  source?: 'test' | 'live' | 'cached' | 'unavailable';
  sourceTimezone?: string;
  status?: 'Upcoming' | 'Released' | 'Revised' | 'Cancelled';
  surprise?: string | null;
  time?: string | null;
};

export const macroAssetDefinitions: MacroAssetDefinition[] = [
  { assetClass: 'equities', label: 'Equities', symbol: 'SPY', kind: 'fund' },
  { assetClass: 'treasury_10y', label: '10Y Bonds', symbol: 'IEF', kind: 'fund' },
  { assetClass: 'treasury_30y', label: '30Y Bonds', symbol: 'TLT', kind: 'fund' },
  { assetClass: 'gold', label: 'Gold', symbol: 'GLD', kind: 'fund' },
  { assetClass: 'oil', label: 'Oil', symbol: 'USO', kind: 'fund' },
  { assetClass: 'dollar', label: 'Dollar', symbol: 'UUP', kind: 'fund' },
  { assetClass: 'credit', label: 'Credit', symbol: 'HYG', kind: 'fund' },
];

export const macroTimeframeSessions: Record<MacroTimeframe, number> = {
  '1M': 22,
  '3M': 66,
  '6M': 132,
  '1Y': 252,
};

export const macroTimeframeDays: Record<MacroTimeframe, number> = {
  '1M': 45,
  '3M': 110,
  '6M': 220,
  '1Y': 370,
};

export function buildMacroDashboardViewModel(
  histories: Partial<Record<string, HistoryData>>,
  timeframe: MacroTimeframe,
  timezone = Intl.DateTimeFormat().resolvedOptions().timeZone,
  testData?: {
    asOfDate: string;
    economicIndicators: EconomicIndicatorSnapshot[];
    macroEvents: MacroEvent[];
    source: 'test';
  } | null,
): MacroDashboardViewModel {
  const assets = macroAssetDefinitions
    .map((definition) => buildAssetPerformance(definition, histories[definition.symbol], timeframe))
    .filter((asset): asset is MacroAssetPerformance => asset !== null);
  const riskAppetite = calculateRiskAppetite(assets);
  const treasuryEquity = buildTreasuryEquity(assets);
  const commodities = buildCommodityDashboard(assets);
  const dataQuality = buildMacroDataQuality(assets);
  const economicDashboard = buildEconomicDashboard(testData?.economicIndicators ?? []);
  const eventTimeline = buildMacroEventTimeline(testData?.macroEvents ?? [], timezone, testData?.asOfDate ?? null);
  const economicRead = buildEconomicRead(economicDashboard.metrics, testData?.source ?? null);
  const overview = buildMacroOverview(assets, riskAppetite, commodities, dataQuality, economicRead);
  return {
    assetRotation: {
      interpretation: buildAssetRotationInterpretation(assets),
      items: [...assets].filter((asset) => asset.periodReturn !== null).sort((a, b) => (b.periodReturn ?? -Infinity) - (a.periodReturn ?? -Infinity)),
    },
    commodities,
    crossAsset: {
      benchmark: 'SPY',
      series: assets.filter((asset) => asset.chartPoints.length >= 2).slice(0, 6),
      sourceLabel: dataQuality.sourceLabel,
    },
    dataQuality,
    economicDashboard,
    eventTimeline,
    interpretation: buildMacroInterpretation(overview, riskAppetite, treasuryEquity, commodities, economicRead),
    overview,
    riskAppetite,
    timeframe,
    treasuryEquity,
  };
}

export function buildEconomicDashboard(indicators: EconomicIndicatorSnapshot[]): MacroDashboardViewModel['economicDashboard'] {
  const metrics = indicators
    .filter((indicator): indicator is EconomicIndicatorSnapshot & { latest: number } => indicator.latest !== null && Number.isFinite(indicator.latest))
    .map((indicator): EconomicMetric => {
      const trend = indicator.trend ?? classifyEconomicTrend(indicator);
      const mode = getEconomicCardMode(indicator);
      const surprise = calculateEconomicSurprise(indicator);
      const surpriseClassification = classifyEconomicSurprise(indicator, surprise.rawValue);
      return {
        actual: {
          formattedValue: formatEconomicValue(indicator.latest, indicator.unit),
          rawValue: indicator.latest,
        },
        change: formatEconomicChange(indicator),
        comment: buildEconomicReleaseComment(indicator, surpriseClassification),
        expected: buildEconomicDisplayValue(indicator.consensus ?? null, indicator.unit),
        interpretation: interpretEconomicIndicator(indicator, trend),
        key: indicator.key,
        label: indicator.label,
        latestDate: formatReleaseDate(indicator.releaseDate),
        latestValue: formatEconomicValue(indicator.latest, indicator.unit),
        mode,
        periodLabel: formatEconomicPeriod(indicator.periodType),
        previous: buildEconomicDisplayValue(indicator.prior, indicator.unit),
        priorValue: indicator.prior === null ? null : formatEconomicValue(indicator.prior, indicator.unit),
        revisedPrevious: buildEconomicDisplayValue(indicator.revised_prior_from ?? null, indicator.unit),
        sourceLabel: sourceLabelForEconomicIndicator(indicator),
        surprise,
        surpriseClassification,
        surpriseLabel: formatEconomicSurpriseClassification(surpriseClassification),
        tone: deriveEconomicReleaseTone(indicator, surpriseClassification),
        trend,
        unit: indicator.unit,
      };
    })
    .sort((a, b) => economicIndicatorRank(a.key) - economicIndicatorRank(b.key) || a.label.localeCompare(b.label));
  return {
    message: metrics.length
      ? `${metrics.length} economic indicators available.`
      : 'Economic release data is unavailable from the configured project data sources.',
    metrics,
    sourceLabel: indicators.some((indicator) => indicator.source === 'test') ? 'Test data' : metrics.length ? 'Mixed sources' : 'Unavailable',
  };
}

export function buildMacroEventTimeline(events: MacroEvent[], timezone: string, asOfDate: string | null): MacroDashboardViewModel['eventTimeline'] {
  const asOfTime = asOfDate ? Date.parse(asOfDate) : null;
  const sorted = [...events]
    .filter((event) => Number.isFinite(Date.parse(event.date)))
    .filter((event) => {
      if (asOfTime === null || event.status === 'Released' || event.status === 'Revised') {
        return true;
      }
      return Date.parse(event.date) > asOfTime;
    })
    .sort((a, b) => Date.parse(a.date) - Date.parse(b.date))
    .map((event) => ({
      ...event,
      date: formatEventDate(event.date, timezone),
      time: formatEventTime(event.date, timezone),
      sourceTimezone: event.sourceTimezone ?? 'America/New_York',
      status: event.status ?? 'Upcoming',
    }))
    .slice(0, 7);
  return {
    events: sorted,
    message: events.length
      ? 'No major US macro events are scheduled in the selected test window.'
      : asOfDate
        ? 'No major US macro events are scheduled in the selected test window.'
      : 'Upcoming macro events unavailable. No reliable economic-calendar source is configured.',
    timezone,
  };
}

export function normalizeMacroSeries(candles: CandleData[], timeframe: MacroTimeframe): MacroChartPoint[] {
  const selected = selectTimeframeCandles(candles, timeframe);
  const first = selected.find((candle) => candle.close > 0);
  if (!first) {
    return [];
  }
  return selected
    .filter((candle) => candle.close > 0 && isFiniteNumber(candle.close))
    .map((candle) => ({
      dateLabel: formatDateLabel(candle.timestamp),
      timestamp: candle.timestamp,
      value: ((candle.close / first.close) - 1) * 100,
    }));
}

export function calculateMacroReturn(candles: CandleData[], timeframe: MacroTimeframe): number | null {
  const selected = selectTimeframeCandles(candles, timeframe);
  const first = selected.find((candle) => candle.close > 0);
  const latest = [...selected].reverse().find((candle) => candle.close > 0);
  if (!first || !latest || first.close <= 0) {
    return null;
  }
  return ((latest.close / first.close) - 1) * 100;
}

export function calculateRiskAppetite(assets: MacroAssetPerformance[]): RiskAppetiteResult {
  const spy = findReturn(assets, 'equities');
  const ief = findReturn(assets, 'treasury_10y');
  const tlt = findReturn(assets, 'treasury_30y');
  const gold = findReturn(assets, 'gold');
  const oil = findReturn(assets, 'oil');
  const dollar = findReturn(assets, 'dollar');
  const credit = findReturn(assets, 'credit');
  const supportingFactors: string[] = [];
  const defensiveFactors: string[] = [];
  let score = 50;
  let weightCount = 0;

  if (spy !== null && (ief !== null || tlt !== null)) {
    const bondAverage = average([ief, tlt]);
    if (bondAverage !== null) {
      const spread = spy - bondAverage;
      score += clamp(spread * 2.4, -28, 28);
      weightCount += 2;
      if (spread > 1.5) {
        supportingFactors.push('Equities are outperforming Treasury bond proxies.');
      } else if (spread < -1.5) {
        defensiveFactors.push('Treasury bond proxies are outperforming equities.');
      }
    }
  }

  if (credit !== null && ief !== null) {
    const creditSpread = credit - ief;
    score += clamp(creditSpread * 1.2, -12, 12);
    weightCount += 1;
    if (creditSpread > 1) {
      supportingFactors.push('Credit risk appetite is stronger than intermediate Treasuries.');
    } else if (creditSpread < -1) {
      defensiveFactors.push('Credit is lagging intermediate Treasuries.');
    }
  }

  if (spy !== null && gold !== null) {
    const goldSpread = gold - spy;
    score += clamp(-goldSpread * 1.1, -12, 12);
    weightCount += 1;
    if (goldSpread > 1.5) {
      defensiveFactors.push('Gold is outperforming equities.');
    } else if (goldSpread < -1.5) {
      supportingFactors.push('Gold is lagging equities.');
    }
  }

  if (spy !== null && dollar !== null) {
    const dollarSpread = dollar - spy;
    score += clamp(-dollarSpread * 0.8, -8, 8);
    weightCount += 1;
    if (dollarSpread > 1.5) {
      defensiveFactors.push('Dollar strength is a macro headwind.');
    }
  }

  if (spy !== null && oil !== null) {
    const oilSpread = oil - spy;
    const oilContribution = spy > 0 ? clamp(oilSpread * 0.35, -5, 5) : clamp(-Math.abs(oilSpread) * 0.35, -5, 2);
    score += oilContribution;
    weightCount += 0.5;
    if (oil > 3 && spy > 0) {
      supportingFactors.push('Oil strength is consistent with firm nominal-growth expectations.');
    } else if (oil > 3 && spy <= 0) {
      defensiveFactors.push('Oil strength without equity confirmation may reflect inflation or supply pressure.');
    }
  }

  if (weightCount === 0) {
    return {
      confidence: 'unavailable',
      defensiveFactors: [],
      explanation: 'Cross-asset data is unavailable.',
      score: null,
      state: 'unavailable',
      supportingFactors: [],
    };
  }

  const finalScore = Math.round(clamp(score, 0, 100));
  return {
    confidence: classifyMacroConfidence(assets.length),
    defensiveFactors,
    explanation: buildRiskExplanation(finalScore, supportingFactors, defensiveFactors),
    score: finalScore,
    state: classifyRiskAppetite(finalScore),
    supportingFactors,
  };
}

export function calculateTreasurySpreads(assets: MacroAssetPerformance[]) {
  const spy = findReturn(assets, 'equities');
  const ief = findReturn(assets, 'treasury_10y');
  const tlt = findReturn(assets, 'treasury_30y');
  return {
    spyVs10Y: spy !== null && ief !== null ? spy - ief : null,
    spyVs30Y: spy !== null && tlt !== null ? spy - tlt : null,
  };
}

export function classifyEconomicTrend(indicator: EconomicIndicatorSnapshot): string {
  if (indicator.latest === null || !Number.isFinite(indicator.latest) || indicator.prior === null || !Number.isFinite(indicator.prior)) {
    return 'Unavailable';
  }
  const delta = indicator.latest - indicator.prior;
  const key = indicator.key.toLowerCase();
  if (key.includes('fed_funds')) {
    if (delta <= -0.1) {
      return 'Easing';
    }
    if (delta >= 0.1) {
      return 'Tightening';
    }
    return indicator.latest >= 4 ? 'Restrictive Hold' : 'Holding';
  }
  if (key.includes('yield')) {
    if (delta <= -0.1) {
      return 'Falling';
    }
    if (delta >= 0.25) {
      return 'Rising Quickly';
    }
    if (delta >= 0.1) {
      return 'Rising';
    }
    return 'Stable';
  }
  if (key.includes('cpi') || key.includes('ppi') || key.includes('pce')) {
    if (delta <= -0.15) {
      return indicator.latest > 2.8 ? 'Cooling Gradually' : 'Cooling';
    }
    if (delta >= 0.2) {
      return 'Heating';
    }
    return indicator.latest > 3 ? 'Sticky' : 'Stable';
  }
  if (key.includes('payroll')) {
    if (indicator.latest < 80 || delta < -75) {
      return 'Weakening';
    }
    if (indicator.latest > 210 || delta > 35) {
      return 'Strong';
    }
    return 'Stable';
  }
  if (key.includes('unemployment')) {
    if (delta >= 0.2 || indicator.latest >= 4.6) {
      return 'Weakening';
    }
    if (delta <= -0.1) {
      return 'Firm';
    }
    return 'Stable';
  }
  if (key.includes('gdp')) {
    if (indicator.latest < 1 || delta < -0.7) {
      return 'Slowing';
    }
    if (indicator.latest > 2) {
      return 'Expanding';
    }
    return 'Stable';
  }
  if (key.includes('retail')) {
    if (indicator.latest < 0) {
      return 'Weakening';
    }
    if (indicator.latest > 0.5) {
      return 'Strong';
    }
    return 'Stable';
  }
  if (key.includes('earnings')) {
    if (indicator.latest < indicator.prior) {
      return 'Cooling';
    }
    return 'Stable';
  }
  return Math.abs(delta) < 0.05 ? 'Stable' : delta > 0 ? 'Rising' : 'Falling';
}

export function formatEconomicValue(value: number | null, unit: EconomicUnit) {
  if (value === null || !Number.isFinite(value)) {
    return 'N/A';
  }
  switch (unit) {
    case 'thousands':
      return `${value >= 0 ? '+' : '-'}${Math.abs(value).toFixed(0)}K`;
    case 'basis_points':
      return `${value.toFixed(0)} bps`;
    case 'annualized_percent':
    case 'percent':
      return `${value.toFixed(1)}%`;
    case 'currency':
      return `$${value.toFixed(2)}`;
    default:
      return value.toFixed(1);
  }
}

export function formatEconomicChange(indicator: EconomicIndicatorSnapshot) {
  if (indicator.latest === null || indicator.prior === null || !Number.isFinite(indicator.latest) || !Number.isFinite(indicator.prior)) {
    return null;
  }
  const delta = indicator.latest - indicator.prior;
  if (Math.abs(delta) < 0.005) {
    return 'No change';
  }
  if (indicator.unit === 'thousands') {
    return `${delta > 0 ? '+' : '-'}${Math.abs(delta).toFixed(0)}K`;
  }
  if (indicator.key.includes('yield') || indicator.key.includes('fed_funds')) {
    return `${delta > 0 ? '+' : '-'}${Math.abs(delta * 100).toFixed(0)} bps`;
  }
  return `${delta > 0 ? '+' : '-'}${Math.abs(delta).toFixed(1)} pts`;
}

export function calculateEconomicSurprise(indicator: EconomicIndicatorSnapshot): EconomicSurprise {
  if (!isFiniteNumber(indicator.latest) || !isFiniteNumber(indicator.consensus)) {
    return { direction: 'unavailable', formattedValue: null, rawValue: null };
  }
  const rawValue = indicator.latest - indicator.consensus;
  const classification = classifyEconomicSurprise(indicator, rawValue);
  return {
    direction: classification === 'above_expectations'
      ? 'above'
      : classification === 'below_expectations'
        ? 'below'
        : classification === 'in_line'
          ? 'in_line'
          : 'unavailable',
    formattedValue: formatEconomicSurpriseValue(rawValue, indicator),
    rawValue,
  };
}

export function classifyEconomicSurprise(
  indicator: EconomicIndicatorSnapshot,
  surpriseValue: number | null,
): EconomicSurpriseClassification {
  if (surpriseValue === null || !Number.isFinite(surpriseValue)) {
    return 'consensus_unavailable';
  }
  const tolerance = economicSurpriseTolerance(indicator);
  if (Math.abs(surpriseValue) <= tolerance) {
    return 'in_line';
  }
  return surpriseValue > 0 ? 'above_expectations' : 'below_expectations';
}

export function formatEconomicSurpriseClassification(classification: EconomicSurpriseClassification) {
  switch (classification) {
    case 'above_expectations':
      return 'Above Expectations';
    case 'below_expectations':
      return 'Below Expectations';
    case 'in_line':
      return 'In Line';
    default:
      return 'Consensus unavailable';
  }
}

export function deriveEconomicReleaseTone(
  indicator: EconomicIndicatorSnapshot,
  classification: EconomicSurpriseClassification,
): EconomicMetric['tone'] {
  const semantics = economicIndicatorSemantics(indicator);
  if (classification === 'consensus_unavailable') {
    const change = indicator.latest !== null && indicator.prior !== null ? indicator.latest - indicator.prior : null;
    if (!Number.isFinite(change)) {
      return 'neutral';
    }
    if (semantics === 'market_level') {
      return Math.abs(change ?? 0) < economicSurpriseTolerance(indicator) ? 'neutral' : (change ?? 0) < 0 ? 'positive' : 'warning';
    }
    return 'neutral';
  }
  if (classification === 'in_line') {
    return 'neutral';
  }
  const above = classification === 'above_expectations';
  switch (semantics) {
    case 'lower_is_cooler':
    case 'policy_rate':
      return above ? 'warning' : 'positive';
    case 'lower_is_stronger':
      return above ? 'warning' : 'positive';
    case 'higher_is_stronger':
      return above ? 'positive' : 'warning';
    default:
      return 'neutral';
  }
}

export function buildEconomicReleaseComment(
  indicator: EconomicIndicatorSnapshot,
  classification: EconomicSurpriseClassification,
) {
  const key = indicator.key.toLowerCase();
  const change = isFiniteNumber(indicator.latest) && isFiniteNumber(indicator.prior)
    ? indicator.latest - indicator.prior
    : null;

  if (economicIndicatorSemantics(indicator) === 'market_level') {
    if (change === null || Math.abs(change) <= economicSurpriseTolerance(indicator)) {
      return key.includes('yield') ? 'Yields stable' : 'Level stable';
    }
    return change < 0 ? 'Yields easing' : 'Yields rising';
  }

  if (key.includes('fed_funds')) {
    if (classification === 'above_expectations') {
      return 'More restrictive';
    }
    if (classification === 'below_expectations') {
      return 'More accommodative';
    }
    return indicator.latest !== null && indicator.latest >= 4 ? 'Restrictive hold' : 'Policy in line';
  }

  if (key.includes('cpi') || key.includes('ppi') || key.includes('pce')) {
    if (classification === 'above_expectations') {
      if (key.includes('core')) {
        return 'Core inflation sticky';
      }
      if (key.includes('ppi')) {
        return 'Input pressure rising';
      }
      return 'Inflation hotter';
    }
    if (classification === 'below_expectations') {
      if (key.includes('core')) {
        return 'Core inflation easing';
      }
      if (key.includes('ppi')) {
        return 'Input pressure easing';
      }
      return 'Inflation cooling';
    }
    return key.includes('core') ? 'Core inflation in line' : 'Inflation in line';
  }

  if (key.includes('payroll')) {
    if (classification === 'above_expectations') {
      return 'Labor resilient';
    }
    if (classification === 'below_expectations') {
      return 'Hiring slowing';
    }
    return 'Labor in line';
  }

  if (key.includes('unemployment')) {
    if (classification === 'above_expectations') {
      return 'Labor softening';
    }
    if (classification === 'below_expectations') {
      return 'Labor remains tight';
    }
    return 'Labor in line';
  }

  if (key.includes('earnings')) {
    if (classification === 'above_expectations') {
      return 'Wage pressure stronger';
    }
    if (classification === 'below_expectations') {
      return 'Wage pressure softer';
    }
    return 'Wages in line';
  }

  if (key.includes('gdp')) {
    if (classification === 'above_expectations') {
      return 'Growth improving';
    }
    if (classification === 'below_expectations') {
      return 'Growth slowing';
    }
    return 'Growth in line';
  }

  if (key.includes('retail')) {
    if (classification === 'above_expectations') {
      return 'Consumer demand firm';
    }
    if (classification === 'below_expectations') {
      return 'Spending weakening';
    }
    return 'Spending in line';
  }

  if (change !== null && Math.abs(change) > economicSurpriseTolerance(indicator)) {
    return change > 0 ? 'Trend improving' : 'Trend softening';
  }
  return 'In line';
}

export function formatMacroEventForTimezone(timestamp: string, timezone: string) {
  return {
    date: formatEventDate(timestamp, timezone),
    time: formatEventTime(timestamp, timezone),
  };
}

function buildEconomicRead(metrics: EconomicMetric[], source: 'test' | null) {
  const trends = metrics.map((metric) => metric.trend.toLowerCase());
  const inflationHeating = trends.filter((trend) => trend.includes('heating') || trend.includes('sticky')).length;
  const inflationCooling = trends.filter((trend) => trend.includes('cooling')).length;
  const laborWeak = trends.filter((trend, index) => {
    const label = metrics[index]?.label.toLowerCase() ?? '';
    return (label.includes('payroll') || label.includes('unemployment') || label.includes('earnings')) && trend.includes('weak');
  }).length;
  const growthWeak = trends.some((trend, index) => {
    const label = metrics[index]?.label.toLowerCase() ?? '';
    return (label.includes('gdp') || label.includes('retail')) && (trend.includes('slow') || trend.includes('weak'));
  });
  const easing = trends.some((trend) => trend.includes('easing') || trend.includes('falling'));
  const confidence: MacroConfidence = !metrics.length
    ? 'unavailable'
    : metrics.length >= 9
      ? 'high'
      : metrics.length >= 5
        ? 'moderate'
        : 'low';

  if (!metrics.length) {
    return {
      confidence,
      implication: null,
      mainRisk: null,
      regime: 'mixed' as MacroRegime,
      summary: null,
      supportiveFactor: null,
    };
  }

  if (inflationHeating >= 2) {
    return {
      confidence,
      implication: 'Inflation pressure is rising, which can keep rate-sensitive equities vulnerable to yield shocks.',
      mainRisk: 'Inflation reacceleration and rising yields',
      regime: 'inflationary' as MacroRegime,
      summary: 'Economic test data points to inflation pressure.',
      supportiveFactor: source === 'test' ? 'Growth inputs remain available in the test scenario' : null,
    };
  }
  if (laborWeak >= 2 || growthWeak) {
    return {
      confidence,
      implication: 'Growth or labor deterioration raises the need for defensive confirmation before treating lower yields as purely supportive.',
      mainRisk: 'Growth slowdown or labor-market deterioration',
      regime: 'growth_slowdown' as MacroRegime,
      summary: 'Economic test data points to slower growth or weaker labor.',
      supportiveFactor: easing ? 'Lower yields may cushion financial conditions' : null,
    };
  }
  if (inflationCooling >= 2 && easing) {
    return {
      confidence,
      implication: 'Disinflation and easier rate pressure support a more constructive macro backdrop.',
      mainRisk: 'A renewed inflation or yield rebound',
      regime: 'disinflationary' as MacroRegime,
      summary: 'Economic test data shows cooling inflation and easing rate pressure.',
      supportiveFactor: 'Cooling inflation',
    };
  }
  return {
    confidence,
    implication: metrics.length < 5 ? 'Macro interpretation is limited by partial economic coverage.' : 'Economic signals are mixed, so macro conviction remains moderate.',
    mainRisk: metrics.length < 5 ? 'Partial economic coverage' : 'Conflicting inflation, rates, and labor signals',
    regime: 'mixed' as MacroRegime,
    summary: metrics.length < 5 ? 'Economic coverage is partial.' : 'Economic test data is mixed.',
    supportiveFactor: null,
  };
}

function buildAssetPerformance(
  definition: MacroAssetDefinition,
  history: HistoryData | undefined,
  timeframe: MacroTimeframe,
): MacroAssetPerformance | null {
  const candles = (history?.candles ?? [])
    .filter(isValidCandle)
    .sort((a, b) => Date.parse(a.timestamp) - Date.parse(b.timestamp));
  const chartPoints = normalizeMacroSeries(candles, timeframe);
  const periodReturn = calculateMacroReturn(candles, timeframe);
  if (!chartPoints.length || periodReturn === null) {
    return null;
  }
  return {
    ...definition,
    chartPoints,
    isLive: Boolean(history?.is_live),
    isMock: String(history?.source ?? '').includes('mock') || Boolean(history?.fallback_used),
    isStale: Boolean(history?.is_stale),
    periodReturn,
    source: history?.source ?? 'unavailable',
  };
}

function buildMacroOverview(
  assets: MacroAssetPerformance[],
  risk: RiskAppetiteResult,
  commodities: MacroDashboardViewModel['commodities'],
  dataQuality: MacroDashboardViewModel['dataQuality'],
  economicRead: ReturnType<typeof buildEconomicRead>,
): MacroDashboardViewModel['overview'] {
  if (risk.state === 'unavailable') {
    return {
      confidence: 'unavailable',
      currentRisks: [],
      supportingEvidence: [],
      invalidationConditions: 'Cross-asset coverage must be restored before an invalidation condition can be assessed.',
      keyRisk: 'Cross-asset coverage unavailable',
      lagging: [],
      leading: [],
      regime: 'unavailable',
      summary: 'Macro overview is unavailable because cross-asset history is incomplete.',
    };
  }
  const ranked = [...assets].filter((asset) => asset.periodReturn !== null).sort((a, b) => (b.periodReturn ?? 0) - (a.periodReturn ?? 0));
  const leading = ranked.slice(0, 2).map((asset) => asset.label);
  const lagging = ranked.slice(-2).reverse().map((asset) => asset.label);
  const oilReturn = commodities.oil?.returnValue ?? null;
  const currentRisks = [
    ...risk.defensiveFactors,
    oilReturn !== null && oilReturn > 5 ? 'Oil strength may keep inflation sensitivity elevated.' : null,
  ].filter((item): item is string => Boolean(item));
  const keyRisk = currentRisks[0] ?? 'No dominant current macro risk is identified.';
  const invalidationConditions = economicRead.mainRisk ?? 'A renewed rise in defensive assets or destabilizing yields would weaken this risk-appetite read.';
  const regime: MacroRegime = economicRead.regime !== 'mixed' ? economicRead.regime : risk.state;
  return {
    confidence: economicRead.confidence === 'unavailable' ? dataQuality.confidence : economicRead.confidence,
    currentRisks,
    supportingEvidence: risk.supportingFactors,
    invalidationConditions,
    keyRisk,
    lagging,
    leading,
    regime,
    summary: buildMacroOverviewSummary(risk, leading, lagging, economicRead),
  };
}

function buildTreasuryEquity(assets: MacroAssetPerformance[]): MacroDashboardViewModel['treasuryEquity'] {
  const spreads = calculateTreasurySpreads(assets);
  const series = assets.filter((asset) => ['equities', 'treasury_10y', 'treasury_30y'].includes(asset.assetClass));
  const spreadText = spreads.spyVs10Y !== null || spreads.spyVs30Y !== null
    ? `SPY is ${describeSpread(average([spreads.spyVs10Y, spreads.spyVs30Y]))} Treasury bond proxies.`
    : 'Treasury/equity spread data is unavailable.';
  return {
    interpretation: `${spreadText} Bond ETF prices are used as proxies here; yield levels are not available from the configured source.`,
    series,
    spyVs10Y: spreads.spyVs10Y,
    spyVs30Y: spreads.spyVs30Y,
    yieldSummary: 'Treasury yield history unavailable; bond ETF prices are shown separately from yields.',
  };
}

function buildCommodityDashboard(assets: MacroAssetPerformance[]): MacroDashboardViewModel['commodities'] {
  const spy = findReturn(assets, 'equities');
  const goldAsset = assets.find((asset) => asset.assetClass === 'gold') ?? null;
  const oilAsset = assets.find((asset) => asset.assetClass === 'oil') ?? null;
  const gold = goldAsset ? buildCommodityRead(goldAsset, spy) : null;
  const oil = oilAsset ? buildCommodityRead(oilAsset, spy) : null;
  const interpretation = gold || oil
    ? 'Gold is treated as a defensive/real-rate proxy, while oil is treated cautiously as a growth, inflation, or supply-sensitive proxy.'
    : 'Commodity proxy data is unavailable.';
  return { gold, interpretation, oil };
}

function buildCommodityRead(asset: MacroAssetPerformance, spyReturn: number | null): CommodityRead {
  const relativeToSpy = spyReturn !== null && asset.periodReturn !== null ? asset.periodReturn - spyReturn : null;
  const trend = asset.periodReturn === null
    ? 'Unavailable'
    : asset.periodReturn > 2
      ? 'Firm'
      : asset.periodReturn < -2
        ? 'Weak'
        : 'Stable';
  const interpretation = asset.assetClass === 'gold'
    ? buildGoldInterpretation(asset.periodReturn, relativeToSpy)
    : buildOilInterpretation(asset.periodReturn, relativeToSpy, spyReturn);
  return {
    interpretation,
    label: asset.label,
    relativeToSpy,
    returnValue: asset.periodReturn,
    sourceLabel: `${asset.symbol} proxy`,
    trend,
  };
}

function buildMacroDataQuality(assets: MacroAssetPerformance[]): MacroDashboardViewModel['dataQuality'] {
  const availableSymbols = new Set(assets.map((asset) => asset.symbol));
  const missingAssets = macroAssetDefinitions
    .filter((definition) => !availableSymbols.has(definition.symbol))
    .map((definition) => `${definition.label} (${definition.symbol})`);
  const liveCount = assets.filter((asset) => asset.isLive).length;
  const mockCount = assets.filter((asset) => asset.isMock).length;
  const staleCount = assets.filter((asset) => asset.isStale).length;
  const sourceKind: MacroSourceKind = !assets.length
    ? 'unavailable'
    : mockCount
      ? 'mixed'
      : staleCount
        ? 'cached'
        : liveCount === assets.length
          ? 'live'
          : 'mixed';
  return {
    confidence: classifyMacroConfidence(assets.length),
    missingAssets,
    sourceKind,
    sourceLabel: formatMacroSourceLabel(sourceKind),
  };
}

function buildMacroInterpretation(
  overview: MacroDashboardViewModel['overview'],
  risk: RiskAppetiteResult,
  treasury: MacroDashboardViewModel['treasuryEquity'],
  commodities: MacroDashboardViewModel['commodities'],
  economicRead: ReturnType<typeof buildEconomicRead>,
): MacroDashboardViewModel['interpretation'] {
  const supportiveFactor = economicRead.supportiveFactor ?? risk.supportingFactors[0] ?? (overview.leading.length ? `${overview.leading[0]} leadership` : 'Supportive factor unavailable');
  const mainRisk = overview.keyRisk;
  const implication = economicRead.implication ?? (risk.state === 'strong_risk_on' || risk.state === 'risk_on'
    ? 'Cross-asset conditions remain supportive of risk appetite.'
    : risk.state === 'risk_off' || risk.state === 'defensive_rotation'
      ? 'The backdrop is defensive, so equity leadership needs confirmation from cross-asset improvement.'
      : commodities.oil?.returnValue !== null && (commodities.oil?.returnValue ?? 0) > 5
        ? 'Oil strength keeps inflation sensitivity in the macro mix even if equities remain stable.'
        : treasury.interpretation);
  return {
    confidence: economicRead.confidence === 'unavailable' ? risk.confidence : economicRead.confidence,
    implication,
    invalidationConditions: overview.invalidationConditions,
    mainRisk,
    stance: formatRiskState(economicRead.regime !== 'mixed' ? economicRead.regime : risk.state),
    supportiveFactor,
  };
}

function buildAssetRotationInterpretation(assets: MacroAssetPerformance[]) {
  const ranked = [...assets].filter((asset) => asset.periodReturn !== null).sort((a, b) => (b.periodReturn ?? 0) - (a.periodReturn ?? 0));
  const leader = ranked[0];
  const laggard = ranked.at(-1);
  if (!leader || !laggard) {
    return 'Asset rotation is unavailable.';
  }
  return `${leader.label} is leading while ${laggard.label} is lagging over the selected window. This is relative performance, not verified fund-flow data.`;
}

function buildMacroOverviewSummary(
  risk: RiskAppetiteResult,
  leading: string[],
  lagging: string[],
  economicRead: ReturnType<typeof buildEconomicRead>,
) {
  const leadText = leading.length ? `${leading.join(' and ')} leading` : 'limited leadership visibility';
  const lagText = lagging.length ? `${lagging.join(' and ')} lagging` : 'laggards unavailable';
  const economicText = economicRead.summary ? ` ${economicRead.summary}` : '';
  return `${formatRiskState(risk.state)} conditions with ${leadText} and ${lagText}. ${risk.explanation}${economicText}`;
}

function buildRiskExplanation(score: number, supportive: string[], defensive: string[]) {
  if (supportive.length && !defensive.length) {
    return supportive[0];
  }
  if (defensive.length && !supportive.length) {
    return defensive[0];
  }
  if (supportive.length && defensive.length) {
    return `${supportive[0]} However, ${defensive[0].charAt(0).toLowerCase()}${defensive[0].slice(1)}`;
  }
  return score >= 55 ? 'Risk appetite is mildly constructive.' : score <= 45 ? 'Defensive assets are gaining relative ground.' : 'Cross-asset conditions are balanced.';
}

function buildGoldInterpretation(returnValue: number | null, relativeToSpy: number | null) {
  if (returnValue === null) {
    return 'Gold proxy data unavailable.';
  }
  if (relativeToSpy !== null && relativeToSpy > 2) {
    return 'Gold strength may reflect defensive demand, real-rate expectations, or dollar sensitivity.';
  }
  if (returnValue < -2) {
    return 'Gold weakness is consistent with muted defensive demand in this window.';
  }
  return 'Gold is relatively stable, suggesting no dominant defensive impulse from this proxy.';
}

function buildOilInterpretation(returnValue: number | null, relativeToSpy: number | null, spyReturn: number | null) {
  if (returnValue === null) {
    return 'Oil proxy data unavailable.';
  }
  if (returnValue > 3 && (spyReturn ?? 0) > 0 && (relativeToSpy ?? 0) < 4) {
    return 'Oil strength is consistent with firm nominal-growth expectations, but may also carry inflation sensitivity.';
  }
  if (returnValue > 3) {
    return 'Oil strength may reflect inflation or supply pressure; equity confirmation is limited.';
  }
  if (returnValue < -3) {
    return 'Oil weakness may be consistent with softer demand expectations.';
  }
  return 'Oil is stable and not a dominant macro signal in this window.';
}

function describeSpread(value: number | null) {
  if (value === null) {
    return 'not comparable with';
  }
  if (value > 2) {
    return 'outperforming';
  }
  if (value < -2) {
    return 'underperforming';
  }
  return 'roughly in line with';
}

function classifyMacroConfidence(availableAssets: number): MacroConfidence {
  if (availableAssets >= 6) {
    return 'high';
  }
  if (availableAssets >= 4) {
    return 'moderate';
  }
  if (availableAssets >= 2) {
    return 'low';
  }
  return 'unavailable';
}

function classifyRiskAppetite(score: number): RiskAppetiteState {
  if (score >= 75) {
    return 'strong_risk_on';
  }
  if (score >= 60) {
    return 'risk_on';
  }
  if (score >= 45) {
    return 'balanced';
  }
  if (score >= 30) {
    return 'defensive_rotation';
  }
  return 'risk_off';
}

export function formatRiskState(state: RiskAppetiteState | MacroRegime) {
  switch (state) {
    case 'strong_risk_on':
      return 'Strong Risk-On';
    case 'risk_on':
      return 'Risk-On';
    case 'balanced':
      return 'Balanced';
    case 'defensive_rotation':
      return 'Defensive Rotation';
    case 'risk_off':
      return 'Risk-Off';
    case 'inflationary':
      return 'Inflationary';
    case 'disinflationary':
      return 'Disinflationary';
    case 'growth_slowdown':
      return 'Growth Slowdown';
    case 'mixed':
      return 'Mixed';
    default:
      return 'Unavailable';
  }
}

export function formatMacroSourceLabel(source: MacroSourceKind) {
  switch (source) {
    case 'live':
      return 'Live proxy data';
    case 'cached':
      return 'Cached proxy data';
    case 'mock':
      return 'Mock proxy data';
    case 'fallback':
      return 'Fallback proxy data';
    case 'mixed':
      return 'Mixed sources';
    default:
      return 'Unavailable';
  }
}

function findReturn(assets: MacroAssetPerformance[], assetClass: MacroAssetClass) {
  return assets.find((asset) => asset.assetClass === assetClass)?.periodReturn ?? null;
}

function average(values: (number | null)[]) {
  const valid = values.filter((value): value is number => value !== null && Number.isFinite(value));
  if (!valid.length) {
    return null;
  }
  return valid.reduce((sum, value) => sum + value, 0) / valid.length;
}

function selectTimeframeCandles(candles: CandleData[], timeframe: MacroTimeframe) {
  return candles
    .filter(isValidCandle)
    .sort((a, b) => Date.parse(a.timestamp) - Date.parse(b.timestamp))
    .slice(-macroTimeframeSessions[timeframe]);
}

function isValidCandle(candle: CandleData) {
  const time = Date.parse(candle.timestamp);
  return Number.isFinite(time)
    && isFiniteNumber(candle.open)
    && isFiniteNumber(candle.high)
    && isFiniteNumber(candle.low)
    && isFiniteNumber(candle.close)
    && candle.high >= Math.max(candle.open, candle.close, candle.low)
    && candle.low <= Math.min(candle.open, candle.close, candle.high)
    && candle.close > 0;
}

function buildEconomicDisplayValue(value: number | null, unit: EconomicUnit): EconomicDisplayValue | null {
  if (!isFiniteNumber(value)) {
    return null;
  }
  return {
    formattedValue: formatEconomicValue(value, unit),
    rawValue: value,
  };
}

function getEconomicCardMode(indicator: EconomicIndicatorSnapshot): EconomicCardMode {
  const semantics = economicIndicatorSemantics(indicator);
  if (semantics === 'market_level') {
    return 'market_level';
  }
  if (semantics === 'policy_rate') {
    return 'policy_decision';
  }
  return 'release_surprise';
}

function economicIndicatorSemantics(indicator: EconomicIndicatorSnapshot): EconomicIndicatorSemantics {
  const key = indicator.key.toLowerCase();
  if (key.includes('yield')) {
    return 'market_level';
  }
  if (key.includes('fed_funds')) {
    return 'policy_rate';
  }
  if (key.includes('cpi') || key.includes('ppi') || key.includes('pce')) {
    return 'lower_is_cooler';
  }
  if (key.includes('unemployment')) {
    return 'lower_is_stronger';
  }
  if (key.includes('payroll') || key.includes('gdp') || key.includes('retail')) {
    return 'higher_is_stronger';
  }
  if (key.includes('earnings')) {
    return 'lower_is_cooler';
  }
  return 'neutral';
}

function economicSurpriseTolerance(indicator: EconomicIndicatorSnapshot) {
  const key = indicator.key.toLowerCase();
  if (key.includes('payroll')) {
    return 10;
  }
  if (key.includes('fed_funds')) {
    return 0.01;
  }
  if (key.includes('yield')) {
    return 0.02;
  }
  if (key.includes('unemployment')) {
    return 0.05;
  }
  if (key.includes('gdp')) {
    return 0.1;
  }
  if (key.includes('cpi') || key.includes('ppi') || key.includes('pce') || key.includes('retail')) {
    return 0.05;
  }
  return indicator.unit === 'thousands' ? 10 : 0.05;
}

function formatEconomicSurpriseValue(value: number, indicator: EconomicIndicatorSnapshot) {
  const sign = value > 0 ? '+' : value < 0 ? '-' : '';
  const abs = Math.abs(value);
  if (indicator.unit === 'thousands') {
    return `${sign}${abs.toFixed(0)}K`;
  }
  if (indicator.unit === 'basis_points') {
    return `${sign}${abs.toFixed(0)} bps`;
  }
  if (indicator.key.toLowerCase().includes('yield') || indicator.key.toLowerCase().includes('fed_funds')) {
    return `${sign}${Math.round(abs * 100)} bps`;
  }
  return `${sign}${abs.toFixed(1)} pts`;
}

function sourceLabelForEconomicIndicator(indicator: EconomicIndicatorSnapshot) {
  switch (indicator.source) {
    case 'test':
      return 'Test data';
    case 'live':
      return 'Live';
    case 'cached':
      return 'Cached';
    case 'unavailable':
      return 'Unavailable';
    default:
      return null;
  }
}

function economicIndicatorRank(key: string) {
  const normalized = key.toLowerCase();
  if (normalized.includes('cpi') && !normalized.includes('core')) {
    return 10;
  }
  if (normalized.includes('core_cpi')) {
    return 20;
  }
  if (normalized.includes('fed_funds')) {
    return 30;
  }
  if (normalized.includes('payroll')) {
    return 40;
  }
  if (normalized.includes('unemployment')) {
    return 50;
  }
  if (normalized.includes('ppi')) {
    return 60;
  }
  if (normalized.includes('pce')) {
    return 70;
  }
  if (normalized.includes('gdp')) {
    return 80;
  }
  if (normalized.includes('retail')) {
    return 90;
  }
  if (normalized.includes('ten_year')) {
    return 100;
  }
  if (normalized.includes('thirty_year')) {
    return 110;
  }
  return 999;
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

function interpretEconomicIndicator(indicator: EconomicIndicatorSnapshot, trend: string) {
  const key = indicator.key.toLowerCase();
  if (key.includes('cpi') || key.includes('ppi') || key.includes('pce')) {
    return trend.toLowerCase().includes('heating') || trend.toLowerCase().includes('sticky')
      ? 'Inflation pressure remains a macro risk.'
      : 'Inflation pressure is moderating.';
  }
  if (key.includes('fed_funds') || key.includes('yield')) {
    return trend.toLowerCase().includes('falling') || trend.toLowerCase().includes('easing')
      ? 'Rate pressure is easing.'
      : trend.toLowerCase().includes('rising') || trend.toLowerCase().includes('tightening')
        ? 'Rate pressure is rising.'
        : 'Rates are broadly stable.';
  }
  if (key.includes('payroll') || key.includes('unemployment') || key.includes('earnings')) {
    return trend.toLowerCase().includes('weak')
      ? 'Labor-market momentum is weakening.'
      : 'Labor-market conditions remain stable.';
  }
  if (key.includes('gdp') || key.includes('retail')) {
    return trend.toLowerCase().includes('slow') || trend.toLowerCase().includes('weak')
      ? 'Growth momentum is softening.'
      : 'Growth remains positive.';
  }
  return 'Macro signal available.';
}

function formatEconomicPeriod(period: EconomicPeriodType) {
  switch (period) {
    case 'month_over_month':
      return 'MoM';
    case 'year_over_year':
      return 'YoY';
    case 'quarter_over_quarter_annualized':
      return 'QoQ annualized';
    default:
      return 'Level';
  }
}

function formatReleaseDate(timestamp: string) {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  return date.toLocaleDateString('en-US', { day: 'numeric', month: 'short' });
}

function formatEventDate(timestamp: string, timezone: string) {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return timestamp;
  }
  return date.toLocaleDateString('en-US', {
    day: 'numeric',
    month: 'short',
    timeZone: timezone,
    weekday: 'short',
  });
}

function formatEventTime(timestamp: string, timezone: string) {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  const formatted = date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    timeZone: timezone,
    timeZoneName: 'short',
  });
  return formatted.replace(/\s/g, ' ');
}

function formatDateLabel(timestamp: string) {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return timestamp.slice(5, 10);
  }
  return date.toLocaleDateString('en-US', { day: 'numeric', month: 'short' });
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}
