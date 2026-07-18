from __future__ import annotations

import os
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.breadth.builder import BreadthSnapshotBuilder
from app.breadth.engine import calculate_breadth
from app.breadth.models import BreadthCalculationInput
from app.breadth.policy import BreadthPolicy
from app.breadth.service import get_breadth_snapshot_service, reset_breadth_snapshot_service
from app.breadth.storage import BreadthSnapshotStorage
from app.market_history.storage import DailyBar, DailyBarStorage
from app.securities.service import SecurityMasterService
from app.securities.storage import SecurityMasterStorage
from main import app


class BreadthSnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "breadth.sqlite3"
        self.env = patch.dict(os.environ, {"BREADTH_DB_PATH": str(self.db), "DATA_PROVIDER": "test", "BREADTH_ENABLED": "true", "BREADTH_STARTUP_REFRESH": "false", "MARKET_SNAPSHOT_STARTUP_REFRESH": "false", "BACKGROUND_REFRESH_ENABLED": "false"}, clear=False)
        self.env.start(); reset_breadth_snapshot_service()
        self.master = SecurityMasterService(SecurityMasterStorage(self.db)); self.bars = DailyBarStorage(self.db); self.snapshot_storage = BreadthSnapshotStorage(self.db)
        self._import_universe(); self._store_histories()

    def tearDown(self) -> None:
        reset_breadth_snapshot_service(); self.env.stop(); self.tmp.cleanup()

    def _import_universe(self) -> None:
        rows = [
            {"ticker": "AAPL", "company_name": "Apple", "sector": "Information Technology"},
            {"ticker": "MSFT", "company_name": "Microsoft", "sector": "Information Technology"},
            {"ticker": "JPM", "company_name": "JPMorgan", "sector": "Financials"},
            {"ticker": "XOM", "company_name": "Exxon", "sector": "Energy"},
        ]
        report = self.master.import_universe(name="sp100", version="test-v1", effective_date="2026-07-17", benchmark_symbol="SPY", rows=rows, source="test", source_timestamp="2026-07-17", dry_run=False)
        self.assertEqual(report.member_count, 4)

    def _store_histories(self) -> None:
        for offset, ticker in enumerate(["AAPL", "MSFT", "JPM", "XOM", "SPY"]):
            self.bars.upsert(make_bars(ticker, offset))

    def test_security_master_rejects_duplicates_and_versions_membership(self) -> None:
        report = self.master.import_universe(name="sp100", version="test-v2", effective_date="2026-07-18", benchmark_symbol="SPY", rows=[{"ticker": "AAPL", "sector": "Information Technology"}, {"ticker": "AAPL", "sector": "Information Technology"}], dry_run=True)
        self.assertTrue(report.invalid)
        self.assertEqual(self.master.storage.get_active_universe("sp100").version, "test-v1")

    def test_daily_bars_are_idempotent_and_validate_ohlc(self) -> None:
        bars = make_bars("AAPL", 0)
        inserted, updated = self.bars.upsert(bars)
        self.assertEqual((inserted, updated), (0, 0))
        with self.assertRaises(ValueError):
            self.bars.upsert([DailyBar("BAD", "polygon", "2026-07-17", "2026-07-17T00:00:00+00:00", 10, 9, 8, 10, 1)])

    def test_pure_engine_counts_advance_decline_and_indicator_coverage(self) -> None:
        universe = self.master.storage.get_active_universe("sp100"); assert universe
        members = tuple(self.master.storage.members(universe.universe_id))
        histories = {member.ticker: tuple(self.bars.history(member.ticker)) for member in members}
        result = calculate_breadth(BreadthCalculationInput(universe, members, "2026-07-17", histories), BreadthPolicy())
        self.assertEqual(result.core["advancing_count"] + result.core["declining_count"] + result.core["unchanged_count"], 4)
        self.assertEqual(result.coverage["coverage_status"], "complete")
        self.assertEqual(result.coverage["indicator_coverage"]["EMA200"], 1.0)
        self.assertTrue(0 <= (result.score or 0) <= 100)

    def test_partial_coverage_does_not_fabricate_missing_member_metrics(self) -> None:
        universe = self.master.storage.get_active_universe("sp100"); assert universe
        members = tuple(self.master.storage.members(universe.universe_id))
        histories = {member.ticker: tuple(self.bars.history(member.ticker)) for member in members if member.ticker != "XOM"}
        result = calculate_breadth(BreadthCalculationInput(universe, members, "2026-07-17", histories), BreadthPolicy())
        self.assertEqual(result.coverage["coverage_status"], "partial")
        self.assertEqual(result.coverage["members_missing"], ["XOM"])
        self.assertEqual(result.coverage["members_available"], 3)

    def test_sparse_live_pilot_publishes_partial_metrics_without_a_score(self) -> None:
        universe = self.master.storage.get_active_universe("sp100"); assert universe
        member = self.master.storage.members(universe.universe_id)[0]
        histories = {member.ticker: tuple(self.bars.history(member.ticker))}
        result = calculate_breadth(BreadthCalculationInput(universe, tuple(self.master.storage.members(universe.universe_id)), "2026-07-17", histories), BreadthPolicy())
        self.assertEqual(result.coverage["coverage_status"], "partial")
        self.assertIsNone(result.score)

    def test_snapshot_is_immutable_persistent_and_warm_read_never_calls_provider(self) -> None:
        builder = BreadthSnapshotBuilder(self.master, self.bars, self.snapshot_storage)
        snapshot = builder.build_and_publish("sp100"); assert snapshot
        self.assertEqual(snapshot.status, "complete")
        restored = self.snapshot_storage.get(snapshot.snapshot_id)
        self.assertEqual(restored.input_hash, snapshot.input_hash)
        with patch("app.market_history.updater.BreadthUniverseHistoryUpdater.update_symbol", side_effect=AssertionError("warm read fetched provider")):
            latest = self.snapshot_storage.latest(snapshot.universe_id, "test:polygon:sp100")
        self.assertEqual(latest.snapshot_id, snapshot.snapshot_id)
        self.assertEqual(len(self.snapshot_storage.history(snapshot.universe_id, "breadth_score")), 1)

    def test_unavailable_build_preserves_last_known_good(self) -> None:
        builder = BreadthSnapshotBuilder(self.master, self.bars, self.snapshot_storage)
        good = builder.build_and_publish("sp100"); assert good
        empty = DailyBarStorage(Path(self.tmp.name) / "empty.sqlite3")
        failing = BreadthSnapshotBuilder(self.master, empty, self.snapshot_storage).build_and_publish("sp100")
        self.assertEqual(failing.snapshot_id, good.snapshot_id)

    def test_api_reads_snapshot_without_constituent_calculation(self) -> None:
        snapshot = BreadthSnapshotBuilder(self.master, self.bars, self.snapshot_storage).build_and_publish("sp100"); assert snapshot
        reset_breadth_snapshot_service()
        with TestClient(app) as client, patch("app.services.breadth.calculate_basket_breadth", side_effect=AssertionError("screen calculated breadth")):
            response = client.get("/market/breadth")
            latest = client.get("/market/breadth/snapshot/latest")
            history = client.get("/market/breadth/history?metric=breadth_score")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["market"]["snapshot_id"], snapshot.snapshot_id)
        self.assertEqual(latest.json()["snapshot_id"], snapshot.snapshot_id)
        self.assertEqual(len(history.json()["items"]), 1)

    def test_strict_live_mode_never_uses_legacy_mock_breadth(self) -> None:
        from app.services.breadth import calculate_market_breadth
        with patch.dict(os.environ, {"DATA_PROVIDER": "live", "HISTORY_DATA_PROVIDER": "polygon", "MARKET_DATA_ALLOW_MOCK_FALLBACK": "false", "BREADTH_DB_PATH": str(Path(self.tmp.name) / "strict.sqlite3")}, clear=False), patch("app.services.breadth.calculate_basket_breadth", side_effect=AssertionError("strict live used mock breadth")):
            reset_breadth_snapshot_service()
            result = calculate_market_breadth()
        self.assertEqual(result.source_state, "unavailable")


def make_bars(ticker: str, offset: int) -> list[DailyBar]:
    end = date(2026, 7, 17); rows = []
    for index in range(270):
        day = end - timedelta(days=269 - index)
        # Stored daily session dates intentionally model completed sessions for deterministic tests.
        close = 100 + offset * 3 + index * (0.12 if offset != 3 else -0.03)
        previous = close - 0.15
        rows.append(DailyBar(ticker, "polygon", day.isoformat(), f"{day.isoformat()}T20:00:00+00:00", previous, close + 1, previous - 1, close, 1000 + index))
    return rows


if __name__ == "__main__":
    unittest.main()
