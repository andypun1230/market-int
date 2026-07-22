from typing import Any, Dict, List

from pydantic import BaseModel, Field


class BriefResponse(BaseModel):
    regime: str
    drivers: List[str]
    risks: List[str]
    top_sectors: List[str]
    summary: str


class TrendResponse(BaseModel):
    spy: str
    qqq: str
    iwm: str
    dji: str


class BreadthResponse(BaseModel):
    status: str
    stocks_above_20ma: int
    stocks_above_50ma: int
    stocks_above_200ma: int
    advance_decline_ratio: float | None
    advance_decline_ratio_smoothed: float | None = None


class VolatilityResponse(BaseModel):
    vix: float
    status: str


class RegimeInstitutionalActivityResponse(BaseModel):
    distribution_days: int
    accumulation_days: int
    follow_through_day: str


class RegimeResponse(BaseModel):
    status: str
    trend: TrendResponse
    breadth: BreadthResponse
    volatility: VolatilityResponse
    institutional_activity: RegimeInstitutionalActivityResponse
    explanation: str
    breadth_snapshot_id: str | None = None
    universe_version: str | None = None
    market_date: str | None = None


class SectorLeader(BaseModel):
    rank: int
    name: str
    status: str
    change: str
    return_1d: float
    return_1w: float
    return_mtd: float
    return_ytd: float
    daily_change_percent: float
    weekly_change_percent: float
    monthly_change_percent: float
    relative_strength_score: int
    percent_above_50ema: float
    advancing_stocks: int
    declining_stocks: int
    data_source: str | None = None
    overall_mode: str | None = None
    coverage_percent: float | None = None
    successful_symbols: int | None = None
    fallback_used: bool | None = None
    as_of: str | None = None
    history_quality_score: int | None = None


class SectorsResponse(BaseModel):
    leaders: List[SectorLeader]
    summary: str
    overall_mode: str | None = None
    coverage_percent: float | None = None
    as_of: str | None = None
    snapshot_id: str | None = None
    universe_id: str | None = None
    universe_version: str | None = None
    market_date: str | None = None
    source_state: str | None = None


class IndustryGroupItem(BaseModel):
    rank: int
    name: str
    parent_sector: str
    score: int
    status: str
    return_1d: float
    return_1w: float
    return_mtd: float
    return_ytd: float
    return_1m: float | None = None
    return_3m: float | None = None
    return_6m: float | None = None
    return_1y: float | None = None
    relative_strength_score: int
    breadth_above_50ema: float
    percent_above_20ema: float | None = None
    percent_above_50ema: float | None = None
    percent_above_200ema: float | None = None
    advancing_stocks: int | None = None
    declining_stocks: int | None = None
    unchanged_stocks: int | None = None
    new_highs: int | None = None
    new_lows: int | None = None
    volume_participation: float | None = None
    trend_direction: str | None = None
    data_source: str | None = None
    overall_mode: str | None = None
    coverage_percent: float | None = None
    successful_symbols: int | None = None
    fallback_used: bool | None = None
    as_of: str | None = None
    history_quality_score: int | None = None
    provenance: Dict[str, Any] = Field(default_factory=dict)


class IndustryGroupResponse(BaseModel):
    items: List[IndustryGroupItem]
    summary: str
    overall_mode: str | None = None
    coverage_percent: float | None = None
    as_of: str | None = None
    theme_provenance: Dict[str, Any] = Field(default_factory=dict)


class WatchlistItem(BaseModel):
    ticker: str
    trend: str
    setup: str
    support_zone: str
    risk_flag: str
    price: float | None = None
    change: float | None = None
    change_percent: float | None = None
    data_source: str | None = None
    provider: str | None = None
    source_state: str | None = None
    quote_timestamp: str | None = None
    saved_at: str | None = None
    sort_order: int | None = None
    is_live: bool | None = None
    is_stale: bool | None = None
    stale: bool | None = None
    fallback_used: bool | None = None
    as_of: str | None = None


class WatchlistResponse(BaseModel):
    items: List[WatchlistItem]


