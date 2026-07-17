from typing import Any

from app.services.candle_data import build_history_metadata, candles_to_dicts, get_symbol_history
from app.services.pattern_detection import WATCHLIST_SYMBOLS


def find_swing_lows(candles: list[dict[str, Any]], lookback: int = 3) -> list[dict[str, Any]]:
    """Return candles whose low is below nearby lows on both sides."""
    swing_lows: list[dict[str, Any]] = []

    for index in range(lookback, len(candles) - lookback):
        candle = candles[index]
        nearby_lows = [
            candles[nearby_index]["low"]
            for nearby_index in range(index - lookback, index + lookback + 1)
            if nearby_index != index
        ]

        if candle["low"] < min(nearby_lows):
            swing_lows.append(
                {
                    "index": index,
                    "date": candle["date"],
                    "price": candle["low"],
                    "candle": candle,
                }
            )

    return swing_lows


def find_swing_highs(candles: list[dict[str, Any]], lookback: int = 3) -> list[dict[str, Any]]:
    """Return candles whose high is above nearby highs on both sides."""
    swing_highs: list[dict[str, Any]] = []

    for index in range(lookback, len(candles) - lookback):
        candle = candles[index]
        nearby_highs = [
            candles[nearby_index]["high"]
            for nearby_index in range(index - lookback, index + lookback + 1)
            if nearby_index != index
        ]

        if candle["high"] > max(nearby_highs):
            swing_highs.append(
                {
                    "index": index,
                    "date": candle["date"],
                    "price": candle["high"],
                    "candle": candle,
                }
            )

    return swing_highs


def calculate_line_from_points(point1: dict[str, Any], point2: dict[str, Any]) -> dict[str, Any]:
    x_distance = point2["index"] - point1["index"]
    slope = 0.0 if x_distance == 0 else (point2["price"] - point1["price"]) / x_distance
    intercept = point1["price"] - slope * point1["index"]

    return {
        "slope": round(slope, 4),
        "intercept": round(intercept, 4),
        "start_date": point1["date"],
        "end_date": point2["date"],
        "start_price": round(point1["price"], 2),
        "end_price": round(point2["price"], 2),
    }


def project_line_value(line: dict[str, Any], x_index: int) -> float:
    return round(line["slope"] * x_index + line["intercept"], 2)


def _empty_trendline_detail(status: str = "No clear trendline detected") -> dict[str, Any]:
    return {
        "detected": False,
        "slope": None,
        "touch_count": 0,
        "start_date": None,
        "end_date": None,
        "start_price": None,
        "end_price": None,
        "current_line_value": None,
        "distance_percent": None,
        "status": status,
    }


def _count_touches(points: list[dict[str, Any]], line: dict[str, Any], tolerance_percent: float = 2.0) -> int:
    touches = 0

    for point in points:
        projected_price = project_line_value(line, point["index"])
        if projected_price == 0:
            continue

        distance_percent = abs(point["price"] - projected_price) / projected_price * 100
        if distance_percent <= tolerance_percent:
            touches += 1

    return touches


def _build_trendline_detail(
    points: list[dict[str, Any]],
    current_price: float,
    current_index: int,
    line_type: str,
) -> dict[str, Any]:
    if len(points) < 2:
        return _empty_trendline_detail(f"No clear {line_type} trendline detected")

    first_point = points[0]
    latest_point = points[-1]
    is_rising_support = line_type == "rising support" and latest_point["price"] > first_point["price"]
    is_falling_resistance = line_type == "falling resistance" and latest_point["price"] < first_point["price"]

    if not (is_rising_support or is_falling_resistance):
        return _empty_trendline_detail(f"No clear {line_type} trendline detected")

    line = calculate_line_from_points(first_point, latest_point)
    current_line_value = project_line_value(line, current_index)
    distance_percent = None

    if current_line_value:
        distance_percent = round((current_price - current_line_value) / current_line_value * 100, 2)

    touch_count = _count_touches(points, line)

    if line_type == "rising support":
        if distance_percent is not None and distance_percent < -1:
            status = "Broken below rising support"
        elif distance_percent is not None and distance_percent <= 2:
            status = "Testing rising support"
        else:
            status = "Holding above rising support"
    else:
        if distance_percent is not None and distance_percent > 1:
            status = "Broken above falling resistance"
        elif distance_percent is not None and distance_percent >= -2:
            status = "Testing falling resistance"
        else:
            status = "Trading below falling resistance"

    return {
        "detected": True,
        "slope": line["slope"],
        "touch_count": touch_count,
        "start_date": line["start_date"],
        "end_date": line["end_date"],
        "start_price": line["start_price"],
        "end_price": line["end_price"],
        "current_line_value": current_line_value,
        "distance_percent": distance_percent,
        "status": status,
    }


