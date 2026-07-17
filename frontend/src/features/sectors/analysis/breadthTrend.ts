import type { BreadthHistoryPoint } from '@/data/sectorTabTestData';

export type BreadthTrendLabel =
  | 'Improving'
  | 'Deteriorating'
  | 'Recovering'
  | 'Rolling Over'
  | 'Stable'
  | 'Volatile';

export type BreadthNetChanges = {
  start20: number;
  end20: number;
  change20: number;
  start50: number;
  end50: number;
  change50: number;
  start200: number;
  end200: number;
  change200: number;
};

export function calculateBreadthNetChanges(history: BreadthHistoryPoint[]): BreadthNetChanges {
  const first = history[0] ?? createEmptyBreadthPoint();
  const latest = history.at(-1) ?? first;
  return {
    change20: roundPoint(latest.percentAbove20Ema - first.percentAbove20Ema),
    change200: roundPoint(latest.percentAbove200Ema - first.percentAbove200Ema),
    change50: roundPoint(latest.percentAbove50Ema - first.percentAbove50Ema),
    end20: latest.percentAbove20Ema,
    end200: latest.percentAbove200Ema,
    end50: latest.percentAbove50Ema,
    start20: first.percentAbove20Ema,
    start200: first.percentAbove200Ema,
    start50: first.percentAbove50Ema,
  };
}

export function calculateBreadthTrendLabel(history: BreadthHistoryPoint[]): BreadthTrendLabel {
  if (history.length < 6) {
    return 'Stable';
  }

  const changes = calculateBreadthNetChanges(history);
  const recent = history.slice(Math.max(0, history.length - Math.max(6, Math.floor(history.length * 0.25))));
  const recentChanges = calculateBreadthNetChanges(recent);
  const low20 = getExtreme(history, 'percentAbove20Ema', 'min');
  const high20 = getExtreme(history, 'percentAbove20Ema', 'max');
  const low50 = getExtreme(history, 'percentAbove50Ema', 'min');
  const high50 = getExtreme(history, 'percentAbove50Ema', 'max');
  const volatility20 = getAverageAdjacentMove(history, 'percentAbove20Ema');
  const volatility50 = getAverageAdjacentMove(history, 'percentAbove50Ema');

  if (
    low20.index < history.length * 0.72 &&
    changes.start20 - low20.value > 5 &&
    changes.end20 - low20.value > 18 &&
    changes.end50 - low50.value > 9 &&
    recentChanges.change20 > 5
  ) {
    return 'Recovering';
  }

  if (
    high20.index > history.length * 0.18 &&
    high20.index < history.length * 0.86 &&
    changes.change20 < -8 &&
    high20.value - changes.end20 > 12 &&
    high50.value - changes.end50 > 6 &&
    recentChanges.change20 < -4
  ) {
    return 'Rolling Over';
  }

  if (changes.change20 > 10 && changes.change50 > 6) {
    return 'Improving';
  }

  if (changes.change20 < -10 && changes.change50 < -5) {
    return 'Deteriorating';
  }

  if (Math.abs(changes.change20) <= 5 && Math.abs(changes.change50) <= 4 && volatility20 <= 3.2 && volatility50 <= 2.2) {
    return 'Stable';
  }

  return 'Volatile';
}

export function formatBreadthPointChange(start: number, end: number) {
  const change = roundPoint(end - start);
  const arrow = change > 0 ? '↑' : change < 0 ? '↓' : '→';
  const prefix = change > 0 ? '+' : '';
  return {
    arrow,
    change,
    changeLabel: `${prefix}${change.toFixed(1)} pts`,
    rangeLabel: `${start.toFixed(1)}% ${arrow} ${end.toFixed(1)}%`,
  };
}

export function buildBreadthAccessibilitySummary(history: BreadthHistoryPoint[]) {
  const trend = calculateBreadthTrendLabel(history).toLowerCase();
  const changes = calculateBreadthNetChanges(history);
  return `Breadth ${trend}. Stocks above the 20-day EMA moved from ${changes.start20.toFixed(1)}% to ${changes.end20.toFixed(1)}%. Stocks above the 50-day EMA moved from ${changes.start50.toFixed(1)}% to ${changes.end50.toFixed(1)}%.`;
}

function createEmptyBreadthPoint(): BreadthHistoryPoint {
  return {
    label: 'N/A',
    percentAbove20Ema: 0,
    percentAbove200Ema: 0,
    percentAbove50Ema: 0,
  };
}

function getAverageAdjacentMove(history: BreadthHistoryPoint[], key: keyof Omit<BreadthHistoryPoint, 'label'>) {
  if (history.length < 2) {
    return 0;
  }
  const total = history.slice(1).reduce((sum, point, index) => sum + Math.abs(point[key] - history[index][key]), 0);
  return total / (history.length - 1);
}

function getExtreme(
  history: BreadthHistoryPoint[],
  key: keyof Omit<BreadthHistoryPoint, 'label'>,
  mode: 'min' | 'max',
) {
  return history.reduce(
    (current, point, index) => {
      const isBetter = mode === 'min' ? point[key] < current.value : point[key] > current.value;
      return isBetter ? { index, value: point[key] } : current;
    },
    { index: 0, value: history[0]?.[key] ?? 0 },
  );
}

function roundPoint(value: number) {
  return Math.round(value * 10) / 10;
}
