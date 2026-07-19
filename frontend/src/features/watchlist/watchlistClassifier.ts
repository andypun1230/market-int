import type { WatchlistSummaryItem } from '@/types/market';

import type {
  WatchlistClassification,
  WatchlistDataStatus,
  WatchlistGroup,
  WatchlistSignalType,
} from './types';

const POSITIVE_WEIGHTS: Partial<Record<WatchlistSignalType, number>> = {
  breakout: 40,
  near_breakout: 25,
  strong_momentum: 20,
  relative_strength: 20,
  volume_surge: 15,
  new_high: 15,
  rating_upgrade: 15,
  earnings_soon: 10,
};

const NEGATIVE_WEIGHTS: Partial<Record<WatchlistSignalType, number>> = {
  lost_support: -40,
  lost_ema: -30,
  weak_momentum: -25,
  earnings_risk: -15,
  stale_data: -30,
  unavailable: -100,
};

export function classifyWatchlistItem(item: WatchlistSummaryItem): WatchlistClassification {
  const ticker = item.ticker.toUpperCase();
  const dataStatus = getDataStatus(item);

  if (dataStatus === 'unavailable') {
    return {
      dataStatus,
      group: 'data_unavailable',
      primarySignal: 'unavailable',
      reason: item.status_reason ?? 'Quote or setup data is unavailable for this ticker.',
      score: null,
      secondarySignals: [],
      severity: 'critical',
      ticker,
    };
  }

  if (dataStatus === 'pending') {
    return {
      dataStatus,
      group: 'watching',
      primarySignal: 'pending',
      reason: item.status_reason ?? 'Preparing analysis snapshot.',
      score: null,
      secondarySignals: [],
      severity: 'neutral',
      ticker,
    };
  }

  if (dataStatus === 'partial') {
    return {
      dataStatus,
      group: 'watching',
      primarySignal: 'partial',
      reason: item.status_reason ?? 'Quote is available while optional analysis metrics are still loading.',
      score: null,
      secondarySignals: [],
      severity: 'neutral',
      ticker,
    };
  }

  const positiveSignals = getPositiveSignals(item);
  const warningSignals = getWarningSignals(item, dataStatus);
  const score = calculateWatchlistScore(positiveSignals, warningSignals);

  if (warningSignals.length) {
    const primarySignal = warningSignals[0];
    return {
      dataStatus,
      group: 'needs_attention',
      primarySignal,
      reason: getReason(primarySignal, item),
      score,
      secondarySignals: [...warningSignals.slice(1), ...positiveSignals].slice(0, 3),
      severity: primarySignal === 'stale_data' ? 'warning' : 'critical',
      ticker,
    };
  }

  const highPrioritySignals = positiveSignals.filter((signal) =>
    ['breakout', 'near_breakout', 'earnings_soon', 'volume_surge', 'new_high', 'rating_upgrade'].includes(signal),
  );
  if (highPrioritySignals.length) {
    const primarySignal = highPrioritySignals[0];
    return {
      dataStatus,
      group: 'high_priority',
      primarySignal,
      reason: getReason(primarySignal, item),
      score,
      secondarySignals: positiveSignals.filter((signal) => signal !== primarySignal).slice(0, 3),
      severity: 'positive',
      ticker,
    };
  }

  if (positiveSignals.length) {
    const primarySignal = positiveSignals[0];
    return {
      dataStatus,
      group: 'momentum',
      primarySignal,
      reason: getReason(primarySignal, item),
      score,
      secondarySignals: positiveSignals.filter((signal) => signal !== primarySignal).slice(0, 3),
      severity: 'positive',
      ticker,
    };
  }

  return {
    dataStatus,
    group: 'watching',
    primarySignal: 'watching',
    reason: 'No major active setup or warning in the compact watchlist snapshot.',
    score,
    secondarySignals: [],
    severity: 'neutral',
    ticker,
  };
}

export function calculateWatchlistScore(
  positiveSignals: WatchlistSignalType[],
  warningSignals: WatchlistSignalType[],
) {
  const counted = new Set<WatchlistSignalType>();
  let score = 0;

  [...positiveSignals, ...warningSignals].forEach((signal) => {
    if (counted.has(signal)) {
      return;
    }
    counted.add(signal);
    score += POSITIVE_WEIGHTS[signal] ?? NEGATIVE_WEIGHTS[signal] ?? 0;
  });

  return Math.max(-100, Math.min(100, score));
}

export function getGroupLabel(group: WatchlistGroup) {
  switch (group) {
    case 'needs_attention':
      return 'Needs Attention';
    case 'high_priority':
      return 'High Priority';
    case 'momentum':
      return 'Momentum';
    case 'watching':
      return 'Watching';
    case 'data_unavailable':
      return 'Data Unavailable';
  }
}

