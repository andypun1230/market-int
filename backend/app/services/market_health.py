from types import SimpleNamespace

from app.models.market import MarketHealthComponents, MarketHealthResponse
from app.services.breadth import calculate_market_breadth
from app.services.decision_confidence import calculate_decision_confidence_from_inputs
from app.services.fear_greed import build_fear_greed_index
from app.services.institutional_activity import build_institutional_activity
from app.services.leadership import build_leadership_dashboard
from app.services.market_cap_rotation import build_market_cap_rotation
from app.services.market_data import get_index_snapshots
from app.services.regime import build_market_regime
from app.services.sector_etfs import build_sector_etf_dashboard
from app.services.sectors import build_market_sectors
from app.services.service_cache import get_or_compute, get_service_ttl
from app.services.volume_analysis import build_volume_analysis

VOLUME_QUALITY_SCORES = {
    "Excellent": 90,
    "Strong": 80,
    "Average": 60,
    "Weak": 40,
    "Poor": 25,
}

INSTITUTIONAL_SCORES = {
    "Bullish": 90,
    "Neutral": 60,
    "Cautious": 50,
    "Bearish": 25,
}

REGIME_SCORES = {
    "Confirmed Uptrend": 90,
    "Uptrend Under Pressure": 70,
    "Choppy / Sideways": 55,
    "Correction": 30,
}

VOLATILITY_SCORES = {
    "Low": 85,
    "Normal": 85,
    "Elevated": 55,
    "High": 25,
}


def calculate_market_health() -> MarketHealthResponse:
    return get_or_compute(
        "market-health",
        get_service_ttl("SERVICE_CACHE_MARKET_HEALTH_TTL_SECONDS", 120),
        _calculate_market_health_uncached,
    )


def _calculate_market_health_uncached() -> MarketHealthResponse:
    index_snapshots = get_index_snapshots()
    breadth = calculate_market_breadth()
    regime = build_market_regime()
    sectors = build_market_sectors()
    sector_etfs = build_sector_etf_dashboard()
    leadership = build_leadership_dashboard()
    institutional_activity = build_institutional_activity()
    volume = build_volume_analysis()

    momentum_score = calculate_momentum_score(index_snapshots)
    breadth_score = clamp_score(breadth.percent_above_50ema)
    trend_score = REGIME_SCORES.get(regime.status, 55)
    volume_score = calculate_volume_score(volume.items)
    institutional_score = INSTITUTIONAL_SCORES.get(institutional_activity.bias.bias, 60)
    volatility_score = VOLATILITY_SCORES.get(regime.volatility.status, 55)
    sector_strength_score = calculate_sector_strength_score(sector_etfs.items)
    components = MarketHealthComponents(
        momentum=momentum_score,
        breadth=breadth_score,
        trend=trend_score,
        volume=volume_score,
        institutional=institutional_score,
        volatility=volatility_score,
        sector_strength=sector_strength_score,
    )
    overall_score = round(
        (components.momentum * 0.20)
        + (components.breadth * 0.20)
        + (components.trend * 0.15)
        + (components.volume * 0.10)
        + (components.institutional * 0.15)
        + (components.volatility * 0.10)
        + (components.sector_strength * 0.10)
    )
    status = classify_market_health(overall_score)
    explanations = {
        "momentum": build_momentum_explanation(index_snapshots, momentum_score),
        "breadth": (
            f"{breadth.percent_above_50ema:.2f}% of the core liquid-stock breadth universe "
            f"is above the 50EMA with {breadth.coverage_percent or 0:.1f}% coverage."
        ),
        "trend": f"Market regime is {regime.status}, mapping to a trend score of {trend_score}.",
        "volume": f"Watchlist volume quality averages to {volume_score}.",
        "institutional": (
            f"Institutional bias is {institutional_activity.bias.bias}, "
            f"mapping to {institutional_score}."
        ),
        "volatility": (
            f"VIX status is {regime.volatility.status} at {regime.volatility.vix}, "
            f"mapping to {volatility_score}."
        ),
        "sector_strength": (
            f"Top sector ETF relative strength averages to {sector_strength_score}."
        ),
    }
    data_quality = build_data_quality(index_snapshots, sector_etfs.items, breadth, leadership)
    improving_factors = build_improving_factors(components, sector_etfs.items, institutional_activity.bias.bias)
    weakening_factors = build_weakening_factors(components, breadth.percent_above_50ema)
    decision_confidence = calculate_decision_confidence_from_inputs(
        market_health=SimpleNamespace(overall_score=overall_score, status=status),
        breadth=breadth,
        regime=regime,
        institutional=institutional_activity.bias,
        fear_greed=build_fear_greed_index(),
        sectors=sectors,
        cap_rotation=build_market_cap_rotation(),
    )

    return MarketHealthResponse(
        overall_score=overall_score,
        status=status,
        components=components,
        component_explanations=explanations,
        summary=(
            f"Market health is {status.lower()} with strong sector leadership and "
            f"{institutional_activity.bias.bias.lower()} institutional activity, "
            "although breadth and volatility still need monitoring."
        ),
        improving_factors=improving_factors,
        weakening_factors=weakening_factors,
        decision_confidence=decision_confidence.model_dump(),
        data_quality=data_quality,
    )


def calculate_momentum_score(index_snapshots: list) -> int:
    snapshot_by_symbol = {snapshot.symbol: snapshot for snapshot in index_snapshots}
    spy = snapshot_by_symbol.get("SPY")
    qqq = snapshot_by_symbol.get("QQQ")
    spy_above_50ema = bool(spy and spy.ema_50 is not None and spy.price > spy.ema_50)
    qqq_above_50ema = bool(qqq and qqq.ema_50 is not None and qqq.price > qqq.ema_50)

    if spy_above_50ema and qqq_above_50ema:
        return 90
    if spy_above_50ema or qqq_above_50ema:
        return 65
    return 35


