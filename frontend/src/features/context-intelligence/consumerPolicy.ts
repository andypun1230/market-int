export const HOME_MARKET_EVENT_LIMIT = 3;

export function shouldRequestStockMaterialEvents(
  detailsOpen: boolean,
  selectedDetailTab: string,
): boolean {
  return detailsOpen && selectedDetailTab === 'overview';
}

export function shouldRequestEntityCatalysts(
  detailOpen: boolean,
  testContext: boolean,
): boolean {
  return detailOpen && !testContext;
}

export function shouldRequestWatchlistCatalysts({
  activeTab,
  focused,
  hydrated,
  symbolCount,
}: {
  activeTab: string;
  focused: boolean;
  hydrated: boolean;
  symbolCount: number;
}): boolean {
  return activeTab === 'stocks' && focused && hydrated && symbolCount > 0;
}

export function watchlistSavedSymbolsLabel(symbolCount: number): string {
  const count = Math.max(0, Math.floor(symbolCount));
  return `${count} saved symbol${count === 1 ? '' : 's'} · batched request`;
}

export function watchlistBatchLimitation(symbols: string[]): string | null {
  const normalized = [...new Set(
    symbols.map((symbol) => symbol.trim().toUpperCase()).filter(Boolean),
  )].sort();
  if (normalized.length > 50) {
    return 'Catalyst coverage is unavailable because the watchlist exceeds the 50-saved-symbol batch limit.';
  }
  if (normalized.join(',').length > 500) {
    return 'Catalyst coverage is unavailable because the saved-symbol request exceeds the 500-character batch limit.';
  }
  return null;
}
