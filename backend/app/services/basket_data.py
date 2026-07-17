import os
import time
from typing import Any

from app.providers.cache import get_cached_value, set_cached_value
from app.providers.models import HistoryData
from app.services.candle_data import get_symbol_history
from app.services.technical_indicators import calculate_ema

DEFAULT_MINIMUM_COVERAGE_RATIO = 0.70


def get_basket_histories(
    symbols: list[str],
    days: int = 260,
    resolution: str = "D",
    minimum_coverage_ratio: float = DEFAULT_MINIMUM_COVERAGE_RATIO,
    cache_ttl_seconds: int | None = None,
) -> dict[str, Any]:
    unique_symbols = list(dict.fromkeys(symbol.upper() for symbol in symbols if symbol))
    cache_key = f"basket:{','.join(unique_symbols)}:{resolution}:{days}"
    cached = get_cached_value(cache_key)
    if cached is not None:
        return cached

    histories: dict[str, HistoryData] = {}
    validations: dict[str, dict[str, Any]] = {}
    failed_symbols: list[str] = []
    started = time.monotonic()
    budget_seconds = get_time_budget_seconds()
    max_symbols = get_max_symbols_per_cycle()

    for index, symbol in enumerate(unique_symbols):
        if index >= max_symbols or (time.monotonic() - started) >= budget_seconds:
            failed_symbols.extend(symbol for symbol in unique_symbols[index:] if symbol not in failed_symbols)
            break
        try:
            history, validation = get_symbol_history(
                symbol,
                days=days,
                resolution=resolution,
                minimum_candles=min(40, days),
            )
            if history.candles and validation.get("valid", False):
                histories[symbol] = history
                validations[symbol] = validation
            else:
                failed_symbols.append(symbol)
        except Exception:
            failed_symbols.append(symbol)

    metadata = build_basket_metadata(
        requested_symbols=unique_symbols,
        histories=histories,
        validations=validations,
        failed_symbols=failed_symbols,
        minimum_coverage_ratio=minimum_coverage_ratio,
    )
    result = {
        "histories": histories,
        "validations": validations,
        "metadata": metadata,
    }
    set_cached_value(cache_key, result, cache_ttl_seconds or get_default_ttl())
    return result


def get_equal_weight_returns(symbols: list[str], interval: str, days: int = 260) -> dict[str, Any]:
    basket = get_basket_histories(symbols, days=days)
    returns = [
        calculate_history_return(history, interval)
        for history in basket["histories"].values()
    ]
    usable_returns = [value for value in returns if value is not None]
    metadata = basket["metadata"]

    return {
        "return": round(sum(usable_returns) / len(usable_returns), 2) if usable_returns else 0.0,
        "metadata": metadata,
    }


def calculate_basket_breadth(symbols: list[str], days: int = 260) -> dict[str, Any]:
    basket = get_basket_histories(symbols, days=days)
    histories: dict[str, HistoryData] = basket["histories"]
    total = len(histories)
    advancing = 0
    declining = 0
    unchanged = 0
    above_20 = 0
    above_50 = 0
    above_200 = 0
    new_highs = 0
    new_lows = 0
    volume_participants = 0

    for history in histories.values():
        candles = history.candles
        if len(candles) < 2:
            continue

        latest = candles[-1]
        previous = candles[-2]
        closes = [candle.close for candle in candles]
        latest_close = latest.close

        if latest_close > previous.close:
            advancing += 1
        elif latest_close < previous.close:
            declining += 1
        else:
            unchanged += 1

        ema_20 = calculate_ema(closes, 20)
        ema_50 = calculate_ema(closes, 50)
        ema_200 = calculate_ema(closes, 200)
        if ema_20 is not None and latest_close > ema_20:
            above_20 += 1
        if ema_50 is not None and latest_close > ema_50:
            above_50 += 1
        if ema_200 is not None and latest_close > ema_200:
            above_200 += 1

        recent_high = max(candle.high for candle in candles[-252:])
        recent_low = min(candle.low for candle in candles[-252:])
        if latest_close >= recent_high:
            new_highs += 1
        if latest_close <= recent_low:
            new_lows += 1

        if len(candles) >= 21:
            average_volume = sum(candle.volume for candle in candles[-21:-1]) / 20
            if average_volume > 0 and latest.volume >= average_volume:
                volume_participants += 1

    advance_decline_ratio = None if declining == 0 else round(advancing / declining, 2)
    metadata = basket["metadata"]

    return {
        "total_stocks": total,
        "advancing_stocks": advancing,
        "declining_stocks": declining,
        "unchanged_stocks": unchanged,
        "advance_decline_ratio": advance_decline_ratio,
        "percent_above_20ema": percent(above_20, total),
        "percent_above_50ema": percent(above_50, total),
        "percent_above_200ema": percent(above_200, total),
        "new_52w_highs": new_highs,
        "new_52w_lows": new_lows,
        "volume_participation": percent(volume_participants, total),
        "metadata": metadata,
    }


def calculate_basket_relative_strength(
    symbols: list[str],
    benchmark_symbol: str = "SPY",
    days: int = 260,
) -> dict[str, Any]:
    basket_return = get_equal_weight_returns(symbols, "1m", days=days)
    benchmark_basket = get_basket_histories([benchmark_symbol], days=days)
    benchmark_history = benchmark_basket["histories"].get(benchmark_symbol.upper())
    benchmark_return = calculate_history_return(benchmark_history, "1m") if benchmark_history else 0.0
    relative_return = basket_return["return"] - (benchmark_return or 0.0)
    score = clamp_score(55 + (relative_return * 3))

    metadata = combine_metadata(
        [basket_return["metadata"], benchmark_basket["metadata"]],
    )
    return {
        "score": score,
        "relative_return": round(relative_return, 2),
        "benchmark_return": round(benchmark_return or 0.0, 2),
        "metadata": metadata,
    }


