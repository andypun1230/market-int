import { useCallback, useEffect, useState } from 'react';
import * as FileSystem from 'expo-file-system/legacy';

import type { CommandItem } from './commandModel';
import { normalizeRecentSearches } from './recentSearchesModel';

const STORAGE_KEY = 'market-intelligence-command-recents-v1';

let memoryRecents: CommandItem[] = [];
let hasLoaded = false;
let loadPromise: Promise<void> | null = null;
let mutationVersion = 0;
const listeners = new Set<(items: CommandItem[]) => void>();

export function useRecentSearches() {
  const [items, setItems] = useState(memoryRecents);
  const [loaded, setLoaded] = useState(hasLoaded);

  useEffect(() => {
    listeners.add(setItems);
    if (!hasLoaded) {
      ensureLoaded().then(() => {
        setLoaded(true);
      });
    }
    return () => {
      listeners.delete(setItems);
    };
  }, []);

  const addRecent = useCallback((item: CommandItem) => {
    mutationVersion += 1;
    memoryRecents = normalizeRecentSearches([item, ...memoryRecents]);
    hasLoaded = true;
    setLoaded(true);
    notify();
    persist(memoryRecents);
  }, []);

  const clearRecents = useCallback(() => {
    mutationVersion += 1;
    memoryRecents = [];
    hasLoaded = true;
    setLoaded(true);
    notify();
    persist(memoryRecents);
  }, []);

  return { addRecent, clearRecents, items, loaded };
}

function notify() {
  listeners.forEach((listener) => listener(memoryRecents));
}

async function loadRecents(): Promise<unknown> {
  try {
    const raw = getWebStorage()?.getItem(STORAGE_KEY) ?? await readFileStorage();
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function ensureLoaded() {
  if (hasLoaded) return Promise.resolve();
  if (!loadPromise) {
    const startingVersion = mutationVersion;
    loadPromise = loadRecents().then((loadedItems) => {
      if (mutationVersion === startingVersion) memoryRecents = normalizeRecentSearches(loadedItems);
      hasLoaded = true;
      notify();
    }).finally(() => {
      loadPromise = null;
    });
  }
  return loadPromise;
}

function persist(items: CommandItem[]) {
  const raw = JSON.stringify(items);
  try {
    getWebStorage()?.setItem(STORAGE_KEY, raw);
  } catch {
    // Native file persistence remains available when web storage is unavailable.
  }
  writeFileStorage(raw).catch(() => {
    // Search history is best-effort and must not block navigation.
  });
}

function getWebStorage(): Storage | null {
  if (typeof globalThis === 'undefined' || !('localStorage' in globalThis)) return null;
  return globalThis.localStorage;
}

async function readFileStorage() {
  const path = getFilePath();
  if (!path) return null;
  const info = await FileSystem.getInfoAsync(path);
  return info.exists ? FileSystem.readAsStringAsync(path) : null;
}

async function writeFileStorage(raw: string) {
  const path = getFilePath();
  if (!path || !FileSystem.documentDirectory) return;
  await FileSystem.makeDirectoryAsync(FileSystem.documentDirectory, { intermediates: true });
  await FileSystem.writeAsStringAsync(path, raw);
}

function getFilePath() {
  return FileSystem.documentDirectory ? `${FileSystem.documentDirectory}${STORAGE_KEY}.json` : null;
}
