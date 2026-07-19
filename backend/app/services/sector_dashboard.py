from __future__ import annotations
import os
from typing import Any
from app.market_history.storage import DailyBarStorage
from app.rotation.engine import build_rotation_series
from app.rotation.policy import INTERVAL_POLICIES, ROTATION_FORMULA_VERSION, ROTATION_NORMALIZATION_VERSION
from app.securities.registry import SECTOR_BY_ID
from app.sector_snapshots.service import get_sector_snapshot_service


def build_sector_dashboard() -> dict[str, Any]:
    snapshot = get_sector_snapshot_service().latest()
    if snapshot is None:
        # Explicit test mode keeps report/PDF fixtures structurally complete.
        # Live reads never substitute these rows for durable sector intelligence.
        if (os.getenv("DATA_PROVIDER") or os.getenv("MARKET_DATA_PROVIDER") or "test").lower() in {"test", "generated_test_data", "mock"}:
            return {"status": "unavailable", "sectors": [{"id": value["sector_id"], "name": value["display_name"], "symbol": value["etf_symbol"], "returns": {"1d": None, "1w": None, "1m": None, "3m": None, "6m": None, "1y": None}, "rotation": {}, "source": "test", "metadata": {"status": "Unavailable", "coverage_percent": 0}} for value in SECTOR_BY_ID.values()], "themes": [], "benchmark": "SPY", "source": "test", "data_status": "unavailable"}
        return {"status": "unavailable", "sectors": [], "themes": [], "benchmark": "SPY", "source": "unavailable"}
    sectors = []
    for row in snapshot.sectors:
        price = row["price_metrics"]; score = row["component_scores"]
        sectors.append({"id": row["sector_id"], "name": row["display_name"], "symbol": row["etf_symbol"], "returns": {"1d": price.get("return_1d"), "1w": price["return_1w"], "1m": price["return_1m"], "3m": price["return_3m"], "6m": price.get("return_6m"), "1y": price.get("return_1y")}, "rotation": {"1w": rotation_from_series(row.get("rotation_series", {}).get("1W")), "1m": rotation_from_series(row.get("rotation_series", {}).get("1M")), "3m": rotation_from_series(row.get("rotation_series", {}).get("3M"))}, "source": snapshot.source_state, "metadata": {"status": row["classification"], "rank": row.get("rank"), "composite_score": row["composite_score"], "relative_strength_1m": row["relative_strength_metrics"]["vs_spy_1m"], "percent_above_50ema": row["breadth_metrics"]["percent_above_ema50"], "coverage_percent": round(row["coverage_ratio"] * 100, 2), "successful_symbols": row["eligible_members"], "total_members": row["total_members"], "as_of": snapshot.market_date, "snapshot_id": snapshot.snapshot_id}})
    return {"status": snapshot.status, "snapshot_id": snapshot.snapshot_id, "universe_id": snapshot.universe_id, "universe_version": snapshot.universe_version, "market_date": snapshot.market_date, "benchmark": snapshot.benchmark, "source": snapshot.source_state, "data_status": snapshot.status, "sectors": sectors, "themes": [], "alerts": list(snapshot.alerts), "summary": snapshot.rotation_summary, "coverage": snapshot.coverage, "warnings": list(snapshot.warnings), "partial": snapshot.status == "partial", "as_of": snapshot.market_date, "cache_status": "snapshot"}


def rotation(relative_strength: float | None, momentum: float | None) -> dict[str, Any] | None:
    if relative_strength is None or momentum is None: return None
    return {"relative_strength": 50 + relative_strength, "relative_momentum": 50 + momentum, "quadrant": "leading" if relative_strength >= 55 and momentum >= 55 else "improving" if momentum >= 50 else "weakening" if relative_strength >= 50 else "lagging", "history": []}


def rotation_from_series(series: object) -> dict[str, Any] | None:
    if not isinstance(series, dict) or not isinstance(series.get("current_point"), dict):
        return None
    point = series["current_point"]
    return {
        "relative_strength": point.get("plotted_x"),
        "relative_momentum": point.get("plotted_y"),
        "quadrant": point.get("quadrant"),
        "history": [],
        "formula_version": series.get("formula_version"),
        "normalization_version": series.get("normalization_version"),
    }


ROTATION_HISTORY_LIMIT = 4
ROTATION_MOVEMENT_THRESHOLD = 1.0


