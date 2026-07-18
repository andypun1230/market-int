import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from app.providers.models import BatchQuoteResult, QuoteData
from app.providers.circuit_breaker import (
    is_circuit_open,
    record_provider_failure,
    record_provider_success,
)
from app.services.background_refresh import queue_refresh
from app.services.market_core_snapshot import build_market_core_snapshot
from app.services.materialized_market_state import update_market_state_component
from app.services.stock_analysis_aggregate import build_stock_analysis
from app.services.watchlist_summary import build_watchlist_summary
from app.services.service_cache import invalidate_service_cache


def quote(symbol: str) -> QuoteData:
    now = datetime.now(timezone.utc).isoformat()
    return QuoteData(
        symbol=symbol,
        price=1,
        change=0,
        change_percent=0,
        open=1,
        high=1,
        low=1,
        previous_close=1,
        volume=1,
        timestamp=now,
        source="unit",
        is_live=False,
        is_stale=False,
        fallback_used=False,
        provider="unit",
        source_state="cached",
    )


class QuoteRepository:
    def get_batch_quotes(self, symbols: list[str]) -> BatchQuoteResult:
        return BatchQuoteResult(
            quotes=[quote(symbol) for symbol in symbols],
            unavailable_symbols=[],
            provider="unit",
            source_state="cached",
            fetched_at=datetime.now(timezone.utc),
        )

    def get_provider_name_for(self, domain: str) -> str:
        return "unit"


class HardPerformanceTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["BACKGROUND_REFRESH_ENABLED"] = "true"
        os.environ["STARTUP_REFRESH_MODE"] = "light"
        invalidate_service_cache()

    def test_light_refresh_queues_only_tier1(self) -> None:
        with patch("app.services.background_refresh.submit_background_task", return_value=True) as submit:
            result = queue_refresh("light")

        self.assertEqual(result["queued"], ["refresh:tier1-quotes"])
        self.assertEqual(submit.call_args.args[0], "refresh:tier1-quotes")

    def test_full_refresh_can_queue_heavy_diagnostics(self) -> None:
        with patch("app.services.background_refresh.submit_background_task", return_value=True):
            result = queue_refresh("full")

        self.assertIn("refresh:tier1-quotes", result["queued"])
        self.assertIn("refresh:breadth", result["queued"])
        self.assertIn("refresh:institutional-intelligence", result["queued"])

    def test_core_endpoint_does_not_call_full_breadth_on_miss(self) -> None:
        with (
            patch("app.services.market_core_snapshot.queue_refresh", return_value={"queued": []}),
            patch("app.services.breadth.calculate_market_breadth") as breadth,
        ):
            snapshot = build_market_core_snapshot()

        self.assertTrue(snapshot["bootstrap"])
        breadth.assert_not_called()

    def test_materialized_component_update_does_not_rebuild_unrelated_components(self) -> None:
        state = update_market_state_component("quote_summary", {"items": []}, {"overall_mode": "live"})

        self.assertEqual(state["quote_summary"], {"items": []})
        self.assertIsNone(state["breadth_summary"])
        self.assertIsNone(state["institutional_summary"])

    def test_circuit_breaker_opens_after_repeated_failures(self) -> None:
        provider = "unit-provider"
        record_provider_success(provider)
        for _ in range(3):
            record_provider_failure(provider, RuntimeError("timeout"))

        self.assertTrue(is_circuit_open(provider))

    def test_watchlist_summary_avoids_full_stock_detail_services(self) -> None:
        with (
            patch("app.services.watchlist_summary.get_market_data_repository", return_value=QuoteRepository()),
            patch("app.services.support_resistance.calculate_support_resistance") as support,
        ):
            result = build_watchlist_summary()

        self.assertIn("items", result)
        support.assert_not_called()

    def test_stock_analysis_aggregate_returns_partial_on_component_failure(self) -> None:
        with patch(
            "app.services.stock_analysis_aggregate.calculate_support_resistance",
            side_effect=RuntimeError("boom"),
        ), patch("app.services.stock_analysis_aggregate.analyze_trendline", return_value={"symbol": "MU"}), patch(
            "app.services.stock_analysis_aggregate.analyze_volume", return_value={"symbol": "MU"}
        ), patch("app.services.stock_analysis_aggregate.calculate_risk_plan", return_value={"symbol": "MU"}), patch(
            "app.services.stock_analysis_aggregate.analyze_multi_timeframe", return_value={"symbol": "MU"}
        ), patch("app.services.stock_analysis_aggregate.detect_patterns", return_value={"patterns": []}), patch(
            "app.services.stock_analysis_aggregate.calculate_rs_score", return_value={"symbol": "MU"}
        ), patch("app.services.stock_analysis_aggregate.calculate_stock_rating", return_value={"symbol": "MU"}), patch(
            "app.services.stock_analysis_aggregate.analyze_symbol_options", return_value={"symbol": "MU"}
        ), patch("app.services.stock_analysis_aggregate.analyze_symbol_liquidity", return_value={"symbol": "MU"}):
            result = build_stock_analysis("MU")

        self.assertTrue(result["partial"])
        self.assertIn("supportResistance", result["errors"])


if __name__ == "__main__":
    unittest.main()
