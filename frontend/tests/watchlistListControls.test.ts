import type { SectorRow } from '../src/features/sectors/sectorSnapshot';
import type { LiveThemeItem } from '../src/features/themes/themeSnapshot';
import {
  DEFAULT_LIST_CONTROL_PREFERENCES,
  filterAndSortSectors,
  filterAndSortStocks,
  filterAndSortThemes,
  getFlatStockSortDescription,
  isGroupedStockSort,
  type ListControlPreferences,
} from '../src/features/watchlist/watchlistListControls';
import {
  normalizeListControlPreferences,
  resetListControlCategory,
} from '../src/features/watchlist/watchlistListPreferences';
import type {
  ClassifiedWatchlistItem,
  WatchlistClassification,
  WatchlistGroup,
  WatchlistSignalType,
} from '../src/features/watchlist/types';

function assert(condition: unknown, message: string) {
  if (!condition) throw new Error(message);
}

function stock({
  change = 0,
  dataStatus = 'live',
  group = 'watching',
  risk = 'Low risk',
  score = 50,
  signal = 'watching',
  ticker,
}: {
  change?: number | null;
  dataStatus?: WatchlistClassification['dataStatus'];
  group?: WatchlistGroup;
  risk?: string;
  score?: number | null;
  signal?: WatchlistSignalType;
  ticker: string;
}): ClassifiedWatchlistItem {
  return {
    classification: {
      dataStatus,
      group,
      primarySignal: signal,
      reason: 'Existing analysis',
      score,
      secondarySignals: [],
      severity: group === 'needs_attention' ? 'critical' : group === 'momentum' ? 'positive' : 'neutral',
      ticker,
    },
    item: {
      analysis_status: signal === 'partial' ? 'partial' : 'complete',
      change_percent: change,
      overall_score: score,
      risk_flag: risk,
      setup: signal === 'lost_support' ? 'Below support' : 'Waiting for confirmation',
      support_zone: 'Existing support',
      ticker,
      trend: 'Existing trend',
    },
    originalIndex: 0,
  };
}

function preferences(sort: ListControlPreferences['sort'], filters: ListControlPreferences['filters'] = []) {
  return { filters, sort, viewMode: 'detailed' as const };
}

function sector(name: string, rank: number, classification: string, score: number, momentum: number) {
  return {
    row: {
      classification,
      compositeScore: score,
      displayName: name,
      rank,
      scores: { momentum },
    } as unknown as SectorRow,
    sectorId: 'energy' as const,
    stored: { name },
  };
}

function theme(name: string, rank: number, classification: string, oneMonth: number, relativeStrength: number, momentum: number) {
  return {
    row: {
      classification,
      name,
      rank,
      returns: { '1M': oneMonth },
      rotation: { '1M': { relativeMomentum: momentum, relativeStrength } },
    } as unknown as LiveThemeItem,
    stored: { name },
  };
}

function tickers(items: ClassifiedWatchlistItem[]) {
  return items.map((item) => item.item.ticker).join(',');
}