def build_sector_rotation_trails(snapshot: Any, history: list[dict[str, Any]], bars: DailyBarStorage | None = None) -> dict[str, Any]:
    """Expose snapshot movement separately from canonical durable-history trails."""
    published = _distinct_published_snapshots(snapshot, history)[-ROTATION_HISTORY_LIMIT:]
    trails: dict[str, list[dict[str, object]]] = {}
    movements: dict[str, dict[str, object]] = {}
    for current in snapshot.sectors:
        sector_id = current["sector_id"]
        points = []
        for published_snapshot in published:
            row = next((item for item in published_snapshot.get("sectors", []) if item.get("sector_id") == sector_id), None)
            scores = row.get("component_scores", {}) if isinstance(row, dict) else {}
            relative_strength = scores.get("relative_strength")
            momentum = scores.get("momentum")
            if not isinstance(relative_strength, (int, float)) or not isinstance(momentum, (int, float)):
                continue
            market_date = published_snapshot.get("market_date")
            if isinstance(market_date, str):
                points.append({"date": market_date, "date_label": market_date, "relative_strength": round(50 + relative_strength, 3), "relative_momentum": round(50 + momentum, 3)})
        trails[sector_id] = points
        movements[sector_id] = movement_for(current, points)
    groups = {"gaining": [], "losing": [], "stable": []}
    if len(published) > 1:
        for current in snapshot.sectors:
            movement = movements[current["sector_id"]]
            groups[movement["direction"]].append({"sector_id": current["sector_id"], "display_name": current["display_name"], "etf_symbol": current["etf_symbol"], **movement})
    series = build_market_rotation_series(snapshot, bars=bars)
    market_trails = {
        entity_id: {
            item["interval"]: [legacy_point(point) for point in item["trail_points"]]
            for item in series
            if item["entity_id"] == entity_id
        }
        for entity_id in {item["entity_id"] for item in series}
    }
    current_points = {
        entity_id: {
            item["interval"]: legacy_point(item["current_point"]) if item["current_point"] else None
            for item in series
            if item["entity_id"] == entity_id
        }
        for entity_id in {item["entity_id"] for item in series}
    }
    current_series = [item for item in series if item.get("current_point")]
    trail_point_count = sum(len(item.get("trail_points") or []) for item in current_series)
    transition_snapshot_count = len(published)
    snapshot_transition_history_available = transition_snapshot_count > 1
    return {
        "entity_type": "sector",
        "source_state": snapshot.source_state,
        "data_mode": "live" if snapshot.source_state == "live" else "test",
        "formula_version": ROTATION_FORMULA_VERSION,
        "normalization_version": ROTATION_NORMALIZATION_VERSION,
        "benchmark": snapshot.benchmark,
        "trails": trails,
        "published_snapshot_trails": trails,
        "market_trails": market_trails,
        "current_points": current_points,
        "series": series,
        # Current positions and durable ETF trails remain usable when the
        # separately-published snapshot transition history is still shallow.
        "current_positions_available": bool(current_series),
        "etf_trails_available": trail_point_count > len(current_series),
        "snapshot_transition_history_available": snapshot_transition_history_available,
        "current_point_count": len(current_series),
        "trail_point_count": trail_point_count,
        "transition_snapshot_count": transition_snapshot_count,
        "limited_history_reason": None if snapshot_transition_history_available else "Snapshot transition alerts require additional daily SectorSnapshots.",
        "movements": movements,
        "flow_groups": groups,
        "history_point_count": len(published),
        "movement_available": snapshot_transition_history_available,
        "trail_limit": ROTATION_HISTORY_LIMIT,
        "trail_source": "published_sector_snapshots",
        "market_trail_source": "durable_polygon_adjusted_daily_history",
        "warnings": ["Published snapshot movement is separate from rotation trails. Rotation series uses adjusted ETF and SPY daily history without endpoint rebasing."],
    }


def _distinct_published_snapshots(snapshot: Any, history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_market_date: dict[str, dict[str, Any]] = {}
    for item in history:
        market_date = item.get("market_date") if isinstance(item, dict) else None
        if isinstance(market_date, str):
            by_market_date[market_date] = item
    by_market_date[snapshot.market_date] = snapshot.model_dump()
    return [by_market_date[market_date] for market_date in sorted(by_market_date)]


def movement_for(current: dict[str, Any], points: list[dict[str, object]]) -> dict[str, object]:
    if len(points) < 2:
        return {"direction": "stable", "state": "insufficient_history", "relative_strength_change": None, "relative_momentum_change": None}
    previous, latest = points[-2], points[-1]
    strength_change = round(float(latest["relative_strength"]) - float(previous["relative_strength"]), 3)
    momentum_change = round(float(latest["relative_momentum"]) - float(previous["relative_momentum"]), 3)
    if strength_change >= ROTATION_MOVEMENT_THRESHOLD and momentum_change >= ROTATION_MOVEMENT_THRESHOLD:
        direction = "gaining"
    elif strength_change <= -ROTATION_MOVEMENT_THRESHOLD and momentum_change <= -ROTATION_MOVEMENT_THRESHOLD:
        direction = "losing"
    else:
        direction = "stable"
    return {"direction": direction, "state": "available", "relative_strength_change": strength_change, "relative_momentum_change": momentum_change}


def build_market_rotation_series(snapshot: Any, *, bars: DailyBarStorage | None = None) -> list[dict[str, object]]:
    """Build interval-specific series from aligned, durable adjusted ETF/SPY bars."""
    storage = bars or DailyBarStorage()
    benchmark = storage.history(snapshot.benchmark, end_date=snapshot.market_date)
    data_mode = "live" if snapshot.source_state == "live" else "test"
    result: list[dict[str, object]] = []
    for row in snapshot.sectors:
        history = storage.history(row["etf_symbol"], end_date=snapshot.market_date)
        for interval in INTERVAL_POLICIES:
            series = build_rotation_series(
                entity_type="sector",
                entity_id=row["sector_id"],
                display_name=row["display_name"],
                short_label=row["etf_symbol"],
                entity_symbol=row["etf_symbol"],
                entity_history=history,
                benchmark_symbol=snapshot.benchmark,
                benchmark_history=benchmark,
                interval=interval,
                source_state=snapshot.source_state,
                data_mode=data_mode,
                universe_id=snapshot.universe_id,
                universe_version=snapshot.universe_version,
                coverage_ratio=row.get("coverage_ratio"),
                snapshot_id=snapshot.snapshot_id,
            )
            result.append(series.model_dump())
    return result


def legacy_point(point: dict[str, object] | None) -> dict[str, object] | None:
    if point is None:
        return None
    return {
        "date": point["market_date"],
        "date_label": point["market_date"],
        "relative_strength": point["plotted_x"],
        "relative_momentum": point["plotted_y"],
        "source_provider": point["source_provider"],
        "is_synthetic": point["is_synthetic"],
        "compatibility_signature": point["compatibility_signature"],
    }
