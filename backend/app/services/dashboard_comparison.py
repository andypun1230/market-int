from app.models.market import DashboardComparisonItem, DashboardComparisonResponse
from app.services.breadth import calculate_market_breadth
from app.services.fear_greed import build_fear_greed_index
from app.services.market_health import calculate_market_health
from app.services.sectors import build_market_sectors
from app.services.service_cache import get_or_compute, get_service_ttl


PREVIOUS_DAY_VALUES = {
    "Market Health": 76,
    "Breadth": 62.5,
    "Aggressiveness": 74,
    "Fear & Greed": 64,
    "Sector Strength": 78,
}


def build_dashboard_comparison() -> DashboardComparisonResponse:
    return get_or_compute(
        "dashboard-comparison",
        get_service_ttl("SERVICE_CACHE_DECISION_TTL_SECONDS", 120),
        _build_dashboard_comparison_uncached,
    )


def _build_dashboard_comparison_uncached() -> DashboardComparisonResponse:
    from app.services.decision_intelligence import calculate_aggressiveness

    market_health = calculate_market_health()
    breadth = calculate_market_breadth()
    aggressiveness = calculate_aggressiveness()
    fear_greed = build_fear_greed_index()
    sectors = build_market_sectors()
    sector_strength = sectors.leaders[0].relative_strength_score if sectors.leaders else 0

    today_values = {
        "Market Health": market_health.overall_score,
        "Breadth": breadth.percent_above_50ema,
        "Aggressiveness": aggressiveness.score,
        "Fear & Greed": fear_greed.score,
        "Sector Strength": sector_strength,
    }
    items = [
        DashboardComparisonItem(
            metric=metric,
            today=round(today, 2) if isinstance(today, float) else today,
            yesterday=yesterday,
            change=round(today - yesterday, 2),
        )
        for metric, today in today_values.items()
        for yesterday in [PREVIOUS_DAY_VALUES[metric]]
    ]

    improving = [item.metric for item in items if isinstance(item.change, (int, float)) and item.change > 0]
    weakening = [item.metric for item in items if isinstance(item.change, (int, float)) and item.change < 0]

    return DashboardComparisonResponse(
        items=items,
        summary=(
            f"Improving: {', '.join(improving) if improving else 'none'}. "
            f"Weakening: {', '.join(weakening) if weakening else 'none'}."
        ),
    )
