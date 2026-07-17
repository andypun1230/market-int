import unittest

from app.providers.test_provider import TEST_DATA_SOURCE, GeneratedTestMarketDataProvider
from app.test_data.repository import get_test_data_state, regenerate_test_data


class GeneratedTestDataTests(unittest.TestCase):
    def tearDown(self) -> None:
        regenerate_test_data(scenario="balanced_market", seed="test-market-001")

    def test_provider_returns_generated_test_quote_metadata(self) -> None:
        regenerate_test_data(scenario="balanced_market", seed="unit-test-a")
        quote = GeneratedTestMarketDataProvider().get_quote("MU")

        self.assertEqual(quote.source, TEST_DATA_SOURCE)
        self.assertFalse(quote.is_live)
        self.assertFalse(quote.fallback_used)
        self.assertGreater(quote.price, 0)

    def test_provider_returns_generated_test_history_metadata(self) -> None:
        regenerate_test_data(scenario="risk_on", seed="unit-test-b")
        history = GeneratedTestMarketDataProvider().get_history("NVDA", days=60)

        self.assertEqual(history.source, TEST_DATA_SOURCE)
        self.assertFalse(history.is_live)
        self.assertFalse(history.fallback_used)
        self.assertEqual(history.returned_candles, len(history.candles))
        self.assertGreaterEqual(len(history.candles), 60)

    def test_regeneration_changes_seeded_history(self) -> None:
        provider = GeneratedTestMarketDataProvider()
        regenerate_test_data(scenario="rotation", seed="unit-test-c")
        first = provider.get_history("SPY", days=20).candles[-1].close

        regenerate_test_data(scenario="rotation", seed="unit-test-d")
        second = provider.get_history("SPY", days=20).candles[-1].close

        self.assertNotEqual(first, second)
        self.assertEqual(get_test_data_state().seed, "unit-test-d")


if __name__ == "__main__":
    unittest.main()
