from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.analysis_engines.session import (
    BarInterval,
    SessionAnalysisResult,
    SessionAnalysisState,
    SessionAnalysisStatus,
    SessionConfidenceLabel,
    SessionDataMode,
    SessionEvidence,
    SessionSourceState,
)


SESSION_NARRATIVE_VERSION = "session-narrative-v1"


class NarrativeContractModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        validate_default=True,
        use_enum_values=False,
    )


class NarrativeAvailability(str, Enum):
    AVAILABLE = "available"
    PARTIAL = "partial"
    DAILY_ONLY = "daily_only"
    UNAVAILABLE = "unavailable"


class SessionSourceAvailability(NarrativeContractModel):
    symbol: Annotated[str, Field(min_length=1, max_length=32)]
    data_mode: SessionDataMode
    narrative_availability: NarrativeAvailability
    intraday_supported: bool
    provider: str | None = None
    as_of: datetime
    reason: Annotated[str, Field(min_length=1, max_length=500)]
    test_data_detected: bool = False

    @field_validator("as_of")
    @classmethod
    def as_of_is_aware(cls, value: datetime) -> datetime:
        return _require_aware(value)


class NarrativeClaim(NarrativeContractModel):
    claim_id: Annotated[str, Field(min_length=1, max_length=240)]
    text: Annotated[str, Field(min_length=1, max_length=700)]
    evidence_ids: Annotated[tuple[str, ...], Field(min_length=1)]
    observed_relationship_only: Literal[True] = True
    causal: Literal[False] = False


class SessionNarrative(NarrativeContractModel):
    narrative_version: str = SESSION_NARRATIVE_VERSION
    symbol: str
    session_date: date | None = None
    availability: NarrativeAvailability
    analysis_state: SessionAnalysisState = SessionAnalysisState.UNAVAILABLE
    data_mode: SessionDataMode
    headline: str
    claims: tuple[NarrativeClaim, ...] = ()
    evidence: tuple[SessionEvidence, ...] = ()
    confidence: SessionConfidenceLabel = SessionConfidenceLabel.LIMITED
    freshness: SessionSourceState = SessionSourceState.UNAVAILABLE
    coverage: Annotated[float, Field(ge=0.0, le=1.0, allow_inf_nan=False)] = 0.0
    caveats: tuple[str, ...]
    causality_disclosure: str = (
        "Event timing and market movement are reported as temporal observations only; "
        "the narrative does not assert that an event caused a price or volume move."
    )

    @model_validator(mode="after")
    def claims_require_nested_evidence_lineage(self) -> "SessionNarrative":
        if self.availability not in {
            NarrativeAvailability.AVAILABLE,
            NarrativeAvailability.PARTIAL,
        }:
            return self
        evidence_ids = [item.evidence_id for item in self.evidence]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("narrative evidence IDs must be unique")
        available = set(evidence_ids)
        for claim in self.claims:
            if len(claim.evidence_ids) != len(set(claim.evidence_ids)):
                raise ValueError("claim evidence IDs must be unique")
            missing = tuple(item for item in claim.evidence_ids if item not in available)
            if missing:
                raise ValueError(
                    f"claim {claim.claim_id} references evidence absent from narrative.evidence: {missing}"
                )
        return self


class SessionNarrativeEnvelope(NarrativeContractModel):
    analysis: SessionAnalysisResult
    narrative: SessionNarrative


class SessionNarrativeQuery(NarrativeContractModel):
    """Transport-neutral query contract suitable for a GET endpoint adapter."""

    symbol: Annotated[str, Field(min_length=1, max_length=32, pattern=r"^[A-Z0-9.\-^]+$")]
    interval: BarInterval = BarInterval.FIVE_MINUTES
    requested_session_date: date | None = None
    as_of: datetime

    @field_validator("as_of")
    @classmethod
    def as_of_is_aware(cls, value: datetime) -> datetime:
        return _require_aware(value)


class SessionNarrativeProvenance(NarrativeContractModel):
    provider: str | None = None
    dataset: str
    source_id: str | None = None
    data_mode: SessionDataMode
    as_of: datetime
    latest_daily_session: date | None = None
    intraday_supported: bool
    test_data_detected: bool = False
    production_policy: str = (
        "Daily observations are never resampled, interpolated, or relabeled as intraday evidence."
    )

    @field_validator("as_of")
    @classmethod
    def as_of_is_aware(cls, value: datetime) -> datetime:
        return _require_aware(value)


class ProductionSessionNarrativeResult(NarrativeContractModel):
    """Canonical response used by the registered production GET endpoints."""

    query: SessionNarrativeQuery
    status: SessionAnalysisStatus
    availability: NarrativeAvailability
    provider: str | None = None
    data_mode: SessionDataMode
    as_of: datetime
    latest_daily_session: date | None = None
    narrative: SessionNarrative
    limitations: tuple[str, ...]
    provenance: SessionNarrativeProvenance

    @model_validator(mode="after")
    def response_is_internally_consistent(self) -> "ProductionSessionNarrativeResult":
        if self.query.as_of != self.as_of or self.provenance.as_of != self.as_of:
            raise ValueError("query, response, and provenance as_of values must match")
        if self.data_mode is not self.provenance.data_mode or self.data_mode is not self.narrative.data_mode:
            raise ValueError("data_mode must match across response, provenance, and narrative")
        if self.availability is not self.narrative.availability:
            raise ValueError("availability must match the nested narrative")
        if self.provider != self.provenance.provider:
            raise ValueError("provider must match provenance")
        if self.latest_daily_session != self.provenance.latest_daily_session:
            raise ValueError("latest daily session must match provenance")
        expected_status = (
            SessionAnalysisStatus.DAILY_ONLY
            if self.data_mode is SessionDataMode.DAILY_ONLY
            else SessionAnalysisStatus.UNAVAILABLE
        )
        if self.status is not expected_status:
            raise ValueError("production response status must fail closed for its data mode")
        expected_analysis_state = (
            SessionAnalysisState.DAILY_ONLY
            if self.data_mode is SessionDataMode.DAILY_ONLY
            else SessionAnalysisState.UNAVAILABLE
        )
        if self.narrative.analysis_state is not expected_analysis_state:
            raise ValueError("production narrative analysis_state must match the fail-closed data mode")
        return self


def availability_from_status(status: SessionAnalysisStatus) -> NarrativeAvailability:
    if status is SessionAnalysisStatus.COMPLETE:
        return NarrativeAvailability.AVAILABLE
    if status is SessionAnalysisStatus.PARTIAL:
        return NarrativeAvailability.PARTIAL
    if status is SessionAnalysisStatus.DAILY_ONLY:
        return NarrativeAvailability.DAILY_ONLY
    return NarrativeAvailability.UNAVAILABLE


def _require_aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("as_of must be timezone-aware")
    return value
