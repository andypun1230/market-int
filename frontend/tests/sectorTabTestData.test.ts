import {
  BREADTH_HISTORY_INTERVALS,
  buildRotationTrailSummary,
  calculateRotationDomain,
  buildRotationAlerts,
  classifyQuadrant,
  generateSectorTabTestData,
  generateFullBreadthHistory,
  getBreadthPatternForItem,
  getDivergenceScenarioForItem,
  SECTOR_TAB_TEST_SEED,
  selectBreadthHistoryWindows,
  TEST_HEATMAP_INTERVALS,
  TEST_ROTATION_INTERVALS,
  type BreadthHistoryPoint,
  type BreadthPattern,
} from '../src/data/sectorTabTestData';
import {
  buildRotationVisibilitySummary,
  doRectsOverlap,
  estimateLabelBounds,
  filterRotationItemsByQuadrant,
  findAvailableLabelPlacement,
  getRotationShortLabel,
  rankRotationLabels,
  selectSmartLabelKeys,
  type RotationLabelCandidate,
} from '../src/features/sectors/analysis/rotationLabels';
import {
  calculateBreadthNetChanges,
  calculateBreadthTrendLabel,
  formatBreadthPointChange,
} from '../src/features/sectors/analysis/breadthTrend';
import { createTestSectorThemeRepository } from '../src/features/sectors/repository/sectorThemeRepository';
import { resetSectorUiPreferencesForTests, useSectorUiPreferences } from '../src/features/sectors/state/sectorUiPreferences';

function assert(condition: unknown, message: string) {
  if (!condition) {
    throw new Error(message);
  }
}

function averageAdjacentMove(history: BreadthHistoryPoint[], key: keyof Omit<BreadthHistoryPoint, 'label'>) {
  const moves = history.slice(1).map((point, index) => Math.abs(point[key] - history[index][key]));
  return moves.reduce((sum, move) => sum + move, 0) / Math.max(moves.length, 1);
}

function breadthDelta(history: BreadthHistoryPoint[], key: keyof Omit<BreadthHistoryPoint, 'label'>) {
  return history[history.length - 1][key] - history[0][key];
}

