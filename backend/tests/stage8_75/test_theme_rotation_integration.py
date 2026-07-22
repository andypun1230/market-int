from __future__ import annotations

import os
import tempfile
import unittest
from collections import Counter
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.market_history.storage import DailyBar, DailyBarStorage
from app.rotation.engine import quadrant
from app.securities.models import SecurityRecord
from app.securities.registry import SECTOR_BY_ID
from app.securities.storage import SecurityMasterStorage
from app.theme_snapshots.builder import ThemeSnapshotBuilder
from app.theme_snapshots.readers import rotation_payload
from app.theme_snapshots.storage import ThemeSnapshotStorage
from app.themes.launch import TAXONOMY_VERSION, get_launch_theme_registry
from app.themes.policy import ThemePolicy
from app.themes.storage import ThemeStorage
from main import app


class CanonicalThemeRotationIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory()
        cls.db = Path(cls.temp.name) / "theme-rotation.sqlite3"
        cls.original_provider = os.environ.get("DATA_PROVIDER")
        cls.original_history = os.environ.get("HISTORY_DATA_PROVIDER")
        os.environ["DATA_PROVIDER"] = "finnhub"
        os.environ["HISTORY_DATA_PROVIDER"] = "polygon"
        cls.registry = get_launch_theme_registry()
        cls.bars = DailyBarStorage(cls.db)
        cls.securities = SecurityMasterStorage(cls.db)
        mapped = sorted({item.symbol for item in cls.registry.mappings})
        for symbol in mapped:
            cls.securities.upsert_security(SecurityRecord(
                security_id=f"rotation-{symbol}", ticker=symbol, company_name=symbol,
                history_provider_symbol=symbol, quote_provider_symbol=symbol,
                source="hermetic-rotation-test", verified_at=date.today().isoformat(),
            ))
        benchmark_symbols = {"SPY"}
        benchmark_symbols.update(symbol for definition in cls.registry.launch() for symbol in definition.benchmark_symbols)
        benchmark_symbols.update(item["etf_symbol"] for item in SECTOR_BY_ID.values())
        rows: list[DailyBar] = []
        for symbol_index, symbol in enumerate(sorted(set(mapped) | benchmark_symbols)):
            for offset in range(280):
                session = date.today() - timedelta(days=279 - offset)
                close = 100 + symbol_index * 0.1 + offset * (0.08 + (symbol_index % 11) * 0.004)
                rows.append(DailyBar(
                    symbol, "polygon", session.isoformat(), f"{session.isoformat()}T21:00:00+00:00",
                    close, close, close, close, 1_000, adjusted=True, quality_status="valid",
                ))
        cls.bars.upsert(rows)
        with patch("app.providers.polygon_provider.PolygonMarketDataProvider.get_history", side_effect=AssertionError("network provider called")):
            cls.snapshot = ThemeSnapshotBuilder(
                theme_storage=ThemeStorage(cls.db),
                snapshot_storage=ThemeSnapshotStorage(cls.db),
                bars=cls.bars,
                securities=cls.securities,
                registry=cls.registry,
                include_launch_registry=True,
            ).build(publish=False)
        assert cls.snapshot is not None

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.original_provider is None:
            os.environ.pop("DATA_PROVIDER", None)
        else:
            os.environ["DATA_PROVIDER"] = cls.original_provider
        if cls.original_history is None:
            os.environ.pop("HISTORY_DATA_PROVIDER", None)
        else:
            os.environ["HISTORY_DATA_PROVIDER"] = cls.original_history
        cls.temp.cleanup()

    def test_all_26_available_themes_produce_26_eligible_points(self) -> None:
        payload = rotation_payload(self.snapshot, "1m")
        self.assertEqual(len(self.snapshot.rows), 26)
        self.assertEqual(payload["eligible_count"], 26)
        self.assertEqual(payload["excluded_count"], 0)
        self.assertEqual(len({item["theme_id"] for item in payload["points"]}), 26)

    def test_global_partial_snapshot_does_not_hide_available_rows(self) -> None:
        partial = replace(self.snapshot, status="partial")
        payload = rotation_payload(partial, "1M")
        self.assertEqual(payload["snapshot_status"], "partial")
        self.assertEqual(payload["status"], "available")
        self.assertEqual(payload["eligible_count"], 26)

    def test_partial_coverage_disclosure_does_not_exclude_available_row(self) -> None:
        rows = list(self.snapshot.rows)
        rows[0] = {**rows[0], "status": "available", "coverage_status": "partial", "coverage_ratio": 0.8}
        payload = rotation_payload(replace(self.snapshot, rows=tuple(rows), status="partial"), "1M")
        selected = next(item for item in payload["points"] if item["theme_id"] == rows[0]["theme_id"])
        self.assertEqual(payload["eligible_count"], 26)
        self.assertIn("unchanged governed coverage gate", selected["partial_coverage_disclosure"])

    def test_unavailable_and_selected_timeframe_missing_rows_have_exact_exclusions(self) -> None:
        rows = list(self.snapshot.rows)
        rows[0] = {**rows[0], "status": "unavailable"}
        rows[1] = {**rows[1], "rotation_series": {**rows[1]["rotation_series"], "1M": {}}}
        payload = rotation_payload(replace(self.snapshot, rows=tuple(rows)), "1M")
        reasons = {item["theme_id"]: item["reason"] for item in payload["exclusions"]}
        self.assertEqual(payload["eligible_count"], 24)
        self.assertEqual(reasons[rows[0]["theme_id"]], "row_status_not_available")
        self.assertEqual(reasons[rows[1]["theme_id"]], "selected_timeframe_metrics_missing")

    def test_timeframes_use_distinct_governed_windows_and_datasets(self) -> None:
        payloads = {timeframe: rotation_payload(self.snapshot, timeframe) for timeframe in ("1W", "1M", "3M")}
        self.assertEqual([payloads[item]["profile"] for item in ("1W", "1M", "3M")], ["short", "medium", "long"])
        self.assertEqual([payloads[item]["timeframe_definition"]["fast_trend_ema"] for item in ("1W", "1M", "3M")], [10, 20, 10])
        self.assertEqual([payloads[item]["timeframe_definition"]["momentum_lag"] for item in ("1W", "1M", "3M")], [3, 5, 4])
        self.assertEqual([payloads[item]["timeframe_definition"]["sampling_frequency"] for item in ("1W", "1M", "3M")], ["daily", "daily", "weekly_last_complete_session"])
        values = [(payloads[item]["points"][0]["relative_trend"], payloads[item]["points"][0]["relative_momentum"]) for item in ("1W", "1M", "3M")]
        self.assertGreater(len(set(values)), 1)

    def test_quadrant_boundaries_at_100_are_deterministic(self) -> None:
        self.assertEqual(quadrant(100, 100), "leading")
        self.assertEqual(quadrant(99.9999, 100), "improving")
        self.assertEqual(quadrant(100, 99.9999), "weakening")
        self.assertEqual(quadrant(99.9999, 99.9999), "lagging")

    def test_trajectories_are_same_theme_real_points_only(self) -> None:
        for timeframe in ("1W", "1M", "3M"):
            for point in rotation_payload(self.snapshot, timeframe)["points"]:
                self.assertTrue(point["trail_points"])
                self.assertTrue(all(not item["is_synthetic"] for item in point["trail_points"]))
                self.assertEqual(point["current_point"], point["trail_points"][-1])
                self.assertIn(point["trajectory"], {"improving", "deteriorating", "stable"})
                self.assertTrue(all(f"theme:{point['theme_id']}:" in item["source_series_ids"][0] for item in point["trail_points"]))

    def test_view_metrics_and_latest_transition_are_exposed_without_recalculation(self) -> None:
        point = rotation_payload(self.snapshot, "1M")["points"][0]
        row = next(item for item in self.snapshot.rows if item["theme_id"] == point["theme_id"])
        previous = point["trail_points"][-2]
        current = point["trail_points"][-1]
        self.assertEqual(point["speed"], row["rotation_series"]["1M"]["speed"])
        self.assertEqual(point["distance_travelled"], row["rotation_series"]["1M"]["distance_travelled"])
        self.assertEqual(point["previous_quadrant"], quadrant(previous["relative_trend"], previous["relative_momentum"]))
        self.assertEqual(point["latest_quadrant_transition"], {
            "from": point["previous_quadrant"],
            "to": quadrant(current["relative_trend"], current["relative_momentum"]),
            "changed": point["previous_quadrant"] != point["quadrant"],
            "as_of": current["market_date"],
        })

    def test_ordering_and_ids_are_deterministic_without_legacy_two_theme_limit(self) -> None:
        first = rotation_payload(self.snapshot, "1M")["points"]
        second = rotation_payload(self.snapshot, "1M")["points"]
        self.assertEqual([item["theme_id"] for item in first], [item["theme_id"] for item in second])
        self.assertEqual(len(first), 26)
        self.assertEqual(len(first), len({item["theme_id"] for item in first}))

    def test_quadrant_counts_cover_every_point(self) -> None:
        for timeframe in ("1W", "1M", "3M"):
            payload = rotation_payload(self.snapshot, timeframe)
            counts = Counter(item["quadrant"] for item in payload["points"])
            self.assertEqual(sum(counts.values()), payload["eligible_count"])
            self.assertEqual(set(counts) - {"leading", "improving", "weakening", "lagging"}, set())

    def test_rotation_api_accepts_timeframe_and_legacy_interval_alias(self) -> None:
        service = SimpleNamespace(latest=lambda: self.snapshot)
        with patch("app.api.market.get_theme_snapshot_service", return_value=service), TestClient(app) as client:
            current = client.get("/market/themes/rotation?timeframe=3m").json()
            legacy = client.get("/market/themes/rotation?interval=1w").json()
            canonical = client.get("/market/themes/rotation?profile=medium").json()
        self.assertEqual((current["timeframe"], current["eligible_count"]), ("3M", 26))
        self.assertEqual((legacy["timeframe"], legacy["eligible_count"]), ("1W", 26))
        self.assertEqual((canonical["profile"], canonical["eligible_count"]), ("medium", 26))

    def test_existing_availability_threshold_is_unchanged(self) -> None:
        self.assertEqual(ThemePolicy().partial_coverage_threshold, 0.75)
        self.assertEqual(TAXONOMY_VERSION, "2026.07.1")


if __name__ == "__main__":
    unittest.main()
