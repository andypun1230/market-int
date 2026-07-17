export type SectorThemeFavourite = {
  id: string;
  type: 'sector' | 'theme';
  addedAt: string;
};

const STORAGE_KEY = 'sector-tab:favourites:v1';
let memoryStore: SectorThemeFavourite[] = [];

export function loadSectorThemeFavourites(): SectorThemeFavourite[] {
  try {
    const raw = getStorage()?.getItem(STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : memoryStore;
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed
      .filter(isFavourite)
      .sort((a, b) => a.addedAt.localeCompare(b.addedAt));
  } catch {
    return memoryStore;
  }
}

export function saveSectorThemeFavourites(favourites: SectorThemeFavourite[]) {
  const unique = dedupeFavourites(favourites);
  memoryStore = unique;
  try {
    getStorage()?.setItem(STORAGE_KEY, JSON.stringify(unique));
  } catch {
    // In-memory fallback is enough when persistent storage is unavailable.
  }
  return unique;
}

export function toggleSectorThemeFavourite(
  favourites: SectorThemeFavourite[],
  item: { id: string; type: 'sector' | 'theme' },
) {
  const exists = favourites.some((favourite) => favourite.id === item.id && favourite.type === item.type);
  if (exists) {
    return favourites.filter((favourite) => !(favourite.id === item.id && favourite.type === item.type));
  }
  return dedupeFavourites([
    ...favourites,
    {
      addedAt: new Date().toISOString(),
      id: item.id,
      type: item.type,
    },
  ]);
}

export function getFavouriteKey(favourite: Pick<SectorThemeFavourite, 'id' | 'type'>) {
  return `${favourite.type}:${favourite.id}`;
}

function dedupeFavourites(favourites: SectorThemeFavourite[]) {
  const seen = new Set<string>();
  return favourites.filter((favourite) => {
    const key = getFavouriteKey(favourite);
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

function getStorage() {
  if (typeof globalThis === 'undefined') {
    return null;
  }
  return 'localStorage' in globalThis ? globalThis.localStorage : null;
}

function isFavourite(value: unknown): value is SectorThemeFavourite {
  if (!value || typeof value !== 'object') {
    return false;
  }
  const candidate = value as Partial<SectorThemeFavourite>;
  return (
    (candidate.type === 'sector' || candidate.type === 'theme') &&
    typeof candidate.id === 'string' &&
    typeof candidate.addedAt === 'string'
  );
}
