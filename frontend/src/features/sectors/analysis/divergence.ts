import {
  classifyQuadrant,
  type RotationPoint,
  type SectorThemeTestItem,
} from '@/data/sectorTabTestData';

import { calculateLeadershipConcentration } from './concentration';

export type DivergenceSignal = {
  id: string;
  itemId: string;
  itemType: 'sector' | 'theme';
  severity: DivergenceSeverity;
  direction: 'positive' | 'negative' | 'mixed';
  type: 'breadth' | 'rotation' | 'concentration' | 'price_rotation';
  title: string;
  summary: string;
  implication: string;
  evidence: string[];
  evidenceRows: DivergenceEvidenceRow[];
  source: 'test';
};

export type DivergenceSeverity = 'low' | 'medium' | 'high';

export type DivergenceEvidenceRow = {
  change?: number;
  label: string;
  primary: string;
  secondary?: string;
  tone?: 'positive' | 'negative' | 'mixed' | 'muted';
};

type DivergenceSeverityInputs = {
  breadthChange20?: number;
  breadthChange50?: number;
  concentrationPercent?: number;
  confirmingMetrics?: number;
  momentumChange?: number;
  priceReturn?: number;
  type: DivergenceSignal['type'];
};

export function detectDivergences(item: SectorThemeTestItem): DivergenceSignal[] {
  const signals: DivergenceSignal[] = [];
  const history = item.rotation['1M'].history;
  const momentumTrend = getTrend(history, 'relativeMomentum');
  const strengthTrend = getTrend(history, 'relativeStrength');
  const latest = history.at(-1);
  const previous = history.at(-2);
  const latestQuadrant = latest ? classifyQuadrant(latest.relativeStrength, latest.relativeMomentum) : item.quadrant;
  const previousQuadrant = previous ? classifyQuadrant(previous.relativeStrength, previous.relativeMomentum) : latestQuadrant;
  const concentration = calculateLeadershipConcentration(item);
  const breadthChange = calculateBreadthTrend(item.breadthHistory['3M']);
  const breadth20 = item.breadth.percentAbove20Ema;
  const breadth50 = item.breadth.percentAbove50Ema;

  if (item.returns['1M'] > 3 && breadthChange.change20 < -10 && breadthChange.change50 < -5 && momentumTrend < 0.05) {
    const severity = calculateDivergenceSeverity({
      breadthChange20: breadthChange.change20,
      breadthChange50: breadthChange.change50,
      confirmingMetrics: 4,
      momentumChange: momentumTrend,
      priceReturn: item.returns['1M'],
      type: 'breadth',
    });
    signals.push({
      direction: 'negative',
      evidence: [
        `1M return: ${formatPercent(item.returns['1M'])}`,
        `Above 20 EMA: ${formatBreadthMove(breadthChange.start20, breadth20)}`,
        `Above 50 EMA: ${formatBreadthMove(breadthChange.start50, breadth50)}`,
        `Relative momentum: ${formatSigned(momentumTrend)}`,
      ],
      id: `${item.id}-negative-breadth`,
      itemId: item.id,
      itemType: item.type,
      evidenceRows: [
        createReturnEvidenceRow('1M Return', item.returns['1M']),
        createMoveEvidenceRow('Above 20 EMA', breadthChange.start20, breadth20, 'pts'),
        createMoveEvidenceRow('Above 50 EMA', breadthChange.start50, breadth50, 'pts'),
        createSingleChangeEvidenceRow('Relative Momentum', momentumTrend),
      ],
      implication: 'The group is still rising, but participation is becoming narrower.',
      severity,
      source: 'test',
      summary: `${item.name} is rising, but short-term breadth and relative momentum are weakening.`,
      title: 'Negative Breadth Divergence',
      type: 'breadth',
    });
  }

  if (item.returns['1M'] < 0 && breadthChange.change20 > 10 && breadthChange.change50 > 6 && momentumTrend > 0.05) {
    const severity = calculateDivergenceSeverity({
      breadthChange20: breadthChange.change20,
      breadthChange50: breadthChange.change50,
      confirmingMetrics: 4,
      momentumChange: momentumTrend,
      priceReturn: item.returns['1M'],
      type: 'breadth',
    });
    signals.push({
      direction: 'positive',
      evidence: [
        `1M return: ${formatPercent(item.returns['1M'])}`,
        `Above 20 EMA: ${formatBreadthMove(breadthChange.start20, breadth20)}`,
        `Above 50 EMA: ${formatBreadthMove(breadthChange.start50, breadth50)}`,
        `Relative momentum: ${formatSigned(momentumTrend)}`,
      ],
      id: `${item.id}-positive-breadth`,
      itemId: item.id,
      itemType: item.type,
      evidenceRows: [
        createReturnEvidenceRow('1M Return', item.returns['1M']),
        createMoveEvidenceRow('Above 20 EMA', breadthChange.start20, breadth20, 'pts'),
        createMoveEvidenceRow('Above 50 EMA', breadthChange.start50, breadth50, 'pts'),
        createSingleChangeEvidenceRow('Relative Momentum', momentumTrend),
      ],
      implication: 'Internal participation is improving before price fully confirms.',
      severity,
      source: 'test',
      summary: `${item.name} remains weak on price, but participation and relative momentum are improving.`,
      title: 'Positive Breadth Divergence',
      type: 'breadth',
    });
  }

  if (latestQuadrant === 'leading' && latest && latest.relativeStrength > 100 && momentumTrend < -0.05) {
    const severity = calculateDivergenceSeverity({
      confirmingMetrics: 3,
      momentumChange: momentumTrend,
      type: 'rotation',
    });
    signals.push({
      direction: 'negative',
      evidence: [
        `Current quadrant: Leading`,
        `Relative momentum trend: ${formatSigned(momentumTrend)}`,
        `Relative strength trend: ${formatSigned(strengthTrend)}`,
      ],
      id: `${item.id}-rotation-deterioration`,
      itemId: item.id,
      itemType: item.type,
      evidenceRows: [
        { label: 'Current Quadrant', primary: 'Leading', tone: 'mixed' },
        createSingleChangeEvidenceRow('Relative Momentum', momentumTrend),
        createSingleChangeEvidenceRow('Relative Strength', strengthTrend),
      ],
      implication: 'Leadership remains positive, but rotation momentum is fading.',
      severity,
      source: 'test',
      summary: `${item.name} remains Leading, but rotation momentum is deteriorating.`,
      title: 'Rotation Divergence',
      type: 'rotation',
    });
  }

  if (
    item.returns['1M'] > 2 &&
    concentration.top3ContributionPercent >= 65 &&
    concentration.medianConstituentReturn < item.returns['1M'] * 0.35 &&
    concentration.percentOutperformingGroup < 35
  ) {
    const severity = calculateDivergenceSeverity({
      concentrationPercent: concentration.top3ContributionPercent,
      confirmingMetrics: 4,
      priceReturn: item.returns['1M'],
      type: 'concentration',
    });
    signals.push({
      direction: 'mixed',
      evidence: [
        `1M return: ${formatPercent(item.returns['1M'])}`,
        `Top 3 contribution: ${concentration.top3ContributionPercent.toFixed(1)}%`,
        `Median constituent return: ${formatPercent(concentration.medianConstituentReturn)}`,
        `Outperforming constituents: ${concentration.percentOutperformingGroup.toFixed(1)}%`,
      ],
      id: `${item.id}-concentration`,
      itemId: item.id,
      itemType: item.type,
      evidenceRows: [
        createReturnEvidenceRow('1M Return', item.returns['1M']),
        createPercentEvidenceRow('Top 3 Contribution', concentration.top3ContributionPercent, 'mixed'),
        createReturnEvidenceRow('Median Constituent Return', concentration.medianConstituentReturn),
        createPercentEvidenceRow('Outperforming Constituents', concentration.percentOutperformingGroup, 'negative'),
      ],
      implication: 'The group is rising, but fewer constituents are carrying the move.',
      severity,
      source: 'test',
      summary: `${item.name} is rising, but gains are concentrated in a small number of constituents.`,
      title: 'Concentration Divergence',
      type: 'concentration',
    });
  }

  if (item.returns['1W'] < -1 && latest && (latestQuadrant === 'improving' || latestQuadrant === 'leading') && previousQuadrant !== 'lagging' && momentumTrend > 0.05) {
    const severity = calculateDivergenceSeverity({
      confirmingMetrics: 3,
      momentumChange: momentumTrend,
      priceReturn: item.returns['1W'],
      type: 'price_rotation',
    });
    signals.push({
      direction: 'positive',
      evidence: [
        `1W return: ${formatPercent(item.returns['1W'])}`,
        `Rotation: ${previousQuadrant} -> ${latestQuadrant}`,
        `Relative strength: ${latest.relativeStrength.toFixed(1)}`,
        `Relative momentum trend: ${formatSigned(momentumTrend)}`,
      ],
      id: `${item.id}-price-rotation`,
      itemId: item.id,
      itemType: item.type,
      evidenceRows: [
        createReturnEvidenceRow('1W Return', item.returns['1W']),
        { label: 'Rotation', primary: `${previousQuadrant} → ${latestQuadrant}`, tone: 'positive' },
        { label: 'Relative Strength', primary: latest.relativeStrength.toFixed(1), tone: latest.relativeStrength >= 100 ? 'positive' : 'muted' },
        createSingleChangeEvidenceRow('Relative Momentum', momentumTrend),
      ],
      implication: 'Price remains weak, but relative rotation continues to improve.',
      severity,
      source: 'test',
      summary: `${item.name} is down over one week, but relative rotation continues to improve.`,
      title: 'Price / Rotation Divergence',
      type: 'price_rotation',
    });
  }

  return signals.sort(compareDivergenceSignals).slice(0, 3);
}

