from app.models.market import StockRatingComponents, StockRatingItem, StockRatingResponse
from app.services.institutional_activity import calculate_institutional_bias
from app.services.industry_groups import build_industry_groups
from app.services.multi_timeframe import analyze_multi_timeframe
from app.services.pattern_detection import detect_patterns
from app.services.regime import build_market_regime
from app.services.relative_strength import SYMBOL_SECTOR, WATCHLIST_SYMBOLS, calculate_rs_score
from app.services.risk import calculate_risk_plan
from app.services.sectors import calculate_sector_rotation
from app.services.support_resistance import calculate_support_resistance
from app.services.trendline import analyze_trendline
from app.services.volume_analysis import analyze_volume
from app.services.service_cache import get_or_compute, get_service_ttl


def get_market_alignment_score(status: str) -> int:
    return {
        "Confirmed Uptrend": 90,
        "Uptrend Under Pressure": 70,
        "Choppy / Sideways": 55,
        "Correction": 30,
    }.get(status, 50)


def get_institutional_support_score(bias: str) -> int:
    return {
        "Bullish": 90,
        "Neutral": 60,
        "Cautious": 50,
        "Bearish": 25,
    }.get(bias, 50)


def get_rating(overall_score: int) -> str:
    if overall_score >= 95:
        return "A+"
    if overall_score >= 90:
        return "A"
    if overall_score >= 80:
        return "B"
    if overall_score >= 70:
        return "C"
    if overall_score >= 60:
        return "D"
    return "F"


def get_status(overall_score: int) -> str:
    if overall_score >= 90:
        return "High Quality Leader"
    if overall_score >= 80:
        return "Strong Candidate"
    if overall_score >= 70:
        return "Watchlist Candidate"
    if overall_score >= 60:
        return "Weak / Needs Confirmation"
    return "Avoid / Poor Setup"


def get_risk_level(risk_control_score: int) -> str:
    if risk_control_score >= 80:
        return "Low"
    if risk_control_score >= 65:
        return "Moderate"
    if risk_control_score >= 50:
        return "Elevated"
    return "High"


def calculate_pattern_quality(symbol: str) -> int:
    patterns = detect_patterns(symbol).patterns

    if not patterns:
        base_quality = 50
    else:
        base_quality = max(pattern.confidence for pattern in patterns)

    volume_analysis = analyze_volume(symbol)
    volume_adjustment = 0

    if volume_analysis.breakout_volume:
        volume_adjustment += 5
    if volume_analysis.accumulation_volume:
        volume_adjustment += 3
    if volume_analysis.distribution_volume:
        volume_adjustment -= 5
    if volume_analysis.climax_run:
        volume_adjustment -= 5

    volume_adjustment = max(-10, min(10, volume_adjustment))

    return max(0, min(100, base_quality + volume_adjustment))


def calculate_sector_strength(sector: str) -> int:
    sector_rows = calculate_sector_rotation()
    matching_sector = next((row for row in sector_rows if row.name == sector), None)

    if matching_sector is not None:
        return matching_sector.relative_strength_score

    industry_groups = build_industry_groups()
    matching_group = next((row for row in industry_groups.items if row.name == sector), None)

    if matching_group is not None:
        return matching_group.relative_strength_score

    return 50


def calculate_risk_control(symbol: str) -> int:
    risk_plan = calculate_risk_plan(symbol)

    return {
        "Low": 90,
        "Moderate": 75,
        "Elevated": 55,
        "High": 35,
    }.get(risk_plan.risk_level, 50)


def calculate_overall_score(components: StockRatingComponents) -> int:
    return round(
        components.relative_strength * 0.25
        + components.pattern_quality * 0.20
        + components.sector_strength * 0.15
        + components.market_alignment * 0.15
        + components.institutional_support * 0.15
        + components.risk_control * 0.10
    )


def get_multi_timeframe_adjustment(alignment: str) -> int:
    return {
        "Strong Bullish Alignment": 5,
        "Bullish but Mixed": 2,
        "Neutral / Choppy": 0,
        "Bearish Alignment": -5,
    }.get(alignment, 0)


def build_strengths(
    symbol: str,
    components: StockRatingComponents,
    regime_status: str,
) -> list[str]:
    strengths: list[str] = []

    if components.relative_strength >= 80:
        strengths.append("Strong relative strength versus SPY and QQQ")
    if components.sector_strength >= 85:
        strengths.append("Sector leadership supports the setup")
    if components.pattern_quality >= 70:
        strengths.append("Bullish chart setup is present")
    if regime_status in {"Confirmed Uptrend", "Uptrend Under Pressure", "Choppy / Sideways"}:
        strengths.append("Market regime is supportive enough for watchlist monitoring")
    if not strengths:
        strengths.append(f"{symbol} remains on watch but needs stronger confirmation")

    return strengths


def build_warnings(
    components: StockRatingComponents,
    risk_level: str,
) -> list[str]:
    warnings: list[str] = []

    if components.risk_control < 65:
        warnings.append("Risk control is not yet ideal")
    else:
        warnings.append("Stock is near breakout level")

    if risk_level in {"Moderate", "Elevated", "High"}:
        warnings.append("Position sizing should account for volatility")

    if components.market_alignment < 70:
        warnings.append("Market regime is not a confirmed uptrend")

    return warnings