def build_basket_metadata(
    requested_symbols: list[str],
    histories: dict[str, HistoryData],
    validations: dict[str, dict[str, Any]],
    failed_symbols: list[str],
    minimum_coverage_ratio: float,
) -> dict[str, Any]:
    requested_count = len(requested_symbols)
    successful_count = len(histories)
    coverage = percent(successful_count, requested_count)
    live_symbols = sum(1 for history in histories.values() if history.is_live)
    fallback_symbols = sum(1 for history in histories.values() if history.fallback_used)
    quality_scores = [
        validation.get("quality_score", 0)
        for validation in validations.values()
        if validation.get("quality_score") is not None
    ]
    as_of_values = [history.as_of for history in histories.values() if history.as_of]
    valid = requested_count > 0 and coverage >= minimum_coverage_ratio * 100

    if live_symbols and not fallback_symbols and live_symbols == successful_count:
        overall_mode = "live"
    elif live_symbols or fallback_symbols:
        overall_mode = "mixed"
    else:
        overall_mode = "mock"

    return {
        "requested_symbols": requested_count,
        "successful_symbols": successful_count,
        "failed_symbols": failed_symbols,
        "failed_symbols_count": len(failed_symbols),
        "coverage_percent": coverage,
        "live_symbols": live_symbols,
        "fallback_symbols": fallback_symbols,
        "overall_mode": overall_mode,
        "history_quality_score": round(sum(quality_scores) / len(quality_scores)) if quality_scores else 0,
        "as_of": max(as_of_values) if as_of_values else None,
        "valid": valid,
    }


def combine_metadata(metadata_items: list[dict[str, Any]]) -> dict[str, Any]:
    requested = sum(item.get("requested_symbols", 0) for item in metadata_items)
    successful = sum(item.get("successful_symbols", 0) for item in metadata_items)
    failed_symbols = [
        symbol
        for item in metadata_items
        for symbol in item.get("failed_symbols", [])
    ]
    live_symbols = sum(item.get("live_symbols", 0) for item in metadata_items)
    fallback_symbols = sum(item.get("fallback_symbols", 0) for item in metadata_items)
    quality_scores = [
        item.get("history_quality_score", 0)
        for item in metadata_items
        if item.get("history_quality_score") is not None
    ]
    modes = {item.get("overall_mode") for item in metadata_items}
    if modes == {"live"}:
        overall_mode = "live"
    elif "live" in modes or "mixed" in modes or fallback_symbols:
        overall_mode = "mixed"
    else:
        overall_mode = "mock"

    return {
        "requested_symbols": requested,
        "successful_symbols": successful,
        "failed_symbols": failed_symbols,
        "failed_symbols_count": len(failed_symbols),
        "coverage_percent": percent(successful, requested),
        "live_symbols": live_symbols,
        "fallback_symbols": fallback_symbols,
        "overall_mode": overall_mode,
        "history_quality_score": round(sum(quality_scores) / len(quality_scores)) if quality_scores else 0,
        "as_of": max((item.get("as_of") for item in metadata_items if item.get("as_of")), default=None),
        "valid": percent(successful, requested) >= DEFAULT_MINIMUM_COVERAGE_RATIO * 100,
    }


def calculate_history_return(history: HistoryData | None, interval: str) -> float | None:
    if history is None or len(history.candles) < 2:
        return None

    candles = history.candles
    latest = candles[-1]
    normalized_interval = interval.lower()

    if normalized_interval == "1d":
        start = candles[-2]
    elif normalized_interval == "1w":
        start = candles[-6] if len(candles) >= 6 else candles[0]
    elif normalized_interval in ("1m", "1mo"):
        start = candles[-22] if len(candles) >= 22 else candles[0]
    elif normalized_interval == "3m":
        start = candles[-64] if len(candles) >= 64 else candles[0]
    elif normalized_interval == "6m":
        start = candles[-127] if len(candles) >= 127 else candles[0]
    elif normalized_interval in ("1y", "12m"):
        start = candles[-253] if len(candles) >= 253 else candles[0]
    elif normalized_interval == "mtd":
        latest_month = latest.timestamp[:7]
        start = next((candle for candle in candles if candle.timestamp.startswith(latest_month)), candles[0])
    elif normalized_interval == "ytd":
        latest_year = latest.timestamp[:4]
        start = next((candle for candle in candles if candle.timestamp.startswith(latest_year)), candles[0])
    else:
        start = candles[0]

    if start.close == 0:
        return None
    return round(((latest.close - start.close) / start.close) * 100, 2)


def percent(part: int | float, whole: int | float) -> float:
    if whole == 0:
        return 0.0
    return round((part / whole) * 100, 2)


def clamp_score(value: float | int) -> int:
    return max(0, min(100, round(value)))


def get_default_ttl() -> int:
    return int(os.getenv("BREADTH_CACHE_TTL_SECONDS", "900"))


def get_time_budget_seconds() -> float:
    try:
        return float(os.getenv("HEAVY_SERVICE_TIME_BUDGET_SECONDS", "15"))
    except ValueError:
        return 15.0


def get_max_symbols_per_cycle() -> int:
    if os.getenv("DATA_PROVIDER", "mock").lower() == "mock" and "MAX_SYMBOL_REFRESH_PER_CYCLE" not in os.environ:
        return 10_000
    try:
        return max(1, int(os.getenv("MAX_SYMBOL_REFRESH_PER_CYCLE", "15")))
    except ValueError:
        return 15
