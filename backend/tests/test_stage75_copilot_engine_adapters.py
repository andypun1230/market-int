from __future__ import annotations

import unittest

from app.copilot.contracts import (
    CopilotEvidenceCategory,
    CopilotEvidenceV1,
    CopilotFreshnessState,
    CopilotFreshnessV1,
    CopilotInterpretationClass,
    CopilotSourceReferenceV1,
)
from app.copilot.engine_adapters import (
    CopilotEvidenceValidationAdapter,
    CopilotFreshnessAdapter,
)
from app.copilot.sources import aggregate_source_states, freshness_state, normalize_source_state


class Stage75CopilotEngineAdapterTests(unittest.TestCase):
    def test_freshness_adapter_preserves_stage7_contract_shape_and_state(self) -> None:
        result = CopilotFreshnessAdapter().evaluate(
            source_state="cached",
            status="complete",
            generated_at="2020-01-01T00:00:00Z",
            observed_at="2020-01-01T00:00:00Z",
            market_date="2020-01-01-extra",
            expires_at=None,
            completeness=1.2,
            provider="fixture",
            warnings=("warning", "warning"),
            test=False,
            stale_after_seconds=60,
        )

        self.assertEqual(result.state, CopilotFreshnessState.STALE)
        self.assertEqual(result.market_date, "2020-01-01")
        self.assertEqual(result.completeness, 1.0)
        self.assertEqual(result.provider, "fixture")
        self.assertEqual(result.warnings, ["warning"])

    def test_source_compatibility_functions_delegate_without_semantic_drift(self) -> None:
        self.assertEqual(normalize_source_state("current"), "live")
        self.assertEqual(normalize_source_state("mock"), "test")
        self.assertEqual(freshness_state(source_state="live", status="partial"), "partial")
        self.assertEqual(
            aggregate_source_states(("live", "unavailable")),
            "partial",
        )

    def test_evidence_adapter_uses_first_win_stable_identity(self) -> None:
        source = CopilotSourceReferenceV1(
            source_id="source",
            provider="fixture",
            dataset="prices",
        )
        freshness = CopilotFreshnessV1(
            state=CopilotFreshnessState.CACHED,
            completeness=1,
            provider="fixture",
        )
        first = CopilotEvidenceV1(
            evidence_id="evidence",
            category=CopilotEvidenceCategory.TECHNICAL,
            entity="AAPL",
            metric="current price",
            value=100,
            interpretation_class=CopilotInterpretationClass.OBSERVED_FACT,
            source=source,
            freshness=freshness,
        )
        conflicting = first.model_copy(update={"value": 101})

        result = CopilotEvidenceValidationAdapter().deduplicate(
            (first, first, conflicting)
        )

        self.assertEqual(result, [first])
        self.assertEqual(result[0].value, 100)


if __name__ == "__main__":
    unittest.main()
