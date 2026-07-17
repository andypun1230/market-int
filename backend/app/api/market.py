from typing import Any, Dict

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.models.market import (
    BriefResponse,
    DashboardComparisonResponse,
    DecisionDashboardResponse,
    IndexHistoryResponse,
    IndexesResponse,
    InstitutionalActivityResponse,
    IndustryGroupResponse,
    InstitutionalDashboardResponse,
    FearGreedResponse,
    IndustryRotationResponse,
    LeadershipResponse,
    LiquidityDashboardResponse,
    MultiTimeframeItem,
    MultiTimeframeResponse,
    MarketHealthResponse,
    MarketCapRotationResponse,
    MarketSentimentResponse,
    MoneyFlowResponse,
    OptionsIntelligenceResponse,
    PatternResponse,
    ProbabilityResponse,
    RegimeResponse,
    RiskPlan,
    RiskPlanResponse,
    RelativeStrengthResponse,
    RiskResponse,
    SectorBreadthResponse,
    SectorEtfResponse,
    SymbolLiquidityResponse,
    SymbolOptionsIntelligence,
    SectorsResponse,
    StockRatingResponse,
    SupportResistanceResponse,
    TrendlineResponse,
    VolumeAnalysis,
    VolumeAnalysisResponse,
    WatchlistResponse,
)
from app.providers.models import HistoryData, QuoteData
from app.providers.selector import get_market_data_provider
from app.services.breadth import calculate_market_breadth, calculate_sector_breadth
from app.services.client_activity import record_client_activity
from app.services.dashboard_comparison import build_dashboard_comparison
from app.services.decision_intelligence import build_decision_dashboard
from app.services.fear_greed import build_fear_greed_index
from app.services.industry_rotation import build_industry_rotation_dashboard
from app.services.institutional_activity import build_institutional_activity
from app.services.industry_groups import build_industry_groups
from app.services.institutional_dashboard import build_institutional_dashboard, build_symbol_institutional_dashboard
from app.services.leadership import build_leadership_dashboard
from app.services.liquidity_dashboard import analyze_symbol_liquidity, build_liquidity_dashboard
from app.services.market_cap_rotation import build_market_cap_rotation
from app.services.market_core_snapshot import build_market_core_snapshot
from app.services.market_data import get_index_history, get_index_snapshots
from app.services.market_detail_aggregates import (
    build_market_decision_details,
    build_market_institutional_details,
    build_market_structure_details,
)
from app.services.market_health import calculate_market_health
from app.services.market_sentiment import build_market_sentiment_dashboard
from app.services.money_flow import build_money_flow_dashboard
from app.services.multi_timeframe import (
    analyze_multi_timeframe,
    build_multi_timeframe_response,
)
from app.services.pattern_detection import detect_all_patterns, detect_patterns
from app.services.options_intelligence import analyze_symbol_options, build_options_intelligence
from app.services.probability_engine import build_probability_engine
from app.services.regime import build_market_brief, build_market_regime, build_market_risk
from app.services.relative_strength import build_relative_strength
from app.services.risk import build_risk_plans, calculate_risk_plan
from app.services.sector_etfs import build_sector_etf_dashboard
from app.services.sector_dashboard import build_sector_dashboard
from app.services.sectors import build_market_sectors
from app.services.sectors_summary import build_sectors_summary
from app.services.stock_rating import build_stock_ratings
from app.services.stock_analysis_aggregate import build_stock_analysis
from app.services.support_resistance import calculate_support_resistance
from app.services.trendline import analyze_trendline, analyze_watchlist_trendlines
from app.services.volume_analysis import analyze_volume, build_volume_analysis
from app.services.watchlist import build_market_watchlist, build_user_watchlist_item
from app.services.watchlist_summary import build_watchlist_summary

router = APIRouter()


class LiveQuotesRequest(BaseModel):
    symbols: list[str] = Field(default_factory=list)


@router.get("/market/brief", response_model=BriefResponse)
async def get_market_brief() -> BriefResponse:
    """Return a stubbed daily market brief."""
    return build_market_brief()


@router.get("/market/regime", response_model=RegimeResponse)
async def get_market_regime() -> RegimeResponse:
    """Return stubbed regime metrics."""
    return build_market_regime()


@router.get("/market/sectors", response_model=SectorsResponse)
async def get_market_sectors() -> SectorsResponse:
    """Return stubbed sector rotation leaders."""
    return build_market_sectors()


