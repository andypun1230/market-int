import {
  generateSectorTabTestData,
  type SectorTabTestData,
  type TestSectorItem,
} from '@/data/sectorTabTestData';
import type { SectorThemeRepository } from '@/features/sectors/types';
import type { SectorDashboardResponse } from '@/types/market';

export function createTestSectorThemeRepository(seed: string): SectorThemeRepository {
  const data = generateSectorTabTestData(seed);
  return createRepositoryFromTestData(data);
}

export function createLiveSectorThemeRepository(dashboard: SectorDashboardResponse | null): SectorThemeRepository {
  const sectors = (dashboard?.sectors ?? []).map((item): TestSectorItem => {
    const rotation = item.rotation.oneMonth;
    const relativeStrength = rotation?.relativeStrength ?? 50;
    const relativeMomentum = rotation?.relativeMomentum ?? 50;
    const metadata = item.metadata ?? {};
    const coverage = metadata.coverage_percent ?? 0;
    const advancing = metadata.successful_symbols ?? 0;
    const quadrant = rotation?.quadrant ?? 'lagging';
    return {
      id: item.id,
      name: item.name,
      type: 'sector',
      returns: { '1D': item.returns.oneDay ?? 0, '1W': item.returns.oneWeek ?? 0, '1M': item.returns.oneMonth ?? 0, '3M': item.returns.threeMonths ?? 0, '6M': item.returns.sixMonths ?? 0, '1Y': item.returns.oneYear ?? 0 },
      rotation: {
        '1W': toRotation(item.rotation.oneWeek, quadrant),
        '1M': toRotation(item.rotation.oneMonth, quadrant),
        '3M': toRotation(item.rotation.threeMonths, quadrant),
      },
      relativeStrength,
      relativeMomentum,
      quadrant,
      rotationHistory: [],
      breadth: { totalStocks: advancing, advancing: 0, declining: 0, unchanged: 0, advanceDeclineRatio: null, percentAbove20Ema: 0, percentAbove50Ema: 0, percentAbove200Ema: 0, newHighs: 0, newLows: 0, coveragePercent: coverage, participationLabel: coverage >= 95 ? 'Healthy' : 'Selective', source: 'test' },
      breadthHistory: { '1M': [], '3M': [], '6M': [] },
      constituents: [],
      source: 'test',
    };
  });
  return { getAllItems: () => sectors, getBenchmark: () => 'SPY', getSectorById: (id) => sectors.find((sector) => sector.id === id) ?? null, getSectors: () => sectors, getThemeById: () => null, getThemes: () => [] };
}

function toRotation(value: { relativeStrength: number | null; relativeMomentum: number | null; quadrant: 'leading' | 'weakening' | 'lagging' | 'improving' | null } | null | undefined, fallback: 'leading' | 'weakening' | 'lagging' | 'improving') {
  return { relativeStrength: value?.relativeStrength ?? 50, relativeMomentum: value?.relativeMomentum ?? 50, quadrant: value?.quadrant ?? fallback, history: [] };
}

function createRepositoryFromTestData(data: SectorTabTestData): SectorThemeRepository {
  return {
    getAllItems: () => [...data.sectors, ...data.themes],
    getBenchmark: () => data.benchmark,
    getSectorById: (id) => data.sectors.find((sector) => sector.id === id) ?? null,
    getSectors: () => data.sectors,
    getThemeById: (id) => data.themes.find((theme) => theme.id === id) ?? null,
    getThemes: () => data.themes,
  };
}
