import type {
  RelativeStrengthItem,
  RiskPlan,
  StockRatingItem,
  SupportResistanceResponse,
  VolumeAnalysis,
  WatchlistItem,
} from '@/types/market';
import type { CurrentPriceSelection } from '@/features/stock-detail/currentPrice';

export type StockExecutiveSummarySource = 'backend' | 'rule_based' | 'unavailable';
export type StockDetailTone = 'success' | 'warning' | 'danger' | 'accent' | 'neutral';

export type StockExecutiveSummary = {
  body: string;
  evidenceKeys: string[];
  headline: string;
  source: StockExecutiveSummarySource;
};

export type StockDetailFactor = {
  key: string;
  label: string;
  score: number | null;
  tone: StockDetailTone;
  interpretation: string;
};

export type StockDetailWatchItem = {
  label: string;
  value: string;
  tone: StockDetailTone;
};

export type StockDetailMetric = {
  label: string;
  value: string;
};

export type StockAssessmentEvidence = {
  label: string;
  tone: StockDetailTone;
};

export type StockDetailOverviewModel = {
  symbol: string;
  quote: {
    price: number | null;
    change: number | null;
    changePercent: number | null;
    source?: string | null;
    timestamp?: string | null;
  };
  status: string;
  rating: string;
  riskLevel: string;
  overallScore: number | null;
  assessmentLabel: string;
  assessmentTone: StockDetailTone;
  assessmentEvidence: StockAssessmentEvidence[];
  executiveSummary: StockExecutiveSummary;
  explanation: string;
  strengths: string[];
  risks: string[];
  factors: StockDetailFactor[];
  watchItems: StockDetailWatchItem[];
  supportingMetrics: StockDetailMetric[];
  sourceLabel: string;
  sourceTone: StockDetailTone;
  methodology: string;
};

type BuildOverviewInput = {
  currentPrice?: CurrentPriceSelection | null;
  relativeStrength?: RelativeStrengthItem | null;
  riskPlan?: RiskPlan | null;
  stock: WatchlistItem;
  stockRating?: StockRatingItem | null;
  supportResistance?: SupportResistanceResponse | null;
  volumeAnalysis?: VolumeAnalysis | null;
};

const factorLabels: { key: keyof StockRatingItem['components']; label: string }[] = [
  { key: 'relative_strength', label: 'Relative Strength' },
  { key: 'pattern_quality', label: 'Pattern Quality' },
  { key: 'sector_strength', label: 'Sector Strength' },
  { key: 'market_alignment', label: 'Market Alignment' },
  { key: 'institutional_support', label: 'Institutional Support' },
  { key: 'risk_control', label: 'Risk Control' },
];

export function buildStockDetailOverview({
  currentPrice,
  relativeStrength,
  riskPlan,
  stock,
  stockRating,
  supportResistance,
  volumeAnalysis,
}: BuildOverviewInput): StockDetailOverviewModel {
  const overallScore = toNumber(stockRating?.overall_score);
  const assessment = getAssessment(overallScore, stockRating?.rating, stockRating?.status);
  const riskLevel = stockRating?.risk_level ?? riskPlan?.risk_level ?? stock.risk_flag ?? 'Unavailable';
  const status = stockRating?.status ?? stock.trend ?? 'Unavailable';
  const source = getSource(stock, stockRating, relativeStrength, riskPlan, supportResistance, volumeAnalysis);
  const quoteSource = currentPrice ? getCurrentPriceSource(currentPrice) : source;
  const factors = buildFactors(stockRating);
  const watchItems = buildWatchItems(supportResistance, riskPlan, relativeStrength, volumeAnalysis);
  const strengths = sanitizeList(stockRating?.strengths).slice(0, 4);
  const risks = sanitizeList(stockRating?.warnings).slice(0, 4);
  const summary = buildExecutiveSummary({
    assessment: assessment.label,
    factors,
    stock,
    stockRating,
    watchItems,
  });

  return {
    symbol: stock.ticker,
    quote: {
      price: currentPrice?.price ?? toNumber(stock.price),
      change: currentPrice?.change ?? toNumber(stock.change),
      changePercent: currentPrice?.changePercent ?? toNumber(stock.change_percent),
      source: currentPrice?.sourceLabel ?? stock.data_source ?? null,
      timestamp: currentPrice?.timestamp ?? stock.quote_timestamp ?? stock.as_of ?? null,
    },
    status,
    rating: stockRating?.rating ?? 'Unavailable',
    riskLevel,
    overallScore,
    assessmentLabel: assessment.label,
    assessmentTone: assessment.tone,
    assessmentEvidence: buildAssessmentEvidence(factors, riskLevel),
    executiveSummary: summary,
    explanation: stockRating?.explanation ?? 'Detailed rating explanation is unavailable for this stock.',
    strengths: strengths.length ? strengths : ['No confirmed strengths are available from the current analysis.'],
    risks: risks.length ? risks : ['No major rule-based risks are available from the current analysis.'],
    factors,
    watchItems,
    supportingMetrics: buildSupportingMetrics(stockRating, relativeStrength, riskPlan, supportResistance, volumeAnalysis),
    sourceLabel: quoteSource.label,
    sourceTone: quoteSource.tone,
    methodology: buildMethodology(quoteSource.label),
  };
}