function run() {
  const stocks = [
    stock({ change: 3, group: 'watching', score: 20, ticker: 'GAIN' }),
    stock({ change: -4, group: 'needs_attention', risk: 'High risk', score: 80, signal: 'lost_support', ticker: 'LOSS' }),
    stock({ change: 0, group: 'momentum', score: 70, signal: 'strong_momentum', ticker: 'MOM' }),
    stock({ change: null, dataStatus: 'stale', group: 'watching', score: null, ticker: 'STALE' }),
    stock({ change: 1, dataStatus: 'partial', group: 'watching', score: 30, signal: 'partial', ticker: 'PART' }),
  ];

  assert(tickers(filterAndSortStocks(stocks, preferences('priority'))) === 'MOM,LOSS,PART,GAIN,STALE', 'priority keeps trading groups separate and uses deterministic score/ticker fallbacks');
  assert(tickers(filterAndSortStocks(stocks, preferences('biggest_gain'))) === 'GAIN,PART,MOM,LOSS,STALE', 'biggest gain sorts descending and puts unknown values last');
  assert(tickers(filterAndSortStocks(stocks, preferences('biggest_loss'))) === 'LOSS,MOM,PART,GAIN,STALE', 'biggest loss sorts ascending and puts unknown values last');
  assert(tickers(filterAndSortStocks(stocks, preferences('alphabetical'))) === 'GAIN,LOSS,MOM,PART,STALE', 'alphabetical sorts ticker A-Z');
  assert(tickers(filterAndSortStocks(stocks, preferences('priority', ['decision_action']))) === '', 'Action Now excludes weakening and maintenance-only items');
  assert(tickers(filterAndSortStocks(stocks, preferences('priority', ['decision_action', 'decision_watching']))) === 'MOM,LOSS', 'same-dimension trading filters use OR');
  assert(tickers(filterAndSortStocks(stocks, preferences('priority', ['decision_action', 'risk_high']))) === '', 'different dimensions use AND');
  assert(tickers(filterAndSortStocks(stocks, preferences('priority', ['data_stale']))) === 'STALE', 'stale data remains explicitly filterable');
  assert(tickers(filterAndSortStocks(stocks, preferences('priority', ['setup_partial']))) === 'PART', 'partial analysis remains explicitly filterable');
  assert(filterAndSortStocks(stocks, preferences('priority', ['decision_stable', 'risk_high'])).length === 0, 'no-match filters return an honest empty result');
  assert(isGroupedStockSort('priority') && !isGroupedStockSort('biggest_gain'), 'only priority retains decision sections');
  assert(getFlatStockSortDescription('biggest_gain')?.includes('daily gain'), 'flat stock sorts explain their scope');

  const sectors = [
    sector('Technology', 1, 'Leading', 85, 72),
    sector('Utilities', 3, 'Lagging', 35, 20),
    sector('Energy', 2, 'Improving', 68, 90),
  ];
  assert(filterAndSortSectors(sectors, preferences('leadership_rank')).map((item) => item.row?.displayName).join(',') === 'Technology,Energy,Utilities', 'sector leadership rank sorts ascending');
  assert(filterAndSortSectors(sectors, preferences('strongest_momentum')).map((item) => item.row?.displayName).join(',') === 'Energy,Technology,Utilities', 'sector momentum uses the existing component score');
  assert(filterAndSortSectors(sectors, preferences('leadership_rank', ['state_lagging'])).length === 1, 'sector state filters use canonical classifications');

  const themes = [
    theme('AI Infrastructure', 1, 'Leading', 8, 104, 103),
    theme('Defensive Yield', 3, 'Lagging', -2, 97, 96),
    theme('Grid Modernization', 2, 'Improving', 4, 102, 105),
  ];
  assert(filterAndSortThemes(themes, preferences('theme_rank')).map((item) => item.row?.name).join(',') === 'AI Infrastructure,Grid Modernization,Defensive Yield', 'theme rank sorts ascending');
  assert(filterAndSortThemes(themes, preferences('one_month_return', ['state_leading', 'state_improving'])).length === 2, 'theme state filters OR within their dimension');
  assert(filterAndSortThemes(themes, preferences('theme_rank', ['state_lagging', 'return_negative'])).length === 1, 'theme state and return filters AND across dimensions');

  const restored = normalizeListControlPreferences({
    sectors: { filters: ['state_lagging'], sort: 'weakest', viewMode: 'compact' },
    stocks: { filters: ['movement_gainer'], sort: 'biggest_gain', viewMode: 'compact' },
    themes: { filters: ['return_positive'], sort: 'one_month_return', viewMode: 'detailed' },
  });
  assert(restored.stocks.sort === 'biggest_gain' && restored.stocks.viewMode === 'compact', 'stock preferences restore independently');
  assert(restored.sectors.filters[0] === 'state_lagging' && restored.sectors.viewMode === 'compact', 'sector preferences restore independently');
  assert(restored.themes.sort === 'one_month_return' && restored.themes.filters[0] === 'return_positive', 'theme preferences restore independently');
  const resetStocks = resetListControlCategory(restored, 'stocks');
  assert(JSON.stringify(resetStocks.stocks) === JSON.stringify(DEFAULT_LIST_CONTROL_PREFERENCES.stocks), 'category reset restores stock defaults');
  assert(resetStocks.sectors.sort === 'weakest' && resetStocks.themes.sort === 'one_month_return', 'category reset does not leak into sectors or themes');

  assert(DEFAULT_LIST_CONTROL_PREFERENCES.stocks.viewMode === 'detailed', 'stock detailed view is the default');
  assert(DEFAULT_LIST_CONTROL_PREFERENCES.stocks.viewMode !== 'compact', 'compact and detailed modes remain distinct');
  assert(DEFAULT_LIST_CONTROL_PREFERENCES.sectors.viewMode === 'detailed', 'sector detailed view is the default');
  assert(DEFAULT_LIST_CONTROL_PREFERENCES.themes.viewMode === 'detailed', 'theme detailed view is the default');
}

run();
