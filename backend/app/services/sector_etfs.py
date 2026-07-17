import os
from datetime import datetime, timezone

from app.models.market import SectorEtfItem, SectorEtfResponse
from app.providers.mock_provider import MockMarketDataProvider
from app.providers.models import HistoryData, QuoteData
from app.providers.selector import get_market_data_provider, mark_mock_fallback
from app.providers.history_validation import validate_history
from app.services.service_cache import get_or_compute, get_service_ttl
from app.services.technical_indicators import calculate_ema

SECTOR_ETFS = [
    {
        "symbol": "XLK",
        "name": "Technology Select Sector SPDR",
        "sector": "Technology",
        "price": 245.3,
        "change_percent": 1.24,
        "return_1d": 1.24,
        "return_1w": 3.2,
        "return_mtd": 8.5,
        "return_ytd": 31.4,
        "return_1m": 8.5,
        "relative_strength_score": 92,
        "volume_trend": "Accumulation",
        "status": "Leading",
    },
    {
        "symbol": "XLF",
        "name": "Financial Select Sector SPDR",
        "sector": "Financials",
        "price": 47.85,
        "change_percent": 0.82,
        "return_1d": 0.82,
        "return_1w": 2.4,
        "return_mtd": 5.1,
        "return_ytd": 16.9,
        "return_1m": 5.1,
        "relative_strength_score": 84,
        "volume_trend": "Accumulation",
        "status": "Strong",
    },
    {
        "symbol": "XLV",
        "name": "Health Care Select Sector SPDR",
        "sector": "Healthcare",
        "price": 151.2,
        "change_percent": -0.22,
        "return_1d": -0.22,
        "return_1w": -0.6,
        "return_mtd": 1.2,
        "return_ytd": 4.8,
        "return_1m": 1.2,
        "relative_strength_score": 48,
        "volume_trend": "Distribution",
        "status": "Weak",
    },
    {
        "symbol": "XLY",
        "name": "Consumer Discretionary Select Sector SPDR",
        "sector": "Consumer Discretionary",
        "price": 212.4,
        "change_percent": 0.55,
        "return_1d": 0.55,
        "return_1w": 1.6,
        "return_mtd": 3.4,
        "return_ytd": 15.1,
        "return_1m": 3.4,
        "relative_strength_score": 66,
        "volume_trend": "Neutral",
        "status": "Improving",
    },
    {
        "symbol": "XLP",
        "name": "Consumer Staples Select Sector SPDR",
        "sector": "Consumer Staples",
        "price": 79.15,
        "change_percent": -0.08,
        "return_1d": -0.08,
        "return_1w": 0.4,
        "return_mtd": 1.1,
        "return_ytd": 5.9,
        "return_1m": 1.1,
        "relative_strength_score": 52,
        "volume_trend": "Neutral",
        "status": "Neutral",
    },
    {
        "symbol": "XLE",
        "name": "Energy Select Sector SPDR",
        "sector": "Energy",
        "price": 94.7,
        "change_percent": 0.18,
        "return_1d": 0.18,
        "return_1w": -0.4,
        "return_mtd": 2.2,
        "return_ytd": 9.3,
        "return_1m": 2.2,
        "relative_strength_score": 54,
        "volume_trend": "Neutral",
        "status": "Weak",
    },
    {
        "symbol": "XLI",
        "name": "Industrial Select Sector SPDR",
        "sector": "Industrials",
        "price": 132.6,
        "change_percent": 0.74,
        "return_1d": 0.74,
        "return_1w": 2.2,
        "return_mtd": 4.8,
        "return_ytd": 18.2,
        "return_1m": 4.8,
        "relative_strength_score": 72,
        "volume_trend": "Accumulation",
        "status": "Improving",
    },
    {
        "symbol": "XLU",
        "name": "Utilities Select Sector SPDR",
        "sector": "Utilities",
        "price": 71.45,
        "change_percent": -0.31,
        "return_1d": -0.31,
        "return_1w": -1.2,
        "return_mtd": -0.8,
        "return_ytd": 2.1,
        "return_1m": -0.8,
        "relative_strength_score": 35,
        "volume_trend": "Distribution",
        "status": "Weak",
    },
    {
        "symbol": "XLC",
        "name": "Communication Services Select Sector SPDR",
        "sector": "Communication Services",
        "price": 93.9,
        "change_percent": 0.68,
        "return_1d": 0.68,
        "return_1w": 2.8,
        "return_mtd": 6.2,
        "return_ytd": 23.4,
        "return_1m": 6.2,
        "relative_strength_score": 80,
        "volume_trend": "Accumulation",
        "status": "Strong",
    },
    {
        "symbol": "XLRE",
        "name": "Real Estate Select Sector SPDR",
        "sector": "Real Estate",
        "price": 42.35,
        "change_percent": -0.14,
        "return_1d": -0.14,
        "return_1w": -0.8,
        "return_mtd": 0.2,
        "return_ytd": 1.8,
        "return_1m": 0.2,
        "relative_strength_score": 42,
        "volume_trend": "Distribution",
        "status": "Weak",
    },
    {
        "symbol": "XLB",
        "name": "Materials Select Sector SPDR",
        "sector": "Materials",
        "price": 98.65,
        "change_percent": 0.36,
        "return_1d": 0.36,
        "return_1w": 1.1,
        "return_mtd": 2.6,
        "return_ytd": 8.7,
        "return_1m": 2.6,
        "relative_strength_score": 58,
        "volume_trend": "Neutral",
        "status": "Neutral",
    },
]


