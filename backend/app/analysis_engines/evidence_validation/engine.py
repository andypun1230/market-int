from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Generic, Iterable, TypeVar


EVIDENCE_VALIDATION_ENGINE_VERSION = "evidence-validation-v1"

T = TypeVar("T")

METRIC_FAMILY_PATTERNS: dict[str, tuple[str, ...]] = {
    "price": ("price", "close", "support", "resistance", "breakout", "trigger", "level"),
    "rsi": ("rsi",),
    "moving_average": ("ema", "sma", "moving average"),
    "return": ("return", "performance", "gain", "loss", "change"),
    "score": ("score", "rating"),
    "volume": ("volume", "participation"),
    "yield": ("yield",),
    "breadth": ("breadth", "advance decline", "constituents above"),
    "count": ("count", "constituent", "securities", "figure types", "items"),
    "ratio": ("ratio", "relative strength"),
    "risk": ("risk", "volatility"),
}


@dataclass(frozen=True)
class DeduplicationCollision:
    identity: str
    first_fingerprint: str
    duplicate_fingerprint: str


@dataclass(frozen=True)
class StableDeduplicationResult(Generic[T]):
    items: tuple[T, ...]
    duplicate_count: int
    collisions: tuple[DeduplicationCollision, ...]
    engine_version: str = EVIDENCE_VALIDATION_ENGINE_VERSION


@dataclass(frozen=True)
class ClaimBindingInput:
    claim: str
    claim_entities: frozenset[str]
    evidence_entities: frozenset[str]
    evidence_metric: str
    evidence_unit: str | None = None
    evidence_value: Any = None
    evidence_current_state: Any = None
    evidence_interpretation_class: str = "observed_fact"
    evidence_quarantined: bool = False
    claim_timeframe: str | None = None
    evidence_timeframe: str | None = None


@dataclass(frozen=True)
class ClaimBindingResult:
    valid: bool
    entity_match: bool
    metric_match: bool
    unit_match: bool
    period_match: bool
    suitable: bool
    reasons: tuple[str, ...] = field(default_factory=tuple)
    engine_version: str = EVIDENCE_VALIDATION_ENGINE_VERSION


@dataclass(frozen=True)
class BreakoutEvidence:
    entity: str
    entity_keys: frozenset[str]
    metric: str
    value: Any


@dataclass(frozen=True)
class BreakoutValidationInput:
    claimed_entities: frozenset[str]
    evidence: tuple[BreakoutEvidence, ...]


@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    provider: str
    dataset: str
    generated_at: str | None
    market_date: str | None
    raw_engine_reference: str | None


