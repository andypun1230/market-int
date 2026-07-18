import type { AnalysisDataQuality, RiskPlan, SupportResistanceResponse } from '@/types/market';
import type { CurrentPriceSelection } from '@/features/stock-detail/currentPrice';

export type RiskPlanTrustState =
  | 'current_compatible'
  | 'test_compatible'
  | 'historical'
  | 'source_incompatible'
  | 'stale'
  | 'mock'
  | 'partial'
  | 'unavailable';

export type RiskPlanTrustAssessment = {
  state: RiskPlanTrustState;
  isCurrent: boolean;
  isCompatible: boolean;
  shouldLeadRiskTab: boolean;
  shouldShowPositionSizing: boolean;
  shouldShowRiskReward: boolean;
  userLabel: string;
  explanation: string | null;
};

export type RiskLevelItem = {
  key: string;
  label: string;
  value: number;
  role: 'current' | 'confirmation' | 'target' | 'support' | 'invalidation' | 'volatility';
  description: string;
};

export type RewardInterpretation = {
  key: string;
  label: string;
  target: number;
  rewardPercent: number;
  ratio: number;
  quality: 'unfavorable' | 'limited' | 'balanced' | 'favorable' | 'strong';
  interpretation: string;
};

export type RiskFactor = {
  key: string;
  label: string;
  tone: 'success' | 'warning' | 'danger' | 'neutral';
  detail: string;
};

export type PositionGuidance = {
  state: 'standard' | 'reduced' | 'conservative' | 'unavailable';
  label: string;
  explanation: string;
};

export type ModeledRisk = 'low' | 'moderate' | 'high' | 'very_high' | 'unavailable';
export type RiskDataTrust = 'test_compatible' | 'current_compatible' | 'partial' | 'stale' | 'incompatible' | 'unavailable';
export type SetupConfirmation = 'confirmed' | 'awaiting_confirmation' | 'failed' | 'unavailable';
export type RiskVolatility = 'low' | 'moderate' | 'high' | 'unavailable';

export type RiskDecisionContext = {
  modeledRisk: ModeledRisk;
  dataTrust: RiskDataTrust;
  setupConfirmation: SetupConfirmation;
  volatility: RiskVolatility;
  downsidePercent: number | null;
};

export type RiskDashboardModel = {
  trust: RiskPlanTrustAssessment;
  decisionContext: RiskDecisionContext;
  headline: string;
  summary: string;
  riskLevel: string | null;
  riskPercent: number | null;
  downsidePercent: number | null;
  currentPrice: number | null;
  currentPriceSource: string;
  invalidationLevel: number | null;
  confirmationLevel: number | null;
  supportLevel: number | null;
  volatilityLevel: string | null;
  atr14: number | null;
  riskLevels: RiskLevelItem[];
  rewards: RewardInterpretation[];
  factors: RiskFactor[];
  positionGuidance: PositionGuidance;
  illustrativeLevels: RiskLevelItem[];
  supportingMetrics: { label: string; value: string }[];
};

type BuildRiskDashboardInput = {
  currentPrice?: CurrentPriceSelection | null;
  riskPlan?: RiskPlan | null;
  supportResistance?: SupportResistanceResponse | null;
};

