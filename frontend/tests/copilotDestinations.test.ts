import {
  normalizeDestinationId,
  resolveCopilotAction,
} from '../src/features/copilot/navigation/copilotDestinations';

function assert(condition: unknown, message: string) {
  if (!condition) throw new Error(message);
}

function run() {
  assert(normalizeDestinationId('indexes') === 'market_indexes', 'backend indexes alias maps to the shared registry');
  assert(normalizeDestinationId('health') === 'market_health', 'backend health alias maps to the shared registry');
  assert(normalizeDestinationId('fear_greed') === 'market_decision', 'backend fear_greed alias maps to Decision');
  assert(normalizeDestinationId('leadership') === 'leadership_scanner', 'backend leadership alias maps to the scanner');
  assert(normalizeDestinationId('macro') === 'market_macro', 'backend macro alias maps to Market Macro');

  const stock = resolveCopilotAction({
    actionId: 'stock-technical',
    actionType: 'open_entity',
    destination: 'stock_technical',
    entity: 'NVDA',
    label: 'Open NVDA Technical',
    parameters: { sectionId: 'stocks', stockTab: 'technical', subTab: 'technical', symbol: 'NVDA' },
    route: '/watchlist',
    sectionId: 'stocks',
    subTab: 'technical',
  });
  assert(stock?.pathname === '/watchlist', 'stock action opens Watchlist detail');
  assert(stock?.params?.section === 'stocks', 'stock sub-tab never replaces the top-level Stocks section');
  assert(stock?.params?.detailTab === 'technical', 'stock technical action selects the Technical detail tab');
  assert(stock?.params?.symbol === 'NVDA', 'stock action retains its entity symbol');

  const fearGreed = resolveCopilotAction({
    actionType: 'navigate', destinationId: 'fear_greed', label: 'Open Fear & Greed', route: '/market', tab: 'decision', subTab: 'fear-greed',
  });
  assert(fearGreed?.params?.section === 'decision', 'market sub-tab does not replace the Decision top-level section');

  const leadership = resolveCopilotAction({ actionType: 'navigate', destinationId: 'leadership', label: 'Open Leadership', route: '/sectors' });
  assert(leadership?.pathname === '/sectors' && leadership.params?.section === 'emergingLeadership', 'leadership opens the canonical Sectors scanner');

  const unsafe = resolveCopilotAction({ actionType: 'navigate', label: 'Unsafe', route: 'https://example.com' });
  assert(unsafe === null, 'unregistered external routes are rejected');

  console.log('PASS Copilot destination aliases, stock detail tabs, section routing, and route safety');
}

run();
