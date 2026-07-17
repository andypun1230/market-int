from __future__ import annotations

import os
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from app.providers.symbols import normalize_market_symbol
from app.stock_snapshots.builder import StockAnalysisSnapshotBuilder
from app.stock_snapshots.models import StockAnalysisSnapshot
from app.stock_snapshots.readers import aggregate_payload, initializing_payload, is_expired, status_payload
from app.stock_snapshots.storage import StockSnapshotStorage


class StockSnapshotService:
    def __init__(self, storage: StockSnapshotStorage | None = None) -> None:
        self.storage = storage or StockSnapshotStorage()
        self.builder = StockAnalysisSnapshotBuilder(self.storage)
        self._lock = threading.RLock()
        self._building: set[str] = set()
        self._executor = ThreadPoolExecutor(max_workers=max(1, int_env("STOCK_SNAPSHOT_MAX_CONCURRENT_BUILDS", 2)), thread_name_prefix="stock-snapshot")
        self._metrics = {
            "reads": 0,
            "builds_started": 0,
            "builds_completed": 0,
            "builds_failed": 0,
            "background_refreshes_triggered": 0,
            "deduped_refreshes": 0,
        }

    def initialize(self) -> None:
        self.storage.initialize()

    def get_snapshot(self, snapshot_id: str) -> StockAnalysisSnapshot | None:
        self._metrics["reads"] += 1
        return self.storage.get_snapshot(snapshot_id)

    def get_latest_snapshot(self, symbol: str) -> StockAnalysisSnapshot | None:
        normalized = normalize_market_symbol(symbol, apply_alias=True)
        self._metrics["reads"] += 1
        return self.storage.get_latest_snapshot(normalized) or self.storage.get_last_successful_snapshot(normalized)

    def get_analysis_payload(self, symbol: str) -> dict[str, Any]:
        normalized = normalize_market_symbol(symbol, apply_alias=True)
        snapshot = self.get_latest_snapshot(normalized)
        if snapshot is None:
            refresh_started = self.trigger_background_refresh(normalized)
            return initializing_payload(normalized, refresh_started=refresh_started or self.is_refreshing(normalized))
        if is_expired(snapshot):
            self.trigger_background_refresh(normalized)
        payload = aggregate_payload(snapshot)
        payload["snapshot_refreshing"] = self.is_refreshing(normalized)
        return payload

    def trigger_background_refresh(self, symbol: str) -> bool:
        if not bool_env("STOCK_SNAPSHOT_ENABLED", True):
            return False
        normalized = normalize_market_symbol(symbol, apply_alias=True)
        with self._lock:
            if normalized in self._building:
                self._metrics["deduped_refreshes"] += 1
                return False
            self._building.add(normalized)
            self._metrics["background_refreshes_triggered"] += 1
        self._executor.submit(self._build_symbol, normalized)
        return True

    def build_now(self, symbol: str) -> StockAnalysisSnapshot | None:
        normalized = normalize_market_symbol(symbol, apply_alias=True)
        with self._lock:
            if normalized in self._building:
                return None
            self._building.add(normalized)
        try:
            return self._build_symbol(normalized)
        finally:
            pass

    def is_refreshing(self, symbol: str) -> bool:
        normalized = normalize_market_symbol(symbol, apply_alias=True)
        with self._lock:
            return normalized in self._building

    def get_status(self, symbol: str) -> dict[str, Any]:
        normalized = normalize_market_symbol(symbol, apply_alias=True)
        snapshot = self.get_latest_snapshot(normalized)
        payload = status_payload(snapshot, refresh_in_progress=self.is_refreshing(normalized), enabled=bool_env("STOCK_SNAPSHOT_ENABLED", True))
        payload["metrics"] = dict(self._metrics)
        payload["storage"] = self.storage.status(normalized)
        return payload

    def clear_symbol(self, symbol: str) -> dict[str, int]:
        normalized = normalize_market_symbol(symbol, apply_alias=True)
        return self.storage.clear_symbol(normalized)

    def clear_all(self) -> dict[str, int]:
        return self.storage.clear_all()

    def clear_incompatible(self) -> dict[str, int]:
        return self.storage.clear_incompatible()

    def clear_namespace(self, namespace: str) -> dict[str, int]:
        return self.storage.clear_namespace(namespace)

    def shutdown(self, *, wait: bool = True) -> None:
        self._executor.shutdown(wait=wait, cancel_futures=True)

    def _build_symbol(self, symbol: str) -> StockAnalysisSnapshot | None:
        self._metrics["builds_started"] += 1
        try:
            snapshot = self.builder.build_and_publish(symbol)
            if snapshot is None:
                self._metrics["builds_failed"] += 1
            else:
                self._metrics["builds_completed"] += 1
            return snapshot
        finally:
            with self._lock:
                self._building.discard(symbol)


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


_service_lock = threading.RLock()
_service: StockSnapshotService | None = None


def get_stock_snapshot_service() -> StockSnapshotService:
    global _service
    with _service_lock:
        if _service is None:
            _service = StockSnapshotService()
            _service.initialize()
        return _service


def reset_stock_snapshot_service() -> None:
    global _service
    with _service_lock:
        if _service is not None:
            _service.shutdown(wait=True)
        _service = None
