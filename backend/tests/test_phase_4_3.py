import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.providers.history_validation import validate_history
from app.providers.base import MarketDataProvider
from app.providers.finnhub_provider import ProviderRequestError
from app.providers.models import CandleData, HistoryData, ProviderCapabilities, ProviderHealth, QuoteData
from app.providers.polygon_provider import (
    PolygonMarketDataProvider,
    normalize_polygon_aggregates,
    normalize_polygon_symbol,
    polygon_timestamp,
    redact_url,
)
from app.providers.router import MarketDataProviderRouter
from app.providers.selector import get_market_data_provider
from app.cache.market_data_cache import LayeredMarketDataCache, SQLiteMarketCache
from app.services.market_data_repository import MarketDataRepository
from app.services.relative_strength import build_relative_strength
from app.services.stock_rating import build_stock_ratings
from app.services.technical_indicators import (
    calculate_atr_from_candles,
    calculate_ema,
    calculate_rsi,
)


class FakeHTTPResponse:
    status = 200

    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None


class PolygonHTTPStub:
    def __init__(self, payloads: list[dict]) -> None:
        self.payloads = list(payloads)
        self.urls: list[str] = []

    def __call__(self, request, timeout=None, context=None):
        self.urls.append(request.full_url)
        payload = self.payloads.pop(0)
        return FakeHTTPResponse(payload)


def polygon_payload(symbol: str = "SPY", *, next_url: str | None = None) -> dict:
    payload = {
        "ticker": symbol,
        "adjusted": True,
        "status": "OK",
        "resultsCount": 3,
        "results": [
            {"t": 1704153600000, "o": 100, "h": 102, "l": 99, "c": 101, "v": 1000, "vw": 100.5, "n": 10},
            {"t": 1704240000000, "o": 101, "h": 103, "l": 100, "c": 102, "v": 0},
            {"t": 1704240000000, "o": 101, "h": 103, "l": 100, "c": 102, "v": 0},
        ],
    }
    if next_url:
        payload["next_url"] = next_url
    return payload


def provider_health(name: str, capabilities: ProviderCapabilities) -> ProviderHealth:
    return ProviderHealth(
        provider=name,
        enabled=True,
        configured=True,
        reachable=True,
        last_successful_request=None,
        last_error=None,
        fallback_active=False,
        capabilities=capabilities,
    )


class HistoryTrapFinnhubProvider(MarketDataProvider):
    def __init__(self) -> None:
        self.quote_calls = 0
        self.history_calls = 0

    def get_quote(self, symbol: str) -> QuoteData:
        self.quote_calls += 1
        return QuoteData(
            symbol=symbol.upper(),
            price=100.0,
            change=1.0,
            change_percent=1.0,
            open=99.0,
            high=101.0,
            low=98.0,
            previous_close=99.0,
            volume=1_000_000,
            timestamp="2026-07-17T00:00:00+00:00",
            source="finnhub",
            is_live=True,
            is_stale=False,
            fallback_used=False,
            provider="finnhub",
            source_state="live",
        )

    def get_history(self, symbol: str, resolution: str = "D", days: int = 240) -> HistoryData:
        self.history_calls += 1
        raise ProviderRequestError("Finnhub history must not be used by stock analysis.", category="test")

    def get_provider_health(self) -> ProviderHealth:
        return provider_health("finnhub", self.get_capabilities())

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            quotes=True,
            daily_history=False,
            intraday_history=False,
            adjusted_history=False,
            volume=False,
        )

    def get_index_snapshots(self) -> dict:
        return {}

    def get_sector_etfs(self) -> dict:
        return {}

    def get_watchlist_symbols(self) -> list[str]:
        return ["MU", "NVDA", "ARM", "SNDK"]


