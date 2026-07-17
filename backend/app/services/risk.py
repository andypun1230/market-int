from typing import Any

from app.models.market import RiskPlan, RiskPlanResponse
from app.services.candle_data import (
    build_dependency_quality,
    build_history_metadata,
    candles_to_dicts,
    get_symbol_history,
)
from app.services.pattern_detection import WATCHLIST_SYMBOLS, detect_patterns
from app.services.support_resistance import calculate_support_resistance
from app.services.technical_indicators import calculate_atr_from_candles


def calculate_atr(candles: list[dict[str, Any]], period: int = 14) -> float | None:
    return calculate_atr_from_candles(candles, period)


def _first_pattern_levels(symbol: str) -> dict[str, float | None]:
    patterns = detect_patterns(symbol).patterns

    if not patterns:
        return {
            "breakout": None,
            "neckline": None,
            "stop_reference": None,
        }

    key_levels = patterns[0].key_levels

    return {
        "breakout": key_levels.breakout,
        "neckline": key_levels.neckline,
        "stop_reference": key_levels.stop_reference,
    }


def _classify_volatility(atr_14: float | None, current_price: float) -> str:
    if atr_14 is None or current_price <= 0:
        return "N/A"

    atr_percent = atr_14 / current_price * 100

    if atr_percent < 2:
        return "Low"
    if atr_percent <= 4:
        return "Moderate"
    return "High"


def _classify_risk(risk_percent: float) -> str:
    if risk_percent <= 4:
        return "Low"
    if risk_percent <= 8:
        return "Moderate"
    if risk_percent <= 12:
        return "Elevated"
    return "High"


def _position_size_note(risk_level: str) -> str:
    return {
        "Low": "Normal position size may be acceptable.",
        "Moderate": "Use standard or slightly reduced size.",
        "Elevated": "Use smaller size because stop distance is wide.",
        "High": "Risk is high. Consider waiting for a better entry.",
    }.get(risk_level, "Position size should reflect the available stop distance.")


def _build_summary(symbol: str, risk_level: str, risk_reward_target_1: float) -> str:
    if risk_level in {"Elevated", "High"}:
        return (
            f"{symbol} has a clear breakout level, but risk is {risk_level.lower()} "
            "because the stop is far from entry."
        )

    if risk_reward_target_1 >= 1:
        return f"{symbol} has a workable risk/reward plan with a defined entry and stop."

    return f"{symbol} has defined levels, but reward does not yet compensate well for risk."


def _round_percent(value: float) -> float:
    return round(value, 2)


def calculate_risk_plan(symbol: str) -> RiskPlan:
    normalized_symbol = symbol.upper()
    history, validation = get_symbol_history(normalized_symbol, days=240, minimum_candles=40)
    metadata = build_history_metadata(history, validation)
    candles = candles_to_dicts(history.candles)
    data_quality = build_dependency_quality(metadata, mock_components=["pattern_levels"])

    if not candles:
        return RiskPlan(
            symbol=normalized_symbol,
            current_price=0,
            entry=0,
            stop_loss=0,
            target_1=0,
            target_2=0,
            atr_14=None,
            risk_percent=0,
            reward_percent_target_1=0,
            reward_percent_target_2=0,
            risk_reward_target_1=0,
            risk_reward_target_2=0,
            volatility_level="N/A",
            risk_level="High",
            position_size_note="Risk is high. Consider waiting for a better entry.",
            summary=f"No risk plan is available for {normalized_symbol}.",
            data_quality=data_quality,
        )

    current_price = round(candles[-1]["close"], 2)
    atr_14 = calculate_atr(candles, 14)
    support_resistance = calculate_support_resistance(normalized_symbol)
    pattern_levels = _first_pattern_levels(normalized_symbol)
    entry = (
        pattern_levels["breakout"]
        or pattern_levels["neckline"]
        or support_resistance.breakout_level
        or current_price
    )
    fallback_atr = atr_14 if atr_14 is not None else current_price * 0.03
    stop_loss = (
        pattern_levels["stop_reference"]
        or support_resistance.stop_reference
        or current_price - 2 * fallback_atr
    )

    if stop_loss >= entry:
        stop_loss = current_price - 2 * fallback_atr

    risk_amount = max(entry - stop_loss, 0.01)
    target_1 = entry + risk_amount
    target_2 = entry + 2 * risk_amount
    risk_percent = _round_percent(risk_amount / entry * 100) if entry > 0 else 0
    reward_percent_target_1 = _round_percent((target_1 - entry) / entry * 100) if entry > 0 else 0
    reward_percent_target_2 = _round_percent((target_2 - entry) / entry * 100) if entry > 0 else 0
    risk_reward_target_1 = round((target_1 - entry) / risk_amount, 2)
    risk_reward_target_2 = round((target_2 - entry) / risk_amount, 2)
    risk_level = _classify_risk(risk_percent)

    return RiskPlan(
        symbol=normalized_symbol,
        current_price=current_price,
        entry=round(entry, 2),
        stop_loss=round(stop_loss, 2),
        target_1=round(target_1, 2),
        target_2=round(target_2, 2),
        atr_14=atr_14,
        risk_percent=risk_percent,
        reward_percent_target_1=reward_percent_target_1,
        reward_percent_target_2=reward_percent_target_2,
        risk_reward_target_1=risk_reward_target_1,
        risk_reward_target_2=risk_reward_target_2,
        volatility_level=_classify_volatility(atr_14, current_price),
        risk_level=risk_level,
        position_size_note=_position_size_note(risk_level),
        summary=_build_summary(normalized_symbol, risk_level, risk_reward_target_1),
        data_quality=data_quality,
    )


def calculate_all_risk_plans() -> list[RiskPlan]:
    return [calculate_risk_plan(symbol) for symbol in WATCHLIST_SYMBOLS]


def build_risk_plans() -> RiskPlanResponse:
    items = calculate_all_risk_plans()

    return RiskPlanResponse(
        items=items,
        summary=build_daily_risk_summary(items)["risk_summary"],
    )


def build_daily_risk_summary(items: list[RiskPlan] | None = None) -> dict[str, str]:
    risk_plans = items if items is not None else calculate_all_risk_plans()
    best_setup = min(
        risk_plans,
        key=lambda item: (item.risk_percent, -item.risk_reward_target_2),
    )
    highest_risk = max(risk_plans, key=lambda item: item.risk_percent)
    elevated_count = sum(1 for item in risk_plans if item.risk_level in {"Elevated", "High"})

    return {
        "best_risk_reward_setup": (
            f"{best_setup.symbol}: {best_setup.risk_reward_target_2:.2f}R to target 2, "
            f"{best_setup.risk_percent:.2f}% risk"
        ),
        "highest_risk_stock": (
            f"{highest_risk.symbol}: {highest_risk.risk_percent:.2f}% risk "
            f"({highest_risk.risk_level})"
        ),
        "risk_summary": (
            f"{elevated_count} watchlist stocks have elevated or high stop-distance risk. "
            "Prefer entries close to support or confirmed breakout levels."
        ),
    }
