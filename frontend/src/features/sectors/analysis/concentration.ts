import type { ConstituentTestItem, SectorThemeTestItem } from '@/data/sectorTabTestData';

export type LeadershipConcentration = {
  top1ContributionPercent: number;
  top3ContributionPercent: number;
  top5ContributionPercent: number;
  weightedReturn: number;
  equalWeightReturn: number;
  medianConstituentReturn: number;
  percentOutperformingGroup: number;
  concentrationScore: number;
  label: 'Broad' | 'Moderate' | 'Concentrated' | 'Highly Concentrated';
  topContributors: (ConstituentTestItem & { contribution: number; contributionShare: number })[];
  source: 'test';
};

export function calculateLeadershipConcentration(item: SectorThemeTestItem): LeadershipConcentration {
  const constituents = item.constituents;
  const weightedReturn = sum(constituents.map((constituent) => constituent.weight * constituent.return1M / 100));
  const equalWeightReturn = average(constituents.map((constituent) => constituent.return1M));
  const medianConstituentReturn = median(constituents.map((constituent) => constituent.return1M));
  const contributions = constituents
    .map((constituent) => ({
      ...constituent,
      contribution: constituent.weight * constituent.return1M / 100,
    }))
    .sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution));
  const totalAbsoluteContribution = sum(contributions.map((constituent) => Math.abs(constituent.contribution)));
  const withShares = contributions.map((constituent) => ({
    ...constituent,
    contributionShare: totalAbsoluteContribution > 0 ? Math.abs(constituent.contribution) / totalAbsoluteContribution * 100 : 0,
  }));
  const top1ContributionPercent = contributionShare(withShares, 1);
  const top3ContributionPercent = contributionShare(withShares, 3);
  const top5ContributionPercent = contributionShare(withShares, 5);
  const percentOutperformingGroup = constituents.length
    ? constituents.filter((constituent) => constituent.return1M > item.returns['1M']).length / constituents.length * 100
    : 0;
  const concentrationScore = Math.max(0, Math.min(100, top3ContributionPercent * 1.1 + top1ContributionPercent * 0.35));

  return {
    concentrationScore: round(concentrationScore),
    equalWeightReturn: round(equalWeightReturn),
    label: getConcentrationLabel(top3ContributionPercent),
    medianConstituentReturn: round(medianConstituentReturn),
    percentOutperformingGroup: round(percentOutperformingGroup),
    source: 'test',
    top1ContributionPercent: round(top1ContributionPercent),
    top3ContributionPercent: round(top3ContributionPercent),
    top5ContributionPercent: round(top5ContributionPercent),
    topContributors: withShares.slice(0, 5).map((constituent) => ({
      ...constituent,
      contribution: round(constituent.contribution),
      contributionShare: round(constituent.contributionShare),
    })),
    weightedReturn: round(weightedReturn),
  };
}

function contributionShare(items: { contributionShare: number }[], count: number) {
  return sum(items.slice(0, count).map((item) => item.contributionShare));
}

function getConcentrationLabel(top3: number): LeadershipConcentration['label'] {
  if (top3 < 35) {
    return 'Broad';
  }
  if (top3 < 55) {
    return 'Moderate';
  }
  if (top3 < 75) {
    return 'Concentrated';
  }
  return 'Highly Concentrated';
}

function average(values: number[]) {
  return values.length ? sum(values) / values.length : 0;
}

function median(values: number[]) {
  if (!values.length) {
    return 0;
  }
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}

function sum(values: number[]) {
  return values.reduce((total, value) => total + value, 0);
}

function round(value: number) {
  return Math.round(value * 100) / 100;
}
