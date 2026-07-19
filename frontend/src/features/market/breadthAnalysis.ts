import type { IndexSnapshot, MarketBreadth, MarketBreadthResponse } from '@/types/market';

export type BreadthSignalTone = 'positive' | 'warning' | 'negative' | 'neutral';
export type BreadthConfidence = 'high' | 'moderate' | 'low' | 'unavailable';
export type BreadthState = 'strong' | 'constructive' | 'mixed' | 'weak' | 'unavailable';
export type BreadthConfirmationState = 'confirmed' | 'diverging' | 'unclear' | 'unavailable';
export type DailyParticipationState = 'positive' | 'mixed' | 'negative' | 'unavailable';
export type LeadershipState = 'expanding' | 'mixed' | 'deteriorating' | 'inactive' | 'unavailable';
export type BreadthProfileMetricKey =
  | 'dailyParticipation'
  | 'leadership'
  | 'above20Ema'
  | 'above50Ema'
  | 'above200Ema'
  | 'coverage';
export type BreadthDivergenceState =
  | 'confirmed_uptrend'
  | 'bearish_divergence'
  | 'bullish_divergence'
  | 'broad_weakness'
  | 'mixed'
  | 'unavailable';

export type BreadthFactor = {
  label: string;
  score: number;
  tone: BreadthSignalTone;
  weight: number;
};

export type BreadthCompositeResult = {
  confidence: BreadthConfidence;
  factors: BreadthFactor[];
  score: number | null;
  validWeight: number;
};

export type AdvanceDeclineViewModel = {
  advancing: number | null;
  advancingPercent: number | null;
  declining: number | null;
  decliningPercent: number | null;
  interpretation: string;
  ratio: number | null;
  ratioDisplay: string;
  state: 'Positive' | 'Mixed' | 'Negative' | 'Unavailable';
  stateKey: DailyParticipationState;
  tone: BreadthSignalTone;
  total: number | null;
  unchanged: number | null;
  unchangedPercent: number | null;
};

export type HighLowViewModel = {
  differential: number | null;
  highPercent: number | null;
  highs: number | null;
  interpretation: string;
  lowPercent: number | null;
  lows: number | null;
  ratioLabel: string;
  showDetails: boolean;
  state: 'Expanding' | 'Mixed' | 'Deteriorating' | 'Inactive' | 'Unavailable';
  stateKey: LeadershipState;
  tone: BreadthSignalTone;
};

export type MovingAverageBreadthViewModel = {
  interpretation: string;
  items: { key: '20' | '50' | '200'; label: string; value: number | null; tone: BreadthSignalTone }[];
  summary: string;
  state: string;
  tone: BreadthSignalTone;
};

export type BreadthQualityViewModel = {
  confidence: BreadthConfidence;
  confidenceLabel: string;
  signalConfidenceLabel?: string;
  signalConfidenceReason?: string | null;
  signalConfidenceSource?: string | null;
  coveragePercent: number | null;
  universeCoverageLabel?: string | null;
  ema200EligibilityLabel?: string | null;
  expectedUniverse: number | null;
  limitation: string;
  sourceLabel: string;
  strengthLabel: string;
  trackedStocks: number | null;
};

export type BreadthDivergenceViewModel = {
  confidence: BreadthConfidence;
  confirmationLabel: string;
  confirmationState: BreadthConfirmationState;
  confirmationScore: number | null;
  explanation: string;
  riskDirection: string;
  state: BreadthDivergenceState;
  stateLabel: string;
  tone: BreadthSignalTone;
};

export type BreadthOverviewViewModel = {
  interpretation: string;
  score: number | null;
  state: BreadthState;
  status: string;
  tone: BreadthSignalTone;
};

export type BreadthProfileMetric = {
  key: BreadthProfileMetricKey;
  label: string;
  status: string;
  tone: BreadthSignalTone;
  value: number | null;
};

