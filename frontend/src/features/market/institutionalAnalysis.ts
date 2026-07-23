import type {
  FollowThroughDay,
  InstitutionalActivityResponse,
  InstitutionalIntelligenceResponse,
} from '@/types/market';
import { buildEvidenceClassSummary, evidenceClass, type EvidenceClassSummary } from '@/features/trust/evidenceClasses';
import { decisionSummary, type DecisionSummary } from '@/features/trust/decisionSummary';

export type InstitutionalTone = 'positive' | 'warning' | 'negative' | 'neutral';
export type InstitutionalConfidence = 'high' | 'moderate' | 'low' | 'unavailable';
export type InstitutionalSourceKind = 'live' | 'cached' | 'mock' | 'proxy' | 'fallback' | 'mixed' | 'unavailable';

export type InstitutionalMetric = {
  label: string;
  tone: InstitutionalTone;
  value: number | null;
};

export type InstitutionalSourceLabel = 'live' | 'cached' | 'proxy' | 'fallback' | 'mixed' | 'mock' | 'unavailable';

export type InstitutionalDashboardViewModel = {
  evidence: EvidenceClassSummary;
  decisionSummary: DecisionSummary;
  overview: {
    bias: string;
    confidence: InstitutionalConfidence;
    directionalBiasScore: number | null;
    score: number | null;
    source: InstitutionalSourceKind;
    subtitle: string;
    summary: string;
    tone: InstitutionalTone;
    supportMetrics: InstitutionalMetric[];
  };
  bias: {
    bias: string;
    followThrough: string;
    interpretation: string;
    tone: InstitutionalTone;
  };
  moneyFlow: {
    buyingPressure: number | null;
    interpretation: string;
    netFlow: number | null;
    sellingPressure: number | null;
    sourceLabel: string;
    state: string;
    tone: InstitutionalTone;
  };
  largePrints: {
    bearish: number | null;
    bullish: number | null;
    confidence: InstitutionalConfidence;
    hasSignal: boolean;
    interpretation: string;
    netBias: number | null;
    neutral: number | null;
    sourceLabel: string;
    state: string;
    tone: InstitutionalTone;
  };
  options: {
    callActivity: number | null;
    confidence: InstitutionalConfidence;
    interpretation: string;
    putActivity: number | null;
    putCallRatio: number | null;
    sourceLabel: string;
    state: string;
    tone: InstitutionalTone;
  };
  liquidity: {
    interpretation: string;
    rows: { label: string; value: string }[];
    score: number | null;
    sourceLabel: string;
    state: string;
    tone: InstitutionalTone;
  };
  accumulationDistribution: {
    accumulation: number | null;
    churning: number | null;
    distribution: number | null;
    interpretation: string;
    maxCount: number;
    netBalance: number | null;
    stall: number | null;
    state: string;
    tone: InstitutionalTone;
  };
  followThroughDay: {
    event: FollowThroughDay | null;
    interpretation: string;
    state: string;
    tone: InstitutionalTone;
  };
  trend: {
    historyAvailable: boolean;
    summary: string;
  };
  dataQuality: {
    confidence: InstitutionalConfidence;
    limitations: string[];
    source: InstitutionalSourceKind;
    sourceLabel: string;
  };
};

