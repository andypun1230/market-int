import type { SectorThemeTestItem, TestHeatmapInterval } from '@/data/sectorTabTestData';

import { calculateLeadershipConcentration } from './concentration';
import { detectDivergences } from './divergence';

export function canCompare(items: SectorThemeTestItem[]) {
  return items.length >= 2 && items.length <= 3;
}

export function addComparisonItem(items: SectorThemeTestItem[], item: SectorThemeTestItem) {
  if (items.some((current) => current.type === item.type && current.id === item.id)) {
    return items;
  }
  if (items.length >= 3) {
    return items;
  }
  return [...items, item];
}

export function removeComparisonItem(items: SectorThemeTestItem[], item: SectorThemeTestItem) {
  return items.filter((current) => !(current.type === item.type && current.id === item.id));
}

export function rankComparisonMetrics(items: SectorThemeTestItem[]) {
  if (!items.length) {
    return null;
  }
  const concentrations = items.map((item) => ({
    item,
    concentration: calculateLeadershipConcentration(item),
  }));

  return {
    bestBreadth: maxBy(items, (item) => item.breadth.percentAbove50Ema),
    bestRotation: maxBy(items, (item) => item.relativeMomentum + item.relativeStrength),
    lowestConcentrationRisk: minBy(concentrations, (entry) => entry.concentration.concentrationScore).item,
    strongestPerformance: maxBy(items, (item) => item.returns['1M']),
  };
}

export function buildComparisonRows(items: SectorThemeTestItem[], intervals: readonly TestHeatmapInterval[]) {
  return [
    ...intervals.map((interval) => ({
      label: interval,
      values: items.map((item) => formatPercent(item.returns[interval])),
    })),
    {
      label: 'Quadrant',
      values: items.map((item) => capitalize(item.quadrant)),
    },
    {
      label: 'Relative Strength',
      values: items.map((item) => item.relativeStrength.toFixed(1)),
    },
    {
      label: 'Relative Momentum',
      values: items.map((item) => item.relativeMomentum.toFixed(1)),
    },
    {
      label: 'Above 20 EMA',
      values: items.map((item) => `${item.breadth.percentAbove20Ema.toFixed(1)}%`),
    },
    {
      label: 'Above 50 EMA',
      values: items.map((item) => `${item.breadth.percentAbove50Ema.toFixed(1)}%`),
    },
    {
      label: 'Above 200 EMA',
      values: items.map((item) => `${item.breadth.percentAbove200Ema.toFixed(1)}%`),
    },
    {
      label: 'A/D Ratio',
      values: items.map((item) => item.breadth.advanceDeclineRatio?.toFixed(2) ?? 'N/A'),
    },
    {
      label: 'Participation',
      values: items.map((item) => item.breadth.participationLabel),
    },
    {
      label: 'Top 3 Contribution',
      values: items.map((item) => `${calculateLeadershipConcentration(item).top3ContributionPercent.toFixed(1)}%`),
    },
    {
      label: 'Weighted Return',
      values: items.map((item) => formatPercent(calculateLeadershipConcentration(item).weightedReturn)),
    },
    {
      label: 'Equal Weight Return',
      values: items.map((item) => formatPercent(calculateLeadershipConcentration(item).equalWeightReturn)),
    },
    {
      label: 'Divergences',
      values: items.map((item) => `${detectDivergences(item).length}`),
    },
  ];
}

function maxBy<T>(items: T[], getValue: (item: T) => number) {
  return items.reduce((best, item) => (getValue(item) > getValue(best) ? item : best), items[0]);
}

function minBy<T>(items: T[], getValue: (item: T) => number) {
  return items.reduce((best, item) => (getValue(item) < getValue(best) ? item : best), items[0]);
}

function capitalize(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function formatPercent(value: number) {
  const prefix = value > 0 ? '+' : '';
  return `${prefix}${value.toFixed(2)}%`;
}
