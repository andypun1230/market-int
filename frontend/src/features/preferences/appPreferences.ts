import { useCallback, useEffect, useState } from 'react';
import * as FileSystem from 'expo-file-system/legacy';

import {
  DEFAULT_PREFERENCES,
  mergePreferences,
  migratePreferences,
  type AppPreferences,
  type AppearancePreferences,
  type DataUsagePreferences,
  type LanguagePreferences,
  type LocalProfilePreferences,
  type NotificationPreferences,
} from './appPreferencesModel';

export type {
  AppPreferences,
  AppearancePreferences,
  DataUsagePreferences,
  LanguagePreferences,
  LocalProfilePreferences,
  NotificationPreferences,
};

const STORAGE_KEY = 'market-intelligence-app-preferences-v1';

let memoryPreferences: AppPreferences = DEFAULT_PREFERENCES;
let hasLoaded = false;
const listeners = new Set<(preferences: AppPreferences) => void>();

export function useAppPreferences() {
  const [preferences, setPreferences] = useState(memoryPreferences);
  const [loaded, setLoaded] = useState(hasLoaded);

  useEffect(() => {
    listeners.add(setPreferences);
    if (!hasLoaded) {
      loadPreferences().then((loadedPreferences) => {
        memoryPreferences = loadedPreferences;
        hasLoaded = true;
        setLoaded(true);
        notify();
      });
    }
    return () => {
      listeners.delete(setPreferences);
    };
  }, []);

  const updatePreferences = useCallback((patch: Partial<AppPreferences>) => {
    memoryPreferences = mergePreferences(memoryPreferences, patch);
    hasLoaded = true;
    setLoaded(true);
    notify();
    savePreferences(memoryPreferences);
  }, []);

  return { loaded, preferences, updatePreferences };
}

export function getDefaultPreferences() {
  return DEFAULT_PREFERENCES;
}

export function migratePreferencesForTests(value: unknown) {
  return migratePreferences(value);
}

function notify() {
  for (const listener of listeners) {
    listener(memoryPreferences);
  }
}

async function loadPreferences(): Promise<AppPreferences> {
  try {
    const raw = getWebStorage()?.getItem(STORAGE_KEY) ?? await readFileStorage();
    return migratePreferences(raw ? JSON.parse(raw) : null);
  } catch {
    return DEFAULT_PREFERENCES;
  }
}

function savePreferences(preferences: AppPreferences) {
  const raw = JSON.stringify(preferences);
  try {
    getWebStorage()?.setItem(STORAGE_KEY, raw);
  } catch {
    // Preferences are best-effort; native file storage remains available.
  }
  writeFileStorage(raw).catch(() => {
    // Preference persistence failure should not block the settings UI.
  });
}

function getWebStorage(): Storage | null {
  if (typeof globalThis === 'undefined' || !('localStorage' in globalThis)) {
    return null;
  }
  return globalThis.localStorage;
}

async function readFileStorage() {
  const path = getFilePath();
  if (!path) {
    return null;
  }
  const info = await FileSystem.getInfoAsync(path);
  if (!info.exists) {
    return null;
  }
  return FileSystem.readAsStringAsync(path);
}

async function writeFileStorage(raw: string) {
  const path = getFilePath();
  if (!path || !FileSystem.documentDirectory) {
    return;
  }
  await FileSystem.makeDirectoryAsync(FileSystem.documentDirectory, { intermediates: true });
  await FileSystem.writeAsStringAsync(path, raw);
}

function getFilePath() {
  return FileSystem.documentDirectory ? `${FileSystem.documentDirectory}${STORAGE_KEY}.json` : null;
}
