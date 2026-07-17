from typing import Any

from app.models.market import VolumeAnalysis, VolumeAnalysisResponse
from app.services.candle_data import build_history_metadata, candles_to_dicts, get_symbol_history
from app.services.pattern_detection import WATCHLIST_SYMBOLS


def calculate_average_volume(candles: list[dict[str, Any]], period: int = 20) -> int | None:
    if len(candles) < period:
        return None

    recent_volumes = [candle["volume"] for candle in candles[-period:]]
    return round(sum(recent_volumes) / len(recent_volumes))


def _calculate_previous_average_volume(
    candles: list[dict[str, Any]],
    period: int = 20,
) -> int | None:
    if len(candles) <= period:
        return calculate_average_volume(candles, period)

    return calculate_average_volume(candles[-(period + 1) : -1], period)


def calculate_relative_volume(current_volume: int, average_volume: int | None) -> float | None:
    if not average_volume:
        return None

    return round(current_volume / average_volume, 2)


def detect_volume_surge(relative_volume: float | None) -> bool:
    return relative_volume is not None and relative_volume >= 1.5


def detect_volume_dry_up(relative_volume: float | None) -> bool:
    return relative_volume is not None and relative_volume <= 0.60


def detect_breakout_volume(candles: list[dict[str, Any]], relative_volume: float | None) -> bool:
    if len(candles) < 21 or relative_volume is None:
        return False

    current_candle = candles[-1]
    previous_20_day_high = max(candle["high"] for candle in candles[-21:-1])

    return current_candle["close"] > previous_20_day_high and relative_volume >= 1.5


def detect_distribution_volume(candles: list[dict[str, Any]]) -> bool:
    if len(candles) < 2:
        return False

    current_candle = candles[-1]
    previous_candle = candles[-2]

    return (
        current_candle["close"] < previous_candle["close"]
        and current_candle["volume"] > previous_candle["volume"]
    )


def detect_accumulation_volume(candles: list[dict[str, Any]]) -> bool:
    if len(candles) < 2:
        return False

    current_candle = candles[-1]
    previous_candle = candles[-2]

    return (
        current_candle["close"] > previous_candle["close"]
        and current_candle["volume"] > previous_candle["volume"]
    )


def detect_climax_run(candles: list[dict[str, Any]]) -> bool:
    if len(candles) < 25:
        return False

    recent_candles = candles[-5:]
    start_price = recent_candles[0]["close"]
    end_price = recent_candles[-1]["close"]

    if start_price <= 0:
        return False

    price_gain_percent = (end_price - start_price) / start_price * 100
    relative_volumes: list[float] = []

    for index in range(len(candles) - 5, len(candles)):
        average_volume = calculate_average_volume(candles[max(0, index - 20) : index], 20)
        relative_volume = calculate_relative_volume(candles[index]["volume"], average_volume)

        if relative_volume is not None:
            relative_volumes.append(relative_volume)

    average_relative_volume = (
        sum(relative_volumes) / len(relative_volumes) if relative_volumes else 0
    )

    return price_gain_percent > 10 and average_relative_volume > 2.0


def _calculate_volume_quality_score(
    relative_volume: float | None,
    breakout_volume: bool,
    accumulation_volume: bool,
    distribution_volume: bool,
    dry_up: bool,
    climax_run: bool,
) -> int:
    score = 55

    if relative_volume is not None:
        if relative_volume >= 2.0:
            score += 25
        elif relative_volume >= 1.5:
            score += 18
        elif relative_volume >= 1.0:
            score += 8
        elif relative_volume <= 0.6:
            score -= 10

    if breakout_volume:
        score += 15
    if accumulation_volume:
        score += 10
    if distribution_volume:
        score -= 18
    if dry_up:
        score -= 8
    if climax_run:
        score -= 15

    return max(0, min(100, round(score)))


def _classify_volume_quality(score: int) -> str:
    if score >= 90:
        return "Excellent"
    if score >= 75:
        return "Strong"
    if score >= 60:
        return "Average"
    if score >= 40:
        return "Weak"
    return "Poor"


def _classify_volume_status(relative_volume: float | None) -> str:
    if relative_volume is None:
        return "Unavailable"
    if relative_volume >= 1.5:
        return "High Volume"
    if relative_volume <= 0.6:
        return "Volume Dry-Up"
    return "Normal Volume"


