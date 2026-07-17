from app.models.market import ProbabilityItem, ProbabilityResponse
from app.services.breadth import calculate_market_breadth
from app.services.fear_greed import build_fear_greed_index
from app.services.industry_groups import build_industry_groups
from app.services.institutional_activity import calculate_institutional_bias
from app.services.market_health import calculate_market_health
from app.services.regime import build_market_regime
from app.services.sectors import build_market_sectors
from app.services.service_cache import get_or_compute, get_service_ttl


def build_probability_engine() -> ProbabilityResponse:
    return get_or_compute(
        "probabilities",
        get_service_ttl("SERVICE_CACHE_DECISION_TTL_SECONDS", 120),
        _build_probability_engine_uncached,
    )


def _build_probability_engine_uncached() -> ProbabilityResponse:
    market_health = calculate_market_health()
    regime = build_market_regime()
    breadth = calculate_market_breadth()
    institutional = calculate_institutional_bias()
    sectors = build_market_sectors()
    industry_groups = build_industry_groups()
    fear_greed = build_fear_greed_index()

    health = market_health.overall_score
    breadth_score = round(breadth.percent_above_50ema)
    sector_score = sectors.leaders[0].relative_strength_score if sectors.leaders else 55
    group_score = industry_groups.items[0].relative_strength_score if industry_groups.items else 55
    institutional_bonus = 8 if institutional.bias == "Bullish" else 0
    trend_bonus = 8 if regime.status == "Confirmed Uptrend" else 0
    sentiment_stretch = max(0, fear_greed.score - 70)
    volatility_penalty = 12 if regime.volatility.status == "High" else 0

    rows = [
        (
            "Momentum Breakouts",
            health * 0.32 + sector_score * 0.25 + group_score * 0.20 + trend_bonus + institutional_bonus - sentiment_stretch * 0.35,
            "Breakout odds improve because market health, broad sector leadership, and industry group strength are constructive.",
        ),
        (
            "Trend Continuation",
            health * 0.40 + breadth_score * 0.20 + sector_score * 0.20 + trend_bonus - volatility_penalty,
            "Trend continuation is supported by the confirmed trend and broad participation above key moving averages.",
        ),
        (
            "Pullback Buying",
            health * 0.30 + breadth_score * 0.20 + group_score * 0.15 + (100 - min(fear_greed.score, 100)) * 0.25,
            "Pullbacks are attractive when leadership is intact but sentiment argues against chasing.",
        ),
        (
            "Gap & Go",
            health * 0.25 + sector_score * 0.20 + institutional_bonus + trend_bonus - sentiment_stretch * 0.45,
            "Gap-and-go setups need strong tape quality and volume confirmation, but elevated sentiment lowers the edge.",
        ),
        (
            "Mean Reversion",
            (100 - health) * 0.25 + fear_greed.score * 0.35 + volatility_penalty + 25,
            "Mean reversion probability rises when sentiment stretches or volatility starts to matter.",
        ),
        (
            "Short Selling",
            (100 - health) * 0.35 + (100 - breadth_score) * 0.25 + volatility_penalty + (15 if regime.status == "Correction" else 0),
            "Short selling remains lower probability while health, trend, and leadership remain constructive.",
        ),
    ]

    items = [
        ProbabilityItem(
            strategy=name,
            probability=probability,
            confidence=build_probability_confidence(probability, health, breadth_score),
            explanation=explanation,
        )
        for name, score, explanation in rows
        for probability in [clamp(round(score))]
    ]

    items = sorted(items, key=lambda item: item.probability, reverse=True)
    return ProbabilityResponse(
        items=items,
        summary=f"{items[0].strategy} has the highest deterministic probability score at {items[0].probability}%.",
    )


def build_probability_confidence(probability: int, health: int, breadth: int) -> int:
    agreement = 100 - abs(health - breadth)
    return clamp(round((probability * 0.55) + (agreement * 0.45)))


def clamp(value: int) -> int:
    return max(0, min(100, value))
