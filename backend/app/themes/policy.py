from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.themes.models import ThemeDefinition, ThemeMember


THEME_BASKET_FORMULA_VERSION = "equal-weight-current-basket-v1"
THEME_SCORING_FORMULA_VERSION = "theme-leadership-composite-v1"
THEME_PARTICIPATION_FORMULA_VERSION = "positive-return-and-contribution-v1"
THEME_SCORING_WEIGHTS = {
    "momentum": 0.25,
    "relative_strength": 0.25,
    "breadth": 0.20,
    "participation": 0.20,
    "concentration_quality": 0.10,
}


@dataclass(frozen=True)
class ThemePolicy:
    minimum_live_members: int = 3
    complete_coverage_threshold: float = 0.90
    partial_coverage_threshold: float = 0.75
    minimum_history_days: int = 200
    participation_lookback_sessions: int = 21
    basket_formula_version: str = THEME_BASKET_FORMULA_VERSION
    scoring_formula_version: str = THEME_SCORING_FORMULA_VERSION


def validate_definition(definition: ThemeDefinition, members: list[ThemeMember], *, require_reviewed: bool) -> list[str]:
    errors: list[str] = []
    if not definition.theme_id or not definition.version:
        errors.append("theme_id_and_version_required")
    if definition.minimum_members < 3:
        errors.append("minimum_members_must_be_at_least_three")
    if not 0 < definition.partial_coverage_threshold <= definition.complete_coverage_threshold <= 1:
        errors.append("invalid_coverage_thresholds")
    if definition.weighting_policy != "equal_weight_v1":
        errors.append("unsupported_weighting_policy")
    if definition.primary_benchmark != "SPY":
        errors.append("primary_benchmark_must_be_spy")
    if not definition.source_references:
        errors.append("source_references_required")
    if len(members) < definition.minimum_members:
        errors.append("minimum_member_count_not_met")
    if len({member.ticker.upper() for member in members if member.active}) != len([member for member in members if member.active]):
        errors.append("duplicate_active_member")
    if any(member.theme_id != definition.theme_id or member.theme_version != definition.version for member in members):
        errors.append("member_theme_version_mismatch")
    if any(not member.inclusion_reason.strip() for member in members):
        errors.append("member_inclusion_reason_required")
    active = [member for member in members if member.active]
    if active and abs(sum(member.weight for member in active) - 1.0) > 0.00001:
        errors.append("member_weights_must_sum_to_one")
    if require_reviewed:
        if definition.status not in {"reviewed", "active"}:
            errors.append("definition_not_reviewed")
        if not definition.reviewed_at or not definition.reviewed_by:
            errors.append("human_review_metadata_required")
        if any(not member.reviewed_at or not member.reviewed_by for member in active):
            errors.append("member_review_metadata_required")
    return errors


def live_definition_allowed(definition: ThemeDefinition, members: list[ThemeMember]) -> bool:
    return not validate_definition(definition, members, require_reviewed=True) and definition.status == "active"


def coverage_status(coverage_ratio: float, policy: ThemePolicy | None = None) -> str:
    current = policy or ThemePolicy()
    if coverage_ratio >= current.complete_coverage_threshold:
        return "complete"
    if coverage_ratio >= current.partial_coverage_threshold:
        return "partial"
    return "unavailable"


def representativeness(eligible_count: int) -> dict[str, str]:
    if eligible_count >= 10:
        return {"label": "High", "reason": f"{eligible_count} eligible constituents meet the 10-member threshold."}
    if eligible_count >= 4:
        return {"label": "Moderate", "reason": f"{eligible_count} eligible constituents meet the 4-member threshold."}
    return {"label": "Limited", "reason": f"Only {eligible_count} eligible constituent(s) are available."}


def score_classification(relative_strength: float | None, momentum: float | None, breadth: float | None, participation: float | None) -> str:
    if None in {relative_strength, momentum, breadth, participation}:
        return "Unavailable"
    assert relative_strength is not None and momentum is not None and breadth is not None and participation is not None
    if relative_strength >= 55 and momentum >= 55 and breadth >= 55 and participation >= 55:
        return "Leading"
    if relative_strength >= 50 and (momentum >= 55 or breadth >= 55):
        return "Improving"
    if relative_strength <= 45 and momentum <= 45 and (breadth <= 45 or participation <= 45):
        return "Lagging"
    if momentum <= 45 or breadth <= 45:
        return "Weakening"
    return "Neutral"


def clip_score(value: float | None) -> float | None:
    return round(max(0.0, min(100.0, value)), 2) if value is not None else None
