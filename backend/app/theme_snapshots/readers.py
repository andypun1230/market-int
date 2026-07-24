from __future__ import annotations

import math
from typing import Any

from app.rotation.engine import quadrant
from app.rotation.theme_policy import (
    THEME_ROTATION_BENCHMARK,
    THEME_ROTATION_MODEL_ID,
    THEME_ROTATION_MODEL_VERSION,
    THEME_ROTATION_NORMALIZATION_VERSION,
    ThemeRotationProfile,
    theme_profile_for,
)
from app.theme_snapshots.models import ThemeSnapshot


def unavailable_theme_payload(reason: str = "Live Theme Intelligence is not yet available.") -> dict[str, Any]:
    return {
        "status": "unavailable",
        "source_state": "unavailable",
        "snapshot_id": None,
        "market_date": None,
        "items": [],
        "rows": [],
        "rankings": [],
        "warnings": [reason],
        "historical_disclosure": "Historical results use the current reviewed constituent basket unless historical membership versions are available.",
    }


def snapshot_payload(snapshot: ThemeSnapshot | None) -> dict[str, Any]:
    if snapshot is None:
        return unavailable_theme_payload()
    value = snapshot.model_dump()
    value["items"] = list(snapshot.rows)
    value["historical_disclosure"] = "Historical results use the current reviewed constituent basket unless historical membership versions are available."
    return value


