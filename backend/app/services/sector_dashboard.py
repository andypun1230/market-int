from __future__ import annotations
import os
import math
from typing import Any
from app.market_history.storage import DailyBarStorage
from app.rotation.sector_engine import build_sector_rotation_series
from app.rotation.sector_policy import (
    SECTOR_ROTATION_BENCHMARK,
    SECTOR_ROTATION_MODEL_ID,
    SECTOR_ROTATION_MODEL_VERSION,
    SECTOR_ROTATION_NORMALIZATION_VERSION,
    sector_profile_for,
)
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
        compatibility_rotation = row.get("legacy_rotation_series", row.get("rotation_series", {}))
        sectors.append({"id": row["sector_id"], "name": row["display_name"], "symbol": row["etf_symbol"], "returns": {"1d": price.get("return_1d"), "1w": price["return_1w"], "1m": price["return_1m"], "3m": price["return_3m"], "6m": price.get("return_6m"), "1y": price.get("return_1y")}, "rotation": {"1w": rotation_from_series(compatibility_rotation.get("1W")), "1m": rotation_from_series(compatibility_rotation.get("1M")), "3m": rotation_from_series(compatibility_rotation.get("3M"))}, "canonical_rotation": {"1w": canonical_rotation_from_series(row.get("rotation_series", {}).get("1W")), "1m": canonical_rotation_from_series(row.get("rotation_series", {}).get("1M")), "3m": canonical_rotation_from_series(row.get("rotation_series", {}).get("3M"))}, "source": snapshot.source_state, "metadata": {"status": row["classification"], "rank": row.get("rank"), "composite_score": row["composite_score"], "relative_strength_1m": row["relative_strength_metrics"]["vs_spy_1m"], "percent_above_50ema": row["breadth_metrics"]["percent_above_ema50"], "coverage_percent": round(row["coverage_ratio"] * 100, 2), "successful_symbols": row["eligible_members"], "total_members": row["total_members"], "as_of": snapshot.market_date, "snapshot_id": snapshot.snapshot_id}})
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


def canonical_rotation_from_series(series: object) -> dict[str, Any] | None:
    if not isinstance(series, dict) or series.get("model_version") != SECTOR_ROTATION_MODEL_VERSION:
        return None
    point = series.get("current_point")
    if not isinstance(point, dict):
        return None
    return {
        "relative_trend": point.get("relative_trend"),
        "relative_momentum": point.get("relative_momentum"),
        "quadrant": point.get("quadrant"),
        "history": [
            {
                "date": item.get("market_date"),
                "relative_trend": item.get("relative_trend"),
                "relative_momentum": item.get("relative_momentum"),
                "quadrant": item.get("quadrant"),
            }
            for item in series.get("trail_points") or []
            if isinstance(item, dict)
        ],
        "model_version": series.get("model_version"),
        "profile": series.get("profile"),
    }


ROTATION_HISTORY_LIMIT = 4
ROTATION_MOVEMENT_THRESHOLD = 1.0


