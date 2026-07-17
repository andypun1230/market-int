from __future__ import annotations

from typing import Any

from app.providers.selector import get_market_data_provider
from app.services.pattern_detection import WATCHLIST_SYMBOLS
from app.services.service_cache import get_cached_service_value, get_or_compute, get_service_ttl


def build_watchlist_summary() -> dict[str, Any]:
    return get_or_compute(
        "watchlist-summary",
        get_service_ttl("SERVICE_CACHE_MARKET_CORE_TTL_SECONDS", 60),
        _build_watchlist_summary_uncached,
    )


def _build_watchlist_summary_uncached() -> dict[str, Any]:
    provider = get_market_data_provider()
    ratings = map_cached_items("stock-ratings")
    relative_strength = map_cached_items("relative-strength")
    patterns = map_cached_patterns()
    items = []

    for symbol in WATCHLIST_SYMBOLS:
        quote = safe_quote(provider, symbol)
        rating = ratings.get(symbol)
        rs = relative_strength.get(symbol)
        pattern = patterns.get(symbol)
        items.append(
            {
                "ticker": symbol,
                "symbol": symbol,
                "trend": rating.get("status") if rating else "Watchlist",
                "setup": pattern.get("name") if pattern else "Setup updating",
                "support_zone": "N/A",
                "risk_flag": rating.get("risk_level") if rating else "N/A",
                "price": quote.get("price"),
                "change": quote.get("change"),
                "change_percent": quote.get("change_percent"),
                "data_source": quote.get("source"),
                "is_live": quote.get("is_live"),
                "is_stale": quote.get("is_stale"),
                "fallback_used": quote.get("fallback_used"),
                "as_of": quote.get("timestamp"),
                "rating": rating.get("rating") if rating else None,
                "overall_score": rating.get("overall_score") if rating else None,
                "rs_rank": rs.get("rank") if rs else None,
                "rs_status": rs.get("status") if rs else None,
                "pattern_name": pattern.get("name") if pattern else None,
                "pattern_confidence": pattern.get("confidence") if pattern else None,
            }
        )

    return {
        "items": items,
        "summary": "Compact watchlist summary uses live/cached quotes and cached intelligence where available.",
        "cache_status": "fresh",
    }


def safe_quote(provider: object, symbol: str) -> dict[str, Any]:
    try:
        return provider.get_quote(symbol).model_dump()
    except Exception:
        return {
            "symbol": symbol,
            "price": None,
            "change": None,
            "change_percent": None,
            "source": "unavailable",
            "is_live": False,
            "is_stale": True,
            "fallback_used": False,
            "timestamp": None,
        }


def map_cached_items(key: str) -> dict[str, dict[str, Any]]:
    value = to_jsonable(get_cached_service_value(key))
    if not isinstance(value, dict):
        return {}
    return {
        item.get("symbol"): item
        for item in value.get("items", [])
        if isinstance(item, dict) and item.get("symbol")
    }


def map_cached_patterns() -> dict[str, dict[str, Any]]:
    value = to_jsonable(get_cached_service_value("patterns"))
    if not isinstance(value, dict):
        return {}
    result = {}
    for item in value.get("patterns", []):
        if isinstance(item, dict) and item.get("symbol") and item["symbol"] not in result:
            result[item["symbol"]] = item
    return result


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
