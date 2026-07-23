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
    entry('STALE', 'watching', 'stale_data', 'stale'),
  ];

  assert(getWatchlistDecisionGroup(items[0]) === 'weakening', 'deteriorating setups remain a trading weakening state');
  assert(getWatchlistDecisionGroup(items[1]) === 'action_now', 'near-term opportunities require action');
  assert(getWatchlistDecisionGroup(items[2]) === 'improving', 'improving momentum is explicit');
  assert(getWatchlistDecisionGroup(items[3]) === 'monitor', 'partial analysis remains a maintenance issue, not a trading conclusion');
  assert(getWatchlistDecisionGroup(items[4]) === 'monitor', 'neutral setups remain monitor-only');

  const groups = groupWatchlistDecisionItems(items);
  assert(groups.action_now.map((item) => item.item.ticker).join(',') === 'BRK', 'action group contains trading triggers only');
  assert(groups.improving.length === 1 && groups.weakening.length === 1, 'improving and weakening remain separate');
  assert(groups.monitor.length === 3, 'partial, quiet, and stale-only items remain monitor trading states');

  const brief = buildWatchlistDecisionBrief(items);
  assert(brief.immediateCount === 1, 'brief counts trading action stocks only');
  assert(brief.improvingCount === 2, 'brief counts improving setups');
  assert(brief.deterioratingCount === 1, 'brief does not mislabel stale data as setup deterioration');
  assert(brief.staleCount === 1, 'brief exposes stale data warning');
  assert(brief.immediateSymbols.join(',') === 'BRK', 'brief names only current trading triggers');

  assert(getWatchlistDecisionStatus(items[0].classification) === 'Price is below support.', 'lost support has concise decision copy');
  assert(getWatchlistDecisionStatus(items[1].classification).includes('breakout'), 'near breakout has concise decision copy');
  assert(getWatchlistDecisionStatus(items[4].classification) === 'Waiting for a clearer setup.', 'stable setup has waiting copy');
}

run();
