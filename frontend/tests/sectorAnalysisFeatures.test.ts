import {
  addComparisonItem,
  buildComparisonRows,
  canCompare,
  rankComparisonMetrics,
} from '../src/features/sectors/analysis/comparison';
import { calculateLeadershipConcentration } from '../src/features/sectors/analysis/concentration';
import {
  buildDivergenceAccessibilitySummary,
  buildDivergenceEvidenceRows,
  calculateBreadthTrend,
  calculateDivergenceSeverity,
  detectDivergences,
} from '../src/features/sectors/analysis/divergence';
import {
  DEFAULT_SECTOR_THEME_FILTERS,
  filterSectorThemeItems,
  getFavouriteKey,
} from '../src/features/sectors/analysis/filters';
import {
  buildEmergingLeadershipScanner,
  buildLeadershipRiskScanner,
} from '../src/features/sectors/analysis/scanners';
import {
  DEFAULT_RELEVANT_STOCK_FILTERS,
  RELEVANT_STOCK_SORT_OPTIONS,
  applyRelevantStockQuickFilter,
  buildRelevantStockActiveFilterChips,
  countRelevantStockActiveFilters,
  filterRelevantStocks,
  getRelevantStockSortLabel,
  removeRelevantStockFilter,
  resetRelevantStockFilters,
  sortRelevantStocks,
  type RelevantStockSortMode,
} from '../src/features/sectors/analysis/relevantStocks';
import {
  saveSectorThemeFavourites,
  loadSectorThemeFavourites,
  toggleSectorThemeFavourite,
} from '../src/features/sectors/storage/favourites';
import {
  generateSectorTabTestData,
  getDivergenceScenarioForItem,
  type SectorThemeTestItem,
} from '../src/data/sectorTabTestData';

function assert(condition: unknown, message: string) {
  if (!condition) {
    throw new Error(message);
  }
}

