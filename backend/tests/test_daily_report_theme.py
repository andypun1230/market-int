import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from app.reports.storage import DailyReportStorage
from app.providers.mock_provider import MockMarketDataProvider
from app.services.market_data_repository import MarketDataRepository, MemoryMarketDataCache
from app.services.report_read_context import ReportReadCacheMiss, report_snapshot_read
from app.services.report import (
    REPORT_SCHEMA_VERSION,
    build_daily_report,
    build_captured_report_ai_summary,
    current_report_identity,
    build_page_insights,
    build_report_narrative_context,
    build_theme_report_section,
    build_visual_report_styles,
    theme_leadership_panel,
    theme_methodology_disclosure,
    theme_rotation_items,
    theme_rotation_panel,
)


def theme_context() -> dict:
    return {
        "available": True,
        "snapshot_id": "theme-2026-07-17-f8ca1be84c",
        "market_date": "2026-07-17",
        "generated_at": "2026-07-18T00:00:00+00:00",
        "historical_disclosure": "Historical results use the current reviewed constituent basket unless historical membership versions are available.",
        "pilot_scope": {
            "active_reviewed_theme_count": 2,
            "rank_scope": "Rank reflects the leadership composite among the 2 currently active reviewed pilot themes.",
        },
        "items": [
            theme_row("cybersecurity", "Cybersecurity", 1, "Leading", 100.0, 112.0, 118.0, "leading"),
            theme_row("memory_storage", "Memory & Storage", 2, "Improving", 62.16, 86.0, 92.0, "lagging"),
        ],
    }


def theme_row(theme_id: str, name: str, rank: int, classification: str, score: float, x: float, y: float, quadrant: str) -> dict:
    trail = [
        {"market_date": "2026-07-03", "plotted_x": x - 4, "plotted_y": y - 3, "raw_rs": x - 104, "raw_momentum": y - 103, "quadrant": quadrant, "source_provider": "polygon", "source_series_ids": [f"theme:{theme_id}:v1.2:polygon"], "is_synthetic": False},
        {"market_date": "2026-07-17", "plotted_x": x, "plotted_y": y, "raw_rs": x - 100, "raw_momentum": y - 100, "quadrant": quadrant, "source_provider": "polygon", "source_series_ids": [f"theme:{theme_id}:v1.2:polygon"], "is_synthetic": False},
    ]
    return {
        "theme_id": theme_id,
        "display_name": name,
        "rank": rank,
        "classification": classification,
        "composite_score": score,
        "performance": {"1d": 1.0, "1w": 2.0, "1m": 3.0, "3m": 4.0, "6m": 5.0, "1y": 6.0},
        "relative_strength": {"vs_spy_1m": 3.0},
        "breadth": {"coverage_ratio": 1.0},
        "coverage_ratio": 1.0,
        "participation": {"participation_score": 100},
        "concentration": {"classification": "low"},
        "signal_confidence": {"score": 85},
        "data_confidence": {"score": 100},
        "representativeness": {"label": "High"},
        "version": "v1.2",
        "definition": {"parent_sector_labels": ["Information Technology"]},
        "rotation_series": {
            "1M": {
                "current_point": trail[-1],
                "trail_points": trail,
                "source_state": "live",
                "data_mode": "live",
                "formula_version": "relative-return-momentum-v1",
                "normalization_version": "midpoint-100-relative-return-v1",
                "synthetic_point_count": 0,
            }
        },
    }


class StoredReportFixture:
    """Small serializable report used to exercise SQLite immutability only."""

    def __init__(self, report_id: str, summary: str) -> None:
        self.report_id = report_id
        self.generated_at = "2026-07-17T00:00:00+00:00"
        self.generated_time = self.generated_at
        self.market_date = "2026-07-17"
        self.date = self.market_date
        self.executive_summary = summary
        self.semantic_context = {"snapshot_ids": {"theme": "theme-before"}}

    def model_dump(self, **_kwargs: object) -> dict:
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at,
            "generated_time": self.generated_time,
            "market_date": self.market_date,
            "date": self.date,
            "executive_summary": self.executive_summary,
            "semantic_context": self.semantic_context,
        }


