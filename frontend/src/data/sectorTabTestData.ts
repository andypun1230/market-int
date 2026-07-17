export const SECTOR_TAB_TEST_SEED = 'sector-tab-test-v1';

export const TEST_HEATMAP_INTERVALS = ['1D', '1W', '1M', '3M', '6M', '1Y'] as const;
export const TEST_ROTATION_INTERVALS = ['1W', '1M', '3M'] as const;
export const BREADTH_HISTORY_INTERVALS = ['1M', '3M', '6M'] as const;

export type TestHeatmapInterval = (typeof TEST_HEATMAP_INTERVALS)[number];
export type TestRotationInterval = (typeof TEST_ROTATION_INTERVALS)[number];
export type BreadthHistoryInterval = (typeof BREADTH_HISTORY_INTERVALS)[number];
export type TestSource = 'test';
export type GroupType = 'sector' | 'theme';
export type RotationQuadrant = 'leading' | 'weakening' | 'lagging' | 'improving';
export type BreadthPattern = 'improving' | 'deteriorating' | 'recovery' | 'rollover' | 'volatileNeutral';
export type DivergenceScenario =
  | 'none'
  | 'positiveBreadth'
  | 'negativeBreadth'
  | 'rotation'
  | 'concentration'
  | 'priceRotation';

export type TestPerformanceIntervals = Record<TestHeatmapInterval, number>;

export type RotationPoint = {
  dateLabel: string;
  relativeStrength: number;
  relativeMomentum: number;
};

export type RotationDomain = {
  xMin: number;
  xMax: number;
  yMin: number;
  yMax: number;
};

export type RotationSpeed = 'Stable' | 'Gradual' | 'Accelerating' | 'Rapid';

export type RotationTrailSummary = {
  startQuadrant: RotationQuadrant;
  currentQuadrant: RotationQuadrant;
  netRelativeStrength: number;
  netRelativeMomentum: number;
  speed: RotationSpeed;
};

export type TestRotationWindow = {
  relativeStrength: number;
  relativeMomentum: number;
  quadrant: RotationQuadrant;
  history: RotationPoint[];
};

export type SectorBreadthSnapshot = {
  totalStocks: number;
  advancing: number;
  declining: number;
  unchanged: number;
  advanceDeclineRatio: number | null;
  percentAbove20Ema: number;
  percentAbove50Ema: number;
  percentAbove200Ema: number;
  newHighs: number;
  newLows: number;
  coveragePercent: number;
  participationLabel: 'Broad' | 'Healthy' | 'Selective' | 'Narrow' | 'Deteriorating';
  source: TestSource;
};

export type ConstituentTestItem = {
  companyName?: string;
  groupId: string;
  groupType: GroupType;
  marketCapCategory: 'large' | 'mid' | 'small';
  momentumLabel: 'strong' | 'improving' | 'neutral' | 'weakening' | 'weak';
  relativeMomentum: number;
  returns: TestPerformanceIntervals;
  source: TestSource;
  ticker: string;
  weight: number;
  return1D: number;
  return1W: number;
  return1M: number;
  relativeStrength: number;
  above20Ema: boolean;
  above50Ema: boolean;
};

export type BreadthHistoryPoint = {
  label: string;
  percentAbove20Ema: number;
  percentAbove50Ema: number;
  percentAbove200Ema: number;
};

export type RotationAlert = {
  id: string;
  name: string;
  previousQuadrant: RotationQuadrant;
  currentQuadrant: RotationQuadrant;
  interval: TestRotationInterval;
  message: string;
  source: TestSource;
};

export type TestPerformanceItem = {
  id: string;
  name: string;
  type: GroupType;
  returns: TestPerformanceIntervals;
  rotation: Record<TestRotationInterval, TestRotationWindow>;
  relativeStrength: number;
  relativeMomentum: number;
  quadrant: RotationQuadrant;
  rotationHistory: RotationPoint[];
  breadth: SectorBreadthSnapshot;
  breadthHistory: Record<BreadthHistoryInterval, BreadthHistoryPoint[]>;
  constituents: ConstituentTestItem[];
  source: TestSource;
};

export type TestSectorItem = TestPerformanceItem & { type: 'sector' };

export type TestThemeItem = TestPerformanceItem & {
  type: 'theme';
  parentSector: string;
};

export type SectorThemeTestItem = TestSectorItem | TestThemeItem;

export type SectorTabTestData = {
  benchmark: 'SPY';
  seed: string;
  sectors: TestSectorItem[];
  themes: TestThemeItem[];
  source: TestSource;
};

