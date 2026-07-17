from threading import Lock
from time import time
from typing import Any

from app.cache.persistent_cache import (
    delete_persistent_prefix,
    get_persistent_cache_status,
    get_persistent_value,
    set_persistent_value,
)
from app.providers.models import HistoryData, QuoteData

_cache: dict[str, tuple[float, Any]] = {}
_lock = Lock()


def get_cached_value(key: str) -> Any | None:
    now = time()
    with _lock:
        cached = _cache.get(key)
        if cached is not None:
            expires_at, value = cached
            if expires_at > now:
                if not is_cached_value_compatible(key, value):
                    _cache.pop(key, None)
                else:
                    return value
            else:
                _cache.pop(key, None)

    persistent = get_persistent_provider_value(key, allow_stale=False)
    if persistent is not None:
        ttl = max(1, int(persistent.expires_in_seconds))
        set_cached_value(key, persistent.value, ttl)
        return persistent.value

    return None


def is_cached_value_compatible(key: str, value: Any) -> bool:
    if (key.startswith("history:") or ":history:" in key) and isinstance(value, HistoryData):
        return is_history_cache_compatible(key, value)
    return True


def get_stale_cached_value(key: str) -> Any | None:
    persistent = get_persistent_provider_value(key, allow_stale=True)
    if persistent is None:
        return None
    value = mark_stale(persistent.value)
    set_cached_value(key, value, 30)
    return value


def set_cached_value(key: str, value: Any, ttl_seconds: int) -> None:
    if not is_cached_value_compatible(key, value):
        return
    with _lock:
        _cache[key] = (time() + max(0, ttl_seconds), value)
    persist_provider_value(key, value, ttl_seconds)


def clear_provider_cache() -> None:
    with _lock:
        _cache.clear()
    delete_persistent_prefix("provider:")
    delete_persistent_prefix("quote:")
    delete_persistent_prefix("history:")


def get_provider_cache_status() -> dict[str, Any]:
    now = time()
    with _lock:
        expired_keys = [key for key, (expires_at, _) in _cache.items() if expires_at <= now]
        for key in expired_keys:
            _cache.pop(key, None)

        return {
            "items": len(_cache),
            "keys": sorted(_cache.keys()),
            "persistent": get_persistent_cache_status(),
        }


def get_persistent_provider_value(key: str, allow_stale: bool) -> Any | None:
    if not is_provider_quote_or_history_key(key):
        return None

    result = get_persistent_value(key, allow_stale=allow_stale)
    if result is None:
        return None
    value = deserialize_provider_value(key, result.value)
    if value is None:
        return None
    result.value = value
    return result


def persist_provider_value(key: str, value: Any, ttl_seconds: int) -> None:
    if not is_provider_quote_or_history_key(key):
        return

    stale_seconds = get_stale_seconds(key)
    source = getattr(value, "source", None)
    metadata = {
        "provider_cache": True,
        "source": source,
        "symbol": getattr(value, "symbol", None),
    }
    set_persistent_value(key, value, ttl_seconds, stale_seconds, data_source=source, metadata=metadata)
    provider_key = build_provider_key(key, value)
    if provider_key != key:
        set_persistent_value(provider_key, value, ttl_seconds, stale_seconds, data_source=source, metadata=metadata)


def is_provider_quote_or_history_key(key: str) -> bool:
    return key.startswith("quote:") or key.startswith("history:")


def deserialize_provider_value(key: str, value: Any) -> Any:
    try:
        if key.startswith("quote:") or ":quote:" in key:
            return QuoteData.model_validate(value)
        if key.startswith("history:") or ":history:" in key:
            history = HistoryData.model_validate(value)
            return history if is_history_cache_compatible(key, history) else None
    except Exception:
        return None
    return None


def is_history_cache_compatible(key: str, history: HistoryData) -> bool:
    requested_days = get_requested_days_from_history_key(key) or history.requested_days
    if not requested_days:
        return True
    returned_candles = history.returned_candles or len(history.candles)
    if requested_days >= 300:
        return returned_candles >= min(220, round(requested_days * 0.60))
    if requested_days >= 120:
        return returned_candles >= min(90, round(requested_days * 0.50))
    return returned_candles >= min(requested_days, len(history.candles))


def get_requested_days_from_history_key(key: str) -> int | None:
    parts = key.split(":")
    if key.startswith("history:") and len(parts) >= 4:
        candidate = parts[3]
    elif ":history:" in key and len(parts) >= 5:
        candidate = parts[4]
    else:
        return None
    try:
        return int(candidate)
    except ValueError:
        return None


def mark_stale(value: Any) -> Any:
    if hasattr(value, "model_copy"):
        return value.model_copy(update={"is_stale": True, "fallback_used": False})
    return value


def get_stale_seconds(key: str) -> int:
    if key.startswith("history:") or ":history:" in key:
        return 7 * 24 * 60 * 60
    return 15 * 60


def build_provider_key(key: str, value: Any) -> str:
    source = getattr(value, "source", None)
    symbol = getattr(value, "symbol", None)
    if not source or not symbol:
        return key
    if key.startswith("quote:"):
        return f"provider:quote:{source}:{symbol}"
    if key.startswith("history:"):
        parts = key.split(":")
        resolution = parts[2] if len(parts) > 2 else "D"
        days = parts[3] if len(parts) > 3 else ""
        return f"provider:history:{source}:{symbol}:{resolution}:{days}"
    return key