export function buildRiskDashboard({
  currentPrice: selectedCurrentPrice,
  riskPlan,
  supportResistance,
}: BuildRiskDashboardInput): RiskDashboardModel {
  const trust = assessRiskPlanTrust(riskPlan, supportResistance);
  const currentPrice = numberOrNull(selectedCurrentPrice?.price)
    ?? numberOrNull(riskPlan?.current_price ?? supportResistance?.current_price);
  const confirmationLevel = numberOrNull(supportResistance?.breakout_level)
    ?? (trust.shouldLeadRiskTab ? numberOrNull(riskPlan?.entry) : null);
  const invalidationLevel = numberOrNull(supportResistance?.stop_reference)
    ?? (trust.shouldLeadRiskTab ? numberOrNull(riskPlan?.stop_loss) : null);
  const supportLevel = getPrimarySupport(supportResistance) ?? (trust.shouldLeadRiskTab ? invalidationLevel : null);
  const target1 = trust.shouldShowRiskReward ? numberOrNull(riskPlan?.target_1) : null;
  const target2 = trust.shouldShowRiskReward ? numberOrNull(riskPlan?.target_2) : null;
  const currentRiskLevels = trust.shouldLeadRiskTab
    ? buildCurrentRiskLevels({
        confirmationLevel,
        currentPrice,
        currentPriceSource: selectedCurrentPrice?.sourceLabel ?? 'Reference',
        invalidationLevel,
        supportLevel,
        target1,
        target2,
      })
    : [];
  const downsidePercent = calculateDownsidePercent(currentPrice, invalidationLevel);
  const rewards = trust.shouldShowRiskReward
    ? buildRewardInterpretations({ currentPrice, invalidationLevel, target1, target2 })
    : [];
  const riskLevel = riskPlan?.risk_level ?? null;
  const riskPercent = downsidePercent ?? numberOrNull(riskPlan?.risk_percent);
  const volatilityLevel = riskPlan?.volatility_level ?? null;
  const decisionContext = buildDecisionContext({
    confirmationLevel,
    currentPrice,
    downsidePercent,
    riskLevel,
    trust,
    volatilityLevel,
  });
  const factors = buildRiskFactors({
    confirmationLevel,
    currentPrice,
    decisionContext,
    downsidePercent,
    supportLevel,
    trust,
  });
  const positionGuidance = buildPositionGuidance({
    decisionContext,
    rewards,
  });
  const headline = buildHeadline(trust, riskLevel);
  const summary = buildSummary({
    confirmationLevel,
    currentPrice,
    decisionContext,
    downsidePercent,
    invalidationLevel,
    rewards,
    supportLevel,
    trust,
    volatilityLevel,
  });

  return {
    atr14: numberOrNull(riskPlan?.atr_14),
    confirmationLevel,
    currentPrice,
    currentPriceSource: selectedCurrentPrice?.sourceLabel ?? 'Reference',
    decisionContext,
    downsidePercent,
    factors,
    headline,
    illustrativeLevels: buildIllustrativeLevels(riskPlan, trust),
    invalidationLevel,
    positionGuidance,
    rewards,
    riskLevel,
    riskLevels: currentRiskLevels,
    riskPercent,
    summary,
    supportLevel,
    supportingMetrics: buildSupportingMetrics(riskPlan, trust, supportResistance),
    trust,
    volatilityLevel,
  };
}

