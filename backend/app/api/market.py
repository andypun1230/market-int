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
from app.securities.registry import canonical_sector_id
from app.services.sector_dashboard import build_sector_rotation_trails
from app.providers.selector import get_market_data_provider
from app.services.breadth import calculate_market_breadth, calculate_sector_breadth, unavailable_market_breadth
from app.breadth.service import get_breadth_snapshot_service
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
from app.services.macro_state import build_macro_state
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
from app.sector_snapshots.service import get_sector_snapshot_service
from app.theme_snapshots.readers import rotation_payload as theme_rotation_payload, snapshot_payload as theme_snapshot_payload
from app.theme_snapshots.service import get_theme_snapshot_service
from app.themes.intelligence import get_theme_intelligence_service
from app.services.stock_rating import build_stock_ratings
from app.services.support_resistance import calculate_support_resistance
from app.services.trendline import analyze_trendline, analyze_watchlist_trendlines
from app.services.volume_analysis import analyze_volume, build_volume_analysis
from app.services.watchlist import build_market_watchlist, build_user_watchlist_item
from app.services.watchlist_summary import build_watchlist_summary
from app.snapshots.readers import (
    get_core_snapshot_from_snapshot,
    get_decision_dashboard_from_snapshot,
    get_fear_greed_from_snapshot,
    get_health_from_snapshot,
    get_regime_from_snapshot,
    get_risk_from_snapshot,
    get_section_payload,
    latest_snapshot_response,
    snapshot_details_payload,
)
from app.snapshots.service import get_market_snapshot_service
from app.stock_snapshots.readers import snapshot_response
from app.stock_snapshots.service import get_stock_snapshot_service

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
    return get_regime_from_snapshot()


@router.get("/market/sectors", response_model=SectorsResponse)
async def get_market_sectors() -> SectorsResponse:
    """Return stubbed sector rotation leaders."""
    return build_market_sectors()


@router.get("/market/sectors/snapshot/latest")
async def get_latest_sector_snapshot() -> dict:
    snapshot = get_sector_snapshot_service().latest()
    return snapshot.model_dump() if snapshot else {"status": "unavailable", "source_state": "unavailable", "warnings": ["No sector snapshot has been published."]}


@router.get("/market/sectors/history")
async def get_sector_snapshot_history(days: int = Query(default=90, ge=1, le=260)) -> dict:
    service = get_sector_snapshot_service()
    history = service.history(days)
    latest = service.latest()
    return {"snapshot_id": latest.snapshot_id if latest else None, "universe_version": latest.universe_version if latest else None, "market_date": latest.market_date if latest else None, "items": history, "limitation": "History contains only snapshots actually built; no historical values are fabricated."}


@router.get("/market/sectors/rotation")
async def get_sector_rotation(
    profile: str | None = Query(default=None, description="Canonical short, medium, or long model profile."),
    timeframe: str | None = Query(default=None, description="Compatibility alias: 1W, 1M, or 3M."),
    interval: str | None = Query(default=None, description="Deprecated alias for timeframe."),
) -> dict:
    service = get_sector_snapshot_service()
    snapshot = service.latest()
    selected = profile or interval or timeframe or "medium"
    try:
        rotation = build_sector_rotation_trails(snapshot, service.history(), profile=selected) if snapshot else {"entity_type": "sector", "source_state": "unavailable", "data_mode": "unavailable", "formula_version": "sector-relative-trend-momentum-v1", "rotation_model_id": "sector-relative-trend-momentum", "rotation_model_version": "sector-relative-trend-momentum-v1", "normalization_version": "zero-centered-rolling-robust-scale-v1", "benchmark": "SPY", "profile": "medium", "timeframe": "1M", "interval": "1M", "points": [], "tails": [], "published_snapshot_trails": {}, "market_trails": {}, "current_points": {}, "series": [], "current_positions_available": False, "etf_trails_available": False, "snapshot_transition_history_available": False, "current_point_count": 0, "trail_point_count": 0, "transition_snapshot_count": 0, "limited_history_reason": "No sector snapshot is available.", "movements": {}, "flow_groups": {"gaining": [], "losing": [], "stable": []}, "history_point_count": 0, "movement_available": False, "trail_limit": 10, "trail_source": "published_sector_snapshots", "market_trail_source": "durable_polygon_adjusted_daily_history", "warnings": ["No sector snapshot is available."]}
    except ValueError:
        rotation = build_sector_rotation_trails(snapshot, service.history(), profile="medium") if snapshot else {}
        rotation = {**rotation, "status": "unavailable", "warnings": ["Unsupported Sector Rotation profile."]}
    return {"snapshot_id": snapshot.snapshot_id if snapshot else None, "universe_version": snapshot.universe_version if snapshot else None, "market_date": snapshot.market_date if snapshot else None, "rankings": list(snapshot.rankings) if snapshot else [], "summary": snapshot.rotation_summary if snapshot else "Sector snapshot is unavailable.", "source_state": snapshot.source_state if snapshot else "unavailable", **rotation}


