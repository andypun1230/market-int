import { themeTabProvenance } from '../src/features/themes/themeProvenance';
import { formatThemeTaxonomyLabel } from '../src/features/themes/presentation';

function assert(condition: unknown, message: string) {
  if (!condition) throw new Error(message);
}

const live = themeTabProvenance({
  snapshotId: 'theme-live-1', marketDate: '2026-07-17', sourceState: 'live', status: 'complete',
  alerts: [], overlap: [], warnings: [], pilotScope: 'Rank reflects the leadership composite among the 2 currently active reviewed pilot themes.',
  items: [
    { memberCount: 7, status: 'available' },
    { memberCount: 7, status: 'available' },
  ],
} as never);

assert(live.title === 'Themes' && live.subtitle === 'Canonical Theme Intelligence · market data 2026-07-17', 'Themes uses canonical Theme Intelligence provenance');
assert(live.badges.includes('2 launch themes') && live.badges.includes('2 available · 0 partial') && live.badges.includes('14 mapped constituents'), 'Themes presents canonical taxonomy and availability provenance');
assert(!JSON.stringify(live).includes('S&P 100') && !JSON.stringify(live).includes('coverage'), 'Themes never inherits SectorSnapshot provenance');

const unavailable = themeTabProvenance(null);
assert(unavailable.subtitle === 'Canonical Theme Intelligence directory unavailable.' && unavailable.badges.length === 0, 'no canonical Theme Intelligence directory renders unavailable provenance');
assert(formatThemeTaxonomyLabel('information_technology') === 'Information Technology', 'taxonomy IDs are formatted only for display');
