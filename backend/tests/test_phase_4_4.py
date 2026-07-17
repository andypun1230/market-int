import os
import unittest

from app.providers.cache import clear_provider_cache, get_provider_cache_status


class Phase44LiveAwareRotationTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["DATA_PROVIDER"] = "mock"
        os.environ["QUOTE_PROVIDER"] = "mock"
        os.environ["HISTORY_PROVIDER"] = "mock"
        os.environ["BREADTH_MAX_SYMBOLS"] = "20"
        clear_provider_cache()

    def test_basket_coverage_metadata(self) -> None:
        from app.services.basket_data import calculate_basket_breadth

        result = calculate_basket_breadth(["AAPL", "MSFT", "NVDA"], days=120)
        metadata = result["metadata"]

        self.assertEqual(metadata["requested_symbols"], 3)
        self.assertEqual(metadata["successful_symbols"], 3)
        self.assertEqual(metadata["coverage_percent"], 100.0)
        self.assertEqual(metadata["overall_mode"], "mock")

    def test_breadth_uses_configured_core_universe(self) -> None:
        from app.services.breadth import calculate_market_breadth

        breadth = calculate_market_breadth()

        self.assertEqual(breadth.universe, "core")
        self.assertEqual(breadth.universe_size, 20)
        self.assertGreaterEqual(breadth.coverage_percent or 0, 80)
        self.assertIn(breadth.overall_mode, {"mock", "mixed", "live"})

    def test_industry_groups_include_basket_metadata(self) -> None:
        from app.services.industry_groups import build_industry_groups

        response = build_industry_groups()

        self.assertTrue(response.items)
        self.assertIsNotNone(response.items[0].coverage_percent)
        self.assertIsNotNone(response.items[0].trend_direction)
        self.assertIn(response.overall_mode, {"mock", "mixed", "live"})

    def test_leadership_categories_use_history_windows(self) -> None:
        from app.services.leadership import build_leadership_dashboard

        response = build_leadership_dashboard()
        categories = {category.category for category in response.categories}

        self.assertIn("Current Leaders", categories)
        self.assertIsNotNone(response.coverage_percent)
        self.assertIn(response.overall_mode, {"mock", "mixed", "live"})

    def test_provider_cache_reuse(self) -> None:
        from app.services.basket_data import calculate_basket_breadth

        calculate_basket_breadth(["AAPL", "MSFT"], days=120)
        first_status = get_provider_cache_status()
        calculate_basket_breadth(["AAPL", "MSFT"], days=120)
        second_status = get_provider_cache_status()

        self.assertEqual(first_status["items"], second_status["items"])


if __name__ == "__main__":
    unittest.main()