@router.get("/market/sectors/alerts")
async def get_sector_alerts() -> dict:
    snapshot = get_sector_snapshot_service().latest()
    return {"snapshot_id": snapshot.snapshot_id if snapshot else None, "universe_version": snapshot.universe_version if snapshot else None, "market_date": snapshot.market_date if snapshot else None, "items": list(snapshot.alerts) if snapshot else [], "source_state": snapshot.source_state if snapshot else "unavailable"}


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


@router.get("/market/themes/snapshot/latest")
async def get_latest_theme_snapshot() -> dict:
    return theme_snapshot_payload(get_theme_snapshot_service().latest())


@router.get("/market/themes/history")
async def get_theme_snapshot_history(days: int = Query(default=90, ge=1, le=260)) -> dict:
    service = get_theme_snapshot_service(); latest = service.latest()
    return {"snapshot_id": latest.snapshot_id if latest else None, "market_date": latest.market_date if latest else None, "items": service.history(days), "limitation": "History contains only immutable ThemeSnapshots actually published; no historical values are fabricated."}


@router.get("/market/themes/rotation")
async def get_theme_rotation(
    profile: str | None = Query(default=None, description="Canonical short, medium, or long model profile."),
    timeframe: str | None = Query(default=None, description="Compatibility alias: 1W, 1M, or 3M."),
    interval: str | None = Query(default=None, description="Deprecated alias for timeframe."),
) -> dict:
    selected = profile or interval or timeframe or "medium"
    try:
        return theme_rotation_payload(get_theme_snapshot_service().latest(), selected)
    except ValueError:
        return {
            **theme_rotation_payload(None, "medium"),
            "timeframe": selected.upper(),
            "interval": selected.upper(),
            "profile": selected.lower(),
            "warnings": ["Unsupported Theme Rotation profile."],
        }


@router.get("/market/themes/alerts")
async def get_theme_alerts() -> dict:
    snapshot = get_theme_snapshot_service().latest()
    return {"snapshot_id": snapshot.snapshot_id if snapshot else None, "market_date": snapshot.market_date if snapshot else None, "source_state": snapshot.source_state if snapshot else "unavailable", "items": list(snapshot.alerts) if snapshot else []}


@router.get("/market/themes/overlap")
async def get_theme_overlap() -> dict:
    snapshot = get_theme_snapshot_service().latest()
    return {"snapshot_id": snapshot.snapshot_id if snapshot else None, "market_date": snapshot.market_date if snapshot else None, "source_state": snapshot.source_state if snapshot else "unavailable", "items": list(snapshot.overlap_matrix) if snapshot else [], "warning": "Overlap is disclosed and is not independent confirmation."}


@router.get("/market/themes/status")
async def get_theme_status() -> dict:
    return get_theme_snapshot_service().status()


@router.post("/market/themes/snapshot/refresh")
async def refresh_theme_snapshot() -> dict:
    snapshot = await run_in_threadpool(get_theme_snapshot_service().build_now)
    return theme_snapshot_payload(snapshot)


@router.get("/market/themes")
async def get_market_themes(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
) -> dict[str, Any]:
    return get_theme_intelligence_service().list_themes(offset=offset, limit=limit)


@router.get("/market/themes/ranking")
async def get_theme_ranking(
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=100),
) -> dict[str, Any]:
    return get_theme_intelligence_service().ranked_themes(status=status, limit=limit)


@router.get("/market/themes/taxonomy")
async def get_theme_taxonomy(include_retired: bool = Query(default=True)) -> dict[str, Any]:
    return get_theme_intelligence_service().taxonomy(include_retired=include_retired)


@router.get("/market/themes/mappings/{symbol}")
async def get_symbol_theme_mappings(symbol: str) -> dict[str, Any]:
    return get_theme_intelligence_service().mappings_for_symbol(symbol)