function run() {
  const first = generateSectorTabTestData(SECTOR_TAB_TEST_SEED);
  const second = generateSectorTabTestData(SECTOR_TAB_TEST_SEED);
  const different = generateSectorTabTestData(`${SECTOR_TAB_TEST_SEED}-alt`);
  const allItems = [...first.sectors, ...first.themes];
  const repository = createTestSectorThemeRepository(SECTOR_TAB_TEST_SEED);

  assert(JSON.stringify(first) === JSON.stringify(second), 'same seed produces stable output');
  assert(JSON.stringify(first) !== JSON.stringify(different), 'different seed changes output');
  assert(first.source === 'test', 'source is test');
  assert(first.sectors.length === 11, 'uses standard broad sectors');
  assert(first.themes.length >= 10, 'uses theme universe');
  assert(repository.getSectors().length === first.sectors.length, 'test repository exposes sectors');
  assert(repository.getThemes().length === first.themes.length, 'test repository exposes themes');
  assert(repository.getAllItems().length === allItems.length, 'test repository exposes combined sector and theme items');
  assert(repository.getSectorById(first.sectors[0].id)?.name === first.sectors[0].name, 'test repository can retrieve a sector by id');
  assert(repository.getThemeById(first.themes[0].id)?.name === first.themes[0].name, 'test repository can retrieve a theme by id');
  assert(new Set(allItems.map((item) => getBreadthPatternForItem(item.id))).size >= 4, 'breadth patterns vary across the universe');
  assert(new Set(allItems.map((item) => getDivergenceScenarioForItem(item.id))).size >= 5, 'divergence scenarios vary across the universe');
  resetSectorUiPreferencesForTests();
  assert(typeof useSectorUiPreferences === 'function', 'sector UI preference hook is exported for screen-level session state');

  const sectorReturns = first.sectors.flatMap((sector) => TEST_HEATMAP_INTERVALS.map((interval) => sector.returns[interval]));
  const themeReturns = first.themes.flatMap((theme) => TEST_HEATMAP_INTERVALS.map((interval) => theme.returns[interval]));
  assert(sectorReturns.some((value) => value > 0), 'sector returns include positive values');
  assert(sectorReturns.some((value) => value < 0), 'sector returns include negative values');
  assert([...sectorReturns, ...themeReturns].some((value) => Math.abs(value) < 1), 'returns include near-zero values');

  const ranges = {
    '1D': [-4, 4],
    '1W': [-8, 8],
    '1M': [-15, 15],
    '3M': [-25, 25],
    '6M': [-35, 35],
    '1Y': [-50, 60],
  } as const;

  allItems.forEach((item) => {
    TEST_HEATMAP_INTERVALS.forEach((interval) => {
      const [min, max] = ranges[interval];
      assert(item.returns[interval] >= min && item.returns[interval] <= max, `${item.name} ${interval} return stays in range`);
    });

    TEST_ROTATION_INTERVALS.forEach((interval) => {
      const rotation = item.rotation[interval];
      const expectedLength = interval === '1W' ? 5 : interval === '1M' ? 10 : 12;
      assert(rotation.history.length === expectedLength, `${item.name} ${interval} uses expected sampled trail length`);
      assert(rotation.quadrant === classifyQuadrant(rotation.relativeStrength, rotation.relativeMomentum), `${item.name} quadrant is classified from latest point`);
      rotation.history.slice(1).forEach((point, index) => {
        const previous = rotation.history[index];
        assert(Math.abs(point.relativeStrength - previous.relativeStrength) <= 2, `${item.name} strength moves gradually`);
        assert(Math.abs(point.relativeMomentum - previous.relativeMomentum) <= 2, `${item.name} momentum moves gradually`);
        assert(point.relativeStrength >= 94 && point.relativeStrength <= 106, `${item.name} strength stays in realistic RRG range`);
        assert(point.relativeMomentum >= 94 && point.relativeMomentum <= 106, `${item.name} momentum stays in realistic RRG range`);
      });
    });

    const oneWeekLatest = item.rotation['1W'].history.at(-1);
    const oneMonthLatest = item.rotation['1M'].history.at(-1);
    const threeMonthLatest = item.rotation['3M'].history.at(-1);
    assert(oneWeekLatest?.relativeStrength === oneMonthLatest?.relativeStrength, `${item.name} shares latest strength across intervals`);
    assert(oneMonthLatest?.relativeStrength === threeMonthLatest?.relativeStrength, `${item.name} shares latest 3M strength`);
    assert(oneWeekLatest?.relativeMomentum === oneMonthLatest?.relativeMomentum, `${item.name} shares latest momentum across intervals`);
    assert(oneMonthLatest?.relativeMomentum === threeMonthLatest?.relativeMomentum, `${item.name} shares latest 3M momentum`);
    assert(item.rotationHistory.length === 64, `${item.name} keeps full source rotation history`);
  });

  const crossingItems = [...first.sectors, ...first.themes].filter((item) => {
    const quadrants = new Set(item.rotation['3M'].history.map((point) => classifyQuadrant(point.relativeStrength, point.relativeMomentum)));
    return quadrants.size > 1;
  });
  assert(crossingItems.length >= 6, 'test data includes multiple quadrant-crossing trails');

  const rotationDomain = calculateRotationDomain(first.sectors[0].rotation['3M'].history);
  assert(rotationDomain.xMin <= 100 && rotationDomain.xMax >= 100, 'rotation domain includes neutral strength');
  assert(rotationDomain.yMin <= 100 && rotationDomain.yMax >= 100, 'rotation domain includes neutral momentum');
  assert(rotationDomain.xMax - rotationDomain.xMin >= 6, 'rotation domain keeps a minimum strength span');
  assert(rotationDomain.yMax - rotationDomain.yMin >= 6, 'rotation domain keeps a minimum momentum span');

  const summary = buildRotationTrailSummary(first.sectors[0].rotation['3M'].history);
  assert(summary !== null, 'rotation summary is available for sampled trail');
  if (!summary) {
    throw new Error('rotation summary should be present');
  }
  assert(summary.currentQuadrant === first.sectors[0].rotation['3M'].quadrant, 'rotation summary current quadrant matches latest point');

  const rotationCandidates: RotationLabelCandidate[] = [...first.sectors.slice(0, 4), ...first.themes.slice(0, 4)].map((item) => ({
    fullName: item.name,
    history: item.rotation['3M'].history,
    id: item.id,
    key: `${item.type}:${item.id}`,
    latest: item.rotation['3M'].history[item.rotation['3M'].history.length - 1],
    shortName: getRotationShortLabel(item),
    type: item.type,
  }));
  const selectedCandidate = rotationCandidates[3];
  const watchlistKey = rotationCandidates[4].key;
  const smartLabels = selectSmartLabelKeys(rotationCandidates, {
    labelMode: 'smart',
    maxLabelCount: 3,
    selectedItemKey: selectedCandidate.key,
    watchlistKeys: new Set([watchlistKey]),
  });
  assert(smartLabels.size <= 4, 'smart labels stay limited while preserving selected label');
  assert(smartLabels.has(selectedCandidate.key), 'selected item remains labelled in smart mode');
  assert(selectSmartLabelKeys(rotationCandidates, { labelMode: 'none', maxLabelCount: 3 }).size === 0, 'none mode hides normal labels');
  assert(selectSmartLabelKeys(rotationCandidates, { labelMode: 'all', maxLabelCount: 3 }).size === rotationCandidates.length, 'all mode attempts every label');
  assert(rankRotationLabels(rotationCandidates, { labelMode: 'smart', maxLabelCount: 3, selectedItemKey: selectedCandidate.key })[0].key === selectedCandidate.key, 'selected item has highest label priority');
  assert(rankRotationLabels(rotationCandidates, { labelMode: 'smart', maxLabelCount: 3, watchlistKeys: new Set([watchlistKey]) })[0].key === watchlistKey, 'watchlist item receives label priority');
  assert(getRotationShortLabel({ name: 'Cybersecurity' }) === 'Cybersec.', 'configured short label works');
  assert(getRotationShortLabel({ name: 'Very Long Technology Services Group' }).length > 1, 'fallback short label avoids one-letter labels');

  const leadingCandidates = filterRotationItemsByQuadrant(rotationCandidates, 'leading');
  leadingCandidates.forEach((item) => {
    assert(classifyQuadrant(item.latest.relativeStrength, item.latest.relativeMomentum) === 'leading', 'leading filter keeps leading items');
  });
  assert(filterRotationItemsByQuadrant(rotationCandidates, 'all').length === rotationCandidates.length, 'all quadrant filter restores every point');

  const labelSize = estimateLabelBounds('Cybersec.', 10);
  assert(labelSize.width > 30 && labelSize.height > 10, 'label bounds are estimated');
  assert(doRectsOverlap({ x: 0, y: 0, width: 20, height: 20 }, { x: 10, y: 10, width: 20, height: 20 }), 'overlapping rectangles are detected');
  const placed = findAvailableLabelPlacement(
    {
      chartHeight: 220,
      chartWidth: 220,
      label: 'Cybersec.',
      pointX: 110,
      pointY: 110,
    },
    [{ x: 122, y: 100, width: 80, height: 20 }],
  );
  assert(placed !== null, 'alternate label placement is selected when first position collides');
  if (!placed) {
    throw new Error('label placement should be present');
  }
  assert(placed.bounds.x >= 0 && placed.bounds.y >= 0, 'label remains inside chart bounds');
  assert(
    buildRotationVisibilitySummary({
      filtered: 8,
      labels: 3,
      mode: 'smart',
      quadrantFilter: 'leading',
      total: 12,
    }).includes('8 points shown'),
    'footer reports point count separately from labels',
  );

  allItems.forEach((item) => {
    const breadth = item.breadth;
    assert(breadth.advancing + breadth.declining + breadth.unchanged === breadth.totalStocks, `${item.name} breadth counts add to total`);
    assert(breadth.coveragePercent >= 80 && breadth.coveragePercent <= 100, `${item.name} coverage stays in range`);
    assert(breadth.newHighs <= breadth.totalStocks && breadth.newLows <= breadth.totalStocks, `${item.name} highs/lows stay below total`);
    assert(item.breadthHistory['1M'].length === 20, `${item.name} 1M breadth uses 20 sessions`);
    assert(item.breadthHistory['3M'].length === 60, `${item.name} 3M breadth uses 60 sessions`);
    assert(item.breadthHistory['6M'].length === 120, `${item.name} 6M breadth uses 120 sessions`);

    BREADTH_HISTORY_INTERVALS.forEach((interval) => {
      const history = item.breadthHistory[interval];
      const latest = history[history.length - 1];
      history.forEach((point) => {
        assert(point.percentAbove20Ema >= 5 && point.percentAbove20Ema <= 95, `${item.name} 20 EMA history in range`);
        assert(point.percentAbove50Ema >= 5 && point.percentAbove50Ema <= 95, `${item.name} 50 EMA history in range`);
        assert(point.percentAbove200Ema >= 5 && point.percentAbove200Ema <= 95, `${item.name} 200 EMA history in range`);
      });
      assert(Math.abs(latest.percentAbove20Ema - breadth.percentAbove20Ema) <= 0.1, `${item.name} latest 20 EMA matches snapshot`);
      assert(Math.abs(latest.percentAbove50Ema - breadth.percentAbove50Ema) <= 0.1, `${item.name} latest 50 EMA matches snapshot`);
      assert(Math.abs(latest.percentAbove200Ema - breadth.percentAbove200Ema) <= 0.1, `${item.name} latest 200 EMA matches snapshot`);
    });

    const latest1M = item.breadthHistory['1M'].at(-1);
    const latest3M = item.breadthHistory['3M'].at(-1);
    const latest6M = item.breadthHistory['6M'].at(-1);
    assert(JSON.stringify(latest1M) === JSON.stringify(latest3M), `${item.name} 1M and 3M share latest breadth point`);
    assert(JSON.stringify(latest3M) === JSON.stringify(latest6M), `${item.name} 3M and 6M share latest breadth point`);
    assert(
      averageAdjacentMove(item.breadthHistory['6M'], 'percentAbove20Ema') >= averageAdjacentMove(item.breadthHistory['6M'], 'percentAbove50Ema'),
      `${item.name} 20 EMA breadth is at least as responsive as 50 EMA`,
    );
    assert(
      averageAdjacentMove(item.breadthHistory['6M'], 'percentAbove50Ema') >= averageAdjacentMove(item.breadthHistory['6M'], 'percentAbove200Ema'),
      `${item.name} 200 EMA breadth is the smoothest series`,
    );
  });

  const patternExpectations: Record<BreadthPattern, BreadthHistoryPoint[]> = {
    deteriorating: generateFullBreadthHistory(`${SECTOR_TAB_TEST_SEED}:pattern:deteriorating`, 'deteriorating', 'concentration'),
    improving: generateFullBreadthHistory(`${SECTOR_TAB_TEST_SEED}:pattern:improving`, 'improving', 'concentration'),
    recovery: generateFullBreadthHistory(`${SECTOR_TAB_TEST_SEED}:pattern:recovery`, 'recovery', 'concentration'),
    rollover: generateFullBreadthHistory(`${SECTOR_TAB_TEST_SEED}:pattern:rollover`, 'rollover', 'concentration'),
    volatileNeutral: generateFullBreadthHistory(`${SECTOR_TAB_TEST_SEED}:pattern:volatile`, 'volatileNeutral', 'concentration'),
  };
  assert(breadthDelta(patternExpectations.improving, 'percentAbove20Ema') > 25, 'improving breadth trends upward');
  assert(breadthDelta(patternExpectations.deteriorating, 'percentAbove20Ema') < -25, 'deteriorating breadth trends downward');
  assert(Math.min(...patternExpectations.recovery.slice(0, 60).map((point) => point.percentAbove20Ema)) < patternExpectations.recovery[0].percentAbove20Ema - 5, 'recovery breadth forms a first-half bottom');
  assert(patternExpectations.recovery.at(-1)!.percentAbove20Ema > Math.min(...patternExpectations.recovery.map((point) => point.percentAbove20Ema)) + 30, 'recovery breadth rises from its low');
  assert(Math.max(...patternExpectations.rollover.slice(20, 80).map((point) => point.percentAbove20Ema)) > patternExpectations.rollover.at(-1)!.percentAbove20Ema + 20, 'rollover breadth peaks before weakening');
  assert(Math.max(...patternExpectations.volatileNeutral.map((point) => point.percentAbove20Ema)) - Math.min(...patternExpectations.volatileNeutral.map((point) => point.percentAbove20Ema)) > 10, 'volatile breadth is not flat');
  assert(selectBreadthHistoryWindows(patternExpectations.improving)['1M'].length === 20, 'breadth window selector returns 1M sessions');
  assert(calculateBreadthTrendLabel(patternExpectations.improving) === 'Improving', 'improving history returns Improving trend');
  assert(calculateBreadthTrendLabel(patternExpectations.deteriorating) === 'Deteriorating', 'deteriorating history returns Deteriorating trend');
  assert(calculateBreadthTrendLabel(patternExpectations.recovery) === 'Recovering', 'recovery history returns Recovering trend');
  assert(calculateBreadthTrendLabel(patternExpectations.rollover) === 'Rolling Over', 'rollover history returns Rolling Over trend');

  const stableHistory = Array.from({ length: 20 }, (_, index) => ({
    label: `${index}`,
    percentAbove20Ema: 50 + Math.sin(index / 3) * 0.8,
    percentAbove200Ema: 52 + Math.sin(index / 8) * 0.2,
    percentAbove50Ema: 51 + Math.cos(index / 4) * 0.6,
  }));
  const volatileHistory = Array.from({ length: 20 }, (_, index) => ({
    label: `${index}`,
    percentAbove20Ema: 50 + Math.sin(index * 1.7) * 9,
    percentAbove200Ema: 52 + Math.sin(index * 0.7) * 2,
    percentAbove50Ema: 50 + Math.cos(index * 1.3) * 7,
  }));
  assert(calculateBreadthTrendLabel(stableHistory) === 'Stable', 'stable history returns Stable trend');
  assert(calculateBreadthTrendLabel(volatileHistory) === 'Volatile', 'volatile history returns Volatile trend');
  const netChanges = calculateBreadthNetChanges(patternExpectations.improving);
  assert(netChanges.change20 === Number((netChanges.end20 - netChanges.start20).toFixed(1)), 'net breadth changes are rounded from source values');
  assert(formatBreadthPointChange(61.9, 36.2).changeLabel === '-25.7 pts', 'breadth point change formats percentage points');

  const alerts = buildRotationAlerts(first.sectors, '1M');
  assert(alerts.length <= 3, 'sector alerts are capped at three');
  alerts.forEach((alert) => {
    const item = first.sectors.find((sector) => sector.id === alert.id.split('-1M-')[0] || alert.name === sector.name);
    assert(item, 'alert maps to an actual sector');
  });
}

run();