def calculate_volume_score(items: list) -> int:
    scores = [
        item.volume_quality_score
        if item.volume_quality_score is not None
        else VOLUME_QUALITY_SCORES.get(item.volume_quality, 60)
        for item in items
    ]

    if not scores:
        return 60

    return clamp_score(sum(scores) / len(scores))


def calculate_sector_strength_score(leaders: list) -> int:
    top_scores = [
        sector.relative_strength_score
        for sector in leaders[:3]
        if sector.relative_strength_score is not None
    ]

    if not top_scores:
        return 60

    return clamp_score(sum(top_scores) / len(top_scores))


def classify_market_health(score: int) -> str:
    if score >= 85:
        return "Very Healthy"
    if score >= 70:
        return "Healthy"
    if score >= 55:
        return "Mixed"
    if score >= 40:
        return "Weak"
    return "Risk-Off"


def build_momentum_explanation(index_snapshots: list, score: int) -> str:
    snapshot_by_symbol = {snapshot.symbol: snapshot for snapshot in index_snapshots}
    spy = snapshot_by_symbol.get("SPY")
    qqq = snapshot_by_symbol.get("QQQ")
    spy_text = "above" if spy and spy.ema_50 is not None and spy.price > spy.ema_50 else "below"
    qqq_text = "above" if qqq and qqq.ema_50 is not None and qqq.price > qqq.ema_50 else "below"

    return f"SPY is {spy_text} its 50EMA and QQQ is {qqq_text} its 50EMA, producing {score}."


def build_improving_factors(
    components: MarketHealthComponents,
    sector_leaders: list,
    institutional_bias: str,
) -> list[str]:
    factors: list[str] = []

    if components.sector_strength >= 80 and sector_leaders:
        factors.append("Sector leadership remains strong")
    if components.institutional >= 80 or institutional_bias == "Bullish":
        factors.append("Institutional activity is supportive")
    if components.momentum >= 80:
        factors.append("SPY and QQQ remain above key intermediate trend levels")
    if components.volume >= 75:
        factors.append("Watchlist volume quality is constructive")

    return factors or ["No major improving factor dominates the current market health score."]


def build_weakening_factors(
    components: MarketHealthComponents,
    percent_above_50ema: float,
) -> list[str]:
    factors: list[str] = []

    if components.breadth < 80:
        factors.append("Breadth remains mixed")
    if percent_above_50ema < 60:
        factors.append("Fewer stocks are holding above the 50EMA")
    if components.volatility < 70:
        factors.append("Volatility is a headwind")
    if components.volume < 60:
        factors.append("Volume confirmation is not broad")

    return factors or ["No major weakening factor is dominant right now."]


def build_data_quality(
    index_snapshots: list,
    sector_etfs: list,
    breadth: object,
    leadership: object,
) -> dict[str, list[str] | str]:
    live_components: list[str] = []
    fallback_components: list[str] = []
    mock_components = ["institutional_activity", "options_intelligence", "intraday_multi_timeframe"]

    if index_snapshots and all(getattr(snapshot, "quote_is_live", False) for snapshot in index_snapshots):
        live_components.append("index_quotes")
    elif any(getattr(snapshot, "quote_is_live", False) for snapshot in index_snapshots):
        live_components.append("partial_index_quotes")

    if index_snapshots and all(getattr(snapshot, "history_is_live", False) for snapshot in index_snapshots):
        live_components.append("index_history")
    elif any(getattr(snapshot, "history_is_live", False) for snapshot in index_snapshots):
        live_components.append("partial_index_history")

    if sector_etfs and all(getattr(item, "quote_is_live", False) for item in sector_etfs):
        live_components.append("sector_etf_quotes")
    elif any(getattr(item, "quote_is_live", False) for item in sector_etfs):
        live_components.append("partial_sector_etf_quotes")

    if sector_etfs and all(getattr(item, "history_is_live", False) for item in sector_etfs):
        live_components.append("sector_etf_history")
    elif any(getattr(item, "history_is_live", False) for item in sector_etfs):
        live_components.append("partial_sector_etf_history")

    if any(getattr(snapshot, "fallback_used", False) for snapshot in index_snapshots):
        fallback_components.append("index_data")
    if any(getattr(item, "fallback_used", False) for item in sector_etfs):
        fallback_components.append("sector_etf_data")

    breadth_mode = getattr(breadth, "overall_mode", None)
    if breadth_mode == "live":
        live_components.append("breadth")
    elif breadth_mode == "mixed":
        fallback_components.append("breadth")
    else:
        mock_components.append("breadth")

    leadership_mode = getattr(leadership, "overall_mode", None)
    if leadership_mode == "live":
        live_components.append("leadership")
    elif leadership_mode == "mixed":
        fallback_components.append("leadership")
    else:
        mock_components.append("leadership")

    if live_components and not fallback_components and not mock_components:
        overall_mode = "live"
    elif live_components or fallback_components:
        overall_mode = "mixed"
    else:
        overall_mode = "mock"

    return {
        "live_components": live_components,
        "fallback_components": fallback_components,
        "mock_components": mock_components,
        "overall_mode": overall_mode,
        "breadth_universe": getattr(breadth, "universe", "core"),
        "breadth_coverage_percent": getattr(breadth, "coverage_percent", None),
        "leadership_coverage_percent": getattr(leadership, "coverage_percent", None),
    }


def clamp_score(value: float | int) -> int:
    return max(0, min(100, round(value)))