def build_sector_etf_dashboard() -> SectorEtfResponse:
    return get_or_compute(
        "sector-etfs",
        get_service_ttl("SERVICE_CACHE_SECTORS_TTL_SECONDS", 900),
        _build_sector_etf_dashboard_uncached,
    )


def _build_sector_etf_dashboard_uncached() -> SectorEtfResponse:
    provider = get_market_data_provider()
    days = int(os.getenv("SECTOR_ROTATION_HISTORY_DAYS", "260"))
    spy_history = safe_get_history(provider, "SPY", days=days)
    spy_return_20d = calculate_return_from_history(spy_history, 20)
    items = [
        build_sector_etf_item(provider, item, spy_return_20d, days)
        for item in get_sector_etfs_for_runtime()
    ]
    leaders = sorted(items, key=lambda item: item.relative_strength_score, reverse=True)[:2]
    coverage_percent = round(
        (sum(1 for item in items if item.history_quality_score and item.history_quality_score >= 60) / len(items)) * 100,
        2,
    ) if items else 0.0
    modes = {get_item_mode(item) for item in items}
    overall_mode = "live" if modes == {"live"} else "mixed" if "live" in modes or "mixed" in modes else "mock"

    return SectorEtfResponse(
        items=items,
        summary=f"{leaders[0].sector} and {leaders[1].sector} are leading sector ETF rotation.",
        overall_mode=overall_mode,
        coverage_percent=coverage_percent,
        as_of=max((item.as_of for item in items if item.as_of), default=None),
    )


