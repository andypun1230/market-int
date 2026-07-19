from app.models.market import (
    AggressivenessResponse,
    DecisionDashboardResponse,
    MarketChecklistItem,
    MarketChecklistResponse,
    MarketPlaybookResponse,
    SuggestedExposure,
    TradingStyleItem,
    TradingStyleResponse,
)
from app.services.breadth import calculate_market_breadth
from app.services.dashboard_comparison import build_dashboard_comparison
from app.services.decision_confidence import calculate_decision_confidence
from app.services.fear_greed import build_fear_greed_index
from app.services.industry_rotation import build_industry_rotation_dashboard
from app.services.industry_groups import build_industry_groups
from app.services.institutional_intelligence import build_institutional_intelligence_dashboard
from app.services.institutional_activity import calculate_institutional_bias
from app.services.leadership import build_leadership_dashboard
from app.services.market_cap_rotation import build_market_cap_rotation
from app.services.market_health import calculate_market_health
from app.services.probability_engine import build_probability_engine
from app.services.regime import build_market_regime
from app.services.risk_dashboard_v2 import build_risk_dashboard_v2
from app.services.sector_etfs import build_sector_etf_dashboard
from app.services.sectors import build_market_sectors
from app.services.service_cache import get_or_compute, get_service_ttl
from app.services.theme_provenance import static_strategy_preference_provenance


DISCLAIMER = "Educational market decision support only, not financial advice."


def calculate_aggressiveness() -> AggressivenessResponse:
    market_health = calculate_market_health()
    regime = build_market_regime()
    institutional = calculate_institutional_bias()
    cap_rotation = build_market_cap_rotation()
    fear_greed = build_fear_greed_index()
    sector_etfs = build_sector_etf_dashboard()

    score = market_health.overall_score
    reasons = [f"Market Health is {market_health.status}"]
    cautions: list[str] = []
    data_mode = (market_health.data_quality or {}).get("overall_mode", "mock")

    if institutional.bias == "Bullish":
        score += 5
        reasons.append("Institutional activity is Bullish")
    elif institutional.bias in ("Cautious", "Bearish"):
        cautions.append(f"Institutional activity is {institutional.bias}")

    if regime.status == "Confirmed Uptrend":
        score += 5
        reasons.append("Market regime is Confirmed Uptrend")
    elif regime.status == "Choppy / Sideways":
        score -= 8
        cautions.append("Market regime is choppy")

    if fear_greed.status == "Extreme Greed":
        score -= 5
        cautions.append("Fear & Greed is Extreme Greed")
    elif fear_greed.status in ("Greed", "Extreme Greed"):
        cautions.append("Fear & Greed is elevated")

    if regime.volatility.status == "High":
        score -= 10
        cautions.append("Volatility is High")

    if cap_rotation.leader in ("Mega Cap", "Large Cap"):
        reasons.append(f"{cap_rotation.leader} leadership remains strong")

    if sector_etfs.items and sector_etfs.items[0].status in ("Leading", "Strong"):
        reasons.append(f"{sector_etfs.items[0].sector} sector ETF leadership is supportive")

    if regime.breadth.stocks_above_50ma < 70:
        cautions.append("Breadth is not perfect")

    if data_mode != "live":
        cautions.append(f"Market analysis data mode is {data_mode}")

    score = clamp(round(score), 0, 100)
    status = get_aggressiveness_status(score)

    return AggressivenessResponse(
        score=score,
        status=status,
        suggested_exposure=get_suggested_exposure(status),
        summary=build_aggressiveness_summary(market_health.status, regime.breadth.status, fear_greed.status),
        reasons=reasons,
        cautions=cautions or ["No major caution flags in the current mock decision model."],
    )