export type BreadthTakeawayViewModel = {
  conclusion: string;
  confirmation: string;
  monitor: string;
  risk: string;
  supports: string;
  tone: BreadthSignalTone;
};

export type BreadthDashboardViewModel = {
  advanceDecline: AdvanceDeclineViewModel;
  composite: BreadthCompositeResult;
  divergence: BreadthDivergenceViewModel;
  highLow: HighLowViewModel;
  movingAverageProfile: MovingAverageBreadthViewModel;
  overview: BreadthOverviewViewModel;
  profile: BreadthProfileMetric[];
  quality: BreadthQualityViewModel;
  riskLabel: string;
  takeaway: BreadthTakeawayViewModel;
};

const COMPOSITE_WEIGHTS = [
  { key: 'advanceDecline', label: 'Advance/Decline participation', weight: 0.2 },
  { key: 'above20', label: 'Above 20 EMA', weight: 0.2 },
  { key: 'above50', label: 'Above 50 EMA', weight: 0.25 },
  { key: 'above200', label: 'Above 200 EMA', weight: 0.2 },
  { key: 'highLow', label: 'New highs vs lows', weight: 0.15 },
] as const;

export function buildBreadthDashboard(breadth: MarketBreadthResponse | null, indexes: IndexSnapshot[] = []): BreadthDashboardViewModel {
  const market = breadth?.market ?? null;
  const advanceDecline = deriveAdvanceDeclineState(market);
  const highLow = deriveHighLowState(market);
  const movingAverageProfile = deriveMovingAverageBreadthProfile(market);
  const quality = deriveBreadthQuality(market);
  const composite = calculateBreadthComposite(market, quality.confidence);
  const divergence = classifyCurrentBreadthConfirmation(market, composite, indexes, quality.confidence);
  const profile = buildBreadthProfile(advanceDecline, highLow, movingAverageProfile, quality);
  const overview = buildBreadthOverview(composite, advanceDecline, highLow, movingAverageProfile, quality, divergence);
  const takeaway = buildBreadthTakeaway(composite, advanceDecline, highLow, movingAverageProfile, quality, divergence);
  return {
    advanceDecline,
    composite,
    divergence,
    highLow,
    movingAverageProfile,
    overview,
    profile,
    quality,
    riskLabel: takeaway.risk,
    takeaway,
  };
}

// Composite weights follow the v1 breadth dashboard contract and are redistributed across valid inputs only.
export function calculateBreadthComposite(market: MarketBreadth | null, confidence: BreadthConfidence = 'unavailable'): BreadthCompositeResult {
  if (!market) {
    return { confidence, factors: [], score: null, validWeight: 0 };
  }
  const inputScores = {
    advanceDecline: calculateAdvanceDeclineScore(market),
    above20: validPercent(market.percent_above_20ema),
    above50: validPercent(market.percent_above_50ema),
    above200: validPercent(market.percent_above_200ema),
    highLow: calculateHighLowScore(market),
  };
  const factors: BreadthFactor[] = COMPOSITE_WEIGHTS
    .map((item): BreadthFactor | null => {
      const score = inputScores[item.key];
      return score === null ? null : {
        label: item.label,
        score,
        tone: toneForScore(score),
        weight: item.weight,
      };
    })
    .filter((factor): factor is BreadthFactor => factor !== null);
  const validWeight = factors.reduce((sum, factor) => sum + factor.weight, 0);
  const score = validWeight > 0
    ? factors.reduce((sum, factor) => sum + factor.score * factor.weight, 0) / validWeight
    : null;
  return {
    confidence,
    factors,
    score: score === null ? null : clamp(score, 0, 100),
    validWeight,
  };
}

export function calculateAdvanceDeclineScore(market: MarketBreadth | null) {
  const state = deriveAdvanceDeclineState(market);
  return state.advancingPercent;
}

