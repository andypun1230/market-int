import re
import unittest

from app.reports.document import ReportDocument
from app.reports.document_builder import build_report_document, moving_average
from app.reports.pdf_v6 import generate_report_pdf_v6, spread_label_positions


def report_fixture(*, previous: bool = False) -> tuple[dict, dict | None]:
    closes = [100 + index * 0.4 for index in range(80)]
    report = {
        "report_id": "daily-2026-07-17-v6-test",
        "report_pdf_format_version": "daily-report-pdf-v6",
        "market_date": "2026-07-17",
        "date": "2026-07-17",
        "generated_at": "2026-07-18T01:15:00+00:00",
        "market_regime": "Selective Risk",
        "market_health": {"overall_score": 68},
        "report_snapshot": {"historicalMetrics": {"breadth": 54}},
        "recommendation_confidence": {"score": 72},
        "sector_leaders": ["Technology"],
        "semantic_context": {"snapshot_ids": {"market": "market-test", "breadth": "unavailable", "sector": "unavailable", "theme": "unavailable"}},
        "index_histories": {symbol: closes for symbol in ("SPY", "QQQ", "IWM", "DIA")},
        "macro": {"source_state": "test"},
        "watchlist_summary": {
            "items": [
                {
                    "symbol": "STALE",
                    "change_percent": 2.5,
                    "overall_score": 88,
                    "signal": "buy",
                    "setup": "Breakout",
                    "source_state": "stale",
                    "missing_sections": ["volume"],
                    "updated_at": "2026-07-15T20:00:00+00:00",
                },
                {
                    "symbol": "READY",
                    "change_percent": 1.2,
                    "overall_score": 79,
                    "signal": "buy",
                    "setup": "Base breakout",
                    "source_state": "live",
                    "missing_sections": [],
                    "updated_at": "2026-07-17T20:00:00+00:00",
                },
            ]
        },
        "stock_charts": [
            {"symbol": "READY", "price_history": closes, "volumes": [1_000_000 + index * 1000 for index in range(80)], "support": 120, "resistance": 132, "breakout": 133, "source": "test", "reason": "READY remains above supported trend references."}
        ],
        "economic_calendar": [{"event": "Invented CPI tomorrow", "date": "T+1"}],
    }
    previous_snapshot = {"overallThesis": "Prior conditional thesis."} if previous else None
    return report, previous_snapshot


class ReportV6DocumentTests(unittest.TestCase):
    def test_registry_integrity_and_stale_security_gating(self) -> None:
        report, previous = report_fixture()
        document = build_report_document(report, previous)
        validated = ReportDocument.model_validate(document.model_dump(mode="json"))
        evidence_ids = {item.evidence_id for item in validated.evidence}
        source_ids = {item.source_id for item in validated.sources}

        self.assertTrue(validated.figures)
        self.assertTrue(all(set(claim.evidence_ids).issubset(evidence_ids) for claim in validated.claims))
        self.assertTrue(all(set(figure.source_ids).issubset(source_ids) for figure in validated.figures))
        self.assertFalse(next(item for item in validated.securities if item.symbol == "STALE").actionable)
        self.assertTrue(next(item for item in validated.securities if item.symbol == "READY").actionable)

    def test_security_commentary_uses_the_same_supported_levels_as_its_chart(self) -> None:
        report, previous = report_fixture()
        document = build_report_document(report, previous)
        security = next(item for item in document.securities if item.symbol == "READY")
        figure = next(item for item in document.figures if item.figure_id == security.figure_id)
        evidence = {item.evidence_id: item for item in document.evidence}

        self.assertIn("breakout at $133.00", security.confirmation)
        self.assertIn("support at $120.00", security.invalidation)
        self.assertIn("support at $120.00", security.risk_considerations)
        self.assertEqual(security.confirmation, figure.confirmation_condition)
        self.assertIn(security.invalidation, figure.risk_condition)
        self.assertEqual(
            {evidence[item_id].metric: evidence[item_id].current_value for item_id in security.evidence_ids if item_id in evidence},
            {
                "READY daily change": 1.2,
                "READY overall score": 79.0,
                "READY support level": 120.0,
                "READY resistance level": 132.0,
                "READY breakout level": 133.0,
            },
        )

    def test_unsourced_events_and_unsupported_causality_are_absent(self) -> None:
        report, previous = report_fixture()
        document = build_report_document(report, previous)
        payload = document.model_dump(mode="json")
        all_prose = " ".join(
            [document.thesis.concise_thesis]
            + [claim.statement for claim in document.claims]
            + [paragraph for section in document.sections for paragraph in section.paragraphs]
        )

        self.assertNotIn("events", payload)
        self.assertNotIn("Invented CPI tomorrow", str(payload))
        self.assertIsNone(re.search(r"\b(caused|drove|investors sold because)\b", all_prose, flags=re.IGNORECASE))
        self.assertTrue(any("yield" in item.lower() for item in document.limitations))
        self.assertTrue(any("spread" in item.lower() for item in document.limitations))

    def test_baseline_and_previous_report_behavior(self) -> None:
        baseline_report, _ = report_fixture()
        baseline = build_report_document(baseline_report)
        compared_report, previous = report_fixture(previous=True)
        compared = build_report_document(compared_report, previous)

        baseline_text = " ".join(paragraph for section in baseline.sections for paragraph in section.paragraphs)
        self.assertEqual(baseline_text.count("Baseline established."), 1)
        self.assertFalse(baseline.previous_report_available)
        self.assertTrue(compared.previous_report_available)
        self.assertEqual(compared.thesis.previous_thesis, "Prior conditional thesis.")

    def test_v6_pdf_renders_from_the_document_only(self) -> None:
        report, previous = report_fixture(previous=True)
        document = build_report_document(report, previous)
        pdf = generate_report_pdf_v6(document).getvalue()

        self.assertTrue(pdf.startswith(b"%PDF-"))
        self.assertGreater(len(pdf), 10_000)
        self.assertIn(b"/Title (Daily Market Intelligence Briefing)", pdf)

    def test_moving_average_requires_the_full_window(self) -> None:
        self.assertEqual(moving_average([1, 2, 3], 2), [None, 1.5, 2.5])
        self.assertEqual(moving_average([1, 2], 3), [None, None])

    def test_close_reference_labels_are_spaced_without_moving_their_lines(self) -> None:
        positions = spread_label_positions([100.0, 101.0, 102.0], lower=90.0, upper=110.0, min_gap=7.0)

        self.assertGreaterEqual(min(positions), 90.0)
        self.assertLessEqual(max(positions), 110.0)
        self.assertGreaterEqual(positions[1] - positions[0], 7.0)
        self.assertGreaterEqual(positions[2] - positions[1], 7.0)


if __name__ == "__main__":
    unittest.main()
