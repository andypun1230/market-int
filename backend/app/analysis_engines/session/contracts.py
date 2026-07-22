from __future__ import annotations

from datetime import date, datetime, time
from enum import Enum
from math import isfinite
from typing import Any, Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


SESSION_ENGINE_VERSION = "session-narrative-analysis-v2"


class SessionContractModel(BaseModel):
    """Strict, immutable contracts shared by the session analysis boundary."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        validate_default=True,
        use_enum_values=False,
    )


class BarInterval(str, Enum):
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"

    @property
    def minutes(self) -> int:
        return 5 if self is BarInterval.FIVE_MINUTES else 15


class SessionDataMode(str, Enum):
    INTRADAY_5M = "intraday_5m"
    INTRADAY_15M = "intraday_15m"
    DAILY_ONLY = "daily_only"
    UNAVAILABLE = "unavailable"


class SessionSourceState(str, Enum):
    LIVE = "live"
    DELAYED = "delayed"
    CACHED = "cached"
    STALE = "stale"
    TEST = "test"
    PARTIAL = "partial"
    MIXED = "mixed"
    UNAVAILABLE = "unavailable"


class SourceAvailabilityState(str, Enum):
    AVAILABLE = "available"
    PARTIAL = "partial"
    FALLBACK = "fallback"
    UNAVAILABLE = "unavailable"


class SessionConfidenceLabel(str, Enum):
    HIGH = "high"
    MODERATE = "moderate"
    LIMITED = "limited"


class SessionConfidenceEffect(str, Enum):
    SET = "set"
    CAP = "cap"
    NONE = "none"


class SessionAnalysisStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    DAILY_ONLY = "daily_only"
    UNAVAILABLE = "unavailable"


class SessionAnalysisState(str, Enum):
    REGULAR_SESSION = "regular_session"
    PREMARKET_ONLY = "premarket_only"
    AFTER_HOURS_ONLY = "after_hours_only"
    EXTENDED_HOURS_ONLY = "extended_hours_only"
    CLOSED_HOLIDAY = "closed_holiday"
    CLOSED_WEEKEND = "closed_weekend"
    DAILY_ONLY = "daily_only"
    UNAVAILABLE = "unavailable"


class SessionPhase(str, Enum):
    PREMARKET = "premarket"
    OPENING_PHASE = "opening_phase"
    OPEN = "opening_phase"  # Backward-compatible enum alias.
    MORNING = "morning"
    MIDDAY = "midday"
    AFTERNOON = "afternoon"
    FINAL_HOUR = "final_hour"
    CLOSE = "close"
    AFTER_HOURS = "after_hours"
    CLOSED = "closed"

    @classmethod
    def _missing_(cls, value: object) -> "SessionPhase | None":
        # Accept the original serialized value while emitting the canonical
        # Stage 8 segment name for all new results.
        if value == "open":
            return cls.OPENING_PHASE
        return None


REGULAR_SESSION_PHASES: frozenset[SessionPhase] = frozenset(
    {
        SessionPhase.OPENING_PHASE,
        SessionPhase.MORNING,
        SessionPhase.MIDDAY,
        SessionPhase.AFTERNOON,
        SessionPhase.FINAL_HOUR,
        SessionPhase.CLOSE,
    }
)


class ReferenceLevelKind(str, Enum):
    SUPPORT = "support"
    RESISTANCE = "resistance"


class BreakoutTestStatus(str, Enum):
    NOT_TESTED = "not_tested"
    TESTED_HELD = "tested_held"
    REJECTED = "rejected"
    UNCONFIRMED_BREAK = "unconfirmed_break"
    CONFIRMED_BREAK = "confirmed_break"


class CloseLocationBand(str, Enum):
    UPPER = "upper_quartile"
    MIDDLE = "middle_half"
    LOWER = "lower_quartile"
    UNDEFINED = "undefined"


class TrendState(str, Enum):
    UP = "up"
    DOWN = "down"
    SIDEWAYS = "sideways_or_mixed"


class PhaseDirection(str, Enum):
    UP = "up"
    DOWN = "down"
    FLAT = "flat"
    UNAVAILABLE = "unavailable"


class PhaseCompleteness(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    MISSING = "missing"
    UNASSESSED = "unassessed"


class TurningPointKind(str, Enum):
    PEAK = "peak"
    TROUGH = "trough"


class ReversalState(str, Enum):
    BULLISH = "bullish_reversal"
    BEARISH = "bearish_reversal"
    NONE = "none"


class VwapBasis(str, Enum):
    REPORTED_BAR_VWAP = "reported_bar_vwap"
    TYPICAL_PRICE_PROXY = "ohlc_typical_price_proxy"
    MIXED = "mixed_reported_and_proxy"
    UNAVAILABLE = "unavailable"


class PriceVwapRelation(str, Enum):
    ABOVE = "above"
    BELOW = "below"
    AT = "at"
    UNAVAILABLE = "unavailable"


class VolumePaceState(str, Enum):
    ABOVE = "above_expected"
    IN_LINE = "in_line"
    BELOW = "below_expected"
    UNAVAILABLE = "unavailable"


class VolumeConfirmationState(str, Enum):
    CONFIRMS_UP = "confirms_upward_price_path"
    CONFIRMS_DOWN = "confirms_downward_price_path"
    DOES_NOT_CONFIRM = "does_not_confirm_price_path"
    NEUTRAL = "neutral"
    UNAVAILABLE = "unavailable"


class CatalystCategory(str, Enum):
    EARNINGS = "earnings"
    GUIDANCE = "guidance"
    COMPANY_NEWS = "company_news"
    ANALYST_ACTION = "analyst_action"
    REGULATORY = "regulatory"
    MACRO = "macro"
    POLICY = "policy"
    MARKET_EVENT = "market_event"
    OTHER = "other"


class CatalystEventStatus(str, Enum):
    CONFIRMED = "confirmed"
    DEVELOPING = "developing"
    CORRECTED = "corrected"
    RETRACTED = "retracted"
    DISPUTED = "disputed"
    UNVERIFIED = "unverified"


class CatalystAttributionConfidence(str, Enum):
    LIMITED = "limited"
    UNAVAILABLE = "unavailable"


class EvidenceInterpretation(str, Enum):
    OBSERVED_FACT = "observed_fact"
    ENGINE_CONCLUSION = "engine_conclusion"
    MISSING_EVIDENCE = "missing_evidence"
    CONTRADICTION = "contradiction"


PositiveFloat = Annotated[float, Field(gt=0.0, allow_inf_nan=False)]
NonNegativeFloat = Annotated[float, Field(ge=0.0, allow_inf_nan=False)]
UnitFloat = Annotated[float, Field(ge=0.0, le=1.0, allow_inf_nan=False)]


def _validate_aware(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value


class MarketCalendarConfig(SessionContractModel):
    timezone_name: str = "America/New_York"
    premarket_open: time = time(4, 0)
    regular_open: time = time(9, 30)
    regular_close: time = time(16, 0)
    after_hours_close: time = time(20, 0)
    opening_phase_minutes: Annotated[int, Field(ge=5, le=120)] = 60
    morning_end: time = time(12, 0)
    midday_end: time = time(14, 0)
    final_hour_minutes: Annotated[int, Field(ge=30, le=120)] = 60
    close_phase_minutes: Annotated[int, Field(ge=5, le=60)] = 30
    holidays: frozenset[date] = frozenset()
    early_closes: dict[date, time] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_calendar(self) -> "MarketCalendarConfig":
        if self.timezone_name != "America/New_York":
            raise ValueError("session calendar timezone must be America/New_York")
        if not (
            self.premarket_open < self.regular_open < self.regular_close < self.after_hours_close
        ):
            raise ValueError("calendar boundaries must be strictly increasing")
        if not self.regular_open < self.morning_end < self.midday_end < self.regular_close:
            raise ValueError("morning and midday boundaries must fall inside the regular session")
        if self.close_phase_minutes >= self.final_hour_minutes:
            raise ValueError("close phase must be shorter than the configured final-hour window")
        for early_date, early_time in self.early_closes.items():
            if early_date in self.holidays or early_date.weekday() >= 5:
                raise ValueError("early closes must fall on open weekdays")
            if not self.regular_open < early_time <= self.regular_close:
                raise ValueError("early close must be after the open and no later than regular close")
        return self


class SessionBounds(SessionContractModel):
    session_date: date
    is_open: bool
    is_early_close: bool = False
    timezone_name: str = "America/New_York"
    premarket_open: datetime | None = None
    regular_open: datetime | None = None
    opening_phase_end: datetime | None = None
    morning_end: datetime | None = None
    midday_end: datetime | None = None
    final_hour_start: datetime | None = None
    close_phase_start: datetime | None = None
    regular_close: datetime | None = None
    after_hours_close: datetime | None = None


class IntradayBar(SessionContractModel):
    timestamp: datetime
    open: PositiveFloat
    high: PositiveFloat
    low: PositiveFloat
    close: PositiveFloat
    volume: Annotated[int, Field(ge=0)]
    aggregate_vwap: PositiveFloat | None = None
    transactions: Annotated[int, Field(ge=0)] | None = None
    is_final: bool = True

    @field_validator("timestamp")
    @classmethod
    def timestamp_is_aware(cls, value: datetime) -> datetime:
        return _validate_aware(value, "timestamp")

    @model_validator(mode="after")
    def validate_ohlc(self) -> "IntradayBar":
        values = (self.open, self.high, self.low, self.close)
        if not all(isfinite(value) for value in values):
            raise ValueError("OHLC values must be finite")
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("high must be at least every other OHLC value")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("low must be no greater than every other OHLC value")
        return self


class ReferenceLevel(SessionContractModel):
    level_id: Annotated[str, Field(min_length=1, max_length=120)]
    kind: ReferenceLevelKind
    price: PositiveFloat
    source_id: Annotated[str, Field(min_length=1, max_length=200)]
    as_of: datetime
    label: Annotated[str, Field(min_length=1, max_length=200)] | None = None

    @field_validator("as_of")
    @classmethod
    def as_of_is_aware(cls, value: datetime) -> datetime:
        return _validate_aware(value, "as_of")


class VolumeProfilePoint(SessionContractModel):
    minute_offset: Annotated[int, Field(ge=0, le=1_440)]
    cumulative_fraction: UnitFloat


class VolumeBaseline(SessionContractModel):
    expected_session_volume: Annotated[int, Field(gt=0)]
    as_of: datetime
    source_id: Annotated[str, Field(min_length=1, max_length=200)]
    cumulative_profile: tuple[VolumeProfilePoint, ...] = ()

    @field_validator("as_of")
    @classmethod
    def as_of_is_aware(cls, value: datetime) -> datetime:
        return _validate_aware(value, "as_of")

    @model_validator(mode="after")
    def profile_is_monotonic(self) -> "VolumeBaseline":
        offsets = [point.minute_offset for point in self.cumulative_profile]
        fractions = [point.cumulative_fraction for point in self.cumulative_profile]
        if offsets != sorted(set(offsets)):
            raise ValueError("volume profile offsets must be unique and increasing")
        if fractions != sorted(fractions):
            raise ValueError("volume profile cumulative fractions must be non-decreasing")
        return self


class CatalystEvent(SessionContractModel):
    event_id: Annotated[str, Field(min_length=1, max_length=160)]
    occurred_at: datetime
    published_at: datetime | None = None
    category: CatalystCategory
    headline: Annotated[str, Field(min_length=1, max_length=500)]
    source_id: Annotated[str, Field(min_length=1, max_length=200)]
    affected_entities: tuple[Annotated[str, Field(min_length=1, max_length=160)], ...] = ()
    event_status: CatalystEventStatus = CatalystEventStatus.CONFIRMED
    materiality: Annotated[int, Field(ge=0, le=100)] | None = None
    observation_window_minutes: Annotated[int, Field(ge=5, le=120)] = 15

    @field_validator("occurred_at", "published_at")
    @classmethod
    def event_times_are_aware(cls, value: datetime | None) -> datetime | None:
        return _validate_aware(value, "event timestamp") if value is not None else None

    @field_validator("affected_entities")
    @classmethod
    def affected_entities_are_unique(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(value.strip() for value in values)
        if any(not value for value in normalized):
            raise ValueError("affected entities cannot be blank")
        if len(normalized) != len(set(normalized)):
            raise ValueError("affected entities must be unique")
        return normalized


class SessionAnalysisInput(SessionContractModel):
    symbol: Annotated[str, Field(min_length=1, max_length=32, pattern=r"^[A-Z0-9.\-^]+$")]
    session_date: date
    interval: BarInterval
    data_mode: SessionDataMode
    bars: tuple[IntradayBar, ...] = ()
    prior_close: PositiveFloat | None = None
    reference_levels: tuple[ReferenceLevel, ...] = ()
    volume_baseline: VolumeBaseline | None = None
    catalysts: tuple[CatalystEvent, ...] = ()
    provider: Annotated[str, Field(min_length=1, max_length=100)]
    dataset: Annotated[str, Field(min_length=1, max_length=160)] = "intraday_ohlcv"
    source_id: Annotated[str, Field(min_length=1, max_length=200)]
    source_state: SessionSourceState
    generated_at: datetime
    observed_at: datetime
    now: datetime
    stale_after_seconds: Annotated[int, Field(gt=0, le=86_400)] = 900
    test_data: bool = False

    @field_validator("generated_at", "observed_at", "now")
    @classmethod
    def timestamps_are_aware(cls, value: datetime) -> datetime:
        return _validate_aware(value, "analysis timestamp")

    @model_validator(mode="after")
    def validate_source_and_bars(self) -> "SessionAnalysisInput":
        if self.data_mode is SessionDataMode.INTRADAY_5M and self.interval is not BarInterval.FIVE_MINUTES:
            raise ValueError("intraday_5m data mode requires 5m bars")
        if self.data_mode is SessionDataMode.INTRADAY_15M and self.interval is not BarInterval.FIFTEEN_MINUTES:
            raise ValueError("intraday_15m data mode requires 15m bars")
        if self.data_mode in {SessionDataMode.DAILY_ONLY, SessionDataMode.UNAVAILABLE} and self.bars:
            raise ValueError("daily-only or unavailable inputs cannot contain intraday bars")
        # An empty intraday observation set is valid at the analytical boundary:
        # the injected calendar may identify a holiday/weekend closure. On an
        # open date the engine fails closed as unavailable rather than inferring
        # a session from absent bars.
        if (
            self.data_mode in {SessionDataMode.INTRADAY_5M, SessionDataMode.INTRADAY_15M}
            and self.source_state is SessionSourceState.UNAVAILABLE
        ):
            raise ValueError("unavailable sources cannot supply eligible intraday bars")
        if self.test_data != (self.source_state is SessionSourceState.TEST):
            raise ValueError("test_data and source_state=test must be declared together")
        if self.generated_at > self.now or self.observed_at > self.now:
            raise ValueError("generated_at and observed_at cannot be later than injected now")
        if self.volume_baseline is not None and self.volume_baseline.as_of > self.now:
            raise ValueError("volume baseline cannot be dated after injected now")
        if any(level.as_of > self.now for level in self.reference_levels):
            raise ValueError("reference levels cannot be dated after injected now")
        if any(event.occurred_at > self.observed_at for event in self.catalysts):
            raise ValueError("catalyst events cannot occur after the observation boundary")
        if any(
            event.published_at is not None and event.published_at > self.now
            for event in self.catalysts
        ):
            raise ValueError("catalyst publication times cannot be later than injected now")
        event_ids = [event.event_id for event in self.catalysts]
        if len(event_ids) != len(set(event_ids)):
            raise ValueError("catalyst event IDs must be unique")
        provider = self.provider.strip().casefold().replace("-", "_")
        test_provider = provider in {"mock", "test", "fixture", "generated_test_data"} or provider.startswith(
            ("mock_", "test_", "fixture_")
        )
        if test_provider and not self.test_data:
            raise ValueError("mock, fixture, or test providers cannot be represented as live data")
        timestamps = [bar.timestamp for bar in self.bars]
        if timestamps != sorted(timestamps) or len(timestamps) != len(set(timestamps)):
            raise ValueError("bars must have unique timestamps in increasing order")
        for timestamp in timestamps:
            if timestamp.second or timestamp.microsecond or timestamp.minute % self.interval.minutes:
                raise ValueError("bar timestamps must align to the declared interval")
        return self


class SegmentedBar(SessionContractModel):
    timestamp: datetime
    phase: SessionPhase
    included_in_regular_session: bool
    included_in_analysis: bool


class PhaseAggregate(SessionContractModel):
    phase: SessionPhase
    observed_bars: Annotated[int, Field(ge=0)]
    expected_bars: Annotated[int, Field(ge=0)]
    coverage: UnitFloat | None = None
    open: PositiveFloat | None = None
    high: PositiveFloat | None = None
    low: PositiveFloat | None = None
    close: PositiveFloat | None = None
    return_pct: float | None = None
    volume: Annotated[int, Field(ge=0)] = 0
    range_points: NonNegativeFloat | None = None
    range_pct_of_open: NonNegativeFloat | None = None
    direction: PhaseDirection = PhaseDirection.UNAVAILABLE
    volatility_proxy_pct: NonNegativeFloat | None = None
    volatility_proxy_method: str = "root_mean_square_close_return_pct"
    close_location: UnitFloat | None = None
    close_location_band: CloseLocationBand = CloseLocationBand.UNDEFINED
    completeness: PhaseCompleteness = PhaseCompleteness.UNASSESSED
    limitations: tuple[str, ...] = ()


class SessionStructure(SessionContractModel):
    open: PositiveFloat
    high: PositiveFloat
    low: PositiveFloat
    close: PositiveFloat
    high_at: datetime
    low_at: datetime
    prior_close: PositiveFloat | None = None
    gap_pct: float | None = None
    range_points: NonNegativeFloat
    range_pct_of_open: NonNegativeFloat
    close_location: UnitFloat | None = None
    close_location_band: CloseLocationBand
    net_change_pct: float
    directional_efficiency: UnitFloat
    trend: TrendState
    reversal: ReversalState


class VwapAnalysis(SessionContractModel):
    session_vwap: PositiveFloat | None = None
    basis: VwapBasis
    reported_vwap_volume_coverage: UnitFloat
    last_price_deviation_pct: float | None = None
    last_price_relation: PriceVwapRelation
    disclosure: str


class PhaseVolume(SessionContractModel):
    phase: SessionPhase
    volume: Annotated[int, Field(ge=0)]
    observed_share: UnitFloat


class VolumeAnalysis(SessionContractModel):
    observed_volume: Annotated[int, Field(ge=0)]
    expected_volume_to_observation: float | None = None
    expected_cumulative_fraction: UnitFloat | None = None
    pace_ratio: NonNegativeFloat | None = None
    pace_state: VolumePaceState
    confirmation: VolumeConfirmationState
    by_phase: tuple[PhaseVolume, ...]
    baseline_source_id: str | None = None
    disclosure: str


class LevelTest(SessionContractModel):
    level_id: str
    kind: ReferenceLevelKind
    price: PositiveFloat
    touched: bool
    breached_intrabar: bool
    closed_beyond: bool
    status: BreakoutTestStatus
    source_id: str
    disclosure: str


class TurningPointSupportBar(SessionContractModel):
    timestamp: datetime
    close: PositiveFloat

    @field_validator("timestamp")
    @classmethod
    def timestamp_is_aware(cls, value: datetime) -> datetime:
        return _validate_aware(value, "turning-point support timestamp")


class TurningPointRecord(SessionContractModel):
    turning_point_id: Annotated[str, Field(min_length=1, max_length=240)]
    kind: TurningPointKind
    timestamp: datetime
    phase: SessionPhase
    price: PositiveFloat
    supporting_bars: tuple[TurningPointSupportBar, ...]
    movement_magnitude_pct: PositiveFloat
    evidence_ids: tuple[Annotated[str, Field(min_length=1, max_length=240)], ...]
    confidence: SessionConfidenceLabel
    limitations: tuple[Annotated[str, Field(min_length=1, max_length=500)], ...]

    @field_validator("timestamp")
    @classmethod
    def timestamp_is_aware(cls, value: datetime) -> datetime:
        return _validate_aware(value, "turning-point timestamp")

    @model_validator(mode="after")
    def require_support_and_lineage(self) -> "TurningPointRecord":
        if len(self.supporting_bars) < 5:
            raise ValueError("turning points require a five-bar support window")
        if not self.evidence_ids:
            raise ValueError("turning points require evidence IDs")
        if not self.limitations:
            raise ValueError("turning points require explicit limitations")
        return self


class CatalystReactionWindow(SessionContractModel):
    start: datetime
    end: datetime
    requested_minutes: Annotated[int, Field(ge=5, le=120)]
    eligible_bar_starts: tuple[datetime, ...] = ()

    @field_validator("start", "end")
    @classmethod
    def timestamps_are_aware(cls, value: datetime) -> datetime:
        return _validate_aware(value, "catalyst reaction-window timestamp")

    @field_validator("eligible_bar_starts")
    @classmethod
    def eligible_starts_are_aware(cls, values: tuple[datetime, ...]) -> tuple[datetime, ...]:
        return tuple(_validate_aware(value, "eligible reaction bar timestamp") for value in values)

    @model_validator(mode="after")
    def window_is_ordered(self) -> "CatalystReactionWindow":
        if self.end <= self.start:
            raise ValueError("catalyst reaction window must end after it starts")
        return self


class CatalystTimelineItem(SessionContractModel):
    event_id: str
    category: CatalystCategory
    headline: str
    occurred_at: datetime
    published_at: datetime | None = None
    phase: SessionPhase
    source_id: str
    affected_entities: tuple[str, ...] = ()
    event_status: CatalystEventStatus
    materiality: Annotated[int, Field(ge=0, le=100)] | None = None
    reaction_window: CatalystReactionWindow
    price_before: PositiveFloat | None = None
    price_after: PositiveFloat | None = None
    observed_response_pct: float | None = None
    attribution_confidence: CatalystAttributionConfidence
    attribution_limitations: tuple[str, ...]
    relationship: str = "temporal_proximity_only"
    disclosure: str = "Temporal proximity does not establish causality."


class SessionEvidence(SessionContractModel):
    evidence_id: Annotated[str, Field(min_length=1, max_length=240)]
    entity: str
    metric: str
    value: Any
    unit: str | None = None
    timeframe: str = "current completed portion of session"
    statement: str
    interpretation: EvidenceInterpretation
    source_id: str
    phase: SessionPhase | None = None
    contradicts_evidence_ids: tuple[str, ...] = ()


class ConfidenceContribution(SessionContractModel):
    rule: str
    effect: SessionConfidenceEffect
    resulting_cap: SessionConfidenceLabel | None = None
    reason: str


class SessionConfidence(SessionContractModel):
    label: SessionConfidenceLabel
    maximum_allowed: SessionConfidenceLabel
    constrained: bool
    contributions: tuple[ConfidenceContribution, ...]
    engine_version: str


class SessionContradictions(SessionContractModel):
    supporting_evidence_ids: tuple[str, ...]
    opposing_evidence_ids: tuple[str, ...]
    neutral_evidence_ids: tuple[str, ...]
    explicit_contradiction_evidence_ids: tuple[str, ...]
    engine_version: str


class SessionFreshness(SessionContractModel):
    state: SessionSourceState
    availability: SourceAvailabilityState
    age_seconds: NonNegativeFloat | None = None
    completeness: UnitFloat
    provider: str
    warnings: tuple[str, ...]
    engine_version: str


class SessionQuality(SessionContractModel):
    is_calendar_session: bool
    is_early_close: bool
    session_complete: bool
    expected_regular_bars: Annotated[int, Field(ge=0)]
    observed_regular_bars: Annotated[int, Field(ge=0)]
    regular_session_coverage: UnitFloat
    missing_regular_bar_starts: tuple[datetime, ...]
    excluded_closed_hours_bars: Annotated[int, Field(ge=0)]
    excluded_unfinalized_bars: Annotated[int, Field(ge=0)]
    freshness: SessionFreshness
    warnings: tuple[str, ...]


class SessionAnalysisResult(SessionContractModel):
    engine_version: str = SESSION_ENGINE_VERSION
    symbol: str
    session_date: date
    status: SessionAnalysisStatus
    analysis_state: SessionAnalysisState = SessionAnalysisState.UNAVAILABLE
    data_mode: SessionDataMode
    interval: BarInterval
    source_id: str
    segmented_bars: tuple[SegmentedBar, ...] = ()
    phases: tuple[PhaseAggregate, ...] = ()
    structure: SessionStructure | None = None
    vwap: VwapAnalysis | None = None
    volume: VolumeAnalysis | None = None
    level_tests: tuple[LevelTest, ...] = ()
    turning_points: tuple[TurningPointRecord, ...] = ()
    catalyst_timeline: tuple[CatalystTimelineItem, ...] = ()
    quality: SessionQuality
    evidence: tuple[SessionEvidence, ...] = ()
    contradictions: SessionContradictions
    confidence: SessionConfidence
    limitations: tuple[str, ...]
    causality_disclosure: str = (
        "The analysis reports observed price, volume, and event timing relationships only; "
        "it does not infer that any event caused a market move."
    )