def build_explanation(symbol: str, components: StockRatingComponents, rating_status: str) -> str:
    return (
        f"{symbol} rates as {rating_status} because it combines a relative strength "
        f"score of {components.relative_strength}, pattern quality of {components.pattern_quality}, "
        f"sector strength of {components.sector_strength}, and market alignment of "
        f"{components.market_alignment}."
    )


def calculate_stock_rating(symbol: str) -> StockRatingItem:
    normalized_symbol = symbol.upper()
    relative_strength = calculate_rs_score(normalized_symbol)
    pattern_quality = calculate_pattern_quality(normalized_symbol)
    volume_analysis = analyze_volume(normalized_symbol)
    risk_plan = calculate_risk_plan(normalized_symbol)
    support_resistance = calculate_support_resistance(normalized_symbol)
    trendline = analyze_trendline(normalized_symbol)
    sector_strength = calculate_sector_strength(SYMBOL_SECTOR[normalized_symbol])
    regime = build_market_regime()
    institutional_bias = calculate_institutional_bias()
    multi_timeframe = analyze_multi_timeframe(normalized_symbol)
    components = StockRatingComponents(
        relative_strength=relative_strength.overall_rs_score,
        pattern_quality=pattern_quality,
        sector_strength=sector_strength,
        market_alignment=get_market_alignment_score(regime.status),
        institutional_support=get_institutional_support_score(institutional_bias.bias),
        risk_control=get_risk_control_score(risk_plan.risk_level),
    )
    overall_score = max(
        0,
        min(
            100,
            calculate_overall_score(components)
            + get_multi_timeframe_adjustment(multi_timeframe.alignment),
        ),
    )
    rating_status = get_status(overall_score)
    risk_level = get_risk_level(components.risk_control)

    return StockRatingItem(
        symbol=normalized_symbol,
        overall_score=overall_score,
        rating=get_rating(overall_score),
        status=rating_status,
        components=components,
        risk_level=risk_level,
        strengths=build_strengths(normalized_symbol, components, regime.status),
        warnings=build_warnings(components, risk_level),
        explanation=build_explanation(normalized_symbol, components, rating_status),
        data_quality=build_rating_data_quality(
            relative_strength,
            volume_analysis,
            risk_plan,
            support_resistance,
            trendline,
        ),
    )


def rank_stock_ratings() -> list[StockRatingItem]:
    return sorted(
        [calculate_stock_rating(symbol) for symbol in WATCHLIST_SYMBOLS],
        key=lambda item: item.overall_score,
        reverse=True,
    )


def build_stock_ratings() -> StockRatingResponse:
    return get_or_compute(
        "stock-ratings",
        get_service_ttl("SERVICE_CACHE_MARKET_CORE_TTL_SECONDS", 60),
        _build_stock_ratings_uncached,
    )


def _build_stock_ratings_uncached() -> StockRatingResponse:
    items = rank_stock_ratings()
    leaders = [item.symbol for item in items[:2]]

    return StockRatingResponse(
        items=items,
        summary=(
            f"{leaders[0]} and {leaders[1]} currently have the strongest overall "
            "scores based on relative strength, sector leadership, pattern quality, "
            "and market alignment."
        ),
    )


def get_risk_control_score(risk_level: str) -> int:
    return {
        "Low": 90,
        "Moderate": 75,
        "Elevated": 55,
        "High": 35,
    }.get(risk_level, 50)


def build_rating_data_quality(
    relative_strength,
    volume_analysis,
    risk_plan,
    support_resistance,
    trendline,
) -> dict:
    live_components: list[str] = []
    fallback_components: list[str] = []
    mock_components = ["pattern_detection", "multi_timeframe", "sector_strength"]

    component_map = {
        "relative_strength": relative_strength,
        "volume_analysis": volume_analysis,
        "support_resistance": support_resistance,
        "trendline": trendline,
    }
    for label, component in component_map.items():
        if getattr(component, "analysis_is_live", False) or (
            isinstance(component, dict) and component.get("analysis_is_live")
        ):
            live_components.append(label)
        elif getattr(component, "fallback_used", False) or (
            isinstance(component, dict) and component.get("fallback_used")
        ):
            fallback_components.append(label)
        else:
            mock_components.append(label)

    risk_quality = risk_plan.data_quality or {}
    if risk_quality.get("overall_mode") == "live":
        live_components.append("risk_plan")
    elif risk_quality.get("overall_mode") == "mixed":
        fallback_components.append("risk_plan")
    else:
        mock_components.append("risk_plan")

    if live_components and not fallback_components and not mock_components:
        overall_mode = "live"
    elif live_components or fallback_components:
        overall_mode = "mixed"
    else:
        overall_mode = "mock"

    return {
        "overall_mode": overall_mode,
        "live_components": live_components,
        "fallback_components": fallback_components,
        "mock_components": mock_components,
    }
