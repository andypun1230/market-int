import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from app.providers.cache import clear_provider_cache, get_provider_cache_status, set_cached_value
from app.services.background_refresh import reset_background_refresh_state, submit_background_task
from app.services.history_request_coordinator import reset_history_request_coordinator
from app.services.market_data_repository import reset_market_data_repository
from app.services.service_cache import invalidate_service_cache
from app.snapshots.service import reset_market_snapshot_service
from app.stock_snapshots.service import reset_stock_snapshot_service


class Phase44LiveAwareRotationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="phase44-cache-")
        self.addCleanup(self.tempdir.cleanup)
        temp_path = Path(self.tempdir.name)
        self.env_patcher = patch.dict(os.environ, {
            "DATA_PROVIDER": "mock",
            "MARKET_DATA_PROVIDER": "mock",
            "QUOTE_PROVIDER": "mock",
            "HISTORY_PROVIDER": "mock",
            "QUOTE_DATA_PROVIDER": "mock",
            "HISTORY_DATA_PROVIDER": "mock",
            "BREADTH_MAX_SYMBOLS": "20",
            "BACKGROUND_REFRESH_ENABLED": "false",
            "STARTUP_REFRESH_MODE": "none",
            "PERSISTENT_CACHE_DB_PATH": str(temp_path / "persistent_cache.sqlite3"),
            "MARKET_DATA_CACHE_DB_PATH": str(temp_path / "market_data_cache.sqlite3"),
            "MARKET_DATA_SQLITE_PATH": str(temp_path / "market_data_cache.sqlite3"),
            "MARKET_SNAPSHOT_DB_PATH": str(temp_path / "market_snapshots.sqlite3"),
            "STOCK_SNAPSHOT_DB_PATH": str(temp_path / "stock_snapshots.sqlite3"),
        }, clear=False)
        self.env_patcher.start()
        self.addCleanup(self.env_patcher.stop)
        self.addCleanup(self.reset_shared_process_state)
        self.reset_shared_process_state()

    def reset_shared_process_state(self) -> None:
        reset_background_refresh_state()
        reset_history_request_coordinator()
        reset_market_data_repository()
        reset_market_snapshot_service()
        reset_stock_snapshot_service()
        invalidate_service_cache()
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

    def test_provider_cache_reuse_after_previous_background_writer_is_drained(self) -> None:
        def late_provider_cache_write() -> None:
            time.sleep(0.05)
            set_cached_value("breadth:leaked-background-job", {"status": "late"}, 60)

        with patch.dict(os.environ, {"BACKGROUND_REFRESH_ENABLED": "true"}, clear=False):
            self.assertTrue(submit_background_task("test:late-provider-cache-writer", late_provider_cache_write))

        self.reset_shared_process_state()

        from app.services.basket_data import calculate_basket_breadth

        calculate_basket_breadth(["AAPL", "MSFT"], days=120)
        first_status = get_provider_cache_status()
        calculate_basket_breadth(["AAPL", "MSFT"], days=120)
        second_status = get_provider_cache_status()

        self.assertEqual(first_status["items"], 1)
        self.assertEqual(first_status["items"], second_status["items"])
        self.assertEqual(second_status["keys"], ["basket:AAPL,MSFT:D:120"])


if __name__ == "__main__":
    unittest.main()
