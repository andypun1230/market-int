import os
from argparse import Namespace
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.providers.models import CandleData, HistoryData, ProviderCapabilities, ProviderHealth, QuoteData
from app.stock_snapshots.input_planner import StockDetailInputPlanner
from app.stock_snapshots.readers import aggregate_payload
from app.stock_snapshots.service import StockSnapshotService
from app.stock_snapshots.storage import StockSnapshotStorage
from scripts.validate_application_data import configure_environment


def make_history(symbol: str, days: int = 450, source: str = "test", *, stale: bool = False) -> HistoryData:
    candles = [
        CandleData(
            timestamp=(datetime(2025, 1, 1, tzinfo=timezone.utc) + timedelta(days=index)).isoformat(),
            open=100 + index * 0.2,
            high=101 + index * 0.2,
            low=99 + index * 0.2,
            close=100 + index * 0.2,
            volume=1_000_000 + index * 1000,
        )
        for index in range(days)
    ]
    return HistoryData(
        symbol=symbol,
        candles=candles,
        timeframe="D",
        source=source,
        is_live=not stale,
        is_stale=stale,
        fallback_used=False,
        as_of=candles[-1].timestamp,
        requested_days=days,
        returned_candles=days,
        provider=source,
        source_state="stale" if stale else "live",
    )


def make_quote(symbol: str, source: str = "test") -> QuoteData:
    return QuoteData(
        symbol=symbol,
        price=180.0,
        change=1.5,
        change_percent=0.84,
        open=178.0,
        high=181.0,
        low=177.0,
        previous_close=178.5,
        volume=2_000_000,
        timestamp=datetime.now(timezone.utc).isoformat(),
        source=source,
        is_live=True,
        is_stale=False,
        fallback_used=False,
        provider=source,
        source_state="live",
    )


class FakeHistoryCache:
    def __init__(self, histories: dict[str, HistoryData] | None = None) -> None:
        self.histories = histories or {}

    def find_history_covering(self, provider: str, symbol: str, resolution: str, days: int):
        history = self.histories.get(symbol)
        if history is None:
            return None, None, None
        return history, 1, f"history:{provider}:{symbol}:{resolution}:{days}"


class FakeProvider:
    def __init__(
        self,
        *,
        benchmark_histories: dict[str, HistoryData] | None = None,
        fail_history: bool = False,
        quote_provider: str = "test",
        history_provider: str = "test",
        history_stale: bool = False,
    ) -> None:
        self.cache = FakeHistoryCache(benchmark_histories)
        self.fail_history = fail_history
        self.quote_provider = quote_provider
        self.history_provider = history_provider
        self.history_stale = history_stale
        self.quote_calls: list[str] = []
        self.history_calls: list[tuple[str, str, int]] = []

    def get_quote(self, symbol: str) -> QuoteData:
        self.quote_calls.append(symbol)
        return make_quote(symbol, self.quote_provider)

    def get_history(self, symbol: str, resolution: str = "D", days: int = 240) -> HistoryData:
        self.history_calls.append((symbol, resolution, days))
        if self.fail_history:
            raise RuntimeError("history failed")
        return make_history(symbol, days, self.history_provider, stale=self.history_stale)

    def get_provider_name_for(self, domain: str) -> str:
        return self.history_provider if domain == "daily_history" else self.quote_provider

    def get_provider_health(self) -> ProviderHealth:
        return ProviderHealth(
            provider=self.quote_provider,
            enabled=True,
            configured=True,
            reachable=True,
            last_successful_request=None,
            last_error=None,
            fallback_active=False,
            capabilities=ProviderCapabilities(quotes=True, daily_history=True, intraday_history=False, adjusted_history=True, volume=True),
        )


class StockSnapshotArchitectureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.env_patcher = patch.dict(os.environ, {
            "DATA_PROVIDER": "test",
            "MARKET_DATA_PROVIDER": "test",
            "QUOTE_DATA_PROVIDER": "test",
            "HISTORY_DATA_PROVIDER": "test",
        }, clear=False)
        self.env_patcher.start()
        self.addCleanup(self.env_patcher.stop)
        self.db_path = os.path.join(self.tempdir.name, "stock_snapshots.sqlite3")
        self.storage = StockSnapshotStorage(self.db_path)
        self.service = StockSnapshotService(self.storage)
        self.service.initialize()

    def test_input_planner_uses_one_canonical_selected_history_window(self) -> None:
        plan = StockDetailInputPlanner(history_days=450).plan("nvda")
        self.assertEqual(plan.symbol, "NVDA")
        self.assertEqual(plan.history_days, 450)
        self.assertEqual(plan.required_inputs, ("quote", "selected_history"))
        self.assertNotIn("selected_history:30", plan.required_inputs)

    def test_build_requests_selected_history_once_and_reuses_cached_benchmarks(self) -> None:
        provider = FakeProvider(benchmark_histories={"SPY": make_history("SPY"), "QQQ": make_history("QQQ"), "SOXX": make_history("SOXX")})
        with patch("app.stock_snapshots.input_bundle.get_market_data_provider", return_value=provider):
            snapshot = self.service.build_now("NVDA")

        self.assertIsNotNone(snapshot)
        self.assertEqual(provider.history_calls, [("NVDA", "D", 450)])
        self.assertEqual(snapshot.metadata["provider_history_requests"], [{"symbol": "NVDA", "resolution": "D", "days": 450}])
        self.assertEqual(snapshot.sections["relative_strength"].status, "complete")

    def test_1m_6m_1y_windows_are_derived_from_same_canonical_history(self) -> None:
        provider = FakeProvider()
        with patch("app.stock_snapshots.input_bundle.get_market_data_provider", return_value=provider):
            snapshot = self.service.build_now("NVDA")

        chart = snapshot.section_payload("chart")
        self.assertEqual(chart["source_history_days"], 450)
        self.assertEqual(len(chart["history"]["candles"]), 450)
        self.assertEqual(len(chart["windows"]["1M"]["candles"]), 30)
        self.assertEqual(len(chart["windows"]["6M"]["candles"]), 180)
        self.assertEqual(len(chart["windows"]["1Y"]["candles"]), 365)
        self.assertEqual(provider.history_calls, [("NVDA", "D", 450)])

    def test_warm_analysis_read_makes_zero_provider_calls(self) -> None:
        provider = FakeProvider()
        with patch("app.stock_snapshots.input_bundle.get_market_data_provider", return_value=provider):
            snapshot = self.service.build_now("NVDA")
        self.assertIsNotNone(snapshot)
        provider.quote_calls.clear()
        provider.history_calls.clear()

        payload = self.service.get_analysis_payload("NVDA")

        self.assertEqual(provider.quote_calls, [])
        self.assertEqual(provider.history_calls, [])
        self.assertEqual(payload["snapshot_id"], snapshot.snapshot_id)
        self.assertTrue(payload["chartHistory"]["candles"])

    def test_snapshot_survives_service_restart(self) -> None:
        provider = FakeProvider()
        with patch("app.stock_snapshots.input_bundle.get_market_data_provider", return_value=provider):
            snapshot = self.service.build_now("NVDA")
        restarted = StockSnapshotService(StockSnapshotStorage(self.db_path))
        restarted.initialize()

        payload = restarted.get_analysis_payload("NVDA")

        self.assertEqual(payload["snapshot_id"], snapshot.snapshot_id)
        self.assertEqual(payload["symbol"], "NVDA")

    def test_failed_refresh_preserves_last_known_good_snapshot(self) -> None:
        provider = FakeProvider()
        with patch("app.stock_snapshots.input_bundle.get_market_data_provider", return_value=provider):
            snapshot = self.service.build_now("NVDA")
        failing = FakeProvider(fail_history=True)
        with patch("app.stock_snapshots.input_bundle.get_market_data_provider", return_value=failing):
            failed = self.service.build_now("NVDA")

        self.assertIsNone(failed)
        latest = self.service.get_latest_snapshot("NVDA")
        self.assertEqual(latest.snapshot_id, snapshot.snapshot_id)

    def test_optional_benchmark_failure_does_not_block_core_analysis(self) -> None:
        provider = FakeProvider()
        with patch("app.stock_snapshots.input_bundle.get_market_data_provider", return_value=provider):
            snapshot = self.service.build_now("NVDA")

        payload = aggregate_payload(snapshot)
        self.assertEqual(snapshot.sections["relative_strength"].status, "partial")
        self.assertIsNotNone(payload["supportResistance"])
        self.assertIsNotNone(payload["volumeAnalysis"])
        self.assertIsNotNone(payload["riskPlan"])

    def test_pattern_and_leadership_failures_are_section_local(self) -> None:
        provider = FakeProvider()
        with (
            patch("app.stock_snapshots.input_bundle.get_market_data_provider", return_value=provider),
            patch("app.stock_snapshots.builder.detect_patterns", side_effect=RuntimeError("pattern failed")),
            patch("app.stock_snapshots.builder.calculate_leadership_signal", side_effect=RuntimeError("leadership failed")),
        ):
            snapshot = self.service.build_now("NVDA")

        self.assertEqual(snapshot.sections["pattern"].status, "unavailable")
        self.assertEqual(snapshot.sections["leadership"].status, "unavailable")
        self.assertEqual(snapshot.sections["support_resistance"].status, "complete")
        self.assertIsNotNone(snapshot.section_payload("rating"))

    def test_stale_snapshot_returns_immediately_and_dedupes_background_refresh(self) -> None:
        provider = FakeProvider()
        with patch("app.stock_snapshots.input_bundle.get_market_data_provider", return_value=provider):
            snapshot = self.service.build_now("NVDA")
        stale = snapshot.model_copy(update={
            "snapshot_id": f"{snapshot.snapshot_id}-stale",
            "expires_at": (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),
        })
        self.storage.publish_snapshot(stale)
        provider.quote_calls.clear()
        provider.history_calls.clear()
        started = time.perf_counter()
        with (
            patch("app.stock_snapshots.input_bundle.get_market_data_provider", return_value=provider),
            patch.dict(os.environ, {"STOCK_SNAPSHOT_ENABLED": "false"}, clear=False),
        ):
            first = self.service.get_analysis_payload("NVDA")
            second = self.service.get_analysis_payload("NVDA")

        self.assertLess((time.perf_counter() - started) * 1000, 500)
        self.assertEqual(first["snapshot_status"], "stale")
        self.assertEqual(second["snapshot_status"], "stale")

    def test_legacy_test_snapshot_is_rejected_when_runtime_switches_to_live(self) -> None:
        provider = FakeProvider()
        with patch("app.stock_snapshots.input_bundle.get_market_data_provider", return_value=provider):
            snapshot = self.service.build_now("NVDA")
        self.storage.set_state("latest:NVDA", snapshot.snapshot_id)
        self.storage.set_state("last_known_good:NVDA", snapshot.snapshot_id)

        with patch.dict(os.environ, {
            "DATA_PROVIDER": "finnhub",
            "MARKET_DATA_PROVIDER": "finnhub",
            "QUOTE_DATA_PROVIDER": "finnhub",
            "HISTORY_DATA_PROVIDER": "polygon",
            "STOCK_SNAPSHOT_ENABLED": "false",
        }, clear=False):
            live_service = StockSnapshotService(StockSnapshotStorage(self.db_path))
            live_service.initialize()
            payload = live_service.get_analysis_payload("NVDA")

        self.assertEqual(payload["snapshot_status"], "initializing")
        self.assertIsNone(payload["chartHistory"])
        self.assertIsNone(self.storage.get_state("latest:NVDA"))

    def test_legacy_mock_snapshot_is_rejected_in_live_mode(self) -> None:
        with patch.dict(os.environ, {
            "DATA_PROVIDER": "mock",
            "MARKET_DATA_PROVIDER": "mock",
            "QUOTE_DATA_PROVIDER": "mock",
            "HISTORY_DATA_PROVIDER": "mock",
        }, clear=False):
            provider = FakeProvider(quote_provider="mock", history_provider="mock")
            mock_service = StockSnapshotService(StockSnapshotStorage(self.db_path))
            mock_service.initialize()
            with patch("app.stock_snapshots.input_bundle.get_market_data_provider", return_value=provider):
                snapshot = mock_service.build_now("NVDA")
        self.storage.set_state("latest:NVDA", snapshot.snapshot_id)

        with patch.dict(os.environ, {
            "DATA_PROVIDER": "finnhub",
            "MARKET_DATA_PROVIDER": "finnhub",
            "QUOTE_DATA_PROVIDER": "finnhub",
            "HISTORY_DATA_PROVIDER": "polygon",
            "STOCK_SNAPSHOT_ENABLED": "false",
        }, clear=False):
            live_service = StockSnapshotService(StockSnapshotStorage(self.db_path))
            payload = live_service.get_analysis_payload("NVDA")

        self.assertEqual(payload["snapshot_status"], "initializing")
        self.assertIsNone(payload["chartHistory"])

    def test_stale_polygon_snapshot_is_accepted_in_live_mode(self) -> None:
        with patch.dict(os.environ, {
            "DATA_PROVIDER": "finnhub",
            "MARKET_DATA_PROVIDER": "finnhub",
            "QUOTE_DATA_PROVIDER": "finnhub",
            "HISTORY_DATA_PROVIDER": "polygon",
            "STOCK_SNAPSHOT_ENABLED": "false",
        }, clear=False):
            provider = FakeProvider(quote_provider="finnhub", history_provider="polygon", history_stale=True)
            live_service = StockSnapshotService(StockSnapshotStorage(self.db_path))
            live_service.initialize()
            with patch("app.stock_snapshots.input_bundle.get_market_data_provider", return_value=provider):
                snapshot = live_service.build_now("NVDA")
            payload = live_service.get_analysis_payload("NVDA")

        self.assertIsNotNone(snapshot)
        self.assertEqual(payload["snapshot_id"], snapshot.snapshot_id)
        self.assertEqual(payload["snapshot_history_provider"], "polygon")
        self.assertFalse(payload["snapshot_test_data"])

    def test_provider_namespace_prevents_cross_provider_contamination(self) -> None:
        with patch.dict(os.environ, {
            "DATA_PROVIDER": "mock",
            "MARKET_DATA_PROVIDER": "mock",
            "QUOTE_DATA_PROVIDER": "mock",
            "HISTORY_DATA_PROVIDER": "mock",
        }, clear=False):
            mock_provider = FakeProvider(quote_provider="mock", history_provider="mock")
            mock_service = StockSnapshotService(StockSnapshotStorage(self.db_path))
            with patch("app.stock_snapshots.input_bundle.get_market_data_provider", return_value=mock_provider):
                mock_snapshot = mock_service.build_now("NVDA")

        with patch.dict(os.environ, {
            "DATA_PROVIDER": "finnhub",
            "MARKET_DATA_PROVIDER": "finnhub",
            "QUOTE_DATA_PROVIDER": "finnhub",
            "HISTORY_DATA_PROVIDER": "polygon",
        }, clear=False):
            live_service = StockSnapshotService(StockSnapshotStorage(self.db_path))
            payload = live_service.get_analysis_payload("NVDA")

        self.assertIsNotNone(mock_snapshot)
        self.assertEqual(payload["snapshot_status"], "initializing")
        self.assertNotEqual(payload["snapshot_id"], mock_snapshot.snapshot_id)

    def test_application_data_validator_uses_temporary_stock_snapshot_database(self) -> None:
        original_path = os.path.join(self.tempdir.name, "development-stock.sqlite3")
        with patch.dict(os.environ, {"STOCK_SNAPSHOT_DB_PATH": original_path}, clear=False):
            temp_dir = configure_environment(Namespace(mode="test", allow_mock_fallback=False))
            try:
                self.assertNotEqual(os.environ["STOCK_SNAPSHOT_DB_PATH"], original_path)
                self.assertTrue(os.environ["STOCK_SNAPSHOT_DB_PATH"].startswith(temp_dir.name))
                self.assertTrue(os.environ["MARKET_DATA_CACHE_DB_PATH"].startswith(temp_dir.name))
            finally:
                temp_dir.cleanup()


if __name__ == "__main__":
    unittest.main()
