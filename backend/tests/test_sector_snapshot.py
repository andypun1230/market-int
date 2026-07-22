from __future__ import annotations
import os, tempfile, unittest
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.market_history.storage import DailyBar, DailyBarStorage
from app.securities.registry import canonical_sector_id, normalized_sector
from app.securities.service import SecurityMasterService
from app.securities.storage import SecurityMasterStorage
from app.models.market import DailyReportResponse
from app.sector_snapshots.builder import SectorSnapshotBuilder
from app.sector_snapshots.storage import SectorSnapshotStorage
from app.sector_snapshots.service import reset_sector_snapshot_service
from main import app


class SectorSnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(); self.db = Path(self.tmp.name) / "sector.sqlite3"
        self.env = patch.dict(os.environ, {"BREADTH_DB_PATH": str(self.db), "DATA_PROVIDER": "live", "HISTORY_DATA_PROVIDER": "polygon", "MARKET_DATA_ALLOW_MOCK_FALLBACK": "false", "BACKGROUND_REFRESH_ENABLED": "false"}, clear=False); self.env.start(); reset_sector_snapshot_service()
        self.master=SecurityMasterService(SecurityMasterStorage(self.db)); self.bars=DailyBarStorage(self.db); self.storage=SectorSnapshotStorage(self.db)
        self.master.import_universe(name="sp100", version="sector-test-v1", effective_date="2026-07-17", benchmark_symbol="SPY", rows=[{"ticker":"AAPL","company_name":"Apple","sector":"Tech"},{"ticker":"MSFT","company_name":"Microsoft","sector":"Information Technology"},{"ticker":"JPM","company_name":"JPMorgan","sector":"Financials"},{"ticker":"XOM","company_name":"Exxon","sector":"Energy"}], source="reviewed-test", source_timestamp="2026-07-17", dry_run=False)
        for ticker, offset in [("AAPL",0),("MSFT",1),("JPM",2),("XOM",3),("SPY",4),("XLC",5),("XLY",6),("XLP",7),("XLE",8),("XLF",9),("XLV",10),("XLI",11),("XLK",12),("XLB",13),("XLRE",14),("XLU",15)]: self.bars.upsert(make_bars(ticker, offset))

    def tearDown(self) -> None:
        reset_sector_snapshot_service(); self.env.stop(); self.tmp.cleanup()

    def test_taxonomy_normalizes_reviewed_aliases(self) -> None:
        self.assertEqual(canonical_sector_id("Technology"), "information_technology")
        self.assertEqual(canonical_sector_id("Consumer Cyclical"), "consumer_discretionary")
        self.assertEqual(canonical_sector_id("Healthcare"), "health_care")
        self.assertEqual(normalized_sector("Communications"), "Communication Services")

    def test_snapshot_is_deterministic_complete_and_immutable(self) -> None:
        builder=SectorSnapshotBuilder(self.master, self.bars, self.storage); first=builder.build(); second=builder.build()
        self.assertIsNotNone(first); assert first
        self.assertEqual(first.status, "complete"); self.assertEqual(first.snapshot_id, second.snapshot_id if second else None)
        self.assertEqual(len(first.sectors), 11); self.assertEqual(first.coverage["etf_coverage_ratio"], 1.0)
        self.assertEqual(first.schema_version, 4); self.assertEqual([row["rank"] for row in first.sectors], sorted(row["rank"] for row in first.sectors))
        self.assertEqual(set(row["rank"] for row in first.sectors), set(range(1, 12)))
        self.assertTrue(all(set(row["rotation_series"]) == {"1W", "1M", "3M"} for row in first.sectors))
        self.assertTrue(all(item["current_point"] == item["trail_points"][-1] for row in first.sectors for item in row["rotation_series"].values()))
        self.assertTrue(all(row["price_metrics"][period] is not None for row in first.sectors for period in ("return_1d", "return_1w", "return_1m", "return_3m", "return_6m", "return_1y")))
        self.assertTrue(all(0 <= row["composite_score"] <= 100 for row in first.sectors if row["composite_score"] is not None))
        self.assertTrue(all(row["participation_metrics"]["is_distinct_from_ema50"] for row in first.sectors))
        self.assertTrue(all(row["composite_audit"]["formula"] == "equal_weight_mean_of_available_component_scores" for row in first.sectors))
        self.assertTrue(all(abs(row["composite_audit"]["total_weight"] - 1) < 0.0001 for row in first.sectors if row["composite_score"] is not None))
        self.assertEqual(self.storage.get(first.snapshot_id).input_hash, first.input_hash)

    def test_zero_decliner_sector_rows_use_display_semantics_and_sample_metadata(self) -> None:
        history = self.bars.history("XOM")
        previous, latest = history[-2], history[-1]
        self.bars.upsert([DailyBar("XOM", "polygon", latest.session_date, latest.timestamp, previous.close, previous.close + 3, previous.close - 1, previous.close + 2, latest.volume)])
        snapshot = SectorSnapshotBuilder(self.master, self.bars, self.storage).build(); assert snapshot
        energy = next(row for row in snapshot.sectors if row["sector_id"] == "energy")
        self.assertEqual(energy["breadth_metrics"]["advance_decline_ratio"], None)
        self.assertEqual(energy["breadth_metrics"]["advance_decline_ratio_display"], "No decliners")
        self.assertEqual(energy["breadth_representativeness"], "Limited")
        self.assertEqual(energy["breadth_confidence"], "Limited")

    def test_partial_is_honest_when_etf_history_is_missing(self) -> None:
        self.bars = DailyBarStorage(Path(self.tmp.name) / "partial.sqlite3")
        # Copying no ETF histories makes a snapshot unavailable; no data is fabricated.
        result=SectorSnapshotBuilder(self.master, self.bars, SectorSnapshotStorage(self.bars.db_path)).build()
        self.assertIsNone(result)

    def test_rotation_engine_uses_interval_specific_independent_coordinates(self) -> None:
        from app.rotation.engine import build_rotation_series, relative_return
        entity = self.bars.history("XLK")
        benchmark = self.bars.history("SPY")
        series = [build_rotation_series(entity_type="sector", entity_id="information_technology", display_name="Information Technology", short_label="XLK", entity_symbol="XLK", entity_history=entity, benchmark_symbol="SPY", benchmark_history=benchmark, interval=interval, source_state="live", data_mode="live", universe_id="test", universe_version="v1", coverage_ratio=1.0) for interval in ("1W", "1M", "3M")]
        self.assertTrue(all(item.status == "complete" and len(item.trail_points) == 5 for item in series))
        self.assertTrue(all(point.market_date for item in series for point in item.trail_points))
        self.assertTrue(all(not point.is_synthetic and point.source_provider == "polygon" for item in series for point in item.trail_points))
        week = series[0].current_point; assert week
        aligned = list(zip(entity, benchmark))
        expected_rs = relative_return(aligned, len(aligned) - 1, 5); previous_rs = relative_return(aligned, len(aligned) - 2, 5)
        self.assertEqual(week.raw_rs, round(expected_rs or 0, 4))
        self.assertEqual(week.raw_momentum, round((expected_rs or 0) - (previous_rs or 0), 4))
        self.assertNotEqual(week.raw_rs, week.raw_momentum)
        self.assertEqual({item.interval for item in series}, {"1W", "1M", "3M"})
        self.assertNotEqual(series[0].trail_points, series[2].trail_points)

    def test_routes_share_snapshot_and_warm_reads_make_no_provider_calls(self) -> None:
        snapshot=SectorSnapshotBuilder(self.master, self.bars, self.storage).build(); assert snapshot
        from app.sector_snapshots import service
        service._service = service.SectorSnapshotService(self.storage)
        with TestClient(app) as client, patch("app.market_history.updater.BreadthUniverseHistoryUpdater.update_symbol", side_effect=AssertionError("read fetched provider")):
            latest=client.get("/market/sectors/snapshot/latest"); sectors=client.get("/market/sectors"); rotation=client.get("/market/sectors/rotation"); alerts=client.get("/market/sectors/alerts"); dashboard=client.get("/market/sector-dashboard"); detail=client.get("/market/sectors/Technology")
        self.assertTrue(all(response.status_code == 200 for response in [latest,sectors,rotation,alerts,dashboard,detail]))
        self.assertEqual(latest.json()["snapshot_id"], snapshot.snapshot_id); self.assertEqual(rotation.json()["snapshot_id"], snapshot.snapshot_id); self.assertEqual(alerts.json()["snapshot_id"], snapshot.snapshot_id); self.assertEqual(dashboard.json()["snapshot_id"], snapshot.snapshot_id)
        self.assertEqual(rotation.json()["trail_source"], "published_sector_snapshots")
        self.assertEqual(rotation.json()["history_point_count"], 1)
        self.assertFalse(rotation.json()["movement_available"])
        self.assertTrue(rotation.json()["current_positions_available"])
        self.assertTrue(rotation.json()["etf_trails_available"])
        self.assertFalse(rotation.json()["snapshot_transition_history_available"])
        self.assertEqual(rotation.json()["current_point_count"], 33)
        self.assertEqual(rotation.json()["trail_point_count"], 165)
        self.assertEqual(rotation.json()["transition_snapshot_count"], 1)
        self.assertTrue(all(len(points) == 1 for points in rotation.json()["trails"].values()))
        self.assertEqual(rotation.json()["formula_version"], "relative-return-momentum-v1")
        self.assertEqual(rotation.json()["normalization_version"], "midpoint-100-relative-return-v1")
        self.assertEqual(rotation.json()["market_trail_source"], "durable_polygon_adjusted_daily_history")
        series = [item for item in rotation.json()["series"] if item["entity_id"] == "information_technology"]
        self.assertEqual({item["interval"] for item in series}, {"1W", "1M", "3M"})
        self.assertTrue(all(len(item["trail_points"]) == 5 for item in series))
        for item in series:
            points = item["trail_points"]
            self.assertEqual([point["market_date"] for point in points], sorted(point["market_date"] for point in points))
            self.assertEqual(len({point["market_date"] for point in points}), len(points))
            self.assertEqual(item["current_point"], points[-1])
            self.assertTrue(all(point["source_provider"] == "polygon" and not point["is_synthetic"] for point in points))
            self.assertTrue(all(point["plotted_x"] == round(100 + point["raw_rs"], 4) and point["plotted_y"] == round(100 + point["raw_momentum"], 4) for point in points))
        snapshot_series = next(row for row in snapshot.sectors if row["sector_id"] == "information_technology")["rotation_series"]
        self.assertTrue(all(item["current_point"]["plotted_x"] == snapshot_series[item["interval"]]["current_point"]["plotted_x"] and item["current_point"]["plotted_y"] == snapshot_series[item["interval"]]["current_point"]["plotted_y"] for item in series))
        self.assertNotEqual(series[0]["trail_points"], series[-1]["trail_points"])
        self.assertEqual(detail.json()["snapshot_id"], snapshot.snapshot_id); self.assertEqual(detail.json()["sector"]["sector_id"], "information_technology")
        self.assertEqual({item["interval"] for item in detail.json()["rotation_series"]}, {"1W", "1M", "3M"})
        self.assertEqual(detail.json()["coverage"], snapshot.coverage); self.assertTrue(detail.json()["constituents"])
        self.assertTrue(all(value is not None for value in detail.json()["sector"]["price_metrics"].values() if isinstance(value, (int, float))))

    def test_rotation_uses_only_real_distinct_snapshot_dates(self) -> None:
        first = SectorSnapshotBuilder(self.master, self.bars, self.storage).build(); assert first
        repeated = {**first.model_dump(), "snapshot_id": "sector-repeated", "generated_at": "2026-07-17T23:00:00+00:00"}
        self.storage.publish(type(first)(**repeated), "live:polygon:sp100")
        from app.services.sector_dashboard import build_sector_rotation_trails
        rotation = build_sector_rotation_trails(first, self.storage.history(first.universe_id))
        self.assertEqual(rotation["history_point_count"], 1)
        self.assertFalse(rotation["movement_available"])
        self.assertTrue(rotation["current_positions_available"])
        self.assertFalse(rotation["snapshot_transition_history_available"])
        self.assertTrue(all(len(points) == 1 for points in rotation["trails"].values()))

    def test_report_sector_order_and_cache_key_follow_snapshot_rank(self) -> None:
        from app.services import report
        ranked = report.get_sector_items(SimpleNamespace(sector_dashboard={"sectors": [
            {"id": "energy", "name": "Energy", "returns": {"1m": 20}, "metadata": {"rank": 2}},
            {"id": "utilities", "name": "Utilities", "returns": {"1m": -5}, "metadata": {"rank": 1}},
        ]}))
        self.assertEqual([item["id"] for item in ranked], ["utilities", "energy"])
        with patch("app.services.report.get_market_snapshot_service") as market, patch("app.services.report.get_sector_snapshot_service") as service, patch("app.services.report.calculate_market_breadth") as breadth, patch("app.services.report.build_theme_intelligence_context") as themes, patch("app.services.report.get_daily_report_storage") as storage, patch("app.services.report.get_or_compute") as cached:
            market.return_value.get_latest_snapshot.return_value = None
            service.return_value.latest.return_value = SimpleNamespace(snapshot_id="sector-ranked")
            breadth.return_value = SimpleNamespace(snapshot_id="breadth-ranked")
            themes.return_value = {"snapshot_id": "theme-ranked"}
            storage.return_value.get_by_identity.return_value = None
            cached.return_value = DailyReportResponse.model_construct()
            storage.return_value.save_if_absent.return_value = SimpleNamespace(report=cached.return_value)
            report.build_daily_report()
        cache_key = cached.call_args.args[0]
        self.assertEqual(
            cache_key.rsplit(":", 1)[0],
            f"report:daily:{report.REPORT_SCHEMA_VERSION}:{report.REPORT_PDF_FORMAT_VERSION}:json:unavailable:breadth-ranked:sector-ranked:theme-ranked",
        )
        self.assertRegex(cache_key.rsplit(":", 1)[1], r"^[0-9a-f]{16}$")

    def test_report_identity_changes_when_only_theme_snapshot_changes(self) -> None:
        from app.services import report
        with patch("app.services.report.latest_market_snapshot_id", return_value="market-1"), patch("app.services.report.latest_breadth_snapshot_id", return_value="breadth-1"), patch("app.services.report.latest_sector_snapshot_id", return_value="sector-1"), patch("app.services.report.latest_theme_snapshot_id", side_effect=["theme-1", "theme-2"]):
            first = report.current_report_identity()
            second = report.current_report_identity()
        self.assertNotEqual(first["cache_key"], second["cache_key"])
        self.assertNotEqual(first["identity_key"], second["identity_key"])
        self.assertIn("theme-1", first["cache_key"])
        self.assertIn("theme-2", second["cache_key"])


def make_bars(ticker: str, offset: int) -> list[DailyBar]:
    end=date(2026,7,17); rows=[]
    for index in range(270):
        day=end-timedelta(days=269-index); close=100+offset+index*(0.13 if offset % 3 else -0.02); previous=close-.1
        rows.append(DailyBar(ticker,"polygon",day.isoformat(),f"{day.isoformat()}T20:00:00+00:00",previous,close+1,previous-1,close,1000+index))
    return rows


if __name__ == "__main__": unittest.main()
