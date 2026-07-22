from __future__ import annotations

import unittest

from app.copilot.evaluation.contracts import ReleaseResult
from app.copilot.evaluation.run_stage7 import build_parser
from app.copilot.evaluation.runtime import run_runtime_suite
from app.copilot.policy import contains_prompt_injection, recommendation_violations


class Stage7RuntimeEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.summary = run_runtime_suite("full")
        cls.results = {item.fixture_id: item for item in cls.summary.case_results}

    def test_full_runtime_suite_is_release_bearing_and_exercises_every_agent(self) -> None:
        self.assertEqual(self.summary.result, ReleaseResult.PASS_WITH_CONDITIONS)
        self.assertTrue(self.summary.release_bearing)
        self.assertEqual(self.summary.fixture_count, 30)
        self.assertEqual(self.summary.passed_count, 30)
        self.assertEqual(self.summary.release_blocker_count, 0)
        coverage = self.summary.runtime_coverage
        self.assertTrue(coverage["hermetic_sources"])
        self.assertEqual(coverage["live_provider_calls"], 0)
        self.assertTrue(coverage["all_registered_agents_exercised"])
        self.assertEqual(len(coverage["agents_exercised"]), 15)
        self.assertTrue(all(coverage["pipeline_boundaries"].values()))

    def test_machine_summary_records_reference_count_and_runtime_versions(self) -> None:
        coverage = self.summary.runtime_coverage
        self.assertEqual(coverage["frozen_reference_fixture_count"], 165)
        self.assertEqual(coverage["runtime_scenario_count"], 30)
        self.assertEqual(coverage["agent_manifest"]["schema_version"], "stage7-agent-manifest-v1")
        self.assertEqual(len(coverage["agent_versions"]), 15)
        self.assertTrue(
            all(item["contract_version"] == "copilot-agent-result-v1" for item in coverage["agent_versions"].values())
        )
        self.assertEqual(
            coverage["pipeline_versions"]["response_contract"],
            "institutional-copilot-response-v1",
        )
        self.assertEqual(
            coverage["pipeline_versions"]["model_version"],
            "institutional-copilot-v1-deterministic",
        )
        self.assertIsNone(coverage["pipeline_versions"]["prompt_version"])

    def test_runtime_response_is_mapped_into_a_diagnostic_candidate(self) -> None:
        result = self.results["runtime-stock-decision"]
        candidate = result.observed_candidate
        self.assertIsNotNone(candidate)
        assert candidate is not None
        self.assertEqual(candidate.output_schema_version, "institutional-copilot-response-v1")
        self.assertEqual(candidate.validation_status, "passed")
        self.assertFalse(candidate.fallback_used)
        self.assertEqual(candidate.response_status, "complete")
        self.assertGreater(candidate.latency_ms, 0)
        self.assertEqual(set(candidate.agent_latency_ms), {"stock", "market", "breadth", "risk"})
        self.assertTrue(candidate.cited_evidence)
        self.assertTrue(candidate.claims)

    def test_unsafe_production_synthesis_is_caught_with_evidence_preserving_fallback(self) -> None:
        result = self.results["runtime-unsafe-synthesis"]
        self.assertTrue(result.passed)
        self.assertTrue(result.observations["injection_observed"])
        self.assertTrue(result.observations["fallback_used"])
        self.assertIn("recommendation", result.observations["validation_issues"])
        candidate = result.observed_candidate
        assert candidate is not None
        self.assertNotIn("validation_quarantine", candidate.failure_categories)
        self.assertEqual(candidate.freshness.value, "cached")
        self.assertTrue(candidate.cited_evidence)
        final_text = " ".join(claim.text for claim in candidate.claims)
        self.assertFalse(recommendation_violations(final_text))

    def test_source_contract_timeout_and_prompt_injections_execute_observably(self) -> None:
        expected = {
            "runtime-market-source-error": "RuntimeError",
            "runtime-malformed-stock": "AttributeError",
            "runtime-breadth-unavailable": "breadth:unavailable",
            "runtime-agent-timeout": "timeout",
            "runtime-agent-contract-mismatch": "agent_contract",
            "runtime-source-prompt-injection": "validation_quarantine",
        }
        for fixture_id, failure in expected.items():
            with self.subTest(fixture_id=fixture_id):
                result = self.results[fixture_id]
                self.assertTrue(result.passed)
                self.assertTrue(result.observations["injection_observed"])
                candidate = result.observed_candidate
                assert candidate is not None
                failure_text = " ".join([
                    *candidate.failure_categories,
                    *[str(value) for value in result.observations["agent_failure_categories"].values()],
                    *[f"{key}:{value}" for key, value in result.observations["agent_statuses"].items()],
                ])
                self.assertIn(failure, failure_text)
        prompt_candidate = self.results["runtime-source-prompt-injection"].observed_candidate
        assert prompt_candidate is not None
        self.assertFalse(contains_prompt_injection(" ".join(claim.text for claim in prompt_candidate.claims)))

    def test_performance_reports_end_to_end_and_per_agent_latency(self) -> None:
        metrics = self.summary.performance_metrics
        self.assertGreater(metrics["p50_latency_ms"], 0)
        self.assertGreaterEqual(metrics["p95_latency_ms"], metrics["p50_latency_ms"])
        self.assertGreaterEqual(metrics["max_latency_ms"], metrics["p95_latency_ms"])
        self.assertEqual(metrics["mean_model_calls"], 0)
        self.assertIn("stock", self.summary.agent_performance_metrics)
        stock = self.summary.agent_performance_metrics["stock"]
        self.assertGreater(stock["count"], 0)
        self.assertGreaterEqual(stock["p95_latency_ms"], stock["p50_latency_ms"])

    def test_cli_defaults_to_release_bearing_runtime_mode(self) -> None:
        args = build_parser().parse_args([])
        self.assertEqual(args.mode, "runtime")
        self.assertEqual(args.suite, "full")


if __name__ == "__main__":
    unittest.main()