class RiskResponse(BaseModel):
    risk_level: str
    main_risks: List[str]
    suggested_positioning: str


class IndexSnapshot(BaseModel):
    symbol: str
    display_symbol: str | None = None
    provider_symbol: str | None = None
    display_name: str | None = None
    asset_type: str | None = None
    price: float
    change: float
    change_percent: float
    previous_close: float | None = None
    volume: int | float | None
    ema_20: float | None
    ema_50: float | None
    ema_200: float | None
    sma_50: float | None
    rsi_14: float | None
    trend: str | None = None
    quote_timestamp: str | None = None
    history_latest_date: str | None = None
    quote_provider: str | None = None
    history_provider: str | None = None
    source_state: str | None = None
    stale: bool | None = None
    warnings: list[str] | None = None
    data_source: str | None = None
    is_live: bool | None = None
    is_stale: bool | None = None
    fallback_used: bool | None = None
    as_of: str | None = None
    quote_is_live: bool | None = None
    history_is_live: bool | None = None
    analysis_is_live: bool | None = None
    history_quality_score: int | None = None


class IndexesResponse(BaseModel):
    indexes: List[IndexSnapshot]


class IndexHistoryResponse(BaseModel):
    symbol: str
    closes: List[float]
    data_source: str | None = None
    is_live: bool | None = None
    is_stale: bool | None = None
    fallback_used: bool | None = None
    as_of: str | None = None
    history_quality_score: int | None = None


class MarketBreadthResponse(BaseModel):
    total_stocks: int
    advancing_stocks: int
    declining_stocks: int
    unchanged_stocks: int
    advance_decline_ratio: float | None
    advance_decline_ratio_display: str | None = None
    advance_decline_ratio_smoothed: float | None = None
    ratio_method: str | None = None
    percent_above_20ema: float
    percent_above_50ema: float
    percent_above_200ema: float
    new_52w_highs: int
    new_52w_lows: int
    breadth_score: int | None = None
    breadth_status: str | None = None
    universe: str | None = None
    universe_size: int | None = None
    successful_symbols: int | None = None
    coverage_percent: float | None = None
    overall_mode: str | None = None
    fallback_used: bool | None = None
    as_of: str | None = None
    history_quality_score: int | None = None
    snapshot_id: str | None = None
    universe_version: str | None = None
    market_date: str | None = None
    coverage_status: str | None = None
    trend: str | None = None
    confidence: str | None = None
    source_state: str | None = None
    providers: list[str] | None = None
    warnings: list[str] | None = None
    coverage_dimensions: dict[str, Any] | None = None
    data_confidence: dict[str, Any] | None = None
    signal_confidence: dict[str, Any] | None = None


class SectorBreadthItem(BaseModel):
    sector: str
    total_stocks: int
    advancing_stocks: int
    declining_stocks: int
    percent_above_50ema: float
    overall_mode: str | None = None
    coverage_percent: float | None = None
    successful_symbols: int | None = None
    universe_size: int | None = None
    as_of: str | None = None
    history_quality_score: int | None = None
    unchanged_stocks: int | None = None
    percent_above_20ema: float | None = None
    percent_above_200ema: float | None = None
    new_52w_highs: int | None = None
    new_52w_lows: int | None = None
    breadth_score: float | None = None
    breadth_status: str | None = None


class SectorBreadthResponse(BaseModel):
    market: MarketBreadthResponse
    sectors: List[SectorBreadthItem]


