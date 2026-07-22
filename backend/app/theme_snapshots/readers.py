from __future__ import annotations

from typing import Any

from app.theme_snapshots.models import ThemeSnapshot


def unavailable_theme_payload(reason: str = "Live Theme Intelligence is not yet available.") -> dict[str, Any]:
    return {"status": "unavailable", "source_state": "unavailable", "snapshot_id": None, "market_date": None, "items": [], "rows": [], "rankings": [], "warnings": [reason], "historical_disclosure": "Historical results use the current reviewed constituent basket unless historical membership versions are available."}


def snapshot_payload(snapshot: ThemeSnapshot | None) -> dict[str, Any]:
    if snapshot is None: return unavailable_theme_payload()
    value = snapshot.model_dump(); value["items"] = list(snapshot.rows); value["historical_disclosure"] = "Historical results use the current reviewed constituent basket unless historical membership versions are available."; return value


def rotation_payload(snapshot: ThemeSnapshot | None, interval: str) -> dict[str, Any]:
    normalized = interval.upper()
    if normalized not in {"1W", "1M", "3M"}: raise ValueError("unsupported_theme_rotation_interval")
    if snapshot is None:
        return {**unavailable_theme_payload(), "entity_type": "theme", "interval": normalized, "series": [], "current_positions_available": False, "basket_trails_available": False, "snapshot_transition_history_available": False, "current_point_count": 0, "trail_point_count": 0, "transition_snapshot_count": 0, "limited_history_reason": "No reviewed active ThemeSnapshot is available."}
    series = [row.get("rotation_series", {}).get(normalized) for row in snapshot.rows]
    series = [item for item in series if isinstance(item, dict)]
    current_count = sum(item.get("current_point") is not None for item in series); trail_count = sum(len(item.get("trail_points") or []) for item in series)
    return {"snapshot_id": snapshot.snapshot_id, "market_date": snapshot.market_date, "source_state": snapshot.source_state, "status": snapshot.status, "entity_type": "theme", "benchmark": "SPY", "interval": normalized, "series": series, "current_positions_available": current_count > 0, "basket_trails_available": trail_count > current_count, "snapshot_transition_history_available": len(snapshot.alerts) > 0, "current_point_count": current_count, "trail_point_count": trail_count, "transition_snapshot_count": 1, "limited_history_reason": "Theme transition alerts require additional immutable ThemeSnapshots." if len(snapshot.alerts) == 0 else None, "warnings": list(snapshot.warnings)}