export function buildInstitutionalDashboardViewModel(
  intelligence: InstitutionalIntelligenceResponse | null,
  activity: InstitutionalActivityResponse | null,
): InstitutionalDashboardViewModel | null {
  if (!intelligence && !activity) {
    return null;
  }
  const accumulationDistribution = buildAccumulationDistribution(activity);
  const moneyFlow = buildMoneyFlow(intelligence);
  const options = buildOptions(intelligence);
  const liquidity = buildLiquidity(intelligence);
  const largePrints = buildLargePrints(intelligence);
  const source = deriveSourceKind(intelligence);
  const confidence = deriveConfidence(intelligence, source);
  // The institutional score is treated as directional bias, not evidence quality.
  // Proxy-heavy or mixed inputs affect confidence/source quality rather than
  // automatically neutralizing a valid directional reading.
  const score = validNumber(intelligence?.institutional?.score)
    ?? averageValid([moneyFlow.buyingPressure, options.callActivity, liquidity.score]);
  const direction = deriveDirectionalBias(score, activity?.bias?.bias);
  const bias = buildBias(score, accumulationDistribution, activity?.bias?.bias, activity?.bias?.follow_through_day ?? null);
  const evidence = buildInstitutionalEvidence({ accumulationDistribution, largePrints, liquidity, moneyFlow, options });
  const directEvidenceLimitations = evidence.classes.filter((item) => item.id !== 'price_volume' && item.availability !== 'available').length;
  const overviewHeadline = evidence.state === 'unavailable'
    ? 'Institutional evidence unavailable'
    : evidence.state === 'available' && !evidence.contradiction
      ? 'Institutional evidence available'
      : 'Partial institutional evidence';
  const overviewSummary = evidence.state === 'unavailable'
    ? 'No supported institutional evidence class is currently available.'
    : `${evidence.availableCount} of ${evidence.totalCount} institutional evidence classes are usable. ${evidence.contradiction ?? 'Each class is reported independently.'}`;
  return {
    accumulationDistribution,
    bias,
    evidence,
    decisionSummary: decisionSummary({
      id: 'market.institutions',
      title: 'Institutional decision summary',
      currentState: overviewHeadline,
      whatChanged: activity?.bias?.follow_through_day?.triggered ? `${activity.bias.follow_through_day.index ?? 'Index'} follow-through detected` : null,
      preferredAction: evidence.state === 'available' ? 'Use the class-level evidence; require direct confirmation before increasing conviction.' : 'Treat price-volume inference as context until direct evidence improves.',
      mainRisk: evidence.state === 'unavailable' ? 'No current institutional confirmation.' : `${directEvidenceLimitations} direct evidence classes are proxy-limited or unavailable.`,
      invalidation: 'A conflicting or newly available direct evidence class should change this view.',
      freshness: 'Freshness is reported by evidence class',
      confidence: evidence.confidence,
      confidenceLabel: evidence.confidence === null ? 'Confidence unavailable' : `${evidence.confidence}/100 evidence confidence`,
      evidence,
      availability: evidence.state,
      contradiction: evidence.contradiction,
      whatWouldChange: 'Direct money flow, options, large-print, or liquidity confirmation.',
      methodology: ['Price-volume evidence does not imply direct institutional confirmation.', 'Class completeness adjusts summary confidence.'],
    }),
    dataQuality: {
      confidence,
      limitations: buildLimitations(intelligence),
      source,
      sourceLabel: sourceLabel(source),
    },
    followThroughDay: buildFollowThrough(activity?.bias?.follow_through_day ?? null, direction.label),
    largePrints,
    liquidity,
    moneyFlow,
    options,
    overview: {
      bias: overviewHeadline,
      confidence,
      directionalBiasScore: score,
      score,
      source,
      subtitle: 'Current institutional activity',
      summary: overviewSummary,
      tone: evidence.state === 'available' ? direction.tone : evidence.state === 'unavailable' ? 'neutral' : 'warning',
      supportMetrics: [
        { label: 'Money Flow', tone: moneyFlow.tone, value: moneyFlow.buyingPressure },
        { label: 'Options', tone: options.tone, value: options.callActivity },
        { label: 'Liquidity', tone: liquidity.tone, value: liquidity.score },
      ],
    },
    trend: {
      historyAvailable: false,
      summary: 'Historical institutional signals will appear when real snapshots are available.',
    },
  };
}

