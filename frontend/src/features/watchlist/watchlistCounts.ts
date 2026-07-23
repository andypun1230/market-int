import type { WatchlistSummaryItem } from '@/types/market';

export type WatchlistCountModel = {
  locallySaved: number;
  displayed: number;
  eligible: number;
  analyzed: number;
  catalystRequested: number;
  partial: number;
  unavailable: number;
  catalystScopeExplanation: string;
};

export function buildWatchlistCountModel({
  locallySavedSymbols,
  displayedItems,
  catalystSymbols,
}: {
  locallySavedSymbols: string[];
  displayedItems: WatchlistSummaryItem[];
  catalystSymbols: string[];
}): WatchlistCountModel {
  const local = unique(locallySavedSymbols);
  const catalyst = unique(catalystSymbols);
  const eligible = displayedItems.filter((item) => typeof item.price === 'number' && typeof item.change_percent === 'number');
  const analyzed = displayedItems.filter((item) => item.overall_status === 'complete' || item.analysis_status === 'complete');
  const partial = displayedItems.filter((item) => item.overall_status === 'partial' || item.analysis_status === 'partial');
  const unavailable = displayedItems.filter((item) => item.overall_status === 'unavailable' || item.overall_status === 'unsupported' || item.data_source === 'unavailable');
  const catalystScopeExplanation = catalyst.size === displayedItems.length
    ? `Catalysts cover all ${catalyst.size} displayed stock${catalyst.size === 1 ? '' : 's'}.`
    : `Catalysts cover ${catalyst.size} locally saved stock${catalyst.size === 1 ? '' : 's'}; ${displayedItems.length} stock${displayedItems.length === 1 ? ' is' : 's are'} displayed because backend defaults or a deep link may add read-only analysis.`;
  return {
    locallySaved: local.size,
    displayed: displayedItems.length,
    eligible: eligible.length,
    analyzed: analyzed.length,
    catalystRequested: catalyst.size,
    partial: partial.length,
    unavailable: unavailable.length,
    catalystScopeExplanation,
  };
}

function unique(values: string[]) {
  return new Set(values.map((value) => value.trim().toUpperCase()).filter(Boolean));
}