@router.get("/market/themes/search/results")
async def search_canonical_themes(
    q: str = Query(min_length=1),
    limit: int = Query(default=20, ge=1, le=50),
) -> dict[str, Any]:
    return get_theme_intelligence_service().search(q, limit=limit)


@router.get("/market/themes/{theme_id}")
async def get_theme_detail(theme_id: str) -> dict[str, Any]:
    return get_theme_intelligence_service().current(theme_id)


@router.get("/market/themes/{theme_id}/constituents")
async def get_theme_constituents(
    theme_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
) -> dict[str, Any]:
    return get_theme_intelligence_service().constituents(theme_id, offset=offset, limit=limit)


@router.get("/market/themes/{theme_id}/history")
async def get_canonical_theme_history(
    theme_id: str,
    days: int = Query(default=90, ge=1, le=260),
) -> dict[str, Any]:
    return get_theme_intelligence_service().history(theme_id, days=days)


@router.get("/market/themes/{theme_id}/changes")
async def get_canonical_theme_changes(theme_id: str) -> dict[str, Any]:
    return get_theme_intelligence_service().changes(theme_id)


@router.get("/market/themes/{theme_id}/evidence")
async def get_canonical_theme_evidence(theme_id: str) -> dict[str, Any]:
    return get_theme_intelligence_service().evidence(theme_id)


@router.get("/market/sectors/{sector_id}")
async def get_sector_detail(sector_id: str) -> dict:
    snapshot = get_sector_snapshot_service().latest()
    canonical_id = canonical_sector_id(sector_id)
    row = next((row for row in snapshot.sectors if row["sector_id"] == canonical_id), None) if snapshot and canonical_id else None
    constituents: list[dict[str, object]] = []
    if snapshot and row:
        service = get_sector_snapshot_service()
        for member in service.builder.security_master.storage.members(snapshot.universe_id):
            if member.sector_id != canonical_id:
                continue
            security = service.builder.security_master.storage.security(member.ticker)
            closes = [bar.close for bar in service.builder.bars.history(member.ticker, end_date=snapshot.market_date)]
            def change(days: int) -> float | None:
                return round((closes[-1] / closes[-days - 1] - 1) * 100, 3) if len(closes) > days and closes[-days - 1] else None
            ema50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else None
            relevance = "Above EMA50" if ema50 is not None and closes[-1] >= ema50 else "Below EMA50" if ema50 is not None else None
            constituents.append({"ticker": member.ticker, "company_name": security.company_name if security else member.ticker, "sector_id": canonical_id, "eligible": len(closes) >= 200, "returns": {"1d": change(1), "1w": change(5), "1m": change(21), "3m": change(63), "6m": change(126), "1y": change(252)}, "relevance": relevance})
    rotation = build_sector_rotation_trails(snapshot, get_sector_snapshot_service().history()) if snapshot and row else {"trails": {}, "movements": {}, "series": []}
    sector_series = list((row.get("rotation_series") or {}).values()) if row else []
    return {"snapshot_id": snapshot.snapshot_id if snapshot else None, "universe_id": snapshot.universe_id if snapshot else None, "universe_version": snapshot.universe_version if snapshot else None, "market_date": snapshot.market_date if snapshot else None, "source_state": snapshot.source_state if snapshot else "unavailable", "status": snapshot.status if snapshot else "unavailable", "coverage": snapshot.coverage if snapshot else {}, "benchmark": snapshot.benchmark if snapshot else "SPY", "provider_provenance": snapshot.provider_provenance if snapshot else {}, "alerts": list(snapshot.alerts) if snapshot else [], "warnings": list(snapshot.warnings) if snapshot else [], "sector": row, "constituents": constituents, "rotation_history": rotation.get("published_snapshot_trails", {}).get(canonical_id, []), "rotation_series": sector_series, "rotation_movement": rotation.get("movements", {}).get(canonical_id)}


@router.get("/market/watchlist", response_model=WatchlistResponse)
async def get_market_watchlist() -> WatchlistResponse:
    """Return stubbed watchlist intelligence."""
    record_client_activity("watchlist")
    return build_market_watchlist()


@router.get("/market/risk", response_model=RiskResponse)
async def get_market_risk() -> RiskResponse:
    """Return stubbed market risk dashboard data."""
    return get_risk_from_snapshot()


