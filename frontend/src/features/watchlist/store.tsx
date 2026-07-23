import * as FileSystem from 'expo-file-system/legacy';
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';

import {
  buildWatchlistKey,
  dedupeWatchlistItems,
  isWatchlistItemInList,
  migrateWatchlistData,
  normalizeNewWatchlistItem,
  normalizeWatchlistId,
  toWatchlistTitle,
  toggleItemInWatchlist,
  type GroupWatchlistItem,
  type NewWatchlistItem,
  type StockWatchlistItem,
  type UnifiedWatchlistItem,
  type WatchlistItemType,
} from '@/features/watchlist/domain';

export {
  buildNextWatchlistItems,
  buildWatchlistKey,
  migrateWatchlistData,
  normalizeWatchlistId,
  normalizeWatchlistItemType,
  toggleItemInWatchlist,
} from '@/features/watchlist/domain';
export type {
  BaseWatchlistItem,
  GroupWatchlistItem,
  NewWatchlistItem,
  StockWatchlistItem,
  UnifiedWatchlistItem,
  WatchlistItemType,
} from '@/features/watchlist/domain';

type WatchlistContextValue = {
  addSector: (id: string, name: string) => void;
  addStock: (ticker: string, name?: string) => void;
  addTheme: (id: string, name: string) => void;
  getGroupItems: () => GroupWatchlistItem[];
  getStockItems: () => StockWatchlistItem[];
  groupItems: GroupWatchlistItem[];
  hydrated: boolean;
  isInWatchlist: (type: WatchlistItemType, id: string) => boolean;
  items: UnifiedWatchlistItem[];
  loading: boolean;
  removeSector: (id: string) => void;
  removeStock: (ticker: string) => void;
  removeTheme: (id: string) => void;
  storageError: string | null;
  stockItems: StockWatchlistItem[];
  toggleWatchlistItem: (item: NewWatchlistItem) => void;
};

const CANONICAL_WATCHLIST_STORAGE_KEY = 'market-intelligence:watchlist:v2';
const LEGACY_WATCHLIST_STORAGE_KEYS = ['watchlist:v2'];
const LEGACY_SECTOR_FAVOURITES_KEY = 'sector-tab:favourites:v1';

const WatchlistContext = createContext<WatchlistContextValue | undefined>(undefined);

export function WatchlistProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<UnifiedWatchlistItem[]>([]);
  const [hydrated, setHydrated] = useState(false);
  const [storageError, setStorageError] = useState<string | null>(null);
  const itemsRef = useRef<UnifiedWatchlistItem[]>([]);
  const pendingRemovedKeysRef = useRef(new Set<string>());

  useEffect(() => {
    itemsRef.current = items;
  }, [items]);

  useEffect(() => {
    let active = true;

    async function hydrate() {
      try {
        const storedItems = await loadAndMigrateWatchlist();
        if (!active) {
          return;
        }
        setItems((previous) => {
          const merged = mergeWatchlistItems(storedItems, previous).filter(
            (item) => !pendingRemovedKeysRef.current.has(buildWatchlistKey(item.type, item.id)),
          );
          itemsRef.current = merged;
          return merged;
        });
        setStorageError(null);
      } catch (error) {
        if (active) {
          const message = error instanceof Error ? error.message : 'Watchlist storage unavailable.';
          setStorageError(message);
        }
      } finally {
        if (active) {
          setHydrated(true);
        }
      }
    }

    void hydrate();

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (hydrated && itemsRef.current.length) {
      void persistWatchlist(itemsRef.current, setStorageError);
    }
  }, [hydrated]);

  const toggleWatchlistItem = useCallback((input: NewWatchlistItem) => {
    const normalized = normalizeNewWatchlistItem(input);
    const targetKey = buildWatchlistKey(normalized.type, normalized.id);
    const previousItems = itemsRef.current;
    const exists = previousItems.some((item) => buildWatchlistKey(item.type, item.id) === targetKey);
    const nextItems = toggleItemInWatchlist(previousItems, normalized);

    if (exists) {
      pendingRemovedKeysRef.current.add(targetKey);
    } else {
      pendingRemovedKeysRef.current.delete(targetKey);
    }

    itemsRef.current = nextItems;
    setItems(nextItems);

    if (hydrated) {
      void persistWatchlist(nextItems, setStorageError).catch((error) => {
        itemsRef.current = previousItems;
        setItems(previousItems);
        const message = error instanceof Error ? error.message : 'Watchlist storage unavailable.';
        setStorageError(message);
      });
    }
  }, [hydrated]);

  const addStock = useCallback((ticker: string, name?: string) => {
    const normalizedTicker = normalizeWatchlistId('stock', ticker);
    const key = buildWatchlistKey('stock', normalizedTicker);
    if (!itemsRef.current.some((item) => buildWatchlistKey(item.type, item.id) === key)) {
      toggleWatchlistItem({ id: normalizedTicker, name, ticker: normalizedTicker, type: 'stock' });
    }
  }, [toggleWatchlistItem]);

  const removeStock = useCallback((ticker: string) => {
    const normalizedTicker = normalizeWatchlistId('stock', ticker);
    if (isWatchlistItemInList(itemsRef.current, 'stock', normalizedTicker)) {
      toggleWatchlistItem({ id: normalizedTicker, ticker: normalizedTicker, type: 'stock' });
    }
  }, [toggleWatchlistItem]);

  const addSector = useCallback((id: string, name: string) => {
    const normalizedId = normalizeWatchlistId('sector', id);
    if (!isWatchlistItemInList(itemsRef.current, 'sector', normalizedId)) {
      toggleWatchlistItem({ id: normalizedId, name, type: 'sector' });
    }
  }, [toggleWatchlistItem]);

  const removeSector = useCallback((id: string) => {
    const normalizedId = normalizeWatchlistId('sector', id);
    if (isWatchlistItemInList(itemsRef.current, 'sector', normalizedId)) {
      toggleWatchlistItem({ id: normalizedId, name: toWatchlistTitle(normalizedId), type: 'sector' });
    }
  }, [toggleWatchlistItem]);

  const addTheme = useCallback((id: string, name: string) => {
    const normalizedId = normalizeWatchlistId('theme', id);
    if (!isWatchlistItemInList(itemsRef.current, 'theme', normalizedId)) {
      toggleWatchlistItem({ id: normalizedId, name, type: 'theme' });
    }
  }, [toggleWatchlistItem]);

  const removeTheme = useCallback((id: string) => {
    const normalizedId = normalizeWatchlistId('theme', id);
    if (isWatchlistItemInList(itemsRef.current, 'theme', normalizedId)) {
      toggleWatchlistItem({ id: normalizedId, name: toWatchlistTitle(normalizedId), type: 'theme' });
    }
  }, [toggleWatchlistItem]);

  const isInWatchlist = useCallback((type: WatchlistItemType, id: string) => {
    return isWatchlistItemInList(itemsRef.current, type, id);
  }, []);

  const stockItems = useMemo(
    () => items.filter((item): item is StockWatchlistItem => item.type === 'stock'),
    [items],
  );
  const groupItems = useMemo(
    () => items.filter((item): item is GroupWatchlistItem => item.type === 'sector' || item.type === 'theme'),
    [items],
  );

  const value = useMemo<WatchlistContextValue>(() => ({
    addSector,
    addStock,
    addTheme,
    getGroupItems: () => groupItems,
    getStockItems: () => stockItems,
    groupItems,
    hydrated,
    isInWatchlist,
    items,
    loading: !hydrated,
    removeSector,
    removeStock,
    removeTheme,
    storageError,
    stockItems,
    toggleWatchlistItem,
  }), [
    addSector,
    addStock,
    addTheme,
    groupItems,
    hydrated,
    isInWatchlist,
    items,
    removeSector,
    removeStock,
    removeTheme,
    storageError,
    stockItems,
    toggleWatchlistItem,
  ]);

  return <WatchlistContext.Provider value={value}>{children}</WatchlistContext.Provider>;
}

