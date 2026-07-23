import { buildSectorThemeSearchItems } from '../src/features/sectors/sectorThemeSearchModel';
import { searchSectorThemeItems } from '../src/features/sectors/analysis/search';
import { generateSectorTabTestData } from '../src/data/sectorTabTestData';

function assert(condition: unknown, message: string) {
  if (!condition) throw new Error(message);
}

const testData = generateSectorTabTestData();
const items = buildSectorThemeSearchItems({ sectors: [], themes: [], testItems: [...testData.sectors, ...testData.themes] });
assert(items.length === testData.sectors.length + testData.themes.length, 'canonical search adapter includes all repository entities');
assert(searchSectorThemeItems(items, testData.sectors[0].name).some((item) => item.id === testData.sectors[0].id), 'search resolves sector names');
assert(searchSectorThemeItems(items, testData.themes[0].constituents[0].ticker).some((item) => item.id === testData.themes[0].id), 'search resolves governed member tickers');
console.log('PASS canonical sector/theme search model');