@router.get("/market/sectors/summary")
async def get_market_sectors_summary() -> dict[str, object]:
    """Return compact cached sector data for first Sectors tab render."""
    record_client_activity("sectors")
    return await run_in_threadpool(build_sectors_summary)


@router.get("/market/sector-dashboard")
async def get_market_sector_dashboard() -> dict[str, object]:
    """Return normalized sector and theme heatmap/rotation data."""
    record_client_activity("sectors")
    return await run_in_threadpool(build_sector_dashboard)


@router.get("/market/watchlist", response_model=WatchlistResponse)
async def get_market_watchlist() -> WatchlistResponse:
    """Return stubbed watchlist intelligence."""
    record_client_activity("watchlist")
    return build_market_watchlist()


@router.get("/market/risk", response_model=RiskResponse)
async def get_market_risk() -> RiskResponse:
    """Return stubbed market risk dashboard data."""
    return build_market_risk()


@router.get("/market/health", response_model=MarketHealthResponse)
async def get_market_health() -> MarketHealthResponse:
    """Return a composite market health score from existing mock engines."""
    return calculate_market_health()


@router.get("/market/core-snapshot")
async def get_market_core_snapshot() -> dict[str, object]:
    """Return critical market data for fast initial dashboard rendering."""
    record_client_activity("market")
    return build_market_core_snapshot()


@router.get("/market/decision-dashboard", response_model=DecisionDashboardResponse)
async def get_market_decision_dashboard() -> DecisionDashboardResponse:
    """Return practical daily decision guidance from existing mock engines."""
    return build_decision_dashboard()


@router.get("/market/probabilities", response_model=ProbabilityResponse)
async def get_market_probabilities() -> ProbabilityResponse:
    """Return deterministic strategy probability scores."""
    return build_probability_engine()


@router.get("/market/leadership", response_model=LeadershipResponse)
async def get_market_leadership() -> LeadershipResponse:
    """Return deterministic leadership buckets for watchlist stocks."""
    return build_leadership_dashboard()


@router.get("/market/comparison", response_model=DashboardComparisonResponse)
async def get_market_comparison() -> DashboardComparisonResponse:
    """Return deterministic today/yesterday dashboard comparison."""
    return build_dashboard_comparison()


@router.get("/market/industry-rotation", response_model=IndustryRotationResponse)
async def get_market_industry_rotation() -> IndustryRotationResponse:
    """Return deterministic industry rotation within broad sectors."""
    return build_industry_rotation_dashboard()


@router.get("/market/sector-etfs", response_model=SectorEtfResponse)
async def get_market_sector_etfs() -> SectorEtfResponse:
    """Return deterministic sector ETF rotation data."""
    return build_sector_etf_dashboard()


@router.get("/market/industry-groups", response_model=IndustryGroupResponse)
async def get_market_industry_groups() -> IndustryGroupResponse:
    """Return deterministic industry group rotation data."""
    return build_industry_groups()


@router.get("/market/cap-rotation", response_model=MarketCapRotationResponse)
async def get_market_cap_rotation() -> MarketCapRotationResponse:
    """Return deterministic market cap rotation data."""
    return build_market_cap_rotation()


@router.get("/market/fear-greed", response_model=FearGreedResponse)
async def get_market_fear_greed() -> FearGreedResponse:
    """Return a deterministic Fear & Greed component model."""
    return build_fear_greed_index()


@router.get("/market/sentiment", response_model=MarketSentimentResponse)
async def get_market_sentiment() -> MarketSentimentResponse:
    """Return deterministic market sentiment intelligence."""
    return build_market_sentiment_dashboard()


@router.get("/market/money-flow", response_model=MoneyFlowResponse)
async def get_market_money_flow() -> MoneyFlowResponse:
    """Return deterministic money-flow intelligence."""
    return build_money_flow_dashboard()


@router.get("/market/institutional", response_model=InstitutionalDashboardResponse)
async def get_market_institutional() -> InstitutionalDashboardResponse:
    """Return deterministic institutional intelligence."""
    record_client_activity("institutional")
    return build_institutional_dashboard()


@router.get("/market/institutional/{symbol}", response_model=dict)
async def get_market_institutional_by_symbol(symbol: str) -> dict:
    """Return cautious large-print candidate analysis for one symbol."""
    return build_symbol_institutional_dashboard(symbol)