export function assessRiskPlanTrust(
  riskPlan?: RiskPlan | null,
  supportResistance?: SupportResistanceResponse | null,
): RiskPlanTrustAssessment {
  if (!riskPlan) {
    return {
      explanation: 'Risk calculations are unavailable for this stock.',
      isCompatible: false,
      isCurrent: false,
      shouldLeadRiskTab: false,
      shouldShowPositionSizing: false,
      shouldShowRiskReward: false,
      state: 'unavailable',
      userLabel: 'Risk unavailable',
    };
  }

  const dataQuality = riskPlan.data_quality;
  const hasCurrentLevels = hasUsableCurrentLevels(riskPlan, supportResistance);
  const haystack = buildSourceHaystack(dataQuality, supportResistance);
  const hasFallback = Boolean(supportResistance?.fallback_used || dataQuality?.fallback_dependencies?.length || dataQuality?.fallback_components?.length);
  const isStale = haystack.includes('stale');
  const isTest = haystack.includes('generated_test_data') || haystack.includes('test_provider') || haystack.includes(' test') || haystack === 'test';
  const isMock = haystack.includes('mock');
  const isHistorical = haystack.includes('historical');
  const isLive = Boolean(
    supportResistance?.is_live
      || supportResistance?.analysis_is_live
      || supportResistance?.history_is_live
      || dataQuality?.overall_mode === 'live',
  );
  const isMixed = dataQuality?.overall_mode === 'mixed';

  if (isStale) {
    return {
      explanation: 'Risk levels are stale, so they should be treated as reference context rather than current guidance.',
      isCompatible: false,
      isCurrent: false,
      shouldLeadRiskTab: false,
      shouldShowPositionSizing: false,
      shouldShowRiskReward: false,
      state: 'stale',
      userLabel: 'Stale risk data',
    };
  }

  if (hasFallback) {
    return {
      explanation: 'Some inputs came from fallback history. Current sizing and reward calculations are withheld until compatible levels are available.',
      isCompatible: false,
      isCurrent: false,
      shouldLeadRiskTab: false,
      shouldShowPositionSizing: false,
      shouldShowRiskReward: false,
      state: 'source_incompatible',
      userLabel: 'Fallback risk context',
    };
  }

  if (isTest && hasCurrentLevels) {
    return {
      explanation: 'Generated Test Data is internally compatible for this screen. Treat it as a scenario, not live trading guidance.',
      isCompatible: true,
      isCurrent: true,
      shouldLeadRiskTab: true,
      shouldShowPositionSizing: true,
      shouldShowRiskReward: true,
      state: 'test_compatible',
      userLabel: 'Test-compatible risk',
    };
  }

  if (isMock) {
    return {
      explanation: 'The available entry, stop, and target levels are mock context and are shown only as an illustrative example.',
      isCompatible: false,
      isCurrent: false,
      shouldLeadRiskTab: false,
      shouldShowPositionSizing: false,
      shouldShowRiskReward: false,
      state: 'mock',
      userLabel: 'Mock risk context',
    };
  }

  if (isHistorical) {
    return {
      explanation: 'The available risk plan is historical. Current-compatible levels are required before sizing or reward guidance is shown.',
      isCompatible: false,
      isCurrent: false,
      shouldLeadRiskTab: false,
      shouldShowPositionSizing: false,
      shouldShowRiskReward: false,
      state: 'historical',
      userLabel: 'Historical risk context',
    };
  }

  if (isLive && hasCurrentLevels && !isMixed) {
    return {
      explanation: null,
      isCompatible: true,
      isCurrent: true,
      shouldLeadRiskTab: true,
      shouldShowPositionSizing: true,
      shouldShowRiskReward: true,
      state: 'current_compatible',
      userLabel: 'Current-compatible risk',
    };
  }

  if (hasCurrentLevels && isMixed) {
    return {
      explanation: 'The setup has current levels, but some dependencies are mixed. Position sizing is reduced until all key inputs agree.',
      isCompatible: true,
      isCurrent: true,
      shouldLeadRiskTab: true,
      shouldShowPositionSizing: true,
      shouldShowRiskReward: true,
      state: 'partial',
      userLabel: 'Partial current risk',
    };
  }

  return {
    explanation: 'Current-compatible risk levels are not available yet. Existing trade levels are shown only as supporting context.',
    isCompatible: false,
    isCurrent: false,
    shouldLeadRiskTab: false,
    shouldShowPositionSizing: false,
    shouldShowRiskReward: false,
    state: 'unavailable',
    userLabel: 'Current risk unavailable',
  };
}

function buildCurrentRiskLevels({
  confirmationLevel,
  currentPrice,
  currentPriceSource,
  invalidationLevel,
  supportLevel,
  target1,
  target2,
}: {
  confirmationLevel: number | null;
  currentPrice: number | null;
  currentPriceSource: string;
  invalidationLevel: number | null;
  supportLevel: number | null;
  target1: number | null;
  target2: number | null;
}): RiskLevelItem[] {
  const confirmationDescription = currentPrice != null && confirmationLevel != null && currentPrice >= confirmationLevel
    ? 'Already cleared'
    : 'Break above';
  return mergeCloseLevels([
    buildLevel('current', 'Current Price', currentPrice, 'current', currentPriceSource),
    buildLevel('confirmation', 'Confirmation', confirmationLevel, 'confirmation', confirmationDescription),
    buildLevel('target-1', 'Target 1', target1, 'target', 'First target'),
    buildLevel('target-2', 'Target 2', target2, 'target', 'Second target'),
    buildLevel('support', 'Near Support', supportLevel, 'support', 'Nearest support'),
    buildLevel('invalidation', 'Invalidation', invalidationLevel, 'invalidation', 'Setup weakens below'),
  ].filter((item): item is RiskLevelItem => item != null));
}

function buildIllustrativeLevels(riskPlan?: RiskPlan | null, trust?: RiskPlanTrustAssessment): RiskLevelItem[] {
  if (!riskPlan || trust?.shouldLeadRiskTab) {
    return [];
  }
  return mergeCloseLevels([
    buildLevel('entry', 'Entry', riskPlan.entry, 'confirmation', 'Illustrative entry from the existing risk plan.'),
    buildLevel('stop', 'Stop Loss', riskPlan.stop_loss, 'invalidation', 'Illustrative stop from the existing risk plan.'),
    buildLevel('target-1', 'Target 1', riskPlan.target_1, 'target', 'Illustrative first target.'),
    buildLevel('target-2', 'Target 2', riskPlan.target_2, 'target', 'Illustrative second target.'),
  ].filter((item): item is RiskLevelItem => item != null));
}

