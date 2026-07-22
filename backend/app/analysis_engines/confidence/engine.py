from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from app.analysis_engines.freshness import CONSTRAINED_FRESHNESS_STATES


CONFIDENCE_ENGINE_VERSION = "confidence-adjustment-v1"

ConfidenceLabel = Literal["high", "moderate", "limited"]
ConfidenceEffect = Literal["set", "cap", "none"]


@dataclass(frozen=True)
class ConfidenceAdjustmentInput:
    intent: str
    evidence_count: int
    freshness_state: str
    missing_evidence_count: int = 0
    stale_count: int = 0
    partial_count: int = 0
    unavailable_count: int = 0
    test_count: int = 0
    contradiction_count: int = 0
    unsupported_dimension_count: int = 0
    fallback_used: bool = False
    source_quality: str | None = None
    exempt_from_market_evidence: bool = False


@dataclass(frozen=True)
class ConfidenceRuleContribution:
    rule: str
    effect: ConfidenceEffect
    resulting_cap: ConfidenceLabel | None
    reason: str


@dataclass(frozen=True)
class ConfidenceAdjustmentResult:
    label: ConfidenceLabel
    maximum_allowed: ConfidenceLabel
    constrained: bool
    contributions: tuple[ConfidenceRuleContribution, ...] = field(default_factory=tuple)
    engine_version: str = CONFIDENCE_ENGINE_VERSION


class ConfidenceAdjustmentEngine:
    """Apply explicit Stage 7 confidence rules and expose every cap."""

    version = CONFIDENCE_ENGINE_VERSION

    def adjust(self, value: ConfidenceAdjustmentInput) -> ConfidenceAdjustmentResult:
        contributions: list[ConfidenceRuleContribution] = []
        constrained = self.is_constrained(value)

        if value.exempt_from_market_evidence:
            contributions.append(
                ConfidenceRuleContribution(
                    rule="non_market_deterministic",
                    effect="set",
                    resulting_cap="high",
                    reason="Navigation and bounded education do not make market-data claims.",
                )
            )
            return ConfidenceAdjustmentResult(
                label="high",
                maximum_allowed="high",
                constrained=False,
                contributions=tuple(contributions),
            )

        if constrained:
            contributions.append(
                ConfidenceRuleContribution(
                    rule="freshness_availability_cap",
                    effect="cap",
                    resulting_cap="limited",
                    reason=(
                        "Stale, partial, mixed, test, unavailable, or fallback evidence "
                        "cannot receive unrestricted confidence."
                    ),
                )
            )
        if value.missing_evidence_count or value.unsupported_dimension_count:
            contributions.append(
                ConfidenceRuleContribution(
                    rule="missing_dimension_cap",
                    effect="cap",
                    resulting_cap="limited",
                    reason="Missing evidence or unsupported dimensions cap confidence.",
                )
            )
        if value.evidence_count <= 0:
            contributions.append(
                ConfidenceRuleContribution(
                    rule="no_evidence_cap",
                    effect="cap",
                    resulting_cap="limited",
                    reason="No factual evidence is available.",
                )
            )
        if value.contradiction_count:
            contributions.append(
                ConfidenceRuleContribution(
                    rule="contradiction_preserved",
                    effect="none",
                    resulting_cap=None,
                    reason=(
                        "Contradictions remain explicit; Stage 7 does not apply a hidden "
                        "numeric penalty beyond its existing constrained-state rules."
                    ),
                )
            )

        limited = bool(
            constrained
            or value.missing_evidence_count
            or value.unsupported_dimension_count
            or value.evidence_count <= 0
        )
        if limited:
            label: ConfidenceLabel = "limited"
            maximum: ConfidenceLabel = "limited"
        elif value.evidence_count >= 3:
            label = "moderate"
            maximum = "moderate"
            contributions.append(
                ConfidenceRuleContribution(
                    rule="evidence_depth",
                    effect="set",
                    resulting_cap="moderate",
                    reason="At least three validated evidence items support moderate confidence.",
                )
            )
        else:
            label = "limited"
            maximum = "limited"
            contributions.append(
                ConfidenceRuleContribution(
                    rule="limited_evidence_depth",
                    effect="cap",
                    resulting_cap="limited",
                    reason="Fewer than three evidence items keep confidence limited.",
                )
            )
        return ConfidenceAdjustmentResult(
            label=label,
            maximum_allowed=maximum,
            constrained=constrained,
            contributions=tuple(contributions),
        )

    @staticmethod
    def is_constrained(value: ConfidenceAdjustmentInput) -> bool:
        return bool(
            value.freshness_state in CONSTRAINED_FRESHNESS_STATES
            or value.stale_count
            or value.partial_count
            or value.unavailable_count
            or value.test_count
            or value.fallback_used
        )

    @staticmethod
    def label_exceeds(label: str, maximum: ConfidenceLabel) -> bool:
        rank = {"limited": 0, "moderate": 1, "high": 2}
        return rank.get(label, 3) > rank[maximum]