export function deriveAdvanceDeclineState(market: MarketBreadth | null): AdvanceDeclineViewModel {
  if (!market) {
    return emptyAdvanceDecline();
  }
  const advancing = validCount(market.advancing_stocks);
  const declining = validCount(market.declining_stocks);
  const unchanged = validCount(market.unchanged_stocks) ?? 0;
  const total = validCount(market.total_stocks) ?? sumValid(advancing, declining, unchanged);
  if (!total || advancing === null || declining === null) {
    return emptyAdvanceDecline();
  }
  const advancingPercent = (advancing / total) * 100;
  const decliningPercent = (declining / total) * 100;
  const unchangedPercent = (unchanged / total) * 100;
  const ratio = market.advance_decline_ratio ?? (declining > 0 ? advancing / declining : advancing > 0 ? null : 0);
  const ratioDisplay = market.advance_decline_ratio_display
    ?? (declining === 0 && advancing > 0 ? 'No decliners' : formatBreadthRatio(ratio));
  const net = advancingPercent - decliningPercent;
  const state = net >= 10 ? 'Positive'
    : net <= -10 ? 'Negative'
    : 'Mixed';
  const tone = state === 'Positive' ? 'positive' : state === 'Negative' ? 'negative' : 'neutral';
  return {
    advancing,
    advancingPercent,
    declining,
    decliningPercent,
    interpretation: buildAdvanceDeclineInterpretation(state, advancing, declining, unchanged),
    ratio,
    ratioDisplay,
    state,
    stateKey: state.toLowerCase() as DailyParticipationState,
    tone,
    total,
    unchanged,
    unchangedPercent,
  };
}

export function calculateHighLowScore(market: MarketBreadth | null) {
  const highLow = deriveHighLowState(market);
  if (highLow.highs === null || highLow.lows === null) {
    return null;
  }
  const denominator = highLow.highs + highLow.lows;
  if (denominator <= 0) {
    return 50;
  }
  return clamp((highLow.highs / denominator) * 100, 0, 100);
}

export function deriveHighLowState(market: MarketBreadth | null): HighLowViewModel {
  if (!market) {
    return emptyHighLow();
  }
  const highs = validCount(market.new_52w_highs);
  const lows = validCount(market.new_52w_lows);
  const total = validCount(market.total_stocks);
  if (highs === null || lows === null) {
    return emptyHighLow();
  }
  const differential = highs - lows;
  const denominator = highs + lows;
  const highPercent = denominator > 0 ? (highs / denominator) * 100 : null;
  const lowPercent = denominator > 0 ? (lows / denominator) * 100 : null;
  const highRate = total ? (highs / total) * 100 : null;
  const lowRate = total ? (lows / total) * 100 : null;
  const ratioLabel = formatHighLowRatio(highs, lows);
  const state = highs === 0 && lows === 0 ? 'Inactive'
    : differential >= 15 || (highRate !== null && highRate >= 8 && highs > lows * 2) || differential > 0 ? 'Expanding'
    : lows > highs * 2 || (lowRate !== null && lowRate >= 8) || differential < 0 ? 'Deteriorating'
    : 'Mixed';
  const tone = state === 'Expanding'
    ? 'positive'
    : state === 'Deteriorating'
      ? 'negative'
      : 'neutral';
  const inactive = state === 'Inactive';
  return {
    differential: inactive ? null : differential,
    highPercent: inactive ? null : highPercent,
    highs,
    interpretation: buildHighLowInterpretation(state, market),
    lowPercent: inactive ? null : lowPercent,
    lows,
    ratioLabel: inactive ? 'No leadership signal' : ratioLabel,
    showDetails: !inactive,
    state,
    stateKey: state.toLowerCase() as LeadershipState,
    tone,
  };
}