def build_sector_rotation_trails(
    snapshot: Any,
    history: list[dict[str, Any]],
    bars: DailyBarStorage | None = None,
    profile: str = "medium",
) -> dict[str, Any]:
    """Expose canonical Sector Relative Trend/Momentum tails and separate snapshot movement."""
    selected = sector_profile_for(profile)
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
    series = build_market_rotation_series(snapshot, profile=selected.profile, bars=bars)
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
    points: list[dict[str, Any]] = []
    tails: list[dict[str, Any]] = []
    for item in current_series:
        trail = [dict(point) for point in item.get("trail_points") or []]
        if not trail:
            continue
        trail[-1] = {**trail[-1], "snapshot_id": snapshot.snapshot_id, "is_current": True}
        current = trail[-1]
        previous = trail[-2] if len(trail) >= 2 else None
        point = {
            "sector_id": item["entity_id"],
            "display_name": item["display_name"],
            "etf_symbol": item["short_label"],
            "snapshot_id": snapshot.snapshot_id,
            "universe_version": snapshot.universe_version,
            "as_of": current["market_date"],
            "timeframe": selected.interval_alias,
            "profile": selected.profile,
            "status": item.get("status"),
            "confidence": current.get("confidence") or item.get("confidence"),
            "relative_trend": current["relative_trend"],
            "relative_momentum": current["relative_momentum"],
            "previous_relative_trend": previous.get("relative_trend") if previous else None,
            "previous_relative_momentum": previous.get("relative_momentum") if previous else None,
            "quadrant": current["quadrant"],
            "direction": item.get("direction"),
            "speed": item.get("speed"),
            "distance_travelled": item.get("distance_travelled"),
            "net_displacement": item.get("net_displacement"),
            "recent_acceleration": item.get("recent_acceleration"),
            "quadrant_transitions": item.get("quadrant_transitions"),
            "coverage_ratio": current.get("coverage_ratio"),
            "evidence_references": list(current.get("evidence") or []),
            "missing_data": list(current.get("missing_data") or []),
            "ranking_eligible": True,
            "rank": next((row.get("rank") for row in snapshot.sectors if row.get("sector_id") == item["entity_id"]), None),
            "label_priority": _label_priority(item, current, previous),
            "trail_points": trail,
            "current_point": current,
            "model_id": SECTOR_ROTATION_MODEL_ID,
            "model_version": SECTOR_ROTATION_MODEL_VERSION,
            "normalization_version": SECTOR_ROTATION_NORMALIZATION_VERSION,
        }
        points.append(point)
        tails.append({
            "sector_id": point["sector_id"],
            "display_name": point["display_name"],
            "etf_symbol": point["etf_symbol"],
            "profile": selected.profile,
            "observations": trail,
            "current_observation": current,
            "direction": point["direction"],
            "speed": point["speed"],
            "distance_travelled": point["distance_travelled"],
            "net_displacement": point["net_displacement"],
            "recent_acceleration": point["recent_acceleration"],
            "quadrant_transitions": point["quadrant_transitions"],
            "latest_common_date": point["as_of"],
            "confidence": point["confidence"],
            "evidence_references": point["evidence_references"],
        })
    trail_point_count = sum(len(item.get("trail_points") or []) for item in current_series)
    transition_snapshot_count = len(published)
    snapshot_transition_history_available = transition_snapshot_count > 1
    return {
        "entity_type": "sector",
        "source_state": snapshot.source_state,
        "data_mode": "live" if snapshot.source_state == "live" else "test",
        "formula_version": SECTOR_ROTATION_MODEL_VERSION,
        "rotation_model_id": SECTOR_ROTATION_MODEL_ID,
        "rotation_model_version": SECTOR_ROTATION_MODEL_VERSION,
        "normalization_version": SECTOR_ROTATION_NORMALIZATION_VERSION,
        "benchmark": SECTOR_ROTATION_BENCHMARK,
        "profile": selected.profile,
        "timeframe": selected.interval_alias,
        "interval": selected.interval_alias,
        "profile_definition": selected.model_dump(),
        "timeframe_definition": _timeframe_definition(selected),
        "trails": tails,
        "points": points,
        "published_snapshot_trails": trails,
        "market_trails": market_trails,
        "current_points": current_points,
        "series": series,
        "status": "available" if current_series else "unavailable",
        "eligible_count": len(current_series),
        "excluded_count": len(snapshot.sectors) - len(current_series),
        "exclusions": [
            {"sector_id": row["sector_id"], "reason": "selected_profile_metrics_missing"}
            for row in snapshot.sectors
            if row["sector_id"] not in {item["entity_id"] for item in current_series}
        ],
        "quadrant_counts": {
            key: sum(point["quadrant"] == key for point in points)
            for key in ("leading", "improving", "weakening", "lagging")
        },
        "latest_common_date": min((str(point["as_of"]) for point in points), default=None),
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
        "trail_limit": selected.tail_observations,
        "trail_source": "published_sector_snapshots",
        "market_trail_source": "durable_polygon_adjusted_daily_history",
        "normalization_metadata": current_series[0].get("normalization_metadata") if current_series else None,
        "evidence_metadata": {
            "required": True,
            "point_evidence_reference_count": sum(len(point["evidence_references"]) for point in points),
            "source": "canonical SectorSnapshot adjusted sector ETF and SPY rotation_series",
        },
        "warnings": ["Published snapshot movement is separate from canonical Sector Relative Trend / Relative Momentum tails."],
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


def build_market_rotation_series(
    snapshot: Any,
    *,
    profile: str = "medium",
    bars: DailyBarStorage | None = None,
) -> list[dict[str, object]]:
    """Read persisted canonical series, with a batched durable-history migration fallback."""
    selected = sector_profile_for(profile)
    persisted: list[dict[str, object]] = []
    for row in snapshot.sectors:
        value = row.get("rotation_series", {}).get(selected.interval_alias)
        if not isinstance(value, dict) or value.get("model_version") != SECTOR_ROTATION_MODEL_VERSION:
            persisted = []
            break
        persisted.append(_with_snapshot_identity(value, snapshot.snapshot_id))
    if len(persisted) == len(snapshot.sectors):
        return persisted

    storage = bars or DailyBarStorage()
    symbols = [snapshot.benchmark, *(row["etf_symbol"] for row in snapshot.sectors)]
    histories = storage.histories(tuple(symbols), end_date=snapshot.market_date)
    benchmark = histories.get(snapshot.benchmark, [])
    data_mode = "live" if snapshot.source_state == "live" else "test"
    result: list[dict[str, object]] = []
    for row in snapshot.sectors:
        result.append(build_sector_rotation_series(
            sector_id=row["sector_id"],
            display_name=row["display_name"],
            etf_symbol=row["etf_symbol"],
            etf_history=histories.get(row["etf_symbol"], []),
            benchmark_history=benchmark,
            profile=selected.profile,
            source_state=snapshot.source_state,
            data_mode=data_mode,
            universe_id=snapshot.universe_id,
            universe_version=snapshot.universe_version,
            coverage_ratio=row.get("coverage_ratio"),
            eligible_members=row.get("eligible_members"),
            total_members=row.get("total_members"),
            snapshot_id=snapshot.snapshot_id,
        ))
    return result


def legacy_point(point: dict[str, object] | None) -> dict[str, object] | None:
    if point is None:
        return None
    return {
        "date": point["market_date"],
        "date_label": point["market_date"],
        "relative_strength": point.get("relative_trend", point["plotted_x"]),
        "relative_trend": point.get("relative_trend", point["plotted_x"]),
        "relative_momentum": point.get("relative_momentum", point["plotted_y"]),
        "source_provider": point["source_provider"],
        "is_synthetic": point["is_synthetic"],
        "compatibility_signature": point["compatibility_signature"],
    }


def _with_snapshot_identity(value: dict[str, Any], snapshot_id: str) -> dict[str, Any]:
    result = dict(value)
    trail = [dict(point) for point in value.get("trail_points") or []]
    if trail:
        trail[-1] = {**trail[-1], "snapshot_id": snapshot_id, "is_current": True}
        result["current_point"] = trail[-1]
        result["current_observation"] = trail[-1]
    result["trail_points"] = trail
    result["observations"] = trail
    return result


def _label_priority(item: dict[str, Any], current: dict[str, Any], previous: dict[str, Any] | None) -> float:
    quadrant_priority = {"leading": 4_000, "improving": 3_000, "weakening": 2_000, "lagging": 1_000}[current["quadrant"]]
    movement = 0.0 if previous is None else math.hypot(
        float(current["relative_trend"]) - float(previous["relative_trend"]),
        float(current["relative_momentum"]) - float(previous["relative_momentum"]),
    )
    materiality = math.hypot(float(current["relative_trend"]) - 100.0, float(current["relative_momentum"]) - 100.0)
    return round(quadrant_priority + movement * 10.0 + materiality, 4)


def _timeframe_definition(profile: Any) -> dict[str, Any]:
    return {
        "meaning": f"{profile.profile.title()} Relative Trend / Relative Momentum model profile; not a simple {profile.interval_alias} return.",
        "sampling_frequency": profile.sampling_frequency,
        "fast_trend_ema": profile.fast_window,
        "slow_trend_ema": profile.slow_window,
        "relative_volatility_window": profile.volatility_window,
        "normalization_window": profile.normalization_window,
        "momentum_lag": profile.momentum_lag,
        "momentum_smoothing": profile.momentum_smoothing,
        "previous_observation_step": profile.observation_spacing,
        "trail_point_count": profile.tail_observations,
        "benchmark_date_alignment": "exact shared valid adjusted session dates; no interpolation",
        "normalization_midpoint": 100,
    }