function buildRewardInterpretations({
  currentPrice,
  invalidationLevel,
  target1,
  target2,
}: {
  currentPrice: number | null;
  invalidationLevel: number | null;
  target1: number | null;
  target2: number | null;
}): RewardInterpretation[] {
  const risk = currentPrice != null && invalidationLevel != null ? currentPrice - invalidationLevel : null;
  if (risk == null || risk <= 0 || currentPrice == null) {
    return [];
  }
  return [
    buildReward('target-1', 'Target 1', currentPrice, risk, target1),
    buildReward('target-2', 'Target 2', currentPrice, risk, target2),
  ].filter((item): item is RewardInterpretation => item != null);
}

function buildReward(
  key: string,
  label: string,
  currentPrice: number,
  risk: number,
  target: number | null,
): RewardInterpretation | null {
  if (target == null || target <= currentPrice) {
    return null;
  }
  const reward = target - currentPrice;
  const ratio = reward / risk;
  const rewardPercent = (reward / currentPrice) * 100;
  const quality = ratio >= 3
    ? 'strong'
    : ratio >= 2
      ? 'favorable'
      : ratio >= 1.5
        ? 'balanced'
        : ratio >= 1
          ? 'limited'
          : 'unfavorable';

  return {
    interpretation: rewardQualityText(quality),
    key,
    label,
    quality,
    ratio,
    rewardPercent,
    target,
  };
}

function buildRiskFactors({
  confirmationLevel,
  currentPrice,
  decisionContext,
  downsidePercent,
  supportLevel,
  trust,
}: {
  confirmationLevel: number | null;
  currentPrice: number | null;
  decisionContext: RiskDecisionContext;
  downsidePercent: number | null;
  supportLevel: number | null;
  trust: RiskPlanTrustAssessment;
}): RiskFactor[] {
  const factors: RiskFactor[] = [];
  if (!trust.shouldLeadRiskTab) {
    factors.push({
      detail: trust.explanation ?? 'Current-compatible risk calculations are unavailable.',
      key: 'trust',
      label: trust.userLabel,
      tone: 'warning',
    });
  }
  if (downsidePercent != null) {
    factors.push({
      detail: `${downsidePercent.toFixed(1)}% below current price.`,
      key: 'downside',
      label: downsidePercent > 8 ? 'Wide downside to invalidation' : downsidePercent > 4 ? 'Moderate downside to invalidation' : 'Contained downside to invalidation',
      tone: downsidePercent > 8 ? 'danger' : downsidePercent > 4 ? 'warning' : 'success',
    });
  }
  if (decisionContext.setupConfirmation === 'awaiting_confirmation' && confirmationLevel != null) {
    factors.push({
      detail: `Needs a break above ${formatCurrency(confirmationLevel)}.`,
      key: 'confirmation',
      label: 'Confirmation still required',
      tone: 'warning',
    });
  } else if (decisionContext.setupConfirmation === 'confirmed' && confirmationLevel != null) {
    factors.push({
      detail: `Price is above ${formatCurrency(confirmationLevel)}.`,
      key: 'confirmation',
      label: 'Confirmation cleared',
      tone: 'success',
    });
  }
  if (currentPrice != null && supportLevel != null && currentPrice > supportLevel) {
    const supportGap = ((currentPrice - supportLevel) / currentPrice) * 100;
    factors.push({
      detail: `Nearest support is ${supportGap.toFixed(1)}% below price.`,
      key: 'support',
      label: supportGap <= 5 ? 'Support nearby' : 'Support lower',
      tone: supportGap <= 5 ? 'success' : 'neutral',
    });
  }
  if (decisionContext.volatility !== 'unavailable') {
    factors.push({
      detail: `Volatility is ${decisionContext.volatility}.`,
      key: 'volatility',
      label: `${capitalizeLabel(decisionContext.volatility)} volatility`,
      tone: decisionContext.volatility === 'high' ? 'danger' : decisionContext.volatility === 'moderate' ? 'warning' : 'success',
    });
  }
  return factors.length
    ? factors.slice(0, 4)
    : [{
        detail: 'Risk drivers will appear once current levels are available.',
        key: 'empty',
        label: 'Risk drivers unavailable',
        tone: 'neutral',
      }];
}

