import type { CopilotContext } from '@/features/copilot/types';

export type CopilotSavedStockMembership = {
  name?: string;
  ticker: string;
};

export function mergeHydratedWatchlistMembership(
  context: CopilotContext,
  hydrated: boolean,
  stockItems: CopilotSavedStockMembership[],
): CopilotContext {
  if (!hydrated) return context;
  const membershipItems = normalizeMembership(stockItems);
  const savedSymbols = membershipItems.map((item) => item.symbol);
  const launchWatchlist = context.watchlist ?? {};
  const launchItems = Array.isArray(launchWatchlist.items) ? launchWatchlist.items : null;
  return {
    ...context,
    savedSymbols,
    watchlist: {
      ...launchWatchlist,
      items: launchItems ?? membershipItems,
      savedSymbols,
    },
  };
}

function normalizeMembership(items: CopilotSavedStockMembership[]) {
  const bySymbol = new Map<string, { name?: string; symbol: string }>();
  items.forEach((item) => {
    const symbol = item.ticker.trim().toUpperCase();
    if (!symbol || bySymbol.has(symbol)) return;
    const name = item.name?.trim();
    bySymbol.set(symbol, name ? { name, symbol } : { symbol });
  });
  return [...bySymbol.values()];
}
