from __future__ import annotations

import os
import threading
import time
from datetime import datetime, timezone
from typing import Any

from app.breadth.builder import BreadthSnapshotBuilder, breadth_namespace
from app.breadth.models import BreadthSnapshot
from app.breadth.storage import BreadthSnapshotStorage


class BreadthSnapshotService:
    def __init__(self, storage: BreadthSnapshotStorage | None = None, builder: BreadthSnapshotBuilder | None = None) -> None:
        self.storage = storage or BreadthSnapshotStorage()
        self.builder = builder or BreadthSnapshotBuilder(storage=self.storage)
        self._lock = threading.RLock(); self._stop = threading.Event(); self._thread: threading.Thread | None = None; self._build_thread: threading.Thread | None = None
        self.provider_calls = 0; self.last_error: str | None = None

    def initialize(self) -> None: self.storage.initialize()
    def universe_name(self) -> str: return os.getenv("BREADTH_UNIVERSE", "sp100").lower()
    def latest(self) -> BreadthSnapshot | None:
        universe = self.builder.security_master.storage.get_active_universe(self.universe_name())
        return self.storage.latest(universe.universe_id, breadth_namespace()) if universe else None
    def get(self, snapshot_id: str) -> BreadthSnapshot | None: return self.storage.get(snapshot_id)
    def trigger_refresh(self) -> bool:
        if os.getenv("BREADTH_ENABLED", "true").lower() not in {"1", "true", "yes", "on"}: return False
        with self._lock:
            if self._build_thread and self._build_thread.is_alive(): return False
            self._build_thread = threading.Thread(target=self.build_now, name="breadth-snapshot-build", daemon=True); self._build_thread.start(); return True
    def build_now(self) -> BreadthSnapshot | None:
        try: return self.builder.build_and_publish(self.universe_name())
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"; return self.latest()
    def start_background_refresh(self) -> None:
        if self._thread and self._thread.is_alive(): return
        self._stop.clear(); self._thread = threading.Thread(target=self._loop, name="breadth-snapshot-refresh", daemon=True); self._thread.start()
    def stop_background_refresh(self) -> None: self._stop.set()
    def shutdown(self, wait: bool = True) -> None:
        self.stop_background_refresh()
        if wait:
            for thread in (self._thread, self._build_thread):
                if thread and thread.is_alive(): thread.join(timeout=5)
    def status(self) -> dict[str, Any]:
        universe = self.builder.security_master.storage.get_active_universe(self.universe_name())
        snapshot = self.latest()
        members = self.builder.security_master.storage.members(universe.universe_id) if universe else []
        bar_status = self.builder.bars.status([member.ticker for member in members])
        return {"configured_universe": self.universe_name(), "universe_id": universe.universe_id if universe else None, "universe_version": universe.version if universe else None, "seed_status": bar_status, "latest_breadth_snapshot": snapshot.snapshot_id if snapshot else None, "snapshot_status": snapshot.status if snapshot else "unavailable", "coverage": snapshot.coverage if snapshot else None, "current_build": bool(self._build_thread and self._build_thread.is_alive()), "last_error": self.last_error, "provider_call_count": self.provider_calls, "next_refresh_seconds": int(os.getenv("BREADTH_REFRESH_INTERVAL_SECONDS", "900"))}
    def _loop(self) -> None:
        delay = float(os.getenv("BREADTH_STARTUP_DELAY_SECONDS", "15"))
        if os.getenv("BREADTH_STARTUP_REFRESH", "true").lower() in {"1", "true", "yes", "on"} and not self._stop.wait(delay): self.trigger_refresh()
        interval = max(60, int(os.getenv("BREADTH_REFRESH_INTERVAL_SECONDS", "900")))
        while not self._stop.wait(interval): self.trigger_refresh()


_service_lock = threading.RLock(); _service: BreadthSnapshotService | None = None
def get_breadth_snapshot_service() -> BreadthSnapshotService:
    global _service
    with _service_lock:
        if _service is None: _service = BreadthSnapshotService(); _service.initialize()
        return _service
def reset_breadth_snapshot_service() -> None:
    global _service
    with _service_lock:
        if _service: _service.shutdown()
        _service = None