function buildPositionGuidance({
  decisionContext,
  rewards,
}: {
  decisionContext: RiskDecisionContext;
  rewards: RewardInterpretation[];
}): PositionGuidance {
  if (
    ['incompatible', 'unavailable'].includes(decisionContext.dataTrust)
    || decisionContext.downsidePercent == null
  ) {
    return {
      explanation: 'Position sizing is unavailable because current risk levels are incomplete or incompatible.',
      label: 'Unavailable',
      state: 'unavailable',
    };
  }
  const weakReward = rewards.length > 0 && !rewards.some((reward) => ['balanced', 'favorable', 'strong'].includes(reward.quality));
  if (
    ['high', 'very_high'].includes(decisionContext.modeledRisk)
    || decisionContext.volatility === 'high'
    || decisionContext.downsidePercent > 8
    || decisionContext.setupConfirmation === 'failed'
  ) {
    return {
      explanation: 'Elevated volatility, high modeled risk, or wider invalidation distance calls for conservative modeled exposure.',
      label: 'Conservative',
      state: 'conservative',
    };
  }
  if (decisionContext.setupConfirmation === 'awaiting_confirmation') {
    return {
      explanation: 'The setup is constructive, but confirmation is not cleared yet, so modeled exposure stays smaller.',
      label: 'Reduced',
      state: 'reduced',
    };
  }
  if (decisionContext.dataTrust === 'partial') {
    return {
      explanation: 'Some current risk inputs are partial, so modeled exposure stays reduced until compatibility improves.',
      label: 'Reduced',
      state: 'reduced',
    };
  }
  if (decisionContext.modeledRisk === 'moderate') {
    return {
      explanation: 'Modeled setup risk is moderate, so exposure stays reduced even with compatible current levels.',
      label: 'Reduced',
      state: 'reduced',
    };
  }
  if (weakReward || decisionContext.downsidePercent > 4) {
    return {
      explanation: weakReward
        ? 'Reward is limited relative to the defined downside, so modeled exposure stays reduced.'
        : decisionContext.setupConfirmation === 'confirmed'
          ? `Confirmation is cleared, but downside to invalidation remains moderately wide at ${decisionContext.downsidePercent.toFixed(1)}%.`
          : `The setup is constructive, but ${decisionContext.downsidePercent.toFixed(1)}% downside to invalidation justifies smaller modeled exposure.`,
      label: 'Reduced',
      state: 'reduced',
    };
  }
  return {
    explanation: 'Low volatility, nearby support, and a defined invalidation level support standard modeled exposure within this scenario.',
    label: 'Standard',
    state: 'standard',
  };
}

function buildSupportingMetrics(
  riskPlan: RiskPlan | null | undefined,
  trust: RiskPlanTrustAssessment,
  supportResistance?: SupportResistanceResponse | null,
): { label: string; value: string }[] {
  return [
    { label: 'Trust state', value: trust.userLabel },
    { label: 'ATR14', value: formatNumber(riskPlan?.atr_14) },
    { label: 'Downside to invalidation', value: formatPercent(riskPlan?.risk_percent) },
    { label: 'Volatility', value: riskPlan?.volatility_level ?? 'Unavailable' },
    { label: 'Source mode', value: riskPlan?.data_quality?.overall_mode ?? supportResistance?.data_source ?? 'Unavailable' },
    { label: 'History quality', value: formatNumber(riskPlan?.data_quality?.history_quality_score ?? supportResistance?.history_quality_score) },
  ];
}

function buildHeadline(trust: RiskPlanTrustAssessment, riskLevel: string | null): string {
  if (!trust.shouldLeadRiskTab) {
    return 'Current risk plan unavailable';
  }
  return `${riskLevel ?? 'Current'} modeled risk`;
}

