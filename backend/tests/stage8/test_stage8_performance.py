from __future__ import annotations

import unittest

from scripts.benchmark_stage8_intelligence import build_payload


class Stage8PerformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = build_payload(iterations=20)

    def test_release_thresholds_pass(self) -> None:
        self.assertEqual(self.payload["status"], "PASS", self.payload)
        self.assertTrue(all(self.payload["threshold_results"].values()))

    def test_benchmark_is_explicitly_hermetic_and_model_free(self) -> None:
        self.assertTrue(self.payload["hermetic"])
        self.assertEqual(self.payload["network_calls"], 0)
        self.assertEqual(self.payload["model_calls"], 0)
        self.assertEqual(
            self.payload["external_call_audit"]["policy"],
            "all attempted external calls fail the benchmark",
        )
        self.assertEqual(self.payload["news_pipeline"]["provider_mode"], "test")
        self.assertEqual(self.payload["news_pipeline"]["freshness"], "test")

    def test_observability_captures_dedup_mapping_and_session_coverage(self) -> None:
        news = self.payload["news_pipeline"]
        self.assertEqual(news["provider_event_count"], 20)
        self.assertEqual(news["cluster_count"], 10)
        self.assertEqual(news["duplicate_reduction_ratio"], 0.5)
        self.assertEqual(news["mapped_canonical_event_ratio"], 1.0)
        self.assertEqual(news["mapping_evidence_lineage_ratio"], 1.0)
        self.assertGreater(news["materiality_contribution_count"], 0)
        self.assertGreater(news["reaction_evidence_count"], 0)
        for component in (
            "provider_fetch",
            "normalization",
            "clustering",
            "mapping",
            "materiality",
            "reaction_analysis",
            "full_service",
        ):
            with self.subTest(component=component):
                self.assertGreater(news["component_latency_ms"][component], 0)
        session = self.payload["session_pipeline"]
        self.assertEqual(session["input_bar_count"], 78)
        self.assertEqual(session["regular_session_coverage"], 1.0)
        self.assertEqual(self.payload["endpoints"]["news_security"]["status_code"], 200)
        self.assertEqual(self.payload["endpoints"]["session_security"]["status_code"], 200)
        copilot = self.payload["copilot_full_pipeline"]
        self.assertEqual(copilot["response_status"], "complete")
        self.assertEqual(copilot["validation_status"], "passed")
        self.assertGreater(copilot["evidence_count"], 0)


if __name__ == "__main__":
    unittest.main()
