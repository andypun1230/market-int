import threading
import time
import unittest
from datetime import datetime, timedelta, timezone

from app.cache.market_data_cache import LayeredMarketDataCache, SQLiteMarketCache
from app.providers.finnhub_provider import ProviderRequestError
from app.providers.models import CandleData, HistoryData, ProviderCapabilities, ProviderHealth, QuoteData
from app.services.history_request_coordinator import HistoryRequestCoordinator
from app.services.market_data_repository import MarketDataRepository


def provider_health(name: str = "polygon") -> ProviderHealth:
    return ProviderHealth(
        provider=name,
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


def history(symbol: str = "SPY", days: int = 240, source: str = "polygon") -> HistoryData:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    candles = [
        CandleData(
            timestamp=(start + timedelta(days=index)).isoformat(),
            open=100 + index,
            high=101 + index,
            low=99 + index,
            close=100.5 + index,
            volume=1000 + index,
        )
        for index in range(days)
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
        requested_days=days,
        returned_candles=len(candles),
        provider=source,
    )


class CountingHistoryProvider:
    def __init__(self, *, delay: float = 0.0, failures: int = 0) -> None:
        self.delay = delay
        self.failures = failures
        self.history_calls = 0
        self.max_running = 0
        self._running = 0
        self._lock = threading.RLock()

    def get_history(self, symbol: str, resolution: str = "D", days: int = 240) -> HistoryData:
        with self._lock:
            self.history_calls += 1
            self._running += 1
            self.max_running = max(self.max_running, self._running)
        try:
            if self.delay:
                time.sleep(self.delay)
            if self.failures > 0:
                self.failures -= 1
                raise ProviderRequestError("temporary provider failure", category="network")
            return history(symbol, days)
        finally:
            with self._lock:
                self._running -= 1

    def get_quote(self, symbol: str) -> QuoteData:
        raise NotImplementedError

    def get_quotes(self, symbols: list[str]) -> list[QuoteData]:
        return [self.get_quote(symbol) for symbol in symbols]

    def get_provider_health(self) -> ProviderHealth:
        return provider_health()

    def get_capabilities(self) -> ProviderCapabilities:
        return provider_health().capabilities

    def get_index_snapshots(self) -> dict:
        return {}

    def get_sector_etfs(self) -> dict:
        return {}

    def get_watchlist_symbols(self) -> list[str]:
        return []


class HistoryRequestCoordinatorTests(unittest.TestCase):
    def test_identical_history_requests_are_deduplicated(self) -> None:
        coordinator = HistoryRequestCoordinator(max_concurrency=2, max_retries=0, max_queue_wait_seconds=2, base_backoff_seconds=0.01)
        calls = 0
        calls_lock = threading.RLock()
        results: list[HistoryData] = []

        def request() -> HistoryData:
            nonlocal calls
            with calls_lock:
                calls += 1
            time.sleep(0.05)
            return history("SPY", 60)

        threads = [
            threading.Thread(target=lambda: results.append(coordinator.run("polygon:SPY:D:60", request)))
            for _ in range(6)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(calls, 1)
        self.assertEqual(len(results), 6)
        self.assertEqual(coordinator.status()["deduplicated"], 5)

    def test_concurrency_cap_is_applied_across_distinct_keys(self) -> None:
        coordinator = HistoryRequestCoordinator(max_concurrency=2, max_retries=0, max_queue_wait_seconds=3, base_backoff_seconds=0.01)
        running = 0
        max_running = 0
        lock = threading.RLock()

        def request() -> HistoryData:
            nonlocal running, max_running
            with lock:
                running += 1
                max_running = max(max_running, running)
            try:
                time.sleep(0.05)
                return history("SPY", 60)
            finally:
                with lock:
                    running -= 1

        threads = [
            threading.Thread(target=lambda index=index: coordinator.run(f"polygon:SYM{index}:D:60", request))
            for index in range(5)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertLessEqual(max_running, 2)
        self.assertLessEqual(coordinator.status()["max_running"], 2)

    def test_retryable_failure_is_retried(self) -> None:
        coordinator = HistoryRequestCoordinator(max_concurrency=1, max_retries=2, max_queue_wait_seconds=2, base_backoff_seconds=0.01)
        calls = 0

        def request() -> HistoryData:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise ProviderRequestError("try again", category="network")
            return history("SPY", 60)

        result = coordinator.run("polygon:SPY:D:60", request)

        self.assertEqual(result.symbol, "SPY")
        self.assertEqual(calls, 2)
        self.assertEqual(coordinator.status()["retries"], 1)

    def test_repository_uses_large_cached_history_for_smaller_window(self) -> None:
        provider = CountingHistoryProvider()
        cache = LayeredMarketDataCache(persistent_cache=SQLiteMarketCache(":memory:"))
        repo = MarketDataRepository(provider=provider, data_provider="polygon", cache=cache)

        repo.get_history("SPY", days=240)
        smaller = repo.get_history("SPY", days=60)

        self.assertEqual(provider.history_calls, 1)
        self.assertEqual(smaller.source_state, "cached")
        self.assertEqual(smaller.requested_days, 60)
        self.assertLessEqual(len(smaller.candles), 63)

    def test_aliases_share_coordinated_cache_key(self) -> None:
        provider = CountingHistoryProvider()
        cache = LayeredMarketDataCache(persistent_cache=SQLiteMarketCache(":memory:"))
        repo = MarketDataRepository(provider=provider, data_provider="polygon", cache=cache)

        first = repo.get_history("SPX", days=60)
        second = repo.get_history("SPY", days=60)

        self.assertEqual(first.symbol, "SPY")
        self.assertEqual(second.source_state, "cached")
        self.assertEqual(provider.history_calls, 1)

    def test_ndx_and_qqq_equivalent_requests_dedupe_to_qqq(self) -> None:
        provider = CountingHistoryProvider(delay=0.05)
        cache = LayeredMarketDataCache(persistent_cache=SQLiteMarketCache(":memory:"))
        repo = MarketDataRepository(provider=provider, data_provider="polygon", cache=cache)
        results: list[HistoryData] = []

        threads = [
            threading.Thread(target=lambda symbol=symbol: results.append(repo.get_history(symbol, days=60)))
            for symbol in ("NDX", "QQQ")
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(provider.history_calls, 1)
        self.assertEqual({result.symbol for result in results}, {"QQQ"})
        self.assertEqual({result.provider_symbol for result in results}, {"QQQ"})
        self.assertEqual({result.requested_symbol for result in results}, {"NDX", "QQQ"})


if __name__ == "__main__":
    unittest.main()
