from __future__ import annotations

from typing import Any


SEMANTICS_VERSION = "market-semantics-v1"
ADVANCE_DECLINE_SMOOTHING_ALPHA = 0.5


def advance_decline_semantics(advancing: int, declining: int, *, alpha: float = ADVANCE_DECLINE_SMOOTHING_ALPHA) -> dict[str, Any]:
    """Return explicit raw, display, and scoring-safe A/D values.

    The raw ratio remains undefined when its denominator is zero.  Consumers
    that need a finite comparison value must opt into the separately labelled
    Laplace-smoothed field.
    """
    raw = round(advancing / declining, 4) if declining > 0 else None
    if declining == 0 and advancing > 0:
        display = "No decliners"
    elif declining == 0:
        display = "N/A"
    else:
        display = f"{raw:.2f}" if raw is not None else "N/A"
    return {
        "advance_decline_ratio": raw,
        "advance_decline_ratio_display": display,
        "advance_decline_ratio_smoothed": round((advancing + alpha) / (declining + alpha), 4),
        "ratio_method": f"raw=advancing/declining; smoothed=(advancing+{alpha})/(declining+{alpha})",
    }


def coverage_dimension(eligible: int, total: int) -> dict[str, Any]:
    ratio = round(eligible / total, 6) if total else 0.0
    return {"eligible": eligible, "total": total, "ratio": ratio, "display": f"{eligible}/{total}"}


def confidence_contract(*, data_score: float | None, data_reason: str, signal_score: float | None, signal_reason: str) -> dict[str, dict[str, Any]]:
    return {
        "data_confidence": {
            "score": round(data_score) if data_score is not None else None,
            "label": confidence_label(data_score),
            "reason": data_reason,
        },
        "signal_confidence": {
            "score": round(signal_score) if signal_score is not None else None,
            "label": confidence_label(signal_score),
            "reason": signal_reason,
        },
    }


def confidence_with_snapshot_provenance(
    confidence: dict[str, Any] | None,
    *,
    source_snapshot_id: str | None,
    calculated_at: str | None,
    unavailable_reason: str = "Insufficient historical breadth snapshots",
) -> dict[str, Any]:
    """Attach immutable snapshot context without changing the calculated score."""
    value = dict(confidence or {})
    if value.get("score") is None:
        value.setdefault("label", "Unavailable")
        value["reason"] = value.get("reason") or unavailable_reason
    value["source_snapshot_id"] = source_snapshot_id
    value["calculated_at"] = calculated_at
    return value


def confidence_label(score: float | None) -> str:
    if score is None:
        return "Unavailable"
    if score >= 80:
        return "High"
    if score >= 60:
        return "Moderate"
    if score >= 40:
        return "Mixed"
    return "Limited"
