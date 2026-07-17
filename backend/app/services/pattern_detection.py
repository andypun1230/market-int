from datetime import date, timedelta
from typing import Any

from app.models.market import (
    Candle,
    DetectedPattern,
    PatternKeyLevels,
    PatternMarker,
    PatternResponse,
    VolumeConfirmation,
)

WATCHLIST_SYMBOLS = ["MU", "NVDA", "ARM", "SNDK"]
START_DATE = date(2026, 5, 1)


def make_candle(
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


def build_candles_from_closes(
    closes: list[float],
    base_volume: int,
    overrides: dict[int, dict[str, Any]] | None = None,
    default_wick: float = 0.75,
) -> list[dict[str, Any]]:
    overrides = overrides or {}
    candles: list[dict[str, Any]] = []

    for index, close in enumerate(closes):
        previous_close = closes[index - 1] if index > 0 else close - 0.3
        open_price = previous_close - 0.25 if close >= previous_close else previous_close + 0.25
        high = max(open_price, close) + default_wick
        low = min(open_price, close) - default_wick
        volume = base_volume + (index % 5) * 110000

        values = {
            "open_price": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        }
        values.update(overrides.get(index, {}))

        candles.append(
            make_candle(
                START_DATE + timedelta(days=index),
                values["open_price"],
                values["high"],
                values["low"],
                values["close"],
                values["volume"],
            )
        )

    return candles


def generate_double_bottom_candles() -> list[dict[str, Any]]:
    closes: list[float] = []

    for index in range(60):
        if index <= 12:
            close = 132.0 + index * 0.34
        elif index <= 30:
            close = 136.1 - (index - 12) * 0.42
        elif index <= 38:
            close = 128.9 + (index - 30) * 1.58
        elif index <= 46:
            close = 141.3 - (index - 38) * 1.47
        else:
            close = 129.5 + (index - 46) * 1.02

        closes.append(round(close, 2))

    overrides = {
        30: {
            "open_price": 129.8,
            "high": 131.0,
            "low": 128.0,
            "close": 129.2,
            "volume": 16800000,
        },
        38: {
            "open_price": 139.6,
            "high": 142.25,
            "low": 138.9,
            "close": 141.55,
            "volume": 18400000,
        },
        46: {
            "open_price": 130.7,
            "high": 131.5,
            "low": 129.0,
            "close": 129.7,
            "volume": 16200000,
        },
        58: {
            "open_price": 140.5,
            "high": 142.4,
            "low": 139.8,
            "close": 141.9,
            "volume": 19600000,
        },
        59: {
            "open_price": 141.6,
            "high": 143.25,
            "low": 140.9,
            "close": 142.65,
            "volume": 21800000,
        },
    }

    return build_candles_from_closes(closes, 11800000, overrides)


def generate_bull_flag_candles() -> list[dict[str, Any]]:
    closes: list[float] = []

    for index in range(60):
        if index <= 20:
            close = 144.0 + index * 0.23
        elif index <= 35:
            close = 149.0 + (index - 20) * 0.92
        elif index <= 50:
            close = 162.0 - (index - 35) * 0.28
        else:
            close = 157.8 + (index - 50) * 0.62

        closes.append(round(close, 2))

    overrides = {
        35: {
            "open_price": 159.7,
            "high": 163.2,
            "low": 159.1,
            "close": 162.8,
            "volume": 62000000,
        },
        36: {
            "open_price": 162.4,
            "high": 164.0,
            "low": 160.9,
            "close": 161.7,
            "volume": 50500000,
        },
        47: {
            "open_price": 159.1,
            "high": 159.8,
            "low": 156.0,
            "close": 157.9,
            "volume": 38800000,
        },
        58: {
            "open_price": 162.1,
            "high": 163.6,
            "low": 161.4,
            "close": 163.15,
            "volume": 57000000,
        },
        59: {
            "open_price": 162.8,
            "high": 164.1,
            "low": 162.0,
            "close": 163.55,
            "volume": 64000000,
        },
    }

    return build_candles_from_closes(closes, 42000000, overrides, default_wick=0.95)


def generate_tight_consolidation_candles() -> list[dict[str, Any]]:
    closes: list[float] = []

    for index in range(60):
        if index <= 32:
            close = 150.0 + index * 0.43
        else:
            range_center = 164.15 + min(index - 32, 18) * 0.03
            oscillation = ((index - 32) % 4 - 1.5) * max(0.46 - (index - 32) * 0.01, 0.18)
            close = range_center + oscillation

        closes.append(round(close, 2))

    overrides = {
        40: {
            "open_price": 162.95,
            "high": 164.05,
            "low": 162.0,
            "close": 162.75,
            "volume": 7600000,
        },
        52: {
            "open_price": 164.95,
            "high": 166.0,
            "low": 164.45,
            "close": 165.55,
            "volume": 8200000,
        },
        56: {
            "open_price": 164.85,
            "high": 165.8,
            "low": 164.35,
            "close": 165.35,
            "volume": 7200000,
        },
        59: {
            "open_price": 165.1,
            "high": 166.15,
            "low": 164.75,
            "close": 165.85,
            "volume": 9800000,
        },
    }

    return build_candles_from_closes(closes, 8200000, overrides, default_wick=0.55)


def generate_bullish_engulfing_candles() -> list[dict[str, Any]]:
    closes: list[float] = []

    for index in range(60):
        if index <= 34:
            close = 58.0 + index * 0.31
        elif index <= 51:
            close = 68.4 - (index - 34) * 0.3
        elif index == 52:
            close = 62.8
        elif index == 53:
            close = 65.2
        else:
            close = 65.2 + (index - 53) * 0.68

        closes.append(round(close, 2))

    overrides = {
        52: {
            "open_price": 64.25,
            "high": 64.65,
            "low": 62.45,
            "close": 62.8,
            "volume": 7800000,
        },
        53: {
            "open_price": 62.35,
            "high": 65.9,
            "low": 62.0,
            "close": 65.25,
            "volume": 14600000,
        },
        56: {
            "open_price": 66.1,
            "high": 68.25,
            "low": 65.7,
            "close": 67.9,
            "volume": 11800000,
        },
        59: {
            "open_price": 69.0,
            "high": 70.4,
            "low": 68.45,
            "close": 69.75,
            "volume": 13200000,
        },
    }

    return build_candles_from_closes(closes, 6200000, overrides, default_wick=0.7)


def get_mock_candles(symbol: str) -> list[dict[str, Any]]:
    normalized_symbol = symbol.upper()
    generators = {
        "MU": generate_double_bottom_candles,
        "NVDA": generate_bull_flag_candles,
        "ARM": generate_tight_consolidation_candles,
        "SNDK": generate_bullish_engulfing_candles,
    }
    generator = generators.get(normalized_symbol)

    if not generator:
        return []

    return generator()


def is_bullish_engulfing(previous_candle: dict[str, Any], current_candle: dict[str, Any]) -> bool:
    previous_is_bearish = previous_candle["close"] < previous_candle["open"]
    current_is_bullish = current_candle["close"] > current_candle["open"]
    body_engulfs = (
        current_candle["open"] <= previous_candle["close"]
        and current_candle["close"] >= previous_candle["open"]
    )

    return previous_is_bearish and current_is_bullish and body_engulfs


def detect_double_bottom(candles: list[dict[str, Any]]) -> bool:
    if len(candles) < 52:
        return False

    first_low = min(candles[24:36], key=lambda candle: candle["low"])
    second_low = min(candles[40:52], key=lambda candle: candle["low"])
    low_distance = abs(first_low["low"] - second_low["low"])
    neckline = max(candle["high"] for candle in candles[34:44])

    return low_distance <= 1.8 and neckline > first_low["low"] * 1.08


def detect_bull_flag(candles: list[dict[str, Any]]) -> bool:
    if len(candles) < 51:
        return False

    prior_advance = candles[35]["close"] > candles[20]["close"] * 1.07
    flag_pullback = candles[47]["close"] < candles[36]["close"]
    controlled_pullback = candles[47]["close"] > candles[35]["close"] * 0.95

    return prior_advance and flag_pullback and controlled_pullback


def find_recent_bullish_engulfing(candles: list[dict[str, Any]]) -> int | None:
    for index in range(max(1, len(candles) - 12), len(candles)):
        if is_bullish_engulfing(candles[index - 1], candles[index]):
            return index

    return None


def build_pattern(
    symbol: str,
    pattern_id: str,
    name: str,
    pattern_type: str,
    direction: str,
    status: str,
    confidence: int,
    description: str,
    key_levels: PatternKeyLevels,
    markers: list[PatternMarker],
) -> DetectedPattern:
    candles = [Candle(**candle) for candle in get_mock_candles(symbol)]
    from app.services.volume_analysis import analyze_volume

    volume_analysis = analyze_volume(symbol)

    return DetectedPattern(
        id=pattern_id,
        symbol=symbol,
        name=name,
        type=pattern_type,
        direction=direction,
        status=status,
        confidence=confidence,
        timeframe="Daily",
        description=description,
        key_levels=key_levels,
        chart_data=candles,
        markers=markers,
        volume_confirmation=VolumeConfirmation(
            volume_quality=volume_analysis.volume_quality,
            relative_volume=volume_analysis.relative_volume,
            signals=volume_analysis.signals,
            summary=volume_analysis.summary,
        ),
    )


def detect_patterns(symbol: str) -> PatternResponse:
    normalized_symbol = symbol.upper()
    candles = get_mock_candles(normalized_symbol)
    patterns: list[DetectedPattern] = []

    if not candles:
        return PatternResponse(symbol=normalized_symbol, patterns=patterns)

    if normalized_symbol == "MU" and detect_double_bottom(candles):
        patterns.append(
            build_pattern(
                symbol="MU",
                pattern_id="mu-double-bottom-001",
                name="Double Bottom",
                pattern_type="chart_setup",
                direction="bullish",
                status="forming",
                confidence=76,
                description="Price carved a clear W-shaped base, reclaimed the neckline, and is testing breakout territory.",
                key_levels=PatternKeyLevels(
                    support=128.0,
                    neckline=142.0,
                    breakout=142.0,
                    stop_reference=126.0,
                ),
                markers=[
                    PatternMarker(date=candles[30]["date"], label="Low 1", price=128.0),
                    PatternMarker(date=candles[46]["date"], label="Low 2", price=129.0),
                    PatternMarker(date=candles[38]["date"], label="Neckline", price=142.0),
                ],
            )
        )
    elif normalized_symbol == "NVDA" and detect_bull_flag(candles):
        patterns.append(
            build_pattern(
                symbol="NVDA",
                pattern_id="nvda-bull-flag-001",
                name="Bull Flag",
                pattern_type="chart_setup",
                direction="bullish",
                status="forming",
                confidence=80,
                description="A sharp flagpole advance is followed by a controlled, tightening flag near the breakout line.",
                key_levels=PatternKeyLevels(
                    support=156.0,
                    neckline=None,
                    breakout=163.5,
                    stop_reference=154.0,
                ),
                markers=[
                    PatternMarker(date=candles[35]["date"], label="Flagpole", price=163.2),
                    PatternMarker(date=candles[36]["date"], label="Flag High", price=164.0),
                    PatternMarker(date=candles[58]["date"], label="Breakout Watch", price=163.5),
                ],
            )
        )
    elif normalized_symbol == "ARM":
        patterns.append(
            build_pattern(
                symbol="ARM",
                pattern_id="arm-tight-consolidation-001",
                name="Tight Consolidation",
                pattern_type="chart_setup",
                direction="bullish",
                status="forming",
                confidence=70,
                description="Prior uptrend has paused into a tight range near highs as volatility contracts.",
                key_levels=PatternKeyLevels(
                    support=162.0,
                    neckline=None,
                    breakout=166.0,
                    stop_reference=160.5,
                ),
                markers=[
                    PatternMarker(date=candles[40]["date"], label="Range Low", price=162.0),
                    PatternMarker(date=candles[52]["date"], label="Range High", price=166.0),
                    PatternMarker(date=candles[56]["date"], label="Tight Area", price=165.35),
                ],
            )
        )
    else:
        engulfing_index = find_recent_bullish_engulfing(candles)

        if normalized_symbol == "SNDK" and engulfing_index is not None:
            patterns.append(
                build_pattern(
                    symbol="SNDK",
                    pattern_id="sndk-bullish-engulfing-001",
                    name="Bullish Engulfing",
                    pattern_type="candlestick_signal",
                    direction="bullish",
                    status="triggered",
                    confidence=77,
                    description="A clear bullish engulfing candle reversed a pullback and drew follow-through volume.",
                    key_levels=PatternKeyLevels(
                        support=62.0,
                        neckline=None,
                        breakout=70.0,
                        stop_reference=61.5,
                    ),
                    markers=[
                        PatternMarker(
                            date=candles[engulfing_index - 1]["date"],
                            label="Bearish Candle",
                            price=candles[engulfing_index - 1]["close"],
                        ),
                        PatternMarker(
                            date=candles[engulfing_index]["date"],
                            label="Bullish Engulfing",
                            price=candles[engulfing_index]["close"],
                        ),
                        PatternMarker(date=candles[56]["date"], label="Follow Through", price=67.9),
                    ],
                )
            )

    return PatternResponse(symbol=normalized_symbol, patterns=patterns)


def detect_all_patterns() -> PatternResponse:
    patterns: list[DetectedPattern] = []

    for symbol in WATCHLIST_SYMBOLS:
        patterns.extend(detect_patterns(symbol).patterns)

    return PatternResponse(symbol="ALL", patterns=patterns)
