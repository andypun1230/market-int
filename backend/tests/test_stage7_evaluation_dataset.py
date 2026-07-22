from __future__ import annotations

import json
import unittest
from collections import Counter
from pathlib import Path

from app.copilot.evaluation.contracts import FIXTURE_SCHEMA_VERSION, GoldenEvaluationCase
from app.copilot.evaluation.loader import cases_for_suite, default_fixture_root, load_fixtures
from tests.fixtures.stage7.generate_cases import build_cases


EXPECTED_CATEGORY_COUNTS = {
    "breadth": 15,
    "leadership": 8,
    "macro": 10,
    "market": 15,
    "navigation": 10,
    "report": 5,
    "research": 10,
    "risk": 15,
    "routing": 12,
    "sector": 8,
    "stock": 25,
    "synthesis": 13,
    "theme": 9,
    "watchlist": 10,
}


class Stage7GoldenDatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = load_fixtures()
        cls.by_id = {case.fixture_id: case for case in cls.cases}

    def test_corpus_has_165_unique_strictly_typed_cases(self) -> None:
        self.assertEqual(len(self.cases), 165)
        self.assertEqual(len(self.by_id), 165)
        self.assertTrue(all(isinstance(case, GoldenEvaluationCase) for case in self.cases))
        self.assertTrue(all(case.schema_version == FIXTURE_SCHEMA_VERSION for case in self.cases))
        self.assertEqual(
            Counter(case.category.value for case in self.cases),
            Counter(EXPECTED_CATEGORY_COUNTS),
        )

    def test_every_checked_in_record_materializes_all_required_brief_fields(self) -> None:
        required = {
            "fixture_id",
            "description",
            "category",
            "suites",
            "tags",
            "frozen_input",
            "expected_intent",
            "acceptable_secondary_intents",
            "expected_agent_selection",
            "expected_structured_conclusion",
            "required_evidence",
            "forbidden_evidence",
            "expected_contradiction_handling",
            "expected_freshness_state",
            "allowed_confidence_range",
            "expected_deep_links",
            "forbidden_claims",
            "context_required",
            "rationale",
            "reference_output",
        }
        path = default_fixture_root() / "cases.jsonl"
        records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(records), 165)
        for record in records:
            with self.subTest(fixture=record["fixture_id"]):
                self.assertTrue(required <= set(record))
                self.assertTrue(record["description"])
                self.assertTrue(record["rationale"])
                self.assertTrue(record["expected_structured_conclusion"])
                self.assertIn("full", record["suites"])

    def test_frozen_corpus_is_offline_complete_and_deterministic(self) -> None:
        for case in self.cases:
            with self.subTest(fixture=case.fixture_id):
                known = {item.evidence_id for item in case.frozen_input.evidence}
                self.assertTrue(set(case.required_evidence) <= known)
                self.assertTrue(all(item.source.startswith("stage7-frozen:") for item in case.frozen_input.evidence))
                self.assertEqual(case.reference_output.model_calls, 0)
                self.assertTrue(set(case.reference_output.cited_evidence) <= known)
                self.assertNotIn("http://", json.dumps(case.model_dump(mode="json")))
                self.assertNotIn("https://", json.dumps(case.model_dump(mode="json")))

        generated = "".join(
            json.dumps(case.model_dump(mode="json"), sort_keys=True) + "\n"
            for case in build_cases()
        )
        checked_in = (default_fixture_root() / "cases.jsonl").read_text(encoding="utf-8")
        self.assertEqual(generated, checked_in)

    def test_required_domain_and_failure_scenarios_are_present(self) -> None:
        required_ids = {
            "market-broad-confirmed-advance",
            "market-narrow-index-advance",
            "market-mixed-index-structure",
            "breadth-negative-ad-positive-high-low",
            "leadership-narrow-etf-strength",
            "macro-bond-etf-proxy",
            "risk-credit-equity-disagreement",
            "stock-confirmed-breakout-volume",
            "stock-above-resistance-weak-volume",
            "stock-support-above-price",
            "stock-level-collision",
            "watchlist-saved-not-owned",
            "research-missing-evidence-stays-missing",
            "report-invalid-report-id",
            "navigation-invalid-destination",
            "routing-pronoun-follow-up",
            "synthesis-truncated-stream",
        }
        self.assertTrue(required_ids <= set(self.by_id))
        constrained = [
            case for case in self.cases
            if {"stale", "partial", "missing-data", "contradiction"} & set(case.tags)
        ]
        failures = [case for case in self.cases if "failure-injection" in case.tags]
        self.assertGreaterEqual(len(constrained), 20)
        self.assertGreaterEqual(len(failures), 15)

    def test_suite_distribution_is_substantive(self) -> None:
        self.assertEqual(len(cases_for_suite(self.cases, "golden")), 165)
        self.assertEqual(len(cases_for_suite(self.cases, "routing")), 35)
        self.assertEqual(len(cases_for_suite(self.cases, "performance")), 14)
        self.assertEqual(len(cases_for_suite(self.cases, "safety")), 13)
        self.assertEqual(len(cases_for_suite(self.cases, "full")), 165)


if __name__ == "__main__":
    unittest.main()
