from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


CONTRADICTION_ENGINE_VERSION = "contradiction-preservation-v1"

Polarity = Literal["positive", "negative", "neutral"]

NEGATIVE_TERMS: frozenset[str] = frozenset(
    {
        "avoid",
        "bearish",
        "below",
        "cautious",
        "defensive",
        "deteriorating",
        "deterioration",
        "elevated risk",
        "failed",
        "fragile",
        "high risk",
        "lagging",
        "missing",
        "negative",
        "narrow",
        "not confirmed",
        "partial",
        "risk-off",
        "stale",
        "unavailable",
        "unconfirmed",
        "weak",
        "weakening",
    }
)
POSITIVE_TERMS: frozenset[str] = frozenset(
    {
        "above",
        "bullish",
        "confirmed",
        "constructive",
        "healthy",
        "improving",
        "leading",
        "low risk",
        "outperforming",
        "positive",
        "risk-on",
        "strong",
        "strengthening",
    }
)


@dataclass(frozen=True)
class ContradictionFinding:
    evidence_id: str
    statement: str
    interpretation_class: str = "observed_fact"
    contradicts_claim_ids: tuple[str, ...] = field(default_factory=tuple)
    explicitly_opposing: bool = False
    preferred_support: bool = False
    watchlist_caution: bool = False
    priority_support: bool = False


@dataclass(frozen=True)
class ContradictionAnalysisInput:
    findings: tuple[ContradictionFinding, ...]
    prefer_declared_support: bool = True


@dataclass(frozen=True)
class ContradictionAnalysisResult:
    supporting_evidence_ids: tuple[str, ...]
    opposing_evidence_ids: tuple[str, ...]
    neutral_evidence_ids: tuple[str, ...]
    polarity_by_evidence_id: dict[str, Polarity]
    engine_version: str = CONTRADICTION_ENGINE_VERSION


@dataclass(frozen=True)
class ContradictionPreservationInput:
    expected_evidence_ids: tuple[str, ...]
    cited_evidence_ids: tuple[str, ...]
    truncation_disclosed: bool
    fail_closed_no_claim: bool = False


@dataclass(frozen=True)
class ContradictionPreservationResult:
    valid: bool
    preserved_evidence_ids: tuple[str, ...]
    omitted_evidence_ids: tuple[str, ...]
    reason: str | None
    engine_version: str = CONTRADICTION_ENGINE_VERSION


class ContradictionEngine:
    """Classify structured findings while preserving disagreement and absence."""

    version = CONTRADICTION_ENGINE_VERSION

    def analyze(self, value: ContradictionAnalysisInput) -> ContradictionAnalysisResult:
        positive: list[str] = []
        neutral: list[str] = []
        opposing: list[str] = []
        preferred = {item.evidence_id for item in value.findings if item.preferred_support}
        polarity_by_id: dict[str, Polarity] = {}

        for item in value.findings:
            polarity = self.polarity(item.statement)
            polarity_by_id.setdefault(item.evidence_id, polarity)
            if self.is_explicit_contradiction(
                interpretation_class=item.interpretation_class,
                contradicts_claim_ids=item.contradicts_claim_ids,
            ) or item.explicitly_opposing or item.watchlist_caution:
                opposing.append(item.evidence_id)
            elif polarity == "negative":
                opposing.append(item.evidence_id)
            elif polarity == "positive":
                positive.append(item.evidence_id)
            else:
                neutral.append(item.evidence_id)

        ordered_support = [*positive, *neutral]
        if value.prefer_declared_support and preferred:
            declared = [item for item in ordered_support if item in preferred]
            if declared:
                ordered_support = declared
        priority = {
            item.evidence_id for item in value.findings if item.priority_support
        }
        if priority:
            ordered_support = [
                *[item for item in ordered_support if item in priority],
                *[item for item in ordered_support if item not in priority],
            ]
        return ContradictionAnalysisResult(
            supporting_evidence_ids=self._dedupe(ordered_support),
            opposing_evidence_ids=self._dedupe(opposing),
            neutral_evidence_ids=self._dedupe(neutral),
            polarity_by_evidence_id=polarity_by_id,
        )

    def validate_preservation(
        self,
        value: ContradictionPreservationInput,
    ) -> ContradictionPreservationResult:
        if value.fail_closed_no_claim:
            return ContradictionPreservationResult(
                valid=True,
                preserved_evidence_ids=(),
                omitted_evidence_ids=(),
                reason=None,
            )
        expected = set(value.expected_evidence_ids)
        cited = set(value.cited_evidence_ids)
        preserved = expected.intersection(cited)
        omitted = expected - cited
        if expected and not preserved:
            return ContradictionPreservationResult(
                valid=False,
                preserved_evidence_ids=(),
                omitted_evidence_ids=tuple(
                    item for item in value.expected_evidence_ids if item in omitted
                ),
                reason="no_contradiction_preserved",
            )
        if omitted and not value.truncation_disclosed:
            return ContradictionPreservationResult(
                valid=False,
                preserved_evidence_ids=tuple(
                    item for item in value.expected_evidence_ids if item in preserved
                ),
                omitted_evidence_ids=tuple(
                    item for item in value.expected_evidence_ids if item in omitted
                ),
                reason="truncation_not_disclosed",
            )
        return ContradictionPreservationResult(
            valid=True,
            preserved_evidence_ids=tuple(
                item for item in value.expected_evidence_ids if item in preserved
            ),
            omitted_evidence_ids=tuple(
                item for item in value.expected_evidence_ids if item in omitted
            ),
            reason=None,
        )

    @staticmethod
    def is_explicit_contradiction(
        *,
        interpretation_class: str,
        contradicts_claim_ids: tuple[str, ...] | list[str] = (),
    ) -> bool:
        return bool(
            contradicts_claim_ids or interpretation_class == "contradiction"
        )

    @staticmethod
    def polarity(statement: str) -> Polarity:
        lowered = statement.casefold()
        negative = any(term in lowered for term in NEGATIVE_TERMS)
        positive = any(term in lowered for term in POSITIVE_TERMS)
        if negative and not positive:
            return "negative"
        if positive and not negative:
            return "positive"
        return "neutral"

    @staticmethod
    def _dedupe(values: list[str]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(values))
