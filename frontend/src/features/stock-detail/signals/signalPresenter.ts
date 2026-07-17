import type {
  MultiTimeframeTechnicalSignals,
  RelativeStrengthItem,
  StockLeadershipSignal,
  VolumeAnalysis,
} from '@/types/market';

export type SignalExecutiveSummary = {
  headline: string;
  body: string;
  source: 'rule_based' | 'unavailable';
  evidenceKeys: string[];
};

export type ComparisonStrength =
  | 'strongly_weaker'
  | 'weaker'
  | 'in_line'
  | 'stronger'
  | 'strongly_stronger'
  | 'unavailable';

export type VolumeParticipationState =
  | 'weak'
  | 'below_average'
  | 'average'
  | 'strong'
  | 'exceptional'
  | 'unavailable';

export function buildSignalSummary({
  leadership,
  relativeStrength,
  timeframeSignals,
  volume,
}: {
  leadership?: StockLeadershipSignal;
  relativeStrength?: RelativeStrengthItem;
  timeframeSignals?: MultiTimeframeTechnicalSignals | null;
  volume?: VolumeAnalysis;
}): SignalExecutiveSummary {
  const momentum = describeMomentum(timeframeSignals);
  const participation = describeParticipation(volume);
  const leadershipLabel = formatLeadershipSignal(leadership?.signal);
  const missingConfirmation = getMissingConfirmation(relativeStrength, volume, leadership);

  if (momentum === 'unavailable' && participation === 'unavailable' && !leadership) {
    return {
      headline: 'Signal summary unavailable',
      body: 'Signal inputs are currently insufficient. Relative strength, participation, and leadership confirmation will appear when reliable data is available.',
      evidenceKeys: [],
      source: 'unavailable',
    };
  }

  return {
    headline: `Momentum is ${momentum}, while participation is ${participation}.`,
    body: `${buildLeadershipSentence(leadershipLabel, relativeStrength)} ${missingConfirmation}`,
    evidenceKeys: ['multi_timeframe', 'relative_strength', 'volume_participation', 'leadership'],
    source: 'rule_based',
  };
}

export function classifyComparison(score?: number | null): ComparisonStrength {
  if (typeof score !== 'number' || !Number.isFinite(score)) {
    return 'unavailable';
  }
  if (score < 35) {
    return 'strongly_weaker';
  }
  if (score < 45) {
    return 'weaker';
  }
  if (score <= 55) {
    return 'in_line';
  }
  if (score <= 65) {
    return 'stronger';
  }
  return 'strongly_stronger';
}

export function comparisonLabel(strength: ComparisonStrength): string {
  switch (strength) {
    case 'strongly_weaker':
      return 'Strongly weaker';
    case 'weaker':
      return 'Weaker';
    case 'in_line':
      return 'In line';
    case 'stronger':
      return 'Stronger';
    case 'strongly_stronger':
      return 'Strongly stronger';
    default:
      return 'Unavailable';
  }
}

export function relativeStrengthInterpretation(relativeStrength?: RelativeStrengthItem): string {
  if (!relativeStrength) {
    return 'Relative strength data is unavailable.';
  }
  const spy = classifyComparison(relativeStrength.rs_vs_spy);
  const qqq = classifyComparison(relativeStrength.rs_vs_qqq);
  const sector = classifyComparison(relativeStrength.rs_vs_sector);
  if (sector === 'stronger' || sector === 'strongly_stronger') {
    if (qqq === 'weaker' || qqq === 'strongly_weaker') {
      return 'Sector performance is stronger, but QQQ confirmation remains weaker.';
    }
    return 'Sector-relative performance is constructive.';
  }
  if (spy === 'weaker' || spy === 'strongly_weaker') {
    return 'Market-relative performance is weak.';
  }
  return 'Performance is near the market average and has not yet established leadership.';
}

export function getVolumeParticipationState(volume?: VolumeAnalysis): VolumeParticipationState {
  if (!volume || volume.relative_volume == null) {
    return 'unavailable';
  }
  if (volume.relative_volume >= 2 || volume.volume_quality_score >= 85) {
    return 'exceptional';
  }
  if (volume.relative_volume >= 1.5 || volume.volume_quality_score >= 70) {
    return 'strong';
  }
  if (volume.relative_volume >= 1) {
    return 'average';
  }
  if (volume.relative_volume >= 0.6) {
    return 'below_average';
  }
  return 'weak';
}

