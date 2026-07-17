import time
from typing import Any

_CACHE: dict[str, dict[str, Any]] = {}


def get_cached_ai_summary(key: str) -> dict[str, Any] | None:
    item = _CACHE.get(key)
    if not item:
        return None

    if item["expires_at"] <= time.time():
        _CACHE.pop(key, None)
        return None

    return item["value"]


def set_cached_ai_summary(
    key: str,
    value: dict[str, Any],
    ttl_seconds: int = 600,
) -> None:
    _CACHE[key] = {
        "expires_at": time.time() + ttl_seconds,
        "value": value.copy(),
    }


def clear_ai_cache() -> None:
    _CACHE.clear()


def get_ai_cache_status() -> dict[str, Any]:
    now = time.time()
    expired_keys = [
        key for key, item in _CACHE.items() if item["expires_at"] <= now
    ]

    for key in expired_keys:
        _CACHE.pop(key, None)

    return {
        "items": len(_CACHE),
        "keys": sorted(_CACHE.keys()),
    }
