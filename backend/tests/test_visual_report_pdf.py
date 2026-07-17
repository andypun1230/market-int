import os
import unittest


class VisualReportPdfTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["DATA_PROVIDER"] = "mock"
        os.environ["MARKET_DATA_PROVIDER"] = "mock"
        os.environ["QUOTE_PROVIDER"] = "mock"
        os.environ["HISTORY_PROVIDER"] = "mock"

    def test_visual_pdf_is_valid_and_contains_report_sections(self) -> None:
        from app.models.market import DailyReportResponse
        from app.services.report import (
            build_daily_report,
            build_page_insights,
            build_report_narrative_context,
            build_risk_triggers,
            build_watchlist_feature_cards,
            generate_daily_report_pdf,
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
        self.assertTrue(report.signal_relationships)
        self.assertTrue(report.trade_off_analysis)
        self.assertTrue(report.report_commentary)
        self.assertTrue(report.previous_playbook_review)
        self.assertTrue(report.market_evolution)

        self.assertIn(b"/Title (Daily Market Report)", pdf)
        self.assertGreaterEqual(pdf.count(b"/Type /Page"), 6)
        self.assertTrue(report.economic_calendar)
        self.assertIsNotNone(report.risk_dashboard)
        self.assertIsNotNone(report.fear_greed)

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
