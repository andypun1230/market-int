const DEFAULT_API_BASE_URL = 'http://localhost:8000';

function normalizeBaseUrl(value: string | undefined): string {
  const trimmed = value?.trim() || DEFAULT_API_BASE_URL;
  return trimmed.replace(/\/+$/, '');
}

export const API_URL = normalizeBaseUrl(process.env.EXPO_PUBLIC_API_BASE_URL);

if (typeof __DEV__ !== 'undefined' && __DEV__) {
  console.log(`[API] Base URL: ${API_URL}`);
}
