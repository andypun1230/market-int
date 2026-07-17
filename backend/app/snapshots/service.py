from __future__ import annotations

import os
import threading
import time
from datetime import datetime, timezone
from typing import Any

from app.snapshots.builder import MarketSnapshotBuilder
from app.snapshots.models import MarketSnapshot
from app.snapshots.storage import MarketSnapshotStorage


class MarketSnapshotService:
    def __init__(self, storage: MarketSnapshotStorage | None = None) -> None:
        self.storage = storage or MarketSnapshotStorage()
        self.builder = MarketSnapshotBuilder(self.storage)
        self._refresh_lock = threading.RLock()
        self._refresh_thread: threading.Thread | None = None
        self._startup_thread: threading.Thread | None = None
        self._build_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._metrics = {
            "builds_started": 0,
            "builds_completed": 0,
            "builds_failed": 0,
            "background_refreshes_triggered": 0,
            "read_count": 0,
        }

    def initialize(self) -> None:
        self.storage.initialize()

    def start_background_refresh(self) -> None:
        if not bool_env("MARKET_SNAPSHOT_ENABLED", True):
            return
        with self._refresh_lock:
            if self._refresh_thread is not None and self._refresh_thread.is_alive():
                return
            self._stop_event.clear()
            self._refresh_thread = threading.Thread(target=self._refresh_loop, name="market-snapshot-refresh", daemon=True)
            self._refresh_thread.start()
            if bool_env("MARKET_SNAPSHOT_STARTUP_REFRESH", True):
                delay = float_env("MARKET_SNAPSHOT_STARTUP_DELAY_SECONDS", 2.0)
                self._startup_thread = threading.Thread(target=self._delayed_refresh, args=(delay,), name="market-snapshot-startup", daemon=True)
                self._startup_thread.start()

    def stop_background_refresh(self) -> None:
        self._stop_event.set()

    def shutdown(self, *, wait: bool = True, timeout_seconds: float = 5.0) -> None:
        self.stop_background_refresh()
        if not wait:
            return
        deadline = time.monotonic() + max(0.0, timeout_seconds)
        for thread in [self._refresh_thread, self._startup_thread, self._build_thread]:
            if thread is not None and thread.is_alive():
                thread.join(timeout=max(0.0, deadline - time.monotonic()))

    def get_latest_snapshot(self) -> MarketSnapshot | None:
        self._metrics["read_count"] += 1
        return self.storage.get_latest_snapshot() or self.storage.get_last_successful_snapshot()

    def get_snapshot(self, snapshot_id: str) -> MarketSnapshot | None:
        self._metrics["read_count"] += 1
        return self.storage.get_snapshot(snapshot_id)

    def trigger_background_refresh(self) -> bool:
        if not bool_env("MARKET_SNAPSHOT_ENABLED", True):
            return False
        with self._refresh_lock:
            name = "market-snapshot-build"
            if self._build_thread is not None and self._build_thread.is_alive():
                return False
            thread = threading.Thread(target=self.build_now, name=name, daemon=True)
            self._build_thread = thread
            thread.start()
            self._metrics["background_refreshes_triggered"] += 1
            return True

    def build_now(self) -> MarketSnapshot | None:
        self._metrics["builds_started"] += 1
        snapshot = self.builder.build_and_publish()
        if snapshot is None:
            self._metrics["builds_failed"] += 1
        else:
            self._metrics["builds_completed"] += 1
        return snapshot

    def get_status(self) -> dict[str, Any]:
        latest = self.get_latest_snapshot()
        state = self.storage.status()
        return {
            "enabled": bool_env("MARKET_SNAPSHOT_ENABLED", True),
            "latest_snapshot_id": latest.snapshot_id if latest else None,
            "latest_status": latest.status if latest else "unavailable",
            "snapshot_age_seconds": snapshot_age_seconds(latest) if latest else None,
            "refresh_in_progress": any(thread.name == "market-snapshot-build" and thread.is_alive() for thread in threading.enumerate()),
            "metrics": dict(self._metrics),
            "storage": state,
        }

    def _refresh_loop(self) -> None:
        interval = int_env("MARKET_SNAPSHOT_REFRESH_INTERVAL_SECONDS", 300)
        while not self._stop_event.wait(interval):
            latest = self.get_latest_snapshot()
            max_age = int_env("MARKET_SNAPSHOT_MAX_AGE_SECONDS", 600)
            if latest is None or (snapshot_age_seconds(latest) or 0) >= max_age:
                self.trigger_background_refresh()

    def _delayed_refresh(self, delay: float) -> None:
        if self._stop_event.wait(max(0.0, delay)):
            return
        self.trigger_background_refresh()


def snapshot_age_seconds(snapshot: MarketSnapshot | None) -> float | None:
    if snapshot is None:
        return None
    try:
        published = datetime.fromisoformat(snapshot.published_at.replace("Z", "+00:00"))
    except ValueError:
        return None
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)
    return round((datetime.now(timezone.utc) - published).total_seconds(), 2)


def bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


_service_lock = threading.RLock()
_service: MarketSnapshotService | None = None


def get_market_snapshot_service() -> MarketSnapshotService:
    global _service
    with _service_lock:
        if _service is None:
            _service = MarketSnapshotService()
            _service.initialize()
        return _service


def reset_market_snapshot_service() -> None:
    global _service
    with _service_lock:
        if _service is not None:
            _service.shutdown(wait=True)
        _service = None
