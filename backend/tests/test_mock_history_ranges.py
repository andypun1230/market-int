import unittest

from app.providers.cache import clear_provider_cache, deserialize_provider_value, get_cached_value, set_cached_value
from app.providers.mock_provider import get_mock_history_candles
from app.providers.models import HistoryData


class MockHistoryRangeTests(unittest.TestCase):
    def test_watchlist_history_extends_long_ranges(self) -> None:
        six_month = get_mock_history_candles("NVDA", 180)
        one_year = get_mock_history_candles("NVDA", 365)

        self.assertEqual(len(six_month), 180)
        self.assertEqual(len(one_year), 365)
        self.assertNotEqual(six_month[0].timestamp, one_year[0].timestamp)
        self.assertEqual(six_month[-1].timestamp, one_year[-1].timestamp)
        self.assertNotEqual(six_month[0].close, one_year[0].close)

    def test_recent_pattern_tail_is_preserved(self) -> None:
        compact = get_mock_history_candles("NVDA", 60)
        extended = get_mock_history_candles("NVDA", 365)

        self.assertEqual(
            [candle.close for candle in compact],
            [candle.close for candle in extended[-60:]],
        )

    def test_underfilled_long_range_cache_is_rejected(self) -> None:
        stale_history = HistoryData(
            symbol="NVDA",
            candles=get_mock_history_candles("NVDA", 60),
            timeframe="D",
            source="mock-fallback",
            is_live=False,
            is_stale=False,
            fallback_used=True,
            as_of="2026-07-12T00:00:00Z",
            requested_days=365,
            returned_candles=60,
        )

        self.assertIsNone(
            deserialize_provider_value("history:NVDA:D:365", stale_history.model_dump()),
        )

    def test_underfilled_l1_history_cache_is_rejected(self) -> None:
        clear_provider_cache()
        stale_history = HistoryData(
            symbol="NVDA",
            candles=get_mock_history_candles("NVDA", 60),
            timeframe="D",
            source="mock-fallback",
            is_live=False,
            is_stale=False,
            fallback_used=True,
            as_of="2026-07-12T00:00:00Z",
            requested_days=365,
            returned_candles=60,
        )

        set_cached_value("history:NVDA:D:365", stale_history, 300)

        self.assertIsNone(get_cached_value("history:NVDA:D:365"))
        clear_provider_cache()


if __name__ == "__main__":
    unittest.main()
