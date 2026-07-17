from datetime import datetime, timedelta, timezone
from typing import Any

from app.providers.base import MarketDataProvider
from app.providers.models import CandleData, HistoryData, ProviderCapabilities, ProviderHealth, QuoteData
from app.services.pattern_detection import WATCHLIST_SYMBOLS, get_mock_candles

INDEX_ALIASES = {
    "DIA": "DJI",
}
MOCK_INDEX_CONFIG = {
    "SPY": {"start": 548.4, "drift": 0.35, "cycle": 0.42, "volume": 58_200_000},
    "QQQ": {"start": 481.2, "drift": 0.38, "cycle": 0.55, "volume": 41_700_000},
    "IWM": {"start": 207.9, "drift": 0.08, "cycle": 0.22, "volume": 28_600_000},
    "DJI": {"start": 40544.6, "drift": 16.8, "cycle": 21.0, "volume": 344_000_000},
}
MOCK_SECTOR_ETF_PRICES = {
    "XLK": 245.3,
    "XLF": 47.85,
    "XLV": 151.2,
    "XLY": 212.4,
    "XLP": 79.15,
    "XLE": 94.7,
    "XLI": 132.6,
    "XLU": 71.45,
    "XLC": 93.9,
    "XLRE": 42.35,
    "XLB": 98.65,
}


class MockMarketDataProvider(MarketDataProvider):
    """Adapter around the current deterministic mock engines."""

    def get_quote(self, symbol: str) -> QuoteData:
        normalized_symbol = symbol.upper()
        history = self.get_history(normalized_symbol, days=2)
        latest = history.candles[-1] if history.candles else None
        previous = history.candles[-2] if len(history.candles) > 1 else latest

        if latest is None:
            raise ValueError(f"No mock quote data available for {normalized_symbol}")

        previous_close = previous.close if previous else latest.close
        change = round(latest.close - previous_close, 2)
        change_percent = round((change / previous_close) * 100, 2) if previous_close else 0.0

        return QuoteData(
            symbol=normalized_symbol,
            price=latest.close,
            change=change,
            change_percent=change_percent,
            open=latest.open,
            high=latest.high,
            low=latest.low,
            previous_close=previous_close,
            volume=latest.volume,
            timestamp=latest.timestamp,
            source="mock",
            is_live=False,
            is_stale=False,
            fallback_used=False,
        )

    def get_history(
        self,
        symbol: str,
        resolution: str = "D",
        days: int = 240,
    ) -> HistoryData:
        normalized_symbol = symbol.upper()
        candles = get_mock_history_candles(normalized_symbol, days)

        if not candles:
            raise ValueError(f"No mock history data available for {normalized_symbol}")

        return HistoryData(
            symbol=normalized_symbol,
            candles=candles,
            timeframe=resolution,
            source="mock",
            is_live=False,
            is_stale=False,
            fallback_used=False,
            as_of=now_iso(),
            adjusted=True,
            requested_days=days,
            returned_candles=len(candles),
            error_message=None,
        )

    def get_provider_health(self) -> ProviderHealth:
        return ProviderHealth(
            provider="mock",
            enabled=True,
            configured=True,
            reachable=True,
            last_successful_request=now_iso(),
            last_error=None,
            fallback_active=False,
            capabilities=self.get_capabilities(),
        )

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            quotes=True,
            daily_history=True,
            intraday_history=False,
            adjusted_history=True,
            volume=True,
        )

    def get_index_snapshots(self) -> dict[str, Any]:
        return {"indexes": [serialize_model(self.get_quote(symbol)) for symbol in ["SPY", "QQQ", "IWM", "DIA"]]}

    def get_sector_etfs(self) -> dict[str, Any]:
        return {
            "items": [
                serialize_model(self.get_quote(symbol))
                for symbol in MOCK_SECTOR_ETF_PRICES
            ],
            "summary": "Mock sector ETF quotes are available through the mock provider.",
        }

    def get_watchlist_symbols(self) -> list[str]:
        return list(WATCHLIST_SYMBOLS)


