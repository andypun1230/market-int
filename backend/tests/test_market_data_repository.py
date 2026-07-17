import os
import threading
import time
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from app.providers.finnhub_provider import normalize_finnhub_candles
from app.providers.models import CandleData, HistoryData, ProviderCapabilities, ProviderHealth, QuoteData
from app.providers.symbols import normalize_market_symbol
from app.services.market_data_repository import MarketDataRepository, MemoryMarketDataCache


def health(provider: str = "fake") -> ProviderHealth:
    return ProviderHealth(
        provider=provider,
        enabled=True,
        configured=True,
        reachable=True,
        last_successful_request=None,
        last_error=None,
        fallback_active=False,
        capabilities=ProviderCapabilities(
            quotes=True,
            daily_history=True,
            intraday_history=False,
            adjusted_history=True,
            volume=True,
        ),
    )


def quote(symbol: str = "SPY", source: str = "fake") -> QuoteData:
    return QuoteData(
        symbol=symbol,
        price=100.0,
        change=1.0,
        change_percent=1.0,
        open=99.0,
        high=101.0,
        low=98.0,
        previous_close=99.0,
        volume=1000,
        timestamp=datetime.now(timezone.utc).isoformat(),
        source=source,
        is_live=True,
        is_stale=False,
        fallback_used=False,
    )


def history_data(symbol: str = "SPY", source: str = "fake") -> HistoryData:
    candles = [
        CandleData(
            timestamp=f"2026-01-{day:02d}T00:00:00+00:00",
            open=100 + day,
            high=101 + day,
            low=99 + day,
            close=100.5 + day,
            volume=1000,
        )
        for day in range(1, 6)
    ]
    return HistoryData(
        symbol=symbol,
        candles=candles,
        timeframe="D",
        source=source,
        is_live=True,
        is_stale=False,
        fallback_used=False,
        as_of=datetime.now(timezone.utc).isoformat(),
        requested_days=5,
        returned_candles=5,
    )


class FakeProvider:
    def __init__(self, fail: bool = False, delay: float = 0.0) -> None:
        self.fail = fail
        self.delay = delay
        self.quote_calls = 0
        self.history_calls = 0

    def get_quote(self, symbol: str) -> QuoteData:
        self.quote_calls += 1
        if self.delay:
            time.sleep(self.delay)
        if self.fail:
            raise RuntimeError("provider down")
        return quote(symbol)

    def get_quotes(self, symbols: list[str]) -> list[QuoteData]:
        return [self.get_quote(symbol) for symbol in symbols]

    def get_history(self, symbol: str, resolution: str = "D", days: int = 240) -> HistoryData:
        self.history_calls += 1
        if self.fail:
            raise RuntimeError("provider down")
        return history_data(symbol)

    def get_provider_health(self) -> ProviderHealth:
        return health()

    def get_capabilities(self) -> ProviderCapabilities:
        return health().capabilities

    def get_index_snapshots(self) -> dict:
        return {}

    def get_sector_etfs(self) -> dict:
        return {}

    def get_watchlist_symbols(self) -> list[str]:
        return []


class MarketDataRepositoryTests(unittest.TestCase):
    def test_symbol_normalization(self) -> None:
        self.assertEqual(normalize_market_symbol(" spy "), "SPY")
        self.assertEqual(normalize_market_symbol("DJI", apply_alias=True), "DIA")
        with self.assertRaises(ValueError):
            normalize_market_symbol("")

    def test_cache_hit_does_not_refetch_quote(self) -> None:
        provider = FakeProvider()
        repo = MarketDataRepository(provider=provider, data_provider="fake", cache=MemoryMarketDataCache())

        first = repo.get_quote("SPY")
        second = repo.get_quote("SPY")

        self.assertEqual(provider.quote_calls, 1)
        self.assertEqual(first.source_state, "live")
        self.assertEqual(second.source_state, "cached")
        self.assertTrue(second.cache_hit)

    def test_ttl_expiry_refetches(self) -> None:
        provider = FakeProvider()
        repo = MarketDataRepository(provider=provider, data_provider="fake", cache=MemoryMarketDataCache())
        repo.quote_ttl_seconds = 1

        repo.get_quote("SPY")
        time.sleep(1.05)
        repo.get_quote("SPY")

        self.assertEqual(provider.quote_calls, 2)

    def test_inflight_request_deduplicates_identical_quote(self) -> None:
        provider = FakeProvider(delay=0.05)
        repo = MarketDataRepository(provider=provider, data_provider="fake", cache=MemoryMarketDataCache())
        results: list[QuoteData] = []

        threads = [threading.Thread(target=lambda: results.append(repo.get_quote("SPY"))) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(provider.quote_calls, 1)
        self.assertEqual(len(results), 5)

    def test_mock_fallback_is_explicit(self) -> None:
        provider = FakeProvider(fail=True)
        repo = MarketDataRepository(provider=provider, data_provider="finnhub", cache=MemoryMarketDataCache())
        repo.allow_mock_fallback = True

        result = repo.get_quote("SPY")

        self.assertEqual(result.source_state, "mock")
        self.assertEqual(result.source, "mock-fallback")
        self.assertTrue(result.fallback_used)
        self.assertEqual(result.fallback_reason, "RuntimeError")

    def test_fallback_disabled_raises_controlled_error(self) -> None:
        provider = FakeProvider(fail=True)
        repo = MarketDataRepository(provider=provider, data_provider="finnhub", cache=MemoryMarketDataCache())
        repo.allow_mock_fallback = False

        with self.assertRaises(Exception):
            repo.get_quote("SPY")

    def test_history_cache_hit(self) -> None:
        provider = FakeProvider()
        repo = MarketDataRepository(provider=provider, data_provider="fake", cache=MemoryMarketDataCache())

        repo.get_history("SPY", days=5)
        cached = repo.get_history("SPY", days=5)

        self.assertEqual(provider.history_calls, 1)
        self.assertEqual(cached.source_state, "cached")

    def test_finnhub_candle_normalization_sorts_and_deduplicates(self) -> None:
        payload = {
            "s": "ok",
            "t": [1_704_067_200, 1_704_153_600, 1_704_067_200],
            "o": [10, 11, 10],
            "h": [12, 13, 12],
            "l": [9, 10, 9],
            "c": [11, 12, 11],
            "v": [100, 200, 100],
        }

        bars = normalize_finnhub_candles(payload, 10)

        self.assertEqual(len(bars), 2)
        self.assertLess(bars[0].timestamp, bars[1].timestamp)

    def test_no_live_provider_during_tests_by_default(self) -> None:
        with patch.dict(os.environ, {"DATA_PROVIDER": "test"}, clear=False):
            repo = MarketDataRepository(data_provider=os.environ["DATA_PROVIDER"])
            self.assertEqual(repo.get_provider_health().provider, "generated_test_data")


if __name__ == "__main__":
    unittest.main()
