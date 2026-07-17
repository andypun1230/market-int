import {
  generateSectorTabTestData,
  type SectorTabTestData,
} from '@/data/sectorTabTestData';
import type { SectorThemeRepository } from '@/features/sectors/types';

export function createTestSectorThemeRepository(seed: string): SectorThemeRepository {
  const data = generateSectorTabTestData(seed);
  return createRepositoryFromTestData(data);
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
