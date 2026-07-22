from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.copilot.evaluation.loader import default_fixture_root, load_fixtures
from app.copilot.evaluation.review import (
    ReviewAvailability,
    ReviewClassification,
    ReviewUsefulness,
    build_review_document,
    load_review_document,
    main,
)
from app.copilot.evaluation.runner import run_suite, write_machine_result


class Stage7HumanReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = load_fixtures()
        cls.summary = run_suite("performance", use_runtime_routing=False)

    def build_document(self, *, summary=None, prior=None):
        return build_review_document(
            self.cases,
            summary or self.summary,
            cases_source=str(default_fixture_root() / "cases.jsonl"),
            evaluation_source="stage7-evaluation.json",
            prior_document=prior,
        )

    def test_review_document_joins_expected_and_observed_evaluation_fields(self) -> None:
        document = self.build_document()
        self.assertEqual(document.case_count, self.summary.fixture_count)
        item = next(
            case for case in document.cases
            if case.fixture_id == "market-broad-confirmed-advance"
        )

        self.assertEqual(item.question, "Is the market healthy?")
        self.assertEqual(item.routing.expected["primary_intent"], "MARKET_STATE")
        self.assertEqual(item.routing.observed.availability, ReviewAvailability.AVAILABLE)
        self.assertEqual(item.routing.observed.value["resolved_intent"], "MARKET_STATE")
        self.assertEqual(item.agents.observed.value, ["market"])
        self.assertEqual(
            item.evidence.observed.value["cited_ids"],
            item.evidence.expected["required_ids"],
        )
        self.assertEqual(item.contradictions.observed.value, [])
        self.assertEqual(item.deep_links.observed.value, ["market_overview"])
        self.assertEqual(item.freshness.observed.value["state"], "live")
        self.assertEqual(item.latency.observed.value["total_ms"], 80.0)
        self.assertEqual(item.model_usage.observed.availability, ReviewAvailability.PARTIAL)
        self.assertEqual(item.model_usage.observed.value["model_calls"], 0.0)
        self.assertIsNone(item.model_usage.observed.value["token_usage"])
        self.assertIsNone(item.model_usage.observed.value["estimated_cost"])
        self.assertEqual(item.validator_failures.observed.value, [])

        self.assertEqual(item.final_answer.observed.availability, ReviewAvailability.UNAVAILABLE)
        self.assertIn("not a synthesized final-answer", item.final_answer.observed.reason)
        self.assertEqual(item.raw_agent_outputs.availability, ReviewAvailability.UNAVAILABLE)
        self.assertIsNotNone(item.structured_output.value)
        self.assertIsNone(item.review.classification)
        self.assertEqual(item.review.usefulness, ReviewUsefulness.UNREVIEWED)

    def test_legacy_result_marks_candidate_only_fields_unavailable(self) -> None:
        legacy_results = [
            item.model_copy(update={"observed_candidate": None}, deep=True)
            for item in self.summary.case_results
        ]
        legacy_summary = self.summary.model_copy(
            update={"case_results": legacy_results},
            deep=True,
        )
        document = self.build_document(summary=legacy_summary)
        item = document.cases[0]

        for observed in (
            item.routing.observed,
            item.plan.observed,
            item.agents.observed,
            item.evidence.observed,
            item.contradictions.observed,
            item.deep_links.observed,
            item.freshness.observed,
        ):
            self.assertEqual(observed.availability, ReviewAvailability.UNAVAILABLE)
            self.assertIsNone(observed.value)
            self.assertIn("cannot be reconstructed honestly", observed.reason)

        self.assertEqual(item.latency.observed.availability, ReviewAvailability.AVAILABLE)
        self.assertEqual(item.model_usage.observed.availability, ReviewAvailability.PARTIAL)

    def test_cli_persists_review_and_preserves_it_when_rebuilt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result_path = write_machine_result(self.summary, root / "evaluation.json")
            review_path = root / "review.json"
            build_args = [
                "build",
                "--cases",
                str(default_fixture_root() / "cases.jsonl"),
                "--results",
                str(result_path),
                "--output",
                str(review_path),
            ]
            self.assertEqual(main(build_args), 0)
            self.assertEqual(
                main([
                    "set-review",
                    "--review-file",
                    str(review_path),
                    "--case-id",
                    "market-broad-confirmed-advance",
                    "--classification",
                    "partially_correct",
                    "--usefulness",
                    "useful",
                    "--notes",
                    "Correct route; answer still needs sharper wording.",
                    "--reviewer",
                    "local-reviewer",
                ]),
                0,
            )

            reviewed = load_review_document(review_path)
            item = next(
                case for case in reviewed.cases
                if case.fixture_id == "market-broad-confirmed-advance"
            )
            self.assertEqual(item.review.classification, ReviewClassification.PARTIALLY_CORRECT)
            self.assertEqual(item.review.usefulness, ReviewUsefulness.USEFUL)
            self.assertEqual(
                item.review.notes,
                "Correct route; answer still needs sharper wording.",
            )
            self.assertEqual(item.review.reviewer, "local-reviewer")
            self.assertIsNotNone(item.review.reviewed_at)

            self.assertEqual(main(build_args), 0)
            rebuilt = load_review_document(review_path)
            rebuilt_item = next(
                case for case in rebuilt.cases
                if case.fixture_id == "market-broad-confirmed-advance"
            )
            self.assertEqual(rebuilt_item.review, item.review)

    def test_review_label_contract_exposes_only_supported_values(self) -> None:
        self.assertEqual(
            {item.value for item in ReviewClassification},
            {
                "correct",
                "partially_correct",
                "incorrect",
                "too_generic",
                "too_confident",
                "missing_contradiction",
                "wrong_evidence",
                "wrong_routing",
                "wrong_link",
            },
        )
        self.assertEqual(
            {item.value for item in ReviewUsefulness},
            {"useful", "not_useful", "unreviewed"},
        )


if __name__ == "__main__":
    unittest.main()
