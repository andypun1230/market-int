from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

from app.services.leadership_signal_service import calculate_leadership_signal
from app.services.liquidity_dashboard import analyze_symbol_liquidity
from app.services.multi_timeframe import analyze_multi_timeframe
from app.services.options_intelligence import analyze_symbol_options
from app.services.pattern_detection import detect_patterns
from app.services.relative_strength import build_relative_strength
from app.services.risk import calculate_risk_plan
from app.services.stock_rating import build_stock_ratings
from app.services.support_resistance import calculate_support_resistance
from app.services.timeframe_signal_service import build_multi_timeframe_technical_signals
from app.services.trendline import analyze_trendline
from app.services.volume_analysis import analyze_volume


def build_stock_analysis(symbol: str) -> dict[str, Any]:
    normalized = symbol.upper()
    tasks: dict[str, Callable[[], Any]] = {
        "supportResistance": lambda: calculate_support_resistance(normalized),
        "trendline": lambda: analyze_trendline(normalized),
        "volumeAnalysis": lambda: analyze_volume(normalized),
        "riskPlan": lambda: calculate_risk_plan(normalized),
        "multiTimeframe": lambda: analyze_multi_timeframe(normalized),
        "patterns": lambda: detect_patterns(normalized),
        "relativeStrength": lambda: find_symbol_item(build_relative_strength().items, normalized),
        "stockRating": lambda: find_symbol_item(build_stock_ratings().items, normalized),
        "options": lambda: analyze_symbol_options(normalized),
        "liquidity": lambda: analyze_symbol_liquidity(normalized),
    }
    result: dict[str, Any] = {"symbol": normalized, "errors": {}, "partial": False}

    with ThreadPoolExecutor(max_workers=3) as executor:
        future_map = {executor.submit(fn): key for key, fn in tasks.items()}
        for future in as_completed(future_map):
            key = future_map[future]
            try:
                value = future.result()
                result[key] = to_jsonable(value)
            except Exception as exc:
                result["partial"] = True
                result["errors"][key] = f"{type(exc).__name__}: {exc}"
                result[key] = None

    try:
        multi_timeframe_signals = to_jsonable(build_multi_timeframe_technical_signals(
            normalized,
            support_resistance=result.get("supportResistance"),
            trendline=result.get("trendline"),
            volume_analysis=result.get("volumeAnalysis"),
            relative_strength=result.get("relativeStrength"),
            patterns=result.get("patterns"),
        ))
        result["multiTimeframeSignals"] = multi_timeframe_signals
    except Exception as exc:
        result["partial"] = True
        result["errors"]["multiTimeframeSignals"] = f"{type(exc).__name__}: {exc}"
        result["multiTimeframeSignals"] = None

    try:
        result["leadershipSignal"] = to_jsonable(calculate_leadership_signal(
            normalized,
            relative_strength=result.get("relativeStrength"),
            volume_analysis=result.get("volumeAnalysis"),
            multi_timeframe_signals=result.get("multiTimeframeSignals"),
            stock_rating=result.get("stockRating"),
        ))
    except Exception as exc:
        result["partial"] = True
        result["errors"]["leadershipSignal"] = f"{type(exc).__name__}: {exc}"
        result["leadershipSignal"] = None

    return result


def find_symbol_item(items: list[Any], symbol: str) -> Any | None:
    for item in items:
        if getattr(item, "symbol", "").upper() == symbol:
            return item
    return None


def to_jsonable(value: object) -> Any:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    return value