export function getSignalLabel(signal: WatchlistSignalType) {
  switch (signal) {
    case 'breakout':
      return 'Breakout';
    case 'near_breakout':
      return 'Near Breakout';
    case 'strong_momentum':
      return 'Strong Momentum';
    case 'relative_strength':
      return 'Strong RS';
    case 'volume_surge':
      return 'Volume Surge';
    case 'new_high':
      return 'New High';
    case 'earnings_soon':
      return 'Earnings Soon';
    case 'major_news':
      return 'Catalyst';
    case 'rating_upgrade':
      return 'Rating Upgrade';
    case 'lost_support':
      return 'Lost Support';
    case 'lost_ema':
      return 'Lost 50 EMA';
    case 'weak_momentum':
      return 'Weak Momentum';
    case 'earnings_risk':
      return 'Earnings Risk';
    case 'stale_data':
      return 'Stale Data';
    case 'partial':
      return 'Partial';
    case 'pending':
      return 'Preparing Analysis';
    case 'unavailable':
      return 'Unavailable';
    case 'watching':
      return 'Watching';
  }
}

export function shouldShowWatchlistStatusDot(
  status: WatchlistDataStatus,
  primarySignal?: WatchlistSignalType,
) {
  return !(
    status === 'live' ||
    status === 'unavailable' ||
    (status === 'pending' && primarySignal === 'pending') ||
    (status === 'partial' && primarySignal === 'partial')
  );
}

function getDataStatus(item: WatchlistSummaryItem): WatchlistDataStatus {
  if (item.overall_status === 'pending') {
    return 'pending';
  }
  if (item.overall_status === 'partial') {
    return 'partial';
  }
  if (item.overall_status === 'unavailable' || item.overall_status === 'unsupported') {
    return 'unavailable';
  }
  if (item.overall_status === 'stale') {
    return 'stale';
  }
  if (typeof item.price !== 'number' || typeof item.change_percent !== 'number' || item.data_source === 'unavailable') {
    return 'unavailable';
  }
  if (item.is_stale) {
    return 'stale';
  }
  if (item.is_live) {
    return 'live';
  }
  if (item.data_source?.includes('generated_test_data') || item.data_source === 'test') {
    return 'test';
  }
  if (item.fallback_used || item.data_source?.includes('fallback')) {
    return 'cached';
  }
  if (item.data_source === 'local' || item.data_source === 'mock') {
    return 'mock';
  }
  return 'cached';
}

function getPositiveSignals(item: WatchlistSummaryItem): WatchlistSignalType[] {
  const signals: WatchlistSignalType[] = [];
  const setup = normalizeText(`${item.setup ?? ''} ${item.pattern_name ?? ''} ${item.trend ?? ''}`);
  const rsStatus = normalizeText(item.rs_status);
  const rating = normalizeText(item.rating);

  if (setup.includes('breakout') && !setup.includes('near')) {
    signals.push('breakout');
  } else if (setup.includes('breakout') || setup.includes('setup')) {
    signals.push('near_breakout');
  }
  if (typeof item.overall_score === 'number' && item.overall_score >= 80) {
    signals.push('strong_momentum');
  }
  if (rsStatus.includes('leading') || rsStatus.includes('strong') || (typeof item.rs_rank === 'number' && item.rs_rank <= 3)) {
    signals.push('relative_strength');
  }
  if (typeof item.pattern_confidence === 'number' && item.pattern_confidence >= 80) {
    signals.push('volume_surge');
  }
  if (rating.includes('a') || rating.includes('upgrade')) {
    signals.push('rating_upgrade');
  }

  return signals;
}

function getWarningSignals(item: WatchlistSummaryItem, dataStatus: WatchlistDataStatus): WatchlistSignalType[] {
  const signals: WatchlistSignalType[] = [];
  const trend = normalizeText(item.trend);
  const risk = normalizeText(item.risk_flag);
  const setup = normalizeText(`${item.setup ?? ''} ${item.support_zone ?? ''}`);

  if (dataStatus === 'stale') {
    signals.push('stale_data');
  }
  if (setup.includes('lost support') || setup.includes('break support')) {
    signals.push('lost_support');
  }
  if (trend.includes('weak') || trend.includes('bearish') || setup.includes('below 50')) {
    signals.push('lost_ema');
  }
  if (risk.includes('high') || risk.includes('elevated')) {
    signals.push('weak_momentum');
  }

  return signals;
}

function getReason(signal: WatchlistSignalType, item: WatchlistSummaryItem) {
  switch (signal) {
    case 'stale_data':
      return 'Quote data is stale, so the current setup should be treated cautiously.';
    case 'lost_support':
      return 'The compact snapshot indicates support has weakened.';
    case 'lost_ema':
      return 'Trend conditions have weakened in the compact snapshot.';
    case 'weak_momentum':
      return `${item.risk_flag ?? 'Risk'} risk is elevated relative to the watchlist.`;
    case 'breakout':
      return `${item.pattern_name ?? 'The setup'} is flagged as a breakout candidate.`;
    case 'near_breakout':
      return `${item.setup ?? 'The setup'} is close enough to monitor.`;
    case 'relative_strength':
      return `${item.rs_status ?? 'Relative strength'} ranks strongly versus the watchlist.`;
    case 'strong_momentum':
      return `Overall score ${item.overall_score ?? 'N/A'} supports momentum monitoring.`;
    case 'volume_surge':
      return `Pattern confidence ${item.pattern_confidence ?? 'N/A'} suggests unusually active setup quality.`;
    case 'rating_upgrade':
      return `${item.rating ?? 'Rating'} is among the strongest compact ratings.`;
    default:
      return 'Watchlist snapshot is available, but no stronger signal is active.';
  }
}

function normalizeText(value?: string | null) {
  return (value ?? '').toLowerCase();
}
