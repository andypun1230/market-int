import { classifyWatchlistItem } from '../src/features/watchlist/watchlistClassifier';
import { getWatchlistDecisionGroup, getWatchlistMaintenanceState } from '../src/features/watchlist/watchlistDecision';
import { buildWatchlistCountModel } from '../src/features/watchlist/watchlistCounts';
import type { WatchlistSummaryItem } from '../src/types/market';

function assert(condition: unknown, message: string) { if (!condition) throw new Error(message); }
const item = (overrides: Partial<WatchlistSummaryItem> = {}): WatchlistSummaryItem => ({ ticker: 'ABC', trend: 'Constructive', setup: 'Normal watch', support_zone: 'Above support', risk_flag: 'Managed', price: 10, change_percent: 1, data_source: 'live', is_live: true, ...overrides });
const classify = (overrides: Partial<WatchlistSummaryItem>) => { const value = item(overrides); return { classification: classifyWatchlistItem(value), item: value, originalIndex: 0 }; };
const freshAction = classify({ setup: 'Confirmed breakout' });
assert(getWatchlistDecisionGroup(freshAction) === 'action_now', 'fresh actionable item');
const staleAction = classify({ setup: 'Confirmed breakout', is_stale: true });
assert(getWatchlistDecisionGroup(staleAction) === 'action_now' && getWatchlistMaintenanceState(staleAction.classification) === 'data_needs_refresh', 'stale actionable preserves both dimensions');
const staleMonitor = classify({ is_stale: true });
assert(getWatchlistDecisionGroup(staleMonitor) === 'monitor', 'stale alone is not Action Now');
const unavailable = classify({ price: null, change_percent: null, data_source: 'unavailable' });
assert(getWatchlistDecisionGroup(unavailable) === 'monitor' && getWatchlistMaintenanceState(unavailable.classification) === 'unavailable', 'unavailable is maintenance, not trading urgency');
const partial = classify({ overall_status: 'partial' });
assert(getWatchlistMaintenanceState(partial.classification) === 'partial_data', 'partial is maintenance');
const counts = buildWatchlistCountModel({ locallySavedSymbols: ['AAPL'], displayedItems: [item({ ticker: 'AAPL', overall_status: 'complete', analysis_status: 'complete' }), item({ ticker: 'MSFT', overall_status: 'partial' })], catalystSymbols: ['AAPL'] });
assert(counts.locallySaved === 1 && counts.displayed === 2 && counts.catalystRequested === 1 && counts.partial === 1, 'counts reconcile independently');
assert(counts.catalystScopeExplanation.includes('1 locally saved') && counts.catalystScopeExplanation.includes('2 stocks are displayed'), 'narrow catalyst scope is explained');
console.log('PASS Stage 10.2 Watchlist trading and maintenance semantics');