@router.get("/market/health", response_model=MarketHealthResponse)
async def get_market_health() -> MarketHealthResponse:
    """Return a composite market health score from existing mock engines."""
    return get_health_from_snapshot()


@router.get("/market/macro")
async def get_market_macro(days: int = Query(default=110, ge=45, le=370)) -> dict[str, Any]:
    """Return the canonical cache-backed cross-asset macro interpretation."""
    record_client_activity("market")
    return await run_in_threadpool(build_macro_state, days)


@router.get("/market/core-snapshot")
async def get_market_core_snapshot() -> dict[str, object]:
    """Return critical market data for fast initial dashboard rendering."""
    record_client_activity("market")
    return get_core_snapshot_from_snapshot()


@router.get("/market/decision-dashboard", response_model=DecisionDashboardResponse)
async def get_market_decision_dashboard() -> DecisionDashboardResponse:
    """Return practical daily decision guidance from existing mock engines."""
    return get_decision_dashboard_from_snapshot()


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
    return get_fear_greed_from_snapshot()


@router.get("/market/snapshot/latest")
async def get_latest_market_snapshot() -> dict[str, object]:
    """Return the latest prepared market snapshot without provider calls."""
    record_client_activity("market")
    return latest_snapshot_response()


@router.get("/market/snapshot/status")
async def get_market_snapshot_status() -> dict[str, object]:
    """Return safe diagnostics for market snapshot freshness and refresh state."""
    return get_market_snapshot_service().get_status()


@router.get("/market/snapshot/{snapshot_id}")
async def get_market_snapshot_by_id(snapshot_id: str) -> dict[str, object]:
    """Return an immutable market snapshot by ID."""
    snapshot = get_market_snapshot_service().get_snapshot(snapshot_id)
    if snapshot is None:
        return {"status": "unavailable", "snapshot_id": snapshot_id}
    return snapshot.model_dump()


@router.post("/market/snapshot/refresh")
async def refresh_market_snapshot() -> dict[str, object]:
    """Queue a market snapshot refresh for development/internal use."""
    queued = get_market_snapshot_service().trigger_background_refresh()
    return {"queued": queued, "status": get_market_snapshot_service().get_status()}


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
    """Fast read of the latest immutable breadth snapshot; never fetches constituents."""
    record_client_activity("market")
    snapshot = get_breadth_snapshot_service().latest()
    if snapshot is None:
        return SectorBreadthResponse(market=unavailable_market_breadth(), sectors=[])
    return SectorBreadthResponse(market=calculate_market_breadth(), sectors=calculate_sector_breadth())


@router.get("/market/breadth/snapshot/latest")
async def get_latest_breadth_snapshot() -> dict:
    snapshot = get_breadth_snapshot_service().latest()
    return snapshot.model_dump() if snapshot else {"status": "unavailable", "source_state": "unavailable", "warnings": ["No breadth snapshot has been published."], "refresh_state": get_breadth_snapshot_service().status()}


@router.get("/market/breadth/snapshot/status")
async def get_breadth_snapshot_status() -> dict:
    return get_breadth_snapshot_service().status()


@router.get("/market/breadth/snapshot/{snapshot_id}")
async def get_breadth_snapshot(snapshot_id: str) -> dict:
    snapshot = get_breadth_snapshot_service().get(snapshot_id)
    if snapshot is None:
        return {"status": "unavailable", "source_state": "unavailable", "snapshot_id": snapshot_id}
    return snapshot.model_dump()


@router.get("/market/breadth/status")
async def get_breadth_status() -> dict:
    return get_breadth_snapshot_service().status()


@router.post("/market/breadth/snapshot/refresh")
async def refresh_breadth_snapshot() -> dict:
    return {"accepted": get_breadth_snapshot_service().trigger_refresh(), "status": get_breadth_snapshot_service().status()}


@router.get("/market/breadth/history")
async def get_breadth_history(metric: str = "breadth_score", days: int = 90, start: str | None = None, end: str | None = None) -> dict:
    service = get_breadth_snapshot_service()
    universe = service.builder.security_master.storage.get_active_universe(service.universe_name())
    return {"universe": universe.universe_id if universe else None, "metric": metric, "items": service.storage.history(universe.universe_id, metric, days, start=start, end=end) if universe else []}