export function buildInstitutionalEvidence({
  accumulationDistribution,
  largePrints,
  liquidity,
  moneyFlow,
  options,
}: Pick<InstitutionalDashboardViewModel, 'accumulationDistribution' | 'largePrints' | 'liquidity' | 'moneyFlow' | 'options'>) {
  return buildEvidenceClassSummary([
    evidenceClass({
      id: 'price_volume', label: 'Price-volume evidence',
      availability: accumulationDistribution.state === 'Unavailable' ? 'unavailable' : 'available', freshness: null,
      confidence: accumulationDistribution.state === 'Unavailable' ? null : 70, provenance: ['Index accumulation/distribution activity'],
      conclusion: accumulationDistribution.state === 'Unavailable' ? null : `Price-volume ${accumulationDistribution.state.toLowerCase()}`,
      direction: toneDirection(accumulationDistribution.tone), limitations: ['Inference from price and volume; institutional identity is not confirmed.'], evidenceIds: [],
    }),
    evidenceClass({ id: 'money_flow', availability: moneyFlow.state === 'Unavailable' ? 'unavailable' : 'partial', freshness: null,
      confidence: moneyFlow.state === 'Unavailable' ? null : 60, provenance: [moneyFlow.sourceLabel], conclusion: moneyFlow.state === 'Unavailable' ? null : moneyFlow.state,
      direction: toneDirection(moneyFlow.tone), limitations: ['Market-derived proxy; buyer identity is not inferred.'], evidenceIds: [] }),
    evidenceClass({ id: 'options', availability: options.state === 'Unavailable' ? 'unavailable' : 'partial', freshness: null,
      confidence: confidenceNumber(options.confidence), provenance: [options.sourceLabel], conclusion: options.state === 'Unavailable' ? null : options.state,
      direction: toneDirection(options.tone), limitations: ['Options coverage may use proxy or fallback inputs.'], evidenceIds: [] }),
    evidenceClass({ id: 'large_prints', label: 'Large prints', availability: largePrints.hasSignal ? 'partial' : 'unavailable', freshness: null,
      confidence: confidenceNumber(largePrints.confidence), provenance: [largePrints.sourceLabel], conclusion: largePrints.hasSignal ? largePrints.state : null,
      direction: toneDirection(largePrints.tone), limitations: ['Candidate prints do not confirm buyer or seller identity.'], evidenceIds: [] }),
    evidenceClass({ id: 'liquidity', availability: liquidity.state === 'Unavailable' ? 'unavailable' : 'partial', freshness: null,
      confidence: liquidity.score, provenance: [liquidity.sourceLabel], conclusion: liquidity.state === 'Unavailable' ? null : liquidity.state,
      direction: toneDirection(liquidity.tone), limitations: ['Displayed depth may be estimated; hidden order-book depth is not measured.'], evidenceIds: [] }),
  ], 'institutional evidence');
}

function toneDirection(tone: InstitutionalTone) {
  return tone === 'positive' ? 'positive' as const : tone === 'negative' ? 'negative' as const : 'neutral' as const;
}

function confidenceNumber(value: InstitutionalConfidence) {
  return value === 'high' ? 90 : value === 'moderate' ? 70 : value === 'low' ? 40 : null;
}

function deriveDirectionalBias(score: number | null, rawBias?: string | null) {
  const label = rawBias && rawBias !== 'N/A'
    ? normalizeBiasLabel(rawBias)
    : score === null ? 'Unavailable'
      : score >= 85 ? 'Strongly Bullish'
        : score >= 70 ? 'Bullish'
          : score >= 58 ? 'Constructive'
            : score >= 45 ? 'Neutral'
              : score >= 32 ? 'Cautious'
                : 'Bearish';
  const tone: InstitutionalTone = label.includes('Bullish') || label === 'Constructive'
    ? 'positive'
    : label === 'Cautious' || label === 'Neutral'
      ? 'warning'
      : label === 'Unavailable'
        ? 'neutral'
        : 'negative';
  return { label, tone };
}

