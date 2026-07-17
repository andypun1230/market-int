from __future__ import annotations

import os
import random
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable

from app.providers.finnhub_provider import ProviderRequestError


RETRYABLE_CATEGORIES = {
    "network",
    "rate_limit",
    "rate_limited",
    "provider_5xx",
    "server_error",
    "timeout",
    "unavailable",
}


@dataclass
class CoordinatedRequest:
    event: threading.Event
    result: Any = None
    error: BaseException | None = None
    waiter_count: int = 0


class HistoryRequestCoordinator:
    """Process-wide guard for live history fetches.

    The repository has a per-instance in-flight map. This coordinator adds the
    missing cross-instance layer plus a global concurrency cap so a cold app
    start cannot fan out dozens of Polygon history calls at once.
    """

    def __init__(
        self,
        *,
        max_concurrency: int | None = None,
        max_retries: int | None = None,
        max_queue_wait_seconds: float | None = None,
        base_backoff_seconds: float | None = None,
    ) -> None:
        self.max_concurrency = max(1, max_concurrency if max_concurrency is not None else env_int("MARKET_DATA_HISTORY_COORDINATOR_CONCURRENCY", 2))
        self.max_retries = max(0, max_retries if max_retries is not None else env_int("MARKET_DATA_HISTORY_COORDINATOR_RETRIES", 2))
        self.max_queue_wait_seconds = max(
            0.1,
            max_queue_wait_seconds
            if max_queue_wait_seconds is not None
            else env_float("MARKET_DATA_HISTORY_COORDINATOR_MAX_QUEUE_WAIT_SECONDS", 20.0),
        )
        self.base_backoff_seconds = max(
            0.01,
            base_backoff_seconds
            if base_backoff_seconds is not None
            else env_float("MARKET_DATA_HISTORY_COORDINATOR_BACKOFF_SECONDS", 0.45),
        )
        self._semaphore = threading.BoundedSemaphore(self.max_concurrency)
        self._lock = threading.RLock()
        self._inflight: dict[str, CoordinatedRequest] = {}
        self._running = 0
        self._queued = 0
        self._metrics: dict[str, int] = {
            "started": 0,
            "succeeded": 0,
            "failed": 0,
            "deduplicated": 0,
            "retries": 0,
            "queue_timeouts": 0,
            "max_running": 0,
            "max_queue_depth": 0,
        }

    def run(self, key: str, request_fn: Callable[[], Any]) -> Any:
        existing, owner = self._get_or_create(key)
        if not owner:
            completed = existing.event.wait(timeout=self.max_queue_wait_seconds + 5)
            if not completed:
                raise ProviderRequestError("History coordinator in-flight wait timed out.", category="timeout")
            if existing.error is not None:
                raise existing.error
            return clone_value(existing.result)

        acquired = False
        try:
            self._note_queued(1)
            acquired = self._semaphore.acquire(timeout=self.max_queue_wait_seconds)
            self._note_queued(-1)
            if not acquired:
                error = ProviderRequestError("History coordinator queue wait timed out.", category="timeout")
                existing.error = error
                self._increment("queue_timeouts")
                raise error

            self._note_running(1)
            self._increment("started")
            result = self._run_with_retries(request_fn)
            existing.result = clone_value(result)
            self._increment("succeeded")
            return result
        except BaseException as exc:
            existing.error = exc
            self._increment("failed")
            raise
        finally:
            if acquired:
                self._note_running(-1)
                self._semaphore.release()
            existing.event.set()
            with self._lock:
                self._inflight.pop(key, None)

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "enabled": True,
                "max_concurrency": self.max_concurrency,
                "running": self._running,
                "queued": self._queued,
                "inflight_keys": len(self._inflight),
                **self._metrics,
            }

    def _get_or_create(self, key: str) -> tuple[CoordinatedRequest, bool]:
        with self._lock:
            existing = self._inflight.get(key)
            if existing is not None:
                existing.waiter_count += 1
                self._metrics["deduplicated"] += 1
                return existing, False
            created = CoordinatedRequest(event=threading.Event())
            self._inflight[key] = created
            return created, True

    def _run_with_retries(self, request_fn: Callable[[], Any]) -> Any:
        attempt = 0
        while True:
            try:
                return request_fn()
            except ProviderRequestError as exc:
                if attempt >= self.max_retries or not is_retryable_provider_error(exc):
                    raise
                self._increment("retries")
                time.sleep(self._retry_delay(attempt))
                attempt += 1

    def _retry_delay(self, attempt: int) -> float:
        jitter = random.uniform(0.05, 0.25)
        return min(4.0, self.base_backoff_seconds * (2 ** attempt) + jitter)

    def _increment(self, key: str) -> None:
        with self._lock:
            self._metrics[key] = self._metrics.get(key, 0) + 1

    def _note_queued(self, delta: int) -> None:
        with self._lock:
            self._queued = max(0, self._queued + delta)
            self._metrics["max_queue_depth"] = max(self._metrics["max_queue_depth"], self._queued)

    def _note_running(self, delta: int) -> None:
        with self._lock:
            self._running = max(0, self._running + delta)
            self._metrics["max_running"] = max(self._metrics["max_running"], self._running)


def is_retryable_provider_error(error: ProviderRequestError) -> bool:
    category = (error.category or "").lower()
    return category in RETRYABLE_CATEGORIES


def clone_value(value: Any) -> Any:
    if hasattr(value, "model_copy"):
        return value.model_copy(deep=True)
    return value


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


_coordinator_lock = threading.RLock()
_coordinator: HistoryRequestCoordinator | None = None


def get_history_request_coordinator() -> HistoryRequestCoordinator:
    global _coordinator
    with _coordinator_lock:
        signature = coordinator_signature()
        if _coordinator is None or getattr(_coordinator, "_signature", None) != signature:
            _coordinator = HistoryRequestCoordinator()
            setattr(_coordinator, "_signature", signature)
        return _coordinator


def reset_history_request_coordinator() -> None:
    global _coordinator
    with _coordinator_lock:
        _coordinator = None


def coordinator_signature() -> tuple[str | None, ...]:
    return (
        os.getenv("MARKET_DATA_HISTORY_COORDINATOR_CONCURRENCY"),
        os.getenv("MARKET_DATA_HISTORY_COORDINATOR_RETRIES"),
        os.getenv("MARKET_DATA_HISTORY_COORDINATOR_MAX_QUEUE_WAIT_SECONDS"),
        os.getenv("MARKET_DATA_HISTORY_COORDINATOR_BACKOFF_SECONDS"),
    )