@router.get("/market/institutional-activity", response_model=InstitutionalActivityResponse)
async def get_market_institutional_activity() -> InstitutionalActivityResponse:
    """Return mock institutional buying and selling signals for major indexes."""
    return build_institutional_activity()


@router.get("/market/indexes", response_model=IndexesResponse)
async def get_market_indexes() -> IndexesResponse:
    """Return canonical index snapshots from the shared market snapshot when available."""
    payload = get_section_payload("indexes")
    if isinstance(payload, list) and payload:
        return IndexesResponse(indexes=payload)
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
async def get_watchlist_summary(symbols: str | None = Query(default=None)) -> dict[str, object]:
    """Return compact watchlist data for first render without full detail fan-out."""
    record_client_activity("watchlist")
    requested_symbols = [symbol for symbol in (symbols or "").split(",") if symbol.strip()]
    return await run_in_threadpool(build_watchlist_summary, requested_symbols)


@router.get("/market/stock-analysis/{symbol}")
async def get_market_stock_analysis(symbol: str) -> dict[str, object]:
    """Return fast-read stock detail analysis from a per-symbol snapshot."""
    record_client_activity("watchlist")
    return get_stock_snapshot_service().get_analysis_payload(symbol)


@router.get("/market/stock-snapshot/{symbol}")
async def get_market_stock_snapshot(symbol: str) -> dict[str, object]:
    """Return the latest persisted per-symbol stock analysis snapshot."""
    record_client_activity("watchlist")
    service = get_stock_snapshot_service()
    snapshot = service.get_latest_snapshot(symbol)
    if snapshot is None:
        refresh_started = service.trigger_background_refresh(symbol)
        return {
            "status": "initializing",
            "source_state": "initializing",
            "symbol": symbol.upper(),
            "snapshot_id": None,
            "refresh_started": refresh_started or service.is_refreshing(symbol),
        }
    response = snapshot_response(snapshot)
    response["refresh_in_progress"] = service.is_refreshing(symbol)
    return response


@router.get("/market/stock-snapshot/{symbol}/status")
async def get_market_stock_snapshot_status(symbol: str) -> dict[str, object]:
    """Return stock snapshot freshness and refresh status for one symbol."""
    return get_stock_snapshot_service().get_status(symbol)


@router.post("/market/stock-snapshot/{symbol}/refresh")
async def refresh_market_stock_snapshot(symbol: str) -> dict[str, object]:
    """Trigger a background stock snapshot refresh for one symbol."""
    started = get_stock_snapshot_service().trigger_background_refresh(symbol)
    return {"status": "queued" if started else "deduped", "symbol": symbol.upper(), "refresh_started": started}


@router.delete("/market/stock-snapshot/{symbol}")
async def clear_market_stock_snapshot(symbol: str) -> dict[str, object]:
    """Clear persisted stock snapshots for one symbol."""
    deleted = get_stock_snapshot_service().clear_symbol(symbol)
    return {"status": "cleared", "symbol": symbol.upper(), "deleted": deleted}


@router.delete("/market/stock-snapshots")
async def clear_market_stock_snapshots(mode: str = Query(default="incompatible")) -> dict[str, object]:
    """Clear incompatible, test/mock namespace, or all persisted stock snapshots."""
    service = get_stock_snapshot_service()
    if mode == "all":
        deleted = service.clear_all()
    elif mode in {"test", "mock"}:
        deleted = service.clear_namespace(mode)
    else:
        mode = "incompatible"
        deleted = service.clear_incompatible()
    return {"status": "cleared", "mode": mode, "deleted": deleted}


@router.get("/market/details/decision")
async def get_market_decision_details() -> dict[str, object]:
    """Return grouped decision details for the Market detail modal."""
    record_client_activity("market")
    return snapshot_details_payload("decision")


@router.get("/market/details/institutional")
async def get_market_institutional_details() -> dict[str, object]:
    """Return grouped institutional details on demand."""
    record_client_activity("institutional")
    return snapshot_details_payload("institutional")


@router.get("/market/details/structure")
async def get_market_structure_details() -> dict[str, object]:
    """Return grouped market-structure details on demand."""
    record_client_activity("market")
    record_client_activity("sectors")
    return snapshot_details_payload("structure")


@router.get("/user/watchlist/{ticker}")
async def get_watchlist_item(ticker: str) -> Dict[str, Any]:
    """Return stub data for a given watchlist ticker."""
    return build_user_watchlist_item(ticker)
