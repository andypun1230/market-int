import time
import unittest

from app.cache.persistent_cache import (
    delete_persistent_prefix,
    get_persistent_value,
    set_persistent_value,
)
from app.providers.cache import _cache as provider_l1_cache
from app.providers.cache import get_cached_value, set_cached_value
from app.providers.models import CandleData, HistoryData


class PersistentCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        delete_persistent_prefix("test:")
        delete_persistent_prefix("history:TEST")
        provider_l1_cache.clear()

    def tearDown(self) -> None:
        delete_persistent_prefix("test:")
        delete_persistent_prefix("history:TEST")
        provider_l1_cache.clear()

    def test_persistent_value_survives_memory_recreation(self) -> None:
        set_persistent_value(
            "test:persistent",
            {"value": 42},
            ttl_seconds=60,
            stale_seconds=60,
            data_source="unit",
        )

        result = get_persistent_value("test:persistent")

        self.assertIsNotNone(result)
        self.assertEqual(result.value, {"value": 42})
        self.assertTrue(result.fresh)

    def test_fresh_persistent_value_returns_immediately(self) -> None:
        set_persistent_value("test:fresh", {"ok": True}, ttl_seconds=60, stale_seconds=60)
        started = time.monotonic()

        result = get_persistent_value("test:fresh")

        self.assertIsNotNone(result)
        self.assertLess(time.monotonic() - started, 0.1)
        self.assertEqual(result.value, {"ok": True})

    def test_provider_daily_history_reads_from_persistent_after_l1_clear(self) -> None:
        history = HistoryData(
            symbol="TEST",
            candles=[
                CandleData(
                    timestamp="2026-07-09T00:00:00+00:00",
                    open=10,
                    high=11,
                    low=9,
                    close=10.5,
                    volume=1000,
                )
            ],
            timeframe="D",
            source="unit-provider",
            is_live=True,
            is_stale=False,
            fallback_used=False,
            as_of="2026-07-09T00:00:00+00:00",
            adjusted=True,
            requested_days=60,
            returned_candles=1,
        )

        set_cached_value("history:TEST:D:60", history, ttl_seconds=60)
        provider_l1_cache.clear()

        restored = get_cached_value("history:TEST:D:60")

        self.assertIsNotNone(restored)
        self.assertEqual(restored.symbol, "TEST")
        self.assertEqual(restored.source, "unit-provider")


if __name__ == "__main__":
    unittest.main()
