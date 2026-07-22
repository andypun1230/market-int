import {
  buildCommandRegistry,
  buildMostActiveCommands,
  buildTickerCommand,
  groupCommands,
  searchCommands,
  type CommandItem,
} from '../src/features/command/commandModel';
import { normalizeRecentSearches } from '../src/features/command/recentSearchesModel';

function assert(condition: unknown, message: string) {
  if (!condition) throw new Error(message);
}

function run() {
  const registry = buildCommandRegistry();
  const breadth = registry.find((item) => item.id === 'feature-market-breadth');
  assert(breadth?.pathname === '/market', 'breadth command routes to Market');
  assert(breadth?.params?.section === 'breadth', 'breadth command selects the Breadth sub-tab');
  assert(breadth?.params?.commandTarget === 'breadth', 'breadth command carries a highlight target');

  const rotation = registry.find((item) => item.id === 'feature-theme-rotation');
  assert(rotation?.pathname === '/sectors', 'theme rotation command routes to Sectors');
  assert(rotation?.params?.section === 'themesRotation', 'theme rotation selects the Themes rotation sub-tab');

  const energy = searchCommands(registry, 'energy')[0];
  assert(energy?.id === 'sector-energy', 'sector names are searchable');
  assert(energy.params?.entityKind === 'sector' && energy.params.entityId === 'energy', 'sector result preserves detail deep-link parameters');

  const memory = searchCommands(registry, 'memory')[0];
  assert(memory?.params?.entityId === 'memory_storage', 'theme result uses the canonical theme id');

  const unknownTicker = buildTickerCommand('adbe');
  assert(unknownTicker?.title === 'ADBE', 'valid free-form tickers normalize to uppercase');
  assert(unknownTicker?.pathname === '/watchlist' && unknownTicker.params?.symbol === 'ADBE', 'free-form tickers open Stock Detail through Watchlist');
  assert(buildTickerCommand('market breadth') === null, 'feature phrases are not misclassified as tickers');

  const active = buildMostActiveCommands([
    { changePercent: 0.5, isLive: true, symbol: 'AAPL' },
    { changePercent: -3.2, fallbackUsed: true, source: 'cache', symbol: 'MSFT' },
    { changePercent: 1.1, isLive: true, isStale: true, symbol: 'NVDA' },
  ]);
  assert(active.map((item) => item.title).join(',') === 'MSFT,NVDA,AAPL', 'most active symbols sort by absolute daily move');
  assert(active.map((item) => item.sourceState).join(',') === 'cached,delayed,live', 'most active symbols expose explicit provenance');

  const grouped = groupCommands(searchCommands(registry, 'market'));
  assert(grouped.some((group) => group.category === 'App Features'), 'search results are grouped by category');
  assert(grouped.some((group) => group.category === 'Reports'), 'cross-category search retains reports');

  const recentSource = [breadth, rotation, breadth, ...registry.slice(0, 10)].filter(Boolean) as CommandItem[];
  const recents = normalizeRecentSearches(recentSource);
  assert(recents.length === 8, 'recent history is bounded');
  assert(recents[0].id === 'feature-market-breadth' && recents[1].id === 'feature-theme-rotation', 'recent history preserves newest-first order');
  assert(new Set(recents.map((item) => item.id)).size === recents.length, 'recent history is deduplicated deterministically');
  assert(normalizeRecentSearches([{ id: 'invalid' }, null]).length === 0, 'invalid persisted history is ignored safely');

  console.log('PASS command search registry, deep links, provenance, and recent history');
}

run();