class PolygonHistoryFixtureProvider(MarketDataProvider):
    def __init__(self, unavailable_symbols: set[str] | None = None) -> None:
        self.history_calls: list[str] = []
        self.quote_calls = 0
        self.unavailable_symbols = {symbol.upper() for symbol in unavailable_symbols or set()}

    def get_quote(self, symbol: str) -> QuoteData:
        self.quote_calls += 1
        raise ProviderRequestError("Polygon quote path is not part of this regression.", category="test")

    def get_history(self, symbol: str, resolution: str = "D", days: int = 240) -> HistoryData:
        normalized = symbol.upper()
        safe_days = max(1, min(days, 1500))
        self.history_calls.append(normalized)
        if normalized in self.unavailable_symbols:
            raise ProviderRequestError(f"No fixture history for {normalized}", category="no_data")
        base = 80.0 + (sum(ord(char) for char in normalized) % 40)
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        candles = [
            CandleData(
                timestamp=(start + timedelta(days=index)).isoformat(),
                open=base + index * 0.4,
                high=base + index * 0.4 + 2.0,
                low=base + index * 0.4 - 1.5,
                close=base + index * 0.5,
                volume=1_000_000 + index * 1_000,
            )
            for index in range(safe_days)
        ]
        return HistoryData(
            symbol=normalized,
            candles=candles,
            timeframe=resolution,
            source="polygon",
            is_live=True,
            is_stale=False,
            fallback_used=False,
            as_of=candles[-1].timestamp,
            adjusted=True,
            requested_days=safe_days,
            returned_candles=len(candles),
            provider="polygon",
            source_state="live",
        )

    def get_provider_health(self) -> ProviderHealth:
        return provider_health("polygon", self.get_capabilities())

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            quotes=False,
            daily_history=True,
            intraday_history=False,
            adjusted_history=True,
            volume=True,
        )

    def get_index_snapshots(self) -> dict:
        return {}

    def get_sector_etfs(self) -> dict:
        return {}

    def get_watchlist_symbols(self) -> list[str]:
        return ["MU", "NVDA", "ARM", "SNDK"]


