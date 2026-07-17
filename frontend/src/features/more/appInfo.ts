import Constants from 'expo-constants';

import { API_URL } from '@/services/api';

export function getAppInfo() {
  const manifest = Constants.expoConfig;
  return {
    apiUrl: API_URL,
    buildNumber: manifest?.ios?.buildNumber ?? manifest?.android?.versionCode?.toString() ?? 'Development',
    environment: __DEV__ ? 'Development' : 'Production',
    name: manifest?.name ?? 'Market Intelligence',
    slug: manifest?.slug ?? 'market-intelligence',
    version: manifest?.version ?? '1.0.0',
  };
}

export function formatDateTime(value?: string | null) {
  if (!value) {
    return 'N/A';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return 'N/A';
  }
  return date.toLocaleString(undefined, {
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    month: 'short',
    year: 'numeric',
  });
}

export function formatProviderName(provider?: string | null) {
  if (!provider) {
    return 'Unavailable';
  }
  const normalized = provider.toLowerCase();
  if (normalized === 'polygon' || normalized === 'massive') {
    return 'Polygon / Massive';
  }
  if (normalized === 'generated_test_data' || normalized === 'test') {
    return 'Test Data';
  }
  return provider.replace(/_/g, ' ').replace(/\b\w/g, (character) => character.toUpperCase());
}
