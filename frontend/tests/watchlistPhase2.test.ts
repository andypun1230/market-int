import { classifyWatchlistItem, calculateWatchlistScore, getSignalLabel, shouldShowWatchlistStatusDot } from '../src/features/watchlist/watchlistClassifier';
import { hasRefreshingWatchlistItems } from '../src/hooks/useWatchlistDashboard';
import { groupSortedWatchlistItems, sortWatchlistItems } from '../src/features/watchlist/watchlistSort';
import type { ClassifiedWatchlistItem } from '../src/features/watchlist/types';
import type { WatchlistSummaryItem } from '../src/types/market';

function assert(condition: unknown, message: string) {
  if (!condition) {
    throw new Error(message);
  }
}

function item(overrides: Partial<WatchlistSummaryItem>): WatchlistSummaryItem {
  return {
    ticker: 'BASE',
    trend: 'Constructive',
    setup: 'Normal watch',
    support_zone: 'Above support',
    risk_flag: 'Managed',
    price: 100,
    change_percent: 0.5,
    data_source: 'mock',
    is_live: false,
    is_stale: false,
    fallback_used: false,
    as_of: '2026-07-11T00:00:00.000Z',
    ...overrides,
  };
}

function classified(overrides: Partial<WatchlistSummaryItem>, originalIndex = 0): ClassifiedWatchlistItem {
  const watchlistItem = item(overrides);
  return {
    classification: classifyWatchlistItem(watchlistItem),
    item: watchlistItem,
    originalIndex,
  };
}

