from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

from app.services.leadership_signal_service import calculate_leadership_signal
from app.services.liquidity_dashboard import analyze_symbol_liquidity
from app.services.multi_timeframe import analyze_multi_timeframe
from app.services.options_intelligence import analyze_symbol_options
from app.services.pattern_detection import detect_patterns
from app.services.relative_strength import calculate_rs_score
from app.services.risk import calculate_risk_plan
from app.services.stock_rating import calculate_stock_rating
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
        "relativeStrength": lambda: calculate_rs_score(normalized),
        "stockRating": lambda: calculate_stock_rating(normalized),
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
                result["errors"][key] = safe_error_summary(exc)
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
        result["errors"]["multiTimeframeSignals"] = safe_error_summary(exc)
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
        result["errors"]["leadershipSignal"] = safe_error_summary(exc)
        result["leadershipSignal"] = None

    return result


def safe_error_summary(error: Exception) -> dict[str, str]:
    category = getattr(error, "category", None)
    if category:
        return {
            "category": str(category),
            "message": "Data dependency unavailable.",
        }
    return {
        "category": "calculation_error",
        "message": "Section unavailable due to a recoverable calculation error.",
    }


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