class CountingProvider(MockMarketDataProvider):
    def __init__(self) -> None:
        super().__init__()
        self.quote_calls = 0
        self.history_calls = 0

    def get_quote(self, symbol: str):  # type: ignore[no-untyped-def]
        self.quote_calls += 1
        return super().get_quote(symbol)

    def get_history(self, symbol: str, resolution: str = "D", days: int = 240):  # type: ignore[no-untyped-def]
        self.history_calls += 1
        return super().get_history(symbol, resolution=resolution, days=days)


class DailyReportThemeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.section = build_theme_report_section(theme_context())

    def test_canonical_theme_payload_contains_the_published_snapshot_and_two_rows(self) -> None:
        self.assertEqual(self.section["theme_snapshot_id"], "theme-2026-07-17-f8ca1be84c")
        self.assertEqual(self.section["active_theme_count"], 2)
        self.assertEqual([row["display_name"] for row in self.section["leadership"]], ["Cybersecurity", "Memory & Storage"])
        self.assertEqual(self.section["leadership"][0]["absolute_composite_score"], 100.0)
        self.assertEqual(self.section["leadership"][1]["absolute_composite_score"], 62.16)
        self.assertEqual(self.section["definition_versions"], {"cybersecurity": "v1.2", "memory_storage": "v1.2"})

    def test_rotation_payload_preserves_current_points_trails_and_provenance(self) -> None:
        items = self.section["rotation"]["items"]
        self.assertEqual(self.section["rotation"]["selected_interval"], "1M")
        self.assertEqual(len(items), 2)
        self.assertTrue(all(len(item["trail_points"]) == 2 for item in items))
        self.assertTrue(all(item["trail_provenance"]["source_state"] == "live" for item in items))
        report = SimpleNamespace(theme_report=self.section)
        points = theme_rotation_items(report)
        self.assertEqual([(point["label"], len(point["trail"])) for point in points], [("Cybersecurity", 2), ("Memory & Storage", 2)])

    def test_pdf_theme_panels_only_use_the_canonical_report_section(self) -> None:
        report = SimpleNamespace(theme_report=self.section)
        styles = build_visual_report_styles()
        leadership = theme_leadership_panel(report, styles)
        rotation = theme_rotation_panel(report, styles)
        self.assertIn("theme-2026-07-17-f8ca1be84c", leadership[0].getPlainText())
        self.assertIn("Cybersecurity", rotation[-1].getPlainText())
        self.assertIn("Memory & Storage", rotation[-1].getPlainText())
        disclosure = theme_methodology_disclosure(report)
        self.assertIn("two currently active reviewed pilot themes", disclosure)
        self.assertNotIn("unavailable until Phase 4.4D", disclosure)

    def test_theme_snapshot_id_changes_the_report_identity(self) -> None:
        with patch("app.services.report.latest_market_snapshot_id", return_value="market-fixed"), patch(
            "app.services.report.latest_breadth_snapshot_id", return_value="breadth-fixed"
        ), patch("app.services.report.latest_sector_snapshot_id", return_value="sector-fixed"), patch(
            "app.services.report.latest_theme_snapshot_id", side_effect=["theme-a", "theme-b"]
        ):
            first = current_report_identity()
            second = current_report_identity()

        self.assertIn("theme-a", first["cache_key"])
        self.assertIn("theme-b", second["cache_key"])
        self.assertNotEqual(first["cache_key"], second["cache_key"])
        self.assertNotEqual(first["identity_key"], second["identity_key"])

    def test_warm_report_read_returns_the_immutable_payload_without_rebuilding(self) -> None:
        from app.models.market import DailyReportResponse

        immutable_report = DailyReportResponse.model_construct(report_id="daily-warm")
        with patch("app.services.report.latest_market_snapshot_id", return_value="market-fixed"), patch(
            "app.services.report.latest_breadth_snapshot_id", return_value="breadth-fixed"
        ), patch("app.services.report.latest_sector_snapshot_id", return_value="sector-fixed"), patch(
            "app.services.report.latest_theme_snapshot_id", return_value="theme-fixed"
        ), patch("app.services.report.get_daily_report_storage") as storage, patch(
            "app.services.report.get_or_compute"
        ) as cache, patch("app.services.report._build_daily_report_uncached") as build:
            storage.return_value.get_by_identity.return_value = SimpleNamespace(report=immutable_report)
            result = build_daily_report()

        self.assertIs(result, immutable_report)
        cache.assert_not_called()
        build.assert_not_called()
        storage.return_value.mark_latest.assert_called_once()

    def test_report_read_blocks_provider_cache_misses_and_stale_refreshes(self) -> None:
        provider = CountingProvider()
        repository = MarketDataRepository(provider=provider, data_provider="live", cache=MemoryMarketDataCache())
        with report_snapshot_read():
            with self.assertRaises(ReportReadCacheMiss):
                repository.get_history("SPY", days=30)
        self.assertEqual(provider.history_calls, 0)
        self.assertEqual(repository.provider_call_count, 0)

        stale_value = SimpleNamespace(value={"captured": True}, stale=True, age_seconds=15)
        with patch.object(repository.cache, "get", return_value=(None, None)), patch.object(
            repository, "_get_stale_cache_value", return_value=stale_value
        ), patch.object(repository, "_start_background_refresh") as refresh:
            with report_snapshot_read():
                result = repository._get_or_compute("report-test", 60, provider.get_history, lambda value, _age: value, domain="daily_history")
        self.assertEqual(result, {"captured": True})
        refresh.assert_not_called()
        self.assertEqual(provider.history_calls, 0)

    def test_report_read_does_not_publish_an_unavailable_macro_cache_value(self) -> None:
        from app.services.macro_state import build_macro_state

        with patch("app.services.macro_state.get_cached_service_value", return_value=None), patch(
            "app.services.macro_state.get_or_compute"
        ) as compute:
            with report_snapshot_read():
                macro = build_macro_state()

        self.assertEqual(macro["source_state"], "unavailable")
        compute.assert_not_called()

    def test_report_brief_uses_frozen_inputs_without_shared_market_analysis(self) -> None:
        inputs = {
            "market_health": SimpleNamespace(status="Healthy", overall_score=82),
            "market_regime": SimpleNamespace(status="Confirmed Uptrend"),
            "decision_dashboard": SimpleNamespace(playbook=SimpleNamespace(headline="Buy strength", main_risk="Breadth narrows.")),
            "breadth": SimpleNamespace(breadth_status="Healthy", percent_above_50ema=67.5),
            "risk_dashboard": SimpleNamespace(score=35),
            "cap_rotation": SimpleNamespace(leader="Large Cap"),
            "decision_confidence": SimpleNamespace(score=81),
            "sector_dashboard": {"sectors": [{"name": "Technology"}]},
        }

        brief = build_captured_report_ai_summary(inputs)

        self.assertEqual(brief["generated_by"], "captured_report_snapshot")
        self.assertIn("Technology", brief["summary"])
        self.assertEqual(brief["confidence"], 81)

    def test_storage_keeps_historical_payload_immutable_and_moves_only_latest_pointer(self) -> None:
        historical = StoredReportFixture("daily-historical-test", "Historical report must not change.")
        attempted_rewrite = StoredReportFixture("daily-attempted-rewrite", "This rewrite must be ignored.")

        with TemporaryDirectory() as temporary_directory:
            storage = DailyReportStorage(Path(temporary_directory) / "daily_reports.sqlite3")
            with patch(
                "app.reports.storage.DailyReportResponse.model_validate",
                side_effect=lambda payload: SimpleNamespace(**payload),
            ):
                stored = storage.save_if_absent(
                    historical,
                    identity_key="immutable-identity",
                    cache_key="report:daily:historical",
                    schema_version=REPORT_SCHEMA_VERSION,
                )
                unchanged = storage.save_if_absent(
                    attempted_rewrite,
                    identity_key="immutable-identity",
                    cache_key="report:daily:historical",
                    schema_version=REPORT_SCHEMA_VERSION,
                )
                latest = storage.latest()

            self.assertEqual(stored.report.report_id, "daily-historical-test")
            self.assertEqual(unchanged.report.report_id, "daily-historical-test")
            self.assertEqual(unchanged.report.executive_summary, "Historical report must not change.")
            self.assertEqual(latest.report.report_id, "daily-historical-test")


if __name__ == "__main__":
    unittest.main()
