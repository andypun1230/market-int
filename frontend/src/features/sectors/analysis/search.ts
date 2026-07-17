import type { SectorThemeTestItem } from '@/data/sectorTabTestData';

export function searchSectorThemeItems(items: SectorThemeTestItem[], query: string) {
  const normalized = query.trim().toLowerCase();
  if (!normalized) {
    return [];
  }
  return items.filter((item) => {
    const keywords = [
      item.id,
      item.name,
      item.type,
      item.type === 'theme' ? item.parentSector : '',
      ...item.constituents.map((stock) => stock.ticker),
      ...item.constituents.map((stock) => stock.companyName ?? ''),
    ];
    return keywords.some((keyword) => keyword.toLowerCase().includes(normalized));
  });
}
