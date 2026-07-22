from __future__ import annotations

import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

from app.analysis_engines.session import (
    EvidenceInterpretation,
    SessionConfidenceLabel,
    SessionDataMode,
    SessionEvidence,
    SessionSourceState,
)
from app.copilot.agents import AgentExecutionContext, CopilotAgentRegistry
from app.copilot.contracts import (
    CopilotAgentName,
    CopilotAgentStatus,
    CopilotEvidenceCategory,
    CopilotIntentType,
)
from app.copilot.entities import EntityResolution, ResolvedEntity
from app.copilot.intent import CopilotIntentClassifier
from app.copilot.planner import CopilotPlanner
from app.copilot.sources import TrustedCopilotSources
from app.intelligence.news import (
    ExpectedDirection,
    MarketReactionObservation,
    NewsEventStatus,
    NewsEventType,
    NewsFreshnessState,
    NewsIntelligenceService,
    NewsQuery,
    NewsQueryMode,
    ReactionWindow,
    SourceQuality,
)
from app.intelligence.session_narrative import (
    NarrativeAvailability,
    NarrativeClaim,
    SessionNarrative,
)
from app.providers.news import HermeticNewsProvider, NewsProviderItem


NOW = datetime(2026, 7, 21, 20, 0, tzinfo=timezone.utc)


class _Resolver:
    def resolve(self, message: str, *, screen_context=None, active_entities=()):
        del screen_context, active_entities
        result = EntityResolution()
        if "NVDA" in message.upper():
            result.entities.append(
                ResolvedEntity("stock", "NVDA", "NVIDIA", symbol="NVDA", source="test_registry")
            )
        return result


def _context(question: str) -> AgentExecutionContext:
    intent = CopilotIntentClassifier(resolver=_Resolver()).classify(question)
    plan = CopilotPlanner().build(intent)
    return AgentExecutionContext(
        request_id="stage8-copilot-test",
        question=question,
        intent=intent,
        plan=plan,
        client_context={},
    )


class _NewsSources:
    def __init__(self, *, with_reaction: bool = False) -> None:
        item = NewsProviderItem(
            provider_event_id="issuer-guidance-1",
            headline="NVIDIA updates full-year guidance",
            summary="The issuer published revised full-year guidance.",
            source_identifier="fixture-company-ir",
            source_name="NVIDIA Investor Relations Fixture",
            source_url="https://ir.fixture.test/releases/guidance",
            published_at=NOW - timedelta(minutes=30),
            first_seen_at=NOW - timedelta(minutes=29),
            structured_event_type=NewsEventType.GUIDANCE,
            structured_symbols=("NVDA",),
            confirmed_facts=("The issuer published revised full-year guidance.",),
            event_status=NewsEventStatus.CONFIRMED,
            is_official_release=True,
        )
        service = NewsIntelligenceService(
            provider=HermeticNewsProvider((item,), clock=lambda: NOW)
        )
        observations = (
            MarketReactionObservation(
                event_id="issuer-guidance-1",
                entity_id="NVDA",
                symbol="NVDA",
                window=ReactionWindow.CLOSE_TO_CLOSE,
                window_start=NOW - timedelta(days=1),
                window_end=NOW,
                price_return=0.025,
                benchmark_return=0.004,
                expected_direction=ExpectedDirection.POSITIVE,
                evidence_ids=("price-evidence-nvda-1",),
                source_id="market-bars:NVDA",
                source_quality=SourceQuality.HIGH_CONFIDENCE_SECONDARY,
                source_state=NewsFreshnessState.TEST,
            ),
        ) if with_reaction else ()
        self.result = service.query(
            NewsQuery(
                mode=NewsQueryMode.SECURITY,
                as_of=NOW,
                symbols=("NVDA",),
            ),
            reaction_observations=observations,
        )

    def news_intelligence(self, intent, *, watchlist_symbols=(), as_of=None):
        del intent, watchlist_symbols, as_of
        return self.result