export function calculateBreadthTrend(history: SectorThemeTestItem['breadthHistory']['1M']) {
  const first = history[0] ?? {
    percentAbove20Ema: 0,
    percentAbove50Ema: 0,
    percentAbove200Ema: 0,
  };
  const latest = history[history.length - 1] ?? first;
  return {
    change20: latest.percentAbove20Ema - first.percentAbove20Ema,
    change200: latest.percentAbove200Ema - first.percentAbove200Ema,
    change50: latest.percentAbove50Ema - first.percentAbove50Ema,
    start20: first.percentAbove20Ema,
    start200: first.percentAbove200Ema,
    start50: first.percentAbove50Ema,
  };
}

export function calculateDivergenceSeverity(inputs: DivergenceSeverityInputs): DivergenceSeverity {
  let score = 0;

  if (inputs.priceReturn !== undefined) {
    score += Math.min(24, Math.abs(inputs.priceReturn) * 3);
  }
  if (inputs.breadthChange20 !== undefined) {
    score += Math.min(28, Math.abs(inputs.breadthChange20) * 1.25);
  }
  if (inputs.breadthChange50 !== undefined) {
    score += Math.min(20, Math.abs(inputs.breadthChange50) * 1.35);
  }
  if (inputs.momentumChange !== undefined) {
    score += Math.min(18, Math.abs(inputs.momentumChange) * 90);
  }
  if (inputs.concentrationPercent !== undefined) {
    score += Math.min(35, Math.max(0, inputs.concentrationPercent - 55) * 1.4);
  }
  score += Math.min(20, (inputs.confirmingMetrics ?? 0) * 4);

  if (inputs.type === 'price_rotation') {
    score *= 0.72;
  }
  if (inputs.type === 'concentration') {
    score *= 0.9;
  }

  if (score >= 70) {
    return 'high';
  }
  if (score >= 40) {
    return 'medium';
  }
  return 'low';
}