@router.get("/market/options", response_model=OptionsIntelligenceResponse)
async def get_market_options() -> OptionsIntelligenceResponse:
    """Return deterministic options sentiment intelligence."""
    return build_options_intelligence()


@router.get("/market/options/{symbol}", response_model=SymbolOptionsIntelligence)
async def get_market_options_by_symbol(symbol: str) -> SymbolOptionsIntelligence:
    """Return options intelligence for one symbol."""
    return analyze_symbol_options(symbol)


@router.get("/market/liquidity", response_model=LiquidityDashboardResponse)
async def get_market_liquidity() -> LiquidityDashboardResponse:
    """Return deterministic liquidity intelligence."""
    return build_liquidity_dashboard()


@router.get("/market/liquidity/{symbol}", response_model=SymbolLiquidityResponse)
async def get_market_liquidity_by_symbol(symbol: str) -> SymbolLiquidityResponse:
    """Return liquidity proxy analysis for one symbol."""
    return analyze_symbol_liquidity(symbol)


@router.get("/market/breadth", response_model=SectorBreadthResponse)
async def get_market_breadth() -> SectorBreadthResponse:
    """Return mock market and sector breadth metrics."""
    record_client_activity("market")
    return SectorBreadthResponse(
        market=calculate_market_breadth(),
        sectors=calculate_sector_breadth(),
    )


@router.get("/market/institutional-activity", response_model=InstitutionalActivityResponse)
async def get_market_institutional_activity() -> InstitutionalActivityResponse:
    """Return mock institutional buying and selling signals for major indexes."""
    return build_institutional_activity()


@router.get("/market/indexes", response_model=IndexesResponse)
async def get_market_indexes() -> IndexesResponse:
    """Return mock index snapshots for the market data engine foundation."""
    return IndexesResponse(indexes=get_index_snapshots())


@router.get("/market/indexes/{symbol}/history", response_model=IndexHistoryResponse)
async def get_market_index_history(symbol: str) -> IndexHistoryResponse:
    """Return deterministic mock historical closes for an index symbol."""
    return get_index_history(symbol)


@router.get("/market/live/quote/{symbol}", response_model=QuoteData)
async def get_market_live_quote(symbol: str) -> QuoteData:
    """Return normalized quote data from the selected provider."""
    return get_market_data_provider().get_quote(symbol)


@router.get("/market/live/history/{symbol}", response_model=HistoryData)
async def get_market_live_history(
    symbol: str,
    resolution: str = Query(default="D"),
    days: int = Query(default=240, ge=1, le=1500),
) -> HistoryData:
    """Return normalized daily OHLCV history from the selected provider."""
    return get_market_data_provider().get_history(symbol, resolution=resolution, days=days)


@router.get("/market/live/quotes", response_model=dict)
async def get_market_live_quotes(symbols: str = Query(...)) -> dict[str, object]:
    """Return normalized quotes for a comma-separated symbol list."""
    symbol_list = [
        symbol.strip().upper()
        for symbol in symbols.split(",")
        if symbol.strip()
    ]
    return build_live_quotes_response(symbol_list)


@router.post("/market/live/quotes", response_model=dict)
async def post_market_live_quotes(payload: LiveQuotesRequest) -> dict[str, object]:
    """Return normalized quotes for a symbol list payload."""
    return build_live_quotes_response(payload.symbols)


def build_live_quotes_response(symbol_list: list[str]) -> dict[str, object]:
    provider = get_market_data_provider()
    if hasattr(provider, "get_batch_quotes"):
        result = provider.get_batch_quotes(symbol_list)
        return {
            "items": result.quotes,
            "unavailable_symbols": result.unavailable_symbols,
            "provider": result.provider,
            "source_state": result.source_state,
            "fetched_at": result.fetched_at.isoformat(),
        }
    return {"items": provider.get_quotes(symbol_list)}


@router.get("/market/patterns", response_model=PatternResponse)
async def get_market_patterns() -> PatternResponse:
    """Return detected mock patterns for the watchlist universe."""
    return detect_all_patterns()


@router.get("/market/patterns/{symbol}", response_model=PatternResponse)
async def get_market_patterns_by_symbol(symbol: str) -> PatternResponse:
    """Return detected mock patterns for one ticker."""
    return detect_patterns(symbol)


