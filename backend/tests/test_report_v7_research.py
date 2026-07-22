from __future__ import annotations

import re
import unittest
from unittest.mock import patch

from app.reports.document import ReportDocument
from app.reports.document_builder import build_report_document
from app.reports.pdf_v6 import generate_report_pdf_v6, spread_label_positions
from app.reports.pdf_v7 import generate_report_pdf_v7
from app.reports.research import (
    PRIMARY_MATERIALITY_THRESHOLD,
    RESEARCH_SCORE_WEIGHTS,
    ResearchCandidateEngine,
)
from tests.fixtures.report_v7 import report_v7_fixture


FIXTURE_NAMES = [
    "user-saved-leading-theme",
    "user-saved-weakening-theme",
    "market-leading-theme-no-overlap",
    "market-lagging-sector-deterioration",
    "individual-saved-stock-major-change",
    "multiple-saved-stocks-one-theme",
    "saved-stock-diverging-from-leading-theme",
    "no-qualifying-focus",
    "empty-watchlist",
    "stale-watchlist",
    "partial-taxonomy",
    "missing-breadth",
    "first-report",
    "previous-report-comparison",
    "weekend-report",
    "mixed-source-report",
]


class ReportV7ResearchTests(unittest.TestCase):
    def document(self, name: str) -> ReportDocument:
        report, previous = report_v7_fixture(name)
        return build_report_document(report, previous)

    def test_all_sixteen_required_fixtures_build_and_validate(self) -> None:
        for name in FIXTURE_NAMES:
            with self.subTest(name=name):
                document = self.document(name)
                validated = ReportDocument.model_validate(document.model_dump(mode="json"))
                self.assertEqual(validated.pdf_format_version, "daily-report-pdf-v7")
                self.assertEqual(validated.figure_count, len(validated.figures))

    def test_leader_laggard_personalized_and_no_focus_paths(self) -> None:
        leader = self.document("user-saved-leading-theme").research_focus
        laggard = self.document("market-lagging-sector-deterioration").research_focus
        no_overlap = self.document("market-leading-theme-no-overlap").research_focus
        no_focus_document = self.document("no-qualifying-focus")

        self.assertIsNotNone(leader)
        self.assertEqual(leader.direction, "leading")
        self.assertEqual(leader.user_relevance.tier, "high")
        self.assertIsNotNone(laggard)
        self.assertIn(laggard.direction, {"weakening", "lagging", "breakdown"})
        self.assertIsNotNone(no_overlap)
        self.assertEqual(no_overlap.user_relevance.tier, "low")
        self.assertIsNone(no_focus_document.research_focus)
        self.assertEqual(no_focus_document.research_inquiry.status, "no_focus")
        self.assertTrue(no_focus_document.research_inquiry.question.endswith("?"))
        self.assertIn("research-focus", {section.section_id for section in no_focus_document.sections})

    def test_fixed_weights_thresholds_and_missing_dimension_policy(self) -> None:
        self.assertEqual(sum(RESEARCH_SCORE_WEIGHTS.values()), 1.0)
        self.assertEqual(PRIMARY_MATERIALITY_THRESHOLD, 60.0)
        document = self.document("user-saved-leading-theme")
        candidate = next(item for item in document.research_candidates if item.candidate_id == document.research_focus.candidate_id)
        self.assertIn("volume_confirmation", candidate.score.missing_dimensions)
        self.assertEqual(candidate.score.weighted_contributions["volume_confirmation"], 0)
        self.assertLessEqual(candidate.score.weighted_contributions["user_relevance"], 15)

    def test_ranking_is_deterministic_and_ties_use_stable_candidate_id(self) -> None:
        report, previous = report_v7_fixture("user-saved-leading-theme")
        first = ResearchCandidateEngine(report, previous).build()
        second = ResearchCandidateEngine(report, previous).build()
        self.assertEqual(
            [(item.candidate_id, item.score.total) for item in first.candidates],
            [(item.candidate_id, item.score.total) for item in second.candidates],
        )

        duplicated = dict(report)
        duplicated["theme_intelligence"] = dict(report["theme_intelligence"])
        original = dict(report["theme_intelligence"]["items"][0])
        alpha = dict(original, theme_id="alpha_tie", display_name="Alpha Tie")
        beta = dict(original, theme_id="beta_tie", display_name="Beta Tie")
        duplicated["theme_intelligence"]["items"] = [beta, alpha]
        duplicated["research_preferences"] = {"saved_stocks": [], "saved_sectors": [], "saved_themes": []}
        duplicated["watchlist_summary"] = {"source_state": "live", "items": [], "symbols_requested": []}
        tied = ResearchCandidateEngine(duplicated, None).build().candidates
        tied_theme_ids = [item.candidate_id for item in tied if item.category == "theme"]
        self.assertEqual(tied_theme_ids, sorted(tied_theme_ids))

    def test_personalization_changes_relevance_but_cannot_create_market_evidence(self) -> None:
        personalized = self.document("user-saved-leading-theme").research_focus
        market_led = self.document("market-leading-theme-no-overlap").research_focus
        self.assertEqual(personalized.subject, market_led.subject)
        self.assertEqual(personalized.user_relevance.score, 100)
        self.assertEqual(market_led.user_relevance.score, 0)
        self.assertGreater(personalized.priority_score, market_led.priority_score)
        self.assertLessEqual(personalized.priority_score - market_led.priority_score, 15)

    def test_saved_preferences_are_normalized_and_part_of_immutable_identity(self) -> None:
        from app.api.report import parse_saved_values
        from app.services import report as report_service

        self.assertEqual(parse_saved_values(" crwd, PANW,crwd "), ["crwd", "PANW"])
        normalized = report_service.normalize_research_preferences(
            [" crwd", "PANW", "CRWD"], ["Information Technology"], ["Cyber-Security"]
        )
        self.assertEqual(normalized, {
            "saved_stocks": ["CRWD", "PANW"],
            "saved_sectors": ["information_technology"],
            "saved_themes": ["cyber_security"],
        })
        with (
            patch("app.services.report.latest_market_snapshot_id", return_value="market"),
            patch("app.services.report.latest_breadth_snapshot_id", return_value="breadth"),
            patch("app.services.report.latest_sector_snapshot_id", return_value="sector"),
            patch("app.services.report.latest_theme_snapshot_id", return_value="theme"),
        ):
            default_identity = report_service.current_report_identity()
            saved_identity = report_service.current_report_identity(saved_stocks=["CRWD"])
        self.assertNotEqual(default_identity["cache_key"], saved_identity["cache_key"])
        self.assertNotEqual(default_identity["identity_key"], saved_identity["identity_key"])

    def test_stale_saved_data_neither_elevates_nor_creates_actionable_focus(self) -> None:
        report, previous = report_v7_fixture("stale-watchlist")
        result = ResearchCandidateEngine(report, previous).build()
        theme = next(item for item in result.candidates if item.candidate_id == "theme:cybersecurity")
        self.assertTrue(theme.user_relevance.stale)
        self.assertEqual(theme.user_relevance.score, 0)
        self.assertIsNone(result.decision.selected_candidate_id)

    def test_selection_explanation_and_evidence_registry_are_auditable(self) -> None:
        document = self.document("previous-report-comparison")
        focus = document.research_focus
        evidence_ids = {item.evidence_id for item in document.evidence}
        candidate = next(item for item in document.research_candidates if item.candidate_id == focus.candidate_id)

        self.assertTrue(document.research_selection.selected_because)
        self.assertGreaterEqual(len(document.research_selection.competing_candidates), 2)
        self.assertTrue(set(focus.evidence_ids).issubset(evidence_ids))
        self.assertTrue(set(candidate.evidence_ids).issubset(evidence_ids))
        for suffix in (
            "materiality-threshold",
            "qualifying-constituents",
            "supported-figure-types",
            "contribution-market-significance",
            "contribution-leadership-weakness-magnitude",
            "contribution-user-relevance",
            "weight-user-relevance",
        ):
            self.assertIn(f"research-theme-cybersecurity-{suffix}", evidence_ids)

    def test_saved_security_levels_and_chart_annotations_use_exact_evidence(self) -> None:
        document = self.document("user-saved-leading-theme")
        evidence = {item.evidence_id: item for item in document.evidence}
        self.assertTrue(document.research_focus.affected_securities)
        for impact in document.research_focus.affected_securities:
            level_ids = [item_id for item_id in impact.evidence_ids if item_id.endswith("key-level")]
            self.assertEqual(len(level_ids), 1)
            level = evidence[level_ids[0]].current_value
            self.assertEqual(impact.key_level, f"${level:,.2f}")
        for figure in document.figures:
            for annotation in figure.annotations:
                self.assertIn(annotation.evidence_id, evidence)
                self.assertNotIn(annotation.freshness.lower(), {"stale", "unavailable"})
            for reference in figure.reference_lines:
                self.assertIn(reference["evidence_id"], evidence)
                self.assertEqual(float(reference["value"]), float(evidence[reference["evidence_id"]].current_value))

    def test_taxonomy_is_membership_only_and_saved_items_are_not_called_positions(self) -> None:
        document = self.document("partial-taxonomy")
        focus_payload = document.research_focus.model_dump(mode="json")
        text = str(focus_payload).lower()
        self.assertNotRegex(text, r"\bpositions?\b")
        self.assertFalse(any(link.get("relationship_type") == "validated_supply_chain" for link in document.research_focus.taxonomy_chain))
        self.assertTrue(all("supplier" not in str(link).lower() and "customer" not in str(link).lower() for link in document.research_focus.taxonomy_chain))
        self.assertNotRegex(" ".join(document.research_focus.prose_sections.values()), r"(?i)because of (earnings|news|a catalyst)")

    def test_market_timeline_requires_three_reliable_observations(self) -> None:
        report, previous = report_v7_fixture("user-saved-leading-theme")
        report["market_evolution"]["points"] = report["market_evolution"]["points"][:2]
        document = build_report_document(report, previous)
        self.assertEqual(document.market_timeline, [])
        self.assertNotIn("market-evolution", {figure.figure_id for figure in document.figures})

    def test_annotation_label_spacing_stays_inside_bounds(self) -> None:
        positions = spread_label_positions([100, 100.1, 100.2, 101], lower=90, upper=110, min_gap=5)
        self.assertGreaterEqual(min(positions), 90)
        self.assertLessEqual(max(positions), 110)
        self.assertTrue(all(right - left >= 5 for left, right in zip(positions, positions[1:])))

    def test_v7_and_legacy_v6_document_renderers_remain_available(self) -> None:
        document = self.document("user-saved-leading-theme")
        v7 = generate_report_pdf_v7(document).getvalue()
        v6_document = document.model_copy(update={"pdf_format_version": "daily-report-pdf-v6", "research_focus": None})
        v6 = generate_report_pdf_v6(v6_document).getvalue()
        self.assertTrue(v7.startswith(b"%PDF-"))
        self.assertTrue(v6.startswith(b"%PDF-"))
        self.assertGreater(len(v7), 20_000)
        self.assertGreater(len(v6), 20_000)
        self.assertNotRegex(v7.decode("latin1", errors="ignore"), re.compile(r"/Count 0\b"))

    def test_legacy_v6_regeneration_without_a_stored_document_keeps_v6_label(self) -> None:
        from io import BytesIO

        from app.models.market import DailyReportResponse
        from app.services.report import generate_daily_report_pdf

        report, _ = report_v7_fixture("no-qualifying-focus")
        legacy = DailyReportResponse.model_construct(**{
            **report,
            "report_pdf_format_version": "daily-report-pdf-v6",
            "report_document": None,
        })
        with patch("app.services.report.generate_report_pdf_v6", return_value=BytesIO(b"%PDF-v6")) as renderer:
            output = generate_daily_report_pdf(legacy)
        self.assertEqual(output.getvalue(), b"%PDF-v6")
        self.assertEqual(renderer.call_args.args[0]["pdf_format_version"], "daily-report-pdf-v6")


if __name__ == "__main__":
    unittest.main()
