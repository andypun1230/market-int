from __future__ import annotations

from datetime import datetime
from typing import Self

from pydantic import Field, field_validator, model_validator

from app.intelligence.news.contracts import (
    CorrectionStatus,
    ExpectedDirection,
    NewsContractModel,
    NewsEventStatus,
    NewsEventType,
    NewsFreshnessState,
    NewsProviderMode,
    NewsProviderProvenance,
)


class NewsProviderItem(NewsContractModel):
    """Provider-neutral ingress metadata; intentionally has no article-body field."""

    provider_event_id: str = Field(min_length=1, max_length=300, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$")
    headline: str = Field(min_length=1, max_length=20_000)
    summary: str = Field(default="", max_length=50_000)
    source_identifier: str = Field(min_length=1, max_length=200, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
    source_name: str = Field(min_length=1, max_length=300)
    source_url: str | None = Field(default=None, max_length=4_000)
    published_at: datetime | None = None
    updated_at: datetime | None = None
    first_seen_at: datetime | None = None
    language: str = Field(default="en", min_length=2, max_length=16, pattern=r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})?$")
    structured_event_type: NewsEventType | None = None
    structured_event_subtype: str | None = Field(default=None, max_length=120)
    structured_symbols: tuple[str, ...] = ()
    structured_company_names: tuple[str, ...] = ()
    confirmed_facts: tuple[str, ...] = ()
    event_status: NewsEventStatus = NewsEventStatus.DEVELOPING
    correction_status: CorrectionStatus = CorrectionStatus.NONE
    supersedes_provider_event_id: str | None = Field(default=None, max_length=300, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$")
    superseded_by_provider_event_id: str | None = Field(default=None, max_length=300, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$")
    correction_reason: str | None = Field(default=None, max_length=2_000)
    canonical_event_reference: str | None = Field(default=None, max_length=300, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$")
    expected_direction: ExpectedDirection = ExpectedDirection.UNKNOWN
    is_official_release: bool = False
    origin_provider: str | None = Field(default=None, max_length=120)
    origin_provider_mode: NewsProviderMode | None = None
    origin_fetched_at: datetime | None = None

    @field_validator("published_at", "updated_at", "first_seen_at", "origin_fetched_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("provider_news_timestamp_must_be_timezone_aware")
        return value

    @field_validator("structured_symbols")
    @classmethod
    def normalize_symbols(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized: list[str] = []
        for raw in values:
            symbol = raw.strip().upper()
            if not symbol or len(symbol) > 20 or not all(character.isalnum() or character in ".-" for character in symbol):
                raise ValueError("invalid_provider_news_symbol")
            if symbol not in normalized:
                normalized.append(symbol)
        return tuple(normalized)

    @model_validator(mode="after")
    def validate_provider_lineage(self) -> Self:
        if self.updated_at and self.published_at and self.updated_at < self.published_at:
            raise ValueError("provider_update_precedes_publication")
        if self.correction_status in {CorrectionStatus.CORRECTED, CorrectionStatus.RETRACTED} and not (
            self.supersedes_provider_event_id or self.correction_reason
        ):
            raise ValueError("provider_correction_requires_lineage")
        if self.correction_status == CorrectionStatus.SUPERSEDED and not self.superseded_by_provider_event_id:
            raise ValueError("provider_superseded_event_requires_successor")
        return self


class NewsProviderRequest(NewsContractModel):
    as_of: datetime
    start_at: datetime | None = None
    end_at: datetime | None = None
    symbols: tuple[str, ...] = ()
    event_types: tuple[NewsEventType, ...] = ()
    limit: int = Field(default=100, ge=1, le=500)
    cursor: str | None = Field(default=None, max_length=500)
    macro_only: bool = False
    official_only: bool = False
    earnings_only: bool = False

    @field_validator("as_of", "start_at", "end_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("provider_request_timestamp_must_be_timezone_aware")
        return value

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        if self.start_at and self.end_at and self.end_at < self.start_at:
            raise ValueError("provider_request_invalid_range")
        return self


class NewsProviderCapabilities(NewsContractModel):
    provider: str
    mode: NewsProviderMode
    fetch_by_time_range: bool
    fetch_by_ticker: bool
    fetch_macro_events: bool
    fetch_official_releases: bool
    fetch_earnings_events: bool
    supports_pagination: bool
    metadata_only: bool = True
    article_bodies_exposed: bool = False

    @model_validator(mode="after")
    def forbid_article_body_capability(self) -> Self:
        if self.article_bodies_exposed or not self.metadata_only:
            raise ValueError("stage8_news_provider_must_be_metadata_only")
        return self


class NewsProviderHealth(NewsContractModel):
    provider: str
    mode: NewsProviderMode
    reachable: bool
    checked_at: datetime
    message: str

    @field_validator("checked_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("provider_health_timestamp_must_be_timezone_aware")
        return value


class NewsProviderResponse(NewsContractModel):
    items: tuple[NewsProviderItem, ...]
    provenance: NewsProviderProvenance
    next_cursor: str | None = None

    @model_validator(mode="after")
    def enforce_mode_state(self) -> Self:
        if self.provenance.mode == NewsProviderMode.UNAVAILABLE and self.items:
            raise ValueError("unavailable_provider_cannot_return_items")
        if self.provenance.source_state == NewsFreshnessState.UNAVAILABLE and self.items:
            raise ValueError("unavailable_source_state_cannot_return_items")
        return self
