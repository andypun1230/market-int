import { useCallback } from 'react';
import { getSectorDetail, getSectorRotation, getSectorSnapshot } from '@/services/api';
import { adaptSectorDetail, adaptSectorRotation, adaptSectorSnapshot, type SectorDetailModel, type SectorRotationModel, type SectorSnapshotModel } from '@/features/sectors/sectorSnapshot';
import { useAsyncData } from './useAsyncData';

export function useSectorSnapshot(enabled = true) {
  const fetchSnapshot = useCallback(async () => adaptSectorSnapshot(await getSectorSnapshot()), []);
  const result = useAsyncData(fetchSnapshot, { enabled });
  return { ...result, snapshot: result.data as SectorSnapshotModel | null };
}
export function useSectorDetail(sectorId: string | null, enabled = true) {
  const fetchDetail = useCallback(async () => sectorId ? adaptSectorDetail(await getSectorDetail(sectorId)) : null, [sectorId]);
  const result = useAsyncData(fetchDetail, { enabled: enabled && Boolean(sectorId) });
  return { ...result, detail: result.data as SectorDetailModel | null };
}
export function useSectorRotationTrails(enabled = true) {
  const fetchHistory = useCallback(async () => adaptSectorRotation(await getSectorRotation()), []);
  const result = useAsyncData(fetchHistory, { enabled });
  return { ...result, rotation: result.data as SectorRotationModel | null };
}
