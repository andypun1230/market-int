import type { SectorThemeTestItem, TestHeatmapInterval } from '@/data/sectorTabTestData';

import type {
  SectorThemeClassification,
  SectorThemeDataStatus,
  SectorThemeGroup,
  SectorThemePrimaryStatus,
} from './types';

type ClassifySectorThemeInput = {
  item: SectorThemeTestItem | null;
  period: TestHeatmapInterval;
  stored: {
    id: string;
    name: string;
    type: 'sector' | 'theme';
  };
};

export function classifySectorThemeItem({
  item,
  period,
  stored,
}: ClassifySectorThemeInput): SectorThemeClassification {
  if (!item || typeof item.returns[period] !== 'number') {
    return {
      dataStatus: 'unavailable',
      group: 'data_unavailable',
      id: stored.id,
      name: stored.name,
      period,
      primaryStatus: 'unavailable',
      reason: 'Saved item is no longer available in the sector/theme dataset.',
      returnPercent: null,
      score: null,
      type: stored.type,
    };
  }

  const dataStatus = getDataStatus(item);
  const returnPercent = item.returns[period];
  const momentumTrend = getRecentTrend(item, 'relativeMomentum');
  const breadthTrend = getBreadthTrend(item);
  const score = calculateSectorThemeScore(item, returnPercent, momentumTrend, breadthTrend);

  // Precedence: unavailable > weakening > leading > improving > watching.
  if (dataStatus === 'unavailable') {
    return buildClassification(item, period, 'data_unavailable', 'unavailable', 'Required data is unavailable.', null, dataStatus);
  }

  if (
    item.quadrant === 'lagging' ||
    item.quadrant === 'weakening' ||
    item.relativeMomentum < 98 ||
    (returnPercent < 0 && momentumTrend < 0) ||
    breadthTrend < -8
  ) {
    const status: SectorThemePrimaryStatus = item.quadrant === 'lagging' ? 'lagging' : 'weakening';
    return buildClassification(
      item,
      period,
      'weakening',
      status,
      getWeakeningReason(item, momentumTrend, breadthTrend),
      score,
      dataStatus,
    );
  }

  if (item.quadrant === 'leading' && item.relativeStrength >= 100 && item.relativeMomentum >= 100) {
    return buildClassification(
      item,
      period,
      'leading',
      'leading',
      'Strong relative performance and leadership.',
      score,
      dataStatus,
    );
  }

  if (item.quadrant === 'improving' || momentumTrend > 0.4 || breadthTrend > 6) {
    return buildClassification(
      item,
      period,
      'improving',
      'improving',
      getImprovingReason(item, momentumTrend, breadthTrend),
      score,
      dataStatus,
    );
  }

  return buildClassification(
    item,
    period,
    'watching',
    'neutral',
    'Saved group without a strong active leadership or risk signal.',
    score,
    dataStatus,
  );
}

export function getSectorThemeGroupLabel(group: SectorThemeGroup) {
  switch (group) {
    case 'leading':
      return 'Leading';
    case 'improving':
      return 'Improving';
    case 'watching':
      return 'Watching';
    case 'weakening':
      return 'Weakening';
    case 'data_unavailable':
      return 'Data Unavailable';
  }
}

export function getSectorThemeStatusLabel(status: SectorThemePrimaryStatus) {
  switch (status) {
    case 'leading':
      return 'Leading';
    case 'improving':
      return 'Improving';
    case 'neutral':
      return 'Neutral';
    case 'weakening':
      return 'Weakening';
    case 'lagging':
      return 'Lagging';
    case 'unavailable':
      return 'Unavailable';
  }
}

function buildClassification(
  item: SectorThemeTestItem,
  period: TestHeatmapInterval,
  group: SectorThemeGroup,
  primaryStatus: SectorThemePrimaryStatus,
  reason: string,
  score: number | null,
  dataStatus: SectorThemeDataStatus,
): SectorThemeClassification {
  return {
    dataStatus,
    group,
    id: item.id,
    name: item.name,
    period,
    primaryStatus,
    reason,
    returnPercent: item.returns[period],
    score,
    type: item.type,
  };
}

function calculateSectorThemeScore(
  item: SectorThemeTestItem,
  returnPercent: number,
  momentumTrend: number,
  breadthTrend: number,
) {
  const quadrantScore = item.quadrant === 'leading'
    ? 32
    : item.quadrant === 'improving'
      ? 24
      : item.quadrant === 'weakening'
        ? 8
        : 0;
  const strengthScore = clamp((item.relativeStrength - 96) * 5, 0, 28);
  const momentumScore = clamp((item.relativeMomentum - 96) * 5, 0, 24);
  const returnScore = clamp(returnPercent * 2, -18, 18);
  const breadthScore = clamp(breadthTrend * 1.5, -12, 12);
  const trendScore = clamp(momentumTrend * 4, -10, 10);
  return Math.round(clamp(quadrantScore + strengthScore + momentumScore + returnScore + breadthScore + trendScore, -100, 100));
}

function getDataStatus(item: SectorThemeTestItem): SectorThemeDataStatus {
  if (item.source === 'test') {
    return 'test';
  }
  return 'cached';
}

function getWeakeningReason(item: SectorThemeTestItem, momentumTrend: number, breadthTrend: number) {
  if (item.quadrant === 'lagging') {
    return 'Relative strength and momentum are lagging.';
  }
  if (item.quadrant === 'weakening') {
    return 'Leadership remains vulnerable as relative momentum weakens.';
  }
  if (breadthTrend < -8) {
    return 'Breadth participation is deteriorating.';
  }
  if (momentumTrend < 0) {
    return 'Relative momentum is deteriorating.';
  }
  return 'Leadership or momentum is deteriorating.';
}

function getImprovingReason(item: SectorThemeTestItem, momentumTrend: number, breadthTrend: number) {
  if (item.quadrant === 'improving') {
    return 'Rotation is moving through the improving quadrant.';
  }
  if (breadthTrend > 6) {
    return 'Breadth participation is strengthening.';
  }
  if (momentumTrend > 0) {
    return 'Relative momentum is strengthening.';
  }
  return 'Momentum or participation is strengthening.';
}

function getRecentTrend(item: SectorThemeTestItem, key: 'relativeMomentum' | 'relativeStrength') {
  const history = item.rotation['1M'].history;
  if (history.length < 3) {
    return 0;
  }
  return history.at(-1)![key] - history.at(-3)![key];
}

function getBreadthTrend(item: SectorThemeTestItem) {
  const history = item.breadthHistory['1M'];
  if (history.length < 5) {
    return 0;
  }
  return history.at(-1)!.percentAbove20Ema - history.at(-5)!.percentAbove20Ema;
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}
