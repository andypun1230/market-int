from __future__ import annotations

import unittest
from unittest.mock import patch

from app.copilot.agent_contracts import load_agent_contracts, validate_agent_result
from app.copilot.agents import AgentExecutionContext, CopilotAgentRegistry
from app.copilot.contracts import (
    CopilotAgentName,
    CopilotAgentStatus,
    CopilotEvidenceCategory,
    CopilotIntentType,
    CopilotIntentV1,
)
from app.copilot.planner import CopilotPlanner
from app.copilot.sources import CopilotWatchlistMembership, TrustedCopilotSources
from tests.test_stage7_copilot_runtime import _HermeticArmSources


class _NoProviderSources(TrustedCopilotSources):
    def market_snapshot(self):
        return None

    def breadth_snapshot(self):
        return None

    def sector_snapshot(self):
        return None

    def theme_snapshot(self):
        return None

    def stock_snapshot(self, symbol: str):
        del symbol
        return None

    def watchlist_membership(self):
        return CopilotWatchlistMembership(
            symbols=None,
            scope="unavailable",
            provider="unavailable",
            source_id="contract-test-membership-unavailable",
            limitation="Saved-list membership is unavailable in the contract fixture.",
        )

    def latest_report_document(self):
        return None


_INTENTS = {
    CopilotAgentName.MARKET: CopilotIntentType.MARKET_STATE,
    CopilotAgentName.INDEX: CopilotIntentType.INDEX_ANALYSIS,
    CopilotAgentName.BREADTH: CopilotIntentType.BREADTH_QUERY,
    CopilotAgentName.LEADERSHIP: CopilotIntentType.SECTOR_ANALYSIS,
    CopilotAgentName.SECTOR: CopilotIntentType.SECTOR_ANALYSIS,
    CopilotAgentName.THEME: CopilotIntentType.THEME_ANALYSIS,
    CopilotAgentName.MACRO: CopilotIntentType.MACRO_QUERY,
    CopilotAgentName.RISK: CopilotIntentType.RISK_QUERY,
    CopilotAgentName.STOCK: CopilotIntentType.STOCK_ANALYSIS,
    CopilotAgentName.WATCHLIST: CopilotIntentType.WATCHLIST_REVIEW,
    CopilotAgentName.REPORT: CopilotIntentType.REPORT_QUERY,
    CopilotAgentName.RESEARCH: CopilotIntentType.RESEARCH_QUERY,
    CopilotAgentName.NAVIGATION: CopilotIntentType.APP_NAVIGATION,
    CopilotAgentName.EDUCATIONAL: CopilotIntentType.EDUCATIONAL_QUERY,
    CopilotAgentName.PORTFOLIO: CopilotIntentType.PORTFOLIO_QUERY,
}


def _context(agent: CopilotAgentName, *, request_id: str = "agent-contract") -> AgentExecutionContext:
    intent_type = _INTENTS[agent]
    intent = CopilotIntentV1(
        intent_id=f"intent-{agent.value}",
        intent=intent_type,
        sub_intent="breadth" if agent == CopilotAgentName.NAVIGATION else "contract_validation",
        ticker_symbols=["ARM"] if agent in {CopilotAgentName.STOCK, CopilotAgentName.INDEX} else [],
        confidence=0.95,
        required_agents=[agent],
    )
    return AgentExecutionContext(
        request_id=request_id,
        question=(
            "Open the breadth screen."
            if agent == CopilotAgentName.NAVIGATION
            else "What does breadth mean?"
            if agent == CopilotAgentName.EDUCATIONAL
            else "Validate the frozen agent contract."
        ),
        intent=intent,
        plan=CopilotPlanner().build(intent),
        client_context={"savedSymbols": ["ARM"]} if agent == CopilotAgentName.WATCHLIST else {},
    )


def _stable_payload(result) -> dict:
    payload = result.model_dump(mode="json", by_alias=True)
    payload.pop("durationMs", None)
    payload["freshness"].pop("generatedAt", None)
    for source in payload["sourceReferences"]:
        source.pop("generatedAt", None)
    for evidence in payload["evidence"]:
        evidence["freshness"].pop("generatedAt", None)
        evidence["source"].pop("generatedAt", None)
    return payload


class Stage7AgentContractEnforcementTests(unittest.TestCase):
    def test_manifest_loads_typed_contract_for_all_runtime_agents(self) -> None:
        contracts = load_agent_contracts()
        self.assertEqual(set(contracts), set(CopilotAgentName))
        self.assertTrue(all(item.deterministic and not item.model_dependent for item in contracts.values()))

    def test_all_actual_registry_handlers_fail_closed_with_no_provider_data(self) -> None:
        registry = CopilotAgentRegistry(sources=_NoProviderSources())
        for agent in CopilotAgentName:
            with self.subTest(agent=agent.value):
                result = registry.execute(agent, _context(agent))
                validation = validate_agent_result(result)
                self.assertEqual(validation.status, "passed", validation.issues)
                self.assertNotEqual(result.failure_category, "agent_contract")

    def test_deterministic_handlers_are_structurally_repeatable(self) -> None:
        registry = CopilotAgentRegistry(sources=_NoProviderSources())
        for agent in CopilotAgentName:
            with self.subTest(agent=agent.value):
                context = _context(agent, request_id=f"repeat-{agent.value}")
                first = registry.execute(agent, context)
                second = registry.execute(agent, context)
                self.assertEqual(_stable_payload(first), _stable_payload(second))

    def test_production_stock_adapter_deduplicates_evidence_before_contract_validation(self) -> None:
        registry = CopilotAgentRegistry(sources=_HermeticArmSources())
        result = registry.execute(CopilotAgentName.STOCK, _context(CopilotAgentName.STOCK))
        evidence_ids = [item.evidence_id for item in result.evidence]
        self.assertTrue(evidence_ids)
        self.assertEqual(len(evidence_ids), len(set(evidence_ids)))
        self.assertNotEqual(result.failure_category, "agent_contract")
        self.assertEqual(validate_agent_result(result).status, "passed")
        self.assertTrue(
            {item.category for item in result.evidence}
            <= {
                CopilotEvidenceCategory.TECHNICAL,
                CopilotEvidenceCategory.SIGNAL,
                CopilotEvidenceCategory.LEADERSHIP,
            }
        )

    def test_registry_rejects_result_from_the_wrong_agent_slot(self) -> None:
        registry = CopilotAgentRegistry()
        context = _context(CopilotAgentName.MARKET)
        wrong_result = registry._educational(context)

        with patch.dict(
            registry._handlers,
            {CopilotAgentName.MARKET: lambda _context: wrong_result},
        ):
            result = registry.execute(CopilotAgentName.MARKET, context)

        self.assertEqual(result.agent, CopilotAgentName.MARKET)
        self.assertEqual(result.status, CopilotAgentStatus.FAILED)
        self.assertEqual(result.failure_category, "agent_contract")
        self.assertTrue(any("agent_mismatch" in value for value in result.warnings))


if __name__ == "__main__":
    unittest.main()
