type CacheEntry<T> = {
  expiresAt: number;
  value: T;
};

const cache = new Map<string, CacheEntry<unknown>>();
const inflight = new Map<string, Promise<unknown>>();
const NETWORK_DEBUG = process.env.EXPO_PUBLIC_NETWORK_DEBUG === 'true';

export async function cachedRequest<T>(
  key: string,
  fetcher: () => Promise<T>,
  ttlMs: number,
): Promise<T> {
  const now = Date.now();
  const cached = cache.get(key);
  if (cached && cached.expiresAt > now) {
    debugLog('cache hit', key);
    return cached.value as T;
  }

  const pending = inflight.get(key);
  if (pending) {
    debugLog('dedupe', key);
    return pending as Promise<T>;
  }

  debugLog('start', key);
  const request = fetcher()
    .then((value) => {
      cache.set(key, {
        value,
        expiresAt: Date.now() + ttlMs,
      });
      debugLog('end', key);
      return value;
    })
    .catch((error) => {
      if (isRequestCancelled(error)) {
        debugLog('cancelled', key);
      }
      throw error;
    })
    .finally(() => {
      inflight.delete(key);
    });

  inflight.set(key, request);
  return request;
}

export function isRequestCancelled(error: unknown): boolean {
  if (!error) {
    return false;
  }
  if (error instanceof DOMException && error.name === 'AbortError') {
    return true;
  }
  const message = error instanceof Error ? error.message : String(error);
  const normalized = message.toLowerCase();
  return (
    normalized.includes('abort') ||
    normalized.includes('aborted') ||
    normalized.includes('canceled') ||
    normalized.includes('cancelled') ||
    normalized.includes('fetch request has been canceled')
  );
}

function debugLog(event: string, key: string) {
  if (NETWORK_DEBUG) {
    console.log(`[network] ${event}: ${key}`);
  }
}

export function clearRequestCache(prefix?: string) {
  if (!prefix) {
    cache.clear();
    inflight.clear();
    return;
  }

  for (const key of cache.keys()) {
    if (key.startsWith(prefix)) {
      cache.delete(key);
    }
  }

  for (const key of inflight.keys()) {
    if (key.startsWith(prefix)) {
      inflight.delete(key);
    }
  }
}