export function buildAccumulationDistribution(activity: InstitutionalActivityResponse | null): InstitutionalDashboardViewModel['accumulationDistribution'] {
  const accumulation = validNumber(activity?.bias?.accumulation_count);
  const distribution = validNumber(activity?.bias?.distribution_count);
  const stall = validNumber(activity?.bias?.stall_count);
  const churning = validNumber(activity?.bias?.churning_count);
  if (accumulation === null && distribution === null) {
    return {
      accumulation,
      churning,
      distribution,
      interpretation: 'Accumulation and distribution data is unavailable.',
      maxCount: 0,
      netBalance: null,
      stall,
      state: 'Unavailable',
      tone: 'neutral',
    };
  }
  const acc = accumulation ?? 0;
  const dist = distribution ?? 0;
  const stallCount = stall ?? 0;
  const churningCount = churning ?? 0;
  const netBalance = acc - dist;
  const elevatedFriction = Math.max(stallCount, churningCount) >= Math.max(acc, dist);
  const state = netBalance >= 8 && !elevatedFriction ? 'Strong Accumulation'
    : netBalance >= 2 ? 'Accumulation Bias'
      : netBalance <= -6 ? 'Heavy Distribution'
        : netBalance <= -2 ? 'Distribution Bias'
          : 'Balanced';
  const tone = netBalance >= 2 ? 'positive' : netBalance <= -2 ? 'negative' : 'neutral';
  return {
    accumulation,
    churning,
    distribution,
    interpretation: netBalance > 0
      ? `Accumulation is outpacing distribution${elevatedFriction ? ', while stall and churning activity remain elevated.' : '.'}`
      : netBalance < 0
        ? 'Distribution is outpacing accumulation, indicating caution in institutional activity.'
        : 'Accumulation and distribution are balanced.',
    maxCount: Math.max(acc, dist, stallCount, churningCount, 1),
    netBalance,
    stall,
    state,
    tone,
  };
}

function buildBias(
  score: number | null,
  accumulation: InstitutionalDashboardViewModel['accumulationDistribution'],
  rawBias?: string | null,
  followThrough?: FollowThroughDay | null,
): InstitutionalDashboardViewModel['bias'] {
  const directionalBias = rawBias && rawBias !== 'N/A'
    ? normalizeBiasLabel(rawBias)
    : score === null ? 'Unavailable'
      : score >= 85 ? 'Strongly Bullish'
        : score >= 70 ? 'Bullish'
          : score >= 58 ? 'Constructive'
            : score >= 45 ? 'Neutral'
              : score >= 32 ? 'Cautious'
                : 'Bearish';
  const tone = directionalBias.includes('Bullish') || directionalBias === 'Constructive'
    ? 'positive'
    : directionalBias === 'Cautious' || directionalBias === 'Neutral'
      ? 'warning'
      : directionalBias === 'Unavailable'
        ? 'neutral'
        : 'negative';
  const followThroughText = followThrough?.triggered
    ? `${followThrough.index ?? 'Index'} follow-through detected`
    : 'No recent follow-through day';
  const evidenceBias = accumulation.state === 'Unavailable' ? directionalBias : accumulation.state;
  return {
    bias: evidenceBias,
    followThrough: followThroughText,
    interpretation: `${accumulation.interpretation} ${followThrough?.triggered ? 'A recent follow-through day supports the constructive reading.' : 'No recent follow-through day is confirming the signal.'}`,
    tone: accumulation.state === 'Unavailable' ? tone : accumulation.tone,
  };
}