export function volumeStateLabel(state: VolumeParticipationState): string {
  switch (state) {
    case 'below_average':
      return 'Below average';
    case 'exceptional':
      return 'Exceptional';
    case 'strong':
      return 'Strong';
    case 'average':
      return 'Average';
    case 'weak':
      return 'Weak';
    default:
      return 'Unavailable';
  }
}

export function getActiveVolumeSignals(volume?: VolumeAnalysis): string[] {
  if (!volume) {
    return [];
  }
  const signals = [
    volume.relative_volume != null && volume.relative_volume >= 1.5 ? 'Volume surge' : null,
    volume.breakout_volume ? 'Breakout participation' : null,
    volume.accumulation_volume ? 'Accumulation present' : null,
    volume.distribution_volume ? 'Distribution present' : null,
    volume.dry_up ? 'Volume dry-up' : null,
    volume.climax_run ? 'Climax activity' : null,
  ];
  return signals.filter((signal): signal is string => signal != null).slice(0, 4);
}

export function volumeInterpretation(volume?: VolumeAnalysis): string {
  const state = getVolumeParticipationState(volume);
  if (state === 'unavailable') {
    return 'Volume participation data is unavailable.';
  }
  if (volume?.distribution_volume) {
    return 'Distribution is present, so participation is not cleanly supportive.';
  }
  if (volume?.accumulation_volume && (state === 'strong' || state === 'exceptional')) {
    return 'Above-normal buying supports the move.';
  }
  if (volume?.accumulation_volume) {
    return 'Accumulation is present, but participation is closer to normal.';
  }
  return `${volumeStateLabel(state)} participation adds limited confirmation.`;
}

export function formatLeadershipSignal(signal?: StockLeadershipSignal['signal']): string {
  switch (signal) {
    case 'leader':
      return 'Leader';
    case 'emerging_leader':
      return 'Emerging Leader';
    case 'follower':
      return 'Follower';
    case 'lagging':
      return 'Lagging';
    default:
      return 'Unavailable';
  }
}

export function leadershipPreview(leadership?: StockLeadershipSignal): string {
  if (!leadership) {
    return 'Leadership signal unavailable';
  }
  return `${formatLeadershipSignal(leadership.signal)}${leadership.score == null ? '' : ` · ${leadership.score}/100`} · ${leadership.availableInputs}/${leadership.requiredInputs} inputs`;
}

function describeMomentum(signals?: MultiTimeframeTechnicalSignals | null): string {
  const states = [signals?.short?.signal, signals?.medium?.signal].filter(Boolean);
  if (!states.length) {
    return 'unavailable';
  }
  if (states.some((state) => state === 'strong_bullish' || state === 'bullish')) {
    return 'constructive';
  }
  if (states.every((state) => state === 'neutral')) {
    return 'neutral';
  }
  if (states.some((state) => state === 'bearish' || state === 'strong_bearish')) {
    return 'weakening';
  }
  return 'mixed';
}

function describeParticipation(volume?: VolumeAnalysis): string {
  const state = getVolumeParticipationState(volume);
  if (state === 'below_average') {
    return 'below average';
  }
  return volumeStateLabel(state).toLowerCase();
}

function buildLeadershipSentence(label: string, relativeStrength?: RelativeStrengthItem): string {
  if (label === 'Unavailable') {
    return 'Leadership confirmation is unavailable from the current inputs.';
  }
  const rsLabel = comparisonLabel(classifyComparison(relativeStrength?.overall_rs_score)).toLowerCase();
  return `Leadership remains at ${label.toLowerCase()} because relative strength is ${rsLabel}.`;
}

function getMissingConfirmation(
  relativeStrength?: RelativeStrengthItem,
  volume?: VolumeAnalysis,
  leadership?: StockLeadershipSignal,
): string {
  if (!relativeStrength) {
    return 'Relative strength confirmation is the most important missing input.';
  }
  if (classifyComparison(relativeStrength.rs_vs_qqq) === 'weaker' || classifyComparison(relativeStrength.rs_vs_qqq) === 'strongly_weaker') {
    return 'Stronger outperformance versus QQQ would improve leadership confirmation.';
  }
  if (!volume || volume.relative_volume == null) {
    return 'Reliable participation data would improve signal confirmation.';
  }
  if (leadership?.signal === 'unavailable') {
    return 'More complete leadership inputs are needed before ranking this as a leader.';
  }
  return 'Continued benchmark and sector outperformance would provide cleaner confirmation.';
}
