from typing import Any

from app.models.market import (
    MovingAverageSupport,
    PriceZone,
    SupportResistanceResponse,
)
from app.services.candle_data import build_history_metadata, get_symbol_history, candles_to_dicts
from app.services.technical_indicators import calculate_ema


def find_recent_swing_highs(
    candles: list[dict[str, Any]],
    lookback: int = 3,
) -> list[float]:
    swing_highs: list[float] = []

    for index in range(lookback, len(candles) - lookback):
        current_high = candles[index]["high"]
        previous_highs = [candle["high"] for candle in candles[index - lookback:index]]
        next_highs = [candle["high"] for candle in candles[index + 1:index + lookback + 1]]

        if current_high > max(previous_highs) and current_high > max(next_highs):
            swing_highs.append(round(current_high, 2))

    return swing_highs


def find_recent_swing_lows(
    candles: list[dict[str, Any]],
    lookback: int = 3,
) -> list[float]:
    swing_lows: list[float] = []

    for index in range(lookback, len(candles) - lookback):
        current_low = candles[index]["low"]
        previous_lows = [candle["low"] for candle in candles[index - lookback:index]]
        next_lows = [candle["low"] for candle in candles[index + 1:index + lookback + 1]]

        if current_low < min(previous_lows) and current_low < min(next_lows):
            swing_lows.append(round(current_low, 2))

    return swing_lows


def cluster_price_levels(
    levels: list[float],
    tolerance_percent: float = 1.0,
) -> list[dict[str, Any]]:
    if not levels:
        return []

    sorted_levels = sorted(levels)
    clusters: list[list[float]] = []

    for level in sorted_levels:
        if not clusters:
            clusters.append([level])
            continue

        cluster_average = sum(clusters[-1]) / len(clusters[-1])
        distance_percent = abs(level - cluster_average) / cluster_average * 100

        if distance_percent <= tolerance_percent:
            clusters[-1].append(level)
        else:
            clusters.append([level])

    return [
        {
            "low": round(min(cluster), 2),
            "high": round(max(cluster), 2),
            "strength": len(cluster),
        }
        for cluster in clusters
    ]


def build_price_zones(
    clusters: list[dict[str, Any]],
    reason: str,
    current_price: float,
    zone_type: str,
) -> list[PriceZone]:
    zones = [
        PriceZone(
            low=cluster["low"],
            high=cluster["high"],
            strength=cluster["strength"],
            reason=reason,
        )
        for cluster in clusters
    ]

    if zone_type == "support":
        zones = [zone for zone in zones if zone.low <= current_price]
        return sorted(zones, key=lambda zone: (abs(current_price - zone.high), -zone.strength))[:3]

    zones = [zone for zone in zones if zone.high >= current_price * 0.985]
    return sorted(zones, key=lambda zone: (abs(zone.low - current_price), -zone.strength))[:3]


def calculate_breakout_level(resistance_zones: list[PriceZone], current_price: float) -> float | None:
    if resistance_zones:
        nearest_resistance = min(
            resistance_zones,
            key=lambda zone: abs(((zone.low + zone.high) / 2) - current_price),
        )
        return round(nearest_resistance.low, 2)

    return None


def calculate_stop_reference(support_zones: list[PriceZone], current_price: float) -> float | None:
    if support_zones:
        nearest_support = min(
            support_zones,
            key=lambda zone: abs(current_price - zone.high),
        )
        return round(nearest_support.low * 0.985, 2)

    return None


def calculate_support_resistance(symbol: str) -> SupportResistanceResponse:
    normalized_symbol = symbol.upper()
    history, validation = get_symbol_history(normalized_symbol, days=240, minimum_candles=40)
    metadata = build_history_metadata(history, validation)
    candles = candles_to_dicts(history.candles)

    if not candles:
        return SupportResistanceResponse(
            symbol=normalized_symbol,
            current_price=0,
            support_zones=[],
            resistance_zones=[],
            breakout_level=None,
            stop_reference=None,
            moving_average_support=MovingAverageSupport(ema_20=None, ema_50=None),
            data_source=metadata["data_source"],
            analysis_is_live=False,
            fallback_used=metadata["fallback_used"],
            as_of=metadata["as_of"],
            history_quality_score=metadata["history_quality_score"],
        )

    current_price = candles[-1]["close"]
    closes = [candle["close"] for candle in candles]
    recent_candles = candles[-30:]
    swing_highs = find_recent_swing_highs(candles)
    swing_lows = find_recent_swing_lows(candles)

    support_levels = swing_lows + [
        min(candle["low"] for candle in recent_candles),
        min(candle["close"] for candle in recent_candles),
    ]
    resistance_levels = swing_highs + [
        max(candle["high"] for candle in recent_candles),
        max(candle["close"] for candle in recent_candles),
    ]

    support_clusters = cluster_price_levels(support_levels)
    resistance_clusters = cluster_price_levels(resistance_levels)
    support_zones = build_price_zones(
        support_clusters,
        reason="Repeated swing lows",
        current_price=current_price,
        zone_type="support",
    )
    resistance_zones = build_price_zones(
        resistance_clusters,
        reason="Recent swing highs / neckline or breakout area",
        current_price=current_price,
        zone_type="resistance",
    )

    return SupportResistanceResponse(
        symbol=normalized_symbol,
        current_price=round(current_price, 2),
        support_zones=support_zones,
        resistance_zones=resistance_zones,
        breakout_level=calculate_breakout_level(resistance_zones, current_price),
        stop_reference=calculate_stop_reference(support_zones, current_price),
        moving_average_support=MovingAverageSupport(
            ema_20=calculate_ema(closes, 20),
            ema_50=calculate_ema(closes, 50),
        ),
        data_source=metadata["data_source"],
        analysis_is_live=metadata["analysis_is_live"],
        fallback_used=metadata["fallback_used"],
        as_of=metadata["as_of"],
        history_quality_score=metadata["history_quality_score"],
    )