function buildMoneyFlow(intelligence: InstitutionalIntelligenceResponse | null): InstitutionalDashboardViewModel['moneyFlow'] {
  const money = intelligence?.money_flow ?? null;
  if (!money) {
    return emptyMoneyFlow();
  }
  const buyingPressure = validNumber(money.score) ?? averageValid(money.items.map((item) => item.score));
  const sellingPressure = buyingPressure === null ? null : Math.max(0, 100 - buyingPressure);
  const netFlow = buyingPressure !== null && sellingPressure !== null ? buyingPressure - sellingPressure : null;
  const state = netFlow === null ? 'Unavailable'
    : netFlow >= 35 ? 'Strong Buying'
      : netFlow >= 12 ? 'Buying Bias'
        : netFlow <= -35 ? 'Strong Selling'
          : netFlow <= -12 ? 'Selling Bias'
            : 'Neutral';
  const tone = netFlow === null ? 'neutral' : netFlow >= 12 ? 'positive' : netFlow <= -12 ? 'negative' : 'neutral';
  const leader = [...money.items].sort((a, b) => b.score - a.score)[0];
  return {
    buyingPressure,
    interpretation: state === 'Unavailable'
      ? 'Money flow proxy is unavailable.'
      : `${state === 'Neutral' ? 'Buying and selling pressure are balanced' : `${state.includes('Buying') ? 'Buying' : 'Selling'} pressure leads`}${leader ? `, with ${leader.area} providing the strongest contribution.` : '.'}`,
    netFlow,
    sellingPressure,
    sourceLabel: money.methodology ? 'Money Flow Proxy' : 'Proxy',
    state,
    tone,
  };
}

function buildLargePrints(intelligence: InstitutionalIntelligenceResponse | null): InstitutionalDashboardViewModel['largePrints'] {
  const candidates = intelligence?.institutional?.block_trade_candidates ?? [];
  if (!intelligence?.institutional) {
    return emptyLargePrints('Unavailable');
  }
  if (!candidates.length) {
    return {
      bearish: 0,
      bullish: 0,
      confidence: deriveConfidence(intelligence),
      hasSignal: false,
      interpretation: 'No large-print signal is currently available.',
      netBias: null,
      neutral: 0,
      sourceLabel: 'Proxy',
      state: 'No Signal',
      tone: 'neutral',
    };
  }
  const bullish = candidates.filter((candidate) => classifyPrint(candidate.side, candidate.reason) === 'bullish').length;
  const bearish = candidates.filter((candidate) => classifyPrint(candidate.side, candidate.reason) === 'bearish').length;
  const neutral = Math.max(0, candidates.length - bullish - bearish);
  const netBias = bullish - bearish;
  return {
    bearish,
    bullish,
    confidence: deriveConfidence(intelligence),
    hasSignal: true,
    interpretation: netBias > 0
      ? 'Large-print candidates lean bullish, but identity is not directly confirmed.'
      : netBias < 0
        ? 'Large-print candidates lean bearish, but identity is not directly confirmed.'
        : 'Large-print candidates are neutral.',
    netBias,
    neutral,
    sourceLabel: 'Proxy',
    state: netBias > 0 ? 'Bullish Candidate Bias' : netBias < 0 ? 'Bearish Candidate Bias' : 'Neutral Candidate Bias',
    tone: netBias > 0 ? 'positive' : netBias < 0 ? 'negative' : 'neutral',
  };
}

function buildOptions(intelligence: InstitutionalIntelligenceResponse | null): InstitutionalDashboardViewModel['options'] {
  const options = intelligence?.options ?? null;
  if (!options) {
    return {
      callActivity: null,
      confidence: 'unavailable',
      interpretation: 'Options positioning unavailable.',
      putActivity: null,
      putCallRatio: null,
      sourceLabel: 'Unavailable',
      state: 'Unavailable',
      tone: 'neutral',
    };
  }
  const putCall = validNumber(options.put_call_ratio);
  const callActivity = putCall === null ? validNumber(options.score) : clamp(100 - putCall * 50, 0, 100);
  const putActivity = putCall === null ? null : clamp(putCall * 50, 0, 100);
  const tone = callActivity === null ? 'neutral' : callActivity >= 60 ? 'positive' : callActivity <= 40 ? 'negative' : 'neutral';
  return {
    callActivity,
    confidence: confidenceFromNumber(options.confidence),
    interpretation: callActivity === null || putActivity === null
      ? 'Options positioning is unavailable.'
      : callActivity > putActivity
        ? 'Call activity exceeds put activity, supporting a constructive options tone.'
        : putActivity > callActivity
          ? 'Put activity exceeds call activity, indicating a defensive options tone.'
          : 'Call and put activity are balanced.',
    putActivity,
    putCallRatio: putCall,
    sourceLabel: options.confidence === null || options.confidence === undefined ? 'Fallback' : 'Proxy',
    state: tone === 'positive' ? 'Constructive' : tone === 'negative' ? 'Defensive' : 'Neutral',
    tone,
  };
}