class _SessionSources:
    def session_narrative(self, intent, *, as_of=None):
        del intent, as_of
        return SessionNarrative(
            symbol="NVDA",
            session_date=date(2026, 7, 21),
            availability=NarrativeAvailability.PARTIAL,
            data_mode=SessionDataMode.INTRADAY_5M,
            headline="NVDA shows an observed afternoon reversal in partial fixture data.",
            claims=(
                NarrativeClaim(
                    claim_id="claim:session-evidence-1",
                    text="The observed price path reversed during the configured afternoon segment.",
                    evidence_ids=("session-evidence-1",),
                ),
                NarrativeClaim(
                    claim_id="claim:session-evidence-2",
                    text="The closing phase did not preserve the earlier reversal.",
                    evidence_ids=("session-evidence-2",),
                ),
            ),
            evidence=(
                SessionEvidence(
                    evidence_id="session-evidence-1",
                    entity="NVDA",
                    metric="afternoon price path",
                    value="reversed",
                    timeframe="configured afternoon segment",
                    statement=(
                        "The observed price path reversed during the configured "
                        "afternoon segment."
                    ),
                    interpretation=EvidenceInterpretation.ENGINE_CONCLUSION,
                    source_id="session-fixture-bars",
                ),
                SessionEvidence(
                    evidence_id="session-evidence-2",
                    entity="NVDA",
                    metric="closing follow-through",
                    value="not preserved",
                    timeframe="configured close segment",
                    statement="The closing phase did not preserve the earlier reversal.",
                    interpretation=EvidenceInterpretation.CONTRADICTION,
                    source_id="session-fixture-bars",
                    contradicts_evidence_ids=("session-evidence-1",),
                ),
            ),
            confidence=SessionConfidenceLabel.LIMITED,
            freshness=SessionSourceState.TEST,
            coverage=0.72,
            caveats=(
                "Hermetic intraday bars are test data.",
                "Temporal proximity does not establish causality.",
            ),
        )