def build_sector_etf_item(
    provider: object,
    base_item: dict,
    spy_return_20d: float,
    days: int,
) -> SectorEtfItem:
    symbol = base_item["symbol"]
    quote = safe_get_quote(provider, symbol)
    history = safe_get_history(provider, symbol, days=days)
    validation = validate_history(history, minimum_candles=min(60, days))
    closes = [candle.close for candle in history.candles]
    return_1d = quote.change_percent
    return_1w = calculate_return_from_history(history, 5)
    return_mtd = calculate_mtd_return(history)
    return_ytd = calculate_ytd_return(history)
    return_1m = calculate_return_from_history(history, 21)
    return_3m = calculate_return_from_history(history, 63)
    return_6m = calculate_return_from_history(history, 126)
    return_1y = calculate_return_from_history(history, 252)
    relative_strength_score = calculate_relative_strength_score(return_1m, spy_return_20d)
    ema_20 = calculate_ema(closes, 20)
    ema_50 = calculate_ema(closes, 50)
    trend_quality = calculate_trend_quality(closes, ema_20, ema_50)
    volume_quality = calculate_volume_quality(history)
    rotation_score = calculate_rotation_score(
        relative_strength_score,
        return_1w,
        return_mtd,
        trend_quality,
        volume_quality,
    )

    return SectorEtfItem(
        symbol=symbol,
        name=base_item["name"],
        sector=base_item["sector"],
        price=quote.price,
        change_percent=quote.change_percent,
        return_1d=return_1d,
        return_1w=return_1w,
        return_mtd=return_mtd,
        return_ytd=return_ytd,
        return_1m=return_1m,
        return_3m=return_3m,
        return_6m=return_6m,
        return_1y=return_1y,
        relative_strength_score=relative_strength_score,
        volume_trend=get_volume_trend(volume_quality),
        status=get_status_from_score(rotation_score, return_1w),
        data_source=build_data_source(quote, history),
        quote_source=quote.source,
        history_source=history.source,
        quote_is_live=quote.is_live,
        history_is_live=history.is_live,
        fallback_used=quote.fallback_used or history.fallback_used,
        as_of=max(quote.timestamp, history.as_of),
        history_quality_score=validation.get("quality_score"),
        ema_20=ema_20,
        ema_50=ema_50,
        trend_status=get_trend_status(closes, ema_20, ema_50),
        rotation_score=rotation_score,
    )


def safe_get_quote(provider: object, symbol: str) -> QuoteData:
    try:
        return provider.get_quote(symbol)
    except Exception:
        if is_live_without_mock_fallback():
            return unavailable_quote(symbol)
        return mark_mock_fallback(MockMarketDataProvider().get_quote(symbol))


def safe_get_history(provider: object, symbol: str, days: int) -> HistoryData:
    try:
        return provider.get_history(symbol, resolution="D", days=days)
    except Exception:
        if is_live_without_mock_fallback():
            return unavailable_history(symbol, days)
        return mark_mock_fallback(MockMarketDataProvider().get_history(symbol, resolution="D", days=days))


def get_sector_etfs_for_runtime() -> list[dict]:
    if not is_live_without_mock_fallback():
        return SECTOR_ETFS
    limit = int_env("SECTOR_ETF_LIVE_MAX_SYMBOLS", 4)
    return SECTOR_ETFS[:max(1, min(limit, len(SECTOR_ETFS)))]


def is_live_without_mock_fallback() -> bool:
    provider_mode = (os.getenv("DATA_PROVIDER") or os.getenv("MARKET_DATA_PROVIDER") or "").lower()
    history_provider = (os.getenv("HISTORY_DATA_PROVIDER") or os.getenv("HISTORY_PROVIDER") or "").lower()
    allow_fallback = os.getenv("MARKET_DATA_ALLOW_MOCK_FALLBACK", "true").lower() in {"1", "true", "yes", "on"}
    return not allow_fallback and (provider_mode in {"live", "auto", "finnhub", "polygon", "massive"} or history_provider in {"polygon", "massive"})


def unavailable_quote(symbol: str) -> QuoteData:
    now = datetime.now(timezone.utc).isoformat()
    return QuoteData(
        symbol=symbol,
        price=0.0,
        change=0.0,
        change_percent=0.0,
        open=None,
        high=None,
        low=None,
        previous_close=None,
        volume=None,
        timestamp=now,
        source="unavailable",
        is_live=False,
        is_stale=False,
        fallback_used=False,
        provider="unavailable",
        source_state="unavailable",
        fetched_at=now,
    )


def unavailable_history(symbol: str, days: int) -> HistoryData:
    now = datetime.now(timezone.utc).isoformat()
    return HistoryData(
        symbol=symbol,
        candles=[],
        timeframe="D",
        source="unavailable",
        is_live=False,
        is_stale=False,
        fallback_used=False,
        as_of=now,
        requested_days=days,
        returned_candles=0,
        provider="unavailable",
        source_state="unavailable",
        fetched_at=now,
    )


def int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def calculate_return_from_history(history: HistoryData, lookback: int) -> float:
    closes = [candle.close for candle in history.candles]
    if len(closes) <= lookback or closes[-lookback - 1] == 0:
        return 0.0
    return round(((closes[-1] - closes[-lookback - 1]) / closes[-lookback - 1]) * 100, 2)


