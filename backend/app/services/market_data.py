from typing import Iterable

from app.models.market import IndexHistoryResponse, IndexSnapshot
from app.providers.mock_provider import generate_mock_index_closes
from app.providers.history_validation import validate_history
from app.providers.models import HistoryData, QuoteData
from app.providers.selector import mark_mock_fallback
from app.services.gain_policy import finite_number, quote_gain
from app.services.candle_data import build_history_metadata, get_symbol_history
from app.services.market_data_repository import get_market_data_repository
from app.services.technical_indicators import (
    calculate_ema,
    calculate_rsi,
    calculate_sma,
    extract_closes_from_history,
)
from app.services.service_cache import get_or_compute, get_service_ttl
from app.validation.symbol_registry import (
    CanonicalIndexEntry,
    canonical_index_universe,
    get_canonical_index_entry,
)

INDEX_SYMBOLS = [entry.display_symbol for entry in canonical_index_universe()]


def get_historical_closes(symbol: str) -> list[float]:
    """Return deterministic legacy mock closes for compatibility."""
    normalized_symbol = "DJI" if symbol.upper() == "DIA" else symbol.upper()
    return generate_mock_index_closes(normalized_symbol)


def get_index_snapshot(symbol: str) -> IndexSnapshot:
    entry = get_canonical_index_entry(symbol)
    repository = get_market_data_repository()
    quote = safe_get_quote(repository, entry.provider_quote_symbol)
    history = safe_get_history(repository, entry.provider_history_symbol, 240)
    validation = validate_history(history, 200)
    return build_index_snapshot(entry, quote, history, validation)


def build_index_snapshots_from_inputs(quotes: dict[str, QuoteData], histories: dict[str, HistoryData]) -> list[IndexSnapshot]:
    snapshots: list[IndexSnapshot] = []
    for entry in canonical_index_universe():
        quote = quotes.get(entry.provider_quote_symbol)
        history = histories.get(entry.provider_history_symbol)
        if quote is None or history is None:
            continue
        snapshots.append(build_index_snapshot(entry, quote, history, validate_history(history, 200)))
    return snapshots


