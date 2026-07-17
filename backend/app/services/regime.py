from app.models.market import (
    BreadthResponse,
    BriefResponse,
    RegimeResponse,
    RegimeInstitutionalActivityResponse,
    RiskResponse,
    TrendResponse,
    VolatilityResponse,
)
from app.services.breadth import calculate_market_breadth
from app.services.institutional_activity import calculate_institutional_bias
from app.services.market_data import get_index_snapshot

MOCK_VIX = 18.5


def build_market_brief() -> BriefResponse:
    return BriefResponse(
        regime="Confirmed Uptrend",
        drivers=["Semiconductors", "AI"],
        risks=["CPI Tomorrow"],
        top_sectors=["Semiconductors", "Software"],
        summary="Market is in a confirmed uptrend with strength in semiconductors and AI.",
    )


def get_trend_text(price: float, ema_50: float | None) -> str:
    if ema_50 is None:
        return "Below 50MA"

    return "Above 50MA" if price > ema_50 else "Below 50MA"


def get_breadth_status(percent_above_50ema: float) -> str:
    if percent_above_50ema >= 60:
        return "Healthy"
    if percent_above_50ema >= 45:
        return "Mixed"
    return "Weak"


def get_volatility_status(vix: float) -> str:
    if vix < 16:
        return "Low"
    if vix < 22:
        return "Normal"
    if vix < 28:
        return "Elevated"
    return "High"


def determine_regime_status(
    spy_above_50ema: bool,
    qqq_above_50ema: bool,
    percent_above_50ema: float,
    advance_decline_ratio: float | None,
    distribution_days: int,
    vix: float,
) -> str:
    safe_advance_decline_ratio = advance_decline_ratio if advance_decline_ratio is not None else 0

    if (
        spy_above_50ema
        and qqq_above_50ema
        and percent_above_50ema >= 60
        and safe_advance_decline_ratio >= 1.0
        and distribution_days <= 3
        and vix < 22
    ):
        return "Confirmed Uptrend"

    if (
        (spy_above_50ema or qqq_above_50ema)
        and percent_above_50ema >= 45
        and (
            4 <= distribution_days <= 5
            or 22 <= vix < 28
            or safe_advance_decline_ratio < 1.0
        )
    ):
        return "Uptrend Under Pressure"

    if (
        not spy_above_50ema
        and not qqq_above_50ema
        and percent_above_50ema < 45
        and (vix >= 28 or safe_advance_decline_ratio < 0.8)
    ):
        return "Correction"

    return "Choppy / Sideways"


def build_regime_explanation(
    status: str,
    spy_above_50ema: bool,
    qqq_above_50ema: bool,
    breadth_status: str,
    volatility_status: str,
    distribution_days: int,
) -> str:
    spy_text = "above" if spy_above_50ema else "below"
    qqq_text = "above" if qqq_above_50ema else "below"

    return (
        f"Market regime is {status} because SPY is {spy_text} its 50-day EMA, "
        f"QQQ is {qqq_text} its 50-day EMA, breadth is {breadth_status.lower()}, "
        f"VIX is {volatility_status.lower()}, and distribution days are {distribution_days}."
    )


def calculate_market_regime() -> RegimeResponse:
    market_breadth = calculate_market_breadth()
    institutional_bias = calculate_institutional_bias()
    spy_snapshot = get_index_snapshot("SPY")
    qqq_snapshot = get_index_snapshot("QQQ")
    iwm_snapshot = get_index_snapshot("IWM")
    dji_snapshot = get_index_snapshot("DJI")
    spy_trend = get_trend_text(spy_snapshot.price, spy_snapshot.ema_50)
    qqq_trend = get_trend_text(qqq_snapshot.price, qqq_snapshot.ema_50)
    iwm_trend = get_trend_text(iwm_snapshot.price, iwm_snapshot.ema_50)
    dji_trend = get_trend_text(dji_snapshot.price, dji_snapshot.ema_50)
    spy_above_50ema = spy_trend == "Above 50MA"
    qqq_above_50ema = qqq_trend == "Above 50MA"
    breadth_status = get_breadth_status(market_breadth.percent_above_50ema)
    volatility_status = get_volatility_status(MOCK_VIX)
    regime_status = determine_regime_status(
        spy_above_50ema=spy_above_50ema,
        qqq_above_50ema=qqq_above_50ema,
        percent_above_50ema=market_breadth.percent_above_50ema,
        advance_decline_ratio=market_breadth.advance_decline_ratio,
        distribution_days=institutional_bias.distribution_count,
        vix=MOCK_VIX,
    )
    follow_through_text = (
        f"Triggered on {institutional_bias.follow_through_day.date}"
        if institutional_bias.follow_through_day.triggered
        else "Not triggered"
    )

    return RegimeResponse(
        status=regime_status,
        trend=TrendResponse(
            spy=spy_trend,
            qqq=qqq_trend,
            iwm=iwm_trend,
            dji=dji_trend,
        ),
        breadth=BreadthResponse(
            status=breadth_status,
            stocks_above_20ma=round(market_breadth.percent_above_20ema),
            stocks_above_50ma=round(market_breadth.percent_above_50ema),
            stocks_above_200ma=round(market_breadth.percent_above_200ema),
            advance_decline_ratio=market_breadth.advance_decline_ratio,
        ),
        volatility=VolatilityResponse(
            vix=MOCK_VIX,
            status=volatility_status,
        ),
        institutional_activity=RegimeInstitutionalActivityResponse(
            distribution_days=institutional_bias.distribution_count,
            accumulation_days=institutional_bias.accumulation_count,
            follow_through_day=follow_through_text,
        ),
        explanation=build_regime_explanation(
            status=regime_status,
            spy_above_50ema=spy_above_50ema,
            qqq_above_50ema=qqq_above_50ema,
            breadth_status=breadth_status,
            volatility_status=volatility_status,
            distribution_days=institutional_bias.distribution_count,
        ),
    )


def build_market_regime() -> RegimeResponse:
    return calculate_market_regime()


def build_market_risk() -> RiskResponse:
    return RiskResponse(
        risk_level="Moderate",
        main_risks=[
            "AI and semiconductor stocks are becoming extended",
            "Breadth is healthy but slightly narrowing",
            "Upcoming CPI may increase volatility",
        ],
        suggested_positioning=(
            "Stay invested, but avoid chasing extended breakouts. "
            "Prefer pullbacks in leading sectors."
        ),
    )