export function deriveMovingAverageBreadthProfile(market: MarketBreadth | null): MovingAverageBreadthViewModel {
  const items = [
    { key: '20' as const, label: '20 EMA', value: validPercent(market?.percent_above_20ema) },
    { key: '50' as const, label: '50 EMA', value: validPercent(market?.percent_above_50ema) },
    { key: '200' as const, label: '200 EMA', value: validPercent(market?.percent_above_200ema) },
  ].map((item) => ({
    ...item,
    tone: item.value === null ? 'neutral' as const : toneForScore(item.value),
  }));
  const values = items.map((item) => item.value).filter((value): value is number => value !== null);
  if (!values.length) {
    return { interpretation: 'Moving-average breadth is unavailable.', items, state: 'Unavailable', summary: 'Breadth profile unavailable', tone: 'neutral' };
  }
  const [above20, above50, above200] = items.map((item) => item.value);
  const average = values.reduce((sum, value) => sum + value, 0) / values.length;
  if (values.every((value) => value >= 70)) {
    return { interpretation: 'Participation is strong across short-, medium-, and long-term breadth.', items, state: 'Strong', summary: 'Fully aligned across all horizons', tone: 'positive' };
  }
  if (above20 !== null && above50 !== null && above200 !== null && above20 > above50 && above50 > above200) {
    return { interpretation: 'Short-term participation is expanding ahead of longer-term breadth.', items, state: 'Constructive', summary: 'Short-term breadth improving', tone: 'positive' };
  }
  if (above20 !== null && above50 !== null && above200 !== null && above20 < above50 && above50 < above200) {
    return { interpretation: 'Short-term breadth is weakening below medium- and long-term participation.', items, state: 'Weakening', summary: 'Short-term breadth weakening', tone: 'warning' };
  }
  if ((above20 ?? 100) < 45 && (above200 ?? 0) >= 60) {
    return { interpretation: 'Short-term breadth is weak while longer-term structure remains healthier.', items, state: 'Mixed', summary: 'Structural breadth remains healthier', tone: 'warning' };
  }
  return {
    interpretation: average >= 60 ? 'Moving-average breadth remains constructive.' : 'Moving-average breadth is mixed and needs confirmation.',
    items,
    state: average >= 60 ? 'Constructive' : 'Mixed',
    summary: average >= 60 ? 'Structural breadth remains healthy' : 'Mixed breadth profile',
    tone: average >= 60 ? 'positive' : 'warning',
  };
}

export function deriveBreadthQuality(market: MarketBreadth | null): BreadthQualityViewModel {
  const trackedStocks = validCount(market?.successful_symbols) ?? validCount(market?.total_stocks);
  const expectedUniverse = validCount(market?.universe_size) ?? validCount(market?.total_stocks);
  const coveragePercent = validPercent(market?.coverage_percent)
    ?? (trackedStocks !== null && expectedUniverse ? (trackedStocks / expectedUniverse) * 100 : null);
  const confidence = classifyBreadthConfidence(coveragePercent);
  const dimensions = market?.coverage_dimensions ?? null;
  const universe = dimensions?.universe ?? null;
  const ema200 = dimensions?.ema200 ?? null;
  const dataLabel = market?.data_confidence?.label ?? null;
  const signalLabel = market?.signal_confidence?.label ?? null;
  const signalScore = validNumber(market?.signal_confidence?.score);
  const signalReason = market?.signal_confidence?.reason
    ?? 'Insufficient historical breadth snapshots';
  const signalConfidenceLabel = signalLabel && signalLabel !== 'Unavailable'
    ? `${signalLabel}${signalScore !== null ? ` · ${Math.round(signalScore)}` : ''}`
    : `Unavailable — ${signalReason}`;
  const sourceLabel = getBreadthSourceLabel(market);
  const strengthLabel = market?.breadth_status && market.breadth_status !== 'N/A'
    ? market.breadth_status
    : labelForScore(market?.breadth_score ?? null);
  return {
    confidence,
    confidenceLabel: dataLabel ? `${dataLabel} Data Confidence` : confidence === 'unavailable' ? 'Unavailable' : `${capitalize(confidence)} Data Confidence`,
    signalConfidenceLabel,
    signalConfidenceReason: signalReason,
    signalConfidenceSource: market?.signal_confidence?.source_snapshot_id
      ? `Snapshot ${market.signal_confidence.source_snapshot_id}${market.signal_confidence.calculated_at ? ` · calculated ${market.signal_confidence.calculated_at}` : ''}`
      : null,
    coveragePercent,
    universeCoverageLabel: universe?.display ?? (trackedStocks !== null && expectedUniverse !== null ? `${trackedStocks}/${expectedUniverse}` : null),
    ema200EligibilityLabel: ema200?.display ?? null,
    expectedUniverse,
    limitation: buildQualityLimitation(confidence),
    sourceLabel,
    strengthLabel,
    trackedStocks,
  };
}

