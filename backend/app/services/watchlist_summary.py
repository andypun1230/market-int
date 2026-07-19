from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from app.providers.models import QuoteData
from app.providers.symbols import normalize_symbol_list
from app.cache.market_data_cache import build_quote_cache_key
from app.services.gain_policy import quote_gain
from app.services.market_data_repository import get_market_data_repository
from app.services.pattern_detection import WATCHLIST_SYMBOLS
from app.services.service_cache import get_or_compute, get_service_ttl
from app.stock_snapshots.models import StockAnalysisSnapshot
from app.stock_snapshots.readers import snapshot_status_for_read
from app.stock_snapshots.service import get_stock_snapshot_service


REQUIRED_ANALYSIS_SECTIONS = ("chart", "rating", "risk", "trend")


def build_watchlist_summary(symbols: list[str] | None = None) -> dict[str, Any]:
    requested_symbols = normalize_watchlist_symbols(symbols or [])
    resolved_symbols = normalize_watchlist_symbols([*WATCHLIST_SYMBOLS, *requested_symbols])
    membership_hash = build_membership_hash(resolved_symbols)
    return get_or_compute(
        f"watchlist-summary:v2:{membership_hash}",
        get_service_ttl("SERVICE_CACHE_MARKET_CORE_TTL_SECONDS", 60),
        lambda: _build_watchlist_summary_uncached(
            resolved_symbols,
            membership_hash,
            refresh_missing_symbols=set(requested_symbols),
        ),
    )


def _build_watchlist_summary_uncached(
    symbols: list[str] | None = None,
    membership_hash: str | None = None,
    *,
    refresh_missing_symbols: set[str] | None = None,
    snapshots: dict[str, StockAnalysisSnapshot | None] | None = None,
    dependency_signature: str | None = None,
) -> dict[str, Any]:
    symbols = normalize_watchlist_symbols(symbols or WATCHLIST_SYMBOLS)
    membership_hash = membership_hash or build_membership_hash(symbols)
    refresh_missing_symbols = refresh_missing_symbols or set()
    repository = get_market_data_repository()
    snapshot_service = get_stock_snapshot_service()
    snapshots = snapshots or {symbol: snapshot_service.get_latest_snapshot(symbol) for symbol in symbols}
    quotes_by_symbol = fetch_quotes_by_symbol(symbols)
    dependency_signature = dependency_signature or build_dependency_signature(repository, symbols, snapshots)
    items: list[dict[str, Any]] = []

    for index, symbol in enumerate(symbols):
        quote = quotes_by_symbol.get(symbol)
        snapshot = snapshots.get(symbol)
        refreshing = snapshot_service.is_refreshing(symbol)
        # Only user-requested symbols may schedule a refresh from a list read.
        # Static/default rows remain read-only so opening Watchlist cannot fan out
        # into snapshot work; the service dedupes the one requested refresh.
        needs_refresh = snapshot is None or snapshot_status_for_read(snapshot) == "stale"
        if needs_refresh and symbol in refresh_missing_symbols:
            snapshot_service.trigger_background_refresh(symbol)
            refreshing = snapshot_service.is_refreshing(symbol)
        items.append(build_summary_item(symbol, index, quote, snapshot, refreshing))

    usable_items = [item for item in items if item["overall_status"] != "unavailable"]
    unavailable = [item["symbol"] for item in items if item["overall_status"] == "unavailable"]
    coverage_ratio = round(len(usable_items) / len(symbols), 4) if symbols else 1.0
    source_state = aggregate_source_state([item.get("source_state") for item in items])
    return {
        "snapshot_id": f"watchlist-{membership_hash}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "membership_hash": membership_hash,
        "dependency_signature": dependency_signature,
        "status": "complete" if not unavailable else "partial" if usable_items else "unavailable",
        "source_state": source_state,
        "symbols_requested": symbols,
        "symbols_available": [item["symbol"] for item in usable_items],
        "symbols_unavailable": unavailable,
        "coverage_ratio": coverage_ratio,
        "items": items,
        "leaders": sorted(usable_items, key=lambda item: item.get("change_percent") or float("-inf"), reverse=True)[:3],
        "laggards": sorted(usable_items, key=lambda item: item.get("change_percent") if item.get("change_percent") is not None else float("inf"))[:3],
        "warnings": [f"{len(unavailable)} watchlist symbol(s) unavailable."] if unavailable else [],
        "summary": "Compact watchlist summary uses the canonical quote and StockAnalysisSnapshot state for each symbol.",
        "cache_status": "fresh",
        "provider": repository.get_provider_name_for("quotes"),
    }


