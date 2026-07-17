from pydantic import BaseModel


class SourceMetadata(BaseModel):
    source: str
    is_live: bool
    is_stale: bool
    fallback_used: bool
    as_of: str
    quality_score: float | None = None
    warnings: list[str] = []


class SentimentComponentData(BaseModel):
    key: str
    label: str
    score: float
    status: str
    value: float | None = None
    previous_value: float | None = None
    trend: str
    explanation: str
    metadata: SourceMetadata


class MarketSentimentData(BaseModel):
    score: float
    status: str
    confidence: float
    components: list[SentimentComponentData]
    summary: str
    metadata: SourceMetadata


class OptionContractData(BaseModel):
    ticker: str
    underlying: str
    expiration: str
    strike: float
    option_type: str
    bid: float | None = None
    ask: float | None = None
    last: float | None = None
    volume: int | None = None
    open_interest: int | None = None
    implied_volatility: float | None = None
    delta: float | None = None
    gamma: float | None = None
    theta: float | None = None
    vega: float | None = None
    underlying_price: float | None = None
    timestamp: str


class OptionsChainData(BaseModel):
    underlying: str
    contracts: list[OptionContractData]
    metadata: SourceMetadata


class TradePrintData(BaseModel):
    symbol: str
    price: float
    size: int
    notional: float
    exchange: str | None = None
    conditions: list[str] = []
    timestamp: str


class BlockTradeCandidate(BaseModel):
    symbol: str
    price: float
    size: int
    notional: float
    relative_size: float
    classification: str
    confidence: float
    reason: str
    timestamp: str
    metadata: SourceMetadata


class LiquidityData(BaseModel):
    symbol: str
    average_daily_volume: float | None = None
    average_dollar_volume: float | None = None
    bid: float | None = None
    ask: float | None = None
    spread: float | None = None
    spread_percent: float | None = None
    relative_volume: float | None = None
    liquidity_score: float
    status: str
    institutional_capacity: str
    summary: str
    metadata: SourceMetadata