export function classifyBreadthConfidence(coverage: number | null | undefined): BreadthConfidence {
  if (coverage === null || coverage === undefined || !Number.isFinite(coverage)) {
    return 'unavailable';
  }
  if (coverage >= 70) {
    return 'high';
  }
  if (coverage >= 40) {
    return 'moderate';
  }
  return 'low';
}

export function classifyCurrentBreadthConfirmation(
  market: MarketBreadth | null,
  composite: BreadthCompositeResult,
  indexes: IndexSnapshot[],
  confidence: BreadthConfidence,
): BreadthDivergenceViewModel {
  const spy = indexes.find((index) => index.symbol === 'SPY');
  const spyReturn = validNumber(spy?.change_percent);
  const score = composite.score;
  if (score === null || spyReturn === null) {
    return {
      confidence,
      confirmationScore: score,
      explanation: 'Breadth confirmation history unavailable.',
      riskDirection: 'Unavailable',
      state: 'unavailable',
      stateLabel: 'Unavailable',
      confirmationLabel: 'Unavailable',
      confirmationState: 'unavailable',
      tone: 'neutral',
    };
  }
  const dailyWeak = deriveAdvanceDeclineState(market).tone === 'negative';
  const structuralStrong = score >= 65;
  const state: BreadthDivergenceState = spyReturn > 0.5 && score < 50
    ? 'bearish_divergence'
    : spyReturn < -0.5 && score > 60
      ? 'bullish_divergence'
      : spyReturn > 0 && structuralStrong && !dailyWeak
        ? 'confirmed_uptrend'
        : spyReturn < 0 && score < 45
          ? 'broad_weakness'
          : 'mixed';
  return buildDivergenceViewModel(state, score, confidence);
}

export function buildBreadthOverview(
  composite: BreadthCompositeResult,
  advanceDecline: AdvanceDeclineViewModel,
  highLow: HighLowViewModel,
  movingAverage: MovingAverageBreadthViewModel,
  quality: BreadthQualityViewModel,
  divergence: BreadthDivergenceViewModel,
): BreadthOverviewViewModel {
  const status = divergence.state !== 'unavailable' && divergence.state !== 'mixed'
    ? labelForScore(composite.score)
    : composite.score !== null
      ? labelForScore(composite.score)
      : 'Unavailable';
  const caveat = quality.confidence === 'low' ? ' Limited coverage reduces confidence.' : '';
  const daily = advanceDecline.tone === 'negative'
    ? 'negative daily participation'
    : advanceDecline.tone === 'positive'
      ? 'positive daily participation'
      : 'mixed daily participation';
  const interpretation = `${movingAverage.summary}, with ${daily}.${caveat}`;
  return {
    interpretation,
    score: composite.score,
    state: scoreToBreadthState(composite.score),
    status,
    tone: divergence.tone !== 'neutral' ? divergence.tone : composite.score === null ? 'neutral' : toneForScore(composite.score),
  };
}

