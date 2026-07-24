import { initialAtomicScreenState, reduceAtomicScreenState } from '../src/features/trust/atomicScreenState';
import { isLatestAsyncDataRequest } from '../src/hooks/useAsyncData';
import { getThemeDetail, getThemeRotation, getThemeSnapshot } from '../src/services/api';
import {
  cachedRequest,
  clearRequestCache,
  isRequestCancelled,
  requestCacheDiagnostics,
} from '../src/services/requestCache';

function assert(condition: unknown, message: string) {
  if (!condition) throw new Error(message);
}

const summary = {
  contract: 'theme_summary_v1',
  snapshot_id: 'theme-stage12-2',
  taxonomy_version: '2026.07.1',
  market_date: '2026-07-22',
  source_state: 'live',
  status: 'available',
  items: [],
};

const rotation = {
  contract: 'theme_rotation_summary_v1',
  snapshot_id: 'theme-stage12-2',
  taxonomy_version: '2026.07.1',
  as_of: '2026-07-22T21:00:00Z',
  timeframe: '1M',
  profile: 'medium',
  rotation_model_version: 'theme-relative-trend-momentum-v1',
  status: 'available',
  snapshot_status: 'available',
  benchmark: 'SPY',
  points: [],
  exclusions: [],
  timeframe_definition: {},
};

async function run() {
  const originalFetch = globalThis.fetch;
  const urls: string[] = [];
  const pending: { resolve: (response: Response) => void; url: string }[] = [];
  globalThis.fetch = ((input) => {
    const url = String(input);
    urls.push(url);
    return new Promise<Response>((resolve) => pending.push({ resolve, url }));
  }) as typeof fetch;
  try {
    clearRequestCache();
    const summaryPromise = getThemeSnapshot();
    const firstRotation = getThemeRotation('1M');
    const duplicateRotation = getThemeRotation('1M');
    await Promise.resolve();
    assert(urls.length === 2, 'summary and rotation start together while identical rotation requests dedupe');
    assert(urls.some((url) => url.endsWith('/market/themes')), 'summary request starts immediately');
    assert(urls.some((url) => url.includes('/market/themes/rotation/summary?profile=medium')), 'compact rotation request starts immediately');
    for (const request of pending) {
      request.resolve(new Response(JSON.stringify(request.url.includes('/rotation/') ? rotation : summary), { status: 200 }));
    }
    await Promise.all([summaryPromise, firstRotation, duplicateRotation]);
    await getThemeRotation('1M', { snapshotId: 'theme-stage12-2', taxonomyVersion: '2026.07.1' });
    assert(urls.length === 2, 'latest rotation primes the immutable snapshot cache key without a duplicate request');

    const detailPromise = getThemeDetail('memory_storage', { snapshotId: 'theme-stage12-2', taxonomyVersion: '2026.07.1' });
    await Promise.resolve();
    assert(urls.length === 3 && urls[2].endsWith('/market/themes/memory_storage'), 'full detail loads only after detail is requested');
    pending.at(-1)?.resolve(new Response(JSON.stringify({ ...summary, contract: 'theme_detail_v1', theme: {} }), { status: 200 }));
    await detailPromise;
  } finally {
    clearRequestCache();
    globalThis.fetch = originalFetch;
  }

  const controller = new AbortController();
  globalThis.fetch = ((_, options) => new Promise<Response>((_, reject) => {
    options?.signal?.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError')), { once: true });
  })) as typeof fetch;
  try {
    const cancelled = getThemeSnapshot(controller.signal).then(() => false, isRequestCancelled);
    controller.abort();
    assert(await cancelled, 'route cancellation aborts the underlying theme request');
  } finally {
    clearRequestCache();
    globalThis.fetch = originalFetch;
  }

  for (let index = 0; index < 140; index += 1) {
    await cachedRequest(`stage12-cache:${index}`, async () => index, 60_000);
  }
  assert(requestCacheDiagnostics().cached === 128, 'request cache enforces its bounded LRU limit');
  clearRequestCache('stage12-cache:');

  assert(isRequestCancelled(new DOMException('aborted', 'AbortError')), 'abort errors are classified as cancellations');
  assert(isLatestAsyncDataRequest(2, 2) && !isLatestAsyncDataRequest(1, 2), 'newer requests prevent stale responses from overwriting state');

  let state = initialAtomicScreenState<{ id: string }>();
  state = reduceAtomicScreenState(state, { type: 'request', requestId: 1 });
  state = reduceAtomicScreenState(state, { type: 'success', requestId: 1, data: { id: 'primary' } });
  state = reduceAtomicScreenState(state, { type: 'request', requestId: 2 });
  state = reduceAtomicScreenState(state, { type: 'failure', requestId: 2, error: 'secondary failed' });
  assert(state.phase === 'stale' && state.data?.id === 'primary' && state.retained, 'secondary failure retains truthful primary content');
}

void run();