function run() {
  const breakout = classifyWatchlistItem(item({ setup: 'Confirmed breakout', ticker: 'BRK' }));
  assert(breakout.group === 'high_priority', 'confirmed breakout goes to High Priority');
  assert(breakout.primarySignal === 'breakout', 'breakout is the primary signal');

  const lostSupport = classifyWatchlistItem(item({ setup: 'Lost support at 50', ticker: 'LOW' }));
  assert(lostSupport.group === 'needs_attention', 'lost support goes to Needs Attention');
  assert(lostSupport.primarySignal === 'lost_support', 'lost support is primary warning');

  const momentum = classifyWatchlistItem(item({ overall_score: 88, setup: 'Normal watch', ticker: 'MOM' }));
  assert(momentum.group === 'momentum', 'strong score goes to Momentum when no higher-priority event exists');
  assert(momentum.primarySignal === 'strong_momentum', 'strong momentum signal is primary');

  const watching = classifyWatchlistItem(item({ ticker: 'NORM' }));
  assert(watching.group === 'watching', 'normal saved stock goes to Watching');

  const unavailable = classifyWatchlistItem(item({ change_percent: null, price: null, ticker: 'BAD' }));
  assert(unavailable.group === 'data_unavailable', 'missing quote data goes to Data Unavailable');
  assert(unavailable.score === null, 'unavailable score is null');

  const aaplComplete = classifyWatchlistItem(item({
    analysis_snapshot_id: 'stock-AAPL-v1',
    overall_status: 'complete',
    price: 200,
    ticker: 'AAPL',
  }));
  assert(aaplComplete.group !== 'data_unavailable', 'complete AAPL snapshot is never grouped under Data Unavailable');

  const msftComplete = classifyWatchlistItem(item({
    analysis_snapshot_id: 'stock-MSFT-v1',
    overall_status: 'complete',
    price: 400,
    ticker: 'MSFT',
  }));
  assert(msftComplete.group !== 'data_unavailable', 'complete MSFT snapshot is never grouped under Data Unavailable');

  const partial = classifyWatchlistItem(item({
    overall_status: 'partial',
    status_reason: 'Quote and trend available; advanced signals are still loading.',
    ticker: 'PART',
  }));
  assert(partial.primarySignal === 'partial' && getSignalLabel(partial.primarySignal) === 'Partial', 'partial stock is labelled Partial with an explicit reason');
  assert(partial.reason.includes('advanced signals'), 'partial stock preserves its canonical reason ahead of secondary warnings');

  const pending = classifyWatchlistItem(item({
    overall_status: 'pending',
    status_reason: 'Preparing analysis snapshot.',
    ticker: 'PEND',
  }));
  assert(pending.primarySignal === 'pending' && getSignalLabel(pending.primarySignal) === 'Preparing Analysis', 'pending stock is labelled Preparing Analysis');
  assert(!shouldShowWatchlistStatusDot('pending', 'pending'), 'pending uses one status badge instead of duplicate badges');

  const stale = classifyWatchlistItem(item({
    overall_status: 'stale',
    status_reason: 'Showing the latest compatible analysis while it refreshes.',
    ticker: 'STALE-SNAPSHOT',
  }));
  assert(stale.group !== 'data_unavailable', 'stale usable analysis is not misclassified as unavailable');
  assert(!shouldShowWatchlistStatusDot('unavailable', 'unavailable'), 'unavailable state never renders a duplicate status badge');
  assert(hasRefreshingWatchlistItems([item({ overall_status: 'pending', refreshing: true })]), 'pending canonical analysis schedules one follow-up summary read');
  assert(!hasRefreshingWatchlistItems([item({ overall_status: 'partial', refreshing: false })]), 'stable partial analysis does not poll the summary endpoint');

  const staleBreakout = classifyWatchlistItem(item({ is_stale: true, setup: 'Confirmed breakout', ticker: 'STALE' }));
  assert(staleBreakout.group === 'needs_attention', 'warning precedence beats high-priority setup');
  assert(staleBreakout.primarySignal === 'stale_data', 'stale data is primary warning');
  assert(!shouldShowWatchlistStatusDot('stale', 'stale_data'), 'stale signal suppresses a duplicate stale data badge');

  const duplicateScore = calculateWatchlistScore(['breakout', 'breakout'], ['lost_support', 'lost_support']);
  assert(duplicateScore === 0, 'duplicate signals are not double-counted');

  const entries = [
    classified({ ticker: 'AAA', setup: 'Normal watch', change_percent: 0.1 }, 0),
    classified({ ticker: 'BBB', setup: 'Confirmed breakout', change_percent: 2.5 }, 1),
    classified({ ticker: 'CCC', setup: 'Lost support', change_percent: -1.1 }, 2),
    classified({ ticker: 'DDD', overall_score: 91, setup: 'Normal watch', change_percent: 1.4 }, 3),
    classified({ ticker: 'EEE', change_percent: null, price: null }, 4),
  ];
  const smart = sortWatchlistItems(entries, 'smartPriority');
  assert(smart.map((entry) => entry.item.ticker).join(',') === 'CCC,BBB,DDD,AAA,EEE', 'smart priority uses group precedence');

  const dailyGain = sortWatchlistItems(entries, 'dailyGain');
  assert(dailyGain[0].item.ticker === 'BBB', 'daily gain sorting puts strongest gain first');
  assert(dailyGain[dailyGain.length - 1].item.ticker === 'EEE', 'missing gain sorts last');

  const dailyLoss = sortWatchlistItems(entries, 'dailyLoss');
  assert(dailyLoss[0].item.ticker === 'CCC', 'daily loss sorting puts weakest move first');
  assert(dailyLoss[dailyLoss.length - 1].item.ticker === 'EEE', 'missing loss sorts last');

  const manual = sortWatchlistItems([...entries].reverse(), 'manualOrder');
  assert(manual.map((entry) => entry.originalIndex).join(',') === '0,1,2,3,4', 'manual order preserves saved order');

  const grouped = groupSortedWatchlistItems(smart);
  const totalGrouped = Object.values(grouped).reduce((sum, group) => sum + group.length, 0);
  assert(totalGrouped === entries.length, 'each stock appears in exactly one group');
  assert(grouped.needs_attention.length === 1, 'empty/non-empty groups are deterministic');
  assert(grouped.data_unavailable.length === 1, 'unavailable group receives missing-data items');
}

run();
