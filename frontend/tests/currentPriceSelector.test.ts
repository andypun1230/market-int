import {
  applyCurrentPrice,
  selectCurrentPrice,
} from '../src/features/stock-detail/currentPrice';
import { buildRiskDashboard } from '../src/features/stock-detail/risk/riskPresenter';
import { buildStockDetailOverview } from '../src/features/stock-detail/stockDetailPresenter';
import { buildPriceLevels } from '../src/features/stock-detail/technical/technicalViewModel';
import { isLatestAsyncDataRequest } from '../src/hooks/useAsyncData';
import type {
  HistoryData,
  QuoteData,
  SupportResistanceResponse,
  WatchlistItem,
} from '../src/types/market';

function assert(condition: unknown, message: string) {
  if (!condition) {
    throw new Error(message);
  }
}

function quote(overrides: Partial<QuoteData> = {}): QuoteData {
  return {
    change: 3.12,
    change_percent: 0.8,
    fallback_used: false,
    high: 395,
    is_live: true,
    is_stale: false,
    low: 390,
    open: 391,
    previous_close: 390.7,
    price: 393.82,
    source: 'finnhub',
    symbol: 'MSFT',
    timestamp: '2026-07-18T14:30:00Z',
    volume: 12_000_000,
    ...overrides,
  };
}

function history(close = 390): HistoryData {
  return {
    adjusted: true,
    as_of: '2026-07-17T20:00:00Z',
    candles: [{ close, high: close + 2, low: close - 2, open: close - 1, timestamp: '2026-07-17T20:00:00Z', volume: 1_000_000 }],
    fallback_used: false,
    is_live: true,
    is_stale: false,
    source: 'polygon',
    symbol: 'MSFT',
    timeframe: 'D',
  };
}

function stock(overrides: Partial<WatchlistItem> = {}): WatchlistItem {
  return {
    change: null,
    change_percent: null,
    data_source: 'local',
    is_live: false,
    price: null,
    risk_flag: 'Medium',
    setup: 'Open for analysis',
    support_zone: 'N/A',
    ticker: 'MSFT',
    trend: 'Local',
    ...overrides,
  };
}

function supportResistance(current_price = 390): SupportResistanceResponse {
  return {
    as_of: '2026-07-17T20:00:00Z',
    breakout_level: 398,
    current_price,
    data_source: 'polygon',
    fallback_used: false,
    moving_average_support: { ema_20: 380, ema_50: 370 },
    resistance_zones: [],
    stop_reference: 375,
    support_zones: [],
    symbol: 'MSFT',
  };
}

function run() {
  const live = selectCurrentPrice({
    history: history(),
    liveQuote: quote(),
    supportResistance: supportResistance(),
  });
  assert(live.price === 393.82 && live.source === 'live_quote', 'new watchlist symbol prefers the live quote');
  assert(live.sourceLabel.includes('finnhub'), 'live quote provenance is retained');

  const displayStock = applyCurrentPrice(stock(), live);
  const overview = buildStockDetailOverview({ currentPrice: live, stock: displayStock });
  const technicalPrice = buildPriceLevels(displayStock, supportResistance()).find((level) => level.kind === 'current')?.value;
  const risk = buildRiskDashboard({ currentPrice: live, supportResistance: supportResistance() });
  assert(overview.quote.price === 393.82, 'Overview receives the selected live price');
  assert(technicalPrice === 393.82, 'Technical receives the same selected price');
  assert(risk.currentPrice === 393.82, 'Risk receives the same selected price');

  const snapshotQuote = selectCurrentPrice({
    liveQuote: null,
    snapshotQuote: quote({ is_live: false, price: 391.25, source: 'snapshot-cache' }),
  });
  assert(snapshotQuote.price === 391.25 && snapshotQuote.source === 'snapshot_quote', 'cached snapshot quote is used when live quote is unavailable');

  const snapshotCurrentPrice = selectCurrentPrice({
    liveQuote: null,
    supportResistance: supportResistance(389.5),
  });
  assert(snapshotCurrentPrice.price === 389.5 && snapshotCurrentPrice.source === 'snapshot_current_price', 'compatible snapshot current price is used after snapshot quote');

  const historyClose = selectCurrentPrice({ history: history(388.4), liveQuote: null });
  assert(historyClose.price === 388.4 && historyClose.source === 'history_close', 'history fallback is explicit when no quote is available');
  assert(historyClose.sourceLabel === 'Latest history close', 'history fallback is labelled as a close, not a live quote');

  const unavailable = selectCurrentPrice({ liveQuote: null });
  assert(unavailable.price == null && unavailable.source === 'unavailable', 'price remains unavailable without a valid source');

  assert(isLatestAsyncDataRequest(2, 2), 'newer complete request is accepted');
  assert(!isLatestAsyncDataRequest(1, 2), 'older partial request cannot overwrite newer complete detail state');
}

run();