def canonicalize_index_payloads(items: object) -> list[dict[str, object]]:
    if not isinstance(items, list):
        return []
    by_symbol: dict[str, dict[str, object]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        raw_symbol = str(item.get("symbol") or item.get("display_symbol") or "")
        try:
            entry = get_canonical_index_entry(raw_symbol)
        except Exception:
            continue
        payload = dict(item)
        payload["symbol"] = entry.display_symbol
        payload["display_symbol"] = entry.display_symbol
        payload["display_name"] = payload.get("display_name") or entry.display_name
        payload["provider_symbol"] = payload.get("provider_symbol") or entry.provider_history_symbol
        by_symbol[entry.display_symbol] = payload
    order = {entry.display_symbol: entry.sort_order for entry in canonical_index_universe(include_optional=True)}
    return [
        by_symbol[symbol]
        for symbol in sorted(by_symbol, key=lambda value: order.get(value, 999))
    ]


def build_index_snapshot(
    entry: CanonicalIndexEntry,
    quote: QuoteData,
    history: HistoryData,
    validation: dict[str, object] | None = None,
) -> IndexSnapshot:
    history_metadata = build_history_metadata(history, validation)
    closes = extract_closes_from_history(history)
    latest_close = finite_number(quote.price) or (closes[-1] if closes else 0.0)
    previous_close = finite_number(quote.previous_close) or (closes[-2] if len(closes) > 1 else latest_close)
    calculated_change, calculated_change_percent = quote_gain(latest_close, previous_close)
    change = calculated_change
    change_percent = calculated_change_percent
    warnings = []
    if change_percent is None:
        warnings.append("Change percent unavailable because previous close is missing or zero.")

    return IndexSnapshot(
        symbol=entry.display_symbol,
        display_symbol=entry.display_symbol,
        provider_symbol=entry.provider_history_symbol,
        display_name=entry.display_name,
        asset_type=entry.asset_type,
        price=latest_close,
        change=change if change is not None else 0.0,
        change_percent=change_percent if change_percent is not None else 0.0,
        previous_close=previous_close,
        volume=quote.volume if quote.volume is not None else latest_volume(history),
        ema_20=calculate_ema(closes, 20),
        ema_50=calculate_ema(closes, 50),
        ema_200=calculate_ema(closes, 200),
        sma_50=calculate_sma(closes, 50),
        rsi_14=calculate_rsi(closes, 14),
        trend=classify_trend(latest_close, calculate_ema(closes, 50), calculate_ema(closes, 200)),
        quote_timestamp=quote.timestamp,
        history_latest_date=history.candles[-1].timestamp if history.candles else history.as_of,
        quote_provider=quote.provider or quote.source,
        history_provider=history.provider or history.source,
        source_state=aggregate_source_state([quote.source_state, history.source_state]),
        stale=quote.is_stale or history.is_stale,
        warnings=warnings,
        data_source=build_data_source(quote, history),
        is_live=quote.is_live and history.is_live,
        is_stale=quote.is_stale or history.is_stale,
        fallback_used=quote.fallback_used or history.fallback_used,
        as_of=max(quote.timestamp, history.as_of),
        quote_is_live=quote.is_live,
        history_is_live=history.is_live,
        analysis_is_live=quote.is_live and history.is_live,
        history_quality_score=history_metadata["history_quality_score"],
    )


def get_index_snapshots() -> list[IndexSnapshot]:
    return get_or_compute(
        "index-snapshots",
        get_service_ttl("SERVICE_CACHE_MARKET_CORE_TTL_SECONDS", 60),
        lambda: [get_index_snapshot(symbol) for symbol in INDEX_SYMBOLS],
    )


def get_index_history(symbol: str) -> IndexHistoryResponse:
    entry = get_canonical_index_entry(symbol)
    provider_symbol = entry.provider_history_symbol
    history, validation = get_symbol_history(provider_symbol, days=240, minimum_candles=200)

    return IndexHistoryResponse(
        symbol=entry.display_symbol,
        closes=extract_closes_from_history(history),
        data_source=history.source,
        is_live=history.is_live,
        is_stale=history.is_stale,
        fallback_used=history.fallback_used,
        as_of=history.as_of,
        history_quality_score=validation.get("quality_score"),
    )


def safe_get_quote(provider: object, symbol: str) -> QuoteData:
    try:
        return provider.get_quote(symbol)
    except Exception:
        return mark_mock_fallback(get_market_data_provider_for_mock().get_quote(symbol))


def safe_get_history(provider: object, symbol: str, days: int) -> HistoryData:
    try:
        return provider.get_history(symbol, resolution="D", days=days)
    except Exception:
        return mark_mock_fallback(get_market_data_provider_for_mock().get_history(symbol, resolution="D", days=days))


def get_market_data_provider_for_mock():
    from app.providers.mock_provider import MockMarketDataProvider

    return MockMarketDataProvider()


def normalize_public_index_symbol(symbol: str) -> str:
    return get_canonical_index_entry(symbol).display_symbol


def latest_volume(history: HistoryData) -> float | None:
    if not history.candles:
        return None
    return history.candles[-1].volume


def build_data_source(quote: QuoteData, history: HistoryData) -> str:
    if quote.source == history.source:
        return quote.source
    return f"quote:{quote.source};history:{history.source}"


def aggregate_source_state(states: Iterable[str | None]) -> str:
    values = {state for state in states if state}
    if not values:
        return "unavailable"
    if len(values) == 1:
        return next(iter(values))
    return "mixed"


def classify_trend(price: float | None, ema_50: float | None, ema_200: float | None) -> str:
    if price is None or ema_50 is None or ema_200 is None:
        return "Unavailable"
    if price >= ema_50 >= ema_200:
        return "Uptrend"
    if price <= ema_50 <= ema_200:
        return "Downtrend"
    return "Mixed"
