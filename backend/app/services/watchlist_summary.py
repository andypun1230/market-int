from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from app.providers.models import QuoteData
from app.providers.symbols import normalize_symbol_list
from app.services.gain_policy import quote_gain
from app.services.market_data_repository import get_market_data_repository
from app.services.pattern_detection import WATCHLIST_SYMBOLS
from app.services.service_cache import get_cached_service_value, get_or_compute, get_service_ttl


def build_watchlist_summary() -> dict[str, Any]:
    symbols = normalize_watchlist_symbols(WATCHLIST_SYMBOLS)
    membership_hash = build_membership_hash(symbols)
    return get_or_compute(
        f"watchlist-summary:{membership_hash}",
        get_service_ttl("SERVICE_CACHE_MARKET_CORE_TTL_SECONDS", 60),
        lambda: _build_watchlist_summary_uncached(symbols, membership_hash),
    )


def _build_watchlist_summary_uncached(
    symbols: list[str] | None = None,
    membership_hash: str | None = None,
) -> dict[str, Any]:
    symbols = symbols or normalize_watchlist_symbols(WATCHLIST_SYMBOLS)
    membership_hash = membership_hash or build_membership_hash(symbols)
    repository = get_market_data_repository()
    ratings = map_cached_items("stock-ratings")
    relative_strength = map_cached_items("relative-strength")
    patterns = map_cached_patterns()
    items = []
    unavailable: list[str] = []
    quotes_by_symbol = fetch_quotes_by_symbol(symbols)

    for index, symbol in enumerate(symbols):
        quote = quotes_by_symbol.get(symbol)
        if quote is None:
            unavailable.append(symbol)
        rating = ratings.get(symbol)
        rs = relative_strength.get(symbol)
        pattern = patterns.get(symbol)
        items.append(build_summary_item(symbol, index, quote, rating, rs, pattern))

    available_items = [item for item in items if item.get("price") is not None]
    coverage_ratio = round(len(available_items) / len(symbols), 4) if symbols else 1.0
    source_state = aggregate_source_state([item.get("source_state") for item in items])
    return {
        "snapshot_id": f"watchlist-{membership_hash}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "membership_hash": membership_hash,
        "status": "complete" if not unavailable else "partial" if available_items else "unavailable",
        "source_state": source_state,
        "symbols_requested": symbols,
        "symbols_available": [item["symbol"] for item in available_items],
        "symbols_unavailable": unavailable,
        "coverage_ratio": coverage_ratio,
        "items": items,
        "leaders": sorted(available_items, key=lambda item: item.get("change_percent") or float("-inf"), reverse=True)[:3],
        "laggards": sorted(available_items, key=lambda item: item.get("change_percent") if item.get("change_percent") is not None else float("inf"))[:3],
        "warnings": [f"{len(unavailable)} watchlist symbol(s) unavailable."] if unavailable else [],
        "summary": "Compact watchlist summary uses live/cached quotes and cached intelligence where available.",
        "cache_status": "fresh",
        "provider": repository.get_provider_name_for("quotes"),
    }


def fetch_quotes_by_symbol(symbols: list[str]) -> dict[str, QuoteData]:
    repository = get_market_data_repository()
    quotes: dict[str, QuoteData] = {}
    result = repository.get_batch_quotes(symbols)
    for quote in result.quotes:
        quotes[quote.symbol] = quote
    return quotes


def build_summary_item(
    symbol: str,
    sort_order: int,
    quote: QuoteData | None,
    rating: dict[str, Any] | None,
    rs: dict[str, Any] | None,
    pattern: dict[str, Any] | None,
) -> dict[str, Any]:
    price = quote.price if quote else None
    change, change_percent = quote_gain(price, quote.previous_close if quote else None)
    timestamp = quote.timestamp if quote else None
    source_state = quote.source_state if quote else "unavailable"
    stale = bool(quote.is_stale) if quote else True
    return {
        "ticker": symbol,
        "symbol": symbol,
        "display_name": symbol,
        "trend": rating.get("status") if rating else "Watchlist",
        "setup": pattern.get("name") if pattern else "Setup updating",
        "support_zone": "N/A",
        "risk_flag": rating.get("risk_level") if rating else "N/A",
        "quote": quote.model_dump() if quote else None,
        "price": price,
        "change": change,
        "change_percent": change_percent,
        "quote_timestamp": timestamp,
        "source_state": source_state,
        "provider": quote.provider or quote.source if quote else None,
        "stale": stale,
        "data_source": quote.source if quote else "unavailable",
        "is_live": quote.is_live if quote else False,
        "is_stale": stale,
        "fallback_used": quote.fallback_used if quote else False,
        "as_of": timestamp,
        "sort_order": sort_order,
        "rating": rating.get("rating") if rating else None,
        "overall_score": rating.get("overall_score") if rating else None,
        "rs_rank": rs.get("rank") if rs else None,
        "rs_status": rs.get("status") if rs else None,
        "pattern_name": pattern.get("name") if pattern else None,
        "pattern_confidence": pattern.get("confidence") if pattern else None,
    }


def normalize_watchlist_symbols(symbols: list[str]) -> list[str]:
    return normalize_symbol_list(symbols, apply_alias=True, limit=50)


def build_membership_hash(symbols: list[str]) -> str:
    payload = {"version": 1, "symbols": symbols}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def aggregate_source_state(states: list[Any]) -> str:
    values = {str(state) for state in states if state}
    if not values:
        return "unavailable"
    if len(values) == 1:
        return next(iter(values))
    return "mixed"


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