function buildSummary({
  confirmationLevel,
  currentPrice,
  decisionContext,
  downsidePercent,
  invalidationLevel,
  rewards,
  supportLevel,
  trust,
  volatilityLevel,
}: {
  confirmationLevel: number | null;
  currentPrice: number | null;
  decisionContext: RiskDecisionContext;
  downsidePercent: number | null;
  invalidationLevel: number | null;
  rewards: RewardInterpretation[];
  supportLevel: number | null;
  trust: RiskPlanTrustAssessment;
  volatilityLevel: string | null;
}): string {
  if (!trust.shouldLeadRiskTab) {
    return trust.explanation ?? 'Current-compatible risk calculations are unavailable. Existing levels are treated as illustrative context only.';
  }
  const parts: string[] = [];
  if (downsidePercent != null && invalidationLevel != null) {
    parts.push(`Invalidation is ${downsidePercent.toFixed(1)}% below the current price`);
  }
  if (supportLevel != null && currentPrice != null && currentPrice > supportLevel) {
    const supportGap = ((currentPrice - supportLevel) / currentPrice) * 100;
    parts.push(supportGap <= 5 ? 'with nearby support' : 'with support further below');
  }
  if (volatilityLevel) {
    parts.push(`and ${volatilityLevel.toLowerCase()} volatility`);
  }
  const bestReward = getBestReward(rewards);
  const confirmationText = confirmationLevel != null && decisionContext.setupConfirmation === 'awaiting_confirmation'
    ? ` if price clears confirmation at ${formatCurrency(confirmationLevel)}`
    : '';
  const rewardSentence = bestReward
    ? `${targetPhrase(bestReward.label)} offers the stronger ${bestReward.quality} reward profile${confirmationText}.`
    : confirmationLevel != null && decisionContext.setupConfirmation === 'awaiting_confirmation'
      ? `Confirmation is still needed above ${formatCurrency(confirmationLevel)}.`
      : '';
  return `${parts.join(', ')}. ${rewardSentence}`.trim();
}

function buildDecisionContext({
  confirmationLevel,
  currentPrice,
  downsidePercent,
  riskLevel,
  trust,
  volatilityLevel,
}: {
  confirmationLevel: number | null;
  currentPrice: number | null;
  downsidePercent: number | null;
  riskLevel: string | null;
  trust: RiskPlanTrustAssessment;
  volatilityLevel: string | null;
}): RiskDecisionContext {
  return {
    dataTrust: normalizeDataTrust(trust),
    downsidePercent,
    modeledRisk: normalizeModeledRisk(riskLevel),
    setupConfirmation: getSetupConfirmation(currentPrice, confirmationLevel),
    volatility: normalizeVolatility(volatilityLevel),
  };
}

function normalizeDataTrust(trust: RiskPlanTrustAssessment): RiskDataTrust {
  switch (trust.state) {
    case 'current_compatible':
      return 'current_compatible';
    case 'test_compatible':
      return 'test_compatible';
    case 'partial':
      return 'partial';
    case 'stale':
      return 'stale';
    case 'source_incompatible':
    case 'historical':
    case 'mock':
      return 'incompatible';
    case 'unavailable':
    default:
      return 'unavailable';
  }
}

function normalizeModeledRisk(riskLevel?: string | null): ModeledRisk {
  const normalized = `${riskLevel ?? ''}`.toLowerCase();
  if (normalized.includes('very') || normalized.includes('extreme')) {
    return 'very_high';
  }
  if (normalized.includes('high')) {
    return 'high';
  }
  if (normalized.includes('elevated') || normalized.includes('moderate')) {
    return 'moderate';
  }
  if (normalized.includes('low') || normalized.includes('controlled')) {
    return 'low';
  }
  return 'unavailable';
}

function normalizeVolatility(volatilityLevel?: string | null): RiskVolatility {
  const normalized = `${volatilityLevel ?? ''}`.toLowerCase();
  if (normalized.includes('high') || normalized.includes('elevated')) {
    return 'high';
  }
  if (normalized.includes('moderate') || normalized.includes('medium')) {
    return 'moderate';
  }
  if (normalized.includes('low')) {
    return 'low';
  }
  return 'unavailable';
}

function getSetupConfirmation(currentPrice: number | null, confirmationLevel: number | null): SetupConfirmation {
  if (currentPrice == null || confirmationLevel == null) {
    return 'unavailable';
  }
  return currentPrice >= confirmationLevel ? 'confirmed' : 'awaiting_confirmation';
}

function hasUsableCurrentLevels(riskPlan: RiskPlan, supportResistance?: SupportResistanceResponse | null): boolean {
  const currentPrice = numberOrNull(riskPlan.current_price ?? supportResistance?.current_price);
  const invalidation = numberOrNull(supportResistance?.stop_reference ?? riskPlan.stop_loss);
  return currentPrice != null && invalidation != null && currentPrice > 0 && invalidation > 0 && currentPrice > invalidation;
}

