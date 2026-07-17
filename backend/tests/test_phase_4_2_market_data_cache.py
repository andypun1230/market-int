import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from app.cache.market_data_cache import (
    CachePolicy,
    CachePolicyRegistry,
    CacheWriteMetadata,
    LayeredMarketDataCache,
    SQLiteMarketCache,
    build_history_cache_key,
)
from app.providers.finnhub_provider import ProviderRequestError
from app.providers.models import CandleData, HistoryData, ProviderCapabilities, ProviderHealth, QuoteData
from app.providers.router import MarketDataProviderRouter, ProviderCapabilityRegistry, is_stable_permission_error
from app.services.market_data_repository import MarketDataRepository


def quote(symbol: str = "SPY", source: str = "fake") -> QuoteData:
    return QuoteData(
        symbol=symbol,
        price=100,
        change=1,
        change_percent=1,
        open=99,
        high=101,
        low=98,
        previous_close=99,
        volume=1000,
        timestamp=datetime.now(timezone.utc).isoformat(),
        source=source,
        is_live=source not in {"mock", "generated_test_data"},
        is_stale=False,
        fallback_used=False,
    )


def history(symbol: str = "SPY", source: str = "fake", days: int = 10) -> HistoryData:
    candles = [
        CandleData(
            timestamp=f"2026-01-{index + 1:02d}T00:00:00+00:00",
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
        is_live=source not in {"mock", "generated_test_data"},
        is_stale=False,
        fallback_used=False,
        as_of=datetime.now(timezone.utc).isoformat(),
        requested_days=days,
        returned_candles=days,
    )


def provider_health(provider: str = "fake") -> ProviderHealth:
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


class CountingProvider:
    def __init__(self, provider: str = "fake", fail_history: bool = False) -> None:
        self.provider = provider
        self.fail_history = fail_history
        self.quote_calls = 0
        self.history_calls = 0

    def get_quote(self, symbol: str) -> QuoteData:
        self.quote_calls += 1
        return quote(symbol, self.provider)

    def get_quotes(self, symbols: list[str]) -> list[QuoteData]:
        return [self.get_quote(symbol) for symbol in symbols]

    def get_history(self, symbol: str, resolution: str = "D", days: int = 240) -> HistoryData:
        self.history_calls += 1
        if self.fail_history:
            raise RuntimeError("history provider unavailable")
        return history(symbol, self.provider, days=min(days, 20))

    def get_provider_health(self) -> ProviderHealth:
        return provider_health(self.provider)

    def get_capabilities(self) -> ProviderCapabilities:
        return provider_health(self.provider).capabilities

    def get_index_snapshots(self) -> dict:
        return {}

    def get_sector_etfs(self) -> dict:
        return {}

    def get_watchlist_symbols(self) -> list[str]:
        return []


class TinyPolicyRegistry(CachePolicyRegistry):
    def for_domain(self, domain: str) -> CachePolicy:
        if domain == "daily_history":
            return CachePolicy(
                memory_ttl_seconds=1,
                persistent_ttl_seconds=1,
                stale_while_revalidate_seconds=60,
                allow_stale_on_error=True,
                persist=True,
                negative_ttl_seconds=1,
                max_entries=None,
                schema_version=1,
            )
        return super().for_domain(domain)


class Phase42MarketDataCacheTests(unittest.TestCase):
    def make_cache(self, path: Path, policy_registry: CachePolicyRegistry | None = None) -> LayeredMarketDataCache:
        return LayeredMarketDataCache(
            persistent_cache=SQLiteMarketCache(path),
            policy_registry=policy_registry or CachePolicyRegistry(),
        )

    def test_persistent_cache_survives_repository_recreation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "market_cache.sqlite3"
            provider = CountingProvider()
            first_repo = MarketDataRepository(provider=provider, data_provider="fake", cache=self.make_cache(db_path))

            first_repo.get_history("SPY", days=10)
            second_repo = MarketDataRepository(provider=provider, data_provider="fake", cache=self.make_cache(db_path))
            cached = second_repo.get_history("SPY", days=10)

            self.assertEqual(provider.history_calls, 1)
            self.assertEqual(cached.source_state, "cached")
            self.assertTrue(cached.persistent_cache_hit)

    def test_stale_history_returns_and_refreshes_in_background(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "market_cache.sqlite3"
            provider = CountingProvider()
            cache = self.make_cache(db_path, TinyPolicyRegistry())
            key = build_history_cache_key("fake", "SPY", "D", 10)
            cache.set(
                key,
                history("SPY", "fake", 10),
                domain="daily_history",
                provider="fake",
                source_state="live",
            )
            time.sleep(1.1)
            repo = MarketDataRepository(provider=provider, data_provider="fake", cache=cache)

            stale = repo.get_history("SPY", days=10)
            time.sleep(0.2)

            self.assertEqual(stale.source_state, "stale")
            self.assertTrue(stale.is_stale)
            self.assertTrue(stale.background_refresh_started)
            self.assertEqual(provider.history_calls, 1)

    def test_failed_refresh_keeps_stale_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "market_cache.sqlite3"
            cache = self.make_cache(db_path, TinyPolicyRegistry())
            key = build_history_cache_key("fake", "SPY", "D", 10)
            cache.set(
                key,
                history("SPY", "fake", 10),
                domain="daily_history",
                provider="fake",
                source_state="live",
            )
            time.sleep(1.1)
            repo = MarketDataRepository(provider=CountingProvider(fail_history=True), data_provider="fake", cache=cache)

            stale = repo.get_history("SPY", days=10)
            time.sleep(0.2)

            self.assertEqual(stale.source_state, "stale")
            self.assertTrue(stale.is_stale)
            self.assertEqual(repo.background_refresh_failure_count, 1)

    def test_repeated_stale_memory_hit_remains_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "market_cache.sqlite3"
            cache = self.make_cache(db_path, TinyPolicyRegistry())
            key = build_history_cache_key("fake", "SPY", "D", 10)
            cache.set(
                key,
                history("SPY", "fake", 10),
                domain="daily_history",
                provider="fake",
                source_state="live",
            )
            time.sleep(1.1)
            repo = MarketDataRepository(provider=CountingProvider(fail_history=True), data_provider="fake", cache=cache)

            first = repo.get_history("SPY", days=10)
            second = repo.get_history("SPY", days=10)

            self.assertEqual(first.source_state, "stale")
            self.assertEqual(second.source_state, "stale")
            self.assertTrue(second.is_stale)

    def test_provider_router_uses_finnhub_quotes_and_mock_history(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "DATA_PROVIDER": "finnhub",
                "QUOTE_DATA_PROVIDER": "finnhub",
                "HISTORY_DATA_PROVIDER": "mock",
            },
            clear=False,
        ):
            router = MarketDataProviderRouter()

            self.assertEqual(router.get_provider_name_for("quotes"), "finnhub")
            self.assertEqual(router.get_provider_name_for("daily_history"), "mock")
            self.assertEqual(router.capability_registry.get_capability("finnhub").daily_history_access_state, "restricted")

    def test_restricted_finnhub_history_is_controlled(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "HISTORY_DATA_PROVIDER": "finnhub",
            },
            clear=False,
        ):
            router = MarketDataProviderRouter(capability_registry=ProviderCapabilityRegistry())

            with self.assertRaises(ProviderRequestError) as context:
                router.get_provider_for("daily_history")

            self.assertEqual(context.exception.category, "permission")

    def test_authentication_error_is_not_capability_restriction(self) -> None:
        self.assertFalse(is_stable_permission_error(ProviderRequestError("bad key", category="authentication")))

    def test_prefix_invalidation_reports_deleted_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "market_cache.sqlite3"
            cache = self.make_cache(db_path)
            key = build_history_cache_key("fake", "SPY", "D", 10)
            cache.set(
                key,
                history("SPY", "fake", 10),
                domain="daily_history",
                provider="fake",
                source_state="live",
            )

            deleted = cache.invalidate("history:fake:SPY")

            self.assertGreaterEqual(deleted, 1)

    def test_one_repository_history_request_feeds_indicator_consumers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "market_cache.sqlite3"
            provider = CountingProvider()
            repo = MarketDataRepository(provider=provider, data_provider="fake", cache=self.make_cache(db_path))

            repo.get_history("SPY", days=20)
            repo.get_history("SPY", days=20)

            self.assertEqual(provider.history_calls, 1)


if __name__ == "__main__":
    unittest.main()
