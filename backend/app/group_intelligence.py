from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Iterable, Literal


EntityType = Literal["sector", "theme"]
TIMEFRAME_DAYS = {"1M": 31, "3M": 93, "6M": 186, "1Y": 366}
PERFORMANCE_KEYS = {
    "1D": ("return_1d", "1d"),
    "1W": ("return_1w", "1w"),
    "1M": ("return_1m", "1m"),
    "3M": ("return_3m", "3m"),
    "6M": ("return_6m", "6m"),
    "1Y": ("return_1y", "1y"),
}


@dataclass(frozen=True)
class GroupSources:
    current: dict[str, Any] | None
    history: list[dict[str, Any]]


def normalize_group_registry(entity_type: EntityType, sources: GroupSources) -> dict[str, Any]:
    current = sources.current
    if not current:
        return _unavailable_registry(entity_type, "No canonical snapshot is available.")
    rows = _rows(current, entity_type)
    previous = sources.history[-2] if len(sources.history) >= 2 else None
    previous_rows = {_entity_id(row, entity_type): row for row in _rows(previous, entity_type)}
    items = [
        _normalize_row(entity_type, row, current, previous_rows.get(_entity_id(row, entity_type)), sources.history)
        for row in rows
    ]
    items.sort(key=lambda item: (item["rank"] is None, item["rank"] or 1_000_000, item["name"], item["id"]))
    return {
        "contract_version": "group-intelligence-v1",
        "entity_type": entity_type,
        "snapshot_id": current.get("snapshot_id"),
        "market_date": current.get("market_date"),
        "source_state": current.get("source_state", "unavailable"),
        "status": _response_status(items),
        "model_versions": _model_versions(current, entity_type),
        "items": items,
        "count": len(items),
        "warnings": list(current.get("warnings") or []),
    }


def compare_groups(registry: dict[str, Any], ids: Iterable[str], timeframe: str) -> dict[str, Any]:
    selected_ids = list(dict.fromkeys(value.strip() for value in ids if value.strip()))
    normalized_timeframe = timeframe.upper()
    if normalized_timeframe not in PERFORMANCE_KEYS:
        raise ValueError("unsupported_timeframe")
    if not 2 <= len(selected_ids) <= 5:
        raise ValueError("comparison_requires_two_to_five_entities")
    by_id = {item["id"]: item for item in registry.get("items", [])}
    missing = [entity_id for entity_id in selected_ids if entity_id not in by_id]
    if missing:
        raise ValueError(f"unknown_entities:{','.join(missing)}")
    items = [by_id[entity_id] for entity_id in selected_ids]
    return {
        "contract_version": "group-comparison-v1",
        "entity_type": registry["entity_type"],
        "snapshot_id": registry.get("snapshot_id"),
        "market_date": registry.get("market_date"),
        "timeframe": normalized_timeframe,
        "status": "available" if all(item["availability"]["state"] == "available" for item in items) else "partial",
        "selected_ids": selected_ids,
        "selection_limits": {"minimum": 2, "desktop_maximum": 5, "mobile_maximum": 3},
        "items": items,
        "model_versions": registry.get("model_versions", {}),
        "canonical_url": f"/sectors?compareType={registry['entity_type']}&compareIds={','.join(selected_ids)}&compareTimeframe={normalized_timeframe}",
    }


