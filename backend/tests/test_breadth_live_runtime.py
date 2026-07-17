import os
import unittest
from unittest.mock import patch

from app.services.breadth import get_breadth_universe_symbols
from app.services.candle_data import get_symbol_history
from app.services.sector_etfs import get_sector_etfs_for_runtime, safe_get_history


class BreadthLiveRuntimeTests(unittest.TestCase):
    def test_live_no_mock_mode_uses_smaller_default_universe(self) -> None:
        env = {
            "DATA_PROVIDER": "live",
            "HISTORY_DATA_PROVIDER": "polygon",
            "MARKET_DATA_ALLOW_MOCK_FALLBACK": "false",
        }
        with patch.dict(os.environ, env, clear=False):
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("BREADTH_MAX_SYMBOLS", None)
                symbols = get_breadth_universe_symbols()

        self.assertEqual(len(symbols), 15)

    def test_explicit_breadth_max_symbols_still_wins(self) -> None:
        env = {
            "DATA_PROVIDER": "live",
            "HISTORY_DATA_PROVIDER": "polygon",
            "MARKET_DATA_ALLOW_MOCK_FALLBACK": "false",
            "BREADTH_MAX_SYMBOLS": "6",
        }
        with patch.dict(os.environ, env, clear=False):
            symbols = get_breadth_universe_symbols()

        self.assertEqual(len(symbols), 6)

    def test_live_no_mock_mode_caps_sector_etfs(self) -> None:
        env = {
            "DATA_PROVIDER": "live",
            "HISTORY_DATA_PROVIDER": "polygon",
            "MARKET_DATA_ALLOW_MOCK_FALLBACK": "false",
        }
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("SECTOR_ETF_LIVE_MAX_SYMBOLS", None)
            items = get_sector_etfs_for_runtime()

        self.assertEqual(len(items), 4)

    def test_live_no_mock_sector_history_failure_is_unavailable_not_mock(self) -> None:
        class FailingProvider:
            def get_history(self, symbol: str, resolution: str = "D", days: int = 240):
                raise RuntimeError("down")

        env = {
            "DATA_PROVIDER": "live",
            "HISTORY_DATA_PROVIDER": "polygon",
            "MARKET_DATA_ALLOW_MOCK_FALLBACK": "false",
        }
        with patch.dict(os.environ, env, clear=False):
            result = safe_get_history(FailingProvider(), "XLK", days=60)

        self.assertEqual(result.source_state, "unavailable")
        self.assertFalse(result.fallback_used)
        self.assertEqual(result.returned_candles, 0)

    def test_service_history_dependency_failure_returns_unavailable_history(self) -> None:
        class FailingProvider:
            def get_history(self, symbol: str, resolution: str = "D", days: int = 240):
                raise RuntimeError("down")

        with patch("app.services.candle_data.get_market_data_provider", return_value=FailingProvider()):
            history, validation = get_symbol_history("IWM", days=60)

        self.assertEqual(history.source_state, "unavailable")
        self.assertFalse(history.fallback_used)
        self.assertFalse(validation["valid"])


if __name__ == "__main__":
    unittest.main()