@router.get("/market/support-resistance/{symbol}", response_model=SupportResistanceResponse)
async def get_market_support_resistance(symbol: str) -> SupportResistanceResponse:
    """Return calculated support, resistance, breakout, and moving-average levels."""
    return calculate_support_resistance(symbol)


@router.get("/market/trendline/{symbol}", response_model=TrendlineResponse)
async def get_market_trendline(symbol: str) -> TrendlineResponse:
    """Return basic rising support and falling resistance trendline analysis."""
    return analyze_trendline(symbol)


@router.get("/market/trendlines", response_model=list[TrendlineResponse])
async def get_market_trendlines() -> list[TrendlineResponse]:
    """Return trendline analysis for the watchlist universe."""
    return analyze_watchlist_trendlines()


@router.get("/market/volume", response_model=VolumeAnalysisResponse)
async def get_market_volume() -> VolumeAnalysisResponse:
    """Return ranked watchlist price-volume analysis."""
    return build_volume_analysis()


@router.get("/market/volume/{symbol}", response_model=VolumeAnalysis)
async def get_market_volume_by_symbol(symbol: str) -> VolumeAnalysis:
    """Return price-volume analysis for one watchlist ticker."""
    return analyze_volume(symbol)


@router.get("/market/risk-plans", response_model=RiskPlanResponse)
async def get_market_risk_plans() -> RiskPlanResponse:
    """Return practical risk/reward plans for the watchlist universe."""
    return build_risk_plans()


@router.get("/market/risk-plans/{symbol}", response_model=RiskPlan)
async def get_market_risk_plan_by_symbol(symbol: str) -> RiskPlan:
    """Return a practical risk/reward plan for one watchlist ticker."""
    return calculate_risk_plan(symbol)


@router.get("/market/multi-timeframe", response_model=MultiTimeframeResponse)
async def get_market_multi_timeframe() -> MultiTimeframeResponse:
    """Return multi-timeframe alignment analysis for the watchlist universe."""
    return build_multi_timeframe_response()


@router.get("/market/multi-timeframe/{symbol}", response_model=MultiTimeframeItem)
async def get_market_multi_timeframe_by_symbol(symbol: str) -> MultiTimeframeItem:
    """Return multi-timeframe alignment analysis for one watchlist ticker."""
    return analyze_multi_timeframe(symbol)


@router.get("/market/relative-strength", response_model=RelativeStrengthResponse)
async def get_market_relative_strength() -> RelativeStrengthResponse:
    """Return ranked watchlist relative strength versus market and sector benchmarks."""
    return build_relative_strength()


@router.get("/market/stock-ratings", response_model=StockRatingResponse)
async def get_market_stock_ratings() -> StockRatingResponse:
    """Return transparent stock intelligence ratings for the watchlist."""
    return build_stock_ratings()


@router.get("/watchlist/summary")
async def get_watchlist_summary() -> dict[str, object]:
    """Return compact watchlist data for first render without full detail fan-out."""
    record_client_activity("watchlist")
    return await run_in_threadpool(build_watchlist_summary)


@router.get("/market/stock-analysis/{symbol}")
async def get_market_stock_analysis(symbol: str) -> dict[str, object]:
    """Return aggregated detail analysis for one symbol with partial-failure tolerance."""
    record_client_activity("watchlist")
    return await run_in_threadpool(build_stock_analysis, symbol)


@router.get("/market/details/decision")
async def get_market_decision_details() -> dict[str, object]:
    """Return grouped decision details for the Market detail modal."""
    record_client_activity("market")
    return await run_in_threadpool(build_market_decision_details)


@router.get("/market/details/institutional")
async def get_market_institutional_details() -> dict[str, object]:
    """Return grouped institutional details on demand."""
    record_client_activity("institutional")
    return await run_in_threadpool(build_market_institutional_details)


@router.get("/market/details/structure")
async def get_market_structure_details() -> dict[str, object]:
    """Return grouped market-structure details on demand."""
    record_client_activity("market")
    record_client_activity("sectors")
    return await run_in_threadpool(build_market_structure_details)


@router.get("/user/watchlist/{ticker}")
async def get_watchlist_item(ticker: str) -> Dict[str, Any]:
    """Return stub data for a given watchlist ticker."""
    return build_user_watchlist_item(ticker)
