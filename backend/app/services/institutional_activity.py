from datetime import date, timedelta
from typing import Any

from app.models.market import (
    FollowThroughDay,
    IndexInstitutionalActivity,
    InstitutionalBias,
    InstitutionalDay,
    InstitutionalActivityResponse,
)

INDEX_SYMBOLS = ["SPY", "QQQ", "IWM", "DJI"]
START_DATE = date(2026, 5, 25)

INDEX_CONFIG = {
    "SPY": {"base": 604.0, "volume": 58000000},
    "QQQ": {"base": 532.0, "volume": 42000000},
    "IWM": {"base": 221.0, "volume": 29000000},
    "DJI": {"base": 42750.0, "volume": 345000000},
}

PERCENT_CHANGES = [
    0.22,
    0.16,
    -0.08,
    0.34,
    0.19,
    -0.36,
    0.31,
    0.08,
    -0.29,
    0.24,
    0.06,
    0.27,
    -0.14,
    0.36,
    -0.24,
    0.18,
    0.05,
    0.33,
    -0.21,
    0.26,
    0.12,
    -0.18,
    0.22,
    -0.32,
    -0.28,
    -0.34,
    -0.21,
    -0.18,
    -0.12,
    -0.09,
    0.42,
    0.28,
    -0.12,
    -0.62,
    0.25,
    0.18,
    -0.04,
    1.28,
    0.46,
    0.21,
    0.08,
    0.27,
    -0.11,
]

VOLUME_MULTIPLIERS = [
    1.00,
    0.97,
    1.12,
    1.18,
    0.96,
    1.28,
    1.33,
    1.42,
    1.45,
    1.09,
    1.24,
    1.31,
    0.94,
    1.22,
    1.30,
    0.98,
    1.18,
    1.24,
    1.34,
    1.18,
    0.97,
    1.23,
    1.20,
    1.38,
    1.42,
    1.45,
    1.36,
    1.16,
    1.10,
    1.21,
    1.18,
    1.12,
    1.05,
    0.98,
    1.44,
    1.35,
    1.02,
    1.26,
    1.29,
    1.08,
    1.16,
    1.22,
    1.06,
    1.11,
]


def make_index_candle(
    candle_date: date,
    open_price: float,
    high: float,
    low: float,
    close: float,
    volume: int,
) -> dict[str, Any]:
    return {
        "date": candle_date.isoformat(),
        "open": round(open_price, 2),
        "high": round(high, 2),
        "low": round(low, 2),
        "close": round(close, 2),
        "volume": volume,
    }


def get_mock_index_candles(symbol: str) -> list[dict[str, Any]]:
    normalized_symbol = symbol.upper()
    config = INDEX_CONFIG[normalized_symbol]
    candles: list[dict[str, Any]] = []
    close = config["base"]

    candles.append(
        make_index_candle(
            START_DATE,
            open_price=close - 0.8,
            high=close + 1.4,
            low=close - 1.8,
            close=close,
            volume=int(config["volume"] * VOLUME_MULTIPLIERS[0]),
        )
    )

    for index, percent_change in enumerate(PERCENT_CHANGES, start=1):
        previous_close = close
        close = previous_close * (1 + percent_change / 100)
        gap = previous_close * 0.0012
        open_price = previous_close - gap if percent_change >= 0 else previous_close + gap
        body_high = max(open_price, close)
        body_low = min(open_price, close)
        wick = max(previous_close * 0.0016, 0.45)
        high = body_high + wick
        low = body_low - wick

        if -0.1 <= percent_change <= 0.3 and index in {8, 11, 17, 30, 41}:
            high = body_high + wick * 2.2
            close = low + (high - low) * 0.42

        candles.append(
            make_index_candle(
                START_DATE + timedelta(days=index),
                open_price=open_price,
                high=high,
                low=low,
                close=close,
                volume=int(config["volume"] * VOLUME_MULTIPLIERS[index]),
            )
        )

    return candles


def calculate_change_percent(current: dict[str, Any], previous: dict[str, Any]) -> float:
    return round(((current["close"] - previous["close"]) / previous["close"]) * 100, 2)


def is_distribution_day(current: dict[str, Any], previous: dict[str, Any]) -> bool:
    change_percent = calculate_change_percent(current, previous)
    return (
        current["close"] < previous["close"]
        and change_percent <= -0.2
        and current["volume"] > previous["volume"]
    )


def is_accumulation_day(current: dict[str, Any], previous: dict[str, Any]) -> bool:
    change_percent = calculate_change_percent(current, previous)
    return (
        current["close"] > previous["close"]
        and change_percent >= 0.2
        and current["volume"] > previous["volume"]
    )


def is_stall_day(current: dict[str, Any], previous: dict[str, Any]) -> bool:
    change_percent = calculate_change_percent(current, previous)
    daily_range = current["high"] - current["low"]
    lower_half_close = daily_range > 0 and current["close"] <= current["low"] + daily_range / 2

    return (
        -0.1 <= change_percent <= 0.3
        and current["volume"] > previous["volume"]
        and lower_half_close
    )


