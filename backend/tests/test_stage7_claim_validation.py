from __future__ import annotations

import unittest

from app.copilot.contracts import (
    AgentResultV1,
    CopilotAgentName,
    CopilotAgentStatus,
    CopilotConfidenceLabel,
    CopilotDestination,
    CopilotEvidenceBundleV1,
    CopilotEvidenceCategory,
    CopilotEvidenceV1,
    CopilotFreshnessState,
    CopilotFreshnessSummaryV1,
    CopilotFreshnessV1,
    CopilotIntentType,
    CopilotIntentV1,
    CopilotInterpretationClass,
    CopilotReasoningFactorV1,
    CopilotReasoningV1,
    CopilotSourceReferenceV1,
    CopilotStance,
    CopilotValidationCheck,
)
from app.copilot.actions import build_action
from app.copilot.planner import CopilotPlanner
from app.copilot.policy import certainty_violations, flow_claim_violations
from app.copilot.validation import CopilotResponseValidator
from scripts.generate_stage7_copilot_artifacts import execute_fixture
from tests.fixtures.stage7_copilot import STAGE7_FIXTURE_BY_ID


class Stage7ClaimValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = CopilotResponseValidator()

    @staticmethod
    def intent(intent: CopilotIntentType = CopilotIntentType.STOCK_ANALYSIS) -> CopilotIntentV1:
        agent = {
            CopilotIntentType.MACRO_QUERY: CopilotAgentName.MACRO,
            CopilotIntentType.REPORT_QUERY: CopilotAgentName.REPORT,
        }.get(intent, CopilotAgentName.STOCK)
        return CopilotIntentV1(
            intent_id=f"intent-{intent.value.casefold()}",
            intent=intent,
            sub_intent="validation_fixture",
            ticker_symbols=["NVDA"] if agent == CopilotAgentName.STOCK else [],
            confidence=0.95,
            required_agents=[agent],
        )

    @staticmethod
    def evidence(
        evidence_id: str,
        *,
        metric: str,
        value: object,
        category: CopilotEvidenceCategory = CopilotEvidenceCategory.TECHNICAL,
        entity: str = "NVDA",
        state: CopilotFreshnessState = CopilotFreshnessState.CACHED,
        dataset: str = "stock_snapshot",
        report_reference: str | None = None,
        source_date: str = "2026-07-21",
        evidence_date: str = "2026-07-21",
    ) -> CopilotEvidenceV1:
        freshness = CopilotFreshnessV1(
            state=state,
            market_date=evidence_date,
            generated_at="2026-07-21T20:00:00Z",
            completeness=1,
            provider="stage7_validation_fixture",
        )
        source = CopilotSourceReferenceV1(
            source_id=f"source-{evidence_id}",
            provider="stage7_validation_fixture",
            dataset=dataset,
            generated_at="2026-07-21T20:00:00Z",
            market_date=source_date,
            raw_engine_reference=f"snapshot-{evidence_id}",
        )
        return CopilotEvidenceV1(
            evidence_id=evidence_id,
            category=category,
            entity=entity,
            metric=metric,
            value=value,
            interpretation_class=CopilotInterpretationClass.OBSERVED_FACT,
            source=source,
            freshness=freshness,
            report_reference=report_reference,
        )

    @staticmethod
    def reasoning(
        factors: list[CopilotReasoningFactorV1],
        *,
        confidence: CopilotConfidenceLabel = CopilotConfidenceLabel.MODERATE,
        direct_answer: str = "The conclusion remains conditional on the cited evidence.",
        confirmation: list[CopilotReasoningFactorV1] | None = None,
        invalidation: list[CopilotReasoningFactorV1] | None = None,
    ) -> CopilotReasoningV1:
        return CopilotReasoningV1(
            direct_answer=direct_answer,
            stance=CopilotStance.MONITOR,
            confidence_label=confidence,
            thesis="The setup remains a monitoring question.",
            supporting_factors=factors,
            confirmation_conditions=confirmation or [],
            invalidation_conditions=invalidation or [],
        )

    @staticmethod
    def bundle(
        intent: CopilotIntentV1,
        evidence: list[CopilotEvidenceV1],
        *,
        state: CopilotFreshnessState = CopilotFreshnessState.CACHED,
    ) -> CopilotEvidenceBundleV1:
        plan = CopilotPlanner().build(intent)
        agent = intent.required_agents[0]
        freshness = CopilotFreshnessV1(
            state=state,
            market_date="2026-07-21",
            generated_at="2026-07-21T20:00:00Z",
            completeness=1,
            provider="stage7_validation_fixture",
        )
        result = AgentResultV1(
            agent=agent,
            status=CopilotAgentStatus.STALE if state == CopilotFreshnessState.STALE else CopilotAgentStatus.COMPLETE,
            source_references=[item.source for item in evidence],
            evidence=evidence,
            freshness=freshness,
        )
        constrained = state == CopilotFreshnessState.STALE
        return CopilotEvidenceBundleV1(
            request_id="stage7-claim-validation",
            question="Validate the cited evidence.",
            intent=intent,
            plan=plan,
            agent_results=[result],
            evidence=evidence,
            supporting_evidence_ids=[item.evidence_id for item in evidence],
            freshness_summary=CopilotFreshnessSummaryV1(
                overall_state=state,
                market_dates=["2026-07-21"],
                generated_timestamps=["2026-07-21T20:00:00Z"],
                current_count=0 if constrained else 1,
                stale_count=1 if constrained else 0,
            ),
            source_summary=[item.source for item in evidence],
        )

    @staticmethod
    def issue_checks(result) -> set[CopilotValidationCheck]:
        return {issue.check for issue in result.issues}

    def test_high_confidence_is_rejected_for_stale_evidence(self) -> None:
        intent = self.intent()
        evidence = self.evidence(
            "stale-price",
            metric="current price",
            value=100,
            state=CopilotFreshnessState.STALE,
        )
        factor = CopilotReasoningFactorV1(statement="NVDA price is 100.", evidence_ids=[evidence.evidence_id])
        result = self.validator.validate(
            self.bundle(intent, [evidence], state=CopilotFreshnessState.STALE),
            self.reasoning([factor], confidence=CopilotConfidenceLabel.HIGH),
        )
        self.assertIn(CopilotValidationCheck.CONFIDENCE_FRESHNESS, self.issue_checks(result))

    def test_certainty_and_unsourced_flow_claims_are_release_blocking(self) -> None:
        intent = self.intent()
        evidence = self.evidence("price", metric="current price", value=100)
        bundle = self.bundle(intent, [evidence])
        factor = CopilotReasoningFactorV1(statement="NVDA price is 100.", evidence_ids=[evidence.evidence_id])
        certainty = self.validator.validate(
            bundle,
            self.reasoning([factor], direct_answer="NVDA will definitely rise."),
        )
        flow = self.validator.validate(
            bundle,
            self.reasoning([factor], direct_answer="Institutional buying confirms the move."),
        )
        self.assertIn(CopilotValidationCheck.HIGH_RISK_LANGUAGE, self.issue_checks(certainty))
        self.assertIn(CopilotValidationCheck.HIGH_RISK_LANGUAGE, self.issue_checks(flow))
        self.assertTrue(certainty_violations("Guaranteed returns are certain to occur."))
        self.assertTrue(flow_claim_violations("Smart money is accumulating."))

    def test_confirmed_breakout_requires_price_and_volume_evidence(self) -> None:
        intent = self.intent()
        trigger = self.evidence("price-trigger", metric="confirmation price", value=110)
        claim = CopilotReasoningFactorV1(
            statement="NVDA breakout is confirmed above 110.",
            evidence_ids=[trigger.evidence_id],
        )
        missing_volume = self.validator.validate(
            self.bundle(intent, [trigger]),
            self.reasoning([claim]),
        )
        self.assertIn(CopilotValidationCheck.CONFIRMED_CLAIMS, self.issue_checks(missing_volume))

        current = self.evidence("current-price", metric="current price", value=111)
        volume = self.evidence("volume", metric="volume confirmation", value="strong")
        grounded_claim = claim.model_copy(
            update={"evidence_ids": [trigger.evidence_id, current.evidence_id, volume.evidence_id]}
        )
        complete = self.validator.validate(
            self.bundle(intent, [trigger, current, volume]),
            self.reasoning([grounded_claim]),
        )
        self.assertNotIn(CopilotValidationCheck.CONFIRMED_CLAIMS, self.issue_checks(complete))

        nvda_below = current.model_copy(update={"value": 95, "current_state": 95})
        aapl_current = self.evidence("aapl-price", metric="current price", value=200, entity="AAPL")
        aapl_volume = self.evidence("aapl-volume", metric="volume confirmation", value="strong", entity="AAPL")
        cross_entity = claim.model_copy(
            update={
                "evidence_ids": [
                    trigger.evidence_id,
                    nvda_below.evidence_id,
                    aapl_current.evidence_id,
                    aapl_volume.evidence_id,
                ]
            }
        )
        rejected = self.validator.validate(
            self.bundle(intent, [trigger, nvda_below, aapl_current, aapl_volume]),
            self.reasoning([cross_entity]),
        )
        self.assertIn(CopilotValidationCheck.CONFIRMED_CLAIMS, self.issue_checks(rejected))

    def test_headline_numbers_require_same_entity_metric_and_cited_factor(self) -> None:
        intent = self.intent()
        spy_rsi = self.evidence("spy-rsi", metric="RSI", value=100, entity="SPY")
        spy_factor = CopilotReasoningFactorV1(
            statement="SPY RSI is 100.",
            evidence_ids=[spy_rsi.evidence_id],
        )
        wrong_entity = self.validator.validate(
            self.bundle(intent, [spy_rsi]),
            self.reasoning([spy_factor], direct_answer="NVDA price is 100."),
        )
        self.assertIn(CopilotValidationCheck.NUMERICAL_CLAIMS, self.issue_checks(wrong_entity))

        nvda_price = self.evidence("nvda-price", metric="current price", value=100)
        price_factor = CopilotReasoningFactorV1(
            statement="NVDA price is 100.",
            evidence_ids=[nvda_price.evidence_id],
        )
        wrong_metric = self.validator.validate(
            self.bundle(intent, [nvda_price]),
            self.reasoning([price_factor], direct_answer="NVDA RSI is 100."),
        )
        self.assertIn(CopilotValidationCheck.NUMERICAL_CLAIMS, self.issue_checks(wrong_metric))

        grounded = self.validator.validate(
            self.bundle(intent, [nvda_price]),
            self.reasoning([price_factor], direct_answer="NVDA price is 100."),
        )
        self.assertNotIn(CopilotValidationCheck.NUMERICAL_CLAIMS, self.issue_checks(grounded))

    def test_confirmation_and_invalidation_cannot_share_evidence(self) -> None:
        intent = self.intent()
        level = self.evidence("level", metric="decision level", value=100)
        factor = CopilotReasoningFactorV1(statement="NVDA decision level is 100.", evidence_ids=[level.evidence_id])
        result = self.validator.validate(
            self.bundle(intent, [level]),
            self.reasoning([factor], confirmation=[factor], invalidation=[factor]),
        )
        self.assertIn(CopilotValidationCheck.CONDITION_COHERENCE, self.issue_checks(result))

    def test_bond_etf_proxy_cannot_be_presented_as_direct_yield(self) -> None:
        intent = self.intent(CopilotIntentType.MACRO_QUERY)
        proxy = self.evidence(
            "tlt-proxy",
            category=CopilotEvidenceCategory.MACRO,
            entity="TLT",
            metric="bond ETF price proxy",
            value="falling",
            dataset="etf_price_proxy",
        )
        factor = CopilotReasoningFactorV1(
            statement="The 10-year yield is rising.",
            evidence_ids=[proxy.evidence_id],
        )
        result = self.validator.validate(self.bundle(intent, [proxy]), self.reasoning([factor]))
        self.assertIn(CopilotValidationCheck.PROXY_LABELING, self.issue_checks(result))

    def test_non_comparison_response_cannot_mix_immutable_report_ids(self) -> None:
        intent = self.intent(CopilotIntentType.REPORT_QUERY)
        first = self.evidence(
            "report-one",
            category=CopilotEvidenceCategory.REPORT,
            entity="latest report",
            metric="report thesis",
            value="constructive",
            dataset="ReportDocument",
            report_reference="report-1:thesis",
        )
        second = self.evidence(
            "report-two",
            category=CopilotEvidenceCategory.REPORT,
            entity="latest report",
            metric="risk thesis",
            value="cautious",
            dataset="ReportDocument",
            report_reference="report-2:risk",
        )
        factors = [
            CopilotReasoningFactorV1(statement="The report thesis is constructive.", evidence_ids=[first.evidence_id]),
            CopilotReasoningFactorV1(statement="The report risk thesis is cautious.", evidence_ids=[second.evidence_id]),
        ]
        result = self.validator.validate(self.bundle(intent, [first, second]), self.reasoning(factors))
        self.assertIn(CopilotValidationCheck.REPORT_LINEAGE, self.issue_checks(result))

    def test_stale_current_price_is_rejected_but_unavailable_disclosure_is_not(self) -> None:
        intent = self.intent()
        evidence = self.evidence(
            "stale-current-price",
            metric="current price",
            value=100,
            state=CopilotFreshnessState.STALE,
        )
        factor = CopilotReasoningFactorV1(
            statement="The stored NVDA price is 100.",
            evidence_ids=[evidence.evidence_id],
        )
        bundle = self.bundle(intent, [evidence], state=CopilotFreshnessState.STALE)
        stale_current = self.validator.validate(
            bundle,
            self.reasoning([factor], direct_answer="NVDA current price is 100."),
        )
        self.assertIn(CopilotValidationCheck.FRESHNESS_LANGUAGE, self.issue_checks(stale_current))

        honest = self.validator.validate(
            bundle,
            self.reasoning([factor], direct_answer="NVDA current price is unavailable."),
        )
        self.assertNotIn(CopilotValidationCheck.FRESHNESS_LANGUAGE, self.issue_checks(honest))

    def test_collected_contradiction_cannot_be_omitted(self) -> None:
        intent = self.intent()
        support = self.evidence("support", metric="current price", value=100)
        opposition = self.evidence("opposition", metric="risk score", value=70).model_copy(
            update={"interpretation_class": CopilotInterpretationClass.CONTRADICTION}
        )
        bundle = self.bundle(intent, [support, opposition]).model_copy(
            update={
                "supporting_evidence_ids": [support.evidence_id],
                "contradictory_evidence_ids": [opposition.evidence_id],
            }
        )
        factor = CopilotReasoningFactorV1(
            statement="NVDA price is 100.",
            evidence_ids=[support.evidence_id],
        )
        result = self.validator.validate(bundle, self.reasoning([factor]))
        self.assertIn(CopilotValidationCheck.CONTRADICTION_PRESERVATION, self.issue_checks(result))

    def test_trade_language_negation_and_short_term_are_not_false_positives(self) -> None:
        intent = self.intent()
        evidence = self.evidence("price-safe-language", metric="current price", value=100)
        factor = CopilotReasoningFactorV1(
            statement="NVDA price is 100.",
            evidence_ids=[evidence.evidence_id],
        )
        bundle = self.bundle(intent, [evidence])
        for direct_answer in (
            "The setup is a short-term consolidation.",
            "This is not a buy recommendation.",
        ):
            with self.subTest(direct_answer=direct_answer):
                result = self.validator.validate(
                    bundle,
                    self.reasoning([factor], direct_answer=direct_answer),
                )
                self.assertNotIn(CopilotValidationCheck.RECOMMENDATION, self.issue_checks(result))

    def test_source_id_conflict_and_arbitrary_action_parameter_are_rejected(self) -> None:
        intent = self.intent()
        evidence = self.evidence("source-conflict", metric="current price", value=100)
        bundle = self.bundle(intent, [evidence])
        conflicting_source = evidence.source.model_copy(update={"provider": "different-provider"})
        conflicting_evidence = evidence.model_copy(update={"source": conflicting_source})
        conflicting_bundle = bundle.model_copy(
            update={
                "evidence": [conflicting_evidence],
                "agent_results": [
                    bundle.agent_results[0].model_copy(update={"evidence": [conflicting_evidence]})
                ],
            }
        )
        factor = CopilotReasoningFactorV1(
            statement="NVDA price is 100.",
            evidence_ids=[evidence.evidence_id],
        )
        source_result = self.validator.validate(conflicting_bundle, self.reasoning([factor]))
        self.assertIn(CopilotValidationCheck.SOURCES, self.issue_checks(source_result))

        action = build_action(
            CopilotDestination.FEAR_GREED,
            parameters={"url": "javascript:alert(1)"},
        )
        self.assertIsNotNone(action)
        action_result = self.validator.validate(bundle, self.reasoning([factor]), [action])
        self.assertIn(CopilotValidationCheck.ACTIONS, self.issue_checks(action_result))

    def test_fixture_conditions_use_distinct_support_and_opposition_evidence(self) -> None:
        execution = execute_fixture(STAGE7_FIXTURE_BY_ID["stock-decision-support"])
        self.assertEqual(execution["status"], "passed")
        reasoning = execution["response"]["reasoning"]
        confirmation_ids = {
            evidence_id
            for factor in reasoning["confirmationConditions"]
            for evidence_id in factor["evidenceIds"]
        }
        invalidation_ids = {
            evidence_id
            for factor in reasoning["invalidationConditions"]
            for evidence_id in factor["evidenceIds"]
        }
        self.assertTrue(confirmation_ids)
        self.assertTrue(invalidation_ids)
        self.assertFalse(confirmation_ids.intersection(invalidation_ids))


if __name__ == "__main__":
    unittest.main()
