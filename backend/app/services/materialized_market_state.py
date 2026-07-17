from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Any

from app.cache.persistent_cache import get_persistent_value, set_persistent_value

STATE_KEY = "materialized:market-state"
STATE_TTL_SECONDS = 60 * 60
STATE_STALE_SECONDS = 24 * 60 * 60

_lock = threading.RLock()
_state: dict[str, Any] | None = None


def get_materialized_market_state() -> dict[str, Any]:
    global _state
    with _lock:
        if _state is not None:
            return dict(_state)

    cached = get_persistent_value(STATE_KEY, allow_stale=True)
    if cached is not None and isinstance(cached.value, dict):
        with _lock:
            _state = cached.value
            return dict(_state)

    state = empty_state()
    with _lock:
        _state = state
    return dict(state)


def update_market_state_component(
    name: str,
    value: Any,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    global _state
    with _lock:
        state = dict(_state or get_materialized_market_state())
        state[name] = value
        component_ages = dict(state.get("component_ages") or {})
        component_ages[name] = 0
        state["component_ages"] = component_ages
        state["component_metadata"] = {
            **(state.get("component_metadata") or {}),
            name: {
                **(metadata or {}),
                "updated_at": now_iso(),
            },
        }
        state["generated_at"] = now_iso()
        state["overall_mode"] = calculate_overall_mode(state)
        _state = state
        persist_state(state)
        return dict(state)


def persist_state(state: dict[str, Any]) -> None:
    set_persistent_value(
        STATE_KEY,
        state,
        ttl_seconds=STATE_TTL_SECONDS,
        stale_seconds=STATE_STALE_SECONDS,
        data_source=state.get("overall_mode"),
        metadata={"materialized": True},
    )


def empty_state() -> dict[str, Any]:
    return {
        "indexes": None,
        "watchlist_quotes": None,
        "sector_etfs": None,
        "breadth_summary": None,
        "sector_summary": None,
        "industry_group_summary": None,
        "leadership_summary": None,
        "sentiment_summary": None,
        "options_summary": None,
        "liquidity_summary": None,
        "institutional_summary": None,
        "generated_at": now_iso(),
        "component_ages": {},
        "component_metadata": {},
        "stale_components": [],
        "overall_mode": "stale",
    }


def get_materialized_state_status() -> dict[str, Any]:
    state = get_materialized_market_state()
    generated_at = state.get("generated_at")
    return {
        "available": bool(state),
        "generated_at": generated_at,
        "overall_mode": state.get("overall_mode"),
        "components": sorted(key for key, value in state.items() if key.endswith("_summary") and value is not None),
    }


def calculate_overall_mode(state: dict[str, Any]) -> str:
    metadata = state.get("component_metadata") or {}
    modes = {
        item.get("overall_mode") or item.get("source")
        for item in metadata.values()
        if isinstance(item, dict)
    }
    if "live" in modes and len(modes) == 1:
        return "live"
    if modes:
        return "mixed"
    return "stale"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
