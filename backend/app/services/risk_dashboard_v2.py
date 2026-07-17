from app.models.market import RiskDashboardContributor, RiskDashboardV2Response
from app.services.breadth import calculate_market_breadth
from app.services.dashboard_comparison import build_dashboard_comparison
from app.services.fear_greed import build_fear_greed_index
from app.services.market_health import calculate_market_health
from app.services.regime import build_market_regime
from app.services.service_cache import get_or_compute, get_service_ttl


def build_risk_dashboard_v2() -> RiskDashboardV2Response:
    return get_or_compute(
        "risk-dashboard-v2",
        get_service_ttl("SERVICE_CACHE_DECISION_TTL_SECONDS", 120),
        _build_risk_dashboard_v2_uncached,
    )


def _build_risk_dashboard_v2_uncached() -> RiskDashboardV2Response:
    market_health = calculate_market_health()
    breadth = calculate_market_breadth()
    fear_greed = build_fear_greed_index()
    regime = build_market_regime()
    comparison = build_dashboard_comparison()

    base_risk = 100 - market_health.overall_score
    risk_score = base_risk
    contributors: list[RiskDashboardContributor] = [
        RiskDashboardContributor(
            label="Market Health",
            impact="Lower risk" if market_health.overall_score >= 70 else "Higher risk",
            explanation=f"Market health is {market_health.status} at {market_health.overall_score}/100.",
        )
    ]

    if breadth.percent_above_50ema < 70:
        risk_score += 8
        contributors.append(
            RiskDashboardContributor(
                label="Breadth",
                impact="Higher risk",
                explanation=f"Only {breadth.percent_above_50ema:.1f}% of stocks are above the 50EMA.",
            )
        )

    if fear_greed.status in ("Greed", "Extreme Greed"):
        risk_score += 7 if fear_greed.status == "Greed" else 12
        contributors.append(
            RiskDashboardContributor(
                label="Sentiment",
                impact="Higher risk",
                explanation=f"Fear & Greed is {fear_greed.status} at {fear_greed.score}/100.",
            )
        )

    if regime.volatility.status in ("Elevated", "High"):
        risk_score += 8 if regime.volatility.status == "Elevated" else 15
        contributors.append(
            RiskDashboardContributor(
                label="Volatility",
                impact="Higher risk",
                explanation=f"Volatility is {regime.volatility.status} with VIX at {regime.volatility.vix}.",
            )
        )

    changed_items = [
        item for item in comparison.items
        if isinstance(item.change, (int, float)) and abs(item.change) >= 2
    ]
    if changed_items:
        contributors.append(
            RiskDashboardContributor(
                label="Daily Change",
                impact="Changed",
                explanation=", ".join(
                    f"{item.metric} changed {item.change:+.1f}" for item in changed_items[:3]
                ),
            )
        )

    risk_score = max(0, min(100, round(risk_score)))
    warnings = build_warnings(risk_score, fear_greed.status, breadth.percent_above_50ema)

    return RiskDashboardV2Response(
        score=risk_score,
        contributors=contributors,
        warnings=warnings,
        upcoming_events=["CPI tomorrow", "Fed speakers", "Large-cap tech earnings"],
        summary=(
            f"Risk score is {risk_score}/100. The main change drivers are "
            f"{contributors[-1].label.lower()} and sentiment/breadth conditions."
        ),
    )


def build_warnings(risk_score: int, fear_greed_status: str, percent_above_50ema: float) -> list[str]:
    warnings: list[str] = []

    if risk_score >= 40:
        warnings.append("Avoid oversized positions while risk remains elevated.")
    if fear_greed_status in ("Greed", "Extreme Greed"):
        warnings.append("Sentiment is elevated, so avoid chasing extended moves.")
    if percent_above_50ema < 70:
        warnings.append("Breadth is healthy but not broad enough for maximum aggression.")

    return warnings or ["No major risk warning dominates the current mock dashboard."]
