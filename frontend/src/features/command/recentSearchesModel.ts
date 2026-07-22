import type { CommandItem } from './commandModel';

const MAX_RECENTS = 8;

export function normalizeRecentSearches(items: unknown): CommandItem[] {
  if (!Array.isArray(items)) return [];
  const seen = new Set<string>();
  return items.flatMap((item) => {
    if (!isCommandItem(item) || seen.has(item.id)) return [];
    seen.add(item.id);
    return [item];
  }).slice(0, MAX_RECENTS);
}

function isCommandItem(value: unknown): value is CommandItem {
  if (!value || typeof value !== 'object') return false;
  const item = value as Partial<CommandItem>;
  return typeof item.id === 'string'
    && typeof item.title === 'string'
    && typeof item.category === 'string'
    && typeof item.pathname === 'string'
    && typeof item.metadata === 'string'
    && Array.isArray(item.keywords);
}