export function buildBreadthTakeaway(
  composite: BreadthCompositeResult,
  advanceDecline: AdvanceDeclineViewModel,
  highLow: HighLowViewModel,
  movingAverage: MovingAverageBreadthViewModel,
  quality: BreadthQualityViewModel,
  divergence: BreadthDivergenceViewModel,
): BreadthTakeawayViewModel {
  const supports = movingAverage.tone === 'positive'
    ? movingAverage.state
    : highLow.tone === 'positive'
      ? highLow.state
      : composite.score !== null ? `${labelForScore(composite.score)} composite breadth` : 'Breadth data unavailable';
  const monitorParts = [
    advanceDecline.tone === 'negative' ? 'negative daily participation' : null,
    highLow.tone === 'negative' ? 'new lows pressure' : null,
    quality.confidence === 'low' ? 'low coverage' : null,
  ].filter((value): value is string => Boolean(value));
  const monitor = monitorParts.length ? joinPhrase(monitorParts) : 'confirmation against SPY';
  const conclusion = divergence.state === 'bearish_divergence'
    ? 'SPY strength is not fully confirmed by participation, so confirmation risk is rising.'
    : divergence.state === 'bullish_divergence'
      ? 'Participation is improving while SPY remains weak, suggesting internal stabilization.'
      : divergence.state === 'confirmed_uptrend'
        ? 'Price action is supported by constructive participation across the tracked universe.'
        : `${movingAverage.summary}, but ${monitor} reduces confidence in the signal.`;
  return {
    conclusion,
    confirmation: divergence.confirmationLabel,
    monitor,
    risk: deriveRiskLabel(divergence, advanceDecline, quality),
    supports,
    tone: divergence.tone,
  };
}

export function buildBreadthProfile(
  advanceDecline: AdvanceDeclineViewModel,
  highLow: HighLowViewModel,
  movingAverage: MovingAverageBreadthViewModel,
  quality: BreadthQualityViewModel,
): BreadthProfileMetric[] {
  const [above20, above50, above200] = movingAverage.items;
  return [
    {
      key: 'dailyParticipation',
      label: 'Daily Participation',
      status: advanceDecline.state,
      tone: advanceDecline.tone,
      value: advanceDecline.advancingPercent,
    },
    {
      key: 'leadership',
      label: 'Leadership',
      status: highLow.state,
      tone: highLow.tone,
      value: highLow.highPercent,
    },
    {
      key: 'above20Ema',
      label: 'Above 20 EMA',
      status: above20?.value === null ? 'Unavailable' : `${formatBreadthPercent(above20?.value ?? null)} above`,
      tone: above20?.tone ?? 'neutral',
      value: above20?.value ?? null,
    },
    {
      key: 'above50Ema',
      label: 'Above 50 EMA',
      status: above50?.value === null ? 'Unavailable' : `${formatBreadthPercent(above50?.value ?? null)} above`,
      tone: above50?.tone ?? 'neutral',
      value: above50?.value ?? null,
    },
    {
      key: 'above200Ema',
      label: 'Above 200 EMA',
      status: above200?.value === null ? 'Unavailable' : `${formatBreadthPercent(above200?.value ?? null)} above`,
      tone: above200?.tone ?? 'neutral',
      value: above200?.value ?? null,
    },
    {
      key: 'coverage',
      label: 'Coverage',
      status: quality.confidenceLabel,
      tone: quality.confidence === 'high' ? 'positive' : quality.confidence === 'moderate' ? 'warning' : 'warning',
      value: quality.coveragePercent,
    },
  ];
}

export function formatHighLowRatio(highs: number, lows: number) {
  if (lows === 0) {
    return highs > 0 ? 'Highs dominant' : 'No new highs or lows';
  }
  return `${(highs / lows).toFixed(1)}×`;
}

export function formatBreadthRatio(value: number | null) {
  return value === null || !Number.isFinite(value) ? 'N/A' : `${value.toFixed(2)}×`;
}

