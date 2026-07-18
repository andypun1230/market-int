import { getStockAnalysis } from '../src/services/api';
import { clearRequestCache } from '../src/services/requestCache';

function assert(condition: unknown, message: string) {
  if (!condition) {
    throw new Error(message);
  }
}

async function run() {
  const originalFetch = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = (async () => {
    calls += 1;
    return new Response(JSON.stringify({ symbol: 'MSFT' }), { status: 200 });
  }) as typeof fetch;

  try {
    clearRequestCache('stock-analysis:v3:MSFT');
    await Promise.all([
      getStockAnalysis('msft'),
      getStockAnalysis('MSFT'),
      getStockAnalysis('MSFT'),
    ]);
    assert(calls === 1, 'repeated component mounts dedupe one stock-analysis request per symbol');

    await getStockAnalysis('MSFT');
    assert(calls === 1, 'tab switching reuses the shared stock-analysis response without refetching');
  } finally {
    clearRequestCache('stock-analysis:v3:MSFT');
    globalThis.fetch = originalFetch;
  }
}

run();
