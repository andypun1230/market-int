import {
  getHeatmapValue,
  getRotationData,
  normalizeSectorDashboardResponse,
} from '../src/utils/sectorDashboardNormalizers';

function assert(condition: unknown, message: string) {
  if (!condition) {
    throw new Error(message);
  }
}

function run() {
  const normalized = normalizeSectorDashboardResponse({
    benchmark: 'SPY',
    source: 'cached',
    sectors: [
      {
        id: 'technology',
        name: 'Technology',
        returns: {
          '1d': 0,
          '1w': '1.25',
          '1m': { value: 3.5 },
          '3m': 5,
          '6m': null,
          '1y': 20,
        },
        rotation: {
          '1w': {
            relative_strength: 101,
            relative_momentum: 100.5,
          },
        },
      },
    ],
    industry_groups: [
      {
        name: 'Memory',
        parent_sector: 'Technology',
        return_1d: -0.5,
        return_1w: 2,
        return_1m: 4,
        return_3m: 8,
        return_6m: 12,
        return_1y: 30,
        relativeStrength: 103,
        relativeMomentum: 98,
      },
    ],
  });

  assert(normalized.benchmark === 'SPY', 'keeps benchmark');
  assert(normalized.sectors.length === 1, 'normalizes sectors');
  assert(normalized.themes.length === 1, 'maps industry groups to themes');
  assert(getHeatmapValue(normalized.sectors[0], '1D') === 0, 'preserves zero returns');
  assert(getHeatmapValue(normalized.sectors[0], '1W') === 1.25, 'parses numeric return strings');
  assert(getHeatmapValue(normalized.sectors[0], '1M') === 3.5, 'parses object wrapped returns');
  assert(getHeatmapValue(normalized.sectors[0], '6M') === null, 'keeps missing intervals nullable');
  assert(getRotationData(normalized.sectors[0], '1W')?.quadrant === 'leading', 'classifies leading quadrant');
  assert(getRotationData(normalized.themes[0], '1W')?.relativeStrength === 103, 'extracts camelCase theme RS');
  assert(getRotationData(normalized.themes[0], '1W')?.quadrant === 'weakening', 'classifies weakening quadrant');

  const partial = normalizeSectorDashboardResponse({
    payload: {
      sectorPerformance: [],
      themePerformance: [],
      source: 'mock',
      partial: true,
    },
  });
  assert(partial.source === 'mock', 'supports nested payload source');
  assert(partial.partial === true, 'preserves partial flag');
}

run();
