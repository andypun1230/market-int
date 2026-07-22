from __future__ import annotations

import unittest

from app.copilot.contracts import (
    CopilotAgentName,
    CopilotAmbiguityLevel,
    CopilotDestination,
    CopilotEvidenceCategory,
    CopilotIntentType,
)
from app.copilot.entities import EntityResolution, ResolvedEntity
from app.copilot.intent import CopilotIntentClassifier
from app.copilot.planner import CopilotPlanner


class _Stage8Resolver:
    def resolve(self, message: str, *, screen_context=None, active_entities=()):
        del screen_context, active_entities
        upper = message.upper()
        lowered = message.casefold()
        result = EntityResolution()
        if "NVDA" in upper:
            result.entities.append(ResolvedEntity("stock", "NVDA", "NVIDIA", symbol="NVDA", source="test_registry"))
        if "QQQ" in upper:
            result.entities.append(ResolvedEntity("index", "QQQ", "Nasdaq 100", symbol="QQQ", source="test_registry"))
        if "technology" in lowered or "semiconductor" in lowered:
            result.entities.append(ResolvedEntity("sector", "technology", "Technology", source="test_taxonomy"))
        if "cybersecurity" in lowered:
            result.entities.append(ResolvedEntity("theme", "cybersecurity", "Cybersecurity", source="test_taxonomy"))
        return result


