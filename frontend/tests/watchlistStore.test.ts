import {
  buildWatchlistKey,
  buildNextWatchlistItems,
  migrateWatchlistData,
  normalizeWatchlistId,
  normalizeWatchlistItemType,
} from '../src/features/watchlist/domain';

function assert(condition: unknown, message: string) {
  if (!condition) {
    throw new Error(message);
  }
}

function run() {
  assert(normalizeWatchlistItemType('stocks') === 'stock', 'normalizes legacy stock plural type');
  assert(normalizeWatchlistItemType('sectors') === 'sector', 'normalizes legacy sector plural type');
  assert(normalizeWatchlistItemType('industry_group') === 'theme', 'normalizes legacy industry group type');
  assert(normalizeWatchlistId('stock', 'mu') === 'MU', 'stock ids normalize to ticker case');
  assert(normalizeWatchlistId('sector', 'Technology') === 'information_technology', 'sector aliases normalize to canonical sector ids');
  assert(normalizeWatchlistId('theme', 'AI Infrastructure') === 'ai-infrastructure', 'theme ids normalize to stable slug');
  assert(buildWatchlistKey('sector', 'Technology') === 'sector:information_technology', 'sector key is canonical');
  assert(buildWatchlistKey('theme', 'Technology') === 'theme:technology', 'theme key remains distinct from sector key');

  const migrated = migrateWatchlistData(
    {
      items: [
        { type: 'stock', ticker: 'mu', addedAt: '2026-01-01T00:00:00.000Z' },
        { type: 'sector', id: 'Technology', name: 'Technology' },
        { type: 'sectors', id: 'Technology', name: 'Technology duplicate' },
        { type: 'theme', id: 'AI Infrastructure', name: 'AI Infrastructure' },
        { type: 'industry_group', id: 'Memory', name: 'Memory' },
        { type: 'stock', ticker: 'MU' },
      ],
    },
    [
      { type: 'sector', id: 'financials', addedAt: '2026-01-02T00:00:00.000Z' },
      { type: 'theme', id: 'cybersecurity', addedAt: '2026-01-02T00:00:00.000Z' },
      { type: 'sector', id: 'financials', addedAt: '2026-01-03T00:00:00.000Z' },
    ],
  );

  const keys = migrated.map((item) => buildWatchlistKey(item.type, item.id));
  assert(keys.includes('stock:MU'), 'migrates stock watchlist item');
  assert(keys.includes('sector:information_technology'), 'migrates sector item to canonical id');
  assert(keys.includes('theme:ai-infrastructure'), 'migrates theme item');
  assert(keys.includes('theme:memory'), 'migrates legacy industry group as theme');
  assert(keys.includes('sector:financials'), 'migrates legacy sector favourite');
  assert(keys.includes('theme:cybersecurity'), 'migrates legacy theme favourite');
  assert(keys.filter((key) => key === 'stock:MU').length === 1, 'deduplicates duplicate stocks');
  assert(keys.filter((key) => key === 'sector:information_technology').length === 1, 'deduplicates duplicate sector aliases');
  assert(keys.filter((key) => key === 'sector:financials').length === 1, 'legacy migration is idempotent');
  assert(keys.includes('theme:technology') === false, 'sector does not become theme accidentally');

  const withSector = buildNextWatchlistItems([], { id: 'Technology', name: 'Technology', type: 'sector' });
  assert(withSector.length === 1, 'adds sector item');
  assert(buildWatchlistKey(withSector[0].type, withSector[0].id) === 'sector:information_technology', 'stores canonical sector id');
  const withoutSector = buildNextWatchlistItems(withSector, { id: 'Technology', name: 'Technology', type: 'sector' });
  assert(withoutSector.length === 0, 'second sector toggle removes item');
  const sectorAndTheme = buildNextWatchlistItems(withSector, { id: 'Technology', name: 'Technology Theme', type: 'theme' });
  assert(sectorAndTheme.length === 2, 'sector and theme with same display id remain distinct');
  assert(sectorAndTheme.some((item) => buildWatchlistKey(item.type, item.id) === 'theme:technology'), 'theme with same id is preserved');
}

run();
