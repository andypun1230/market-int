from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Literal


FRESHNESS_ENGINE_VERSION = "freshness-availability-v1"

FreshnessState = Literal[
    "live",
    "delayed",
    "cached",
    "stale",
    "test",
    "partial",
    "mixed",
    "unavailable",
]
AvailabilityState = Literal["available", "partial", "fallback", "unavailable"]
ConfidenceCap = Literal["moderate", "limited"]

TRUSTED_SOURCE_STATES: frozenset[str] = frozenset(
    {
        "live",
        "delayed",
        "cached",
        "stale",
        "test",
        "partial",
        "mixed",
        "unavailable",
    }
)
CONSTRAINED_FRESHNESS_STATES: frozenset[str] = frozenset(
    {"stale", "test", "partial", "mixed", "unavailable"}
)


@dataclass(frozen=True)
class FreshnessAvailabilityInput:
    """Presentation-independent freshness facts supplied by a source adapter.

    ``now`` is injectable so frozen-input tests are deterministic.  Production
    adapters may omit it and use the current UTC clock, preserving Stage 7.
    Market-session fields are retained explicitly even when the current source
    contract has no calendar-aware threshold override.
    """

    source_state: Any
    provider_status: Any = None
    generated_at: str | None = None
    observed_at: str | None = None
    market_date: str | None = None
    expires_at: str | None = None
    expected_update_frequency_seconds: int | None = None
    stale_after_seconds: int = 129_600
    completeness: float = 0.0
    provider: str = "unavailable"
    market_session_context: str | None = None
    test_data: bool = False
    fallback_used: bool = False
    mixed_sources: bool = False
    warnings: tuple[str, ...] = field(default_factory=tuple)
    now: datetime | None = None


@dataclass(frozen=True)
class FreshnessAvailabilityResult:
    state: FreshnessState
    availability: AvailabilityState
    market_date: str | None
    generated_at: str | None
    observed_at: str | None
    expires_at: str | None
    age_seconds: float | None
    completeness: float
    provider: str
    fallback_used: bool
    mixed_sources: bool
    confidence_cap_recommendation: ConfidenceCap | None
    warnings: tuple[str, ...]
    engine_version: str = FRESHNESS_ENGINE_VERSION


@dataclass(frozen=True)
class FreshnessSummaryInput:
    state: str
    market_date: str | None = None
    generated_at: str | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class FreshnessSummaryResult:
    overall_state: FreshnessState
    market_dates: tuple[str, ...]
    generated_timestamps: tuple[str, ...]
    current_count: int
    stale_count: int
    partial_count: int
    unavailable_count: int
    test_count: int
    warnings: tuple[str, ...]
    confidence_cap_recommendation: ConfidenceCap | None
    engine_version: str = FRESHNESS_ENGINE_VERSION


