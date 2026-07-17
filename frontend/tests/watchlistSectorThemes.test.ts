import type { SectorThemeTestItem, TestHeatmapInterval } from '../src/data/sectorTabTestData';
import { classifySectorThemeItem } from '../src/features/watchlist/sectorThemeClassifier';
import {
  groupSectorThemeItems,
  sortSectorThemeItems,
  type ClassifiedSectorThemeItem,
} from '../src/features/watchlist/sectorThemeSort';
import type { GroupWatchlistItem } from '../src/features/watchlist/store';

function assert(condition: unknown, message: string) {
  if (!condition) {
    throw new Error(message);
  }
}

function item(overrides: Partial<SectorThemeTestItem>): SectorThemeTestItem {
  const base = {
    breadth: { source: 'test' },
    breadthHistory: {
      '1M': [
        { label: 'a', percentAbove20Ema: 50, percentAbove50Ema: 50, percentAbove200Ema: 50 },
        { label: 'b', percentAbove20Ema: 52, percentAbove50Ema: 51, percentAbove200Ema: 50 },
        { label: 'c', percentAbove20Ema: 54, percentAbove50Ema: 52, percentAbove200Ema: 50 },
        { label: 'd', percentAbove20Ema: 56, percentAbove50Ema: 53, percentAbove200Ema: 51 },
        { label: 'e', percentAbove20Ema: 59, percentAbove50Ema: 55, percentAbove200Ema: 51 },
      ],
    },
    constituents: [],
    id: 'technology',
    name: 'Technology',
    quadrant: 'leading',
    relativeMomentum: 103,
    relativeStrength: 104,
    returns: {
      '1D': 0.5,
      '1W': 1.5,
      '1M': 4,
      '3M': 8,
      '6M': 12,
      '1Y': 20,
    },
    rotation: {
      '1M': {
        history: [
          { dateLabel: 'a', relativeMomentum: 101, relativeStrength: 102 },
          { dateLabel: 'b', relativeMomentum: 102, relativeStrength: 103 },
          { dateLabel: 'c', relativeMomentum: 103, relativeStrength: 104 },
        ],
        quadrant: 'leading',
        relativeMomentum: 103,
        relativeStrength: 104,
      },
    },
    rotationHistory: [],
    source: 'test',
    type: 'sector',
  } as unknown as SectorThemeTestItem;
  return { ...base, ...overrides } as SectorThemeTestItem;
}

function stored(id: string, name: string, type: 'sector' | 'theme' = 'sector', index = 0): GroupWatchlistItem {
  return {
    addedAt: `2026-07-11T00:00:0${index}.000Z`,
    id,
    name,
    type,
  };
}

function classified(
  itemOverride: Partial<SectorThemeTestItem> | null,
  originalIndex: number,
  period: TestHeatmapInterval = '1M',
): ClassifiedSectorThemeItem {
  const storedItem = stored(`item-${originalIndex}`, itemOverride?.name ?? `Item ${originalIndex}`, itemOverride?.type ?? 'sector', originalIndex);
  const sectorThemeItem = itemOverride === null ? null : item({ id: storedItem.id, name: storedItem.name, ...itemOverride });
  return {
    classification: classifySectorThemeItem({
      item: sectorThemeItem,
      period,
      stored: storedItem,
    }),
    item: sectorThemeItem,
    originalIndex,
    stored: storedItem,
  };
}