export function useWatchlist() {
  const context = useContext(WatchlistContext);
  if (!context) {
    throw new Error('useWatchlist must be used inside WatchlistProvider');
  }
  return context;
}

function mergeWatchlistItems(storedItems: UnifiedWatchlistItem[], currentItems: UnifiedWatchlistItem[]) {
  return dedupeWatchlistItems([...storedItems, ...currentItems]);
}

async function loadAndMigrateWatchlist() {
  const [canonical, ...legacyValues] = await Promise.all([
    readJson(CANONICAL_WATCHLIST_STORAGE_KEY),
    ...LEGACY_WATCHLIST_STORAGE_KEYS.map((key) => readJson(key)),
    readJson(LEGACY_SECTOR_FAVOURITES_KEY),
  ]);
  const legacyGroups = legacyValues.at(-1);
  const storedCandidates = [canonical, ...legacyValues.slice(0, -1)];
  return dedupeWatchlistItems(storedCandidates.flatMap((candidate) => migrateWatchlistData(candidate, [])).concat(migrateWatchlistData(null, legacyGroups)));
}

async function persistWatchlist(items: UnifiedWatchlistItem[], setStorageError: (value: string | null) => void) {
  await writeJson(CANONICAL_WATCHLIST_STORAGE_KEY, { items, version: 2 });
  setStorageError(null);
}

async function readJson(key: string) {
  const storage = getWebStorage();
  if (storage) {
    const raw = storage.getItem(key);
    return raw ? JSON.parse(raw) : null;
  }
  const raw = await readFileStorage(key);
  return raw ? JSON.parse(raw) : null;
}

async function writeJson(key: string, value: unknown) {
  const raw = JSON.stringify(value);
  const storage = getWebStorage();
  if (storage) {
    storage.setItem(key, raw);
    return;
  }
  await writeFileStorage(key, raw);
}

function getWebStorage() {
  if (typeof globalThis === 'undefined') {
    return null;
  }
  return 'localStorage' in globalThis ? globalThis.localStorage : null;
}

async function readFileStorage(key: string) {
  const path = getFileStoragePath(key);
  if (!path) {
    return null;
  }
  const info = await FileSystem.getInfoAsync(path);
  if (!info.exists) {
    return null;
  }
  return FileSystem.readAsStringAsync(path);
}

async function writeFileStorage(key: string, raw: string) {
  const path = getFileStoragePath(key);
  const directory = FileSystem.documentDirectory;
  if (!path || !directory) {
    throw new Error('Persistent file storage unavailable.');
  }
  await FileSystem.makeDirectoryAsync(directory, { intermediates: true });
  await FileSystem.writeAsStringAsync(path, raw);
}

function getFileStoragePath(key: string) {
  if (!FileSystem.documentDirectory) {
    return null;
  }
  return `${FileSystem.documentDirectory}${key.replace(/[^a-z0-9-]/gi, '-')}.json`;
}
