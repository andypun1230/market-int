from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


SourceState = Literal["live", "delayed", "cached", "stale", "mock", "mixed", "unavailable"]


class QuoteData(BaseModel):
    symbol: str
    price: float
    change: float
    change_percent: float
    open: float | None
    high: float | None
    low: float | None
    previous_close: float | None
    volume: float | None
    timestamp: str
    source: str
    is_live: bool
    is_stale: bool
    fallback_used: bool
    provider: str | None = None
    requested_provider: str | None = None
    original_provider: str | None = None
    source_state: SourceState | None = None
    fetched_at: str | None = None
    cache_hit: bool = False
    cache_age_seconds: int | None = None
    memory_cache_hit: bool = False
    persistent_cache_hit: bool = False
    expires_at: str | None = None
    stale_until: str | None = None
    background_refresh_started: bool = False
    capability_state: str | None = None
    fallback_reason: str | None = None


class CandleData(BaseModel):
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class HistoryData(BaseModel):
    symbol: str
    candles: list[CandleData]
    timeframe: str
    source: str
    is_live: bool
    is_stale: bool
    fallback_used: bool
    as_of: str
    adjusted: bool = True
    requested_days: int | None = None
    returned_candles: int | None = None
    error_message: str | None = None
    provider: str | None = None
    requested_provider: str | None = None
    original_provider: str | None = None
    source_state: SourceState | None = None
    fetched_at: str | None = None
    cache_hit: bool = False
    cache_age_seconds: int | None = None
    memory_cache_hit: bool = False
    persistent_cache_hit: bool = False
    expires_at: str | None = None
    stale_until: str | None = None
    background_refresh_started: bool = False
    capability_state: str | None = None
    fallback_reason: str | None = None


class ProviderCapabilities(BaseModel):
    quotes: bool
    daily_history: bool
    intraday_history: bool
    adjusted_history: bool
    volume: bool


class ProviderHealth(BaseModel):
    provider: str
    enabled: bool
    configured: bool
    reachable: bool
    last_successful_request: str | None
    last_error: str | None
    fallback_active: bool
    capabilities: ProviderCapabilities | None = None
    status: str | None = None
    checked_at: str | None = None
    response_time_ms: float | None = None
    last_success_at: str | None = None
    last_failure_at: str | None = None
    recent_error_count: int = 0
    rate_limit_state: str | None = None
    message: str | None = None


class DataFallbackMetadata(BaseModel):
    used: bool = False
    reason: str | None = None
    original_provider: str | None = None


class DataFreshnessMetadata(BaseModel):
    provider: str
    source_state: SourceState
    fetched_at: datetime
    market_timestamp: datetime | None = None
    cache_hit: bool = False
    cache_age_seconds: int | None = None
    expires_at: datetime | None = None
    fallback_used: bool = False
    is_stale: bool = False


class NormalizedQuote(BaseModel):
    symbol: str
    price: float | None
    open: float | None
    high: float | None
    low: float | None
    previous_close: float | None
    change: float | None
    change_percent: float | None
    volume: float | None
    market_timestamp: datetime | None
    provider: str
    source_state: SourceState
    fetched_at: datetime
    is_market_open: bool | None = None
    currency: str | None = None
    exchange: str | None = None
    freshness: DataFreshnessMetadata | None = None
    fallback: DataFallbackMetadata = Field(default_factory=DataFallbackMetadata)

    @field_validator("price", "open", "high", "low", "previous_close", "change", "volume")
    @classmethod
    def validate_prices(cls, value: float | None, info):
        if value is None:
            return value
        if info.field_name != "change" and value < 0:
            raise ValueError(f"{info.field_name} cannot be negative")
        return value

    @model_validator(mode="after")
    def validate_high_low(self):
        comparable = [value for value in (self.open, self.low, self.price) if value is not None]
        if self.high is not None and comparable and self.high < max(comparable):
            raise ValueError("high must be at least open, low, and price")
        comparable_low = [value for value in (self.open, self.high, self.price) if value is not None]
        if self.low is not None and comparable_low and self.low > min(comparable_low):
            raise ValueError("low must be no greater than open, high, and price")
        return self


class NormalizedOHLCVBar(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float | None

    @model_validator(mode="after")
    def validate_ohlcv(self):
        if min(self.open, self.high, self.low, self.close) <= 0:
            raise ValueError("OHLC values must be positive")
        if self.high < max(self.open, self.low, self.close):
            raise ValueError("high must be at least open, low, and close")
        if self.low > min(self.open, self.high, self.close):
            raise ValueError("low must be no greater than open, high, and close")
        if self.volume is not None and self.volume < 0:
            raise ValueError("volume cannot be negative")
        return self


class NormalizedPriceHistory(BaseModel):
    symbol: str
    interval: Literal["1d"] = "1d"
    bars: list[NormalizedOHLCVBar]
    provider: str
    source_state: SourceState
    fetched_at: datetime
    start_at: datetime | None = None
    end_at: datetime | None = None
    currency: str | None = None
    exchange: str | None = None
    freshness: DataFreshnessMetadata | None = None
    fallback: DataFallbackMetadata = Field(default_factory=DataFallbackMetadata)

    @model_validator(mode="after")
    def validate_bars(self):
        seen: set[datetime] = set()
        previous: datetime | None = None
        unique_bars: list[NormalizedOHLCVBar] = []
        for bar in sorted(self.bars, key=lambda item: item.timestamp):
            if bar.timestamp in seen:
                continue
            if previous and bar.timestamp < previous:
                raise ValueError("bars must be sorted ascending")
            seen.add(bar.timestamp)
            previous = bar.timestamp
            unique_bars.append(bar)
        self.bars = unique_bars
        if self.bars:
            self.start_at = self.start_at or self.bars[0].timestamp
            self.end_at = self.end_at or self.bars[-1].timestamp
        return self


class BatchQuoteResult(BaseModel):
    quotes: list[QuoteData]
    unavailable_symbols: list[str] = Field(default_factory=list)
    provider: str
    source_state: SourceState
    fetched_at: datetime