def filter_groups(registry: dict[str, Any], filters: dict[str, Any]) -> dict[str, Any]:
    items = list(registry.get("items", []))
    state = _text(filters.get("state"))
    quadrant = _text(filters.get("quadrant"))
    rank_max = _number(filters.get("rank_max"))
    breadth_min = _number(filters.get("breadth_min"))
    momentum_min = _number(filters.get("momentum_min"))
    availability = _text(filters.get("availability"))
    movement = _text(filters.get("movement"))
    recent_transition = _bool(filters.get("recent_transition"))
    strong_movement = _bool(filters.get("strong_movement"))
    saved_ids = set(filters.get("saved_ids") or [])
    saved_only = _bool(filters.get("saved_only"))
    def include(item: dict[str, Any]) -> bool:
        if state and item["state"].lower() != state.lower(): return False
        if quadrant and item["quadrant"].lower() != quadrant.lower(): return False
        if rank_max is not None and (item["rank"] is None or item["rank"] > rank_max): return False
        if breadth_min is not None and (item["breadth"]["above_50"] is None or item["breadth"]["above_50"] < breadth_min): return False
        if momentum_min is not None and (item["relative_momentum"] is None or item["relative_momentum"] < momentum_min): return False
        if availability and item["availability"]["state"] != availability: return False
        if movement and item["movement"]["direction"] != movement: return False
        if recent_transition and not item["movement"]["recent_transition"]: return False
        if strong_movement and abs(item["rank_change"] or 0) < 2: return False
        if saved_only and item["id"] not in saved_ids: return False
        return True
    filtered = [item for item in items if include(item)]
    sort_key = _text(filters.get("sort")) or "rank"
    reverse = sort_key in {"performance", "breadth", "momentum", "rank_change"}
    key_paths = {
        "rank": lambda item: item["rank"] if item["rank"] is not None else 1_000_000,
        "performance": lambda item: item["performance"].get((_text(filters.get("timeframe")) or "1M").upper()) if item["performance"].get((_text(filters.get("timeframe")) or "1M").upper()) is not None else -1_000_000,
        "breadth": lambda item: item["breadth"]["above_50"] if item["breadth"]["above_50"] is not None else -1_000_000,
        "momentum": lambda item: item["relative_momentum"] if item["relative_momentum"] is not None else -1_000_000,
        "rank_change": lambda item: item["rank_change"] if item["rank_change"] is not None else -1_000_000,
        "name": lambda item: item["name"].lower(),
    }
    filtered.sort(key=key_paths.get(sort_key, key_paths["rank"]), reverse=reverse)
    return {
        **{key: value for key, value in registry.items() if key != "items"},
        "items": filtered,
        "count": len(filtered),
        "total_count": len(items),
        "active_filters": {key: value for key, value in filters.items() if value not in (None, "", False, [], {})},
        "status": "empty" if not filtered else registry.get("status", "available"),
    }


def build_breadth_history(entity_type: EntityType, entity_id: str, sources: GroupSources, timeframe: str) -> dict[str, Any]:
    normalized_timeframe = timeframe.upper()
    if normalized_timeframe not in TIMEFRAME_DAYS:
        raise ValueError("unsupported_timeframe")
    snapshots = sources.history[-TIMEFRAME_DAYS[normalized_timeframe]:]
    observations: list[dict[str, Any]] = []
    snapshot_ids: list[str] = []
    for snapshot in snapshots:
        row = next((item for item in _rows(snapshot, entity_type) if _entity_id(item, entity_type) == entity_id), None)
        if not row:
            continue
        breadth = _breadth(row, entity_type)
        observations.append({
            "market_date": snapshot.get("market_date"),
            "snapshot_id": snapshot.get("snapshot_id"),
            "relative_strength": _relative_strength(row, entity_type),
            "relative_momentum": _relative_momentum(row, entity_type),
            "rank": _integer(row.get("rank")),
            **breadth,
        })
        if snapshot.get("snapshot_id"):
            snapshot_ids.append(str(snapshot["snapshot_id"]))
    available_metrics = sorted({key for item in observations for key, value in item.items() if key not in {"market_date", "snapshot_id"} and value is not None})
    interpretation = _breadth_interpretation(observations)
    status = "unavailable" if not observations else "partial" if len(available_metrics) < 4 else "available"
    return {
        "contract_version": "group-breadth-history-v1",
        "entity_type": entity_type,
        "entity_id": entity_id,
        "timeframe": normalized_timeframe,
        "status": status,
        "observations": observations,
        "observation_count": len(observations),
        "available_metrics": available_metrics,
        "snapshot_ids": snapshot_ids,
        "interpretation": interpretation,
        "limitation": "Only immutable snapshots actually published are returned; missing history and metrics remain unavailable.",
    }


