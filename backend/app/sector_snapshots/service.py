from __future__ import annotations

import os
import threading
from typing import Any

from app.sector_snapshots.builder import SectorSnapshotBuilder, sector_namespace
from app.sector_snapshots.models import SectorSnapshot
from app.sector_snapshots.storage import SectorSnapshotStorage


class SectorSnapshotService:
    def __init__(self, storage: SectorSnapshotStorage | None = None) -> None:
        self.storage = storage or SectorSnapshotStorage()
        self.builder = SectorSnapshotBuilder(storage=self.storage)
        self._lock = threading.Lock()

    def latest(self, universe_name: str = "sp100") -> SectorSnapshot | None:
        universe = self.builder.security_master.storage.get_active_universe(universe_name)
        return self.storage.latest(universe.universe_id, sector_namespace()) if universe else None

    def history(self, days: int = 90, universe_name: str = "sp100") -> list[dict[str, Any]]:
        universe = self.builder.security_master.storage.get_active_universe(universe_name)
        return self.storage.history(universe.universe_id, days) if universe else []

    def build_now(self, universe_name: str = "sp100", *, publish: bool = True) -> SectorSnapshot | None:
        if not self._lock.acquire(blocking=False): return self.latest(universe_name)
        try: return self.builder.build(universe_name, publish=publish)
        finally: self._lock.release()


_service: SectorSnapshotService | None = None
_service_lock = threading.RLock()

def get_sector_snapshot_service() -> SectorSnapshotService:
    global _service
    with _service_lock:
        if _service is None: _service = SectorSnapshotService()
        return _service

def reset_sector_snapshot_service() -> None:
    global _service
    with _service_lock: _service = None