class EvidenceValidationEngine:
    """Pure evidence identity, binding, lineage, and breakout validation."""

    version = EVIDENCE_VALIDATION_ENGINE_VERSION

    def deduplicate(
        self,
        values: Iterable[T],
        *,
        identity: Callable[[T], str],
        fingerprint: Callable[[T], Any] | None = None,
    ) -> StableDeduplicationResult[T]:
        selected: dict[str, T] = {}
        collisions: list[DeduplicationCollision] = []
        duplicate_count = 0
        for value in values:
            key = identity(value)
            if key in selected:
                duplicate_count += 1
                first = selected[key]
                first_value = fingerprint(first) if fingerprint else first
                duplicate_value = fingerprint(value) if fingerprint else value
                if first_value != duplicate_value:
                    collisions.append(
                        DeduplicationCollision(
                            identity=key,
                            first_fingerprint=self.canonical_fingerprint(first_value),
                            duplicate_fingerprint=self.canonical_fingerprint(duplicate_value),
                        )
                    )
                continue
            selected[key] = value
        return StableDeduplicationResult(
            items=tuple(selected.values()),
            duplicate_count=duplicate_count,
            collisions=tuple(collisions),
        )

    def validate_claim_binding(self, value: ClaimBindingInput) -> ClaimBindingResult:
        reasons: list[str] = []
        entity_match = not value.claim_entities or bool(
            value.claim_entities.intersection(value.evidence_entities)
        )
        if not entity_match:
            reasons.append("entity_mismatch")

        claim_metrics = self.metric_families(value.claim)
        descriptor = " ".join(
            (
                value.evidence_metric,
                value.evidence_unit or "",
                self.json_text(value.evidence_value),
                self.json_text(value.evidence_current_state),
            )
        )
        evidence_metrics = self.metric_families(descriptor)
        metric_match = not claim_metrics or bool(claim_metrics.intersection(evidence_metrics))
        if not metric_match:
            reasons.append("metric_mismatch")

        lowered = value.claim.casefold()
        unit_descriptor = (
            f"{value.evidence_unit or ''} {self.json_text(value.evidence_value)} "
            f"{self.json_text(value.evidence_current_state)}"
        ).casefold()
        metric = value.evidence_metric.casefold()
        percent_match = not (
            "%" in value.claim or "percent" in lowered or "percentage" in lowered
        ) or bool(
            "%" in unit_descriptor
            or "percent" in unit_descriptor
            or "percentage" in metric
        )
        currency_match = "$" not in value.claim or any(
            marker in f"{metric} {unit_descriptor}"
            for marker in ("price", "usd", "dollar")
        )
        unit_match = percent_match and currency_match
        if not unit_match:
            reasons.append("unit_mismatch")

        period_match = self._periods_compatible(
            value.claim_timeframe,
            value.evidence_timeframe,
        )
        if not period_match:
            reasons.append("period_mismatch")

        suitable = not value.evidence_quarantined and value.evidence_interpretation_class != "missing_evidence"
        if not suitable:
            reasons.append("evidence_unsuitable")

        return ClaimBindingResult(
            valid=entity_match and metric_match and unit_match and period_match and suitable,
            entity_match=entity_match,
            metric_match=metric_match,
            unit_match=unit_match,
            period_match=period_match,
            suitable=suitable,
            reasons=tuple(reasons),
        )

    def validate_breakout_confirmation(self, value: BreakoutValidationInput) -> bool:
        by_entity: dict[str, dict[str, Any]] = {}
        for item in value.evidence:
            if value.claimed_entities and not item.entity_keys.intersection(value.claimed_entities):
                continue
            state = by_entity.setdefault(
                item.entity.strip().casefold(),
                {"current": [], "trigger": [], "volume": False},
            )
            metric = item.metric.casefold()
            number = self.scalar_decimal(item.value)
            if any(term in metric for term in ("breakout", "resistance", "confirmation", "trigger")):
                if number is not None:
                    state["trigger"].append(number)
            elif metric in {"price", "current price", "last price", "close", "closing price"}:
                if number is not None:
                    state["current"].append(number)
            if "volume" in metric and self.volume_supports_confirmation(metric, item.value):
                state["volume"] = True
        return any(
            state["current"]
            and state["trigger"]
            and max(state["current"]) > max(state["trigger"])
            and state["volume"]
            for state in by_entity.values()
        )

    def claims_semantically_compatible(
        self,
        first: str,
        second: str,
        *,
        first_entities: frozenset[str],
        second_entities: frozenset[str],
    ) -> bool:
        if first_entities and second_entities and not first_entities.intersection(second_entities):
            return False
        first_metrics = self.metric_families(first)
        second_metrics = self.metric_families(second)
        if first_metrics and second_metrics and not first_metrics.intersection(second_metrics):
            return False
        first_percent = "%" in first or "percent" in first.casefold() or "percentage" in first.casefold()
        second_percent = "%" in second or "percent" in second.casefold() or "percentage" in second.casefold()
        if first_percent != second_percent and (first_metrics or second_metrics):
            return False
        return True

    @staticmethod
    def source_identity(source: SourceRecord) -> tuple[str | None, ...]:
        return (
            source.provider,
            source.dataset,
            source.generated_at,
            source.market_date,
            source.raw_engine_reference,
        )

    @staticmethod
    def source_timestamp_is_valid(source: SourceRecord) -> bool:
        if source.generated_at:
            try:
                datetime.fromisoformat(source.generated_at.replace("Z", "+00:00"))
            except ValueError:
                return False
        if source.market_date and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", source.market_date):
            return False
        return True

    @staticmethod
    def metric_families(text: str) -> set[str]:
        lowered = text.casefold().replace("-", " ")
        return {
            family
            for family, markers in METRIC_FAMILY_PATTERNS.items()
            if any(marker in lowered for marker in markers)
        }

    @staticmethod
    def scalar_decimal(value: Any) -> Decimal | None:
        if value is None or isinstance(value, bool):
            return None
        raw = str(value).strip().replace(",", "").rstrip("%")
        if not re.fullmatch(r"[-+]?\d+(?:\.\d+)?", raw):
            return None
        try:
            return Decimal(raw)
        except InvalidOperation:
            return None

    def volume_supports_confirmation(self, metric: str, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        number = self.scalar_decimal(value)
        lowered_metric = metric.casefold()
        if number is not None:
            return any(
                term in lowered_metric for term in ("ratio", "relative", "vs average")
            ) and number >= 1
        text = str(value or "").casefold()
        if any(
            term in text
            for term in (
                "weak",
                "below average",
                "declining",
                "missing",
                "partial",
                "unavailable",
                "not confirmed",
            )
        ):
            return False
        return any(
            term in text
            for term in ("strong", "above average", "expanding", "confirmed", "supportive")
        )

    @staticmethod
    def canonical_fingerprint(value: Any) -> str:
        if hasattr(value, "model_dump"):
            value = value.model_dump(mode="json", by_alias=False)
        elif hasattr(value, "__dict__"):
            value = value.__dict__
        return json.dumps(value, sort_keys=True, default=str, ensure_ascii=True)

    @staticmethod
    def json_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        try:
            return json.dumps(value, sort_keys=True, default=str, ensure_ascii=True)
        except (TypeError, ValueError):
            return str(value)

    @staticmethod
    def _periods_compatible(claim_timeframe: str | None, evidence_timeframe: str | None) -> bool:
        if not claim_timeframe or not evidence_timeframe:
            return True
        return claim_timeframe.casefold().strip() == evidence_timeframe.casefold().strip()