function run() {
  const data = generateSectorTabTestData();
  const allItems: SectorThemeTestItem[] = [...data.sectors, ...data.themes];
  const divergenceTitles = new Map<string, number>();
  let noDivergenceItems = 0;
  const first = data.sectors[0];
  const second = data.sectors[1];
  const third = data.themes[0];
  const fourth = data.themes[1];

  let comparison: SectorThemeTestItem[] = [];
  comparison = addComparisonItem(comparison, first);
  comparison = addComparisonItem(comparison, first);
  comparison = addComparisonItem(comparison, second);
  comparison = addComparisonItem(comparison, third);
  comparison = addComparisonItem(comparison, fourth);
  assert(comparison.length === 3, 'comparison prevents duplicates and maxes at three');
  assert(canCompare(comparison), 'three comparison items are valid');
  assert(buildComparisonRows(comparison, ['1D', '1W']).some((row) => row.label === 'Top 3 Contribution'), 'comparison includes concentration rows');
  assert(rankComparisonMetrics(comparison)?.strongestPerformance, 'comparison scorecard selects winners');

  const favourites = saveSectorThemeFavourites([]);
  const withFavourite = toggleSectorThemeFavourite(favourites, first);
  const duplicateFavourite = toggleSectorThemeFavourite(withFavourite, first);
  assert(withFavourite.length === 1, 'adds favourite');
  assert(duplicateFavourite.length === 0, 'removes favourite');
  saveSectorThemeFavourites(withFavourite);
  assert(loadSectorThemeFavourites().length === 1, 'restores saved favourites');

  const favouriteKeys = new Set(withFavourite.map((favourite) => `${favourite.type}:${favourite.id}`));
  const favouriteFiltered = filterSectorThemeItems(data.sectors, {
    ...DEFAULT_SECTOR_THEME_FILTERS,
    favouriteMode: 'only',
  }, '1M', favouriteKeys);
  assert(favouriteFiltered.length === 1 && getFavouriteKey(favouriteFiltered[0]) === getFavouriteKey(first), 'favourites-only filter works');

  const positive = filterSectorThemeItems(allItems, {
    ...DEFAULT_SECTOR_THEME_FILTERS,
    performance: 'positive',
  }, '1M', new Set());
  assert(positive.every((item) => item.returns['1M'] > 0.5), 'positive performance filter works');

  const leading = filterSectorThemeItems(allItems, {
    ...DEFAULT_SECTOR_THEME_FILTERS,
    quadrant: 'leading',
  }, '1M', new Set());
  assert(leading.every((item) => item.quadrant === 'leading'), 'quadrant filter works');

  const sortedByMomentum = filterSectorThemeItems(allItems, {
    ...DEFAULT_SECTOR_THEME_FILTERS,
    sortMode: 'strongestRelativeMomentum',
  }, '1M', new Set());
  assert(sortedByMomentum[0].relativeMomentum >= sortedByMomentum[1].relativeMomentum, 'sort by relative momentum works');

  const stocks = first.constituents;
  const emptyStockWatchlist = new Set<string>();
  const savedStockKey = `stock:${stocks[0].ticker.toLowerCase()}`;
  const savedStockWatchlist = new Set([savedStockKey]);
  const leadersFilters = applyRelevantStockQuickFilter(DEFAULT_RELEVANT_STOCK_FILTERS, 'leaders');
  const laggardsFilters = applyRelevantStockQuickFilter(DEFAULT_RELEVANT_STOCK_FILTERS, 'laggards');
  const above20Filters = applyRelevantStockQuickFilter(DEFAULT_RELEVANT_STOCK_FILTERS, 'above20');
  const savedFilters = applyRelevantStockQuickFilter(DEFAULT_RELEVANT_STOCK_FILTERS, 'watchlisted');

  assert(leadersFilters.performance === 'positive' && leadersFilters.sortMode === 'highestReturn', 'leaders quick filter uses shared performance and sort state');
  assert(laggardsFilters.performance === 'negative' && laggardsFilters.sortMode === 'lowestReturn', 'laggards quick filter uses shared performance and sort state');
  assert(above20Filters.trend === 'above20', 'above 20 EMA quick filter uses shared trend state');
  assert(savedFilters.watchlist === 'saved', 'saved quick filter uses shared watchlist state');
  assert(filterRelevantStocks(stocks, '', leadersFilters, '1M', emptyStockWatchlist).every((stock) => stock.returns['1M'] > 0.5), 'leaders filter works');
  assert(filterRelevantStocks(stocks, '', laggardsFilters, '1M', emptyStockWatchlist).every((stock) => stock.returns['1M'] < -0.5), 'laggards filter works');
  assert(filterRelevantStocks(stocks, '', above20Filters, '1M', emptyStockWatchlist).every((stock) => stock.above20Ema), 'above 20 EMA filter works');
  assert(filterRelevantStocks(stocks, '', savedFilters, '1M', savedStockWatchlist).every((stock) => stock.ticker === stocks[0].ticker), 'saved filter works');

  const sortModes: RelevantStockSortMode[] = [
    'highestReturn',
    'lowestReturn',
    'highestRelativeStrength',
    'largestWeight',
    'alphabetical',
    'watchlistedFirst',
  ];
  assert(RELEVANT_STOCK_SORT_OPTIONS.length === sortModes.length, 'visible sort sheet keeps six options');
  sortModes.forEach((sortMode) => {
    const sorted = sortRelevantStocks(stocks, sortMode, '1M', savedStockWatchlist);
    assert(sorted.length === stocks.length, `${sortMode} sort preserves all stocks`);
    assert(getRelevantStockSortLabel(sortMode).length > 0, `${sortMode} has toolbar label`);
  });
  assert(sortRelevantStocks(stocks, 'highestReturn', '1M', emptyStockWatchlist)[0].returns['1M'] >= sortRelevantStocks(stocks, 'highestReturn', '1M', emptyStockWatchlist)[1].returns['1M'], 'highest return sort works');
  assert(sortRelevantStocks(stocks, 'lowestReturn', '1M', emptyStockWatchlist)[0].returns['1M'] <= sortRelevantStocks(stocks, 'lowestReturn', '1M', emptyStockWatchlist)[1].returns['1M'], 'lowest return sort works');
  assert(sortRelevantStocks(stocks, 'highestRelativeStrength', '1M', emptyStockWatchlist)[0].relativeStrength >= sortRelevantStocks(stocks, 'highestRelativeStrength', '1M', emptyStockWatchlist)[1].relativeStrength, 'highest RS sort works');
  assert(sortRelevantStocks(stocks, 'largestWeight', '1M', emptyStockWatchlist)[0].weight >= sortRelevantStocks(stocks, 'largestWeight', '1M', emptyStockWatchlist)[1].weight, 'largest weight sort works');
  assert(sortRelevantStocks(stocks, 'alphabetical', '1M', emptyStockWatchlist)[0].ticker.localeCompare(sortRelevantStocks(stocks, 'alphabetical', '1M', emptyStockWatchlist)[1].ticker) <= 0, 'alphabetical sort works');
  assert(sortRelevantStocks(stocks, 'watchlistedFirst', '1M', savedStockWatchlist)[0].ticker === stocks[0].ticker, 'saved first sort works');

  const activeFilters = {
    ...DEFAULT_RELEVANT_STOCK_FILTERS,
    marketCap: 'large' as const,
    momentum: 'strong' as const,
    performance: 'positive' as const,
    relativeStrength: 'above100' as const,
    sortMode: 'largestWeight' as const,
    trend: 'above20' as const,
    watchlist: 'saved' as const,
  };
  assert(countRelevantStockActiveFilters(activeFilters) === 6, 'active filter count excludes sort mode');
  assert(buildRelevantStockActiveFilterChips(activeFilters).length === 6, 'active filter chips mirror active filters');
  assert(removeRelevantStockFilter(activeFilters, 'trend').trend === 'all', 'removing one chip clears one filter');
  const resetFilters = resetRelevantStockFilters(activeFilters);
  assert(resetFilters.sortMode === 'largestWeight', 'reset filters preserves sort mode');
  assert(countRelevantStockActiveFilters(resetFilters) === 0, 'reset filters clears active filters');

  allItems.forEach((item) => {
    const concentration = calculateLeadershipConcentration(item);
    assert(concentration.top3ContributionPercent >= 0 && concentration.top3ContributionPercent <= 100, 'top contribution is safe');
    assert(Number.isFinite(concentration.weightedReturn), 'weighted return is finite');
    assert(Number.isFinite(concentration.equalWeightReturn), 'equal-weight return is finite');
    const weightSum = item.constituents.reduce((sum, constituent) => sum + constituent.weight, 0);
    assert(Math.abs(weightSum - 100) < 0.25, 'constituent weights sum approximately to 100');

    const signals = detectDivergences(item);
    assert(signals.length <= 3, 'divergence detector caps signals at three');
    if (!signals.length) {
      noDivergenceItems += 1;
    }
    signals.forEach((signal) => {
      divergenceTitles.set(signal.title, (divergenceTitles.get(signal.title) ?? 0) + 1);
      assert(signal.source === 'test', 'divergence uses test source');
      assert(signal.evidence.length > 0, 'divergence has evidence');
      assert(buildDivergenceEvidenceRows(signal).length > 0, 'divergence has structured evidence rows');
      assert(['low', 'medium', 'high'].includes(signal.severity), 'divergence severity is explicit');
      assert(signal.implication.length > 0, 'divergence includes beginner-friendly implication');
      assert(buildDivergenceAccessibilitySummary(signal).includes(signal.summary), 'divergence accessibility summary includes explanation');
      assert(signal.evidence.every((evidence) => evidence.includes(':')), 'divergence evidence includes derived values');
    });
  });

  [
    'Positive Breadth Divergence',
    'Negative Breadth Divergence',
    'Rotation Divergence',
    'Concentration Divergence',
    'Price / Rotation Divergence',
  ].forEach((title) => {
    assert((divergenceTitles.get(title) ?? 0) > 0, `${title} appears in deterministic test data`);
  });
  assert(noDivergenceItems > 0, 'some items intentionally produce no divergence');

  const positiveBreadthItem = allItems.find((item) =>
    getDivergenceScenarioForItem(item.id) === 'positiveBreadth' &&
    detectDivergences(item).some((signal) => signal.title === 'Positive Breadth Divergence')
  );
  assert(positiveBreadthItem, 'positive breadth scenario produces positive breadth signal');
  if (positiveBreadthItem) {
    const trend = calculateBreadthTrend(positiveBreadthItem.breadthHistory['3M']);
    assert(positiveBreadthItem.returns['1M'] < 0 && trend.change20 > 10 && trend.change50 > 6, 'positive breadth evidence matches underlying data');
  }

  const negativeBreadthItem = allItems.find((item) =>
    getDivergenceScenarioForItem(item.id) === 'negativeBreadth' &&
    detectDivergences(item).some((signal) => signal.title === 'Negative Breadth Divergence')
  );
  assert(negativeBreadthItem, 'negative breadth scenario produces negative breadth signal');
  if (negativeBreadthItem) {
    const trend = calculateBreadthTrend(negativeBreadthItem.breadthHistory['3M']);
    assert(negativeBreadthItem.returns['1M'] > 3 && trend.change20 < -10 && trend.change50 < -5, 'negative breadth evidence matches underlying data');
    const signal = detectDivergences(negativeBreadthItem).find((currentSignal) => currentSignal.title === 'Negative Breadth Divergence');
    assert(signal?.evidenceRows.some((row) => row.label === 'Above 20 EMA' && row.secondary?.includes('pts')), 'breadth divergence evidence uses percentage-point changes');
  }

  const concentrationItem = allItems.find((item) =>
    getDivergenceScenarioForItem(item.id) === 'concentration' &&
    detectDivergences(item).some((signal) => signal.title === 'Concentration Divergence')
  );
  assert(concentrationItem, 'concentration scenario produces concentration divergence');
  if (concentrationItem) {
    const concentration = calculateLeadershipConcentration(concentrationItem);
    assert(concentration.top3ContributionPercent >= 65 && concentration.percentOutperformingGroup < 35, 'concentration signal matches constituent data');
  }

  assert(
    calculateDivergenceSeverity({
      breadthChange20: -26,
      breadthChange50: -14,
      confirmingMetrics: 4,
      momentumChange: -0.18,
      priceReturn: 6.4,
      type: 'breadth',
    }) === 'high',
    'strong negative breadth case returns High severity',
  );
  assert(
    calculateDivergenceSeverity({
      breadthChange20: -13,
      breadthChange50: -7,
      confirmingMetrics: 3,
      momentumChange: -0.08,
      priceReturn: 3.5,
      type: 'breadth',
    }) === 'medium',
    'moderate divergence case returns Medium severity',
  );
  assert(
    calculateDivergenceSeverity({
      confirmingMetrics: 2,
      momentumChange: 0.05,
      priceReturn: -1.2,
      type: 'price_rotation',
    }) === 'low',
    'near-threshold price rotation case returns Low severity',
  );

  const multiSignalItem = allItems.find((item) => detectDivergences(item).length > 1);
  if (multiSignalItem) {
    const signals = detectDivergences(multiSignalItem);
    assert(signals[0].title !== 'Price / Rotation Divergence', 'lower-priority price/rotation signal does not lead multi-signal lists');
  }

  const emerging = buildEmergingLeadershipScanner(allItems, 5);
  const risk = buildLeadershipRiskScanner(allItems, 5);
  assert(emerging.length <= 5 && risk.length <= 5, 'scanners limit output');
  [...emerging, ...risk].forEach((result) => {
    assert(result.score >= 0 && result.score <= 100, 'scanner score stays 0-100');
    assert(result.reasons.length > 0, 'scanner reasons are populated');
  });
}

run();