function buildLiquidity(intelligence: InstitutionalIntelligenceResponse | null): InstitutionalDashboardViewModel['liquidity'] {
  const liquidity = intelligence?.liquidity ?? null;
  if (!liquidity) {
    return {
      interpretation: 'Liquidity data unavailable.',
      rows: [],
      score: null,
      sourceLabel: 'Unavailable',
      state: 'Unavailable',
      tone: 'neutral',
    };
  }
  const score = validNumber(liquidity.score);
  return {
    interpretation: buildLiquidityInterpretation(liquidity.status, liquidity.spread_condition, liquidity.depth_condition),
    rows: [
      { label: 'Classification', value: liquidity.status },
      { label: 'Spread Quality', value: liquidity.spread_condition },
      { label: 'Volume Depth', value: simplifyLiquidityDepth(liquidity.depth_condition) },
      { label: 'Funding', value: liquidity.funding_condition },
      { label: 'Execution Risk', value: liquidity.score >= 65 ? 'Low' : liquidity.score >= 45 ? 'Moderate' : 'Elevated' },
    ],
    score,
    sourceLabel: 'Proxy',
    state: liquidity.status,
    tone: score === null ? 'neutral' : score >= 65 ? 'positive' : score >= 45 ? 'warning' : 'negative',
  };
}

function buildLiquidityInterpretation(status: string, spread: string, depth: string) {
  const concerns = [
    spread.toLowerCase().includes('wide') ? 'wider spreads' : null,
    depth.toLowerCase().includes('moderate') || depth.toLowerCase().includes('thin') ? `${simplifyLiquidityDepth(depth).toLowerCase()} depth` : null,
  ].filter(Boolean);
  if (!concerns.length) {
    return `Liquidity is ${status.toLowerCase()} overall.`;
  }
  return `Liquidity is ${status.toLowerCase()} overall, although ${concerns.join(' and ')} may increase execution friction.`;
}

function simplifyLiquidityDepth(value: string) {
  const normalized = value.toLowerCase();
  if (normalized.includes('hidden') || normalized.includes('estimated') || normalized.includes('dollar')) {
    return 'Estimated';
  }
  if (normalized.includes('thin') || normalized.includes('shallow')) {
    return 'Thin';
  }
  if (normalized.includes('deep') || normalized.includes('healthy')) {
    return 'Deep';
  }
  if (normalized.includes('moderate') || normalized.includes('normal')) {
    return 'Moderate';
  }
  return value || 'Unavailable';
}

function buildFollowThrough(event: FollowThroughDay | null, bias: string): InstitutionalDashboardViewModel['followThroughDay'] {
  if (!event) {
    return {
      event,
      interpretation: 'Follow-through day data unavailable.',
      state: 'Unavailable',
      tone: 'neutral',
    };
  }
  if (!event.triggered) {
    return {
      event,
      interpretation: 'No recent follow-through day is confirming institutional demand.',
      state: 'No recent follow-through day',
      tone: 'neutral',
    };
  }
  return {
    event,
    interpretation: `Supports the current ${bias.toLowerCase()} institutional reading, but does not guarantee continuation.`,
    state: 'Detected',
    tone: 'positive',
  };
}

function buildLimitations(intelligence: InstitutionalIntelligenceResponse | null) {
  return Array.from(new Set([
    ...(intelligence?.institutional?.limitations ?? []),
    ...(intelligence?.sentiment?.limitations ?? []),
    'Block-trade candidates are heuristic.',
    'Buyer/seller identity is not inferred.',
    'Some sentiment and money-flow inputs are market-derived proxies.',
    'Volume depth is estimated from traded dollar volume; hidden order-book depth is not measured.',
    'Put/call may use a deterministic fallback when live options data is unavailable.',
    'Large-print activity is estimated from public market data.',
  ])).slice(0, 6);
}

