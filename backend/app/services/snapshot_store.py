from __future__ import annotations

import os
from typing import Any

from app.cache.persistent_cache import PersistentCacheResult, get_persistent_value, set_persistent_value
from app.services.service_cache import get_service_ttl

MARKET_CORE_KEY = "snapshot:market-core"
HOME_DASHBOARD_KEY = "snapshot:home-dashboard"
SNAPSHOT_STALE_SECONDS = 24 * 60 * 60


def get_last_market_core_snapshot() -> PersistentCacheResult | None:
    return get_persistent_value(MARKET_CORE_KEY, allow_stale=True)


def save_market_core_snapshot(snapshot: dict[str, Any]) -> None:
    set_persistent_value(
        MARKET_CORE_KEY,
        snapshot,
        ttl_seconds=get_service_ttl("SERVICE_CACHE_MARKET_CORE_TTL_SECONDS", 60),
        stale_seconds=SNAPSHOT_STALE_SECONDS,
        data_source=snapshot.get("overall_mode"),
        metadata={"snapshot": "market-core"},
    )


def get_last_home_dashboard() -> PersistentCacheResult | None:
    return get_persistent_value(HOME_DASHBOARD_KEY, allow_stale=True)


def save_home_dashboard(snapshot: dict[str, Any]) -> None:
    set_persistent_value(
        HOME_DASHBOARD_KEY,
        snapshot,
        ttl_seconds=get_service_ttl("SERVICE_CACHE_MARKET_CORE_TTL_SECONDS", 60),
        stale_seconds=SNAPSHOT_STALE_SECONDS,
        data_source=(snapshot.get("core") or {}).get("overall_mode") if isinstance(snapshot.get("core"), dict) else None,
        metadata={"snapshot": "home-dashboard"},
    )


def get_snapshot_status() -> dict[str, Any]:
    return {
        "market_core_snapshot": summarize_snapshot(get_last_market_core_snapshot()),
        "home_dashboard": summarize_snapshot(get_last_home_dashboard()),
        "snapshot_stale_hours": round(SNAPSHOT_STALE_SECONDS / 3600),
        "background_enabled": os.getenv("BACKGROUND_REFRESH_ENABLED", "true").lower() != "false",
    }


def summarize_snapshot(result: PersistentCacheResult | None) -> dict[str, Any]:
    if result is None:
        return {"available": False, "age_seconds": None, "stale": None}
    return {
        "available": True,
        "age_seconds": round(result.age_seconds, 2),
        "stale": result.stale,
        "fresh": result.fresh,
        "expires_in_seconds": round(result.expires_in_seconds, 2),
    }