def recommend_trading_styles() -> TradingStyleResponse:
    market_health = calculate_market_health()
    regime = build_market_regime()
    breadth = calculate_market_breadth()
    sectors = build_market_sectors()
    fear_greed = build_fear_greed_index()

    top_sector = sectors.leaders[0] if sectors.leaders else None
    health_score = market_health.overall_score
    breadth_score = breadth.percent_above_50ema
    sector_strength = top_sector.relative_strength_score if top_sector else 50
    volatility_penalty = 20 if regime.volatility.status == "High" else 0
    greed_penalty = 8 if fear_greed.status == "Extreme Greed" else 0

    style_rows = [
        (
            "Momentum Breakouts",
            round((health_score * 0.35) + (sector_strength * 0.35) + (breadth_score * 0.20) - greed_penalty),
            "Healthy market with strong sector and industry leadership supports momentum setups.",
        ),
        (
            "Trend Following",
            round((health_score * 0.45) + (sector_strength * 0.25) + (breadth_score * 0.20) - (volatility_penalty * 0.25)),
            "Trend-following remains useful while indexes and leading groups continue to hold trend.",
        ),
        (
            "Pullback Buying",
            round((health_score * 0.30) + (breadth_score * 0.25) + (100 - min(fear_greed.score, 100)) * 0.20 + 25),
            "Pullbacks are preferred when leadership is strong but sentiment is elevated.",
        ),
        (
            "Mean Reversion",
            round((100 - health_score) * 0.35 + fear_greed.score * 0.25 + volatility_penalty + 25),
            "Mean reversion improves when sentiment stretches or market health deteriorates.",
        ),
        (
            "Short Selling",
            round((100 - health_score) * 0.45 + volatility_penalty + (20 if regime.status == "Correction" else 0)),
            "Short selling remains lower priority unless market health weakens materially.",
        ),
    ]

    items = [
        TradingStyleItem(
            style=style,
            score=clamp(score, 0, 100),
            rating=get_style_rating(clamp(score, 0, 100)),
            status=get_style_status(clamp(score, 0, 100)),
            reason=reason,
        )
        for style, score, reason in style_rows
    ]
    ranked_items = sorted(items, key=lambda item: item.score, reverse=True)
    preferred_style = ranked_items[0].style if ranked_items else "N/A"

    return TradingStyleResponse(
        items=ranked_items,
        preferred_style=preferred_style,
        summary=(
            f"{preferred_style} is preferred while market health is {market_health.status} "
            "and leadership remains concentrated in stronger areas."
        ),
    )


def build_market_checklist() -> MarketChecklistResponse:
    market_health = calculate_market_health()
    breadth = calculate_market_breadth()
    institutional = calculate_institutional_bias()
    sectors = build_market_sectors()
    regime = build_market_regime()
    fear_greed = build_fear_greed_index()
    cap_rotation = build_market_cap_rotation()

    top_sector = sectors.leaders[0] if sectors.leaders else None
    distribution_days = regime.institutional_activity.distribution_days

    items = [
        MarketChecklistItem(
            label="Market health above 70",
            passed=market_health.overall_score >= 70,
            value=f"{market_health.overall_score} / 100",
        ),
        MarketChecklistItem(
            label="Breadth above 50EMA >= 60%",
            passed=breadth.percent_above_50ema >= 60,
            value=f"{breadth.percent_above_50ema:.1f}%",
        ),
        MarketChecklistItem(
            label="Institutional bias Bullish or Neutral",
            passed=institutional.bias in ("Bullish", "Neutral"),
            value=institutional.bias,
        ),
        MarketChecklistItem(
            label="Top sector strength >= 75",
            passed=(top_sector.relative_strength_score if top_sector else 0) >= 75,
            value=f"{top_sector.relative_strength_score if top_sector else 'N/A'} / 100",
        ),
        MarketChecklistItem(
            label="Volatility not High",
            passed=regime.volatility.status != "High",
            value=regime.volatility.status,
        ),
        MarketChecklistItem(
            label="Distribution days <= 3",
            passed=distribution_days <= 3,
            value=str(distribution_days),
        ),
        MarketChecklistItem(
            label="Fear & Greed not Extreme Greed",
            passed=fear_greed.status != "Extreme Greed",
            value=fear_greed.status,
        ),
        MarketChecklistItem(
            label="Mega or large cap leadership positive",
            passed=cap_rotation.leader in ("Mega Cap", "Large Cap"),
            value=cap_rotation.leader,
        ),
    ]
    score = sum(1 for item in items if item.passed)

    return MarketChecklistResponse(
        score=score,
        max_score=len(items),
        grade=get_checklist_grade(score),
        items=items,
        summary=f"{score} of {len(items)} checklist items are positive.",
    )


def build_market_playbook() -> MarketPlaybookResponse:
    aggressiveness = calculate_aggressiveness()
    trading_styles = recommend_trading_styles()
    sectors = build_market_sectors()
    industry_groups = build_industry_groups()
    cap_rotation = build_market_cap_rotation()
    fear_greed = build_fear_greed_index()
    breadth = calculate_market_breadth()

    top_sector = sectors.leaders[0].name if sectors.leaders else "N/A"
    top_group = industry_groups.items[0].name if industry_groups.items else "N/A"
    main_risk = build_main_risk(fear_greed.status, breadth.percent_above_50ema)

    return MarketPlaybookResponse(
        headline=get_playbook_headline(aggressiveness.status),
        summary=(
            "The market remains constructive but not perfect. Focus on leading sectors "
            "and verified setups, and avoid chasing extended moves."
        ),
        preferred_strategy=trading_styles.preferred_style,
        suggested_aggressiveness=aggressiveness.status,
        top_sector=top_sector,
        top_industry_group=top_group,
        top_industry_group_provenance=static_strategy_preference_provenance(industry_groups.as_of),
        cap_rotation_leader=cap_rotation.leader,
        main_risk=main_risk,
        action_guidelines=[
            "Prioritize high-RS stocks in leading sectors; configured strategy baskets are not live theme evidence.",
            "Prefer breakouts with strong volume confirmation.",
            "Avoid chasing stocks far above short-term moving averages.",
        ],
        avoid=[
            "Low-RS laggards",
            "Overextended setups",
            "Large positions before major macro events",
        ],
        disclaimer=DISCLAIMER,
    )


