import { useCallback } from "react";
import {
  getSectorDetail,
  getSectorRotation,
  getSectorSnapshot,
} from "@/services/api";
import {
  adaptSectorDetail,
  adaptSectorRotation,
  adaptSectorSnapshot,
  SECTOR_ROTATION_MODEL_VERSION,
  type SectorDetailModel,
  type SectorRotationInterval,
  type SectorRotationModel,
  type SectorSnapshotModel,
} from "@/features/sectors/sectorSnapshot";
import { useAsyncData } from "./useAsyncData";

export function useSectorSnapshot(enabled = true) {
  const fetchSnapshot = useCallback(
    async () => adaptSectorSnapshot(await getSectorSnapshot()),
    [],
  );
  const result = useAsyncData(fetchSnapshot, { enabled });
  return { ...result, snapshot: result.data as SectorSnapshotModel | null };
}
export function useSectorDetail(sectorId: string | null, enabled = true) {
  const fetchDetail = useCallback(
    async () =>
      sectorId ? adaptSectorDetail(await getSectorDetail(sectorId)) : null,
    [sectorId],
  );
  const result = useAsyncData(fetchDetail, {
    enabled: enabled && Boolean(sectorId),
  });
  return { ...result, detail: result.data as SectorDetailModel | null };
}
export function useSectorRotationTrails(
  timeframe: SectorRotationInterval,
  snapshot: SectorSnapshotModel | null,
  enabled = true,
) {
  const snapshotId = snapshot?.snapshotId ?? "";
  const universeVersion = snapshot?.universeVersion ?? "";
  const fetchHistory = useCallback(async () => {
    if (!snapshotId || !universeVersion) return null;
    return adaptSectorRotation(
      await getSectorRotation(timeframe, { snapshotId, universeVersion }),
    );
  }, [snapshotId, timeframe, universeVersion]);
  const result = useAsyncData(fetchHistory, {
    enabled: enabled && Boolean(snapshotId && universeVersion),
  });
  const current =
    result.data?.snapshotId === snapshotId &&
    result.data?.universeVersion === universeVersion &&
    result.data?.timeframe === timeframe &&
    result.data?.modelVersion === SECTOR_ROTATION_MODEL_VERSION
      ? (result.data as SectorRotationModel)
      : null;
  const waitingForCurrentIdentity =
    enabled &&
    Boolean(snapshotId && universeVersion) &&
    current === null &&
    result.error === null;
  return {
    ...result,
    data: current,
    loading: result.loading || waitingForCurrentIdentity,
    rotation: current,
  };
}
