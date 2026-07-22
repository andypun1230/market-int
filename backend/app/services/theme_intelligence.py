from __future__ import annotations

from typing import Any

from app.theme_snapshots.service import get_theme_snapshot_service


UNAVAILABLE_MESSAGE = "Live Theme Intelligence is not yet available."
DECISION_THEME_POLICY = {
    "minimum_coverage_ratio": 0.90,
    "minimum_absolute_composite_score": 70.0,
    "minimum_signal_confidence": 70.0,
    "required_classification": "Leading",
    "disallowed_concentration": {"elevated", "high"},
}


def build_theme_intelligence_context() -> dict[str, Any]:
    """Expose one immutable ThemeSnapshot summary to cross-screen consumers.

    This adapter deliberately never derives a theme from static preferences or
    request-time market data. A consumer either receives the published durable
    snapshot or the explicit review-gate state.
    """
    service = get_theme_snapshot_service()
    snapshot = service.latest()
    if snapshot is None or snapshot.source_state != "live":
        status = service.status()
        return {
            "available": False,
            "availability": UNAVAILABLE_MESSAGE,
            "snapshot_id": None,
            "market_date": None,
            "source_state": "unavailable",
            "reason": status.get("reason") or "no_reviewed_active_theme_definitions",
            "items": [],
            "warnings": [UNAVAILABLE_MESSAGE],
        }

    rows = list(snapshot.rows)
    leaders = [leader_summary(row) for row in rows[:3]]
    decision_signals = [decision_theme_signal(snapshot, row) for row in rows]
    qualified = [signal for signal in decision_signals if signal["qualified"]]
    return {
        "available": True,
        "availability": "Reviewed live Theme Intelligence from the published ThemeSnapshot.",
        "snapshot_id": snapshot.snapshot_id,
        "market_date": snapshot.market_date,
        "generated_at": snapshot.generated_at,
        "source_state": snapshot.source_state,
        "status": snapshot.status,
        "formula_version": snapshot.formula_version,
        "leaders": leaders,
        "items": rows,
        "overlap_matrix": list(snapshot.overlap_matrix),
        "decision_theme_signals": decision_signals,
        "qualified_decision_theme_signals": qualified,
        # Static preferences are owned by the Decision playbook. They are not
        # manufactured from a Theme row that happens not to clear its live gate.
        "live_theme_signal_overrides_static_preferences": [signal["display_name"] for signal in qualified],
        "pilot_scope": {
            "active_reviewed_theme_count": len(rows),
            "rank_scope": f"Rank reflects the leadership composite among the {len(rows)} currently active reviewed pilot themes.",
            "proposed_inactive_themes_excluded": True,
        },
        "warnings": list(snapshot.warnings),
        "historical_disclosure": "Historical results use the current reviewed constituent basket unless historical membership versions are available.",
    }


def leader_summary(row: dict[str, Any]) -> dict[str, Any]:
    score = row.get("score_semantics") if isinstance(row.get("score_semantics"), dict) else {}
    return {
        "theme_id": row.get("theme_id"),
        "display_name": row.get("display_name"),
        "rank": row.get("rank"),
        "composite_score": row.get("composite_score"),
        "absolute_composite_score": row.get("composite_score"),
        "score_semantics": score,
        "classification": row.get("classification"),
        "performance": row.get("performance", {}),
        "relative_strength": row.get("relative_strength", {}),
        "breadth": row.get("breadth", {}),
        "participation": row.get("participation", {}),
        "concentration": row.get("concentration", {}),
        "coverage_ratio": row.get("coverage_ratio"),
        "representativeness": row.get("representativeness", {}),
        "definition_version": row.get("version"),
        "parent_sector_labels": (row.get("definition") or {}).get("parent_sector_labels", []),
        "pilot_scope": row.get("pilot_scope", {}),
    }