def rotation_payload(
    snapshot: ThemeSnapshot | None,
    timeframe: str,
    *,
    compact: bool = False,
) -> dict[str, Any]:
    try:
        profile = theme_profile_for(timeframe)
    except ValueError as error:
        raise ValueError("unsupported_theme_rotation_interval") from error
    normalized = profile.interval_alias
    if snapshot is None:
        unavailable = {
            **unavailable_theme_payload(),
            "entity_type": "theme",
            "taxonomy_version": None,
            "as_of": None,
            "timeframe": normalized,
            "interval": normalized,
            "profile": profile.profile,
            "rotation_model_id": THEME_ROTATION_MODEL_ID,
            "rotation_model_version": THEME_ROTATION_MODEL_VERSION,
            "benchmark": THEME_ROTATION_BENCHMARK,
            "snapshot_status": "unavailable",
            "eligible_count": 0,
            "excluded_count": 0,
            "points": [],
            "tails": [],
            "series": [],
            "exclusions": [],
            "current_positions_available": False,
            "basket_trails_available": False,
            "snapshot_transition_history_available": False,
            "current_point_count": 0,
            "trail_point_count": 0,
            "transition_snapshot_count": 0,
            "limited_history_reason": "No reviewed active ThemeSnapshot is available.",
            "profile_definition": profile.model_dump(),
            "timeframe_definition": _timeframe_definition(profile),
        }
        return {**unavailable, "contract": "theme_rotation_summary_v1"} if compact else unavailable

    points: list[dict[str, Any]] = []
    exclusions: list[dict[str, str]] = []
    eligible_series: list[dict[str, Any]] = []
    seen: set[str] = set()
    ordered_rows = sorted(snapshot.rows, key=lambda row: (row.get("rank") is None, int(row.get("rank") or 1_000_000), str(row.get("theme_id") or "")))
    for row in ordered_rows:
        theme_id = str(row.get("theme_id") or "").strip()
        reason = _rotation_exclusion(row, normalized, seen, snapshot.source_state)
        if reason:
            exclusions.append({"theme_id": theme_id, "reason": reason})
            continue
        seen.add(theme_id)
        series = row["rotation_series"][normalized]
        trail = [item for item in series.get("trail_points") or [] if _valid_rotation_point(item)]
        if trail:
            trail[-1] = {**trail[-1], "snapshot_id": snapshot.snapshot_id, "is_current": True}
        current = trail[-1]
        previous = trail[-2] if len(trail) >= 2 else None
        evidence = _evidence_references(row, current)
        status = _row_status(row)
        coverage_ratio = _finite(current.get("coverage_ratio")) or _finite(row.get("coverage_ratio"))
        current_x = float(current["relative_trend"])
        current_y = float(current["relative_momentum"])
        current_quadrant = quadrant(current_x, current_y)
        previous_quadrant = quadrant(float(previous["relative_trend"]), float(previous["relative_momentum"])) if previous else None
        latest_transition = (
            {
                "from": previous_quadrant,
                "to": current_quadrant,
                "changed": previous_quadrant != current_quadrant,
                "as_of": str(current.get("market_date") or snapshot.market_date),
            }
            if previous_quadrant
            else None
        )
        point = {
            "theme_id": theme_id,
            "display_name": str(row.get("display_name") or row.get("name") or theme_id),
            "taxonomy_version": snapshot.taxonomy_version,
            "snapshot_id": snapshot.snapshot_id,
            "as_of": str(current.get("market_date") or snapshot.market_date),
            "timeframe": normalized,
            "profile": profile.profile,
            "status": status,
            "confidence": current.get("confidence") or series.get("confidence") or _confidence(row),
            "relative_trend": current_x,
            "relative_trend_value": current_x,
            "relative_strength_value": float(current["raw_rs"]),
            "relative_strength_normalized": current_x,
            "relative_momentum": current_y,
            "momentum_value": current_y,
            "momentum_normalized": current_y,
            "previous_relative_trend": float(previous["relative_trend"]) if previous else None,
            "previous_relative_strength_normalized": float(previous["relative_trend"]) if previous else None,
            "previous_momentum_normalized": float(previous["relative_momentum"]) if previous else None,
            "quadrant": current_quadrant,
            "previous_quadrant": previous_quadrant,
            "latest_quadrant_transition": latest_transition,
            "trajectory": _trajectory(previous, current),
            "direction": series.get("direction"),
            "speed": series.get("speed"),
            "distance_travelled": series.get("distance_travelled"),
            "net_displacement": series.get("net_displacement"),
            "recent_acceleration": series.get("recent_acceleration"),
            "quadrant_transitions": series.get("quadrant_transitions"),
            "coverage_ratio": coverage_ratio,
            "evidence_references": evidence,
            "missing_data": list(row.get("missing_data") or []),
            "ranking_eligible": row.get("rank") is not None,
            "rank": row.get("rank"),
            "label_priority": _label_priority(row, current_quadrant, previous, current),
            "partial_coverage_disclosure": _partial_coverage_disclosure(row, coverage_ratio),
            "trail_points": trail,
            "current_point": current,
            "previous_point": previous,
            "compatibility_signature": series.get("compatibility_signature"),
            "formula_version": series.get("formula_version"),
            "model_id": series.get("model_id"),
            "model_version": series.get("model_version"),
            "normalization_version": series.get("normalization_version"),
            "normalization_metadata": series.get("normalization_metadata"),
        }
        if compact:
            points.append(_compact_rotation_point(point, row))
        else:
            points.append(point)
            eligible_series.append(series)

    trail_count = sum(len(point["trail_points"]) for point in points)
    latest_dates = [str(point["as_of"]) for point in points if point.get("as_of")]
    response_status = "available" if points and not exclusions else "partial" if points else "unavailable"
    quadrant_counts = {key: sum(point["quadrant"] == key for point in points) for key in ("leading", "improving", "weakening", "lagging")}
    tails = [
        {
            "theme_id": point["theme_id"],
            "display_name": point["display_name"],
            "profile": profile.profile,
            "observations": point["trail_points"],
            "current_observation": point["current_point"],
            "direction": point["direction"],
            "speed": point["speed"],
            "distance_travelled": point["distance_travelled"],
            "net_displacement": point["net_displacement"],
            "recent_acceleration": point["recent_acceleration"],
            "quadrant_transitions": point["quadrant_transitions"],
            "latest_common_date": point["as_of"],
            "confidence": point["confidence"],
            "evidence_references": point["evidence_references"],
        }
        for point in points
    ] if not compact else []
    result = {
        "snapshot_id": snapshot.snapshot_id,
        "taxonomy_version": snapshot.taxonomy_version,
        "market_date": snapshot.market_date,
        "as_of": snapshot.published_at,
        "source_state": snapshot.source_state,
        "status": response_status,
        "snapshot_status": snapshot.status,
        "entity_type": "theme",
        "benchmark": THEME_ROTATION_BENCHMARK,
        "timeframe": normalized,
        "interval": normalized,
        "profile": profile.profile,
        "profile_definition": profile.model_dump(),
        "rotation_model_id": THEME_ROTATION_MODEL_ID,
        "rotation_model_version": THEME_ROTATION_MODEL_VERSION,
        "normalization_version": THEME_ROTATION_NORMALIZATION_VERSION,
        "eligible_count": len(points),
        "excluded_count": len(exclusions),
        "points": points,
        "exclusions": exclusions,
        "current_positions_available": bool(points),
        "basket_trails_available": trail_count > len(points),
        "snapshot_transition_history_available": len(snapshot.alerts) > 0,
        "current_point_count": len(points),
        "trail_point_count": trail_count,
        "transition_snapshot_count": 1,
        "latest_common_date": min(latest_dates) if latest_dates else None,
        "quadrant_counts": quadrant_counts,
        "limited_history_reason": "Theme transition alerts require additional immutable ThemeSnapshots." if len(snapshot.alerts) == 0 else None,
        "timeframe_definition": _timeframe_definition(profile),
        "label_priority_policy": "canonical rank, quadrant materiality, and same-theme trail movement; frontend watchlist priority remains additive",
        "warnings": list(snapshot.warnings),
    }
    if compact:
        return {**result, "contract": "theme_rotation_summary_v1"}
    return {
        **result,
        "tails": tails,
        "series": eligible_series,
        "normalization_metadata": eligible_series[0].get("normalization_metadata") if eligible_series else None,
        "evidence_metadata": {
            "required": True,
            "point_evidence_reference_count": sum(len(point["evidence_references"]) for point in points),
            "source": "canonical ThemeSnapshot rotation_series and row evidence",
        },
    }


