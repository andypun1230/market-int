from datetime import datetime, timezone
from typing import Any

from app.providers.models import HistoryData


def validate_history(history: HistoryData, minimum_candles: int = 60) -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []
    candles = history.candles

    if len(candles) < minimum_candles:
        errors.append(f"Only {len(candles)} candles returned; {minimum_candles} required.")

    timestamps = [candle.timestamp for candle in candles]
    if len(set(timestamps)) != len(timestamps):
        errors.append("Duplicate candle timestamps detected.")

    if timestamps != sorted(timestamps):
        errors.append("Candles are not strictly ascending by timestamp.")

    for candle in candles:
        if candle.close <= 0:
            errors.append(f"Invalid close price at {candle.timestamp}.")
            break
        if candle.volume < 0:
            errors.append(f"Invalid negative volume at {candle.timestamp}.")
            break
        if candle.high < max(candle.open, candle.close, candle.low):
            errors.append(f"High/low relationship is invalid at {candle.timestamp}.")
            break
        if candle.low > min(candle.open, candle.close, candle.high):
            errors.append(f"Low/high relationship is invalid at {candle.timestamp}.")
            break

    if candles:
        last_age_days = calculate_last_age_days(candles[-1].timestamp)
        if last_age_days is not None and last_age_days > 10:
            warnings.append(f"Last candle is {last_age_days} calendar days old.")

        discontinuities = count_discontinuities([candle.close for candle in candles])
        if discontinuities:
            warnings.append(f"{discontinuities} large price discontinuity warning(s) detected.")

    quality_score = 100
    quality_score -= len(errors) * 30
    quality_score -= len(warnings) * 8
    if history.fallback_used or not history.is_live:
        quality_score -= 10
    quality_score = max(0, min(100, quality_score))

    return {
        "valid": not errors,
        "warnings": warnings,
        "errors": errors,
        "quality_score": quality_score,
    }


def calculate_last_age_days(timestamp: str) -> int | None:
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return (datetime.now(timezone.utc) - parsed).days


def count_discontinuities(closes: list[float]) -> int:
    count = 0
    for index in range(1, len(closes)):
        previous = closes[index - 1]
        current = closes[index]
        if previous > 0 and abs(current - previous) / previous > 0.35:
            count += 1
    return count
