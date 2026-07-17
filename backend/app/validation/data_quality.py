from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

RAW_ERROR_MARKERS = (
    "Traceback",
    "ProviderRequestError",
    "Internal Server Error",
    "KeyError:",
    "ValueError:",
    "undefined",
    "NaN",
    "Infinity",
)


def get_path(payload: Any, path: str) -> Any:
    value = payload
    for part in path.split("."):
        if isinstance(value, dict):
            value = value.get(part)
        elif isinstance(value, list):
            try:
                value = value[int(part)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return value


def has_path(payload: Any, path: str) -> bool:
    return get_path(payload, path) is not None


def validate_required_fields(payload: Any, fields: tuple[str, ...]) -> list[str]:
    return [field for field in fields if not has_path(payload, field)]


def walk_values(value: Any):
    if isinstance(value, dict):
        for item in value.values():
            yield from walk_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk_values(item)
    else:
        yield value


def find_invalid_numbers(payload: Any) -> list[str]:
    issues: list[str] = []

    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                walk(item, f"{path}.{key}" if path else str(key))
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, f"{path}.{index}" if path else str(index))
        elif isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            issues.append(path or "<root>")

    walk(payload, "")
    return issues


def find_raw_error_text(payload: Any) -> list[str]:
    issues: list[str] = []

    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                walk(item, f"{path}.{key}" if path else str(key))
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, f"{path}.{index}" if path else str(index))
        elif isinstance(value, str):
            for marker in RAW_ERROR_MARKERS:
                if marker in value:
                    issues.append(f"{path or '<root>'}: {marker}")

    walk(payload, "")
    return issues


def finite_positive(value: Any) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value)) and float(value) > 0


def validate_quote(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not finite_positive(payload.get("price")):
        errors.append("price must be finite and positive")
    change_percent = payload.get("change_percent")
    if not isinstance(change_percent, (int, float)) or not math.isfinite(float(change_percent)):
        errors.append("change_percent must be finite")
    if not valid_timestamp(payload.get("timestamp")):
        errors.append("timestamp must be valid and not in the future")
    return errors


def validate_history(payload: dict[str, Any], *, minimum_bars: int = 1) -> list[str]:
    errors: list[str] = []
    candles = payload.get("candles")
    if not isinstance(candles, list) or len(candles) < minimum_bars:
        errors.append(f"candles length must be at least {minimum_bars}")
        return errors

    previous_timestamp: str | None = None
    seen: set[str] = set()
    for index, candle in enumerate(candles):
        if not isinstance(candle, dict):
            errors.append(f"candles.{index} must be object")
            continue
        timestamp = str(candle.get("timestamp") or "")
        if not valid_timestamp(timestamp):
            errors.append(f"candles.{index}.timestamp invalid")
        if timestamp in seen:
            errors.append(f"candles.{index}.timestamp duplicate")
        seen.add(timestamp)
        if previous_timestamp and timestamp <= previous_timestamp:
            errors.append(f"candles.{index}.timestamp not ascending")
        previous_timestamp = timestamp
        open_price = as_float(candle.get("open"))
        high = as_float(candle.get("high"))
        low = as_float(candle.get("low"))
        close = as_float(candle.get("close"))
        volume = as_float(candle.get("volume"))
        if min(open_price, high, low, close) <= 0:
            errors.append(f"candles.{index}.ohlc must be positive")
        if high < max(open_price, low, close):
            errors.append(f"candles.{index}.high must be >= open/low/close")
        if low > min(open_price, high, close):
            errors.append(f"candles.{index}.low must be <= open/high/close")
        if volume < 0:
            errors.append(f"candles.{index}.volume must be non-negative")
    return errors[:25]


def valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed <= datetime.now(timezone.utc).replace(microsecond=0)


def as_float(value: Any) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return result


def classify_status(required_failures: list[str], optional_failures: list[str] | None = None) -> str:
    if required_failures:
        return "FAIL"
    if optional_failures:
        return "PARTIAL"
    return "PASS"