function buildDivergenceViewModel(
  state: BreadthDivergenceState,
  confirmationScore: number,
  confidence: BreadthConfidence,
): BreadthDivergenceViewModel {
  switch (state) {
    case 'confirmed_uptrend':
      return {
        confirmationLabel: 'Confirmed',
        confirmationState: 'confirmed',
        confidence,
        confirmationScore,
        explanation: 'SPY price action is supported by constructive internal participation.',
        riskDirection: confidence === 'low' ? 'Moderately Elevated' : 'Stable',
        state,
        stateLabel: 'Confirmed',
        tone: 'positive',
      };
    case 'bearish_divergence':
      return {
        confirmationLabel: 'Diverging',
        confirmationState: 'diverging',
        confidence,
        confirmationScore,
        explanation: 'SPY is stronger than the Breadth Composite, indicating narrowing participation beneath the index move.',
        riskDirection: 'Elevated',
        state,
        stateLabel: 'Diverging',
        tone: 'warning',
      };
    case 'bullish_divergence':
      return {
        confirmationLabel: 'Diverging',
        confirmationState: 'diverging',
        confidence,
        confirmationScore,
        explanation: 'Internal participation is firmer than SPY price action, suggesting participation is stabilizing first.',
        riskDirection: 'Stabilizing',
        state,
        stateLabel: 'Diverging',
        tone: 'positive',
      };
    case 'broad_weakness':
      return {
        confirmationLabel: 'Confirmed',
        confirmationState: 'confirmed',
        confidence,
        confirmationScore,
        explanation: 'SPY weakness is confirmed by weak internal participation.',
        riskDirection: 'Elevated',
        state,
        stateLabel: 'Confirmed',
        tone: 'negative',
      };
    case 'mixed':
      return {
        confirmationLabel: 'Unclear',
        confirmationState: 'unclear',
        confidence,
        confirmationScore,
        explanation: 'Price and breadth signals are mixed, with no clear divergence from current data.',
        riskDirection: confidence === 'low' ? 'Moderately Elevated' : 'Neutral',
        state,
        stateLabel: 'Unclear',
        tone: 'neutral',
      };
    default:
      return {
        confirmationLabel: 'Unavailable',
        confirmationState: 'unavailable',
        confidence,
        confirmationScore,
        explanation: 'Breadth confirmation history unavailable.',
        riskDirection: 'Unavailable',
        state: 'unavailable',
        stateLabel: 'Unavailable',
        tone: 'neutral',
      };
  }
}

function buildAdvanceDeclineInterpretation(state: AdvanceDeclineViewModel['state'], advancing: number, declining: number, unchanged: number) {
  if (state === 'Unavailable') {
    return 'Daily participation is unavailable.';
  }
  return `${advancing} advancing, ${declining} declining, and ${unchanged} unchanged stocks point to ${state.toLowerCase()} participation.`;
}

function buildHighLowInterpretation(state: HighLowViewModel['state'], market: MarketBreadth | null) {
  switch (state) {
    case 'Expanding':
      return (market?.advancing_stocks ?? 0) < (market?.declining_stocks ?? 0)
        ? 'New highs exceed new lows, but daily participation remains weak.'
        : 'New highs exceed new lows, indicating leadership expansion.';
    case 'Deteriorating':
      return 'New lows are gaining relative to new highs, showing internal deterioration.';
    case 'Inactive':
      return 'No tracked stocks recorded a new 52-week high or low.';
    case 'Unavailable':
      return 'New high/new low data is unavailable.';
    default:
      return 'New highs and new lows are mixed.';
  }
}

function buildQualityLimitation(confidence: BreadthConfidence) {
  switch (confidence) {
    case 'high':
      return 'Coverage is sufficient for a higher-confidence tracked-universe read.';
    case 'moderate':
      return 'Coverage is usable, but not complete enough for full-market breadth claims.';
    case 'low':
      return 'Limited coverage reduces confidence in broad-market representation.';
    default:
      return 'Coverage is unavailable, so confidence is limited.';
  }
}