class Stage8CopilotIntegrationTests(unittest.TestCase):
    def test_news_result_is_adapted_by_existing_stock_agent(self) -> None:
        context = _context("What news affected NVDA?")
        self.assertEqual(context.intent.intent, CopilotIntentType.NEWS_QUERY)
        result = CopilotAgentRegistry(sources=_NewsSources()).execute(
            CopilotAgentName.STOCK,
            context,
        )
        self.assertEqual(result.agent, CopilotAgentName.STOCK)
        self.assertEqual(result.status, CopilotAgentStatus.PARTIAL)
        self.assertTrue(result.evidence)
        self.assertEqual({item.category for item in result.evidence}, {CopilotEvidenceCategory.NEWS})
        self.assertTrue(result.metrics["event_ids"])
        self.assertTrue(result.metrics["cluster_ids"])
        self.assertEqual(result.metrics["provider_mode"], "test")
        self.assertNotIn("article_body", result.model_dump_json())

    def test_missing_news_reaction_remains_missing_instead_of_becoming_a_conclusion(self) -> None:
        result = CopilotAgentRegistry(sources=_NewsSources()).execute(
            CopilotAgentName.STOCK,
            _context("Did price confirm the news for NVDA?"),
        )

        self.assertEqual(result.status, CopilotAgentStatus.PARTIAL)
        self.assertTrue(result.missing_data)
        self.assertFalse(
            any(item.metric == "market reaction classification" for item in result.evidence)
        )
        self.assertFalse(
            any("insufficient" in item.casefold() for item in result.conclusions)
        )
        self.assertEqual(result.metrics["news_confidence"], "limited")

    def test_news_lineage_confidence_and_deep_links_survive_copilot_adaptation(self) -> None:
        sources = _NewsSources(with_reaction=True)
        result = CopilotAgentRegistry(sources=sources).execute(
            CopilotAgentName.STOCK,
            _context("Did price confirm the news for NVDA?"),
        )

        registered_sources = {item.source_id for item in result.source_references}
        self.assertTrue(registered_sources)
        self.assertTrue(
            all(item.source.source_id in registered_sources for item in result.evidence)
        )
        mapping_lineage = {
            item.source.raw_engine_reference
            for item in result.evidence
            if item.metric == "validated entity mapping"
        }
        self.assertEqual(
            mapping_lineage,
            set(result.metrics["mapping_evidence_ids"]),
        )
        reaction = next(
            item
            for item in result.evidence
            if item.metric == "observed price reaction evidence"
        )
        self.assertEqual(reaction.source.provider, "market-bars:NVDA")
        self.assertEqual(reaction.source.raw_engine_reference, "price-evidence-nvda-1")
        self.assertEqual(reaction.confidence.value, sources.result.confidence.value)
        self.assertIn("stock_detail", {item.value for item in result.deep_link_targets})
        self.assertIn("sector_detail", {item.value for item in result.deep_link_targets})
        self.assertTrue(result.metrics["news_deep_links"])

    def test_event_detail_intent_uses_the_direct_cached_event_boundary(self) -> None:
        intent = CopilotIntentClassifier().classify(
            "Show source for news-event-123."
        )
        expected = _NewsSources().result

        class RecordingService:
            event_id: str | None = None

            def query_cached_event(self, event_id, *, as_of):
                self.event_id = event_id
                self.as_of = as_of
                return expected

        service = RecordingService()
        with patch(
            "app.intelligence.news.get_news_intelligence_service",
            return_value=service,
        ):
            value = TrustedCopilotSources().news_intelligence(intent, as_of=NOW)

        self.assertIs(value, expected)
        self.assertEqual(service.event_id, "news-event-123")
        self.assertEqual(service.as_of, NOW)

    def test_leadership_risk_and_research_agents_consume_typed_news_evidence(self) -> None:
        cases = (
            (
                "Was the reaction broad or concentrated?",
                CopilotAgentName.LEADERSHIP,
            ),
            (
                "What event risk came from the NVDA news?",
                CopilotAgentName.RISK,
            ),
            (
                "Show the research catalyst for NVDA.",
                CopilotAgentName.RESEARCH,
            ),
        )
        for question, expected_agent in cases:
            with self.subTest(question=question):
                context = _context(question)
                self.assertEqual(context.intent.required_agents, [expected_agent])
                result = CopilotAgentRegistry(sources=_NewsSources()).execute(
                    expected_agent,
                    context,
                )
                self.assertEqual(result.agent, expected_agent)
                self.assertEqual(result.status, CopilotAgentStatus.PARTIAL)
                self.assertTrue(result.evidence)
                self.assertEqual(
                    {item.category for item in result.evidence},
                    {CopilotEvidenceCategory.NEWS},
                )

    def test_session_result_is_adapted_by_existing_stock_agent(self) -> None:
        context = _context("Describe NVDA intraday structure and its VWAP reclaim.")
        self.assertEqual(context.intent.intent, CopilotIntentType.SESSION_NARRATIVE)
        result = CopilotAgentRegistry(sources=_SessionSources()).execute(
            CopilotAgentName.STOCK,
            context,
        )
        self.assertEqual(result.agent, CopilotAgentName.STOCK)
        self.assertEqual(result.status, CopilotAgentStatus.PARTIAL)
        self.assertTrue(result.evidence)
        self.assertEqual({item.category for item in result.evidence}, {CopilotEvidenceCategory.SESSION})
        self.assertEqual(result.metrics["data_mode"], "intraday_5m")
        self.assertIn("does not establish causality", " ".join(result.conclusions).casefold())
        registered_sources = {item.source_id for item in result.source_references}
        self.assertTrue(
            all(item.source.source_id in registered_sources for item in result.evidence)
        )
        self.assertTrue(
            all(item.source.provider == "session-fixture-bars" for item in result.evidence)
        )
        contradiction = next(
            item
            for item in result.evidence
            if item.interpretation_class.value == "contradiction"
        )
        self.assertEqual(
            contradiction.contradicts_claim_ids,
            ["claim:session-evidence-1"],
        )

    def test_report_agent_has_a_retrieval_seam_without_pdf_rendering_changes(self) -> None:
        news = CopilotAgentRegistry(sources=_NewsSources()).execute(
            CopilotAgentName.REPORT,
            _context("What news affected NVDA?"),
        )
        session = CopilotAgentRegistry(sources=_SessionSources()).execute(
            CopilotAgentName.REPORT,
            _context("Describe NVDA intraday structure and its VWAP reclaim."),
        )

        self.assertEqual(news.agent, CopilotAgentName.REPORT)
        self.assertTrue(news.evidence)
        self.assertEqual(
            {item.category for item in news.evidence},
            {CopilotEvidenceCategory.NEWS},
        )
        self.assertEqual(session.agent, CopilotAgentName.REPORT)
        self.assertTrue(session.evidence)
        self.assertEqual(
            {item.category for item in session.evidence},
            {CopilotEvidenceCategory.SESSION},
        )

    def test_production_default_news_and_session_fail_closed(self) -> None:
        registry = CopilotAgentRegistry()
        news = registry.execute(CopilotAgentName.MARKET, _context("What moved the market today?"))
        session = registry.execute(
            CopilotAgentName.MARKET,
            _context("What happened during the final hour?"),
        )
        self.assertEqual(news.status, CopilotAgentStatus.UNAVAILABLE)
        self.assertEqual(session.status, CopilotAgentStatus.UNAVAILABLE)
        self.assertFalse(news.evidence)
        self.assertFalse(session.evidence)
        self.assertTrue(news.missing_data)
        self.assertTrue(session.missing_data)


if __name__ == "__main__":
    unittest.main()