def get_mock_history_candles(symbol: str, days: int) -> list[CandleData]:
    watchlist_candles = get_mock_candles(symbol)
    if watchlist_candles:
        extended_candles = extend_watchlist_mock_candles(symbol, watchlist_candles, days)
        return [
            CandleData(
                timestamp=normalize_daily_timestamp(candle["date"]),
                open=float(candle["open"]),
                high=float(candle["high"]),
                low=float(candle["low"]),
                close=float(candle["close"]),
                volume=float(candle["volume"]),
            )
            for candle in extended_candles[-days:]
        ]

    index_symbol = INDEX_ALIASES.get(symbol, symbol)
    if index_symbol in MOCK_INDEX_CONFIG:
        closes = generate_mock_index_closes(index_symbol)
        if symbol == "DIA":
            closes = [round(close / 100, 2) for close in closes]
        return candles_from_closes(symbol, closes[-days:], base_volume=get_base_volume(symbol))

    if symbol in MOCK_SECTOR_ETF_PRICES:
        closes = generate_synthetic_closes(MOCK_SECTOR_ETF_PRICES[symbol], days)
        return candles_from_closes(symbol, closes, base_volume=12_000_000)

    closes = generate_synthetic_closes(get_symbol_seed_price(symbol), days)
    return candles_from_closes(symbol, closes, base_volume=5_000_000)


def candles_from_closes(symbol: str, closes: list[float], base_volume: int) -> list[CandleData]:
    start = datetime.now(timezone.utc).date() - timedelta(days=len(closes) - 1)
    candles: list[CandleData] = []

    for index, close in enumerate(closes):
        previous_close = closes[index - 1] if index else close * 0.997
        open_price = previous_close
        high = max(open_price, close) * 1.004
        low = min(open_price, close) * 0.996
        volume = base_volume + ((index % 7) * 175_000)
        candles.append(
            CandleData(
                timestamp=f"{(start + timedelta(days=index)).isoformat()}T00:00:00+00:00",
                open=round(open_price, 2),
                high=round(high, 2),
                low=round(low, 2),
                close=round(close, 2),
                volume=float(volume),
            )
        )

    return candles


def extend_watchlist_mock_candles(
    symbol: str,
    candles: list[dict[str, Any]],
    days: int,
) -> list[dict[str, Any]]:
    """Prepend deterministic history so 6M and 1Y chart ranges are distinct.

    Pattern detection intentionally uses its own compact example candles. The
    market-data provider needs a longer, deterministic OHLCV series for charting
    and long-range indicators, so we preserve the pattern candles as the recent
    tail and synthesize only the older context.
    """
    if days <= len(candles):
        return candles[-days:]

    missing_days = days - len(candles)
    first = candles[0]
    first_date = datetime.fromisoformat(str(first["date"])).date()
    first_open = float(first["open"])
    seed = sum(ord(character) for character in symbol.upper())
    history_depth_discount = min(missing_days, 365) * 0.00035
    start_close = first_open * max(0.45, 0.72 + (seed % 9) * 0.015 - history_depth_discount)
    prior_candles: list[dict[str, Any]] = []

    for index in range(missing_days):
        progress = index / max(missing_days - 1, 1)
        date = first_date - timedelta(days=missing_days - index)
        trend_close = start_close + (first_open * 0.985 - start_close) * progress
        cycle = ((index % 13) - 6) * first_open * 0.0018
        close = round(max(1, trend_close + cycle), 2)
        previous_close = prior_candles[-1]["close"] if prior_candles else close * 0.996
        open_price = round(float(previous_close), 2)
        high = round(max(open_price, close) * 1.006, 2)
        low = round(min(open_price, close) * 0.994, 2)
        volume = int(float(first["volume"]) * (0.72 + ((index + seed) % 11) * 0.025))
        prior_candles.append({
            "date": date.isoformat(),
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        })

    return prior_candles + candles


def generate_synthetic_closes(anchor_price: float, days: int) -> list[float]:
    start = anchor_price * 0.88
    return [
        round(start + (index * anchor_price * 0.0017) + (((index % 9) - 4) * anchor_price * 0.0009), 2)
        for index in range(days)
    ]


def generate_mock_index_closes(symbol: str, days: int = 240) -> list[float]:
    config = MOCK_INDEX_CONFIG[symbol]
    closes: list[float] = []

    for day in range(days):
        wave = ((day % 9) - 4) * config["cycle"]
        close = config["start"] + (day * config["drift"]) + wave
        closes.append(round(close, 2))

    return closes


def get_symbol_seed_price(symbol: str) -> float:
    seed = sum(ord(character) for character in symbol)
    return round(40 + (seed % 220), 2)


def get_base_volume(symbol: str) -> int:
    volumes = {
        "SPY": 58_200_000,
        "QQQ": 41_700_000,
        "IWM": 28_600_000,
        "DJI": 344_000_000,
        "DIA": 7_800_000,
    }
    return volumes.get(symbol, 5_000_000)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_daily_timestamp(value: str) -> str:
    if "T" in value:
        return value
    return f"{value}T00:00:00+00:00"


def serialize_model(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()

    if hasattr(value, "dict"):
        return value.dict()

    return dict(value)