function run() {
  const leading = classified({ name: 'Leading', quadrant: 'leading', relativeMomentum: 104, relativeStrength: 105 }, 0);
  assert(leading.classification.group === 'leading', 'leading item goes to Leading');

  const improving = classified({
    name: 'Improving',
    quadrant: 'improving',
    relativeMomentum: 101,
    relativeStrength: 98,
    rotation: {
      '1M': {
        history: [
          { dateLabel: 'a', relativeMomentum: 98, relativeStrength: 97 },
          { dateLabel: 'b', relativeMomentum: 99, relativeStrength: 98 },
          { dateLabel: 'c', relativeMomentum: 101, relativeStrength: 98 },
        ],
        quadrant: 'improving',
        relativeMomentum: 101,
        relativeStrength: 98,
      },
    },
  } as Partial<SectorThemeTestItem>, 1);
  assert(improving.classification.group === 'improving', 'improving item goes to Improving');

  const neutral = classified({
    name: 'Neutral',
    quadrant: 'leading',
    relativeMomentum: 99,
    relativeStrength: 100.2,
    breadthHistory: {
      '1M': [
        { label: 'a', percentAbove20Ema: 50, percentAbove50Ema: 50, percentAbove200Ema: 50 },
        { label: 'b', percentAbove20Ema: 50.2, percentAbove50Ema: 50, percentAbove200Ema: 50 },
        { label: 'c', percentAbove20Ema: 50.1, percentAbove50Ema: 50, percentAbove200Ema: 50 },
        { label: 'd', percentAbove20Ema: 50.4, percentAbove50Ema: 50, percentAbove200Ema: 50 },
        { label: 'e', percentAbove20Ema: 50.5, percentAbove50Ema: 50, percentAbove200Ema: 50 },
      ],
    },
    rotation: {
      '1M': {
        history: [
          { dateLabel: 'a', relativeMomentum: 99, relativeStrength: 100 },
          { dateLabel: 'b', relativeMomentum: 99.1, relativeStrength: 100.1 },
          { dateLabel: 'c', relativeMomentum: 99.2, relativeStrength: 100.2 },
        ],
        quadrant: 'leading',
        relativeMomentum: 99,
        relativeStrength: 100.2,
      },
    },
    returns: { '1D': 0, '1W': 0.1, '1M': 0.2, '3M': 1, '6M': 2, '1Y': 3 },
  } as Partial<SectorThemeTestItem>, 2);
  assert(neutral.classification.group === 'watching', 'neutral item goes to Watching');

  const weakening = classified({
    name: 'Weakening',
    quadrant: 'weakening',
    relativeMomentum: 97,
    relativeStrength: 102,
  }, 3);
  assert(weakening.classification.group === 'weakening', 'weakening item goes to Weakening');

  const unavailable = classified(null, 4);
  assert(unavailable.classification.group === 'data_unavailable', 'missing item goes to Data Unavailable');
  assert(unavailable.classification.score === null, 'unavailable score is null');

  const laggingPositive = classified({
    name: 'Lagging Positive',
    quadrant: 'lagging',
    relativeMomentum: 99,
    relativeStrength: 99,
    returns: { '1D': 1, '1W': 2, '1M': 6, '3M': 8, '6M': 10, '1Y': 14 },
  }, 5);
  assert(laggingPositive.classification.group === 'weakening', 'weakening precedence beats positive return');

  const entries = [neutral, unavailable, leading, weakening, improving];
  const smart = sortSectorThemeItems(entries, 'smartPriority');
  assert(smart.map((entry) => entry.classification.group).join(',') === 'leading,improving,watching,weakening,data_unavailable', 'smart priority order');

  const topReturn = sortSectorThemeItems(entries, 'topReturn');
  assert(topReturn[0].classification.returnPercent === 4, 'top return puts highest valid return first');
  assert(topReturn.at(-1)?.classification.group === 'data_unavailable', 'missing returns sort last');

  const weakest = sortSectorThemeItems(entries, 'weakest');
  assert(weakest[0].classification.returnPercent === 0.2, 'weakest puts lowest valid return first');
  assert(weakest.at(-1)?.classification.group === 'data_unavailable', 'missing weak return sorts last');

  const recent = sortSectorThemeItems(entries, 'recent');
  assert(recent[0].originalIndex === 4, 'recent uses saved timestamp/order');

  const grouped = groupSectorThemeItems(entries);
  const totalGrouped = Object.values(grouped).reduce((sum, group) => sum + group.length, 0);
  assert(totalGrouped === entries.length, 'each item appears in exactly one group');
  assert(grouped.data_unavailable.length === 1, 'data unavailable group is populated');
}

run();
