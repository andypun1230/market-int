import type { SectorThemeTestItem, TestHeatmapInterval } from '@/data/sectorTabTestData';
import type { SectorRow } from '@/features/sectors/sectorSnapshot';
import type { LiveThemeItem } from '@/features/themes/themeSnapshot';

export type SectorThemeSearchItem = {
  id: string;
  keywords: string[];
  name: string;
  sourceState: string;
  status: string;
  type: 'sector' | 'theme';
  values: Record<TestHeatmapInterval, number | null>;
};

export function buildSectorThemeSearchItems({
  sectors,
  testItems,
  themes,
}: {
  sectors: SectorRow[];
  testItems: SectorThemeTestItem[];
  themes: LiveThemeItem[];
}): SectorThemeSearchItem[] {
  if (testItems.length) return testItems.map(fromTestItem);
  return [...sectors.map(fromSector), ...themes.map(fromTheme)];
}

function fromTestItem(item: SectorThemeTestItem): SectorThemeSearchItem {
  return {
    id: item.id,
    keywords: [
      item.id,
      item.name,
      item.type,
      item.type === 'theme' ? item.parentSector : '',
      ...item.constituents.flatMap((stock) => [stock.ticker, stock.companyName ?? '']),
    ],
    name: item.name,
    sourceState: 'test',
    status: capitalize(item.quadrant),
    type: item.type,
    values: item.returns,
  };
}

function fromSector(item: SectorRow): SectorThemeSearchItem {
  return {
    id: item.sectorId,
    keywords: [item.sectorId, item.displayName, item.etfSymbol, 'sector'],
    name: item.displayName,
    sourceState: 'snapshot',
    status: item.classification,
    type: 'sector',
    values: item.returns,
  };
}

function fromTheme(item: LiveThemeItem): SectorThemeSearchItem {
  return {
    id: item.id,
    keywords: [item.id, item.name, item.parentSector, ...item.aliases, ...item.members.flatMap((member) => [member.ticker, member.companyName])],
    name: item.name,
    sourceState: item.sourceState,
    status: item.classification,
    type: 'theme',
    values: item.returns,
  };
}

function capitalize(value: string) {
  return `${value.charAt(0).toUpperCase()}${value.slice(1)}`;
}
