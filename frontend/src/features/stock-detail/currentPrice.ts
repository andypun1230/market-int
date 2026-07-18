import type {
  HistoryData,
  QuoteData,
  RiskPlan,
  SupportResistanceResponse,
  TrendlineResponse,
} from '@/types/market';

export type CurrentPriceSource =
  | 'live_quote'
  | 'snapshot_quote'
  | 'snapshot_current_price'
  | 'history_close'
  | 'unavailable';

export type CurrentPriceSelection = {
  price: number | null;
  change: number | null;
  changePercent: number | null;
  source: CurrentPriceSource;
  sourceLabel: string;
  timestamp: string | null;
  isLive: boolean;
};

type SelectCurrentPriceInput = {
  history?: HistoryData | null;
  liveQuote?: QuoteData | null;
  riskPlan?: RiskPlan | null;
  snapshotCurrentPrice?: number | null;
  snapshotQuote?: QuoteData | null;
  supportResistance?: SupportResistanceResponse | null;
  trendline?: TrendlineResponse | null;
};

const UNAVAILABLE_PRICE: CurrentPriceSelection = {
  change: null,
  changePercent: null,
  isLive: false,
  price: null,
  source: 'unavailable',
  sourceLabel: 'Price unavailable',
  timestamp: null,
};

export function selectCurrentPrice({
  history,
  liveQuote,
  riskPlan,
  snapshotCurrentPrice,
  snapshotQuote,
  supportResistance,
  trendline,
}: SelectCurrentPriceInput): CurrentPriceSelection {
  if (isValidPrice(liveQuote?.price)) {
    return quoteSelection(liveQuote, 'live_quote', 'Live quote');
  }
  if (isValidPrice(snapshotQuote?.price)) {
    return quoteSelection(snapshotQuote, 'snapshot_quote', 'Snapshot quote');
  }

  const snapshotPrice = firstValidPrice(
    snapshotCurrentPrice,
    supportResistance?.current_price,
    trendline?.current_price,
    riskPlan?.current_price,
  );
  if (snapshotPrice != null) {
    return {
      change: null,
      changePercent: null,
      isLive: false,
      price: snapshotPrice,
      source: 'snapshot_current_price',
      sourceLabel: 'Snapshot current price',
      timestamp: supportResistance?.as_of ?? trendline?.as_of ?? history?.as_of ?? null,
    };
  }

  const latestClose = latestValidClose(history);
  if (latestClose) {
    return {
      change: null,
      changePercent: null,
      isLive: false,
      price: latestClose.close,
      source: 'history_close',
      sourceLabel: 'Latest history close',
      timestamp: latestClose.timestamp ?? history?.as_of ?? null,
    };
  }

  return UNAVAILABLE_PRICE;
}

export function applyCurrentPrice<T extends {
  change?: number | null;
  change_percent?: number | null;
  data_source?: string | null;
  is_live?: boolean | null;
  price?: number | null;
  quote_timestamp?: string | null;
  source_state?: string | null;
}>(
  stock: T,
  currentPrice: CurrentPriceSelection,
): T {
  if (currentPrice.price == null) {
    return stock;
  }
  return {
    ...stock,
    change: currentPrice.change,
    change_percent: currentPrice.changePercent,
    data_source: currentPrice.sourceLabel,
    is_live: currentPrice.isLive,
    price: currentPrice.price,
    quote_timestamp: currentPrice.timestamp,
    source_state: currentPrice.source,
  };
}

function quoteSelection(quote: QuoteData, source: 'live_quote' | 'snapshot_quote', prefix: string): CurrentPriceSelection {
  const provider = quote.provider ?? quote.source;
  return {
    change: finiteNumber(quote.change),
    changePercent: finiteNumber(quote.change_percent),
    isLive: Boolean(quote.is_live),
    price: quote.price,
    source,
    sourceLabel: provider ? `${prefix} · ${provider}` : prefix,
    timestamp: quote.timestamp || quote.fetched_at || null,
  };
}

function latestValidClose(history?: HistoryData | null): { close: number; timestamp: string | null } | null {
  if (!history?.candles?.length) {
    return null;
  }
  for (let index = history.candles.length - 1; index >= 0; index -= 1) {
    const candle = history.candles[index];
    if (isValidPrice(candle.close)) {
      return { close: candle.close, timestamp: candle.timestamp || null };
    }
  }
  return null;
}

function firstValidPrice(...values: (number | null | undefined)[]): number | null {
  return values.find(isValidPrice) ?? null;
}

function isValidPrice(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value) && value > 0;
}

function finiteNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}