def is_churning_day(current: dict[str, Any], previous: dict[str, Any]) -> bool:
    change_percent = calculate_change_percent(current, previous)
    return abs(change_percent) <= 0.2 and current["volume"] > previous["volume"] * 1.1


def build_institutional_day(
    current: dict[str, Any],
    previous: dict[str, Any],
    reason: str,
) -> InstitutionalDay:
    return InstitutionalDay(
        date=current["date"],
        close=current["close"],
        volume=current["volume"],
        change_percent=calculate_change_percent(current, previous),
        reason=reason,
    )


def detect_follow_through_day(
    candles: list[dict[str, Any]],
    symbol: str = "SPY",
) -> FollowThroughDay:
    if len(candles) < 10:
        return FollowThroughDay(triggered=False)

    recent_window_start = len(candles) - 10
    recent_low_index = min(
        range(recent_window_start, len(candles)),
        key=lambda index: candles[index]["close"],
    )

    for index in range(recent_low_index + 4, len(candles)):
        current = candles[index]
        previous = candles[index - 1]
        gain_percent = calculate_change_percent(current, previous)

        if gain_percent >= 1.0 and current["volume"] > previous["volume"]:
            return FollowThroughDay(
                triggered=True,
                date=current["date"],
                index=symbol.upper(),
                gain_percent=gain_percent,
            )

    return FollowThroughDay(triggered=False)


def analyze_index_activity(symbol: str) -> IndexInstitutionalActivity:
    normalized_symbol = symbol.upper()
    candles = get_mock_index_candles(normalized_symbol)
    distribution_days: list[InstitutionalDay] = []
    accumulation_days: list[InstitutionalDay] = []
    stall_days: list[InstitutionalDay] = []
    churning_days: list[InstitutionalDay] = []

    for index in range(1, len(candles)):
        current = candles[index]
        previous = candles[index - 1]

        if is_distribution_day(current, previous):
            distribution_days.append(
                build_institutional_day(
                    current,
                    previous,
                    "Index declined more than 0.2% on higher volume.",
                )
            )

        if is_accumulation_day(current, previous):
            accumulation_days.append(
                build_institutional_day(
                    current,
                    previous,
                    "Index gained at least 0.2% on higher volume.",
                )
            )

        if is_stall_day(current, previous):
            stall_days.append(
                build_institutional_day(
                    current,
                    previous,
                    "Index closed flat-to-slightly-positive on higher volume in the lower half of the range.",
                )
            )

        if is_churning_day(current, previous):
            churning_days.append(
                build_institutional_day(
                    current,
                    previous,
                    "Index changed less than 0.2% while volume expanded more than 10%.",
                )
            )

    return IndexInstitutionalActivity(
        symbol=normalized_symbol,
        distribution_days=distribution_days,
        accumulation_days=accumulation_days,
        stall_days=stall_days,
        churning_days=churning_days,
        follow_through_day=detect_follow_through_day(candles, normalized_symbol),
    )


def calculate_institutional_bias() -> InstitutionalBias:
    primary_indexes = [analyze_index_activity("SPY"), analyze_index_activity("QQQ")]
    distribution_count = sum(len(index.distribution_days) for index in primary_indexes)
    accumulation_count = sum(len(index.accumulation_days) for index in primary_indexes)
    stall_count = sum(len(index.stall_days) for index in primary_indexes)
    churning_count = sum(len(index.churning_days) for index in primary_indexes)
    follow_through_day = next(
        (
            index.follow_through_day
            for index in primary_indexes
            if index.follow_through_day.triggered
        ),
        FollowThroughDay(triggered=False),
    )

    if distribution_count >= 4 and not follow_through_day.triggered:
        bias = "Bearish"
        summary = "Distribution is elevated and no follow-through day has been detected."
    elif accumulation_count > distribution_count and follow_through_day.triggered:
        bias = "Bullish"
        summary = "Accumulation is outpacing distribution and a follow-through day was detected."
    elif distribution_count >= 3 or stall_count + churning_count >= 3:
        bias = "Cautious"
        summary = "Institutional activity is mixed, with distribution, stalling, or churning requiring caution."
    else:
        bias = "Neutral"
        summary = "Institutional buying and selling signals are balanced."

    return InstitutionalBias(
        bias=bias,
        summary=summary,
        distribution_count=distribution_count,
        accumulation_count=accumulation_count,
        stall_count=stall_count,
        churning_count=churning_count,
        follow_through_day=follow_through_day,
    )


def build_institutional_activity() -> InstitutionalActivityResponse:
    return InstitutionalActivityResponse(
        bias=calculate_institutional_bias(),
        indexes=[analyze_index_activity(symbol) for symbol in INDEX_SYMBOLS],
    )