class Candle(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class PatternKeyLevels(BaseModel):
    support: float | None = None
    neckline: float | None = None
    breakout: float | None = None
    stop_reference: float | None = None


class PatternMarker(BaseModel):
    date: str
    label: str
    price: float


class VolumeConfirmation(BaseModel):
    volume_quality: str
    relative_volume: float | None
    signals: List[str]
    summary: str


class DetectedPattern(BaseModel):
    id: str
    symbol: str
    name: str
    type: str
    direction: str
    status: str
    confidence: int
    timeframe: str
    description: str
    key_levels: PatternKeyLevels
    chart_data: List[Candle]
    markers: List[PatternMarker]
    volume_confirmation: VolumeConfirmation | None = None
    data_source: str | None = "mock"
    is_live: bool | None = False


class PatternResponse(BaseModel):
    symbol: str
    patterns: List[DetectedPattern]


class PriceZone(BaseModel):
    low: float
    high: float
    strength: int
    reason: str


class MovingAverageSupport(BaseModel):
    ema_20: float | None
    ema_50: float | None


class SupportResistanceResponse(BaseModel):
    symbol: str
    current_price: float
    support_zones: List[PriceZone]
    resistance_zones: List[PriceZone]
    breakout_level: float | None
    stop_reference: float | None
    moving_average_support: MovingAverageSupport
    data_source: str | None = None
    analysis_is_live: bool | None = None
    fallback_used: bool | None = None
    as_of: str | None = None
    history_quality_score: int | None = None


class TrendlineDetail(BaseModel):
    detected: bool
    slope: float | None
    touch_count: int
    start_date: str | None
    end_date: str | None
    start_price: float | None
    end_price: float | None
    current_line_value: float | None
    distance_percent: float | None
    status: str


class TrendlineBreak(BaseModel):
    broken: bool
    direction: str
    description: str


class TrendlineResponse(BaseModel):
    symbol: str
    current_price: float
    rising_support: TrendlineDetail
    falling_resistance: TrendlineDetail
    trendline_break: TrendlineBreak
    summary: str
    data_source: str | None = None
    analysis_is_live: bool | None = None
    fallback_used: bool | None = None
    as_of: str | None = None
    history_quality_score: int | None = None


class VolumeAnalysis(BaseModel):
    symbol: str
    average_volume_20: int | None
    relative_volume: float | None
    status: str
    signals: List[str]
    volume_quality: str
    volume_quality_score: int
    distribution_volume: bool
    accumulation_volume: bool
    dry_up: bool
    climax_run: bool
    breakout_volume: bool
    summary: str
    data_source: str | None = None
    analysis_is_live: bool | None = None
    fallback_used: bool | None = None
    as_of: str | None = None
    history_quality_score: int | None = None


class VolumeAnalysisResponse(BaseModel):
    items: List[VolumeAnalysis]
    summary: str


class RiskPlan(BaseModel):
    symbol: str
    current_price: float
    entry: float
    stop_loss: float
    target_1: float
    target_2: float
    atr_14: float | None
    risk_percent: float
    reward_percent_target_1: float
    reward_percent_target_2: float
    risk_reward_target_1: float
    risk_reward_target_2: float
    volatility_level: str
    risk_level: str
    position_size_note: str
    summary: str
    data_quality: Dict[str, Any] | None = None


class RiskPlanResponse(BaseModel):
    items: List[RiskPlan]
    summary: str


class TimeframeAnalysis(BaseModel):
    timeframe: str
    trend: str
    price_vs_ema20: str
    price_vs_ema50: str
    momentum: str
    structure: str
    score: int


class MultiTimeframeItem(BaseModel):
    symbol: str
    alignment: str
    alignment_score: int
    timeframes: List[TimeframeAnalysis]
    summary: str
    data_source: str | None = "mock"
    is_live: bool | None = False


class MultiTimeframeResponse(BaseModel):
    items: List[MultiTimeframeItem]
    summary: str


class TimeframeSignalEvidence(BaseModel):
    key: str
    label: str
    value: Any | None = None
    sourceStatus: str | None = None


class TimeframeSignalInput(BaseModel):
    key: str
    label: str
    timeframe: str
    contribution: float | None = None
    weight: float
    value: Any | None = None
    sourceStatus: str
    available: bool


class TimeframeTechnicalSignal(BaseModel):
    timeframe: str
    horizonLabel: str
    signal: str
    score: int | None
    strength: str
    headline: str
    explanation: str
    positiveEvidence: List[TimeframeSignalEvidence]
    negativeEvidence: List[TimeframeSignalEvidence]
    availableInputs: int
    requiredInputs: int
    dataStatus: str
    asOf: str | None = None
    inputs: List[TimeframeSignalInput] = []


class MultiTimeframeTechnicalSignals(BaseModel):
    short: TimeframeTechnicalSignal
    medium: TimeframeTechnicalSignal
    long: TimeframeTechnicalSignal
    overallDataStatus: str
    generatedAt: str | None = None
    methodologyVersion: str


class StockLeadershipSignal(BaseModel):
    signal: str
    score: int | None
    strength: str
    explanation: str
    positiveEvidence: List[str]
    limitingEvidence: List[str]
    availableInputs: int
    requiredInputs: int
    dataStatus: str
    asOf: str | None = None
    methodologyVersion: str


class RelativeStrengthItem(BaseModel):
    symbol: str
    sector: str
    rs_vs_spy: int
    rs_vs_qqq: int
    rs_vs_sector: int
    return_5d: float
    return_20d: float
    return_60d: float
    benchmark_return_20d: float
    sector_return_20d: float
    overall_rs_score: int
    rank: int
    status: str
    explanation: str
    data_source: str | None = None
    analysis_is_live: bool | None = None
    fallback_used: bool | None = None
    as_of: str | None = None
    history_quality_score: int | None = None
    comparisons_requested: List[str] | None = None
    comparisons_available: List[str] | None = None
    comparisons_missing: List[str] | None = None
    coverage_ratio: float | None = None
    degraded: bool | None = None
    degradation_reason: str | None = None
    confidence_state: str | None = None


class RelativeStrengthResponse(BaseModel):
    items: List[RelativeStrengthItem]
    summary: str


class StockRatingComponents(BaseModel):
    relative_strength: int
    pattern_quality: int
    sector_strength: int
    market_alignment: int
    institutional_support: int
    risk_control: int


class StockRatingItem(BaseModel):
    symbol: str
    overall_score: int
    rating: str
    status: str
    components: StockRatingComponents
    risk_level: str
    strengths: List[str]
    warnings: List[str]
    explanation: str
    data_quality: Dict[str, Any] | None = None


class StockRatingResponse(BaseModel):
    items: List[StockRatingItem]
    summary: str


class InstitutionalDay(BaseModel):
    date: str
    close: float
    volume: int
    change_percent: float
    reason: str


class FollowThroughDay(BaseModel):
    triggered: bool
    date: str | None = None
    index: str | None = None
    gain_percent: float | None = None


class IndexInstitutionalActivity(BaseModel):
    symbol: str
    distribution_days: List[InstitutionalDay]
    accumulation_days: List[InstitutionalDay]
    stall_days: List[InstitutionalDay]
    churning_days: List[InstitutionalDay]
    follow_through_day: FollowThroughDay


class InstitutionalBias(BaseModel):
    bias: str
    summary: str
    distribution_count: int
    accumulation_count: int
    stall_count: int
    churning_count: int
    follow_through_day: FollowThroughDay


class InstitutionalActivityResponse(BaseModel):
    bias: InstitutionalBias
    indexes: List[IndexInstitutionalActivity]


class MarketHealthComponents(BaseModel):
    momentum: int
    breadth: int
    trend: int
    volume: int
    institutional: int
    volatility: int
    sector_strength: int


class MarketHealthResponse(BaseModel):
    overall_score: int
    status: str
    components: MarketHealthComponents
    component_explanations: Dict[str, str]
    summary: str
    improving_factors: List[str]
    weakening_factors: List[str]
    decision_confidence: Dict[str, Any] | None = None
    data_quality: Dict[str, Any] | None = None
    breadth_snapshot_id: str | None = None
    universe_version: str | None = None
    market_date: str | None = None


class SectorEtfItem(BaseModel):
    symbol: str
    name: str
    sector: str
    price: float
    change_percent: float
    return_1d: float
    return_1w: float
    return_mtd: float
    return_ytd: float
    return_1m: float
    return_3m: float | None = None
    return_6m: float | None = None
    return_1y: float | None = None
    relative_strength_score: int
    volume_trend: str
    status: str
    data_source: str | None = None
    quote_source: str | None = None
    history_source: str | None = None
    quote_is_live: bool | None = None
    history_is_live: bool | None = None
    fallback_used: bool | None = None
    as_of: str | None = None
    history_quality_score: int | None = None
    ema_20: float | None = None
    ema_50: float | None = None
    trend_status: str | None = None
    rotation_score: int | None = None


class SectorEtfResponse(BaseModel):
    items: List[SectorEtfItem]
    summary: str
    overall_mode: str | None = None
    coverage_percent: float | None = None
    as_of: str | None = None


class MarketCapRotationItem(BaseModel):
    category: str
    symbol: str
    score: int
    return_1w: float
    return_1m: float
    relative_strength: int
    money_flow: str
    status: str


class MarketCapRotationResponse(BaseModel):
    items: List[MarketCapRotationItem]
    leader: str
    laggard: str
    summary: str


class FearGreedComponent(BaseModel):
    key: str
    label: str
    score: int
    status: str
    explanation: str
    source: str | None = None
    source_timestamp: str | None = None
    data_state: str | None = None
    confidence: int | None = None
    missing: bool | None = None
    warnings: List[str] | None = None


class FearGreedResponse(BaseModel):
    score: int | None
    status: str
    components: List[FearGreedComponent]
    summary: str
    title: str | None = None
    subtitle: str | None = None
    source: str | None = None
    source_type: str | None = None
    fetched_at: str | None = None
    source_timestamp: str | None = None
    previous_close: int | None = None
    one_week_ago: int | None = None
    one_month_ago: int | None = None
    one_year_ago: int | None = None
    stale: bool | None = None
    confidence: int | None = None
    parser_version: str | None = None
    cache_status: str | None = None
    partial: bool | None = None
    coverage_percent: float | None = None
    coverage_components: int | None = None
    required_components: int | None = None
    overall_mode: str | None = None
    dependencies_requested: int | None = None
    dependencies_available: int | None = None
    dependencies_missing: List[str] | None = None
    degraded_reasons: List[str] | None = None


class ProbabilityItem(BaseModel):
    strategy: str
    probability: int
    confidence: int
    explanation: str


class ProbabilityResponse(BaseModel):
    items: List[ProbabilityItem]
    summary: str


class LeadershipStock(BaseModel):
    symbol: str
    score: int
    reason: str
    relative_strength: int
    category: str | None = None
    change_in_rs: float | None = None
    trend_status: str | None = None
    sector: str | None = None
    industry_group: str | None = None
    data_source: str | None = None
    overall_mode: str | None = None


class LeadershipCategory(BaseModel):
    category: str
    items: List[LeadershipStock]


class LeadershipResponse(BaseModel):
    categories: List[LeadershipCategory]
    summary: str
    overall_mode: str | None = None
    coverage_percent: float | None = None
    as_of: str | None = None


class DecisionConfidenceContributor(BaseModel):
    label: str
    score: int
    signal: str


class DecisionConfidenceResponse(BaseModel):
    score: int | None
    status: str
    contributors: List[DecisionConfidenceContributor]
    disagreements: List[str]
    summary: str
    reason: str | None = None
    calculated_at: str | None = None
    source_snapshot_id: str | None = None


class DashboardComparisonItem(BaseModel):
    metric: str
    today: float | int | str
    yesterday: float | int | str
    change: float | int | str


class DashboardComparisonResponse(BaseModel):
    items: List[DashboardComparisonItem]
    summary: str


class IndustryRotationSector(BaseModel):
    sector: str
    strongest_industry_groups: List[str]
    weakest_industry_groups: List[str]
    improving: List[str]
    deteriorating: List[str]


class IndustryRotationResponse(BaseModel):
    sectors: List[IndustryRotationSector]
    summary: str
    overall_mode: str | None = None
    coverage_percent: float | None = None
    as_of: str | None = None


class RiskDashboardContributor(BaseModel):
    label: str
    impact: str
    explanation: str


class RiskDashboardV2Response(BaseModel):
    score: int
    contributors: List[RiskDashboardContributor]
    warnings: List[str]
    upcoming_events: List[str]
    summary: str


class MarketSentimentSignal(BaseModel):
    key: str | None = None
    label: str
    score: int
    status: str
    value: float | None = None
    previous_value: float | None = None
    trend: str | None = None
    explanation: str
    metadata: Dict[str, Any] | None = None


class MarketSentimentResponse(BaseModel):
    score: int
    status: str
    confidence: float | None = None
    signals: List[MarketSentimentSignal]
    opportunities: List[str]
    risks: List[str]
    summary: str
    methodology: str | None = None
    official_index: bool | None = None
    metadata: Dict[str, Any] | None = None
    overall_mode: str | None = None
    limitations: List[str] | None = None


class MoneyFlowItem(BaseModel):
    area: str
    score: int
    status: str
    flow: str
    change_1d: float
    change_1w: float
    summary: str
    metadata: Dict[str, Any] | None = None


class MoneyFlowResponse(BaseModel):
    score: int
    status: str
    items: List[MoneyFlowItem]
    summary: str
    methodology: str | None = None
    inflow_leaders: List[str] | None = None
    outflow_leaders: List[str] | None = None
    metadata: Dict[str, Any] | None = None


class InstitutionalDashboardResponse(BaseModel):
    score: int
    status: str
    accumulation_distribution: str
    block_trade_bias: str
    dark_pool_bias: str
    program_trading: str
    signals: List[str]
    risks: List[str]
    summary: str
    block_trade_candidates: List[Dict[str, Any]] | None = None
    block_notional_by_symbol: Dict[str, float] | None = None
    block_notional_by_sector: Dict[str, float] | None = None
    repeated_large_print_symbols: List[str] | None = None
    confidence: float | None = None
    limitations: List[str] | None = None
    metadata: Dict[str, Any] | None = None


class OptionsIntelligenceResponse(BaseModel):
    score: int
    status: str
    put_call_ratio: float
    implied_volatility_rank: int
    skew: str
    options_flow_bias: str
    unusual_activity: List[str]
    summary: str
    market_summary: Dict[str, Any] | None = None
    items: List[Dict[str, Any]] | None = None
    expected_move: float | None = None
    estimated_gamma_regime: str | None = None
    call_wall: float | None = None
    put_wall: float | None = None
    confidence: float | None = None
    metadata: Dict[str, Any] | None = None


class SymbolOptionsIntelligence(BaseModel):
    symbol: str
    score: int
    status: str
    put_call_ratio: float | None = None
    implied_volatility_rank: int | None = None
    expected_move: float | None = None
    estimated_gamma_regime: str | None = None
    call_wall: float | None = None
    put_wall: float | None = None
    unusual_volume_candidates: List[str]
    summary: str
    metadata: Dict[str, Any] | None = None


class LiquidityDashboardResponse(BaseModel):
    score: int
    status: str
    spread_condition: str
    depth_condition: str
    funding_condition: str
    volume_condition: str
    warnings: List[str]
    summary: str
    items: List[Dict[str, Any]] | None = None
    metadata: Dict[str, Any] | None = None


class SymbolLiquidityResponse(BaseModel):
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
    metadata: Dict[str, Any] | None = None


class IntelligenceStatusResponse(BaseModel):
    sentiment: Dict[str, Any]
    options: Dict[str, Any]
    trade_flow: Dict[str, Any]
    liquidity: Dict[str, Any]
    overall_mode: str
    limitations: List[str]
    cache_status: Dict[str, Any]


class InstitutionalIntelligenceResponse(BaseModel):
    sentiment: MarketSentimentResponse
    money_flow: MoneyFlowResponse
    institutional: InstitutionalDashboardResponse
    options: OptionsIntelligenceResponse
    liquidity: LiquidityDashboardResponse
    summary: str


class SuggestedExposure(BaseModel):
    stocks: int
    cash: int
    margin: str
    options: str


class AggressivenessResponse(BaseModel):
    score: int
    status: str
    suggested_exposure: SuggestedExposure
    summary: str
    reasons: List[str]
    cautions: List[str]


class TradingStyleItem(BaseModel):
    style: str
    score: int
    rating: int
    status: str
    reason: str


class TradingStyleResponse(BaseModel):
    items: List[TradingStyleItem]
    preferred_style: str
    summary: str


class MarketChecklistItem(BaseModel):
    label: str
    passed: bool
    value: str


class MarketChecklistResponse(BaseModel):
    score: int
    max_score: int
    grade: str
    items: List[MarketChecklistItem]
    summary: str


class MarketPlaybookResponse(BaseModel):
    headline: str
    summary: str
    preferred_strategy: str
    suggested_aggressiveness: str
    top_sector: str
    top_industry_group: str
    top_industry_group_provenance: Dict[str, Any] = Field(default_factory=dict)
    cap_rotation_leader: str
    main_risk: str
    action_guidelines: List[str]
    avoid: List[str]
    disclaimer: str


class DecisionDashboardResponse(BaseModel):
    aggressiveness: AggressivenessResponse
    trading_styles: TradingStyleResponse
    checklist: MarketChecklistResponse
    playbook: MarketPlaybookResponse
    probabilities: ProbabilityResponse
    leadership: LeadershipResponse
    decision_confidence: DecisionConfidenceResponse
    comparison: DashboardComparisonResponse
    industry_rotation: IndustryRotationResponse
    risk_dashboard: RiskDashboardV2Response
    institutional_intelligence: InstitutionalIntelligenceResponse
    theme_intelligence: Dict[str, Any] = Field(default_factory=dict)


class DailyVolumeAnalysis(BaseModel):
    highest_relative_volume: str
    best_volume_setup: str
    distribution_volume_alerts: List[str]


class DailyRiskPlans(BaseModel):
    best_risk_reward_setup: str
    highest_risk_stock: str
    risk_summary: str


class DailyMultiTimeframe(BaseModel):
    strongest_alignment_stock: str
    weakest_alignment_stock: str
    summary: str


class DailyReportResponse(BaseModel):
    date: str
    title: str
    executive_summary: str
    market_regime: str
    key_drivers: List[str]
    main_risks: List[str]
    sector_leaders: List[str]
    tomorrow_watch: List[str]
    strategy_note: str
    institutional_activity: InstitutionalBias
    volume_analysis: DailyVolumeAnalysis
    risk_plans: DailyRiskPlans
    multi_timeframe: DailyMultiTimeframe
    market_health: MarketHealthResponse
    sector_etfs: SectorEtfResponse
    industry_groups: IndustryGroupResponse
    cap_rotation: MarketCapRotationResponse
    fear_greed: FearGreedResponse
    decision_dashboard: DecisionDashboardResponse
    probabilities: ProbabilityResponse
    leadership: LeadershipResponse
    decision_confidence: DecisionConfidenceResponse
    comparison: DashboardComparisonResponse
    industry_rotation: IndustryRotationResponse
    risk_dashboard: RiskDashboardV2Response
    institutional_intelligence: InstitutionalIntelligenceResponse
    ai_summary: Dict[str, Any] | None = None
    report_id: str | None = None
    market_date: str | None = None
    generated_time: str | None = None
    generated_at: str | None = None
    report_schema_version: str | None = None
    report_cache_key: str | None = None
    report_pdf_format_version: str | None = None
    report_snapshot: Dict[str, Any] = Field(default_factory=dict)
    report_narrative: Dict[str, Any] = Field(default_factory=dict)
    report_changes: Dict[str, Any] = Field(default_factory=dict)
    signal_convergence: Dict[str, Any] = Field(default_factory=dict)
    hidden_warnings: List[str] = Field(default_factory=list)
    hidden_confirmations: List[str] = Field(default_factory=list)
    market_conviction: Dict[str, Any] = Field(default_factory=dict)
    decision_checklist: Dict[str, Any] = Field(default_factory=dict)
    recommendation_confidence: Dict[str, Any] = Field(default_factory=dict)
    scenario_plan: List[Dict[str, Any]] = Field(default_factory=list)
    previous_playbook_review: Dict[str, Any] = Field(default_factory=dict)
    market_evolution: Dict[str, Any] = Field(default_factory=dict)
    signal_relationships: List[str] = Field(default_factory=list)
    trade_off_analysis: Dict[str, Any] = Field(default_factory=dict)
    report_commentary: Dict[str, Any] = Field(default_factory=dict)
    indexes: List[IndexSnapshot] = Field(default_factory=list)
    index_histories: Dict[str, List[float]] = Field(default_factory=dict)
    index_ohlcv: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    watchlist_summary: Dict[str, Any] | None = None
    sector_dashboard: Dict[str, Any] | None = None
    sector_snapshot_id: str | None = None
    theme_intelligence: Dict[str, Any] = Field(default_factory=dict)
    theme_report: Dict[str, Any] = Field(default_factory=dict)
    stock_charts: List[Dict[str, Any]] = Field(default_factory=list)
    economic_calendar: List[Dict[str, Any]] = Field(default_factory=list)
    macro: Dict[str, Any] = Field(default_factory=dict)
    semantic_context: Dict[str, Any] = Field(default_factory=dict)
    research_preferences: Dict[str, List[str]] = Field(default_factory=dict)
    security_taxonomy: List[Dict[str, Any]] = Field(default_factory=list)
    report_document: Dict[str, Any] | None = None


class MarketAnalysisResponse(BaseModel):
    type: str
    market_health: Dict[str, Any]
    sector_etfs: Dict[str, Any]
    industry_groups: Dict[str, Any]
    cap_rotation: Dict[str, Any]
    fear_greed: Dict[str, Any]
    decision_dashboard: Dict[str, Any]
    probabilities: Dict[str, Any]
    leadership: Dict[str, Any]
    decision_confidence: Dict[str, Any]
    comparison: Dict[str, Any]
    industry_rotation: Dict[str, Any]
    risk_dashboard: Dict[str, Any]
    institutional_intelligence: Dict[str, Any]
    regime: Dict[str, Any]
    breadth: Dict[str, Any]
    sectors: Dict[str, Any]
    institutional_activity: Dict[str, Any]
    volume: Dict[str, Any]
    risk: Dict[str, Any]
    summary_points: List[str]
    key_opportunities: List[str]
    key_risks: List[str]
    ai_prompt_context: Dict[str, Any]


class StockAnalysisResponse(BaseModel):
    type: str
    symbol: str
    stock_rating: Dict[str, Any]
    relative_strength: Dict[str, Any]
    patterns: Dict[str, Any]
    support_resistance: Dict[str, Any]
    trendline: Dict[str, Any]
    volume: Dict[str, Any]
    risk_plan: Dict[str, Any]
    multi_timeframe: Dict[str, Any]
    summary_points: List[str]
    strengths: List[str]
    warnings: List[str]
    ai_prompt_context: Dict[str, Any]


class AllStockAnalysisResponse(BaseModel):
    type: str
    items: List[StockAnalysisResponse]
    summary_points: List[str]


class MarketAISummaryResponse(BaseModel):
    type: str
    headline: str
    summary: str
    confidence: int
    generated_by: str
    next_update: str
    key_points: List[str]
    opportunities: List[str]
    risks: List[str]
    what_to_watch: List[str]
    disclaimer: str
    cached: bool | None = None


class StockAISummaryResponse(BaseModel):
    type: str
    symbol: str
    headline: str
    summary: str
    confidence: int
    generated_by: str
    next_update: str
    why_it_matters: List[str]
    strengths: List[str]
    risks: List[str]
    what_to_watch: List[str]
    disclaimer: str
    cached: bool | None = None


class AllStockAISummaryResponse(BaseModel):
    type: str
    items: List[StockAISummaryResponse]
    summary_points: List[str]
    confidence: int
    generated_by: str
    next_update: str
    disclaimer: str
    cached: bool | None = None


class AIChatRequest(BaseModel):
    message: str
    symbol: str | None = None


class AIChatResponse(BaseModel):
    type: str
    answer: str
    key_points: List[str]
    risks: List[str]
    what_to_watch: List[str]
    related_symbols: List[str]
    confidence: int
    generated_by: str
    disclaimer: str