def _build_break_status(
    current_price: float,
    rising_support: dict[str, Any],
    falling_resistance: dict[str, Any],
) -> dict[str, Any]:
    if rising_support["detected"] and rising_support["current_line_value"] is not None:
        if current_price < rising_support["current_line_value"] * 0.99:
            return {
                "broken": True,
                "direction": "down",
                "description": "Price has broken below rising support by more than 1%.",
            }

    if falling_resistance["detected"] and falling_resistance["current_line_value"] is not None:
        if current_price > falling_resistance["current_line_value"] * 1.01:
            return {
                "broken": True,
                "direction": "up",
                "description": "Price has broken above falling resistance by more than 1%.",
            }

    if rising_support["detected"]:
        return {
            "broken": False,
            "direction": "none",
            "description": "Price remains above rising support.",
        }

    if falling_resistance["detected"]:
        return {
            "broken": False,
            "direction": "none",
            "description": "Price remains below falling resistance.",
        }

    return {
        "broken": False,
        "direction": "none",
        "description": "No clear trendline break is detected.",
    }


def _build_summary(
    symbol: str,
    rising_support: dict[str, Any],
    falling_resistance: dict[str, Any],
    trendline_break: dict[str, Any],
) -> str:
    if trendline_break["broken"]:
        return f"{symbol} has a {trendline_break['direction']}side trendline break signal."

    if rising_support["detected"]:
        touches = rising_support["touch_count"]
        return f"{symbol} remains above its rising support trendline with {touches} confirmed touches."

    if falling_resistance["detected"]:
        touches = falling_resistance["touch_count"]
        return f"{symbol} remains below its falling resistance trendline with {touches} confirmed touches."

    return f"{symbol} does not have a clear v1 trendline setup from the current candles."


def analyze_trendline(symbol: str) -> dict[str, Any]:
    normalized_symbol = symbol.upper()
    history, validation = get_symbol_history(normalized_symbol, days=240, minimum_candles=40)
    metadata = build_history_metadata(history, validation)
    candles = candles_to_dicts(history.candles)

    if not candles:
        return {
            "symbol": normalized_symbol,
            "current_price": 0.0,
            "rising_support": _empty_trendline_detail("No candle data available"),
            "falling_resistance": _empty_trendline_detail("No candle data available"),
            "trendline_break": {
                "broken": False,
                "direction": "none",
                "description": "No candle data available.",
            },
            "summary": f"No trendline analysis is available for {normalized_symbol}.",
            "data_source": metadata["data_source"],
            "analysis_is_live": False,
            "fallback_used": metadata["fallback_used"],
            "as_of": metadata["as_of"],
            "history_quality_score": metadata["history_quality_score"],
        }

    current_index = len(candles) - 1
    current_price = round(candles[-1]["close"], 2)
    swing_lows = find_swing_lows(candles)
    swing_highs = find_swing_highs(candles)

    rising_support = _build_trendline_detail(
        swing_lows,
        current_price,
        current_index,
        "rising support",
    )
    falling_resistance = _build_trendline_detail(
        swing_highs,
        current_price,
        current_index,
        "falling resistance",
    )
    trendline_break = _build_break_status(current_price, rising_support, falling_resistance)

    return {
        "symbol": normalized_symbol,
        "current_price": current_price,
        "rising_support": rising_support,
        "falling_resistance": falling_resistance,
        "trendline_break": trendline_break,
        "summary": _build_summary(
            normalized_symbol,
            rising_support,
            falling_resistance,
            trendline_break,
        ),
        "data_source": metadata["data_source"],
        "analysis_is_live": metadata["analysis_is_live"],
        "fallback_used": metadata["fallback_used"],
        "as_of": metadata["as_of"],
        "history_quality_score": metadata["history_quality_score"],
    }


def analyze_watchlist_trendlines() -> list[dict[str, Any]]:
    return [analyze_trendline(symbol) for symbol in WATCHLIST_SYMBOLS]