export function buildDivergenceEvidenceRows(signal: DivergenceSignal): DivergenceEvidenceRow[] {
  return signal.evidenceRows;
}

export function buildDivergenceAccessibilitySummary(signal: DivergenceSignal) {
  return `${capitalize(signal.severity)} ${signal.direction} divergence. ${signal.summary}`;
}

function compareDivergenceSignals(a: DivergenceSignal, b: DivergenceSignal) {
  return getSignalPriority(a) - getSignalPriority(b);
}

function getSignalPriority(signal: DivergenceSignal) {
  if (signal.title === 'Negative Breadth Divergence' && signal.severity === 'high') {
    return 1;
  }
  if (signal.title === 'Concentration Divergence' && signal.severity === 'high') {
    return 2;
  }
  if (signal.title === 'Rotation Divergence') {
    return 3;
  }
  if (signal.title === 'Positive Breadth Divergence') {
    return 4;
  }
  if (signal.title === 'Price / Rotation Divergence') {
    return 5;
  }
  return 6;
}

function getTrend(history: RotationPoint[], key: 'relativeStrength' | 'relativeMomentum') {
  if (history.length < 3) {
    return 0;
  }
  const first = history[0];
  const latest = history[history.length - 1];
  return (latest[key] - first[key]) / Math.max(history.length - 1, 1);
}

function formatPercent(value: number) {
  const prefix = value > 0 ? '+' : '';
  return `${prefix}${value.toFixed(1)}%`;
}

function formatBreadthMove(start: number, end: number) {
  return `${start.toFixed(1)}% -> ${end.toFixed(1)}%`;
}

function formatSigned(value: number) {
  const prefix = value > 0 ? '+' : '';
  return `${prefix}${value.toFixed(2)}`;
}

function createMoveEvidenceRow(label: string, start: number, end: number, unit: 'pts'): DivergenceEvidenceRow {
  const change = end - start;
  const arrow = change > 0 ? '↑' : change < 0 ? '↓' : '→';
  const prefix = change > 0 ? '+' : '';
  return {
    change,
    label,
    primary: `${start.toFixed(1)}% ${arrow} ${end.toFixed(1)}%`,
    secondary: `Change: ${prefix}${change.toFixed(1)} ${unit}`,
    tone: change > 0 ? 'positive' : change < 0 ? 'negative' : 'muted',
  };
}

function createSingleChangeEvidenceRow(label: string, change: number): DivergenceEvidenceRow {
  const arrow = change > 0 ? '↑' : change < 0 ? '↓' : '→';
  const prefix = change > 0 ? '+' : '';
  return {
    change,
    label,
    primary: `${arrow} ${prefix}${change.toFixed(2)}`,
    secondary: `Change: ${prefix}${change.toFixed(2)}`,
    tone: change > 0 ? 'positive' : change < 0 ? 'negative' : 'muted',
  };
}

function createReturnEvidenceRow(label: string, value: number): DivergenceEvidenceRow {
  return {
    change: value,
    label,
    primary: formatPercent(value),
    tone: value > 0 ? 'positive' : value < 0 ? 'negative' : 'muted',
  };
}

function createPercentEvidenceRow(label: string, value: number, tone: DivergenceEvidenceRow['tone']): DivergenceEvidenceRow {
  return {
    change: value,
    label,
    primary: `${value.toFixed(1)}%`,
    tone,
  };
}

function capitalize(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}