const SECTOR_NAMES = [
  'Technology',
  'Financials',
  'Healthcare',
  'Consumer Discretionary',
  'Consumer Staples',
  'Communication Services',
  'Industrials',
  'Energy',
  'Utilities',
  'Real Estate',
  'Materials',
] as const;

const THEME_DEFINITIONS = [
  ['AI Infrastructure', 'Technology'],
  ['Semiconductors', 'Technology'],
  ['Memory', 'Technology'],
  ['Data Centers', 'Technology'],
  ['Optical Networking', 'Technology'],
  ['Cybersecurity', 'Technology'],
  ['Robotics', 'Industrials'],
  ['Defense Technology', 'Industrials'],
  ['Nuclear Energy', 'Utilities'],
  ['Space', 'Industrials'],
  ['Quantum Computing', 'Technology'],
  ['Fintech', 'Financials'],
  ['Biotechnology', 'Healthcare'],
  ['Medical Devices', 'Healthcare'],
  ['Oil & Gas', 'Energy'],
] as const;

const RETURN_RANGES: Record<TestHeatmapInterval, [number, number]> = {
  '1D': [-4, 4],
  '1W': [-8, 8],
  '1M': [-15, 15],
  '3M': [-25, 25],
  '6M': [-35, 35],
  '1Y': [-50, 60],
};
const BREADTH_PATTERNS: BreadthPattern[] = ['improving', 'deteriorating', 'recovery', 'rollover', 'volatileNeutral'];
const DIVERGENCE_SCENARIOS: DivergenceScenario[] = [
  'none',
  'none',
  'none',
  'positiveBreadth',
  'positiveBreadth',
  'negativeBreadth',
  'negativeBreadth',
  'rotation',
  'concentration',
  'priceRotation',
];