def fetch_quotes_by_symbol(symbols: list[str]) -> dict[str, QuoteData]:
    result = get_market_data_repository().get_batch_quotes(symbols)
    return {quote.symbol: quote for quote in result.quotes}


def build_summary_item(
    symbol: str,
    sort_order: int,
    quote: QuoteData | None,
    snapshot: StockAnalysisSnapshot | None,
    refreshing: bool,
) -> dict[str, Any]:
    evaluation = build_watchlist_evaluation(symbol, quote, snapshot, refreshing)
    rating = section_payload(snapshot, "rating")
    risk = section_payload(snapshot, "risk")
    trend = section_payload(snapshot, "trend")
    pattern = section_payload(snapshot, "pattern")
    signal = section_payload(snapshot, "signals")
    price = quote.price if quote else None
    change, change_percent = quote_gain(price, quote.previous_close if quote else None)
    pattern_items = pattern.get("patterns", []) if isinstance(pattern, dict) else []
    primary_pattern = pattern_items[0] if pattern_items and isinstance(pattern_items[0], dict) else {}
    return {
        "ticker": symbol,
        "symbol": symbol,
        "display_name": symbol,
        "trend": value_at(rating, "status") or value_at(trend, "summary") or status_label(evaluation["overall_status"]),
        "setup": value_at(primary_pattern, "name") or evaluation["status_reason"],
        "support_zone": "N/A",
        "risk_flag": value_at(risk, "risk_level") or value_at(rating, "risk_level"),
        "quote": quote.model_dump() if quote else None,
        "price": price,
        "change": change,
        "change_percent": change_percent,
        "quote_timestamp": quote.timestamp if quote else None,
        "source_state": evaluation["source_state"],
        "provider": quote.provider or quote.source if quote else None,
        "stale": bool(quote.is_stale) if quote else evaluation["overall_status"] == "stale",
        "data_source": quote.source if quote else "unavailable",
        "is_live": quote.is_live if quote else False,
        "is_stale": bool(quote.is_stale) if quote else evaluation["overall_status"] == "stale",
        "fallback_used": quote.fallback_used if quote else False,
        "as_of": quote.timestamp if quote else evaluation["analysis_updated_at"],
        "sort_order": sort_order,
        "rating": value_at(rating, "rating"),
        "overall_score": value_at(rating, "overall_score"),
        "rs_rank": value_at(section_payload(snapshot, "relative_strength"), "rank"),
        "rs_status": value_at(section_payload(snapshot, "relative_strength"), "status"),
        "pattern_name": value_at(primary_pattern, "name"),
        "pattern_confidence": value_at(primary_pattern, "confidence"),
        "signal": value_at(signal, "short", "headline") or value_at(rating, "status"),
        "signal_confidence": value_at(signal, "short", "confidence"),
        **evaluation,
    }


def build_watchlist_evaluation(
    symbol: str,
    quote: QuoteData | None,
    snapshot: StockAnalysisSnapshot | None,
    refreshing: bool,
) -> dict[str, Any]:
    available_fields, missing_fields = snapshot_fields(snapshot)
    analysis_status = snapshot_status_for_read(snapshot) if snapshot else "initializing"
    quote_status = quote_state(quote)
    quote_available = quote is not None and quote.price is not None
    required_available = all(section in available_fields for section in REQUIRED_ANALYSIS_SECTIONS)
    snapshot_source = snapshot.source_state if snapshot else "unavailable"
    source_state = aggregate_source_state([quote.source_state if quote else None, snapshot_source])

    if snapshot is None:
        if quote_available:
            overall_status = "pending"
            reason_code = "snapshot_building" if refreshing else "snapshot_missing"
            reason = "Preparing analysis snapshot." if refreshing else "Quote available; analysis snapshot is preparing."
            next_action = "Analysis refresh is scheduled automatically."
        else:
            overall_status = "unavailable"
            reason_code = "quote_unavailable"
            reason = "Quote and analysis snapshot are unavailable."
            next_action = "Retry when a provider quote or validated analysis snapshot becomes available."
    elif analysis_status == "stale":
        overall_status = "stale"
        reason_code = "stale_last_known_good"
        reason = "Showing the latest compatible analysis while it refreshes."
        next_action = "A compatible analysis refresh is in progress or due."
    elif quote_available and required_available and snapshot.status == "complete":
        overall_status = "complete"
        reason_code = None
        reason = "Live quote and compatible analysis snapshot are available."
        next_action = None
    elif quote_available and available_fields:
        overall_status = "partial"
        reason_code = "optional_metrics_missing" if missing_fields else "insufficient_history"
        reason = "Quote and trend available; advanced signals are still loading." if "trend" in available_fields else "Quote available; analysis is partially evaluated."
        next_action = "The remaining compatible analysis sections will refresh automatically."
    elif available_fields:
        overall_status = "stale"
        reason_code = "quote_unavailable"
        reason = "Analysis is available, but the current quote is unavailable."
        next_action = "Retry when a current provider quote becomes available."
    else:
        overall_status = "unavailable"
        reason_code = "validation_failed" if snapshot.status == "unavailable" else "insufficient_history"
        reason = "Analysis unavailable because the symbol lacks sufficient validated history."
        next_action = "Retry after validated history is available for this symbol."

    return {
        "quote_status": quote_status,
        "quote_price": quote.price if quote else None,
        "quote_change_percent": quote.change_percent if quote else None,
        "quote_source": quote.provider or quote.source if quote else None,
        "quote_timestamp": quote.timestamp if quote else None,
        "analysis_status": analysis_status,
        "analysis_snapshot_id": snapshot.snapshot_id if snapshot else None,
        "analysis_updated_at": snapshot.published_at if snapshot else None,
        "overall_status": overall_status,
        "status_reason_code": reason_code,
        "status_reason": reason,
        "next_action": next_action,
        "retryable": overall_status in {"pending", "partial", "stale"} or reason_code in {"quote_unavailable", "provider_unavailable"},
        "refreshing": refreshing,
        "available_fields": available_fields,
        "missing_fields": missing_fields,
        "source_state": source_state,
    }