function getCurrentPriceSource(currentPrice: CurrentPriceSelection): { label: string; tone: StockDetailTone } {
  switch (currentPrice.source) {
    case 'live_quote':
      return { label: currentPrice.sourceLabel, tone: 'success' };
    case 'snapshot_quote':
    case 'snapshot_current_price':
      return { label: currentPrice.sourceLabel, tone: 'accent' };
    case 'history_close':
      return { label: currentPrice.sourceLabel, tone: 'warning' };
    default:
      return { label: currentPrice.sourceLabel, tone: 'neutral' };
  }
}

export function getAssessment(
  score?: number | null,
  rating?: string | null,
  status?: string | null,
): { label: string; tone: StockDetailTone } {
  const normalizedText = `${rating ?? ''} ${status ?? ''}`.toLowerCase();
  if (score == null) {
    return { label: status ?? rating ?? 'Unavailable', tone: 'neutral' };
  }
  if (normalizedText.includes('risk') || score < 45) {
    return { label: 'Needs Confirmation', tone: score < 40 ? 'danger' : 'warning' };
  }
  if (score >= 85) {
    return { label: 'High Conviction', tone: 'success' };
  }
  if (score >= 70) {
    return { label: 'Constructive', tone: 'accent' };
  }
  if (score >= 55) {
    return { label: 'Selective', tone: 'warning' };
  }
  if (score >= 45) {
    return { label: 'Needs Confirmation', tone: 'warning' };
  }
  return { label: 'Weak', tone: 'danger' };
}

export function getFactorTone(score?: number | null): StockDetailTone {
  if (score == null) {
    return 'neutral';
  }
  if (score >= 75) {
    return 'success';
  }
  if (score >= 55) {
    return 'accent';
  }
  if (score >= 40) {
    return 'warning';
  }
  return 'danger';
}

