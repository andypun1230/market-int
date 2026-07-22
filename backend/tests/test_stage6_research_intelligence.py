from __future__ import annotations

from copy import deepcopy
import unittest

from pydantic import ValidationError

from app.reports.document import FigureAnnotation, ReportDocument, ResearchRelationshipEdge
from app.reports.document_builder import build_report_document
from app.reports.pdf_v7 import generate_report_pdf_v7
from tests.fixtures.report_v7 import report_v7_fixture


STAGE6_CASES = {
    "leading-theme": "market-leading-theme-no-overlap",
    "lagging-theme": "market-lagging-theme",
    "no-focus": "no-qualifying-focus",
    "weekend": "weekend-report",
    "mixed": "mixed-source-report",
    "personalized": "user-saved-leading-theme",
}

ALLOWED_RELATIONSHIPS = {
    "sector_hierarchy",
    "theme_hierarchy",
    "relative_performance",
    "benchmark_relationship",
    "user_watchlist_overlap",
    "validated_taxonomy",
    "validated_supply_chain",
}


class Stage6ResearchIntelligenceTests(unittest.TestCase):
    def document(self, fixture_name: str) -> ReportDocument:
        report, previous = report_v7_fixture(fixture_name)
        return build_report_document(report, previous)

    def test_six_required_cases_build_with_fixed_v7_architecture(self) -> None:
        expected_sections = [
            "cover", "executive-summary", "index-structure", "breadth", "leadership",
            "research-focus", "macro", "risk", "scenarios", "watchlist",
            "operating-plan", "methodology",
        ]
        for label, fixture_name in STAGE6_CASES.items():
            with self.subTest(case=label):
                document = self.document(fixture_name)
                self.assertEqual(document.document_version, "report-document-v2")
                self.assertEqual(document.pdf_format_version, "daily-report-pdf-v7")
                self.assertEqual([section.section_id for section in document.sections], expected_sections)
                self.assertTrue(all(section.question and section.question.endswith("?") for section in document.sections))
                self.assertTrue(document.research_inquiry.question.endswith("?"))
                self.assertLessEqual(len(document.market_timeline), 10)
                self.assertEqual(len(document.market_timeline), 10)
                ReportDocument.model_validate(document.model_dump(mode="json"))

    def test_qualified_focus_contains_all_ten_research_components(self) -> None:
        focus = self.document("user-saved-leading-theme").research_focus
        self.assertIsNotNone(focus)
        self.assertTrue(focus.question.endswith("?"))
        self.assertTrue(focus.executive_answer)
        self.assertTrue(focus.evidence_matrix)
        self.assertTrue(focus.counter_thesis)
        self.assertGreaterEqual(len(focus.figure_ids), 4)
        self.assertTrue(focus.relationship_graph.edges)
        self.assertTrue(focus.leading_securities)
        self.assertTrue(focus.lagging_securities)
        self.assertTrue(focus.execution_implications)
        self.assertTrue(focus.conclusion_change_conditions)

    def test_stage6_validation_rejects_blank_core_focus_research(self) -> None:
        payload = self.document("user-saved-leading-theme").model_dump(mode="json")
        mutations = {
            "main thesis": lambda focus: focus.__setitem__("main_thesis", "   "),
            "counter thesis": lambda focus: focus.__setitem__("counter_thesis", ""),
            "focus evidence": lambda focus: focus.__setitem__("evidence_ids", []),
            "selection reasons": lambda focus: focus.__setitem__("why_selected", []),
            "key evidence": lambda focus: focus.__setitem__("key_evidence", []),
            "confirmation conditions": lambda focus: focus.__setitem__("confirmation_conditions", []),
            "invalidation conditions": lambda focus: focus.__setitem__("invalidation_conditions", []),
        }
        for label, mutate in mutations.items():
            with self.subTest(field=label):
                candidate = deepcopy(payload)
                mutate(candidate["research_focus"])
                with self.assertRaises(ValidationError):
                    ReportDocument.model_validate(candidate)

    def test_stage6_validation_allows_honest_empty_relationship_and_security_fallbacks(self) -> None:
        payload = self.document("user-saved-leading-theme").model_dump(mode="json")
        payload["research_focus"]["leading_securities"] = []
        payload["research_focus"]["lagging_securities"] = []
        payload["research_focus"]["relationship_graph"] = {"nodes": [], "edges": []}

        validated = ReportDocument.model_validate(payload)

        self.assertEqual(validated.research_focus.leading_securities, [])
        self.assertEqual(validated.research_focus.lagging_securities, [])
        self.assertEqual(validated.research_focus.relationship_graph.nodes, [])
        self.assertEqual(validated.research_focus.relationship_graph.edges, [])

    def test_questions_reflect_leading_and_lagging_evidence(self) -> None:
        leader = self.document("market-leading-theme-no-overlap").research_focus
        laggard = self.document("market-lagging-theme").research_focus
        self.assertIn("leading", leader.question.lower())
        self.assertEqual(laggard.direction, "lagging")
        self.assertIn("temporary or structural", laggard.question.lower())

    def test_named_leadership_and_sector_influence_graphics_are_emitted_when_applicable(self) -> None:
        leadership = next(
            item for item in self.document("user-saved-leading-theme").figures
            if item.figure_id == "sector-return-heatmap"
        )
        self.assertEqual(leadership.chart_type, "leadership_matrix")
        sector_document = self.document("market-lagging-sector-deterioration")
        relationship = next(item for item in sector_document.figures if item.figure_id == "research-chain")
        self.assertEqual(relationship.chart_type, "sector_influence_map")

    def test_no_focus_still_answers_a_research_question_without_inventing_a_subject(self) -> None:
        document = self.document("no-qualifying-focus")
        self.assertIsNone(document.research_focus)
        self.assertEqual(document.research_inquiry.status, "no_focus")
        self.assertIn("no candidate", document.research_inquiry.executive_answer.lower())
        section = next(item for item in document.sections if item.section_id == "research-focus")
        self.assertEqual(section.figure_ids, ["research-priority-comparison"])

    def test_evidence_quality_is_discrete_and_not_a_probability(self) -> None:
        quality = self.document("user-saved-leading-theme").research_focus.evidence_quality
        values = {quality.label, quality.freshness, quality.breadth, quality.participation, quality.completeness, quality.consistency}
        self.assertTrue(values.issubset({"High", "Medium", "Low"}))
        self.assertNotIn("probability", str(quality.model_dump()).lower())

    def test_evidence_matrix_and_relationships_reference_registered_evidence(self) -> None:
        document = self.document("user-saved-leading-theme")
        focus = document.research_focus
        evidence_ids = {item.evidence_id for item in document.evidence}
        self.assertIn("supports", {item.stance for item in focus.evidence_matrix})
        self.assertIn("neutral", {item.stance for item in focus.evidence_matrix})
        for row in focus.evidence_matrix:
            self.assertTrue(set(row.evidence_ids).issubset(evidence_ids))
        for edge in focus.relationship_graph.edges:
            self.assertIn(edge.relationship_type, ALLOWED_RELATIONSHIPS)
            self.assertTrue(set(edge.evidence_ids).issubset(evidence_ids))
        self.assertFalse(any(edge.relationship_type == "validated_supply_chain" for edge in focus.relationship_graph.edges))

    def test_supply_chain_requires_explicit_structured_mapping(self) -> None:
        with self.assertRaises(ValidationError):
            ResearchRelationshipEdge(
                relationship_id="bad",
                source_node_id="a",
                target_node_id="b",
                relationship_type="validated_supply_chain",
                label="unsupported",
                mapping_source="",
                structured_data=False,
                evidence_ids=["evidence"],
            )
        report, previous = report_v7_fixture("user-saved-leading-theme")
        report["validated_relationships"] = [{
            "relationship_type": "validated_supply_chain",
            "source_symbol": "CRWD",
            "target_symbol": "PANW",
            "label": "Structured test relationship",
            "mapping_source": "fixture-relationship-master",
            "structured_data": True,
        }]
        document = build_report_document(report, previous)
        supply_edges = [edge for edge in document.research_focus.relationship_graph.edges if edge.relationship_type == "validated_supply_chain"]
        self.assertEqual(len(supply_edges), 1)
        self.assertTrue(supply_edges[0].structured_data)

    def test_leader_laggard_constituents_are_ranked_from_registered_metrics(self) -> None:
        focus = self.document("user-saved-leading-theme").research_focus
        leader_values = [float(item.metric_value) for item in focus.leading_securities]
        laggard_values = [float(item.metric_value) for item in focus.lagging_securities]
        self.assertEqual(leader_values, sorted(leader_values, reverse=True))
        self.assertLessEqual(max(laggard_values), min(leader_values))

    def test_weekend_continuity_retains_latest_durable_session(self) -> None:
        focus = self.document("weekend-report").research_focus
        self.assertIn("No new market session", focus.research_evolution.today)
        self.assertTrue(focus.research_evolution.tomorrow.startswith("Next test:"))
        self.assertEqual(focus.research_evolution.previous_report_date, "2026-07-20")
        self.assertEqual(focus.research_evolution.previous_focus, "Cybersecurity")
        self.assertEqual(focus.research_evolution.status, "Follow-up")
        self.assertNotIn("First report", focus.research_evolution.yesterday)

    def test_explicit_timeline_focus_prevents_a_false_first_report_baseline(self) -> None:
        document = self.document("market-leading-theme-no-overlap")
        focus = document.research_focus
        prior_timeline_focus = next(
            item.research_focus for item in reversed(document.market_timeline[:-1]) if item.research_focus
        )
        self.assertEqual(focus.research_evolution.previous_focus, prior_timeline_focus)
        self.assertNotIn("First report", focus.research_evolution.yesterday)

    def test_cover_summary_copy_does_not_repeat_the_full_research_answer(self) -> None:
        document = self.document("user-saved-leading-theme")
        executive = next(item for item in document.sections if item.section_id == "executive-summary")
        self.assertNotIn(document.research_inquiry.executive_answer, executive.paragraphs)
        self.assertTrue(any("Research priority:" in item for item in executive.paragraphs))

    def test_empty_watchlist_has_an_explicit_no_selection_state(self) -> None:
        document = self.document("no-qualifying-focus")
        section = next(item for item in document.sections if item.section_id == "watchlist")
        self.assertFalse(section.security_ids)
        self.assertIn("No frozen saved-security records", section.paragraphs[0])

    def test_selected_security_research_is_complete_and_bounded(self) -> None:
        document = self.document("user-saved-leading-theme")
        selected = [item for item in document.securities if item.selected_for_research]
        self.assertGreater(len(selected), 0)
        self.assertLessEqual(len(selected), 4)
        for security in selected:
            self.assertTrue(security.why_here)
            self.assertTrue(security.context)
            self.assertTrue(security.sector)
            self.assertTrue(security.themes)
            self.assertTrue(security.execution_consideration)
            self.assertTrue(security.figure_id)
            if security.actionable:
                self.assertIn("Selection alone is not an entry", security.execution_consideration)
                figure = next(item for item in document.figures if item.figure_id == security.figure_id)
                self.assertNotIn("remains a monitoring classification", figure.interpretation)

    def test_sample_security_research_profiles_are_visibly_distinct(self) -> None:
        report, previous = report_v7_fixture("user-saved-leading-theme")
        charts = {item["symbol"]: item for item in report["stock_charts"]}
        self.assertEqual(charts["CRWD"]["breakout"], 136.15)
        self.assertEqual(len({tuple(charts[symbol]["price_history"]) for symbol in ("CRWD", "PANW", "FTNT")}), 3)
        self.assertEqual(
            len({(charts[symbol]["support"], charts[symbol]["resistance"], charts[symbol]["breakout"]) for symbol in ("CRWD", "PANW", "FTNT")}),
            3,
        )

        document = build_report_document(report, previous)
        selected = {item.symbol: item for item in document.securities if item.selected_for_research}
        self.assertEqual(set(selected), {"CRWD", "PANW", "FTNT"})
        self.assertEqual(len({item.setup_state for item in selected.values()}), 3)
        self.assertEqual(len({item.relative_strength for item in selected.values()}), 3)
        self.assertEqual(len({item.volume_condition for item in selected.values()}), 3)
        self.assertEqual(len({item.confirmation_level for item in selected.values()}), 3)
        self.assertEqual(len({item.invalidation_level for item in selected.values()}), 3)

    def test_stage6_annotations_are_evidence_linked_and_future_arrows_are_rejected(self) -> None:
        report, previous = report_v7_fixture("user-saved-leading-theme")
        first_chart = report["stock_charts"][0]
        first_chart["breakout"] = first_chart["price_history"][-1] - 0.5
        first_chart["validated_annotations"] = [
            {"annotation_type": "pivot", "label": "Observed pivot", "value": first_chart["price_history"][-10], "point_index": 90, "date": "2026-07-15"},
            {"annotation_type": "gap", "label": "Observed gap", "value": first_chart["price_history"][-8], "point_index": 92, "date": "2026-07-16"},
            {"annotation_type": "trendline", "label": "Validated trendline", "value": first_chart["price_history"][-5], "point_index": 95, "date": "2026-07-17"},
            {"annotation_type": "failed_breakout", "label": "Failed breakout", "value": first_chart["price_history"][-3], "point_index": 97, "date": "2026-07-20"},
            {"annotation_type": "pivot", "label": "Future marker", "value": first_chart["price_history"][-1], "point_index": 99, "date": "2026-08-01"},
        ]
        document = build_report_document(report, previous)
        figure = next(item for item in document.figures if item.figure_id == "stock-crwd")
        annotation_types = {item.annotation_type for item in figure.annotations}
        self.assertTrue({"support", "resistance", "breakout", "ema", "current_thesis", "confirmation", "risk", "invalidation", "pivot", "gap", "trendline", "failed_breakout"}.issubset(annotation_types))
        self.assertNotIn("Future marker", {item.label for item in figure.annotations})
        with self.assertRaises(ValidationError):
            FigureAnnotation(
                annotation_id="future",
                annotation_type="future_arrow",
                label="Projected",
                evidence_id="known",
            )

    def test_individual_security_rs_rank_is_not_labeled_as_benchmark_points(self) -> None:
        document = self.document("individual-saved-stock-major-change")
        evidence = next(item for item in document.evidence if item.evidence_id == "research-security-crwd-relative-strength")
        self.assertEqual(evidence.unit, "rank")
        self.assertEqual(evidence.timeframe, "current stock snapshot")
        security = next(item for item in document.securities if item.symbol == "CRWD" and item.selected_for_research)
        self.assertNotIn(security.figure_id, document.research_focus.figure_ids)

    def test_stage6_pdf_renders_and_figure_numbers_are_monotonic(self) -> None:
        document = self.document("user-saved-leading-theme")
        figure_ids = [item.figure_id for item in document.figures]
        self.assertEqual(len(figure_ids), len(set(figure_ids)))
        self.assertEqual([item.figure_number for item in document.figures], list(range(1, len(document.figures) + 1)))
        payload = generate_report_pdf_v7(document).getvalue()
        self.assertTrue(payload.startswith(b"%PDF-"))
        self.assertGreater(len(payload), 40_000)


if __name__ == "__main__":
    unittest.main()
