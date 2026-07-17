from app.models.market import IndexHistoryResponse, IndexSnapshot
from app.providers.mock_provider import generate_mock_index_closes
from app.providers.models import HistoryData, QuoteData
from app.providers.selector import get_market_data_provider, mark_mock_fallback
from app.services.candle_data import build_history_metadata, get_symbol_history
from app.services.technical_indicators import (
    calculate_ema,
    calculate_rsi,
    calculate_sma,
    extract_closes_from_history,
)
from app.services.service_cache import get_or_compute, get_service_ttl

INDEX_SYMBOLS = ["SPY", "QQQ", "IWM", "DJI"]
PROVIDER_INDEX_SYMBOLS = {
    "SPY": "SPY",
    "QQQ": "QQQ",
    "IWM": "IWM",
    "DJI": "DIA",
}


def get_historical_closes(symbol: str) -> list[float]:
    """Return deterministic legacy mock closes for compatibility."""
    normalized_symbol = "DJI" if symbol.upper() == "DIA" else symbol.upper()
    return generate_mock_index_closes(normalized_symbol)


def get_index_snapshot(symbol: str) -> IndexSnapshot:
    public_symbol = normalize_public_index_symbol(symbol)
    provider_symbol = PROVIDER_INDEX_SYMBOLS[public_symbol]
    provider = get_market_data_provider()
    quote = safe_get_quote(provider, provider_symbol)
    history, validation = get_symbol_history(provider_symbol, days=240, minimum_candles=200)
    history_metadata = build_history_metadata(history, validation)
    closes = extract_closes_from_history(history)
    latest_close = quote.price
    previous_close = quote.previous_close or (closes[-2] if len(closes) > 1 else latest_close)

    return IndexSnapshot(
        symbol=public_symbol,
        price=latest_close,
        change=quote.change if quote.change is not None else round(latest_close - previous_close, 2),
        change_percent=quote.change_percent,
        volume=quote.volume if quote.volume is not None else latest_volume(history),
        ema_20=calculate_ema(closes, 20),
        ema_50=calculate_ema(closes, 50),
        ema_200=calculate_ema(closes, 200),
        sma_50=calculate_sma(closes, 50),
        rsi_14=calculate_rsi(closes, 14),
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
    public_symbol = normalize_public_index_symbol(symbol)
    provider_symbol = PROVIDER_INDEX_SYMBOLS[public_symbol]
    history, validation = get_symbol_history(provider_symbol, days=240, minimum_candles=200)

    return IndexHistoryResponse(
        symbol=public_symbol,
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
    normalized_symbol = symbol.upper()
    if normalized_symbol == "DIA":
        return "DJI"
    if normalized_symbol not in PROVIDER_INDEX_SYMBOLS:
        raise KeyError(f"Unsupported index symbol: {symbol}")
    return normalized_symbol


def latest_volume(history: HistoryData) -> float | None:
    if not history.candles:
        return None
    return history.candles[-1].volume


def build_data_source(quote: QuoteData, history: HistoryData) -> str:
    if quote.source == history.source:
        return quote.source
    return f"quote:{quote.source};history:{history.source}"
