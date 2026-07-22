import {
  getMarketNewsIntelligence,
  getSecurityNewsIntelligence,
  getWatchlistNewsIntelligence,
} from '../src/services/api';
import { clearRequestCache } from '../src/services/requestCache';

function assert(condition: unknown, message: string) {
  if (!condition) throw new Error(message);
}

async function rejects(action: () => Promise<unknown>): Promise<boolean> {
  try {
    await action();
    return false;
  } catch {
    return true;
  }
}

async function run() {
  const originalFetch = globalThis.fetch;
  const urls: string[] = [];
  globalThis.fetch = (async (input) => {
    urls.push(String(input));
    return new Response(JSON.stringify({ status: 'unavailable' }), { status: 200 });
  }) as typeof fetch;

  try {
    clearRequestCache('intelligence-news:');

    await Promise.all([
      getMarketNewsIntelligence(3),
      getMarketNewsIntelligence(3),
      getMarketNewsIntelligence(3),
    ]);
    assert(urls.length === 1, 'concurrent market-news consumers share one in-flight request');
    await getMarketNewsIntelligence(3);
    assert(urls.length === 1, 'cached market-news result is reused without refetching');

    await Promise.all([
      getSecurityNewsIntelligence('msft', 5),
      getSecurityNewsIntelligence(' MSFT ', 5),
    ]);
    assert(urls.length === 2, 'security request key is canonical across symbol case and whitespace');

    await Promise.all([
      getWatchlistNewsIntelligence(['msft', 'AAPL', 'aapl'], 10),
      getWatchlistNewsIntelligence(['AAPL', 'MSFT'], 10),
      getWatchlistNewsIntelligence([' MSFT ', ' aapl '], 10),
    ]);
    assert(urls.length === 3, 'saved symbols use one canonical batched request instead of N+1 calls');
    const watchlistUrl = decodeURIComponent(urls[2] ?? '');
    assert(watchlistUrl.includes('symbols=AAPL,MSFT'), 'watchlist request sorts and deduplicates explicit saved symbols');

    const beforeLimits = urls.length;
    const tooMany = Array.from({ length: 51 }, (_, index) => `S${index}`);
    assert(await rejects(() => getWatchlistNewsIntelligence(tooMany)), 'more than 50 saved symbols fails explicitly');
    const tooLong = Array.from({ length: 30 }, (_, index) => `SYMBOL${String(index).padStart(14, '0')}`);
    assert(await rejects(() => getWatchlistNewsIntelligence(tooLong)), 'over-500-character batch fails explicitly');
    assert(urls.length === beforeLimits, 'over-limit saved-symbol sets never send partial requests');
  } finally {
    clearRequestCache('intelligence-news:');
    globalThis.fetch = originalFetch;
  }
}

run();
