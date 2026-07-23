import type { SectorThemeSearchItem } from '@/features/sectors/sectorThemeSearchModel';

export function searchSectorThemeItems(items: SectorThemeSearchItem[], query: string) {
  const normalized = query.trim().toLowerCase();
  if (!normalized) {
    return [];
  }
  return items.filter((item) => {
    return item.keywords.some((keyword) => keyword.toLowerCase().includes(normalized));
  });
}