function buildSourceHaystack(dataQuality?: AnalysisDataQuality | null, supportResistance?: SupportResistanceResponse | null): string {
  return [
    dataQuality?.history_source,
    dataQuality?.overall_mode,
    ...(dataQuality?.live_dependencies ?? []),
    ...(dataQuality?.fallback_dependencies ?? []),
    ...(dataQuality?.mock_dependencies ?? []),
    ...(dataQuality?.live_components ?? []),
    ...(dataQuality?.fallback_components ?? []),
    ...(dataQuality?.mock_components ?? []),
    supportResistance?.data_source,
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();
}

function getPrimarySupport(supportResistance?: SupportResistanceResponse | null): number | null {
  if (supportResistance?.support_zones?.length) {
    return Math.max(...supportResistance.support_zones.map((zone) => zone.high).filter((value) => Number.isFinite(value)));
  }
  return numberOrNull(supportResistance?.moving_average_support?.ema_20)
    ?? numberOrNull(supportResistance?.moving_average_support?.ema_50);
}

function calculateDownsidePercent(currentPrice: number | null, invalidationLevel: number | null): number | null {
  if (currentPrice == null || invalidationLevel == null || currentPrice <= 0 || invalidationLevel <= 0 || currentPrice <= invalidationLevel) {
    return null;
  }
  return ((currentPrice - invalidationLevel) / currentPrice) * 100;
}

function buildLevel(
  key: string,
  label: string,
  value: number | null | undefined,
  role: RiskLevelItem['role'],
  description: string,
): RiskLevelItem | null {
  const numericValue = numberOrNull(value);
  return numericValue == null ? null : { description, key, label, role, value: numericValue };
}

function mergeCloseLevels(levels: RiskLevelItem[]): RiskLevelItem[] {
  const sorted = levels.sort((a, b) => b.value - a.value);
  return sorted.reduce<RiskLevelItem[]>((merged, level) => {
    const existing = merged.find((item) => Math.abs(item.value - level.value) <= 0.01);
    if (existing) {
      existing.label = `${existing.label} / ${level.label}`;
      existing.description = `${existing.description} ${level.description}`;
      return merged;
    }
    merged.push({ ...level });
    return merged;
  }, []);
}

function numberOrNull(value: number | null | undefined): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function getBestReward(rewards: RewardInterpretation[]): RewardInterpretation | null {
  return rewards.length
    ? [...rewards].sort((first, second) => second.ratio - first.ratio)[0]
    : null;
}

function capitalizeLabel(value: string): string {
  if (!value) {
    return 'Unavailable';
  }
  return `${value.charAt(0).toUpperCase()}${value.slice(1).replace('_', ' ')}`;
}

function rewardQualityText(quality: RewardInterpretation['quality']): string {
  switch (quality) {
    case 'strong':
      return 'Strong reward';
    case 'favorable':
      return 'Favorable reward';
    case 'balanced':
      return 'Balanced reward';
    case 'limited':
      return 'Limited reward';
    case 'unfavorable':
      return 'Unfavorable reward';
    default:
      return 'Reward interpretation unavailable.';
  }
}

function targetPhrase(label: string): string {
  if (label.toLowerCase().includes('2')) {
    return 'The second target';
  }
  if (label.toLowerCase().includes('1')) {
    return 'The first target';
  }
  return label;
}

function formatCurrency(value?: number | null): string {
  const numericValue = numberOrNull(value);
  if (numericValue == null) {
    return 'Unavailable';
  }
  return `$${numericValue.toLocaleString('en-US', { maximumFractionDigits: 2, minimumFractionDigits: 2 })}`;
}

function formatNumber(value?: number | null): string {
  const numericValue = numberOrNull(value);
  if (numericValue == null) {
    return 'Unavailable';
  }
  return numericValue.toLocaleString('en-US', { maximumFractionDigits: 2 });
}

function formatPercent(value?: number | null): string {
  const numericValue = numberOrNull(value);
  if (numericValue == null) {
    return 'Unavailable';
  }
  return `${numericValue.toLocaleString('en-US', { maximumFractionDigits: 1 })}%`;
}