class Stage8CopilotRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.classifier = CopilotIntentClassifier(resolver=_Stage8Resolver())

    def assert_route(
        self,
        question: str,
        intent_type: CopilotIntentType,
        sub_intent: str,
        agent: CopilotAgentName,
        category: CopilotEvidenceCategory,
        destination: CopilotDestination,
    ) -> None:
        intent = self.classifier.classify(question)
        plan = CopilotPlanner().build(intent)
        self.assertEqual(intent.intent, intent_type)
        self.assertEqual(intent.sub_intent, sub_intent)
        self.assertEqual(intent.required_agents, [agent])
        self.assertEqual([item.agent for item in plan.ordered_steps], [agent])
        self.assertEqual([item.category for item in plan.evidence_requirements], [category])
        self.assertEqual(plan.deep_link_requirements, [destination])

    def test_market_news_and_move_explanation_use_market_agent(self) -> None:
        self.assert_route(
            "What were today's most important events?",
            CopilotIntentType.NEWS_QUERY,
            "latest_market_news",
            CopilotAgentName.MARKET,
            CopilotEvidenceCategory.NEWS,
            CopilotDestination.MARKET_OVERVIEW,
        )
        self.assert_route(
            "What moved the market today?",
            CopilotIntentType.NEWS_QUERY,
            "market_move_explanation",
            CopilotAgentName.MARKET,
            CopilotEvidenceCategory.NEWS,
            CopilotDestination.MARKET_OVERVIEW,
        )

    def test_entity_news_uses_existing_specialist_agents(self) -> None:
        cases = (
            ("What news affected NVDA?", "security_news", CopilotAgentName.STOCK, CopilotDestination.STOCK_DETAIL),
            ("Why did QQQ fall?", "market_move_explanation", CopilotAgentName.INDEX, CopilotDestination.INDEXES),
            ("What catalyst affected the Technology sector?", "sector_news", CopilotAgentName.SECTOR, CopilotDestination.SECTOR_DETAIL),
            ("What news affected cybersecurity?", "theme_news", CopilotAgentName.THEME, CopilotDestination.THEME_DETAIL),
        )
        for question, sub_intent, agent, destination in cases:
            with self.subTest(question=question):
                self.assert_route(
                    question,
                    CopilotIntentType.NEWS_QUERY,
                    sub_intent,
                    agent,
                    CopilotEvidenceCategory.NEWS,
                    destination,
                )

    def test_macro_reaction_uses_macro_agent(self) -> None:
        self.assert_route(
            "Did the market react positively to the CPI release?",
            CopilotIntentType.NEWS_QUERY,
            "macro_event_reaction",
            CopilotAgentName.MACRO,
            CopilotEvidenceCategory.NEWS,
            CopilotDestination.MACRO,
        )

    def test_headline_price_contradiction_is_explicit(self) -> None:
        self.assert_route(
            "Did price confirm the news for NVDA?",
            CopilotIntentType.NEWS_QUERY,
            "headline_price_contradiction",
            CopilotAgentName.STOCK,
            CopilotEvidenceCategory.NEWS,
            CopilotDestination.STOCK_DETAIL,
        )

    def test_leadership_risk_and_research_reuse_existing_agents_for_news_context(self) -> None:
        cases = (
            (
                "Was the reaction broad or concentrated?",
                "reaction_breadth",
                CopilotAgentName.LEADERSHIP,
                CopilotDestination.LEADERSHIP,
            ),
            (
                "What event risk came from the NVDA news?",
                "event_risk",
                CopilotAgentName.RISK,
                CopilotDestination.STOCK_RISK,
            ),
            (
                "Show the research catalyst for NVDA.",
                "research_event_context",
                CopilotAgentName.RESEARCH,
                CopilotDestination.REPORT_RESEARCH_FOCUS,
            ),
        )
        for question, sub_intent, agent, destination in cases:
            with self.subTest(question=question):
                self.assert_route(
                    question,
                    CopilotIntentType.NEWS_QUERY,
                    sub_intent,
                    agent,
                    CopilotEvidenceCategory.NEWS,
                    destination,
                )

    def test_session_queries_use_session_evidence_without_new_agents(self) -> None:
        self.assert_route(
            "What happened during the final hour?",
            CopilotIntentType.SESSION_NARRATIVE,
            "final_hour",
            CopilotAgentName.MARKET,
            CopilotEvidenceCategory.SESSION,
            CopilotDestination.MARKET_OVERVIEW,
        )
        self.assert_route(
            "Describe NVDA intraday structure and its VWAP reclaim.",
            CopilotIntentType.SESSION_NARRATIVE,
            "vwap_context",
            CopilotAgentName.STOCK,
            CopilotEvidenceCategory.SESSION,
            CopilotDestination.STOCK_DETAIL,
        )

    def test_validated_stage7_market_question_keeps_legacy_route(self) -> None:
        intent = self.classifier.classify("Why did the market fall?")
        self.assertEqual(intent.intent, CopilotIntentType.MARKET_EXPLANATION)
        self.assertEqual(intent.required_agents, [CopilotAgentName.MARKET, CopilotAgentName.BREADTH])

    def test_exact_stage8_prompts_use_production_resolution_or_fail_closed(self) -> None:
        classifier = CopilotIntentClassifier()

        semiconductors = classifier.classify("Why did semiconductors underperform?")
        self.assertEqual(semiconductors.intent, CopilotIntentType.NEWS_QUERY)
        self.assertEqual(semiconductors.sub_intent, "theme_news")
        self.assertEqual(semiconductors.required_agents, [CopilotAgentName.THEME])
        self.assertEqual(semiconductors.themes, ["semiconductors"])

        event_detail = classifier.classify("Show source for news-event-123.")
        self.assertEqual(event_detail.intent, CopilotIntentType.NEWS_QUERY)
        self.assertEqual(event_detail.sub_intent, "event_detail")
        self.assertEqual(event_detail.required_agents, [CopilotAgentName.MARKET])
        self.assertEqual(event_detail.entities[0].entity_type.value, "news_event")
        self.assertEqual(event_detail.entities[0].entity_id, "news-event-123")

        ambiguous_navigation = classifier.classify(
            "Open the related stock or sector screen."
        )
        self.assertEqual(
            ambiguous_navigation.intent,
            CopilotIntentType.UNSUPPORTED_OR_AMBIGUOUS,
        )
        self.assertEqual(
            ambiguous_navigation.sub_intent,
            "related_navigation_requires_context",
        )
        self.assertEqual(
            ambiguous_navigation.ambiguity_level,
            CopilotAmbiguityLevel.HIGH,
        )
        self.assertTrue(ambiguous_navigation.clarification_question)
        self.assertEqual(ambiguous_navigation.required_agents, [])

        contextual_navigation = classifier.classify(
            "Open the related stock or sector screen.",
            screen_context={
                "screenType": "sector",
                "sector": {"id": "information_technology"},
            },
        )
        self.assertEqual(
            contextual_navigation.intent,
            CopilotIntentType.APP_NAVIGATION,
        )
        self.assertEqual(contextual_navigation.sub_intent, "sector_detail")
        self.assertEqual(
            contextual_navigation.required_agents,
            [CopilotAgentName.NAVIGATION],
        )

    def test_all_twelve_required_stage8_prompts_have_explicit_routes(self) -> None:
        classifier = CopilotIntentClassifier()
        cases = (
            ("What moved the market today?", CopilotIntentType.NEWS_QUERY, "market_move_explanation", CopilotAgentName.MARKET),
            ("Why did QQQ fall?", CopilotIntentType.NEWS_QUERY, "market_move_explanation", CopilotAgentName.INDEX),
            ("What happened during the final hour?", CopilotIntentType.SESSION_NARRATIVE, "final_hour", CopilotAgentName.MARKET),
            ("What news affected NVDA?", CopilotIntentType.NEWS_QUERY, "security_news", CopilotAgentName.STOCK),
            ("Did the market react positively to CPI?", CopilotIntentType.NEWS_QUERY, "macro_event_reaction", CopilotAgentName.MACRO),
            ("Why did semiconductors underperform?", CopilotIntentType.NEWS_QUERY, "theme_news", CopilotAgentName.THEME),
            ("Was the reaction broad or concentrated?", CopilotIntentType.NEWS_QUERY, "reaction_breadth", CopilotAgentName.LEADERSHIP),
            ("What were today’s most important events?", CopilotIntentType.NEWS_QUERY, "latest_market_news", CopilotAgentName.MARKET),
            ("Did price confirm the news?", CopilotIntentType.NEWS_QUERY, "headline_price_contradiction", CopilotAgentName.MARKET),
            ("Is this headline already priced in?", CopilotIntentType.NEWS_QUERY, "headline_price_contradiction", CopilotAgentName.MARKET),
            ("What happened after the Fed announcement?", CopilotIntentType.NEWS_QUERY, "macro_event_reaction", CopilotAgentName.MACRO),
            ("Open the related stock or sector screen.", CopilotIntentType.UNSUPPORTED_OR_AMBIGUOUS, "related_navigation_requires_context", None),
        )
        for question, intent_type, sub_intent, required_agent in cases:
            with self.subTest(question=question):
                intent = classifier.classify(question)
                self.assertEqual(intent.intent, intent_type)
                self.assertEqual(intent.sub_intent, sub_intent)
                self.assertEqual(
                    intent.required_agents,
                    [required_agent] if required_agent is not None else [],
                )

        comparison = classifier.classify("Compare the catalysts for NVDA and MSFT.")
        self.assertEqual(comparison.intent, CopilotIntentType.NEWS_QUERY)
        self.assertEqual(comparison.sub_intent, "catalyst_comparison")

    def test_no_registered_agent_was_added(self) -> None:
        self.assertEqual(len(CopilotAgentName), 15)
        self.assertNotIn("news", {item.value for item in CopilotAgentName})
        self.assertNotIn("session", {item.value for item in CopilotAgentName})


if __name__ == "__main__":
    unittest.main()
