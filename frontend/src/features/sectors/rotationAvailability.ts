import { CANONICAL_SECTOR_IDS, type SectorId, type SectorRotationInterval, type SectorRotationModel } from './sectorSnapshot';

export type RotationChartSector = {
  displayName: string;
  etfSymbol: string;
  rank: number;
  sectorId: SectorId;
};

export function buildRotationChartSectors(
  rotation: SectorRotationModel | null,
  interval: SectorRotationInterval,
  ranks: Map<SectorId, number>,
): RotationChartSector[] {
  if (!rotation) {
    return [];
  }
  return CANONICAL_SECTOR_IDS.flatMap((sectorId) => {
    const series = rotation.seriesBySector.get(sectorId)?.[interval];
    if (!series?.currentPoint) {
      return [];
    }
    return [{
      displayName: series.displayName,
      etfSymbol: series.shortLabel,
      rank: ranks.get(sectorId) ?? 999,
      sectorId,
    }];
  });
}

export function rotationRenderState(
  rotation: SectorRotationModel | null,
  interval: SectorRotationInterval,
): 'ready' | 'unavailable' {
  const items = buildRotationChartSectors(rotation, interval, new Map());
  return items.length ? 'ready' : 'unavailable';
}
