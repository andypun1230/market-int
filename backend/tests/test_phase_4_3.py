import os
import unittest

from app.providers.history_validation import validate_history
from app.providers.models import CandleData, HistoryData
from app.providers.selector import get_market_data_provider
from app.services.relative_strength import build_relative_strength
from app.services.stock_rating import build_stock_ratings
from app.services.technical_indicators import (
    calculate_atr_from_candles,
    calculate_ema,
    calculate_rsi,
)


class Phase43Tests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["DATA_PROVIDER"] = "test"

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


if __name__ == "__main__":
    unittest.main()
