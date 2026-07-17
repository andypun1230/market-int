from __future__ import annotations

import threading
import time
from typing import Any

_lock = threading.RLock()
_state: dict[str, dict[str, Any]] = {}

FAILURE_THRESHOLD = 3
OPEN_SECONDS = 5 * 60


def is_circuit_open(provider: str) -> bool:
    with _lock:
        entry = _state.get(provider, {})
        open_until = entry.get("open_until") or 0
        if open_until > time.time():
            return True
        if open_until:
            entry["open_until"] = 0
            entry["half_open"] = True
        return False


def record_provider_success(provider: str) -> None:
    with _lock:
        _state[provider] = {
            **_state.get(provider, {}),
            "failure_count": 0,
            "consecutive_timeouts": 0,
            "open_until": 0,
            "last_error": None,
            "last_success": time.time(),
            "half_open": False,
        }


def record_provider_failure(provider: str, error: Exception | str) -> None:
    with _lock:
        entry = dict(_state.get(provider, {}))
        failure_count = int(entry.get("failure_count") or 0) + 1
        entry["failure_count"] = failure_count
        entry["last_error"] = str(error)
        entry["last_failure"] = time.time()
        if failure_count >= FAILURE_THRESHOLD:
            entry["open_until"] = time.time() + OPEN_SECONDS
            entry["half_open"] = False
        _state[provider] = entry


def get_circuit_breaker_status() -> dict[str, Any]:
    now = time.time()
    with _lock:
        return {
            provider: {
                **entry,
                "open": (entry.get("open_until") or 0) > now,
                "opens_in_seconds": max(0, round((entry.get("open_until") or 0) - now, 2)),
            }
            for provider, entry in sorted(_state.items())
        }
