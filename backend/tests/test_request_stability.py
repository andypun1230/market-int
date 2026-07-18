import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from app.cache.persistent_cache import delete_persistent_prefix, set_persistent_value
from app.providers.models import BatchQuoteResult, QuoteData
from app.services.market_detail_aggregates import (
    build_market_institutional_details,
    build_market_structure_details,
)
from app.services.sectors_summary import build_sectors_summary
from app.services.service_cache import invalidate_service_cache
from app.services.watchlist_summary import build_watchlist_summary


def quote(symbol: str, price: float = 100.0, previous_close: float = 95.0) -> QuoteData:
    now = datetime.now(timezone.utc).isoformat()
    return QuoteData(
        symbol=symbol,
        price=price,
        change=999.0,
        change_percent=999.0,
        open=previous_close,
        high=price,
        low=previous_close,
        previous_close=previous_close,
        volume=1000,
        timestamp=now,
        source="fake",
        is_live=True,
        is_stale=False,
        fallback_used=False,
        provider="finnhub",
        source_state="live",
    )


class WatchlistQuoteRepository:
    def __init__(self, quotes: list[QuoteData], unavailable: list[str] | None = None) -> None:
        self.quotes = quotes
        self.unavailable = unavailable or []
        self.quote_calls = 0
        self.history_calls = 0

    def get_batch_quotes(self, symbols: list[str]) -> BatchQuoteResult:
        self.quote_calls += 1
        return BatchQuoteResult(
            quotes=[item for item in self.quotes if item.symbol in symbols],
            unavailable_symbols=self.unavailable,
            provider="finnhub",
            source_state="live" if not self.unavailable else "mixed",
            fetched_at=datetime.now(timezone.utc),
        )

    def get_history(self, *args, **kwargs):
        self.history_calls += 1
        raise AssertionError("watchlist summary must not fetch history")

    def get_provider_name_for(self, domain: str) -> str:
        return "finnhub"


class RequestStabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["BACKGROUND_REFRESH_ENABLED"] = "false"
        invalidate_service_cache()
        delete_persistent_prefix("sectors-summary")
        delete_persistent_prefix("watchlist-summary")
        delete_persistent_prefix("materialized:market-details")

    def tearDown(self) -> None:
        delete_persistent_prefix("sectors-summary")
        delete_persistent_prefix("watchlist-summary")
        delete_persistent_prefix("materialized:market-details")
        invalidate_service_cache()

    def test_sectors_summary_reads_cached_state_without_full_rebuilds(self) -> None:
        with (
            patch(
                "app.services.sectors_summary.get_cached_service_value",
                side_effect=lambda key: {
                    "sectors": {
                        "leaders": [
                            {
                                "name": "Technology",
                                "rank": 1,
                                "status": "Leading",
                                "relative_strength_score": 91,
                            }
                        ],
                        "summary": "Technology leads.",
                        "overall_mode": "mixed",
                    },
                    "sector-etfs": {"items": [{"symbol": "XLK", "sector": "Technology"}]},
                    "industry-groups": {"items": [{"name": "Semiconductors", "parent_sector": "Technology"}]},
                    "industry-rotation": {"summary": "Semiconductors lead."},
                }.get(key),
            ),
            patch("app.services.sectors.build_market_sectors") as sectors,
            patch("app.services.industry_groups.build_industry_groups") as industry_groups,
        ):
            result = build_sectors_summary()

        self.assertEqual(result["top_sectors"][0]["name"], "Technology")
        self.assertEqual(result["top_sector_etfs"][0]["symbol"], "XLK")
        self.assertEqual(result["top_industry_groups"][0]["name"], "Semiconductors")
        sectors.assert_not_called()
        industry_groups.assert_not_called()

    def test_repeated_sectors_summary_uses_service_cache(self) -> None:
        with patch(
            "app.services.sectors_summary._build_sectors_summary_uncached",
            return_value={"top_sectors": [], "top_sector_etfs": [], "top_industry_groups": []},
        ) as compute:
            self.assertEqual(build_sectors_summary()["top_sectors"], [])
            self.assertEqual(build_sectors_summary()["top_sectors"], [])

        self.assertEqual(compute.call_count, 1)

    def test_repeated_watchlist_summary_uses_service_cache(self) -> None:
        with patch(
            "app.services.watchlist_summary._build_watchlist_summary_uncached",
            return_value={"items": [], "summary": "cached"},
        ) as compute:
            self.assertEqual(build_watchlist_summary()["items"], [])
            self.assertEqual(build_watchlist_summary()["items"], [])

        self.assertEqual(compute.call_count, 1)

    def test_watchlist_summary_uses_repository_quotes_and_membership_metadata(self) -> None:
        repository = WatchlistQuoteRepository([quote("MU", 110, 100), quote("NVDA", 95, 100)], unavailable=["ARM", "SNDK"])
        with patch("app.services.watchlist_summary.get_market_data_repository", return_value=repository):
            result = build_watchlist_summary()

        self.assertEqual(repository.quote_calls, 1)
        self.assertEqual(repository.history_calls, 0)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["symbols_requested"], ["MU", "NVDA", "ARM", "SNDK"])
        self.assertEqual(result["symbols_unavailable"], ["ARM", "SNDK"])
        self.assertEqual(result["coverage_ratio"], 0.5)
        self.assertTrue(result["membership_hash"])
        self.assertEqual(result["items"][0]["change_percent"], 10.0)
        self.assertEqual(result["items"][1]["change_percent"], -5.0)
        self.assertIsNone(result["items"][2]["price"])

    def test_warm_watchlist_summary_read_makes_zero_repository_calls(self) -> None:
        repository = WatchlistQuoteRepository([quote(symbol) for symbol in ["MU", "NVDA", "ARM", "SNDK"]])
        with patch("app.services.watchlist_summary.get_market_data_repository", return_value=repository):
            first = build_watchlist_summary()
        self.assertEqual(repository.quote_calls, 1)

        with patch("app.services.watchlist_summary.get_market_data_repository", side_effect=AssertionError("warm read called repository")):
            second = build_watchlist_summary()

        self.assertEqual(first["membership_hash"], second["membership_hash"])
        self.assertEqual(second["symbols_unavailable"], [])

    def test_stale_market_detail_aggregate_returns_without_synchronous_refresh(self) -> None:
        key = "materialized:market-details:structure"
        set_persistent_value(
            key,
            {"breadth": {"market": {"breadth_status": "Cached"}}, "errors": {}},
            ttl_seconds=0,
            stale_seconds=60,
        )

        with patch("app.services.market_detail_aggregates.trigger_background_refresh") as refresh:
            result = build_market_structure_details()

        self.assertEqual(result["cache_status"], "stale")
        self.assertTrue(result["refreshing"])
        self.assertEqual(result["breadth"]["market"]["breadth_status"], "Cached")
        refresh.assert_called_once()

    def test_market_structure_detail_miss_uses_partial_cache_only(self) -> None:
        with (
            patch("app.services.market_detail_aggregates.trigger_background_refresh") as refresh,
            patch("app.services.market_detail_aggregates.calculate_market_breadth") as breadth,
            patch("app.services.market_detail_aggregates.build_institutional_dashboard") as institutional,
        ):
            result = build_market_structure_details()

        self.assertEqual(result["cache_status"], "miss")
        self.assertTrue(result["refreshing"])
        self.assertTrue(result["partial"])
        breadth.assert_not_called()
        institutional.assert_not_called()
        refresh.assert_called_once()

    def test_institutional_detail_miss_does_not_load_market_structure(self) -> None:
        with (
            patch("app.services.market_detail_aggregates.trigger_background_refresh") as refresh,
            patch("app.services.market_detail_aggregates.calculate_market_breadth") as breadth,
            patch("app.services.market_detail_aggregates.build_industry_groups") as industry_groups,
        ):
            result = build_market_institutional_details()

        self.assertEqual(result["cache_status"], "miss")
        self.assertTrue(result["refreshing"])
        self.assertTrue(result["partial"])
        breadth.assert_not_called()
        industry_groups.assert_not_called()
        refresh.assert_called_once()


if __name__ == "__main__":
    unittest.main()
