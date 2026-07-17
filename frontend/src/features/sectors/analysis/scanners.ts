import type { SectorThemeTestItem } from '@/data/sectorTabTestData';

import { calculateLeadershipConcentration } from './concentration';
import { detectDivergences } from './divergence';

export type ScannerResult = {
  item: SectorThemeTestItem;
  score: number;
  label: string;
  reasons: string[];
  source: 'test';
};

export function buildEmergingLeadershipScanner(items: SectorThemeTestItem[], maxItems = 5): ScannerResult[] {
  return items
    .map((item) => {
      const concentration = calculateLeadershipConcentration(item);
      const momentumTrend = trend(item, 'relativeMomentum');
      const breadthTrend = breadthTrend20(item);
      const score = clamp(
        (item.quadrant === 'improving' ? 28 : item.quadrant === 'lagging' ? 12 : 8) +
          (item.relativeMomentum >= 100 ? 18 : 8) +
          Math.max(0, 18 - Math.abs(100 - item.relativeStrength) * 3) +
          clamp(breadthTrend * 4, 0, 18) +
          clamp((item.returns['1M'] - item.returns['3M'] / 3) * 2, 0, 16) +
          (concentration.top3ContributionPercent < 55 ? 12 : 4),
        0,
        100,
      );
      const reasons = [
        item.quadrant === 'improving' ? 'Improving quadrant' : `${capitalize(item.quadrant)} quadrant`,
        momentumTrend >= 0 ? 'Relative momentum rising' : 'Momentum stabilizing',
        breadthTrend >= 0 ? 'Breadth expanding' : 'Breadth watch',
      ];

      return {
        item,
        label: score >= 78 ? 'Strong candidate' : score >= 62 ? 'Developing' : 'Early improvement',
        reasons,
        score: Math.round(score),
        source: 'test' as const,
      };
    })
    .filter((result) => result.score >= 48)
    .sort((a, b) => b.score - a.score || a.item.name.localeCompare(b.item.name))
    .slice(0, maxItems);
}

export function buildLeadershipRiskScanner(items: SectorThemeTestItem[], maxItems = 5): ScannerResult[] {
  return items
    .map((item) => {
      const concentration = calculateLeadershipConcentration(item);
      const divergences = detectDivergences(item);
      const momentumTrend = trend(item, 'relativeMomentum');
      const breadthTrend = breadthTrend20(item);
      const score = clamp(
        (item.quadrant === 'leading' ? 18 : item.quadrant === 'weakening' ? 30 : 6) +
          clamp(-momentumTrend * 13, 0, 24) +
          clamp(-breadthTrend * 5, 0, 18) +
          (divergences.some((signal) => signal.direction === 'negative') ? 18 : 0) +
          (concentration.top3ContributionPercent >= 58 ? 14 : 4) +
          (item.relativeMomentum < 100 ? 10 : 0),
        0,
        100,
      );
      const reasons = [
        item.quadrant === 'weakening' ? 'Weakening quadrant' : `${capitalize(item.quadrant)} quadrant`,
        momentumTrend < 0 ? 'Relative momentum falling' : 'Momentum still positive',
        concentration.top3ContributionPercent >= 58 ? 'Concentration elevated' : 'Concentration manageable',
      ];

      return {
        item,
        label: score >= 75 ? 'High deterioration risk' : score >= 58 ? 'Moderate deterioration risk' : 'Early warning',
        reasons,
        score: Math.round(score),
        source: 'test' as const,
      };
    })
    .filter((result) => result.score >= 42)
    .sort((a, b) => b.score - a.score || a.item.name.localeCompare(b.item.name))
    .slice(0, maxItems);
}

function trend(item: SectorThemeTestItem, key: 'relativeMomentum' | 'relativeStrength') {
  const history = item.rotation['1M'].history;
  if (history.length < 3) {
    return 0;
  }
  return history.at(-1)![key] - history.at(-3)![key];
}

function breadthTrend20(item: SectorThemeTestItem) {
  const history = item.breadthHistory['1M'];
  if (history.length < 5) {
    return 0;
  }
  return history.at(-1)!.percentAbove20Ema - history.at(-5)!.percentAbove20Ema;
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

function capitalize(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}