function buildExecutiveSummary({
  assessment,
  factors,
  stock,
  stockRating,
  watchItems,
}: {
  assessment: string;
  factors: StockDetailFactor[];
  stock: WatchlistItem;
  stockRating?: StockRatingItem | null;
  watchItems: StockDetailWatchItem[];
}): StockExecutiveSummary {
  const backendSummary = sanitizeSummaryText(stockRating?.explanation);
  if (backendSummary && isSpecificSummary(backendSummary) && backendSummary.length <= 180) {
    return {
      body: capWords(backendSummary, 62),
      evidenceKeys: ['rating_explanation'],
      headline: getSummaryHeadline(assessment, watchItems),
      source: 'backend',
    };
  }

  const positiveFactors = factors
    .filter((factor) => factor.score != null && (factor.tone === 'success' || factor.tone === 'accent'))
    .sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
    .slice(0, 2);
  const limitingFactors = factors
    .filter((factor) => factor.score != null && (factor.tone === 'warning' || factor.tone === 'danger'))
    .sort((a, b) => (a.score ?? 0) - (b.score ?? 0))
    .slice(0, 2);
  const confirmation = getConfirmationPhrase(watchItems);

  if (!positiveFactors.length && !limitingFactors.length && !confirmation) {
    return {
      body: 'The current setup cannot be summarized reliably because key analysis fields are unavailable.',
      evidenceKeys: [],
      headline: 'Setup summary unavailable.',
      source: 'unavailable',
    };
  }

  const positivePhrase = positiveFactors.length
    ? `${joinLabels(positiveFactors.map((factor) => lowerFirst(factor.label)))} ${positiveFactors.length === 1 ? 'is' : 'are'} supportive`
    : 'Available support signals are limited';
  const limitingPhrase = limitingFactors.length
    ? `, while ${joinLabels(limitingFactors.map((factor) => lowerFirst(factor.label)))} ${limitingFactors.length === 1 ? 'needs' : 'need'} confirmation`
    : '';
  const confirmationSentence = confirmation
    ? ` ${confirmation}`
    : stock.setup && !isPlaceholderText(stock.setup)
      ? ` The setup remains ${stock.setup.toLowerCase()} and needs confirmation.`
      : '';

  return {
    body: capWords(`${positivePhrase}${limitingPhrase}.${confirmationSentence}`, 62),
    evidenceKeys: [...positiveFactors, ...limitingFactors].map((factor) => factor.key),
    headline: getSummaryHeadline(assessment, watchItems),
    source: 'rule_based',
  };
}

function buildFactors(stockRating?: StockRatingItem | null): StockDetailFactor[] {
  return factorLabels.map(({ key, label }) => {
    const score = toNumber(stockRating?.components?.[key]);
    return {
      key,
      label,
      score,
      tone: getFactorTone(score),
      interpretation: getFactorInterpretation(score),
    };
  });
}

function getFactorInterpretation(score?: number | null): string {
  if (score == null) {
    return 'Unavailable';
  }
  if (score >= 75) {
    return 'Supportive';
  }
  if (score >= 55) {
    return 'Constructive';
  }
  if (score >= 40) {
    return 'Mixed';
  }
  return 'Weak';
}

function buildAssessmentEvidence(factors: StockDetailFactor[], riskLevel: string): StockAssessmentEvidence[] {
  const positives = factors
    .filter((factor) => factor.score != null && factor.tone === 'success')
    .sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
    .slice(0, 2)
    .map((factor) => ({ label: `${factor.label}: ${factor.interpretation}`, tone: factor.tone }));
  const limiter = factors
    .filter((factor) => factor.score != null && (factor.tone === 'warning' || factor.tone === 'danger'))
    .sort((a, b) => (a.score ?? 0) - (b.score ?? 0))
    .slice(0, 1)
    .map((factor) => ({ label: `${factor.label}: ${factor.interpretation}`, tone: factor.tone }));
  const riskTone = getRiskEvidenceTone(riskLevel);
  const risk = riskTone === 'neutral' ? [] : [{ label: `${riskLevel} risk`, tone: riskTone }];
  return [...positives, ...limiter, ...risk].slice(0, 3);
}

function buildWatchItems(
  supportResistance?: SupportResistanceResponse | null,
  riskPlan?: RiskPlan | null,
  relativeStrength?: RelativeStrengthItem | null,
  volumeAnalysis?: VolumeAnalysis | null,
): StockDetailWatchItem[] {
  const items: StockDetailWatchItem[] = [];
  if (supportResistance?.breakout_level != null) {
    items.push({
      label: 'Breakout level',
      value: formatCurrency(supportResistance.breakout_level),
      tone: 'success',
    });
  }
  if (supportResistance?.stop_reference != null) {
    items.push({
      label: 'Stop reference',
      value: formatCurrency(supportResistance.stop_reference),
      tone: 'warning',
    });
  } else if (riskPlan?.stop_loss != null) {
    items.push({
      label: 'Risk stop',
      value: formatCurrency(riskPlan.stop_loss),
      tone: 'warning',
    });
  }
  if (relativeStrength?.status) {
    items.push({
      label: 'RS confirmation',
      value: relativeStrength.status,
      tone: getFactorTone(relativeStrength.overall_rs_score),
    });
  }
  if (volumeAnalysis?.volume_quality) {
    items.push({
      label: 'Volume quality',
      value: volumeAnalysis.volume_quality,
      tone: getFactorTone(volumeAnalysis.volume_quality_score),
    });
  }
  return items.length
    ? items
    : [{ label: 'Next checkpoint', value: 'Wait for more complete technical data.', tone: 'neutral' }];
}

