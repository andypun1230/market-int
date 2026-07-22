from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Self
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


NEWS_SERVICE_VERSION = "news-intelligence-v1"


class NewsContractModel(BaseModel):
    """Strict, immutable contracts shared by every News Intelligence layer."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class NewsEventType(str, Enum):
    MONETARY_POLICY = "monetary_policy"
    INFLATION = "inflation"
    EMPLOYMENT = "employment"
    ECONOMIC_GROWTH = "economic_growth"
    GOVERNMENT_POLICY = "government_policy"
    REGULATION = "regulation"
    GEOPOLITICS = "geopolitics"
    EARNINGS = "earnings"
    GUIDANCE = "guidance"
    MERGER_ACQUISITION = "merger_acquisition"
    CAPITAL_RAISE = "capital_raise"
    BUYBACK = "buyback"
    DIVIDEND = "dividend"
    PRODUCT_LAUNCH = "product_launch"
    SUPPLY_CHAIN = "supply_chain"
    CUSTOMER_CONTRACT = "customer_contract"
    LEGAL = "legal"
    MANAGEMENT_CHANGE = "management_change"
    ANALYST_ACTION = "analyst_action"
    CREDIT_RATING = "credit_rating"
    CYBERSECURITY_INCIDENT = "cybersecurity_incident"
    EXCHANGE_NOTICE = "exchange_notice"
    MARKET_STRUCTURE = "market_structure"
    POSITIONING_COMMENTARY = "positioning_commentary"
    OTHER = "other"


class SourceQuality(str, Enum):
    PRIMARY = "primary"
    HIGH_CONFIDENCE_SECONDARY = "high_confidence_secondary"
    SUPPORTING_SECONDARY = "supporting_secondary"
    UNVERIFIED = "unverified"
    UNAVAILABLE = "unavailable"


class NewsEventStatus(str, Enum):
    CONFIRMED = "confirmed"
    DEVELOPING = "developing"
    CORRECTED = "corrected"
    RETRACTED = "retracted"
    DISPUTED = "disputed"
    UNVERIFIED = "unverified"


class CorrectionStatus(str, Enum):
    NONE = "none"
    CORRECTED = "corrected"
    SUPERSEDED = "superseded"
    RETRACTED = "retracted"


class NewsProviderMode(str, Enum):
    LIVE = "live"
    CACHED = "cached"
    HERMETIC = "test"
    UNAVAILABLE = "unavailable"


class NewsFreshnessState(str, Enum):
    LIVE = "live"
    DELAYED = "delayed"
    CACHED = "cached"
    STALE = "stale"
    TEST = "test"
    PARTIAL = "partial"
    MIXED = "mixed"
    UNAVAILABLE = "unavailable"


class NewsAvailability(str, Enum):
    AVAILABLE = "available"
    PARTIAL = "partial"
    FALLBACK = "fallback"
    UNAVAILABLE = "unavailable"


class NewsServiceStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    STALE = "stale"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


class NewsSessionPhase(str, Enum):
    PREMARKET = "premarket"
    REGULAR = "regular"
    AFTER_HOURS = "after_hours"
    CLOSED = "closed"
    WEEKEND = "weekend"
    UNKNOWN = "unknown"


class NewsQueryMode(str, Enum):
    MARKET = "market"
    INDEX = "index"
    SECTOR = "sector"
    THEME = "theme"
    SECURITY = "security"
    WATCHLIST = "watchlist"


class EntityType(str, Enum):
    SECURITY = "security"
    COMPANY = "company"
    INDUSTRY = "industry"
    SECTOR = "sector"
    THEME = "theme"
    ETF = "etf"
    INDEX = "index"
    WATCHLIST = "watchlist"


class MappingRelationship(str, Enum):
    DIRECTLY_NAMED = "directly_named"
    COMPANY_PARENT = "company_parent"
    SECTOR_MEMBERSHIP = "sector_membership"
    INDUSTRY_MEMBERSHIP = "industry_membership"
    THEME_MEMBERSHIP = "theme_membership"
    ETF_CONSTITUENT = "ETF_constituent"
    BENCHMARK_RELATIONSHIP = "benchmark_relationship"
    VALIDATED_PEER = "validated_peer"
    WATCHLIST_OVERLAP = "watchlist_overlap"


class ExpectedDirection(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    UNKNOWN = "unknown"


class ReactionWindow(str, Enum):
    FIVE_MINUTES = "5_minutes"
    FIFTEEN_MINUTES = "15_minutes"
    THIRTY_MINUTES = "30_minutes"
    SIXTY_MINUTES = "60_minutes"
    SESSION_TO_DATE = "session_to_date"
    CLOSE_TO_CLOSE = "close_to_close"
    NEXT_SESSION = "next_session"
    MULTI_DAY = "multi_day"


class ReactionClassification(str, Enum):
    CONFIRMS_POSITIVE = "confirms_positive"
    CONFIRMS_NEGATIVE = "confirms_negative"
    REJECTS_POSITIVE = "rejects_positive"
    REJECTS_NEGATIVE = "rejects_negative"
    MIXED = "mixed"
    NO_MATERIAL_REACTION = "no_material_reaction"
    INSUFFICIENT_DATA = "insufficient_data"


class ConfidenceLabel(str, Enum):
    HIGH = "high"
    MODERATE = "moderate"
    LIMITED = "limited"


class EvidenceKind(str, Enum):
    CONFIRMED_FACT = "confirmed_fact"
    SOURCE_METADATA = "source_metadata"
    ENTITY_MAPPING = "entity_mapping"
    PRICE_REACTION = "price_reaction"
    VOLUME_REACTION = "volume_reaction"
    BREADTH_REACTION = "breadth_reaction"
    CROSS_ASSET_REACTION = "cross_asset_reaction"
    MISSING_EVIDENCE = "missing_evidence"


class InterpretationClass(str, Enum):
    OBSERVED_FACT = "observed_fact"
    ENGINE_CONCLUSION = "engine_conclusion"
    MISSING_EVIDENCE = "missing_evidence"
    CONTRADICTION = "contradiction"


class SourceRegistryRecord(NewsContractModel):
    source_id: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    display_name: str = Field(min_length=1, max_length=200)
    domain: str = Field(min_length=1, max_length=253)
    quality_tier: SourceQuality
    primary_source_categories: tuple[NewsEventType, ...] = ()
    allowed_event_types: tuple[NewsEventType, ...]
    storage_licensing_notes: str = Field(min_length=1, max_length=1000)
    metadata_storage_allowed: bool
    article_body_storage_allowed: bool = False
    active: bool = True
    test_only: bool = False

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, value: str) -> str:
        normalized = value.casefold().strip().rstrip(".")
        if "://" in normalized or "/" in normalized or " " in normalized:
            raise ValueError("source_domain_must_be_a_hostname")
        return normalized

    @model_validator(mode="after")
    def enforce_storage_boundary(self) -> Self:
        if self.article_body_storage_allowed:
            raise ValueError("stage8_news_registry_forbids_article_body_storage")
        return self


class NewsFreshness(NewsContractModel):
    state: NewsFreshnessState
    availability: NewsAvailability
    market_date: date | None = None
    generated_at: datetime | None = None
    observed_at: datetime | None = None
    expires_at: datetime | None = None
    age_seconds: float | None = Field(default=None, ge=0)
    completeness: float = Field(ge=0, le=1)
    provider: str
    fallback_used: bool = False
    mixed_sources: bool = False
    confidence_cap_recommendation: ConfidenceLabel | None = None
    warnings: tuple[str, ...] = ()
    engine_version: str

    @field_validator("generated_at", "observed_at", "expires_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("freshness_timestamp_must_be_timezone_aware")
        return value


class EventProviderMetadata(NewsContractModel):
    provider: str = Field(min_length=1, max_length=120)
    provider_event_id: str = Field(min_length=1, max_length=300, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$")
    provider_mode: NewsProviderMode
    fetched_at: datetime
    canonical_event_reference: str | None = Field(default=None, max_length=300, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$")

    @field_validator("fetched_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("provider_fetched_at_must_be_timezone_aware")
        return value


class NewsProviderProvenance(NewsContractModel):
    provider: str
    mode: NewsProviderMode
    source_state: NewsFreshnessState
    as_of: datetime
    fetched_at: datetime | None = None
    cache_hit: bool = False
    fallback_reason: str | None = None
    errors: tuple[str, ...] = ()
    latency_ms: float | None = Field(default=None, ge=0)

    @field_validator("as_of", "fetched_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("provider_timestamp_must_be_timezone_aware")
        return value

    @model_validator(mode="after")
    def forbid_silent_test_fallback(self) -> Self:
        if self.mode == NewsProviderMode.HERMETIC and self.source_state != NewsFreshnessState.TEST:
            raise ValueError("hermetic_provider_must_be_test_state")
        if self.mode == NewsProviderMode.UNAVAILABLE and self.source_state != NewsFreshnessState.UNAVAILABLE:
            raise ValueError("unavailable_provider_must_be_unavailable_state")
        if self.mode == NewsProviderMode.LIVE and self.source_state == NewsFreshnessState.TEST:
            raise ValueError("live_provider_cannot_claim_test_payload_as_live_mode")
        if self.mode == NewsProviderMode.CACHED and self.source_state in {
            NewsFreshnessState.LIVE,
            NewsFreshnessState.DELAYED,
        }:
            raise ValueError("cached_provider_cannot_claim_live_source_state")
        return self


class EntityMapping(NewsContractModel):
    entity_id: str = Field(min_length=1, max_length=200)
    entity_type: EntityType
    display_name: str = Field(min_length=1, max_length=300)
    symbol: str | None = Field(default=None, max_length=20, pattern=r"^[A-Z][A-Z0-9.-]{0,19}$")
    relationship: MappingRelationship
    mapping_source: str = Field(min_length=1, max_length=500)
    confidence: float = Field(ge=0, le=1)
    evidence_id: str = Field(min_length=1, max_length=200)
    freshness: NewsFreshness
    mapping_version: str = Field(min_length=1, max_length=80)


class MaterialityInputs(NewsContractModel):
    source_credibility: float = Field(default=0, ge=0, le=1)
    directness: float = Field(default=0, ge=0, le=1)
    surprise: float = Field(default=0, ge=0, le=1)
    market_scope: float = Field(default=0, ge=0, le=1)
    entity_significance: float = Field(default=0, ge=0, le=1)
    observed_price_reaction: float = Field(default=0, ge=0, le=1)
    observed_volume_reaction: float = Field(default=0, ge=0, le=1)
    breadth_confirmation: float = Field(default=0, ge=0, le=1)
    cross_asset_confirmation: float = Field(default=0, ge=0, le=1)
    duration: float = Field(default=0, ge=0, le=1)
    freshness: float = Field(default=0, ge=0, le=1)
    user_watchlist_relevance: float = Field(default=0, ge=0, le=1)
    duplicate_count: int = Field(default=0, ge=0)
    uncertainty: float = Field(default=0, ge=0, le=1)


class MaterialityContribution(NewsContractModel):
    component: str
    points: float
    reason: str


class MaterialityAssessment(NewsContractModel):
    market_materiality: int = Field(ge=0, le=100)
    entity_materiality: int = Field(ge=0, le=100)
    user_relevance: int = Field(ge=0, le=100)
    contributions: tuple[MaterialityContribution, ...]
    methodology_version: str


class MarketReactionObservation(NewsContractModel):
    event_id: str
    entity_id: str | None = Field(
        default=None,
        max_length=160,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:^\-]{0,159}$",
    )
    symbol: str | None = Field(default=None, max_length=20, pattern=r"^[A-Z][A-Z0-9.-]{0,19}$")
    window: ReactionWindow
    window_start: datetime
    window_end: datetime
    price_return: float | None = None
    benchmark_return: float | None = None
    sector_return: float | None = None
    volume_ratio: float | None = Field(default=None, ge=0)
    realized_range: float | None = Field(default=None, ge=0)
    breadth_change: float | None = None
    cross_asset_confirmation: float | None = Field(default=None, ge=-1, le=1)
    expected_direction: ExpectedDirection = ExpectedDirection.UNKNOWN
    evidence_ids: tuple[str, ...]
    source_id: str | None = Field(default=None, min_length=1, max_length=200)
    source_quality: SourceQuality = SourceQuality.UNAVAILABLE
    source_state: NewsFreshnessState

    @field_validator("evidence_ids")
    @classmethod
    def validate_evidence_ids(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        for value in values:
            if not value or len(value) > 200 or not all(
                character.isalnum() or character in "._:/-" for character in value
            ):
                raise ValueError("invalid_reaction_evidence_id")
        return tuple(dict.fromkeys(values))

    @field_validator("window_start", "window_end")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("reaction_window_must_be_timezone_aware")
        return value

    @model_validator(mode="after")
    def validate_window(self) -> Self:
        if self.window_end <= self.window_start:
            raise ValueError("reaction_window_end_must_follow_start")
        return self


class MarketReactionAssessment(NewsContractModel):
    classification: ReactionClassification
    supported_windows: tuple[ReactionWindow, ...]
    observations: tuple[MarketReactionObservation, ...]
    summary: str
    evidence_ids: tuple[str, ...]
    limitations: tuple[str, ...] = ()
    methodology_version: str


class CorrectionLineage(NewsContractModel):
    status: CorrectionStatus = CorrectionStatus.NONE
    supersedes_event_id: str | None = None
    superseded_by_event_id: str | None = None
    correction_reason: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def require_lineage_for_supersession(self) -> Self:
        if self.status == CorrectionStatus.SUPERSEDED and not self.superseded_by_event_id:
            raise ValueError("superseded_event_requires_successor")
        return self


class NewsEvidenceRecord(NewsContractModel):
    evidence_id: str = Field(min_length=1, max_length=200)
    source_id: str = Field(min_length=1, max_length=200)
    event_id: str = Field(min_length=1, max_length=200)
    kind: EvidenceKind
    statement: str = Field(min_length=1, max_length=2000)
    interpretation_class: InterpretationClass
    entity_ids: tuple[str, ...] = ()
    observed_at: datetime | None = None
    market_date: date | None = None
    source_quality: SourceQuality
    quarantined: bool = False

    @field_validator("observed_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("evidence_timestamp_must_be_timezone_aware")
        return value


class NewsContradiction(NewsContractModel):
    contradiction_id: str
    event_id: str
    statement: str
    evidence_ids: tuple[str, ...]
    preserved: bool
    engine_version: str


class NewsEventRecord(NewsContractModel):
    event_id: str = Field(min_length=1, max_length=200)
    cluster_id: str = Field(min_length=1, max_length=200)
    canonical_headline: str = Field(min_length=1, max_length=500)
    event_type: NewsEventType
    event_subtype: str | None = Field(default=None, max_length=120)
    expected_direction: ExpectedDirection = ExpectedDirection.UNKNOWN
    source_name: str = Field(min_length=1, max_length=200)
    source_identifier: str = Field(min_length=1, max_length=200, pattern=r"^[a-z0-9][a-z0-9._:-]*$")
    source_url: str | None = Field(default=None, max_length=2000)
    source_quality: SourceQuality
    primary_source: bool
    published_at: datetime
    updated_at: datetime | None = None
    first_seen_at: datetime
    language: str = Field(default="en", min_length=2, max_length=16, pattern=r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})?$")
    market_date: date
    session_phase: NewsSessionPhase
    confirmed_facts: tuple[str, ...] = ()
    source_summary: str = Field(default="", max_length=2000)
    affected_entities: tuple[EntityMapping, ...] = ()
    affected_sectors: tuple[str, ...] = ()
    affected_themes: tuple[str, ...] = ()
    affected_indexes: tuple[str, ...] = ()
    event_status: NewsEventStatus
    correction: CorrectionLineage = Field(default_factory=CorrectionLineage)
    materiality_inputs: MaterialityInputs = Field(default_factory=MaterialityInputs)
    materiality: MaterialityAssessment | None = None
    reaction: MarketReactionAssessment | None = None
    evidence_ids: tuple[str, ...]
    freshness: NewsFreshness
    provider_metadata: EventProviderMetadata
    quarantined: bool = False
    quarantine_reasons: tuple[str, ...] = ()

    @field_validator("published_at", "updated_at", "first_seen_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("news_event_timestamp_must_be_timezone_aware")
        return value

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("source_url_must_be_safe_https")
        return value

    @model_validator(mode="after")
    def enforce_fact_and_quality_safety(self) -> Self:
        if self.updated_at is not None and self.updated_at < self.published_at:
            raise ValueError("updated_at_must_not_precede_published_at")
        if self.first_seen_at < self.published_at:
            raise ValueError("first_seen_at_must_not_precede_published_at")
        if self.confirmed_facts and not self.evidence_ids:
            raise ValueError("confirmed_facts_require_evidence")
        if self.source_quality in {SourceQuality.UNVERIFIED, SourceQuality.UNAVAILABLE} and self.event_status == NewsEventStatus.CONFIRMED:
            raise ValueError("unverified_source_cannot_confirm_event")
        if self.quarantined:
            if self.event_status != NewsEventStatus.UNVERIFIED or self.confirmed_facts:
                raise ValueError("quarantined_event_must_be_unverified_without_facts")
            if not self.quarantine_reasons:
                raise ValueError("quarantined_event_requires_reason")
        return self


class NewsClusterSourceMember(NewsContractModel):
    event_id: str
    source_identifier: str
    source_name: str
    source_url: str | None = None
    source_quality: SourceQuality
    primary_source: bool
    published_at: datetime
    updated_at: datetime | None = None
    event_status: NewsEventStatus
    correction: CorrectionLineage
    provider: str
    provider_event_id: str

    @field_validator("published_at", "updated_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("cluster_source_timestamp_must_be_timezone_aware")
        return value


class NewsEventCluster(NewsContractModel):
    cluster_id: str
    canonical_event_id: str
    member_event_ids: tuple[str, ...]
    earliest_event_id: str
    primary_source_event_id: str | None = None
    update_event_ids: tuple[str, ...] = ()
    correction_event_ids: tuple[str, ...] = ()
    contradiction_event_ids: tuple[str, ...] = ()
    duplicate_count: int = Field(default=0, ge=0)
    source_count: int = Field(ge=1)
    source_members: tuple[NewsClusterSourceMember, ...]
    cluster_version: str


class NewsDeepLink(NewsContractModel):
    destination: str
    entity_id: str | None = None
    symbol: str | None = None
    parameters: tuple[tuple[str, str], ...] = ()


class NewsProcessingMetrics(NewsContractModel):
    provider_fetch_ms: float = Field(default=0, ge=0)
    normalization_ms: float = Field(default=0, ge=0)
    clustering_ms: float = Field(default=0, ge=0)
    mapping_ms: float = Field(default=0, ge=0)
    materiality_ms: float = Field(default=0, ge=0)
    reaction_ms: float = Field(default=0, ge=0)
    materiality_reaction_ms: float = Field(default=0, ge=0)
    total_ms: float = Field(default=0, ge=0)
    provider_event_count: int = Field(default=0, ge=0)
    normalized_event_count: int = Field(default=0, ge=0)
    cluster_count: int = Field(default=0, ge=0)
    returned_event_count: int = Field(default=0, ge=0)
    duplicate_reduction_ratio: float = Field(default=0, ge=0, le=1)
    cache_hit: bool = False


class NewsQuery(NewsContractModel):
    mode: NewsQueryMode
    as_of: datetime
    start_at: datetime | None = None
    end_at: datetime | None = None
    entity_id: str | None = Field(
        default=None,
        max_length=160,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:^\-]{0,159}$",
    )
    symbols: tuple[str, ...] = ()
    event_types: tuple[NewsEventType, ...] = ()
    source_qualities: tuple[SourceQuality, ...] = ()
    minimum_materiality: int = Field(default=0, ge=0, le=100)
    limit: int = Field(default=20, ge=1, le=100)

    @field_validator("as_of", "start_at", "end_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("news_query_timestamp_must_be_timezone_aware")
        return value

    @field_validator("symbols")
    @classmethod
    def normalize_symbols(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized: list[str] = []
        for value in values:
            symbol = value.strip().upper()
            if not symbol or len(symbol) > 20 or not all(character.isalnum() or character in ".-" for character in symbol):
                raise ValueError("invalid_news_query_symbol")
            if symbol not in normalized:
                normalized.append(symbol)
        return tuple(normalized)

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        if self.start_at and self.end_at and self.end_at < self.start_at:
            raise ValueError("news_query_end_must_not_precede_start")
        if self.start_at and self.start_at > self.as_of:
            raise ValueError("news_query_start_must_not_exceed_as_of")
        if self.end_at and self.end_at > self.as_of:
            raise ValueError("news_query_end_must_not_exceed_as_of")
        if self.mode in {NewsQueryMode.SECURITY, NewsQueryMode.WATCHLIST} and not (self.symbols or self.entity_id):
            raise ValueError("entity_news_query_requires_entity")
        if self.mode in {NewsQueryMode.INDEX, NewsQueryMode.SECTOR, NewsQueryMode.THEME} and not self.entity_id:
            raise ValueError("scoped_news_query_requires_entity_id")
        return self


class NewsIntelligenceResult(NewsContractModel):
    query: NewsQuery
    status: NewsServiceStatus
    provider: NewsProviderProvenance
    as_of: datetime
    events: tuple[NewsEventRecord, ...] = ()
    clusters: tuple[NewsEventCluster, ...] = ()
    evidence: tuple[NewsEvidenceRecord, ...] = ()
    contradictions: tuple[NewsContradiction, ...] = ()
    confidence: ConfidenceLabel
    confidence_contributions: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    deep_links: tuple[NewsDeepLink, ...] = ()
    metrics: NewsProcessingMetrics = Field(default_factory=NewsProcessingMetrics)
    freshness: NewsFreshness
    service_version: str = NEWS_SERVICE_VERSION

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("result_as_of_must_be_timezone_aware")
        return value

    @model_validator(mode="after")
    def enforce_status_contract(self) -> Self:
        if self.status in {NewsServiceStatus.UNAVAILABLE, NewsServiceStatus.FAILED} and self.events:
            raise ValueError("unavailable_result_cannot_contain_events")
        if self.provider.mode == NewsProviderMode.HERMETIC and self.freshness.state != NewsFreshnessState.TEST:
            raise ValueError("hermetic_result_must_remain_test_labeled")
        return self
