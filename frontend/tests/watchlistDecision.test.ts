import {
  buildWatchlistDecisionBrief,
  getWatchlistDecisionGroup,
  getWatchlistDecisionStatus,
  groupWatchlistDecisionItems,
} from '../src/features/watchlist/watchlistDecision';
import type { ClassifiedWatchlistItem, WatchlistClassification, WatchlistGroup, WatchlistSignalType } from '../src/features/watchlist/types';

function assert(condition: unknown, message: string) {
  if (!condition) throw new Error(message);
}

function entry(
  ticker: string,
  group: WatchlistGroup,
  primarySignal: WatchlistSignalType,
  dataStatus: WatchlistClassification['dataStatus'] = 'live',
): ClassifiedWatchlistItem {
  return {
    classification: {
      dataStatus,
      group,
      primarySignal,
      reason: 'Existing analytics reason.',
      score: 50,
      secondarySignals: [],
      severity: group === 'needs_attention' ? 'critical' : group === 'watching' ? 'neutral' : 'positive',
      ticker,
    },
    item: {
      risk_flag: 'Managed',
      setup: 'Existing setup',
      support_zone: 'Above support',
      ticker,
      trend: 'Constructive',
    },
    originalIndex: 0,
  };
}

function run() {
  const items = [
    entry('LOW', 'needs_attention', 'lost_support'),
    entry('BRK', 'high_priority', 'near_breakout'),
    entry('MOM', 'momentum', 'strong_momentum'),
    entry('LOAD', 'watching', 'partial', 'partial'),
    entry('WAIT', 'watching', 'watching'),
    entry('STALE', 'needs_attention', 'stale_data', 'stale'),
  ];

  assert(getWatchlistDecisionGroup(items[0]) === 'action_required', 'deteriorating setups require action');
  assert(getWatchlistDecisionGroup(items[1]) === 'action_required', 'near-term opportunities require action');
  assert(getWatchlistDecisionGroup(items[2]) === 'watching_closely', 'improving momentum is watched closely');
  assert(getWatchlistDecisionGroup(items[3]) === 'watching_closely', 'partial analysis is watched closely');
  assert(getWatchlistDecisionGroup(items[4]) === 'stable_waiting', 'neutral setups remain stable and waiting');

  const groups = groupWatchlistDecisionItems(items);
  assert(groups.action_required.map((item) => item.item.ticker).join(',') === 'LOW,BRK,STALE', 'action group preserves sorted input order');
  assert(groups.watching_closely.length === 2, 'watching closely combines improving and loading setups');
  assert(groups.stable_waiting.length === 1, 'stable section contains quiet setups');

  const brief = buildWatchlistDecisionBrief(items);
  assert(brief.immediateCount === 3, 'brief counts immediate attention stocks');
  assert(brief.improvingCount === 2, 'brief counts improving setups');
  assert(brief.deterioratingCount === 1, 'brief does not mislabel stale data as setup deterioration');
  assert(brief.staleCount === 1, 'brief exposes stale data warning');
  assert(brief.immediateSymbols.join(',') === 'LOW,BRK,STALE', 'brief names the highest-priority symbols');

  assert(getWatchlistDecisionStatus(items[0].classification) === 'Price is below support.', 'lost support has concise decision copy');
  assert(getWatchlistDecisionStatus(items[1].classification).includes('breakout'), 'near breakout has concise decision copy');
  assert(getWatchlistDecisionStatus(items[4].classification) === 'Waiting for a clearer setup.', 'stable setup has waiting copy');
}

run();
