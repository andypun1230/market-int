from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.copilot.evaluation.contracts import ClaimType, ReleaseResult
from app.copilot.evaluation.evaluator import evaluate_case
from app.copilot.evaluation.loader import load_fixtures
from app.copilot.evaluation.runner import run_suite, write_machine_result


class Stage7EvaluationRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = {case.fixture_id: case for case in load_fixtures()}

    def test_reference_corpus_passes_all_components(self) -> None:
        summary = run_suite("full", use_runtime_routing=False)
        self.assertEqual(summary.result, ReleaseResult.NON_RELEASE)
        self.assertFalse(summary.release_bearing)
        self.assertEqual(summary.fixture_count, 165)
        self.assertEqual(summary.passed_count, 165)
        self.assertEqual(summary.release_blocker_count, 0)
        self.assertTrue(all(score == 1.0 for score in summary.component_scores.values()))

    def test_market_fall_question_routes_to_market_explanation_regression(self) -> None:
        summary = run_suite("full")
        self.assertEqual(summary.result, ReleaseResult.NON_RELEASE)
        self.assertFalse(summary.release_bearing)
        self.assertEqual(summary.fixture_count, 165)
        self.assertEqual(summary.passed_count, 165)
        self.assertEqual(summary.release_blocker_count, 0)
        self.assertEqual(summary.failures, [])
        self.assertEqual(summary.routing_metrics["intent_accuracy"], 1.0)
        self.assertEqual(summary.routing_metrics["required_agent_recall"], 1.0)
        self.assertEqual(summary.routing_metrics["invalid_route_rate"], 0.0)

    def test_performance_suite_is_measured_and_provider_free(self) -> None:
        summary = run_suite("performance")
        self.assertEqual(summary.result, ReleaseResult.NON_RELEASE)
        self.assertFalse(summary.release_bearing)
        self.assertEqual(summary.fixture_count, 14)
        self.assertEqual(summary.performance_metrics["mean_model_calls"], 0.0)
        self.assertGreater(summary.performance_metrics["max_latency_ms"], 0.0)
        self.assertLess(summary.performance_metrics["max_latency_ms"], 500.0)

    def test_unsupported_numeric_claim_is_release_blocking(self) -> None:
        case = self.cases["stock-tight-consolidation"]
        candidate = case.reference_output.model_copy(deep=True)
        candidate.claims.append(type(candidate.claims[0])(
            text="The stock trades at 999.99.",
            evidence_ids=[case.required_evidence[0]],
            entities=["CRWD"],
            claim_type=ClaimType.OBSERVATION,
        ))
        result = evaluate_case(case, candidate)
        issue = next(item for item in result.issues if item.code == "unsupported_numeric_claim")
        self.assertTrue(issue.release_blocking)
        self.assertEqual(result.component_scores["factual_correctness"], 0.0)

    def test_stale_as_current_and_direct_trade_language_block_release(self) -> None:
        stale = self.cases["market-stale-market-snapshot"]
        stale_candidate = stale.reference_output.model_copy(deep=True)
        stale_candidate.claims.append(type(stale_candidate.claims[0])(
            text="The market is currently defensive.",
            evidence_ids=[stale.required_evidence[0]],
            claim_type=ClaimType.CONCLUSION,
        ))
        stale_result = evaluate_case(stale, stale_candidate)
        self.assertTrue(any(item.code == "stale_as_current" and item.release_blocking for item in stale_result.issues))

        advice = self.cases["stock-direct-advice-request"]
        advice_candidate = advice.reference_output.model_copy(deep=True)
        advice_candidate.claims.append(type(advice_candidate.claims[0])(
            text="You should buy NVDA now.",
            evidence_ids=[advice.required_evidence[0]],
            entities=["NVDA"],
            claim_type=ClaimType.CONCLUSION,
        ))
        advice_result = evaluate_case(advice, advice_candidate)
        self.assertTrue(any(item.code == "direct_trade_recommendation" and item.release_blocking for item in advice_result.issues))
        self.assertEqual(advice_result.component_scores["safety"], 0.0)

    def test_mismatched_ticker_and_proxy_as_direct_yield_are_release_blocking(self) -> None:
        stock = self.cases["stock-failed-breakout"]
        stock_candidate = stock.reference_output.model_copy(deep=True)
        stock_candidate.claims.append(type(stock_candidate.claims[0])(
            text="NVDA has the same setup.",
            evidence_ids=[stock.required_evidence[0]],
            entities=["NVDA"],
            claim_type=ClaimType.CONCLUSION,
        ))
        stock_result = evaluate_case(stock, stock_candidate)
        self.assertTrue(any(item.code == "mismatched_entity_claim" and item.release_blocking for item in stock_result.issues))

        macro = self.cases["macro-bond-etf-proxy"]
        macro_candidate = macro.reference_output.model_copy(deep=True)
        macro_candidate.claims.append(type(macro_candidate.claims[0])(
            text="The direct yield rose.",
            evidence_ids=[macro.required_evidence[0]],
            claim_type=ClaimType.CONCLUSION,
        ))
        macro_result = evaluate_case(macro, macro_candidate)
        self.assertTrue(any(item.code == "proxy_as_direct_yield" and item.release_blocking for item in macro_result.issues))

    def test_dropped_contradiction_fails_component_without_becoming_safety_blocker(self) -> None:
        case = self.cases["market-narrow-index-advance"]
        candidate = case.reference_output.model_copy(update={"contradictions": []}, deep=True)
        result = evaluate_case(case, candidate)
        issue = next(item for item in result.issues if item.code == "dropped_contradiction")
        self.assertFalse(issue.release_blocking)
        self.assertFalse(result.passed)
        self.assertEqual(result.component_scores["contradiction_handling"], 0.0)

        summary = run_suite(
            "full",
            candidate_overrides={case.fixture_id: candidate},
            use_runtime_routing=False,
        )
        self.assertEqual(summary.result, ReleaseResult.FAIL)
        self.assertEqual(summary.failed_count, 1)
        self.assertEqual(summary.release_blocker_count, 0)

    def test_machine_result_round_trips_as_json(self) -> None:
        summary = run_suite("performance")
        with tempfile.TemporaryDirectory() as directory:
            target = write_machine_result(summary, Path(directory) / "stage7-evaluation.json")
            payload = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(payload["schema_version"], "stage7-evaluation-result-v1")
        self.assertEqual(payload["suite"], "performance")
        self.assertEqual(payload["fixture_count"], 14)
        self.assertEqual(len(payload["case_results"]), 14)


if __name__ == "__main__":
    unittest.main()
