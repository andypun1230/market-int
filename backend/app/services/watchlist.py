from typing import Any, Dict

from app.models.market import WatchlistItem, WatchlistResponse
from app.providers.mock_provider import MockMarketDataProvider
from app.providers.models import QuoteData
from app.providers.selector import get_market_data_provider, mark_mock_fallback
from app.services.service_cache import get_or_compute, get_service_ttl

WATCHLIST_ROWS = [
    {
        "ticker": "MU",
        "trend": "Uptrend",
        "setup": "Pullback near 20EMA",
        "support_zone": "$128–132",
        "risk_flag": "Earnings soon",
    },
    {
        "ticker": "NVDA",
        "trend": "Strong uptrend",
        "setup": "Extended",
        "support_zone": "$145–150",
        "risk_flag": "Too far above 50MA",
    },
    {
        "ticker": "ARM",
        "trend": "Constructive",
        "setup": "Tight consolidation",
        "support_zone": "$160–165",
        "risk_flag": "High valuation",
    },
    {
        "ticker": "SNDK",
        "trend": "Uptrend",
        "setup": "Breakout watch",
        "support_zone": "$62–65",
        "risk_flag": "Volatile price action",
    },
]


def build_market_watchlist() -> WatchlistResponse:
    return get_or_compute(
        "watchlist",
        get_service_ttl("SERVICE_CACHE_MARKET_CORE_TTL_SECONDS", 60),
        _build_market_watchlist_uncached,
    )


def _build_market_watchlist_uncached() -> WatchlistResponse:
    provider = get_market_data_provider()
    tickers = [row["ticker"] for row in WATCHLIST_ROWS]
    quotes_by_symbol = {
        quote.symbol: quote
        for quote in safe_get_quotes(provider, tickers)
    }

    return WatchlistResponse(
        items=[
            build_watchlist_item(row, quotes_by_symbol[row["ticker"]])
            for row in WATCHLIST_ROWS
        ],
    )


def build_watchlist_item(row: dict[str, str], quote: QuoteData) -> WatchlistItem:
    return WatchlistItem(
        ticker=row["ticker"],
        trend=row["trend"],
        setup=row["setup"],
        support_zone=row["support_zone"],
        risk_flag=row["risk_flag"],
        price=quote.price,
        change=quote.change,
        change_percent=quote.change_percent,
        data_source=quote.source,
        is_live=quote.is_live,
        is_stale=quote.is_stale,
        fallback_used=quote.fallback_used,
        as_of=quote.timestamp,
    )


def safe_get_quote(provider: object, symbol: str) -> QuoteData:
    try:
        return provider.get_quote(symbol)
    except Exception:
        return mark_mock_fallback(MockMarketDataProvider().get_quote(symbol))


def safe_get_quotes(provider: object, symbols: list[str]) -> list[QuoteData]:
    try:
        return provider.get_quotes(symbols)
    except Exception:
        return [safe_get_quote(provider, symbol) for symbol in symbols]


def build_user_watchlist_item(ticker: str) -> Dict[str, Any]:
    return {
        "ticker": ticker.upper(),
        "trend": "up",
        "setup": "none",
        "support": [90, 95],
        "resistance": [110, 115],
        "earnings_date": "2026-07-25",
    }
