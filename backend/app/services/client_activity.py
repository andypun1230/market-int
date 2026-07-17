from __future__ import annotations

import threading
import time
from typing import Any

_lock = threading.RLock()
_last_access: dict[str, float] = {}


def record_client_activity(area: str) -> None:
    with _lock:
        _last_access[area] = time.time()


def was_recently_active(area: str, within_seconds: int = 600) -> bool:
    with _lock:
        last_access = _last_access.get(area)
    return last_access is not None and (time.time() - last_access) <= within_seconds


def any_recently_active(areas: list[str], within_seconds: int = 600) -> bool:
    return any(was_recently_active(area, within_seconds) for area in areas)


def get_client_activity_status() -> dict[str, Any]:
    now = time.time()
    with _lock:
        return {
            area: {
                "last_access_age_seconds": round(now - timestamp, 2),
                "active_10m": (now - timestamp) <= 600,
            }
            for area, timestamp in sorted(_last_access.items())
        }
