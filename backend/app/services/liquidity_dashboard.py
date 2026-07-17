from statistics import mean

from app.models.market import LiquidityDashboardResponse, SymbolLiquidityResponse
from app.providers.selector import get_liquidity_provider
from app.services.service_cache import get_or_compute, get_service_ttl

WATCH_SYMBOLS = ["SPY", "QQQ", "IWM", "DIA", "MU", "NVDA", "ARM", "SNDK"]


def build_liquidity_dashboard() -> LiquidityDashboardResponse:
    return get_or_compute(
        "liquidity-dashboard",
        get_service_ttl("SERVICE_CACHE_INSTITUTIONAL_TTL_SECONDS", 300),
        _build_liquidity_dashboard_uncached,
    )


def _build_liquidity_dashboard_uncached() -> LiquidityDashboardResponse:
    items = [analyze_symbol_liquidity(symbol) for symbol in WATCH_SYMBOLS]
    score = round(mean(item.liquidity_score for item in items)) if items else 55
    warnings = sorted({warning for item in items for warning in ((item.metadata or {}).get("warnings") or [])})
    weakest = min(items, key=lambda item: item.liquidity_score) if items else None
    modes = {(item.metadata or {}).get("source", "mock") for item in items}
    fallback_used = any((item.metadata or {}).get("fallback_used") for item in items)

    return LiquidityDashboardResponse(
        score=score,
        status=get_liquidity_status(score),
        spread_condition=build_spread_condition(items),
        depth_condition="Estimated from dollar volume; hidden order-book liquidity is not inferred.",
        funding_condition="Stable",
        volume_condition=build_volume_condition(items),
        warnings=warnings or ["No major liquidity warnings from the current proxy inputs."],
        summary=(
            f"Liquidity is {get_liquidity_status(score).lower()} across the monitored market/watchlist universe. "
            f"Weakest liquidity score: {weakest.symbol if weakest else 'N/A'}."
        ),
        items=[item.model_dump() for item in items],
        metadata={
            "overall_mode": "mixed" if fallback_used else "live" if all(source != "mock" for source in modes) else "mock",
            "fallback_used": fallback_used,
            "coverage_percent": 100.0 if items else 0.0,
            "limitations": [
                "Liquidity score uses quote/history proxies and does not infer hidden order-book depth.",
            ],
        },
    )


def analyze_symbol_liquidity(symbol: str) -> SymbolLiquidityResponse:
    item = get_liquidity_provider().get_quote_liquidity(symbol)
    return SymbolLiquidityResponse(**item.model_dump())


def get_liquidity_status(score: float) -> str:
    if score >= 85:
        return "Excellent"
    if score >= 72:
        return "Strong"
    if score >= 58:
        return "Adequate"
    if score >= 40:
        return "Thin"
    return "Poor"


def build_spread_condition(items: list[SymbolLiquidityResponse]) -> str:
    spread_values = [
        item.spread_percent for item in items if item.spread_percent is not None
    ]
    if not spread_values:
        return "Incomplete quote data"
    average = mean(spread_values)
    if average <= 0.1:
        return "Tight"
    if average <= 0.35:
        return "Normal"
    return "Wide"


def build_volume_condition(items: list[SymbolLiquidityResponse]) -> str:
    relative_values = [
        item.relative_volume for item in items if item.relative_volume is not None
    ]
    if not relative_values:
        return "Incomplete volume data"
    average = mean(relative_values)
    if average >= 1.2:
        return "Above-average participation"
    if average >= 0.8:
        return "Normal participation"
    return "Below-average participation"