function buildSupportingMetrics(
  stockRating?: StockRatingItem | null,
  relativeStrength?: RelativeStrengthItem | null,
  riskPlan?: RiskPlan | null,
  supportResistance?: SupportResistanceResponse | null,
  volumeAnalysis?: VolumeAnalysis | null,
): StockDetailMetric[] {
  return [
    { label: 'Overall score', value: formatNumber(stockRating?.overall_score) },
    { label: 'Rating', value: stockRating?.rating ?? 'Unavailable' },
    { label: 'Risk level', value: stockRating?.risk_level ?? riskPlan?.risk_level ?? 'Unavailable' },
    { label: 'RS rank', value: formatNumber(relativeStrength?.rank) },
    { label: 'RS score', value: formatNumber(relativeStrength?.overall_rs_score) },
    { label: '20D return', value: formatPercent(relativeStrength?.return_20d) },
    { label: '60D return', value: formatPercent(relativeStrength?.return_60d) },
    { label: 'Relative volume', value: formatNumber(volumeAnalysis?.relative_volume, 2) },
    { label: 'ATR 14', value: formatNumber(riskPlan?.atr_14, 2) },
    { label: 'Target 1', value: formatCurrency(riskPlan?.target_1) },
    { label: 'Breakout level', value: formatCurrency(supportResistance?.breakout_level) },
    { label: 'Stop reference', value: formatCurrency(supportResistance?.stop_reference) },
  ];
}

function getSource(
  stock: WatchlistItem,
  stockRating?: StockRatingItem | null,
  relativeStrength?: RelativeStrengthItem | null,
  riskPlan?: RiskPlan | null,
  supportResistance?: SupportResistanceResponse | null,
  volumeAnalysis?: VolumeAnalysis | null,
): { label: string; tone: StockDetailTone } {
  const qualities = [
    stockRating?.data_quality?.overall_mode,
    riskPlan?.data_quality?.overall_mode,
    stock.data_source,
    relativeStrength?.data_source,
    supportResistance?.data_source,
    volumeAnalysis?.data_source,
  ].filter(Boolean).map((value) => String(value).toLowerCase());

  if (stock.is_stale || qualities.some((value) => value.includes('stale'))) {
    return { label: 'Stale data', tone: 'warning' };
  }
  if (stock.fallback_used || qualities.some((value) => value.includes('fallback'))) {
    return { label: 'Fallback data', tone: 'warning' };
  }
  if (qualities.some((value) => value.includes('mock'))) {
    return { label: 'Mock data', tone: 'neutral' };
  }
  if (qualities.some((value) => value.includes('mixed'))) {
    return { label: 'Mixed data', tone: 'accent' };
  }
  if (stock.is_live || qualities.some((value) => value.includes('live'))) {
    return { label: 'Live data', tone: 'accent' };
  }
  if (qualities.some((value) => value.includes('cached'))) {
    return { label: 'Cached data', tone: 'accent' };
  }
  return { label: 'Data source unavailable', tone: 'neutral' };
}

function getRiskEvidenceTone(riskLevel: string): StockDetailTone {
  const normalized = riskLevel.toLowerCase();
  if (normalized.includes('high') || normalized.includes('elevated')) {
    return 'danger';
  }
  if (normalized.includes('medium') || normalized.includes('moderate')) {
    return 'warning';
  }
  return 'neutral';
}