def build_decision_dashboard() -> DecisionDashboardResponse:
    return get_or_compute(
        "decision-dashboard",
        get_service_ttl("SERVICE_CACHE_DECISION_TTL_SECONDS", 120),
        _build_decision_dashboard_uncached,
    )


def _build_decision_dashboard_uncached() -> DecisionDashboardResponse:
    aggressiveness = calculate_aggressiveness()
    trading_styles = recommend_trading_styles()
    checklist = build_market_checklist()
    playbook = build_market_playbook()
    probabilities = build_probability_engine()
    leadership = build_leadership_dashboard()
    decision_confidence = calculate_decision_confidence()
    comparison = build_dashboard_comparison()
    industry_rotation = build_industry_rotation_dashboard()
    risk_dashboard = build_risk_dashboard_v2()
    institutional_intelligence = build_institutional_intelligence_dashboard()

    return DecisionDashboardResponse(
        aggressiveness=aggressiveness,
        trading_styles=trading_styles,
        checklist=checklist,
        playbook=playbook,
        probabilities=probabilities,
        leadership=leadership,
        decision_confidence=decision_confidence,
        comparison=comparison,
        industry_rotation=industry_rotation,
        risk_dashboard=risk_dashboard,
        institutional_intelligence=institutional_intelligence,
    )


def get_aggressiveness_status(score: int) -> str:
    if score >= 85:
        return "Highly Aggressive"
    if score >= 70:
        return "Moderately Aggressive"
    if score >= 55:
        return "Selective"
    if score >= 40:
        return "Defensive"
    return "Risk-Off"


def get_suggested_exposure(status: str) -> SuggestedExposure:
    exposure_by_status = {
        "Highly Aggressive": SuggestedExposure(
            stocks=90,
            cash=10,
            margin="Moderate acceptable",
            options="Suitable for high-quality breakouts",
        ),
        "Moderately Aggressive": SuggestedExposure(
            stocks=80,
            cash=20,
            margin="Light / selective",
            options="Suitable for strong setups only",
        ),
        "Selective": SuggestedExposure(
            stocks=60,
            cash=40,
            margin="Avoid",
            options="Limited / defined risk only",
        ),
        "Defensive": SuggestedExposure(
            stocks=35,
            cash=65,
            margin="Avoid",
            options="Avoid directional long calls",
        ),
        "Risk-Off": SuggestedExposure(
            stocks=15,
            cash=85,
            margin="Avoid",
            options="Avoid",
        ),
    }

    return exposure_by_status.get(status, exposure_by_status["Selective"])


def build_aggressiveness_summary(
    market_health_status: str,
    breadth_status: str,
    fear_greed_status: str,
) -> str:
    return (
        f"Market health is {market_health_status.lower()}, but {breadth_status.lower()} breadth "
        f"and {fear_greed_status.lower()} sentiment suggest staying selective rather than fully aggressive."
    )


def get_style_rating(score: int) -> int:
    if score >= 85:
        return 5
    if score >= 70:
        return 4
    if score >= 55:
        return 3
    if score >= 40:
        return 2
    return 1


def get_style_status(score: int) -> str:
    if score >= 80:
        return "Preferred"
    if score >= 65:
        return "Suitable"
    if score >= 50:
        return "Selective"
    return "Avoid"


def get_checklist_grade(score: int) -> str:
    if score >= 7:
        return "Healthy"
    if score >= 5:
        return "Mixed"
    if score >= 3:
        return "Weak"
    return "Risk-Off"


def get_playbook_headline(aggressiveness_status: str) -> str:
    if aggressiveness_status in ("Highly Aggressive", "Moderately Aggressive"):
        return "Stay selectively aggressive"
    if aggressiveness_status == "Selective":
        return "Be selective and confirmation-driven"
    if aggressiveness_status == "Defensive":
        return "Defend capital and wait for cleaner setups"
    return "Risk-off posture preferred"


def build_main_risk(fear_greed_status: str, percent_above_50ema: float) -> str:
    if fear_greed_status in ("Greed", "Extreme Greed") and percent_above_50ema < 70:
        return "Fear & Greed is elevated and breadth is not perfect."
    if fear_greed_status in ("Greed", "Extreme Greed"):
        return "Fear & Greed is elevated, so avoid chasing extended setups."
    if percent_above_50ema < 60:
        return "Breadth is not broad enough for maximum aggressiveness."
    return "The main risk is overextending before confirmation."


def clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))