function getBreadthSourceLabel(market: MarketBreadth | null) {
  const source = `${market?.overall_mode ?? market?.data_source ?? ''}`.toLowerCase();
  if (source.includes('mock')) {
    return 'Mock Data';
  }
  if (source.includes('live')) {
    return 'Live Data';
  }
  if (source.includes('mixed')) {
    return 'Mixed Data';
  }
  if (source.includes('cached')) {
    return 'Cached Data';
  }
  return source ? `${capitalize(source)} Data` : 'Source Unavailable';
}

function emptyAdvanceDecline(): AdvanceDeclineViewModel {
  return {
    advancing: null,
    advancingPercent: null,
    declining: null,
    decliningPercent: null,
    interpretation: 'Daily participation is unavailable.',
    ratio: null,
    ratioDisplay: 'N/A',
    state: 'Unavailable',
    stateKey: 'unavailable',
    tone: 'neutral',
    total: null,
    unchanged: null,
    unchangedPercent: null,
  };
}

function emptyHighLow(): HighLowViewModel {
  return {
    differential: null,
    highPercent: null,
    highs: null,
    interpretation: 'New high/new low data is unavailable.',
    lowPercent: null,
    lows: null,
    ratioLabel: 'N/A',
    showDetails: false,
    state: 'Unavailable',
    stateKey: 'unavailable',
    tone: 'neutral',
  };
}

function validNumber(value: number | null | undefined) {
  return value === null || value === undefined || !Number.isFinite(value) ? null : value;
}

function validCount(value: number | null | undefined) {
  const number = validNumber(value);
  return number === null || number < 0 ? null : number;
}

function validPercent(value: number | null | undefined) {
  const number = validNumber(value);
  return number === null ? null : clamp(number, 0, 100);
}

function sumValid(...values: (number | null)[]) {
  const valid = values.filter((value): value is number => value !== null);
  return valid.length ? valid.reduce((sum, value) => sum + value, 0) : null;
}

function toneForScore(score: number): BreadthSignalTone {
  if (score >= 65) {
    return 'positive';
  }
  if (score >= 45) {
    return 'neutral';
  }
  if (score >= 30) {
    return 'warning';
  }
  return 'negative';
}

function labelForScore(score: number | null) {
  if (score === null || !Number.isFinite(score)) {
    return 'Unavailable';
  }
  if (score >= 75) {
    return 'Strong';
  }
  if (score >= 60) {
    return 'Constructive';
  }
  if (score >= 45) {
    return 'Mixed';
  }
  return 'Weak';
}

function scoreToBreadthState(score: number | null): BreadthState {
  const label = labelForScore(score);
  switch (label) {
    case 'Strong':
      return 'strong';
    case 'Constructive':
      return 'constructive';
    case 'Mixed':
      return 'mixed';
    case 'Weak':
      return 'weak';
    default:
      return 'unavailable';
  }
}

function deriveRiskLabel(
  divergence: BreadthDivergenceViewModel,
  advanceDecline: AdvanceDeclineViewModel,
  quality: BreadthQualityViewModel,
) {
  if (divergence.tone === 'negative') {
    return 'Elevated';
  }
  if (divergence.tone === 'warning' || advanceDecline.tone === 'negative' || quality.confidence === 'low') {
    return 'Moderately Elevated';
  }
  if (divergence.tone === 'positive') {
    return 'Stable';
  }
  return 'Neutral';
}

export function formatBreadthPercent(value: number | null) {
  if (value === null || !Number.isFinite(value)) {
    return 'N/A';
  }
  const rounded = Math.round(value * 10) / 10;
  return Number.isInteger(rounded) ? `${rounded.toFixed(0)}%` : `${rounded.toFixed(1)}%`;
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

function capitalize(value: string) {
  return `${value.charAt(0).toUpperCase()}${value.slice(1)}`;
}

function joinPhrase(items: string[]) {
  if (items.length <= 1) {
    return items[0] ?? '';
  }
  if (items.length === 2) {
    return `${items[0]} and ${items[1]}`;
  }
  return `${items.slice(0, -1).join(', ')}, and ${items.at(-1)}`;
}