function sanitizeSummaryText(value?: string | null): string | null {
  if (!value || isPlaceholderText(value)) {
    return null;
  }
  const stripped = value
    .replace(/\b[A-Z]{1,5}\b\s+/g, '')
    .replace(/\bscreens as\b/gi, 'has a')
    .replace(/\bthe current setup is\s+(setup updating|unknown|n\/a)\.?/gi, '')
    .replace(/\bsetup updating\b/gi, '')
    .replace(/\bN\/A\b/g, '')
    .replace(/\s+/g, ' ')
    .trim();
  return isPlaceholderText(stripped) ? null : stripped;
}

function isSpecificSummary(value: string): boolean {
  const normalized = value.toLowerCase();
  return ![
    'screens as',
    'setup updating',
    'current setup is current',
    'rating score',
    'risk is currently',
    'has a constructive',
    'unknown',
  ].some((bad) => normalized.includes(bad));
}

function isPlaceholderText(value?: string | null): boolean {
  const normalized = (value ?? '').trim().toLowerCase();
  return !normalized || ['n/a', 'unknown', 'setup updating', 'current', 'unavailable'].includes(normalized);
}

function getSummaryHeadline(assessment: string, watchItems: StockDetailWatchItem[]): string {
  if (watchItems.some((item) => item.label.toLowerCase().includes('breakout'))) {
    return `${assessment}, awaiting breakout confirmation.`;
  }
  if (watchItems.some((item) => item.label.toLowerCase().includes('stop'))) {
    return `${assessment}, with invalidation levels defined.`;
  }
  return `${assessment}, pending stronger confirmation.`;
}

function getConfirmationPhrase(watchItems: StockDetailWatchItem[]): string | null {
  const breakout = watchItems.find((item) => item.label.toLowerCase().includes('breakout') && item.value !== 'Unavailable');
  if (breakout) {
    return `A sustained move above ${breakout.value} with improving participation would provide stronger confirmation.`;
  }
  const stop = watchItems.find((item) => item.label.toLowerCase().includes('stop') && item.value !== 'Unavailable');
  if (stop) {
    return `Holding above ${stop.value} keeps the setup from weakening further.`;
  }
  const volume = watchItems.find((item) => item.label.toLowerCase().includes('volume') && item.value !== 'Unavailable');
  if (volume) {
    return `Volume confirmation remains the next useful checkpoint.`;
  }
  return null;
}

function joinLabels(items: string[]): string {
  if (items.length <= 1) {
    return items[0] ?? '';
  }
  return `${items.slice(0, -1).join(', ')} and ${items[items.length - 1]}`;
}

function lowerFirst(value: string): string {
  return value ? value.charAt(0).toLowerCase() + value.slice(1) : value;
}

function capWords(value: string, maxWords: number): string {
  const words = value.trim().split(/\s+/);
  if (words.length <= maxWords) {
    return value.trim();
  }
  return `${words.slice(0, maxWords).join(' ')}...`;
}

function buildMethodology(sourceLabel: string): string {
  return `This overview summarizes the existing stock rating, relative strength, volume, support/resistance, and risk-plan engines. Source status: ${sourceLabel}. Missing fields are shown as unavailable rather than estimated.`;
}

function sanitizeList(items?: string[] | null): string[] {
  return (items ?? []).filter((item) => typeof item === 'string' && item.trim()).map((item) => item.trim());
}

function toNumber(value?: number | string | null): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string' && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function formatNumber(value?: number | string | null, digits = 0): string {
  const number = toNumber(value);
  return number == null ? 'Unavailable' : number.toFixed(digits);
}

function formatPercent(value?: number | string | null): string {
  const number = toNumber(value);
  return number == null ? 'Unavailable' : `${number >= 0 ? '+' : ''}${number.toFixed(2)}%`;
}

function formatCurrency(value?: number | string | null): string {
  const number = toNumber(value);
  return number == null ? 'Unavailable' : `$${number.toFixed(2)}`;
}