def _build_volume_summary(
    breakout_volume: bool,
    accumulation_volume: bool,
    distribution_volume: bool,
    dry_up: bool,
    climax_run: bool,
    quality: str,
) -> str:
    if breakout_volume and quality in {"Excellent", "Strong"}:
        return "Breakout is supported by strong institutional-quality volume."
    if accumulation_volume:
        return "Price is advancing on higher volume, suggesting constructive demand."
    if distribution_volume:
        return "Price declined on higher volume, flagging possible institutional selling."
    if dry_up:
        return "Volume is drying up, which can be constructive during a controlled consolidation."
    if climax_run:
        return "Recent gains and elevated volume suggest possible climax-run risk."
    return "Volume action is neutral and needs stronger confirmation."


def analyze_volume(symbol: str) -> VolumeAnalysis:
    normalized_symbol = symbol.upper()
    history, validation = get_symbol_history(normalized_symbol, days=240, minimum_candles=40)
    metadata = build_history_metadata(history, validation)
    candles = candles_to_dicts(history.candles)

    if not candles:
        return VolumeAnalysis(
            symbol=normalized_symbol,
            average_volume_20=None,
            relative_volume=None,
            status="Unavailable",
            signals=[],
            volume_quality="Poor",
            volume_quality_score=0,
            distribution_volume=False,
            accumulation_volume=False,
            dry_up=False,
            climax_run=False,
            breakout_volume=False,
            summary=f"No volume analysis is available for {normalized_symbol}.",
            data_source=metadata["data_source"],
            analysis_is_live=False,
            fallback_used=metadata["fallback_used"],
            as_of=metadata["as_of"],
            history_quality_score=metadata["history_quality_score"],
        )

    current_volume = candles[-1]["volume"]
    average_volume_20 = _calculate_previous_average_volume(candles, 20)
    relative_volume = calculate_relative_volume(current_volume, average_volume_20)
    breakout_volume = detect_breakout_volume(candles, relative_volume)
    distribution_volume = detect_distribution_volume(candles)
    accumulation_volume = detect_accumulation_volume(candles)
    dry_up = detect_volume_dry_up(relative_volume)
    climax_run = detect_climax_run(candles)
    volume_surge = detect_volume_surge(relative_volume)
    signals: list[str] = []

    if volume_surge:
        signals.append("Volume Surge")
    if breakout_volume:
        signals.append("Breakout Volume")
    if accumulation_volume:
        signals.append("Accumulation Volume")
    if distribution_volume:
        signals.append("Distribution Volume")
    if dry_up:
        signals.append("Volume Dry-Up")
    if climax_run:
        signals.append("Climax Run")

    quality_score = _calculate_volume_quality_score(
        relative_volume,
        breakout_volume,
        accumulation_volume,
        distribution_volume,
        dry_up,
        climax_run,
    )
    quality = _classify_volume_quality(quality_score)

    return VolumeAnalysis(
        symbol=normalized_symbol,
        average_volume_20=average_volume_20,
        relative_volume=relative_volume,
        status=_classify_volume_status(relative_volume),
        signals=signals,
        volume_quality=quality,
        volume_quality_score=quality_score,
        distribution_volume=distribution_volume,
        accumulation_volume=accumulation_volume,
        dry_up=dry_up,
        climax_run=climax_run,
        breakout_volume=breakout_volume,
        summary=_build_volume_summary(
            breakout_volume,
            accumulation_volume,
            distribution_volume,
            dry_up,
            climax_run,
            quality,
        ),
        data_source=metadata["data_source"],
        analysis_is_live=metadata["analysis_is_live"],
        fallback_used=metadata["fallback_used"],
        as_of=metadata["as_of"],
        history_quality_score=metadata["history_quality_score"],
    )


def build_volume_analysis() -> VolumeAnalysisResponse:
    items = [analyze_volume(symbol) for symbol in WATCHLIST_SYMBOLS]
    strongest = max(
        items,
        key=lambda item: (
            item.relative_volume if item.relative_volume is not None else 0,
            item.volume_quality_score,
        ),
    )

    return VolumeAnalysisResponse(
        items=items,
        summary=f"{strongest.symbol} currently shows the strongest institutional volume.",
    )
