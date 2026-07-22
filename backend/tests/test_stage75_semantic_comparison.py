from __future__ import annotations

import unittest

from scripts.compare_stage75_semantics import compare


def runtime_payload(*, symbol: str, latency_ms: float) -> dict:
    return {
        "generated_at": "2026-07-22T00:00:00Z",
        "performance_metrics": {"p95_latency_ms": latency_ms},
        "case_results": [
            {
                "fixture_id": "runtime-action",
                "passed": True,
                "suites": ["performance"],
                "component_scores": {"contract_correctness": 1.0},
                "metrics": {"latency_ms": latency_ms},
                "observed_candidate": {},
                "observations": {
                    "actions": [
                        {
                            "actionId": "open-stock",
                            "destinationId": "stock_detail",
                            "parameters": {"symbol": symbol, "stockTab": "overview"},
                        }
                    ]
                },
            }
        ],
    }


class Stage75SemanticComparisonTests(unittest.TestCase):
    def test_action_parameter_drift_fails_even_when_latency_is_ignored(self) -> None:
        result = compare(
            runtime_payload(symbol="AAPL", latency_ms=5.0),
            runtime_payload(symbol="MSFT", latency_ms=8.0),
        )

        self.assertEqual(result["result"], "FAIL")
        self.assertEqual(result["failed_count"], 1)
        self.assertEqual(result["cases"][0]["mismatches"], ["runtime_observations"])
        self.assertIn("actions", result["compared_fields"]["runtime_observations"])


if __name__ == "__main__":
    unittest.main()