class Phase43Tests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["DATA_PROVIDER"] = "test"
        os.environ["MARKET_DATA_PROVIDER"] = "test"
        os.environ["QUOTE_DATA_PROVIDER"] = "test"
        os.environ["HISTORY_DATA_PROVIDER"] = "test"
        os.environ["MARKET_DATA_ALLOW_MOCK_FALLBACK"] = "true"
        from app.services.market_data_repository import reset_market_data_repository
        from app.services.service_cache import invalidate_service_cache
        from app.services.history_request_coordinator import reset_history_request_coordinator

        reset_history_request_coordinator()
        reset_market_data_repository()
        invalidate_service_cache("relative-strength")
        invalidate_service_cache("stock-ratings")

    def test_history_validation_accepts_ordered_candles(self) -> None:
        history = HistoryData(
            symbol="TEST",
            candles=[
                CandleData(
                    timestamp=f"2026-07-{day:02d}T00:00:00+00:00",
                    open=100 + day,
                    high=102 + day,
                    low=99 + day,
                    close=101 + day,
                    volume=1_000_000,
                )
                for day in range(1, 6)
            ],
            timeframe="D",
            source="fixture",
            is_live=False,
            is_stale=False,
            fallback_used=False,
            as_of="2026-07-10T00:00:00+00:00",
            adjusted=True,
            requested_days=5,
            returned_candles=5,
        )

        result = validate_history(history, minimum_candles=5)

        self.assertTrue(result["valid"])
        self.assertGreaterEqual(result["quality_score"], 80)

    def test_indicator_math(self) -> None:
        values = [float(value) for value in range(1, 31)]
        candles = [
            {"high": value + 1, "low": value - 1, "close": value}
            for value in values
        ]

        self.assertIsNotNone(calculate_ema(values, 20))
        self.assertEqual(calculate_rsi(values, 14), 100.0)
        self.assertIsNotNone(calculate_atr_from_candles(candles, 14))

    def test_selected_provider_metadata(self) -> None:
        quote = get_market_data_provider().get_quote("MU")
        history = get_market_data_provider().get_history("MU", days=60)

        self.assertEqual(quote.source, "generated_test_data")
        self.assertFalse(quote.is_live)
        self.assertEqual(history.source, "generated_test_data")
        self.assertEqual(history.returned_candles, 60)

    def test_relative_strength_ranking(self) -> None:
        response = build_relative_strength()

        self.assertEqual(len(response.items), 4)
        self.assertEqual(response.items[0].rank, 1)
        self.assertIsNotNone(response.items[0].data_source)

    def test_stock_rating_source_mode(self) -> None:
        response = build_stock_ratings()

        self.assertEqual(len(response.items), 4)
        self.assertIn(response.items[0].data_quality["overall_mode"], {"mock", "mixed", "live"})

    def test_polygon_symbol_and_timestamp_normalization(self) -> None:
        self.assertEqual(normalize_polygon_symbol("brk-b"), "BRK.B")
        self.assertEqual(normalize_polygon_symbol("NDX"), "QQQ")
        self.assertEqual(normalize_polygon_symbol("SPX"), "SPY")
        self.assertEqual(normalize_polygon_symbol("IXIC"), "QQQ")
        self.assertEqual(normalize_polygon_symbol("RUT"), "IWM")
        self.assertEqual(normalize_polygon_symbol("DJI"), "DIA")
        self.assertEqual(polygon_timestamp(1704153600000).tzinfo.utcoffset(None).total_seconds(), 0)

    def test_polygon_request_formation_and_normalization(self) -> None:
        stub = PolygonHTTPStub([polygon_payload("AAPL")])
        provider = PolygonMarketDataProvider(api_key="test-key", base_url="https://api.polygon.io", max_retries=0)

        with patch("app.providers.polygon_provider.urlopen", side_effect=stub):
            history = provider.get_history("aapl", days=2)

        self.assertEqual(history.provider, "polygon")
        self.assertEqual(history.source_state, "live")
        self.assertTrue(history.adjusted)
        self.assertEqual(history.returned_candles, 2)
        self.assertIn("/v2/aggs/ticker/AAPL/range/1/day/", stub.urls[0])
        self.assertIn("adjusted=true", stub.urls[0])
        self.assertIn("sort=asc", stub.urls[0])
        self.assertIn("apiKey=test-key", stub.urls[0])
        self.assertEqual(history.candles[0].volume, 1000)
        self.assertEqual(history.candles[0].vwap, 100.5)
        self.assertEqual(history.candles[0].transactions, 10)

    def test_polygon_ndx_history_uses_qqq_ticker(self) -> None:
        stub = PolygonHTTPStub([polygon_payload("QQQ")])
        provider = PolygonMarketDataProvider(api_key="test-key", base_url="https://api.polygon.io", max_retries=0)

        with patch("app.providers.polygon_provider.urlopen", side_effect=stub):
            history = provider.get_history("NDX", days=2)

        self.assertEqual(history.symbol, "QQQ")
        self.assertIn("/v2/aggs/ticker/QQQ/range/1/day/", stub.urls[0])
        self.assertNotIn("/ticker/NDX/", stub.urls[0])

    def test_polygon_redacts_api_key(self) -> None:
        self.assertNotIn("secret", redact_url("https://api.polygon.io/v2/aggs?apiKey=secret&limit=1"))

    def test_polygon_normalization_skips_malformed_and_deduplicates(self) -> None:
        bars = normalize_polygon_aggregates(
            [
                {
                    "results": [
                        {"t": 1704153600000, "o": 100, "h": 101, "l": 99, "c": 100.5, "v": 10},
                        {"t": 1704153600000, "o": 100, "h": 101, "l": 99, "c": 100.5, "v": 10},
                        {"t": 1704240000000, "o": 100, "h": 99, "l": 98, "c": 100, "v": 10},
                        {"t": 1704326400000, "o": 101, "h": 102, "l": 100, "c": 101, "v": 0},
                    ],
                }
            ],
            requested_days=10,
        )

        self.assertEqual(len(bars), 2)
        self.assertEqual(bars[-1].volume, 0)
        self.assertLess(bars[0].timestamp, bars[1].timestamp)

    def test_polygon_all_malformed_fails_controlled(self) -> None:
        provider = PolygonMarketDataProvider(api_key="test-key", base_url="https://api.polygon.io", max_retries=0)
        stub = PolygonHTTPStub([{"status": "OK", "results": [{"t": 1, "o": -1, "h": 1, "l": 1, "c": 1, "v": 1}]}])

        with patch("app.providers.polygon_provider.urlopen", side_effect=stub):
            with self.assertRaises(Exception):
                provider.get_history("SPY", days=10)

    def test_polygon_pagination_attaches_key_and_deduplicates(self) -> None:
        first = polygon_payload("SPY", next_url="https://api.polygon.io/v2/aggs/ticker/SPY/range/1/day/2024-01-01/2024-01-05?cursor=abc")
        second = {
            "ticker": "SPY",
            "adjusted": True,
            "status": "OK",
            "results": [{"t": 1704326400000, "o": 102, "h": 104, "l": 101, "c": 103, "v": 2000}],
        }
        stub = PolygonHTTPStub([first, second])
        provider = PolygonMarketDataProvider(api_key="test-key", base_url="https://api.polygon.io", max_retries=0)

        with patch("app.providers.polygon_provider.urlopen", side_effect=stub):
            history = provider.get_history("SPY", days=10)

        self.assertEqual(len(stub.urls), 2)
        self.assertIn("apiKey=test-key", stub.urls[1])
        self.assertEqual(history.returned_candles, 3)

    def test_router_sends_history_to_polygon_and_quotes_to_finnhub(self) -> None:
        with patch.dict(
            os.environ,
            {
                "QUOTE_DATA_PROVIDER": "finnhub",
                "HISTORY_DATA_PROVIDER": "polygon",
                "POLYGON_API_KEY": "configured",
            },
            clear=False,
        ):
            router = MarketDataProviderRouter()
            self.assertEqual(router.get_provider_name_for("quotes"), "finnhub")
            self.assertEqual(router.get_provider_name_for("daily_history"), "polygon")
            self.assertEqual(router.capability_registry.get_capability("polygon").daily_history_access_state, "available")

    def test_stock_analysis_uses_polygon_history_when_quotes_are_finnhub(self) -> None:
        from app.services.market_data_repository import reset_market_data_repository
        from app.services.service_cache import invalidate_service_cache
        from app.services.stock_analysis_aggregate import build_stock_analysis

        finnhub = HistoryTrapFinnhubProvider()
        polygon = PolygonHistoryFixtureProvider()

        def build_provider(name: str):
            normalized = name.lower()
            if normalized == "finnhub":
                return finnhub
            if normalized in {"polygon", "massive"}:
                return polygon
            raise AssertionError(f"Unexpected provider requested: {name}")

        with patch.dict(
            os.environ,
            {
                "DATA_PROVIDER": "finnhub",
                "MARKET_DATA_PROVIDER": "finnhub",
                "QUOTE_DATA_PROVIDER": "finnhub",
                "HISTORY_DATA_PROVIDER": "polygon",
                "POLYGON_API_KEY": "configured",
                "FINNHUB_API_KEY": "configured",
                "MARKET_DATA_ALLOW_MOCK_FALLBACK": "false",
                "MARKET_DATA_CACHE_ENABLED": "false",
            },
            clear=False,
        ), patch("app.providers.selector.build_provider", side_effect=build_provider), patch(
            "app.services.stock_rating.calculate_sector_strength", return_value=82
        ), patch(
            "app.services.stock_rating.build_market_regime",
            return_value=SimpleNamespace(status="Confirmed Uptrend"),
        ), patch(
            "app.services.stock_rating.calculate_institutional_bias",
            return_value=SimpleNamespace(bias="Bullish"),
        ), patch(
            "app.services.stock_analysis_aggregate.analyze_symbol_options",
            return_value={"symbol": "NVDA", "source": "fixture"},
        ), patch(
            "app.services.stock_analysis_aggregate.analyze_symbol_liquidity",
            return_value={"symbol": "NVDA", "source": "fixture"},
        ):
            reset_market_data_repository()
            invalidate_service_cache("stock-ratings")
            invalidate_service_cache("relative-strength")
            result = build_stock_analysis("NVDA")

        self.assertEqual(finnhub.history_calls, 0)
        self.assertGreater(polygon.history_calls.count("NVDA"), 0)
        self.assertIn("SPY", polygon.history_calls)
        self.assertIn("QQQ", polygon.history_calls)
        self.assertIsNotNone(result["supportResistance"])
        self.assertIsNotNone(result["trendline"])
        self.assertIsNotNone(result["volumeAnalysis"])
        self.assertIsNotNone(result["riskPlan"])
        self.assertIsNotNone(result["relativeStrength"])
        self.assertIsNotNone(result["stockRating"])
        self.assertIsNotNone(result["multiTimeframeSignals"])
        self.assertNotIn("relativeStrength", result["errors"])
        self.assertNotIn("stockRating", result["errors"])

    def test_sndk_stock_analysis_keeps_core_sections_when_secondary_benchmark_history_is_unavailable(self) -> None:
        from app.services.market_data_repository import reset_market_data_repository
        from app.services.service_cache import invalidate_service_cache
        from app.services.stock_analysis_aggregate import build_stock_analysis

        finnhub = HistoryTrapFinnhubProvider()
        polygon = PolygonHistoryFixtureProvider(unavailable_symbols={"XLK"})

        def build_provider(name: str):
            normalized = name.lower()
            if normalized == "finnhub":
                return finnhub
            if normalized in {"polygon", "massive"}:
                return polygon
            raise AssertionError(f"Unexpected provider requested: {name}")

        with patch.dict(
            os.environ,
            {
                "DATA_PROVIDER": "finnhub",
                "MARKET_DATA_PROVIDER": "finnhub",
                "QUOTE_DATA_PROVIDER": "finnhub",
                "HISTORY_DATA_PROVIDER": "polygon",
                "POLYGON_API_KEY": "configured",
                "FINNHUB_API_KEY": "configured",
                "MARKET_DATA_ALLOW_MOCK_FALLBACK": "false",
                "MARKET_DATA_CACHE_ENABLED": "false",
            },
            clear=False,
        ), patch("app.providers.selector.build_provider", side_effect=build_provider), patch(
            "app.services.stock_rating.calculate_sector_strength",
            side_effect=RuntimeError("sector rotation unavailable"),
        ), patch(
            "app.services.stock_rating.build_market_regime",
            return_value=SimpleNamespace(status="Confirmed Uptrend"),
        ), patch(
            "app.services.stock_rating.calculate_institutional_bias",
            return_value=SimpleNamespace(bias="Bullish"),
        ), patch(
            "app.services.stock_analysis_aggregate.analyze_symbol_options",
            return_value={"symbol": "SNDK", "source": "fixture"},
        ), patch(
            "app.services.stock_analysis_aggregate.analyze_symbol_liquidity",
            return_value={"symbol": "SNDK", "source": "fixture"},
        ):
            reset_market_data_repository()
            invalidate_service_cache("stock-ratings")
            invalidate_service_cache("relative-strength")
            result = build_stock_analysis("SNDK")

        self.assertEqual(finnhub.history_calls, 0)
        self.assertGreater(polygon.history_calls.count("SNDK"), 0)
        self.assertIn("XLK", polygon.history_calls)
        self.assertIsNotNone(result["supportResistance"])
        self.assertIsNotNone(result["trendline"])
        self.assertIsNotNone(result["volumeAnalysis"])
        self.assertIsNotNone(result["riskPlan"])
        self.assertIsNotNone(result["relativeStrength"])
        self.assertIsNotNone(result["stockRating"])
        self.assertIsNotNone(result["multiTimeframeSignals"])
        self.assertIsNotNone(result["leadershipSignal"])
        self.assertNotIn("relativeStrength", result["errors"])
        self.assertNotIn("stockRating", result["errors"])
        self.assertEqual(result["relativeStrength"]["rs_vs_sector"], 50)

    def test_polygon_cache_keys_are_provider_isolated(self) -> None:
        stub = PolygonHTTPStub([polygon_payload("SPY")])
        provider = PolygonMarketDataProvider(api_key="test-key", base_url="https://api.polygon.io", max_retries=0)
        with tempfile.TemporaryDirectory() as tmp:
            cache = LayeredMarketDataCache(persistent_cache=SQLiteMarketCache(Path(tmp) / "cache.sqlite3"))
            repo = MarketDataRepository(provider=provider, data_provider="polygon", cache=cache)
            with patch("app.providers.polygon_provider.urlopen", side_effect=stub):
                first = repo.get_history("SPY", days=2)
                second = repo.get_history("SPY", days=2)

        self.assertEqual(first.provider, "polygon")
        self.assertEqual(second.source_state, "cached")
        self.assertEqual(len(stub.urls), 1)


if __name__ == "__main__":
    unittest.main()
