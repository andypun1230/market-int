import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


class VisualReportPdfTests(unittest.TestCase):
    def setUp(self) -> None:
        self._provider_environment = {
            name: os.environ.get(name)
            for name in ("DATA_PROVIDER", "MARKET_DATA_PROVIDER", "QUOTE_PROVIDER", "HISTORY_PROVIDER")
        }
        self._storage_environment = {
            name: os.environ.get(name)
            for name in ("DAILY_REPORT_DB_PATH", "PERSISTENT_CACHE_DB_PATH")
        }
        self._temporary_directory = TemporaryDirectory()
        os.environ["DATA_PROVIDER"] = "mock"
        os.environ["MARKET_DATA_PROVIDER"] = "mock"
        os.environ["QUOTE_PROVIDER"] = "mock"
        os.environ["HISTORY_PROVIDER"] = "mock"
        os.environ["DAILY_REPORT_DB_PATH"] = str(Path(self._temporary_directory.name) / "daily_reports.sqlite3")
        os.environ["PERSISTENT_CACHE_DB_PATH"] = str(Path(self._temporary_directory.name) / "market_cache.sqlite3")

        from app.cache.persistent_cache import reset_persistent_cache_state
        from app.reports.storage import reset_daily_report_storage
        from app.services.market_data_repository import reset_market_data_repository
        from app.services.service_cache import invalidate_service_cache

        reset_persistent_cache_state()
        reset_daily_report_storage()
        reset_market_data_repository()
        invalidate_service_cache()

    def tearDown(self) -> None:
        from app.cache.persistent_cache import reset_persistent_cache_state
        from app.reports.storage import reset_daily_report_storage
        from app.services.market_data_repository import reset_market_data_repository
        from app.services.service_cache import invalidate_service_cache

        invalidate_service_cache()
        reset_market_data_repository()
        reset_daily_report_storage()
        reset_persistent_cache_state()
        for name, value in self._provider_environment.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        for name, value in self._storage_environment.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        self._temporary_directory.cleanup()

    def test_visual_pdf_is_valid_and_contains_report_sections(self) -> None:
        from app.models.market import DailyReportResponse
        from app.services.report import (
            build_daily_report,
            build_page_insights,
            build_report_narrative_context,
            build_risk_triggers,
            build_watchlist_feature_cards,
            generate_daily_report_pdf,
            generate_daily_report_pdf_v5,
        )

        raw_report = build_daily_report()
        report = DailyReportResponse(**raw_report) if isinstance(raw_report, dict) else raw_report
        pdf = generate_daily_report_pdf(report).getvalue()

        self.assertTrue(pdf.startswith(b"%PDF-"))
        self.assertGreater(len(pdf), 20_000)
        self.assertGreaterEqual(len(report.indexes), 4)
        self.assertIn("SPY", report.index_histories)
        self.assertGreater(len(report.index_histories["SPY"]), 100)
        self.assertTrue((report.watchlist_summary or {}).get("items"))
        self.assertTrue((report.sector_dashboard or {}).get("sectors"))
        self.assertTrue(report.stock_charts)
        self.assertTrue(report.report_id)
        self.assertTrue(report.report_snapshot)
        self.assertTrue(report.report_narrative)
        self.assertTrue(report.signal_convergence)
        self.assertTrue(report.hidden_warnings)
        self.assertTrue(report.market_conviction)
        self.assertTrue(report.decision_checklist)
        self.assertTrue(report.recommendation_confidence)
        self.assertTrue(report.scenario_plan)
        self.assertIsInstance(report.signal_relationships, list)
        self.assertTrue(report.trade_off_analysis)
        self.assertTrue(report.report_commentary)
        self.assertTrue(report.previous_playbook_review)
        self.assertTrue(report.market_evolution)

        self.assertEqual(report.title, "Daily Market Intelligence Briefing")
        self.assertEqual(report.report_schema_version, "daily-report-v23")
        self.assertEqual(report.report_pdf_format_version, "daily-report-pdf-v7")
        self.assertIsNotNone(report.report_document)
        self.assertEqual((report.report_document or {}).get("pdf_format_version"), "daily-report-pdf-v7")
        self.assertEqual((report.report_document or {}).get("figure_count"), len((report.report_document or {}).get("figures") or []))
        self.assertIn(b"/Title (Daily Market Intelligence Briefing)", pdf)
        self.assertGreaterEqual(pdf.count(b"/Type /Page"), 8)
        self.assertTrue(report.economic_calendar)
        self.assertNotIn("events", report.report_document or {})
        self.assertIsNotNone(report.risk_dashboard)
        self.assertIsNotNone(report.fear_greed)

        legacy_pdf = generate_daily_report_pdf_v5(report.model_copy(update={"report_pdf_format_version": "daily-report-pdf-v5", "report_document": None})).getvalue()
        self.assertTrue(legacy_pdf.startswith(b"%PDF-"))
        self.assertGreater(len(legacy_pdf), 20_000)

        context = build_report_narrative_context(report)
        for page in ["playbook", "health", "leadership", "risk", "watchlist", "macro", "methodology"]:
            insights = build_page_insights(report, context, page)
            self.assertGreaterEqual(len(insights), 3)
            self.assertLessEqual(len(insights), 5)
            self.assertTrue(all("..." not in insight for insight in insights))

        self.assertEqual(len(build_watchlist_feature_cards(report)), 3)
        self.assertLessEqual(len(build_risk_triggers(report)), 5)


if __name__ == "__main__":
    unittest.main()
