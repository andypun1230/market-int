from __future__ import annotations

from typing import Any


THEME_INTELLIGENCE_UNAVAILABLE_REASON = (
    "Live Theme Intelligence is unavailable until reviewed membership, durable history, and a ThemeSnapshot are published."
)


def static_strategy_preference_provenance(as_of: str | None = None) -> dict[str, Any]:
    """Describe configured industry baskets without treating them as live themes."""
    return {
        "category": "static_strategy_preference",
        "label": "Static strategy preference",
        "data_mode": "unverified_strategy_basket",
        "is_live_theme_intelligence": False,
        "verified": False,
        "source": "configured industry-group basket",
        "snapshot_id": None,
        "last_updated": as_of,
        "reason": THEME_INTELLIGENCE_UNAVAILABLE_REASON,
    }


def is_live_theme_intelligence(provenance: object) -> bool:
    return isinstance(provenance, dict) and provenance.get("is_live_theme_intelligence") is True
