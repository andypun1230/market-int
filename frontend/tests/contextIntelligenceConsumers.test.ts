import {
  HOME_MARKET_EVENT_LIMIT,
  shouldRequestEntityCatalysts,
  shouldRequestStockMaterialEvents,
  shouldRequestWatchlistCatalysts,
  watchlistBatchLimitation,
  watchlistSavedSymbolsLabel,
} from '../src/features/context-intelligence/consumerPolicy';
import { buildNewsConsumerPresentation } from '../src/features/context-intelligence/newsIntelligenceNormalizer';
import type { NewsEventModel, NewsIntelligenceModel } from '../src/features/context-intelligence/types';

function assert(condition: unknown, message: string) {
  if (!condition) throw new Error(message);
}

function newsEvent(index: number): NewsEventModel {
  return {
    id: `event-${index}`,
    headline: `Event ${index}`,
    summary: null,
    sourceName: 'Primary source',
    sourceQuality: 'primary',
    publishedAt: '2026-07-22T10:00:00Z',
    eventStatus: 'confirmed',
    eventType: 'macro_policy',
    materiality: { market: 80, entity: 70, user: 60 },
    affectedEntities: [],
    reactionSummary: null,
    evidenceIds: [`evidence-${index}`],
    state: 'live',
  };
}

function model(overrides: Partial<NewsIntelligenceModel> = {}): NewsIntelligenceModel {
  return {
    state: 'live',
    status: 'complete',
    provider: 'licensed-provider',
    asOf: '2026-07-22T10:00:00Z',
    events: [1, 2, 3, 4, 5].map(newsEvent),
    contradictions: [],
    evidenceCount: 5,
    limitations: [],
    errors: [],
    ...overrides,
  };
}

const home = buildNewsConsumerPresentation({
  model: model(),
  title: 'What Moved the Market',
  maxItems: HOME_MARKET_EVENT_LIMIT,
});
assert(home.items.length === 3, 'Home presents at most three market events');
assert(home.title === 'What Moved the Market', 'Home uses the required consumer title');

const unavailable = buildNewsConsumerPresentation({
  model: model({
    state: 'unavailable',
    status: 'unavailable',
    events: [],
    limitations: ['Licensed news provider is unavailable.'],
  }),
  title: 'Catalysts',
});
assert(unavailable.stateLabel === 'Unavailable', 'unavailable consumers remain visibly unavailable');
assert(unavailable.message?.includes('Licensed news provider'), 'backend limitation is surfaced');

const failed = buildNewsConsumerPresentation({
  model: model({ state: 'failed', status: 'failed', events: [] }),
  title: 'Material Events',
});
assert(failed.message?.includes('Other screen data is unaffected'), 'consumer failure is explicitly isolated');

assert(!shouldRequestStockMaterialEvents(false, 'overview'), 'closed stock detail does not fetch material events');
assert(!shouldRequestStockMaterialEvents(true, 'technical'), 'non-overview stock tab does not fetch material events');
assert(shouldRequestStockMaterialEvents(true, 'overview'), 'open stock overview fetches material events');
assert(shouldRequestEntityCatalysts(true, false), 'selected live entity requests catalysts');
assert(!shouldRequestEntityCatalysts(true, true), 'test entity never requests live catalysts');

assert(!shouldRequestWatchlistCatalysts({ activeTab: 'stocks', focused: true, hydrated: false, symbolCount: 2 }), 'watchlist waits for saved state hydration');
assert(!shouldRequestWatchlistCatalysts({ activeTab: 'themes', focused: true, hydrated: true, symbolCount: 2 }), 'non-stock watchlist tabs do not request stock catalysts');
assert(shouldRequestWatchlistCatalysts({ activeTab: 'stocks', focused: true, hydrated: true, symbolCount: 2 }), 'focused hydrated stock watchlist requests one batch');

const savedLabel = watchlistSavedSymbolsLabel(2);
assert(savedLabel === '2 saved symbols · batched request', 'watchlist language describes explicit saved symbols and batching');
assert(!/holding|portfolio|position|owned/i.test(savedLabel), 'watchlist catalyst copy never implies ownership');
assert(watchlistBatchLimitation(Array.from({ length: 51 }, (_, index) => `S${index}`))?.includes('50-saved-symbol'), 'over-limit watchlists surface an explicit coverage limitation');
