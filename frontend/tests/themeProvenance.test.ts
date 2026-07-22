import { themeTabProvenance } from '../src/features/themes/themeProvenance';
import { formatThemeTaxonomyLabel } from '../src/features/themes/presentation';

function assert(condition: unknown, message: string) {
  if (!condition) throw new Error(message);
}

const live = themeTabProvenance({
  snapshotId: 'theme-live-1', marketDate: '2026-07-17', sourceState: 'live', status: 'complete',
  alerts: [], overlap: [], warnings: [], pilotScope: 'Rank reflects the leadership composite among the 2 currently active reviewed pilot themes.',
  items: [
    { memberCount: 7 },
    { memberCount: 7 },
  ],
} as never);

assert(live.title === 'Themes' && live.subtitle === 'Reviewed live ThemeSnapshot · 2026-07-17', 'Themes uses ThemeSnapshot provenance');
assert(live.badges.includes('2 live pilot themes') && live.badges.includes('14/14 approved member histories ready'), 'Themes presents live pilot provenance');
assert(!JSON.stringify(live).includes('S&P 100') && !JSON.stringify(live).includes('coverage'), 'Themes never inherits SectorSnapshot provenance');

const unavailable = themeTabProvenance(null);
assert(unavailable.subtitle === 'Reviewed ThemeSnapshot unavailable.' && unavailable.badges.length === 0, 'no live ThemeSnapshot renders its review gate provenance');
assert(formatThemeTaxonomyLabel('information_technology') === 'Information Technology', 'taxonomy IDs are formatted only for display');