export function createSeededRandom(seed: string) {
  let hash = 2166136261;
  for (let index = 0; index < seed.length; index += 1) {
    hash ^= seed.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }

  return function seededRandom() {
    hash += 0x6D2B79F5;
    let value = hash;
    value = Math.imul(value ^ (value >>> 15), value | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}

export function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

export function classifyQuadrant(relativeStrength: number, relativeMomentum: number): RotationQuadrant {
  if (relativeStrength >= 100 && relativeMomentum >= 100) {
    return 'leading';
  }
  if (relativeStrength >= 100 && relativeMomentum < 100) {
    return 'weakening';
  }
  if (relativeStrength < 100 && relativeMomentum < 100) {
    return 'lagging';
  }
  return 'improving';
}

export function generateSectorTabTestData(seed = SECTOR_TAB_TEST_SEED): SectorTabTestData {
  const sectors = SECTOR_NAMES.map((name, index) => {
    const id = slugify(name);
    const scenario = getDivergenceScenarioForItem(id, seed);
    const pattern = getBreadthPatternForItem(id, seed);
    const returns = applyDivergenceScenarioToReturns(generateReturns(`${seed}:sector:${id}:returns`, index), scenario);
    const rotationState = generateRotationState(`${seed}:sector:${id}:rotation`, index, scenario);
    const mainRotation = rotationState.windows['1M'];
    const fullBreadthHistory = generateFullBreadthHistory(`${seed}:sector:${id}:history`, pattern, scenario);
    const breadth = deriveBreadthSnapshotFromHistory(`${seed}:sector:${id}:breadth`, fullBreadthHistory, returns['1M'], scenario);
    const breadthHistory = selectBreadthHistoryWindows(fullBreadthHistory);
    const constituents = generateConstituents(`${seed}:sector:${id}:constituents`, id, 'sector', breadth.totalStocks, returns, scenario);

    return {
      breadth,
      breadthHistory,
      constituents,
      id,
      name,
      quadrant: mainRotation.quadrant,
      relativeMomentum: mainRotation.relativeMomentum,
      relativeStrength: mainRotation.relativeStrength,
      returns,
      rotation: rotationState.windows,
      rotationHistory: rotationState.fullHistory,
      source: 'test' as const,
      type: 'sector' as const,
    };
  });

  const themes = THEME_DEFINITIONS.map(([name, parentSector], index) => {
    const id = slugify(name);
    const scenario = getDivergenceScenarioForItem(id, seed);
    const pattern = getBreadthPatternForItem(id, seed);
    const returns = applyDivergenceScenarioToReturns(generateReturns(`${seed}:theme:${id}:returns`, index + 3), scenario);
    const rotationState = generateRotationState(`${seed}:theme:${id}:rotation`, index + 5, scenario);
    const mainRotation = rotationState.windows['1M'];
    const fullBreadthHistory = generateFullBreadthHistory(`${seed}:theme:${id}:history`, pattern, scenario);
    const breadth = deriveBreadthSnapshotFromHistory(`${seed}:theme:${id}:breadth`, fullBreadthHistory, returns['1M'], scenario);
    return {
      breadth,
      breadthHistory: selectBreadthHistoryWindows(fullBreadthHistory),
      constituents: generateConstituents(`${seed}:theme:${id}:constituents`, id, 'theme', Math.min(32, Math.max(12, Math.round(breadth.totalStocks * 0.45))), returns, scenario),
      id,
      name,
      parentSector,
      quadrant: mainRotation.quadrant,
      relativeMomentum: mainRotation.relativeMomentum,
      relativeStrength: mainRotation.relativeStrength,
      returns,
      rotation: rotationState.windows,
      rotationHistory: rotationState.fullHistory,
      source: 'test' as const,
      type: 'theme' as const,
    };
  });

  return {
    benchmark: 'SPY',
    seed,
    sectors,
    themes,
    source: 'test',
  };
}

export function getBreadthPatternForItem(itemId: string, seed = SECTOR_TAB_TEST_SEED): BreadthPattern {
  return BREADTH_PATTERNS[stableHash(`${seed}:breadth-pattern:${itemId}`) % BREADTH_PATTERNS.length];
}

export function getDivergenceScenarioForItem(itemId: string, seed = SECTOR_TAB_TEST_SEED): DivergenceScenario {
  return DIVERGENCE_SCENARIOS[stableHash(`${seed}:divergence-scenario:${itemId}`) % DIVERGENCE_SCENARIOS.length];
}

export function buildRotationAlerts(
  items: SectorThemeTestItem[],
  interval: TestRotationInterval,
  maxAlerts = 3,
): RotationAlert[] {
  const alerts = items
    .map((item) => {
      const history = item.rotation[interval].history;
      const previous = history.at(-2);
      const current = history.at(-1);
      if (!previous || !current) {
        return null;
      }
      const previousQuadrant = classifyQuadrant(previous.relativeStrength, previous.relativeMomentum);
      const currentQuadrant = classifyQuadrant(current.relativeStrength, current.relativeMomentum);
      const move =
        Math.abs(current.relativeStrength - previous.relativeStrength) +
        Math.abs(current.relativeMomentum - previous.relativeMomentum);

      if (previousQuadrant !== currentQuadrant) {
        return {
          id: `${item.id}-${interval}-quadrant`,
          name: item.name,
          previousQuadrant,
          currentQuadrant,
          interval,
          message: `${formatQuadrant(previousQuadrant)} -> ${formatQuadrant(currentQuadrant)}`,
          move,
          source: 'test' as const,
        };
      }

      if (currentQuadrant === 'leading' && history.slice(-3).every((point) => classifyQuadrant(point.relativeStrength, point.relativeMomentum) === 'leading')) {
        return {
          id: `${item.id}-${interval}-held-leading`,
          name: item.name,
          previousQuadrant,
          currentQuadrant,
          interval,
          message: 'Remained Leading',
          move,
          source: 'test' as const,
        };
      }

      return null;
    })
    .filter((alert): alert is RotationAlert & { move: number } => alert !== null)
    .sort((a, b) => b.move - a.move)
    .slice(0, maxAlerts);

  return alerts.map(({ move: _move, ...alert }) => alert);
}

export function formatQuadrant(quadrant: RotationQuadrant) {
  switch (quadrant) {
    case 'leading':
      return 'Leading';
    case 'weakening':
      return 'Weakening';
    case 'lagging':
      return 'Lagging';
    case 'improving':
      return 'Improving';
  }
}

export function getRotationWindow<T extends TestPerformanceItem>(item: T, interval: TestRotationInterval) {
  return item.rotation[interval];
}

export function selectRotationTrail(history: RotationPoint[], interval: TestRotationInterval): RotationPoint[] {
  if (interval === '1W') {
    return history.slice(-5);
  }

  const lookback = interval === '1M' ? 20 : 60;
  const targetPoints = interval === '1M' ? 10 : 12;
  const window = history.slice(-lookback);
  return sampleRotationTrail(window, targetPoints);
}

export function calculateRotationDomain(points: RotationPoint[]): RotationDomain {
  const strengths = points.map((point) => point.relativeStrength);
  const momentum = points.map((point) => point.relativeMomentum);
  const xBounds = calculateAxisBounds(strengths);
  const yBounds = calculateAxisBounds(momentum);

  return {
    xMin: xBounds.min,
    xMax: xBounds.max,
    yMin: yBounds.min,
    yMax: yBounds.max,
  };
}

export function buildRotationTrailSummary(points: RotationPoint[]): RotationTrailSummary | null {
  const first = points[0];
  const latest = points[points.length - 1];
  if (!first || !latest) {
    return null;
  }

  return {
    currentQuadrant: classifyQuadrant(latest.relativeStrength, latest.relativeMomentum),
    netRelativeMomentum: round(latest.relativeMomentum - first.relativeMomentum, 2),
    netRelativeStrength: round(latest.relativeStrength - first.relativeStrength, 2),
    speed: calculateRotationSpeed(points),
    startQuadrant: classifyQuadrant(first.relativeStrength, first.relativeMomentum),
  };
}

export function calculateRotationSpeed(points: RotationPoint[]): RotationSpeed {
  if (points.length < 2) {
    return 'Stable';
  }

  const distances = points.slice(1).map((point, index) => {
    const previous = points[index];
    return Math.hypot(point.relativeStrength - previous.relativeStrength, point.relativeMomentum - previous.relativeMomentum);
  });
  const average = distances.reduce((sum, value) => sum + value, 0) / distances.length;
  const recent = distances.slice(-3);
  const recentAverage = recent.reduce((sum, value) => sum + value, 0) / Math.max(recent.length, 1);

  if (recentAverage >= 0.9 || average >= 0.75) {
    return 'Rapid';
  }
  if (recentAverage >= average * 1.3 && recentAverage >= 0.45) {
    return 'Accelerating';
  }
  if (average >= 0.22) {
    return 'Gradual';
  }
  return 'Stable';
}

function generateReturns(seed: string, index: number): TestPerformanceIntervals {
  const rng = createSeededRandom(seed);
  const intervals = {} as TestPerformanceIntervals;

  TEST_HEATMAP_INTERVALS.forEach((interval, intervalIndex) => {
    const [min, max] = RETURN_RANGES[interval];
    const leaderBias = index % 7 === 0 ? 0.65 : index % 5 === 0 ? -0.55 : 0;
    const nearZeroBias = index % 9 === 0 && intervalIndex < 2 ? -0.48 : 0;
    const raw = min + (max - min) * clamp(rng() + leaderBias * 0.18 + nearZeroBias * 0.14, 0, 1);
    intervals[interval] = round(raw, 2);
  });

  return intervals;
}

function applyDivergenceScenarioToReturns(
  returns: TestPerformanceIntervals,
  scenario: DivergenceScenario,
): TestPerformanceIntervals {
  const adjusted = { ...returns };
  switch (scenario) {
    case 'positiveBreadth':
      adjusted['1W'] = Math.min(adjusted['1W'], -1.4);
      adjusted['1M'] = Math.min(adjusted['1M'], -3.4);
      break;
    case 'negativeBreadth':
      adjusted['1W'] = Math.max(adjusted['1W'], 1.2);
      adjusted['1M'] = Math.max(adjusted['1M'], 4.8);
      break;
    case 'rotation':
      adjusted['1M'] = Math.max(adjusted['1M'], 2.5);
      break;
    case 'concentration':
      adjusted['1M'] = Math.max(adjusted['1M'], 5.4);
      adjusted['3M'] = Math.max(adjusted['3M'], 8.5);
      break;
    case 'priceRotation':
      adjusted['1W'] = Math.min(adjusted['1W'], -2.2);
      adjusted['1M'] = Math.min(adjusted['1M'], -1.2);
      break;
    case 'none':
      adjusted['1W'] = clamp(adjusted['1W'], -0.4, 1.4);
      adjusted['1M'] = clamp(adjusted['1M'], -0.8, 1.8);
      adjusted['3M'] = clamp(adjusted['3M'], -2.2, 3.2);
      adjusted['6M'] = clamp(adjusted['6M'], -4.5, 6.5);
      break;
    default:
      break;
  }
  return adjusted;
}

function generateRotationState(seed: string, index: number, scenario: DivergenceScenario) {
  const fullHistory = generateRotationHistory(seed, index, scenario);
  const windows = TEST_ROTATION_INTERVALS.reduce((accumulator, interval) => {
    const history = selectRotationTrail(fullHistory, interval);
    const latest = history[history.length - 1];
    accumulator[interval] = {
      history,
      relativeStrength: latest.relativeStrength,
      relativeMomentum: latest.relativeMomentum,
      quadrant: classifyQuadrant(latest.relativeStrength, latest.relativeMomentum),
    };
    return accumulator;
  }, {} as Record<TestRotationInterval, TestRotationWindow>);

  return {
    fullHistory,
    windows,
  };
}

function generateRotationHistory(seed: string, index: number, scenario: DivergenceScenario): RotationPoint[] {
  const rng = createSeededRandom(seed);
  const count = 64;
  if (scenario === 'rotation') {
    return generateRotationDeteriorationHistory(rng, count);
  }
  const style = getRotationStyleForScenario(index, scenario);
  const start = getRotationStart(style, rng);
  const end = getRotationEnd(style, rng);

  return Array.from({ length: count }, (_, pointIndex) => {
    const progress = pointIndex / (count - 1);
    const eased = easeInOut(progress);
    const wave = Math.sin(progress * Math.PI * (style % 3 === 0 ? 2.2 : 1.35) + rng() * 0.6);
    const reverse = Math.max(0, (progress - 0.62) / 0.38);
    const reversalStrength = style === 2 || style === 6 ? reverse * (style === 2 ? -2.4 : 2.1) : 0;
    const reversalMomentum = style === 3 || style === 7 ? reverse * (style === 3 ? 2.2 : -2) : 0;
    const noiseStrength = (rng() - 0.5) * 0.34;
    const noiseMomentum = (rng() - 0.5) * 0.34;
    const relativeStrength = clamp(
      start.relativeStrength + (end.relativeStrength - start.relativeStrength) * eased + wave * 0.35 + reversalStrength + noiseStrength,
      94,
      106,
    );
    const relativeMomentum = clamp(
      start.relativeMomentum + (end.relativeMomentum - start.relativeMomentum) * eased + Math.cos(progress * Math.PI * 1.8) * 0.28 + reversalMomentum + noiseMomentum,
      94,
      106,
    );

    return {
      dateLabel: buildRotationLabel(count - pointIndex - 1),
      relativeStrength: round(relativeStrength, 2),
      relativeMomentum: round(relativeMomentum, 2),
    };
  });
}

function generateRotationDeteriorationHistory(rng: () => number, count: number): RotationPoint[] {
  return Array.from({ length: count }, (_, pointIndex) => {
    const progress = pointIndex / (count - 1);
    const relativeStrength = clamp(102.1 + progress * 2.1 + Math.sin(progress * Math.PI * 1.4) * 0.35 + (rng() - 0.5) * 0.24, 100.4, 106);
    const relativeMomentum = clamp(104.6 - progress * 3.2 + Math.cos(progress * Math.PI * 1.6) * 0.25 + (rng() - 0.5) * 0.22, 100.6, 106);
    return {
      dateLabel: buildRotationLabel(count - pointIndex - 1),
      relativeMomentum: round(relativeMomentum, 2),
      relativeStrength: round(relativeStrength, 2),
    };
  });
}

function getRotationStyleForScenario(index: number, scenario: DivergenceScenario) {
  switch (scenario) {
    case 'positiveBreadth':
    case 'priceRotation':
      return 4;
    case 'negativeBreadth':
      return 7;
    case 'rotation':
      return 1;
    case 'concentration':
      return 5;
    case 'none':
    default:
      return index % 8;
  }
}

function sampleRotationTrail(history: RotationPoint[], targetPoints: number) {
  if (history.length <= targetPoints) {
    return history;
  }

  const selected: RotationPoint[] = [];
  const maxIndex = history.length - 1;
  for (let index = 0; index < targetPoints; index += 1) {
    const sourceIndex = Math.round((index / (targetPoints - 1)) * maxIndex);
    selected.push(history[sourceIndex]);
  }
  return selected;
}

function calculateAxisBounds(values: number[]) {
  const validValues = values.length ? values : [100];
  const rawMin = Math.min(100, ...validValues);
  const rawMax = Math.max(100, ...validValues);
  const center = (rawMin + rawMax) / 2;
  const span = Math.max(rawMax - rawMin + 1.2, 6);
  const min = clamp(center - span / 2, 92, 108 - span);
  const max = clamp(center + span / 2, min + span, 108);
  return {
    max: round(max, 1),
    min: round(min, 1),
  };
}

function getRotationStart(style: number, rng: () => number) {
  const starts = [
    { relativeStrength: 97.2, relativeMomentum: 96.2 },
    { relativeStrength: 99.1, relativeMomentum: 102.5 },
    { relativeStrength: 103.6, relativeMomentum: 103.2 },
    { relativeStrength: 104.2, relativeMomentum: 98.3 },
    { relativeStrength: 96.5, relativeMomentum: 101.2 },
    { relativeStrength: 101.4, relativeMomentum: 101.6 },
    { relativeStrength: 95.4, relativeMomentum: 95.8 },
    { relativeStrength: 102.7, relativeMomentum: 96.4 },
  ];
  return jitterRotationPoint(starts[style], rng, 0.45);
}

function getRotationEnd(style: number, rng: () => number) {
  const ends = [
    { relativeStrength: 103.5, relativeMomentum: 103.8 },
    { relativeStrength: 104.6, relativeMomentum: 98.4 },
    { relativeStrength: 99.2, relativeMomentum: 96.6 },
    { relativeStrength: 97.1, relativeMomentum: 101.9 },
    { relativeStrength: 100.9, relativeMomentum: 104.2 },
    { relativeStrength: 103.8, relativeMomentum: 102.4 },
    { relativeStrength: 101.8, relativeMomentum: 99.5 },
    { relativeStrength: 100.3, relativeMomentum: 95.6 },
  ];
  return jitterRotationPoint(ends[style], rng, 0.5);
}

function jitterRotationPoint(point: Pick<RotationPoint, 'relativeStrength' | 'relativeMomentum'>, rng: () => number, amount: number) {
  return {
    relativeMomentum: clamp(point.relativeMomentum + (rng() - 0.5) * amount, 94, 106),
    relativeStrength: clamp(point.relativeStrength + (rng() - 0.5) * amount, 94, 106),
  };
}

function easeInOut(value: number) {
  return value < 0.5 ? 2 * value * value : 1 - Math.pow(-2 * value + 2, 2) / 2;
}

function deriveBreadthSnapshotFromHistory(
  seed: string,
  history: BreadthHistoryPoint[],
  oneMonthReturn: number,
  scenario: DivergenceScenario,
): SectorBreadthSnapshot {
  const rng = createSeededRandom(seed);
  const latest = history[history.length - 1];
  const previous = history[Math.max(0, history.length - 6)];
  const totalStocks = randomInteger(rng, 48, 95);
  const directionalBias =
    scenario === 'negativeBreadth' || scenario === 'rotation'
      ? -0.1
      : scenario === 'positiveBreadth' || scenario === 'priceRotation'
        ? 0.08
        : 0;
  const participation = clamp(latest.percentAbove50Ema / 100 + oneMonthReturn / 120 + directionalBias, 0.12, 0.9);
  const advancing = clamp(Math.round(totalStocks * participation), 4, totalStocks - 4);
  const unchanged = randomInteger(rng, 0, Math.min(4, totalStocks - advancing));
  const declining = totalStocks - advancing - unchanged;
  const recent20Change = latest.percentAbove20Ema - previous.percentAbove20Ema;

  return {
    advancing,
    advanceDeclineRatio: declining > 0 ? round(advancing / declining, 2) : null,
    coveragePercent: round(randomBetween(rng, 84, 100), 1),
    declining,
    newHighs: clamp(Math.round(totalStocks * clamp((latest.percentAbove20Ema - 50) / 190 + Math.max(0, recent20Change) / 170, 0.01, 0.16)), 0, totalStocks),
    newLows: clamp(Math.round(totalStocks * clamp((50 - latest.percentAbove20Ema) / 180 + Math.max(0, -recent20Change) / 170, 0.01, 0.14)), 0, totalStocks),
    participationLabel: getParticipationLabel(latest.percentAbove50Ema),
    percentAbove20Ema: latest.percentAbove20Ema,
    percentAbove200Ema: latest.percentAbove200Ema,
    percentAbove50Ema: latest.percentAbove50Ema,
    source: 'test',
    totalStocks,
    unchanged,
  };
}

function generateConstituents(
  seed: string,
  prefix: string,
  groupType: GroupType,
  requestedCount: number,
  returns: TestPerformanceIntervals,
  scenario: DivergenceScenario,
): ConstituentTestItem[] {
  const rng = createSeededRandom(seed);
  const count = clamp(requestedCount, 8, 32);
  const rawWeights = Array.from({ length: count }, (_, index) => {
    const scenarioBoost = scenario === 'concentration' && index < 3 ? 4.5 - index * 0.75 : 1;
    const leaderBoost = index < 3 ? 2.4 - index * 0.45 : 1;
    return (0.45 + rng() * 1.25) * leaderBoost * scenarioBoost;
  });
  const totalWeight = rawWeights.reduce((sum, value) => sum + value, 0);

  return rawWeights.map((rawWeight, index) => {
    const relativeNoise = (rng() - 0.5) * 9;
    const stockReturns = generateStockReturns(rng, returns, index, scenario);
    const return1M = stockReturns['1M'];
    const relativeStrength = clamp(100 + returns['1M'] * 0.18 + relativeNoise, 82, 118);
    const relativeMomentum = clamp(100 + stockReturns['1W'] * 0.22 + (rng() - 0.5) * 7, 82, 118);

    return {
      above20Ema: return1M > -2 || relativeStrength > 99,
      above50Ema: return1M > 1 || relativeStrength > 102,
      companyName: `${prefix.replace(/-/g, ' ')} ${index + 1}`,
      groupId: prefix,
      groupType,
      marketCapCategory: index < 4 ? 'large' : index < 12 ? 'mid' : 'small',
      momentumLabel: getMomentumLabel(relativeMomentum, stockReturns['1W']),
      relativeStrength: round(relativeStrength, 1),
      relativeMomentum: round(relativeMomentum, 1),
      returns: stockReturns,
      return1D: stockReturns['1D'],
      return1M: round(return1M, 2),
      return1W: stockReturns['1W'],
      source: 'test',
      ticker: `${prefix.replace(/-/g, '').slice(0, 4).toUpperCase()}${index + 1}`,
      weight: round(rawWeight / totalWeight * 100, 2),
    };
  });
}

function generateStockReturns(
  rng: () => number,
  groupReturns: TestPerformanceIntervals,
  index: number,
  scenario: DivergenceScenario,
): TestPerformanceIntervals {
  const leaderBoost = index < 3 ? 1 : 0;
  return TEST_HEATMAP_INTERVALS.reduce((accumulator, interval) => {
    const noiseScale = interval === '1D' ? 2.8 : interval === '1W' ? 5.5 : interval === '1M' ? 14 : interval === '3M' ? 18 : interval === '6M' ? 24 : 30;
    const concentrationBias = scenario === 'concentration'
      ? index < 3
        ? noiseScale * 0.46
        : -Math.max(5, Math.abs(groupReturns[interval]) * 1.1)
      : 0;
    accumulator[interval] = round(groupReturns[interval] + (rng() - 0.5) * noiseScale + leaderBoost * rng() * (noiseScale * 0.25) + concentrationBias, 2);
    return accumulator;
  }, {} as TestPerformanceIntervals);
}

function getMomentumLabel(relativeMomentum: number, weeklyReturn: number): ConstituentTestItem['momentumLabel'] {
  if (relativeMomentum >= 108 && weeklyReturn > 1) {
    return 'strong';
  }
  if (relativeMomentum >= 102) {
    return 'improving';
  }
  if (relativeMomentum <= 92 || weeklyReturn < -3) {
    return 'weak';
  }
  if (relativeMomentum < 98) {
    return 'weakening';
  }
  return 'neutral';
}

export function selectBreadthHistoryWindows(history: BreadthHistoryPoint[]): Record<BreadthHistoryInterval, BreadthHistoryPoint[]> {
  return {
    '1M': history.slice(-20),
    '3M': history.slice(-60),
    '6M': history.slice(-120),
  };
}

export function generateFullBreadthHistory(
  seed: string,
  pattern: BreadthPattern,
  scenario: DivergenceScenario = 'none',
): BreadthHistoryPoint[] {
  const rng = createSeededRandom(seed);
  const count = 120;
  const anchors = getBreadthAnchors(pattern, scenario, rng);
  const raw = Array.from({ length: count }, (_, index) => {
    const progress = index / (count - 1);
    const base20 = interpolateAnchors(anchors.above20, progress);
    const base50 = interpolateAnchors(anchors.above50, progress);
    const base200 = interpolateAnchors(anchors.above200, progress);
    const cycle = Math.sin(progress * Math.PI * 5.2 + rng() * 0.8);
    const slowCycle = Math.cos(progress * Math.PI * 2.2 + rng() * 0.7);

    return {
      label: index === count - 1 ? 'Current' : `-${count - index - 1}`,
      percentAbove20Ema: clampPercent(base20 + cycle * 3.4 + (rng() - 0.5) * 4.5),
      percentAbove50Ema: clampPercent(base50 + cycle * 1.8 + slowCycle * 1.2 + (rng() - 0.5) * 2.8),
      percentAbove200Ema: clampPercent(base200 + slowCycle * 0.9 + (rng() - 0.5) * 1.5),
    };
  });

  return smoothBreadthSeries(raw).map((point, index) => ({
    ...point,
    label: index === count - 1 ? 'Current' : `-${count - index - 1}`,
  }));
}

function getBreadthAnchors(pattern: BreadthPattern, scenario: DivergenceScenario, rng: () => number) {
  const scenarioPattern = getScenarioBreadthPattern(pattern, scenario);
  const jitter = () => (rng() - 0.5) * 5;
  switch (scenarioPattern) {
    case 'improving':
      return {
        above20: [34 + jitter(), 47 + jitter(), 59 + jitter(), 73 + jitter()],
        above50: [32 + jitter(), 41 + jitter(), 51 + jitter(), 62 + jitter()],
        above200: [40 + jitter() * 0.4, 43 + jitter() * 0.4, 47 + jitter() * 0.4, 51 + jitter() * 0.4],
      };
    case 'deteriorating':
      return {
        above20: [79 + jitter(), 69 + jitter(), 54 + jitter(), 38 + jitter()],
        above50: [71 + jitter(), 64 + jitter(), 56 + jitter(), 47 + jitter()],
        above200: [62 + jitter() * 0.4, 60 + jitter() * 0.4, 57 + jitter() * 0.4, 54 + jitter() * 0.4],
      };
    case 'recovery':
      return {
        above20: [34 + jitter(), 24 + jitter(), 40 + jitter(), 68 + jitter()],
        above50: [40 + jitter(), 31 + jitter(), 39 + jitter(), 56 + jitter()],
        above200: [46 + jitter() * 0.4, 43 + jitter() * 0.4, 45 + jitter() * 0.4, 49 + jitter() * 0.4],
      };
    case 'rollover':
      return {
        above20: [62 + jitter(), 80 + jitter(), 68 + jitter(), 48 + jitter()],
        above50: [58 + jitter(), 70 + jitter(), 63 + jitter(), 54 + jitter()],
        above200: [52 + jitter() * 0.4, 58 + jitter() * 0.4, 58 + jitter() * 0.4, 55 + jitter() * 0.4],
      };
    case 'volatileNeutral':
    default:
      return {
        above20: [45 + jitter(), 61 + jitter(), 48 + jitter(), 57 + jitter(), 44 + jitter()],
        above50: [47 + jitter(), 55 + jitter(), 50 + jitter(), 54 + jitter(), 49 + jitter()],
        above200: [51 + jitter() * 0.4, 53 + jitter() * 0.4, 52 + jitter() * 0.4, 54 + jitter() * 0.4, 53 + jitter() * 0.4],
      };
  }
}

function getScenarioBreadthPattern(pattern: BreadthPattern, scenario: DivergenceScenario): BreadthPattern {
  switch (scenario) {
    case 'positiveBreadth':
    case 'priceRotation':
      return 'recovery';
    case 'negativeBreadth':
      return 'deteriorating';
    case 'rotation':
      return 'rollover';
    case 'none':
      return 'volatileNeutral';
    default:
      return pattern;
  }
}

function interpolateAnchors(values: number[], progress: number) {
  const scaled = progress * (values.length - 1);
  const startIndex = Math.floor(scaled);
  const endIndex = Math.min(values.length - 1, startIndex + 1);
  const localProgress = scaled - startIndex;
  const eased = easeInOut(localProgress);
  return values[startIndex] + (values[endIndex] - values[startIndex]) * eased;
}

function smoothBreadthSeries(points: BreadthHistoryPoint[]) {
  return points.map((point, index) => {
    const previous = points[index - 1];
    if (!previous) {
      return point;
    }
    return {
      ...point,
      percentAbove20Ema: clampPercent(previous.percentAbove20Ema + clamp(point.percentAbove20Ema - previous.percentAbove20Ema, -6.5, 6.5)),
      percentAbove50Ema: clampPercent(previous.percentAbove50Ema + clamp(point.percentAbove50Ema - previous.percentAbove50Ema, -4.2, 4.2)),
      percentAbove200Ema: clampPercent(previous.percentAbove200Ema + clamp(point.percentAbove200Ema - previous.percentAbove200Ema, -2, 2)),
    };
  });
}

function clampPercent(value: number) {
  return round(clamp(value, 5, 95), 1);
}

function buildRotationLabel(stepsAgo: number) {
  if (stepsAgo === 0) {
    return 'Current';
  }
  return `-${stepsAgo}d`;
}

function getParticipationLabel(value: number): SectorBreadthSnapshot['participationLabel'] {
  if (value >= 78) {
    return 'Broad';
  }
  if (value >= 62) {
    return 'Healthy';
  }
  if (value >= 45) {
    return 'Selective';
  }
  if (value >= 30) {
    return 'Narrow';
  }
  return 'Deteriorating';
}

function slugify(value: string) {
  return value.toLowerCase().replace(/&/g, 'and').replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
}

function randomBetween(rng: () => number, min: number, max: number) {
  return min + (max - min) * rng();
}

function randomInteger(rng: () => number, min: number, max: number) {
  return Math.floor(randomBetween(rng, min, max + 1));
}

function stableHash(value: string) {
  let hash = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return Math.abs(hash >>> 0);
}

function round(value: number, digits: number) {
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}