def rotation_summary_payload(snapshot: ThemeSnapshot | None, timeframe: str) -> dict[str, Any]:
    """Return the canonical rotation coordinates without detail-only series duplication."""
    return rotation_payload(snapshot, timeframe, compact=True)


def _compact_rotation_point(point: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    definition = row.get("definition") if isinstance(row.get("definition"), dict) else {}
    fields = (
        "theme_id", "display_name", "taxonomy_version", "snapshot_id", "as_of",
        "timeframe", "profile", "status", "confidence", "relative_trend",
        "relative_momentum", "previous_relative_trend", "previous_momentum_normalized",
        "quadrant", "previous_quadrant", "latest_quadrant_transition", "trajectory",
        "direction", "speed", "distance_travelled", "net_displacement",
        "recent_acceleration", "quadrant_transitions", "coverage_ratio",
        "evidence_references", "missing_data", "ranking_eligible", "rank",
        "label_priority", "partial_coverage_disclosure", "trail_points", "model_version",
    )
    return {
        **{key: point.get(key) for key in fields},
        "aliases": list(definition.get("aliases") or row.get("aliases") or []),
        "parent_sector_ids": list(definition.get("parent_sector_ids") or []),
        "taxonomy_status": definition.get("status", "active"),
    }


def _rotation_exclusion(row: dict[str, Any], timeframe: str, seen: set[str], snapshot_source_state: str) -> str | None:
    theme_id = str(row.get("theme_id") or "").strip()
    if not theme_id:
        return "missing_theme_id"
    if theme_id in seen:
        return "duplicate_theme_id"
    definition = row.get("definition") if isinstance(row.get("definition"), dict) else {}
    if definition.get("status") == "retired":
        return "retired_theme"
    if _row_status(row) != "available":
        return "row_status_not_available"
    provenance = row.get("provenance") if isinstance(row.get("provenance"), dict) else {}
    series = row.get("rotation_series", {}).get(timeframe) if isinstance(row.get("rotation_series"), dict) else None
    if not isinstance(series, dict):
        return "selected_timeframe_series_missing"
    if snapshot_source_state == "live" and (provenance.get("category") == "test_fixture" or series.get("data_mode") == "test"):
        return "test_only_data"
    current = series.get("current_point")
    if not _valid_rotation_point(current):
        return "selected_timeframe_metrics_missing"
    if not _confidence_is_usable(row):
        return "confidence_below_usable_threshold"
    if not _evidence_references(row, current):
        return "evidence_validation_failed"
    return None


def _row_status(row: dict[str, Any]) -> str:
    explicit = row.get("status")
    if explicit in {"available", "partial", "unavailable"}:
        return str(explicit)
    coverage = row.get("coverage_status")
    return "available" if coverage in {"complete", "partial"} else "unavailable"


def _confidence(row: dict[str, Any]) -> dict[str, Any]:
    canonical = row.get("confidence")
    if isinstance(canonical, dict):
        return canonical
    return {
        "label": str((row.get("signal_confidence") or {}).get("label") or (row.get("data_confidence") or {}).get("label") or "unknown").lower(),
        "signal": row.get("signal_confidence"),
        "data": row.get("data_confidence"),
    }


def _confidence_is_usable(row: dict[str, Any]) -> bool:
    if row.get("rank") is not None:
        return True
    label = str(_confidence(row).get("label") or "").lower()
    return label in {"moderate", "high", "strong"}


def _evidence_references(row: dict[str, Any], current: dict[str, Any]) -> list[str]:
    result = [
        str(item.get("evidence_id"))
        for item in row.get("evidence") or []
        if isinstance(item, dict) and item.get("evidence_id")
    ]
    result.extend(str(item) for item in current.get("source_series_ids") or [] if item)
    return list(dict.fromkeys(result))


def _valid_rotation_point(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    return all(_finite(value.get(key)) is not None for key in ("relative_trend", "relative_momentum", "plotted_x", "plotted_y"))


def _finite(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and math.isfinite(float(value)) else None


def _trajectory(previous: dict[str, Any] | None, current: dict[str, Any]) -> str | None:
    if previous is None:
        return None
    delta_x = float(current["relative_trend"]) - float(previous["relative_trend"])
    delta_y = float(current["relative_momentum"]) - float(previous["relative_momentum"])
    tolerance = 1e-9
    if delta_x >= -tolerance and delta_y >= -tolerance and (delta_x > tolerance or delta_y > tolerance):
        return "improving"
    if delta_x <= tolerance and delta_y <= tolerance and (delta_x < -tolerance or delta_y < -tolerance):
        return "deteriorating"
    return "stable"


def _label_priority(row: dict[str, Any], current_quadrant: str, previous: dict[str, Any] | None, current: dict[str, Any]) -> float:
    quadrant_priority = {"leading": 4_000, "improving": 3_000, "weakening": 2_000, "lagging": 1_000}[current_quadrant]
    rank_priority = max(0, 1_000 - int(row.get("rank") or 1_000) * 10)
    movement = 0.0 if previous is None else math.hypot(float(current["plotted_x"]) - float(previous["plotted_x"]), float(current["plotted_y"]) - float(previous["plotted_y"]))
    materiality = math.hypot(float(current["plotted_x"]) - 100, float(current["plotted_y"]) - 100)
    return round(quadrant_priority + rank_priority + movement * 10 + materiality, 4)


def _partial_coverage_disclosure(row: dict[str, Any], coverage_ratio: float | None) -> str | None:
    if row.get("coverage_status") != "partial":
        return None
    return f"Available under the unchanged governed coverage gate with {coverage_ratio:.1%} mapped 21-session coverage." if coverage_ratio is not None else "Available with explicit partial coverage disclosure."


def _timeframe_definition(profile: ThemeRotationProfile) -> dict[str, Any]:
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