def decision_theme_signal(snapshot: Any, row: dict[str, Any]) -> dict[str, Any]:
    coverage = float(row.get("coverage_ratio") or 0)
    score = row.get("composite_score")
    confidence = ((row.get("signal_confidence") or {}).get("score"))
    classification = row.get("classification")
    concentration = ((row.get("concentration") or {}).get("classification") or "unavailable").lower()
    data_confidence = ((row.get("data_confidence") or {}).get("score"))
    reasons: list[str] = []
    failures: list[str] = []
    if snapshot.status in {"complete", "partial"}:
        reasons.append("published live ThemeSnapshot")
    else:
        failures.append("snapshot status is not publishable")
    if coverage >= DECISION_THEME_POLICY["minimum_coverage_ratio"]:
        reasons.append(f"coverage {coverage:.0%} meets the {DECISION_THEME_POLICY['minimum_coverage_ratio']:.0%} gate")
    else:
        failures.append(f"coverage {coverage:.0%} is below the documented gate")
    if classification == DECISION_THEME_POLICY["required_classification"]:
        reasons.append("classification is Leading")
    else:
        failures.append(f"classification {classification or 'Unavailable'} does not meet the Leading gate")
    if isinstance(score, (int, float)) and score >= DECISION_THEME_POLICY["minimum_absolute_composite_score"]:
        reasons.append(f"absolute composite {score:.1f} meets the documented gate")
    else:
        failures.append("absolute composite score is below the documented gate")
    if isinstance(confidence, (int, float)) and confidence >= DECISION_THEME_POLICY["minimum_signal_confidence"]:
        reasons.append(f"signal confidence {confidence:.0f} meets the documented gate")
    else:
        failures.append("signal confidence is below the documented gate")
    if concentration not in DECISION_THEME_POLICY["disallowed_concentration"]:
        reasons.append(f"concentration is {concentration}")
    else:
        failures.append(f"concentration is {concentration}")
    if not isinstance(data_confidence, (int, float)) or data_confidence < 75:
        failures.append("data confidence is below the documented gate")
    else:
        reasons.append(f"data confidence {data_confidence:.0f} meets the documented gate")
    qualified = not failures
    return {
        "theme_id": row.get("theme_id"), "display_name": row.get("display_name"),
        # Provenance answers where the record came from; qualification answers
        # whether Decision may promote it. Do not recast an unqualified live row
        # as a static strategy preference.
        "source_type": "live_theme_signal",
        "qualified": qualified,
        "theme_snapshot_id": snapshot.snapshot_id,
        "rank": row.get("rank"), "classification": classification, "score": score,
        "coverage": coverage, "signal_confidence": confidence, "data_confidence": data_confidence,
        "concentration_classification": concentration,
        "qualification_reason": "; ".join(reasons) if qualified else None,
        "disqualification_reason": "; ".join(failures) if failures else None,
        "policy": {**DECISION_THEME_POLICY, "disallowed_concentration": sorted(DECISION_THEME_POLICY["disallowed_concentration"])},
    }


def enrich_copilot_theme_context(message: str, context: dict[str, Any]) -> dict[str, Any]:
    """Attach the deterministic current Theme row when a request resolves to it."""
    live = build_theme_intelligence_context()
    if not live.get("available"):
        return context
    candidate = find_theme_row(message, context, live.get("items") or [])
    if candidate is None:
        return context
    focused = {
        "name": candidate.get("display_name"), "theme_id": candidate.get("theme_id"),
        "snapshot_id": live.get("snapshot_id"), "market_date": live.get("market_date"),
        "definition_version": candidate.get("version"), "rank": candidate.get("rank"),
        "classification": candidate.get("classification"), "absolute_composite_score": candidate.get("composite_score"),
        "performance": candidate.get("performance", {}), "relative_strength": candidate.get("relative_strength", {}),
        "breadth": candidate.get("breadth", {}), "participation": candidate.get("participation", {}),
        "concentration": candidate.get("concentration", {}), "coverage_ratio": candidate.get("coverage_ratio"),
        "signal_confidence": candidate.get("signal_confidence", {}), "data_confidence": candidate.get("data_confidence", {}),
        "representativeness": candidate.get("representativeness", {}), "members": candidate.get("members", []),
        "warnings": candidate.get("warnings", []), "basket_methodology": candidate.get("basket_methodology", {}),
        "score_semantics": candidate.get("score_semantics", {}),
        "top_contributors": (candidate.get("concentration") or {}).get("top_contributors", []),
        "invalidation_conditions": [
            "Relative strength, breadth, participation, or concentration no longer confirms the Theme signal.",
            "A future immutable ThemeSnapshot revises the reviewed live evidence.",
        ],
        "parent_sector_labels": (candidate.get("definition") or {}).get("parent_sector_labels", []),
        "overlap": [item for item in live.get("overlap_matrix", []) if candidate.get("theme_id") in {item.get("left_theme_id"), item.get("right_theme_id")}],
    }
    enriched = dict(context)
    enriched["sourceState"] = "live"
    enriched["theme"] = {"snapshot_id": live.get("snapshot_id"), "market_date": live.get("market_date"), "source_state": "live", "focused": focused, "themes": [leader_summary(row) for row in live.get("items", [])]}
    return enriched


def find_theme_row(message: str, context: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    candidates = [message.lower()]
    theme_context = context.get("theme") if isinstance(context.get("theme"), dict) else {}
    for key in ("theme_id", "id", "name", "display_name"):
        value = theme_context.get(key)
        if isinstance(value, str):
            candidates.append(value.lower())
    focused = theme_context.get("focused") if isinstance(theme_context.get("focused"), dict) else {}
    for key in ("theme_id", "id", "name", "display_name"):
        value = focused.get(key)
        if isinstance(value, str):
            candidates.append(value.lower())
    for row in rows:
        theme_id = str(row.get("theme_id") or "").lower()
        display = str(row.get("display_name") or "").lower()
        aliases = {theme_id, theme_id.replace("_", " "), display}
        if any(alias and any(alias in candidate for candidate in candidates) for alias in aliases):
            return row
    if "this theme" in message.lower() and len(rows) == 1:
        return rows[0]
    return None