def detect_divergences(item: dict[str, Any], observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not observations:
        return []
    first, latest = observations[0], observations[-1]
    price = item.get("performance", {}).get("1M")
    strength = item.get("relative_strength")
    momentum = item.get("relative_momentum")
    breadth20 = _delta(first.get("above_20"), latest.get("above_20"))
    breadth50 = _delta(first.get("above_50"), latest.get("above_50"))
    ad_delta = _delta(first.get("advance_decline_ratio"), latest.get("advance_decline_ratio"))
    highs_lows_delta = _delta(first.get("highs_minus_lows"), latest.get("highs_minus_lows"))
    concentration = item.get("concentration")
    entity_type = item.get("type")
    relative_strength_change = _delta(first.get("relative_strength"), latest.get("relative_strength"))
    momentum_change = _delta(first.get("relative_momentum"), latest.get("relative_momentum"))
    candidates = [
        ("sector_price_rising_participation_weakening", "negative", entity_type == "sector" and _gt(price, 2) and _lt(breadth50, -5), "Sector price is rising while constituent participation weakens."),
        ("theme_relative_strength_rising_breadth_falling", "negative", entity_type == "theme" and _gt(relative_strength_change, 1) and _lt(breadth50, -5), "Theme relative strength is rising while constituent breadth falls."),
        ("rank_improvement_without_persistence", "mixed", _gt(item.get("rank_change"), 1) and int(item.get("persistence", {}).get("snapshot_count") or 0) < 2, "Leadership rank improved without persistence confirmation."),
        ("momentum_improvement_relative_trend_weak", "positive", _gt(momentum_change, 5) and _lt(strength, 0), "Momentum is improving while the relative trend remains weak."),
        ("price_up_breadth_down", "negative", _gt(price, 2) and _lt(breadth20, -8) and _lt(breadth50, -5), "Price is advancing while participation is contracting."),
        ("price_down_breadth_up", "positive", _lt(price, -1) and _gt(breadth20, 8) and _gt(breadth50, 5), "Participation is improving before price confirms."),
        ("rotation_leading_momentum_fading", "negative", item.get("quadrant") == "leading" and _lt(momentum, 100), "The group remains Leading while relative momentum fades."),
        ("rotation_improving_price_weak", "positive", item.get("quadrant") == "improving" and _lt(price, 0), "Relative rotation is improving despite weak price."),
        ("price_up_ad_down", "negative", _gt(price, 2) and _lt(ad_delta, -0.2), "Price is advancing while the advance/decline ratio deteriorates."),
        ("price_up_highs_lows_down", "negative", _gt(price, 2) and _lt(highs_lows_delta, 0), "Price is advancing while new-high participation deteriorates."),
        ("leadership_concentrated", "mixed", _gt(price, 2) and _gt(concentration, 60), "Leadership is concentrated in a small share of constituents."),
    ]
    evidence = {
        "price_1m": price, "breadth_20_change": breadth20, "breadth_50_change": breadth50,
        "advance_decline_change": ad_delta, "highs_lows_change": highs_lows_delta,
        "relative_strength": strength, "relative_momentum": momentum, "concentration": concentration,
        "relative_strength_change": relative_strength_change, "relative_momentum_change": momentum_change,
    }
    alerts = []
    for rule_id, direction, matches, explanation in candidates:
        if not matches:
            continue
        severity = _severity(rule_id, evidence)
        stable = f"{item['type']}:{item['id']}:{rule_id}:{latest.get('market_date') or item.get('freshness', {}).get('as_of')}"
        alerts.append({
            "id": hashlib.sha256(stable.encode()).hexdigest()[:20],
            "rule_id": rule_id,
            "entity": {"id": item["id"], "type": item["type"], "name": item["name"]},
            "direction": direction,
            "severity": severity,
            "detected_at": latest.get("market_date") or item.get("freshness", {}).get("as_of"),
            "evidence": {key: value for key, value in evidence.items() if value is not None},
            "explanation": explanation,
            "why_it_matters": "Confirmation has weakened; verify breadth and rotation before relying on the headline move.",
            "confirmation": "The divergence is confirmed if the internal trend persists in the next immutable snapshot.",
            "invalidation": "The divergence is invalidated if price and internals realign beyond the documented threshold.",
            "confidence": _alert_confidence(item, observations),
            "freshness": item.get("freshness"),
            "availability": item.get("availability"),
            "canonical_destination": item.get("canonical_destination"),
        })
    return sorted(alerts, key=lambda alert: ({"high": 0, "medium": 1, "low": 2}[alert["severity"]], alert["rule_id"], alert["id"]))


def build_sector_alerts(registry: dict[str, Any], sources: GroupSources) -> dict[str, Any]:
    type_map = {
        "sector_price_rising_participation_weakening": "breadth_deterioration",
        "price_up_breadth_down": "breadth_deterioration",
        "price_down_breadth_up": "rotation_acceleration",
        "rotation_leading_momentum_fading": "momentum_reversal",
        "rotation_improving_price_weak": "rotation_acceleration",
        "price_up_ad_down": "breadth_deterioration",
        "price_up_highs_lows_down": "breadth_deterioration",
        "rank_improvement_without_persistence": "persistence_loss",
        "momentum_improvement_relative_trend_weak": "rotation_acceleration",
        "leadership_concentrated": "concentration_warning",
    }
    items = []
    for item in registry.get("items", []):
        history = build_breadth_history("sector", item["id"], sources, "3M")
        for divergence in detect_divergences(item, history["observations"]):
            alert_type = type_map[divergence["rule_id"]]
            items.append({**divergence, "type": alert_type, "group": _alert_group(alert_type)})
        if item["movement"]["recent_transition"]:
            alert_type = _transition_type(item["state"])
            stable = f"sector:{item['id']}:{alert_type}:{item['freshness']['as_of']}"
            items.append({
                "id": hashlib.sha256(stable.encode()).hexdigest()[:20], "type": alert_type,
                "group": _alert_group(alert_type), "entity": {"id": item["id"], "type": "sector", "name": item["name"]},
                "direction": "positive" if alert_type in {"entered_leading", "entered_improving", "rotation_acceleration"} else "negative",
                "severity": "medium", "detected_at": item["freshness"]["as_of"],
                "evidence": {"previous_state": item["movement"]["previous_state"], "current_state": item["state"], "rank_change": item["rank_change"]},
                "explanation": f"{item['name']} changed from {item['movement']['previous_state']} to {item['state']}.",
                "why_it_matters": "A canonical state transition can change leadership monitoring priority.",
                "confirmation": "Confirm with the next immutable snapshot and supporting breadth.",
                "invalidation": "Invalidate if the entity returns to its prior state on the next snapshot.",
                "confidence": item["confidence"]["signal"], "freshness": item["freshness"], "availability": item["availability"],
                "canonical_destination": item["canonical_destination"],
            })
        if _gt(item.get("relative_strength"), 5) and _gt(item.get("rank_change"), 1):
            alert_type = "relative_strength_breakout"
            stable = f"sector:{item['id']}:{alert_type}:{item['freshness']['as_of']}"
            items.append({
                "id": hashlib.sha256(stable.encode()).hexdigest()[:20], "type": alert_type,
                "group": "momentum", "entity": {"id": item["id"], "type": "sector", "name": item["name"]},
                "direction": "positive", "severity": "medium", "detected_at": item["freshness"]["as_of"],
                "evidence": {"relative_strength": item["relative_strength"], "rank_change": item["rank_change"]},
                "explanation": f"{item['name']} relative strength and rank improved beyond the documented breakout threshold.",
                "why_it_matters": "A confirmed benchmark-relative breakout can alter leadership priority.",
                "confirmation": "Confirm if relative strength remains above 5 and the improved rank persists.",
                "invalidation": "Invalidate if relative strength falls to 5 or below or rank improvement reverses.",
                "confidence": item["confidence"]["signal"], "freshness": item["freshness"], "availability": item["availability"],
                "canonical_destination": item["canonical_destination"],
            })
    deduped = {item["id"]: item for item in items}
    ordered = sorted(deduped.values(), key=lambda item: ({"high": 0, "medium": 1, "low": 2}[item["severity"]], item["group"], item["entity"]["name"], item["id"]))
    return {
        "contract_version": "sector-alerts-v1", "snapshot_id": registry.get("snapshot_id"),
        "market_date": registry.get("market_date"), "status": "available" if ordered else "empty",
        "types": ["entered_leading", "exited_leading", "entered_improving", "breadth_deterioration", "momentum_reversal", "relative_strength_breakout", "persistence_loss", "rotation_acceleration", "concentration_warning"],
        "items": ordered, "count": len(ordered),
    }


def _normalize_row(entity_type: EntityType, row: dict[str, Any], snapshot: dict[str, Any], previous: dict[str, Any] | None, history: list[dict[str, Any]]) -> dict[str, Any]:
    entity_id = _entity_id(row, entity_type)
    state = str(row.get("classification") or row.get("leadership_state") or "Unavailable").lower()
    previous_state = str((previous or {}).get("classification") or (previous or {}).get("leadership_state") or "").lower() or None
    rank = _integer(row.get("rank"))
    previous_rank = _integer((previous or {}).get("rank"))
    performance = _performance(row, entity_type)
    breadth = _breadth(row, entity_type)
    freshness_state = _freshness_state(row, snapshot)
    availability = _availability(row, snapshot)
    confidence = {
        "data": _confidence(row.get("data_confidence") or row.get("confidence")),
        "signal": _confidence(row.get("signal_confidence") or row.get("confidence")),
    }
    item = {
        "id": entity_id, "type": entity_type,
        "name": str(row.get("display_name") or row.get("name") or entity_id),
        "parent": _parent(row, entity_type), "state": state, "quadrant": state if state in {"leading", "improving", "weakening", "lagging"} else "unavailable",
        "performance": performance,
        "relative_strength": _relative_strength(row, entity_type),
        "relative_momentum": _relative_momentum(row, entity_type),
        "breadth": breadth,
        "concentration": _concentration(row, entity_type),
        "persistence": _persistence(entity_id, entity_type, state, history),
        "rank": rank, "rank_change": previous_rank - rank if rank is not None and previous_rank is not None else None,
        "movement": {"direction": _movement(rank, previous_rank), "recent_transition": bool(previous_state and previous_state != state), "previous_state": previous_state},
        "confidence": confidence,
        "freshness": {"state": freshness_state, "as_of": snapshot.get("market_date"), "generated_at": snapshot.get("generated_at") or snapshot.get("published_at")},
        "availability": availability,
        "canonical_destination": {"route": "/sectors", "params": {"entityKind": entity_type, "entityId": entity_id}},
        "evidence": {"snapshot_id": snapshot.get("snapshot_id"), "input_hash": row.get("input_hash") or snapshot.get("input_hash")},
    }
    return item


def _rows(snapshot: dict[str, Any] | None, entity_type: EntityType) -> list[dict[str, Any]]:
    if not snapshot: return []
    value = snapshot.get("sectors") if entity_type == "sector" else snapshot.get("rows") or snapshot.get("items")
    return [item for item in (value or []) if isinstance(item, dict)]


def _entity_id(row: dict[str, Any], entity_type: EntityType) -> str:
    return str(row.get("sector_id" if entity_type == "sector" else "theme_id") or row.get("id") or "").strip()


def _performance(row: dict[str, Any], entity_type: EntityType) -> dict[str, float | None]:
    source = row.get("price_metrics") if entity_type == "sector" else row.get("performance") or row.get("returns")
    source = source if isinstance(source, dict) else {}
    return {label: _first_number(source, *keys) for label, keys in PERFORMANCE_KEYS.items()}


def _breadth(row: dict[str, Any], entity_type: EntityType) -> dict[str, float | None]:
    source = row.get("breadth_metrics") if entity_type == "sector" else row.get("breadth")
    source = source if isinstance(source, dict) else {}
    highs = _first_number(source, "new_52_week_highs", "new_highs")
    lows = _first_number(source, "new_52_week_lows", "new_lows")
    return {
        "above_20": _first_number(source, "percent_above_ema20", "percent_above_20_day_average"),
        "above_50": _first_number(source, "percent_above_ema50", "percent_above_50_day_average"),
        "above_200": _first_number(source, "percent_above_ema200", "percent_above_200_day_average"),
        "advance_decline_ratio": _first_number(source, "advance_decline_ratio"),
        "advancing": _first_number(source, "advancing"), "declining": _first_number(source, "declining"),
        "new_highs": highs, "new_lows": lows,
        "highs_minus_lows": highs - lows if highs is not None and lows is not None else None,
    }


def _relative_strength(row: dict[str, Any], entity_type: EntityType) -> float | None:
    source = row.get("relative_strength_metrics") if entity_type == "sector" else row.get("relative_strength")
    source = source if isinstance(source, dict) else {}
    primary = _first_number(source, "vs_spy_1m", "vs_spy_3m", "vs_spy", "relative_strength")
    return primary if primary is not None else _first_number(row.get("component_scores") or {}, "relative_strength")


def _relative_momentum(row: dict[str, Any], entity_type: EntityType) -> float | None:
    source = row.get("relative_strength") if entity_type == "theme" else {}
    source = source if isinstance(source, dict) else {}
    primary = _first_number(source, "momentum", "relative_momentum")
    return primary if primary is not None else _first_number(row.get("component_scores") or {}, "momentum")


def _concentration(row: dict[str, Any], entity_type: EntityType) -> float | None:
    source = row.get("participation_metrics") if entity_type == "sector" else row.get("concentration")
    source = source if isinstance(source, dict) else {}
    return _first_number(source, "top_contributor_concentration", "top_3_contribution_percent", "top_three_contribution_percent")


def _parent(row: dict[str, Any], entity_type: EntityType) -> str | None:
    if entity_type == "sector": return None
    definition = row.get("definition") if isinstance(row.get("definition"), dict) else {}
    return _text(row.get("parent_sector") or row.get("parentSector") or definition.get("parent_sector"))


def _availability(row: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    explicit = str(row.get("status") or row.get("coverage_status") or "").lower()
    state = explicit if explicit in {"available", "partial", "unavailable", "stale", "failed"} else "available" if str(row.get("classification", "")).lower() != "unavailable" else "unavailable"
    warnings = list(row.get("warnings") or [])
    return {"state": state, "reason": warnings[0] if warnings else None, "source_state": snapshot.get("source_state", "unavailable")}


def _freshness_state(row: dict[str, Any], snapshot: dict[str, Any]) -> str:
    freshness = row.get("freshness")
    if isinstance(freshness, dict): return str(freshness.get("state") or freshness.get("status") or "unknown").lower()
    if isinstance(freshness, str): return freshness.lower()
    return "current" if snapshot.get("market_date") else "unavailable"


def _confidence(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return {"label": str(value.get("label") or "Unavailable"), "score": _number(value.get("score")), "reason": value.get("reason")}
    return {"label": str(value or "Unavailable").title(), "score": None, "reason": None}


def _persistence(entity_id: str, entity_type: EntityType, state: str, history: list[dict[str, Any]]) -> dict[str, Any]:
    count = 0
    for snapshot in reversed(history):
        row = next((item for item in _rows(snapshot, entity_type) if _entity_id(item, entity_type) == entity_id), None)
        row_state = str((row or {}).get("classification") or (row or {}).get("leadership_state") or "").lower()
        if row_state != state: break
        count += 1
    return {"state": state, "snapshot_count": count, "available": count > 0}


def _breadth_interpretation(observations: list[dict[str, Any]]) -> dict[str, Any]:
    if len(observations) < 2:
        return {"state": "unavailable", "conclusion": "At least two published snapshots are required for a breadth trend.", "evidence": [], "confidence": "unavailable", "freshness": observations[-1].get("market_date") if observations else None}
    first, latest = observations[0], observations[-1]
    deltas = {key: _delta(first.get(key), latest.get(key)) for key in ("above_20", "above_50", "above_200", "advance_decline_ratio", "highs_minus_lows")}
    usable = {key: value for key, value in deltas.items() if value is not None}
    improving = sum(value > 0.5 for value in usable.values())
    weakening = sum(value < -0.5 for value in usable.values())
    if improving == weakening == 0:
        state = "stable"
    elif improving > weakening:
        state = "expanding"
    elif weakening > improving:
        state = "weakening"
    else:
        state = "diverging"
    return {
        "state": state,
        "conclusion": f"Breadth is {state} across {len(usable)} available internal measures.",
        "evidence": [{"metric": key, "change": value, "from": first.get(key), "to": latest.get(key)} for key, value in usable.items()],
        "confidence": "high" if len(usable) >= 5 and len(observations) >= 6 else "moderate" if len(usable) >= 3 else "low",
        "freshness": latest.get("market_date"),
    }


def _model_versions(snapshot: dict[str, Any], entity_type: EntityType) -> dict[str, Any]:
    provenance = snapshot.get("provider_provenance") if isinstance(snapshot.get("provider_provenance"), dict) else {}
    return {
        "snapshot_schema": snapshot.get("schema_version"),
        "formula": snapshot.get("formula_version") or ("sector-composite-v1" if entity_type == "sector" else None),
        "rotation": provenance.get("rotation_model_version") or "theme-relative-trend-momentum-v1" if entity_type == "theme" else provenance.get("rotation_model_version"),
        "contract": "group-intelligence-v1",
    }


def _response_status(items: list[dict[str, Any]]) -> str:
    if not items: return "unavailable"
    states = {item["availability"]["state"] for item in items}
    return "available" if states == {"available"} else "partial"


def _unavailable_registry(entity_type: EntityType, reason: str) -> dict[str, Any]:
    return {"contract_version": "group-intelligence-v1", "entity_type": entity_type, "snapshot_id": None, "market_date": None, "source_state": "unavailable", "status": "unavailable", "model_versions": {"contract": "group-intelligence-v1"}, "items": [], "count": 0, "warnings": [reason]}


def _severity(rule_id: str, evidence: dict[str, Any]) -> str:
    magnitude = sum(abs(value) for value in evidence.values() if isinstance(value, (int, float)))
    threshold = 180 if rule_id == "leadership_concentrated" else 135
    return "high" if magnitude >= threshold else "medium" if magnitude >= threshold * 0.55 else "low"


def _alert_confidence(item: dict[str, Any], observations: list[dict[str, Any]]) -> dict[str, Any]:
    base = item.get("confidence", {}).get("signal", {})
    return {"label": base.get("label", "Unavailable"), "score": base.get("score"), "observation_count": len(observations)}


def _alert_group(alert_type: str) -> str:
    if alert_type in {"entered_leading", "exited_leading", "entered_improving"}: return "leadership"
    if alert_type in {"momentum_reversal", "relative_strength_breakout", "rotation_acceleration"}: return "momentum"
    if alert_type == "breadth_deterioration": return "breadth"
    return "risk"


def _transition_type(state: str) -> str:
    if state == "leading": return "entered_leading"
    if state in {"weakening", "lagging"}: return "exited_leading"
    if state == "improving": return "entered_improving"
    return "momentum_reversal"


def _movement(rank: int | None, previous_rank: int | None) -> str:
    if rank is None or previous_rank is None: return "unavailable"
    change = previous_rank - rank
    return "gaining" if change > 0 else "losing" if change < 0 else "stable"


def _first_number(value: Any, *keys: str) -> float | None:
    if not isinstance(value, dict): return None
    for key in keys:
        number = _number(value.get(key))
        if number is not None: return number
    return None


def _number(value: Any) -> float | None:
    if isinstance(value, bool): return None
    if isinstance(value, (int, float)) and value == value: return float(value)
    if isinstance(value, str):
        try: return float(value.replace("%", "").replace(",", "").strip())
        except ValueError: return None
    return None


def _integer(value: Any) -> int | None:
    number = _number(value)
    return int(number) if number is not None else None


def _text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _bool(value: Any) -> bool:
    return value is True or (isinstance(value, str) and value.lower() in {"true", "1", "yes"})


def _delta(first: Any, latest: Any) -> float | None:
    left, right = _number(first), _number(latest)
    return round(right - left, 4) if left is not None and right is not None else None


def _gt(value: Any, threshold: float) -> bool:
    number = _number(value); return number is not None and number > threshold


def _lt(value: Any, threshold: float) -> bool:
    number = _number(value); return number is not None and number < threshold