function deriveConfidence(
  intelligence: InstitutionalIntelligenceResponse | null,
  source = deriveSourceKind(intelligence),
): InstitutionalConfidence {
  const values = [
    intelligence?.sentiment?.confidence,
    intelligence?.institutional?.confidence,
    intelligence?.options?.confidence,
  ].map(validNumber).filter((value): value is number => value !== null);
  if (!values.length) {
    return intelligence ? 'moderate' : 'unavailable';
  }
  const confidence = confidenceFromNumber(averageValid(values));
  if (source === 'mixed' || source === 'mock' || source === 'fallback' || source === 'proxy') {
    return confidence === 'high' ? 'moderate' : confidence;
  }
  return confidence;
}

function confidenceFromNumber(value: number | null | undefined): InstitutionalConfidence {
  const score = validNumber(value);
  if (score === null) {
    return 'moderate';
  }
  if (score >= 75) {
    return 'high';
  }
  if (score >= 45) {
    return 'moderate';
  }
  return 'low';
}

function deriveSourceKind(intelligence: InstitutionalIntelligenceResponse | null): InstitutionalSourceKind {
  const mode = intelligence?.sentiment?.overall_mode?.toLowerCase();
  if (!intelligence) {
    return 'unavailable';
  }
  if (mode?.includes('live')) {
    return 'live';
  }
  if (mode?.includes('mock')) {
    return 'mock';
  }
  if (mode?.includes('fallback')) {
    return 'fallback';
  }
  return 'mixed';
}

function sourceLabel(source: InstitutionalSourceKind) {
  switch (source) {
    case 'live':
      return 'Live';
    case 'cached':
      return 'Cached';
    case 'proxy':
      return 'Proxy';
    case 'mock':
      return 'Mock Data';
    case 'fallback':
      return 'Fallback';
    case 'unavailable':
      return 'Unavailable';
    default:
      return 'Mixed Sources';
  }
}

function normalizeBiasLabel(label: string) {
  const normalized = label.toLowerCase();
  if (normalized.includes('strong') && normalized.includes('bull')) {
    return 'Strongly Bullish';
  }
  if (normalized.includes('bull')) {
    return 'Bullish';
  }
  if (normalized.includes('bear')) {
    return 'Bearish';
  }
  if (normalized.includes('caut')) {
    return 'Cautious';
  }
  if (normalized.includes('construct')) {
    return 'Constructive';
  }
  return 'Neutral';
}

function classifyPrint(side?: string | null, reason?: string | null) {
  const text = `${side ?? ''} ${reason ?? ''}`.toLowerCase();
  if (text.includes('buy') || text.includes('accum') || text.includes('bull')) {
    return 'bullish';
  }
  if (text.includes('sell') || text.includes('distrib') || text.includes('bear')) {
    return 'bearish';
  }
  return 'neutral';
}

function emptyMoneyFlow(): InstitutionalDashboardViewModel['moneyFlow'] {
  return {
    buyingPressure: null,
    interpretation: 'Money flow data unavailable.',
    netFlow: null,
    sellingPressure: null,
    sourceLabel: 'Unavailable',
    state: 'Unavailable',
    tone: 'neutral',
  };
}

function emptyLargePrints(sourceLabel: string): InstitutionalDashboardViewModel['largePrints'] {
  return {
    bearish: null,
    bullish: null,
    confidence: 'unavailable',
    hasSignal: false,
    interpretation: 'Large-print data unavailable.',
    netBias: null,
    neutral: null,
    sourceLabel,
    state: 'Unavailable',
    tone: 'neutral',
  };
}

function averageValid(values: (number | null | undefined)[]) {
  const valid = values.filter((value): value is number => typeof value === 'number' && Number.isFinite(value));
  return valid.length ? valid.reduce((sum, value) => sum + value, 0) / valid.length : null;
}

function validNumber(value: number | null | undefined) {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}