def calculate_mtd_return(history: HistoryData) -> float:
    if not history.candles:
        return 0.0

    latest_month = history.candles[-1].timestamp[:7]
    month_start = next(
        (candle for candle in history.candles if candle.timestamp.startswith(latest_month)),
        history.candles[0],
    )
    return calculate_return(history.candles[-1].close, month_start.close)


def calculate_ytd_return(history: HistoryData) -> float:
    if not history.candles:
        return 0.0

    latest_year = history.candles[-1].timestamp[:4]
    year_start = next(
        (candle for candle in history.candles if candle.timestamp.startswith(latest_year)),
        history.candles[0],
    )
    return calculate_return(history.candles[-1].close, year_start.close)


def calculate_return(latest: float, start: float) -> float:
    if start == 0:
        return 0.0
    return round(((latest - start) / start) * 100, 2)


def calculate_relative_strength_score(return_1m: float, spy_return_20d: float) -> int:
    raw_score = 55 + ((return_1m - spy_return_20d) * 3)
    return max(0, min(100, round(raw_score)))


def get_status_from_score(score: int, return_1w: float) -> str:
    if score >= 85:
        return "Leading"
    if score >= 70:
        return "Strong"
    if return_1w > 0 and score >= 55:
        return "Improving"
    if score < 45 or return_1w < 0:
        return "Deteriorating" if return_1w < -1 else "Weak"
    return "Neutral"


def build_data_source(quote: QuoteData, history: HistoryData) -> str:
    if quote.source == history.source:
        return quote.source
    return f"quote:{quote.source};history:{history.source}"


def calculate_trend_quality(closes: list[float], ema_20: float | None, ema_50: float | None) -> int:
    if not closes:
        return 50
    latest = closes[-1]
    score = 45
    if ema_20 is not None and latest > ema_20:
        score += 25
    if ema_50 is not None and latest > ema_50:
        score += 25
    if len(closes) >= 20 and latest > closes[-20]:
        score += 5
    return max(0, min(100, score))


def calculate_volume_quality(history: HistoryData) -> int:
    candles = history.candles
    if len(candles) < 21:
        return 55
    recent_volume = sum(candle.volume for candle in candles[-5:]) / 5
    baseline_volume = sum(candle.volume for candle in candles[-25:-5]) / 20
    if baseline_volume <= 0:
        return 55
    ratio = recent_volume / baseline_volume
    if ratio >= 1.2:
        return 85
    if ratio >= 1.0:
        return 70
    if ratio >= 0.8:
        return 55
    return 40


def calculate_rotation_score(
    relative_strength_score: int,
    return_1w: float,
    return_mtd: float,
    trend_quality: int,
    volume_quality: int,
) -> int:
    weekly_score = normalize_return(return_1w, -5, 8)
    mtd_score = normalize_return(return_mtd, -8, 15)
    return max(
        0,
        min(
            100,
            round(
                (relative_strength_score * 0.30)
                + (weekly_score * 0.20)
                + (mtd_score * 0.20)
                + (trend_quality * 0.15)
                + (volume_quality * 0.15)
            ),
        ),
    )


def normalize_return(value: float, low: float, high: float) -> int:
    if high == low:
        return 50
    return max(0, min(100, round(((value - low) / (high - low)) * 100)))


def get_volume_trend(volume_quality: int) -> str:
    if volume_quality >= 80:
        return "Accumulation"
    if volume_quality >= 55:
        return "Neutral"
    return "Distribution"


def get_trend_status(closes: list[float], ema_20: float | None, ema_50: float | None) -> str:
    if not closes:
        return "Unavailable"
    latest = closes[-1]
    if ema_20 is not None and ema_50 is not None and latest > ema_20 > ema_50:
        return "Above EMA20/EMA50"
    if ema_50 is not None and latest > ema_50:
        return "Above EMA50"
    if ema_50 is not None:
        return "Below EMA50"
    return "Trend unavailable"


def get_item_mode(item: SectorEtfItem) -> str:
    if item.history_is_live and not item.fallback_used:
        return "live"
    if item.history_is_live or item.fallback_used:
        return "mixed"
    return "mock"
