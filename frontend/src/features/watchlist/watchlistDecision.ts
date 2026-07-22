import type { ClassifiedWatchlistItem, WatchlistClassification } from './types';

export type WatchlistDecisionGroup = 'action_required' | 'watching_closely' | 'stable_waiting';

export type WatchlistDecisionBrief = {
  deterioratingCount: number;
  deterioratingSymbols: string[];
  immediateCount: number;
  immediateSymbols: string[];
  improvingCount: number;
  improvingSymbols: string[];
  staleCount: number;
};

export const WATCHLIST_DECISION_ORDER: WatchlistDecisionGroup[] = [
  'action_required',
  'watching_closely',
  'stable_waiting',
];

export function getWatchlistDecisionGroup(item: ClassifiedWatchlistItem): WatchlistDecisionGroup {
  const { classification } = item;
  if (
    classification.group === 'needs_attention'
    || classification.group === 'high_priority'
    || classification.group === 'data_unavailable'
  ) {
    return 'action_required';
  }
  if (
    classification.group === 'momentum'
    || classification.primarySignal === 'partial'
    || classification.primarySignal === 'pending'
  ) {
    return 'watching_closely';
  }
  return 'stable_waiting';
}

export function groupWatchlistDecisionItems(items: ClassifiedWatchlistItem[]) {
  return items.reduce<Record<WatchlistDecisionGroup, ClassifiedWatchlistItem[]>>(
    (groups, item) => {
      groups[getWatchlistDecisionGroup(item)].push(item);
      return groups;
    },
    {
      action_required: [],
      stable_waiting: [],
      watching_closely: [],
    },
  );
}

export function buildWatchlistDecisionBrief(items: ClassifiedWatchlistItem[]): WatchlistDecisionBrief {
  const immediate = items.filter((item) => getWatchlistDecisionGroup(item) === 'action_required');
  const improving = items.filter((item) => (
    item.classification.group === 'high_priority' || item.classification.group === 'momentum'
  ));
  const deteriorating = items.filter((item) => (
    item.classification.group === 'needs_attention'
    && item.classification.primarySignal !== 'stale_data'
  ));
  return {
    deterioratingCount: deteriorating.length,
    deterioratingSymbols: symbols(deteriorating),
    immediateCount: immediate.length,
    immediateSymbols: symbols(immediate),
    improvingCount: improving.length,
    improvingSymbols: symbols(improving),
    staleCount: items.filter((item) => item.classification.dataStatus === 'stale').length,
  };
}

export function getWatchlistDecisionStatus(classification: WatchlistClassification): string {
  switch (classification.primarySignal) {
    case 'breakout':
      return 'Breakout confirmed; watch follow-through.';
    case 'near_breakout':
      return 'Waiting for breakout confirmation.';
    case 'strong_momentum':
      return 'Momentum is improving.';
    case 'relative_strength':
      return 'Relative strength is improving.';
    case 'volume_surge':
      return 'Volume participation is expanding.';
    case 'new_high':
      return 'Testing a new high.';
    case 'earnings_soon':
      return 'Earnings are approaching.';
    case 'major_news':
      return 'A current catalyst needs review.';
    case 'rating_upgrade':
      return 'The rating has improved.';
    case 'lost_support':
      return 'Price is below support.';
    case 'lost_ema':
      return 'Price lost its medium-term trend.';
    case 'weak_momentum':
      return 'Momentum is deteriorating.';
    case 'earnings_risk':
      return 'Earnings risk is elevated.';
    case 'stale_data':
      return 'Refresh data before making a decision.';
    case 'partial':
      return 'Quote is ready; deeper signals are loading.';
    case 'pending':
      return 'Analysis is being prepared.';
    case 'unavailable':
      return 'Current analysis is unavailable.';
    case 'watching':
    default:
      return 'Waiting for a clearer setup.';
  }
}

export function getWatchlistDecisionLabel(classification: WatchlistClassification): string {
  if (
    classification.group === 'needs_attention'
    || classification.group === 'high_priority'
    || classification.group === 'data_unavailable'
  ) {
    return 'Action';
  }
  if (
    classification.group === 'momentum'
    || classification.primarySignal === 'partial'
    || classification.primarySignal === 'pending'
  ) {
    return 'Watching';
  }
  return 'Stable';
}

function symbols(items: ClassifiedWatchlistItem[]) {
  return items.map((item) => item.item.ticker).slice(0, 4);
}
