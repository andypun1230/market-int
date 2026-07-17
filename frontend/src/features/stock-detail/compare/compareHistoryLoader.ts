import { getLiveHistory } from '@/services/api';
import { isRequestCancelled } from '@/services/requestCache';
import type { HistoryData } from '@/types/market';

const MAX_CONCURRENT_HISTORY_REQUESTS = 2;
const MAX_TRANSIENT_ATTEMPTS = 3;
const TRANSIENT_BACKOFF_MS = 350;

const PROVIDER_SYMBOL_ALIASES: Record<string, string> = {
  DJI: 'DIA',
  IXIC: 'QQQ',
  RUT: 'IWM',
  SPX: 'SPY',
};

export type CompareHistoryLoadState = {
  coverage: CompareCoverageMetadata;
  histories: Record<string, HistoryData | null>;
};

export type CompareCoverageMetadata = {
  coverage_ratio: number;
  partial: boolean;
  peers_available: string[];
  peers_requested: string[];
  peers_unavailable: string[];
  refreshing: boolean;
  unavailable_reasons: Record<string, string>;
};

type LoadOptions = {
  days: number;
  onUpdate?: (state: CompareHistoryLoadState) => void;
  resolution?: string;
};

type SymbolRequest = {
  displaySymbol: string;
  providerSymbol: string;
};

export async function loadComparisonHistories(
  symbols: string[],
  options: LoadOptions,
): Promise<CompareHistoryLoadState> {
  const requests = normalizeComparisonSymbols(symbols);
  const histories: Record<string, HistoryData | null> = {};
  const unavailableReasons: Record<string, string> = {};

  requests.forEach((request) => {
    histories[request.displaySymbol] = null;
  });

  const emit = (refreshing: boolean) => {
    options.onUpdate?.({
      coverage: buildCoverageMetadata(requests, histories, unavailableReasons, refreshing),
      histories: { ...histories },
    });
  };

  emit(true);
  await runBounded(requests, MAX_CONCURRENT_HISTORY_REQUESTS, async (request) => {
    try {
      histories[request.displaySymbol] = await fetchHistoryWithRetry(request.providerSymbol, {
        days: options.days,
        resolution: options.resolution ?? 'D',
      });
      delete unavailableReasons[request.displaySymbol];
    } catch (error) {
      histories[request.displaySymbol] = null;
      unavailableReasons[request.displaySymbol] = compactUnavailableReason(error);
    } finally {
      emit(true);
    }
  });

  return {
    coverage: buildCoverageMetadata(requests, histories, unavailableReasons, false),
    histories,
  };
}

export function normalizeComparisonSymbols(symbols: string[]): SymbolRequest[] {
  const seen = new Set<string>();
  const requests: SymbolRequest[] = [];
  symbols.forEach((symbol) => {
    const displaySymbol = symbol.trim().toUpperCase();
    if (!displaySymbol || seen.has(displaySymbol)) {
      return;
    }
    seen.add(displaySymbol);
    requests.push({
      displaySymbol,
      providerSymbol: PROVIDER_SYMBOL_ALIASES[displaySymbol] ?? displaySymbol,
    });
  });
  return requests;
}

async function fetchHistoryWithRetry(
  symbol: string,
  options: { days: number; resolution: string },
): Promise<HistoryData> {
  let lastError: unknown = null;
  for (let attempt = 1; attempt <= MAX_TRANSIENT_ATTEMPTS; attempt += 1) {
    try {
      return await getLiveHistory(symbol, options.resolution, options.days);
    } catch (error) {
      lastError = error;
      if (!isTransientHistoryFailure(error) || attempt === MAX_TRANSIENT_ATTEMPTS) {
        break;
      }
      await delay(TRANSIENT_BACKOFF_MS * attempt);
    }
  }
  throw lastError;
}

async function runBounded<T>(
  items: T[],
  concurrency: number,
  worker: (item: T) => Promise<void>,
): Promise<void> {
  let cursor = 0;
  const workers = Array.from({ length: Math.min(concurrency, items.length) }, async () => {
    while (cursor < items.length) {
      const item = items[cursor];
      cursor += 1;
      await worker(item);
    }
  });
  await Promise.all(workers);
}

function buildCoverageMetadata(
  requests: SymbolRequest[],
  histories: Record<string, HistoryData | null>,
  unavailableReasons: Record<string, string>,
  refreshing: boolean,
): CompareCoverageMetadata {
  const peersRequested = requests.map((request) => request.displaySymbol);
  const peersAvailable = peersRequested.filter((symbol) => Boolean(histories[symbol]?.candles?.length));
  const peersUnavailable = peersRequested.filter((symbol) => !peersAvailable.includes(symbol));
  return {
    coverage_ratio: peersRequested.length ? roundTo(peersAvailable.length / peersRequested.length, 2) : 0,
    partial: peersUnavailable.length > 0,
    peers_available: peersAvailable,
    peers_requested: peersRequested,
    peers_unavailable: peersUnavailable,
    refreshing,
    unavailable_reasons: unavailableReasons,
  };
}

function isTransientHistoryFailure(error: unknown): boolean {
  if (isRequestCancelled(error)) {
    return false;
  }
  const message = error instanceof Error ? error.message : String(error);
  return /HTTP (408|429|500|502|503|504)\b/i.test(message)
    || /timeout|timed out|network request failed/i.test(message);
}

function compactUnavailableReason(error: unknown): string {
  if (isRequestCancelled(error)) {
    return 'cancelled';
  }
  const message = error instanceof Error ? error.message : String(error);
  const httpMatch = message.match(/HTTP (\d{3})/i);
  if (httpMatch) {
    return `history unavailable (${httpMatch[1]})`;
  }
  if (/underfilled/i.test(message)) {
    return 'history range underfilled';
  }
  if (/timeout|timed out/i.test(message)) {
    return 'history request timed out';
  }
  return 'history unavailable';
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function roundTo(value: number, digits: number): number {
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}