def snapshot_fields(snapshot: StockAnalysisSnapshot | None) -> tuple[list[str], list[str]]:
    if snapshot is None:
        return [], list(REQUIRED_ANALYSIS_SECTIONS)
    available: list[str] = []
    missing: list[str] = []
    for name, section in snapshot.sections.items():
        if section.payload is not None and section.status != "unavailable":
            available.append(name)
        else:
            missing.append(name)
    for name in REQUIRED_ANALYSIS_SECTIONS:
        if name not in available and name not in missing:
            missing.append(name)
    return sorted(available), sorted(missing)


def section_payload(snapshot: StockAnalysisSnapshot | None, name: str) -> dict[str, Any]:
    payload = snapshot.section_payload(name) if snapshot else None
    return payload if isinstance(payload, dict) else {}


def value_at(payload: dict[str, Any], *keys: str) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def quote_state(quote: QuoteData | None) -> str:
    if quote is None or quote.price is None:
        return "unavailable"
    if quote.is_stale:
        return "stale"
    return "live" if quote.is_live else "cached"


def status_label(status: str) -> str:
    return {
        "complete": "Complete",
        "partial": "Partial",
        "pending": "Preparing analysis",
        "stale": "Stale",
        "unavailable": "Unavailable",
    }.get(status, "Unavailable")


def normalize_watchlist_symbols(symbols: list[str]) -> list[str]:
    return normalize_symbol_list(symbols, apply_alias=True, limit=50)


def build_membership_hash(symbols: list[str]) -> str:
    payload = {"version": 2, "symbols": symbols}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def build_dependency_signature(
    repository: Any,
    symbols: list[str],
    snapshots: dict[str, StockAnalysisSnapshot | None],
) -> str:
    provider = repository.get_provider_name_for("quotes")
    payload = {
        "quote_provider": provider,
        "quote_timestamps": {
            symbol: cached_quote_timestamp(repository, provider, symbol)
            for symbol in symbols
        },
        "snapshots": {
            symbol: {
                "snapshot_id": snapshot.snapshot_id if snapshot else None,
                "status": snapshot_status_for_read(snapshot) if snapshot else "initializing",
                "published_at": snapshot.published_at if snapshot else None,
            }
            for symbol, snapshot in snapshots.items()
        },
    }
    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def cached_quote_timestamp(repository: Any, provider: str, symbol: str) -> str | None:
    cache = getattr(repository, "cache", None)
    if cache is None or not hasattr(cache, "get"):
        return None
    try:
        cached, _age = cache.get(build_quote_cache_key(provider, symbol))
    except Exception:
        return None
    return str(getattr(cached, "timestamp", "")) or None


def aggregate_source_state(states: list[Any]) -> str:
    values = {str(state) for state in states if state and state != "unavailable"}
    if not values:
        return "unavailable"
    if len(values) == 1:
        return next(iter(values))
    return "mixed"