class FreshnessAvailabilityEngine:
    """Normalize availability and age without producing presentation prose."""

    version = FRESHNESS_ENGINE_VERSION

    def evaluate(self, value: FreshnessAvailabilityInput) -> FreshnessAvailabilityResult:
        state = self.state_from_source(
            source_state=value.source_state,
            provider_status=value.provider_status,
            expires_at=value.expires_at,
            test_data=value.test_data,
            now=value.now,
        )
        timestamp = self.parse_datetime(value.observed_at) or self.parse_datetime(value.generated_at)
        now = self._utc(value.now or datetime.now(timezone.utc))
        age: float | None = None
        if timestamp is not None:
            age = max(0.0, (now - timestamp).total_seconds())
            if state not in {"test", "unavailable"} and age > max(0, value.stale_after_seconds):
                state = "stale"
        if value.mixed_sources and state not in {"test", "unavailable"}:
            state = "mixed"

        completeness = self.clamp_completeness(value.completeness)
        availability: AvailabilityState
        if state == "unavailable":
            availability = "unavailable"
        elif value.fallback_used:
            availability = "fallback"
        elif state in CONSTRAINED_FRESHNESS_STATES:
            availability = "partial"
        else:
            availability = "available"

        return FreshnessAvailabilityResult(
            state=state,
            availability=availability,
            market_date=(value.market_date or "")[:10] or None,
            generated_at=value.generated_at,
            observed_at=value.observed_at,
            expires_at=value.expires_at,
            age_seconds=round(age, 3) if age is not None else None,
            completeness=completeness,
            provider=value.provider,
            fallback_used=value.fallback_used,
            mixed_sources=value.mixed_sources,
            confidence_cap_recommendation=(
                "limited" if state in CONSTRAINED_FRESHNESS_STATES else None
            ),
            warnings=self._dedupe(value.warnings),
        )

    def summarize(self, values: Iterable[FreshnessSummaryInput]) -> FreshnessSummaryResult:
        items = tuple(values)
        states = tuple(self.normalize_source_state(item.state) for item in items)
        overall = self.aggregate_states(states)
        current_states = {"live", "delayed", "cached"}
        return FreshnessSummaryResult(
            overall_state=overall,
            market_dates=tuple(sorted({item.market_date for item in items if item.market_date})),
            generated_timestamps=tuple(
                sorted({item.generated_at for item in items if item.generated_at})
            ),
            current_count=sum(state in current_states for state in states),
            stale_count=sum(state == "stale" for state in states),
            partial_count=sum(state in {"partial", "mixed"} for state in states),
            unavailable_count=sum(state == "unavailable" for state in states),
            test_count=sum(state == "test" for state in states),
            warnings=self._dedupe(
                warning for item in items for warning in item.warnings if warning
            ),
            confidence_cap_recommendation=(
                "limited" if overall in CONSTRAINED_FRESHNESS_STATES else None
            ),
        )

    def state_from_source(
        self,
        *,
        source_state: Any,
        provider_status: Any = None,
        expires_at: str | None = None,
        test_data: bool = False,
        now: datetime | None = None,
    ) -> FreshnessState:
        normalized_status = str(
            getattr(provider_status, "value", provider_status) or ""
        ).lower()
        if test_data:
            return "test"
        if self.is_expired(expires_at, now=now) or normalized_status == "stale":
            return "stale"
        if normalized_status in {"partial", "initializing"}:
            return "partial" if normalized_status == "partial" else "unavailable"
        if normalized_status in {"unavailable", "failed"}:
            return "unavailable"
        return self.normalize_source_state(source_state)

    def normalize_source_state(
        self,
        value: Any,
        *,
        partial: bool = False,
        test: bool = False,
    ) -> FreshnessState:
        if test:
            return "test"
        text = str(getattr(value, "value", value) or "unavailable").strip().lower()
        if partial and text not in {"test", "stale", "unavailable"}:
            return "partial"
        if text in TRUSTED_SOURCE_STATES:
            return text  # type: ignore[return-value]
        if text in {"current", "fresh", "official", "available"}:
            return "live"
        if text in {"mock", "generated_test_data"}:
            return "test"
        return "unavailable"

    def aggregate_states(self, states: Iterable[Any]) -> FreshnessState:
        values = {self.normalize_source_state(state) for state in states}
        if not values or values == {"unavailable"}:
            return "unavailable"
        unavailable = "unavailable" in values
        values.discard("unavailable")
        if "test" in values:
            result: FreshnessState = "test" if values == {"test"} else "mixed"
            return "mixed" if unavailable else result
        if "stale" in values:
            result = "stale" if values == {"stale"} else "mixed"
            return "mixed" if unavailable else result
        if "partial" in values:
            return "partial" if values <= {"partial", "live", "cached", "delayed"} else "mixed"
        if unavailable:
            return "partial"
        if len(values) == 1:
            return next(iter(values))
        return "mixed"

    def is_expired(self, expires_at: str | None, *, now: datetime | None = None) -> bool:
        parsed = self.parse_datetime(expires_at)
        if parsed is None:
            return False
        return parsed <= self._utc(now or datetime.now(timezone.utc))

    @staticmethod
    def parse_datetime(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    @staticmethod
    def clamp_completeness(value: Any) -> float:
        try:
            number = float(value or 0)
        except (TypeError, ValueError):
            number = 0.0
        return max(0.0, min(1.0, number))

    @staticmethod
    def _utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(value for value in values if value))
