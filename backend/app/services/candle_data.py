from typing import Any

from app.providers.history_validation import validate_history
from app.providers.models import CandleData, HistoryData
from app.providers.selector import get_market_data_provider


def get_symbol_history(
    symbol: str,
    days: int = 240,
    resolution: str = "D",
    minimum_candles: int | None = None,
) -> tuple[HistoryData, dict[str, Any]]:
    history = get_market_data_provider().get_history(symbol.upper(), resolution=resolution, days=days)
    validation = validate_history(history, minimum_candles or min(60, days))
    return history, validation


def get_closes(symbol: str, days: int = 240) -> list[float]:
    history, _ = get_symbol_history(symbol, days=days)
    return [candle.close for candle in history.candles]


def get_ohlcv(symbol: str, days: int = 240) -> list[dict[str, Any]]:
    history, _ = get_symbol_history(symbol, days=days)
    return candles_to_dicts(history.candles)


def get_history_metadata(symbol: str, days: int = 240) -> dict[str, Any]:
    history, validation = get_symbol_history(symbol, days=days)
    return build_history_metadata(history, validation)


def candles_to_dicts(candles: list[CandleData]) -> list[dict[str, Any]]:
    return [
        {
            "date": candle.timestamp[:10],
            "timestamp": candle.timestamp,
            "open": candle.open,
            "high": candle.high,
            "low": candle.low,
            "close": candle.close,
            "volume": candle.volume,
        }
        for candle in candles
    ]


def build_history_metadata(history: HistoryData, validation: dict[str, Any]) -> dict[str, Any]:
    return {
        "data_source": history.source,
        "history_source": history.source,
        "provider": history.provider,
        "requested_provider": history.requested_provider,
        "source_state": history.source_state,
        "analysis_is_live": history.is_live and validation.get("valid", False),
        "history_is_live": history.is_live,
        "history_is_stale": history.is_stale,
        "fallback_used": history.fallback_used,
        "fallback_reason": history.fallback_reason,
        "cache_hit": history.cache_hit,
        "cache_age_seconds": history.cache_age_seconds,
        "memory_cache_hit": history.memory_cache_hit,
        "persistent_cache_hit": history.persistent_cache_hit,
        "background_refresh_started": history.background_refresh_started,
        "as_of": history.as_of,
        "history_quality_score": validation.get("quality_score"),
        "history_warnings": validation.get("warnings", []),
        "history_errors": validation.get("errors", []),
    }


def build_dependency_quality(
    history_metadata: dict[str, Any],
    mock_components: list[str] | None = None,
    fallback_components: list[str] | None = None,
) -> dict[str, Any]:
    live_components: list[str] = []
    fallback_items: list[str] = list(fallback_components or [])
    mock_items: list[str] = list(mock_components or [])

    if history_metadata.get("history_is_live"):
        live_components.append("history")
    elif history_metadata.get("fallback_used"):
        fallback_items.append("history")
    else:
        mock_items.append("history")

    if live_components and not fallback_items and not mock_items:
        overall_mode = "live"
    elif live_components or fallback_items:
        overall_mode = "mixed"
    else:
        overall_mode = "mock"

    return {
        "history_source": history_metadata.get("history_source"),
        "live_dependencies": live_components,
        "fallback_dependencies": fallback_items,
        "mock_dependencies": mock_items,
        "overall_mode": overall_mode,
        "history_quality_score": history_metadata.get("history_quality_score"),
    }
