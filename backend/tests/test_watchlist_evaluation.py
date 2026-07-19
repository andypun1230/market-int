from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.providers.models import QuoteData
from app.services.watchlist_summary import _build_watchlist_summary_uncached, build_dependency_signature, build_watchlist_evaluation
from app.stock_snapshots.builder import StockAnalysisSnapshotBuilder
from app.stock_snapshots.models import StockAnalysisSnapshot, StockSnapshotSection


def quote(symbol: str) -> QuoteData:
    now = datetime.now(timezone.utc).isoformat()
    return QuoteData(
        symbol=symbol,
        price=100.0,
        change=2.0,
        change_percent=2.04,
        open=98.0,
        high=101.0,
        low=97.0,
        previous_close=98.0,
        volume=1000,
        timestamp=now,
        source="finnhub",
        provider="finnhub",
        source_state="live",
        is_live=True,
        is_stale=False,
        fallback_used=False,
    )


def snapshot(
    symbol: str,
    *,
    snapshot_id: str = "stock-AAPL-v1",
    status: str = "complete",
    expires_at: str | None = None,
    optional_unavailable: bool = False,
) -> StockAnalysisSnapshot:
    now = datetime.now(timezone.utc)
    sections = {
        "chart": StockSnapshotSection(status="complete", calculated_at=now.isoformat(), payload={"history": {}}),
        "rating": StockSnapshotSection(status="complete", calculated_at=now.isoformat(), payload={"overall_score": 74, "status": "Constructive"}),
        "risk": StockSnapshotSection(status="complete", calculated_at=now.isoformat(), payload={"risk_level": "Managed"}),
        "trend": StockSnapshotSection(status="complete", calculated_at=now.isoformat(), payload={"summary": "Holding support"}),
        "signals": StockSnapshotSection(
            status="unavailable" if optional_unavailable else "complete",
            calculated_at=now.isoformat(),
            payload=None if optional_unavailable else {"short": {"headline": "Constructive", "confidence": 72}},
        ),
    }
    return StockAnalysisSnapshot(
        snapshot_id=snapshot_id,
        symbol=symbol,
        created_at=now.isoformat(),
        published_at=now.isoformat(),
        expires_at=expires_at or (now + timedelta(minutes=15)).isoformat(),
        stale_until=(now + timedelta(days=1)).isoformat(),
        status=status,  # type: ignore[arg-type]
        source_state="live",
        data_mode="live",
        input_hash="input",
        coverage_ratio=1.0,
        sections=sections,
    )


class _Storage:
    def __init__(self) -> None:
        self.published: StockAnalysisSnapshot | None = None

    def publish_snapshot(self, value: StockAnalysisSnapshot) -> None:
        self.published = value

    def set_build_error(self, _symbol: str, _error: str) -> None:
        raise AssertionError("compatible snapshot should not set a build error")


class _Repository:
    def __init__(self, timestamp: str) -> None:
        self.timestamp = timestamp

    def get_provider_name_for(self, _domain: str) -> str:
        return "finnhub"


class WatchlistEvaluationTests(unittest.TestCase):
    def test_complete_snapshot_and_live_quote_are_complete(self) -> None:
        evaluation = build_watchlist_evaluation("AAPL", quote("AAPL"), snapshot("AAPL"), False)
        self.assertEqual(evaluation["overall_status"], "complete")
        self.assertEqual(evaluation["analysis_snapshot_id"], "stock-AAPL-v1")
        self.assertEqual(evaluation["quote_price"], 100.0)
        self.assertEqual(evaluation["status_reason_code"], None)
        self.assertIsNone(evaluation["next_action"])

    def test_partial_snapshot_keeps_quote_and_reason(self) -> None:
        evaluation = build_watchlist_evaluation(
            "MSFT",
            quote("MSFT"),
            snapshot("MSFT", status="partial", optional_unavailable=True),
            False,
        )
        self.assertEqual(evaluation["overall_status"], "partial")
        self.assertEqual(evaluation["status_reason_code"], "optional_metrics_missing")
        self.assertEqual(evaluation["quote_price"], 100.0)
        self.assertIn("signals", evaluation["missing_fields"])
        self.assertIn("refresh", evaluation["next_action"].lower())

    def test_pending_quote_is_not_marked_unavailable(self) -> None:
        evaluation = build_watchlist_evaluation("MSFT", quote("MSFT"), None, True)
        self.assertEqual(evaluation["overall_status"], "pending")
        self.assertEqual(evaluation["status_reason_code"], "snapshot_building")
        self.assertEqual(evaluation["quote_price"], 100.0)
        self.assertIn("scheduled", evaluation["next_action"].lower())

    def test_expired_requested_snapshot_is_refreshed_in_the_background(self) -> None:
        expired = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        with patch("app.services.watchlist_summary.get_market_data_repository"), patch(
            "app.services.watchlist_summary.get_stock_snapshot_service"
        ) as snapshot_service:
            service = snapshot_service.return_value
            service.get_latest_snapshot.return_value = snapshot("AAPL", expires_at=expired)
            service.is_refreshing.return_value = True
            with patch("app.services.watchlist_summary.fetch_quotes_by_symbol", return_value={"AAPL": quote("AAPL")}):
                result = _build_watchlist_summary_uncached(
                    ["AAPL"],
                    refresh_missing_symbols={"AAPL"},
                    dependency_signature="test",
                )
        service.trigger_background_refresh.assert_called_once_with("AAPL")
        self.assertEqual(result["items"][0]["overall_status"], "stale")
        self.assertTrue(result["items"][0]["refreshing"])

    def test_stale_compatible_snapshot_is_stale_not_unavailable(self) -> None:
        expired = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        evaluation = build_watchlist_evaluation("AAPL", quote("AAPL"), snapshot("AAPL", expires_at=expired), True)
        self.assertEqual(evaluation["overall_status"], "stale")
        self.assertEqual(evaluation["status_reason_code"], "stale_last_known_good")

    def test_no_quote_and_no_snapshot_is_explicitly_unavailable(self) -> None:
        evaluation = build_watchlist_evaluation("BAD", None, None, False)
        self.assertEqual(evaluation["overall_status"], "unavailable")
        self.assertEqual(evaluation["status_reason_code"], "quote_unavailable")

    def test_dependency_signature_changes_when_a_snapshot_publishes(self) -> None:
        repository = _Repository(datetime.now(timezone.utc).isoformat())
        before = build_dependency_signature(repository, ["AAPL"], {"AAPL": None})
        after = build_dependency_signature(repository, ["AAPL"], {"AAPL": snapshot("AAPL", snapshot_id="stock-AAPL-v2")})
        self.assertNotEqual(before, after)

    def test_snapshot_publish_invalidates_watchlist_summary_cache(self) -> None:
        storage = _Storage()
        builder = StockAnalysisSnapshotBuilder(storage)  # type: ignore[arg-type]
        published = snapshot("AAPL")
        with patch.object(builder.planner, "plan", return_value=type("Plan", (), {"symbol": "AAPL"})()), patch.object(
            builder, "build", return_value=published
        ), patch("app.stock_snapshots.builder.is_snapshot_compatible", return_value=(True, None)), patch(
            "app.services.service_cache.invalidate_service_cache"
        ) as invalidate:
            result = builder.build_and_publish("AAPL")
        self.assertEqual(result, published)
        self.assertEqual(storage.published, published)
        invalidate.assert_called_once_with("watchlist-summary:v2")


if __name__ == "__main__":
    unittest.main()
