from __future__ import annotations

import re
from typing import Any
from uuid import uuid4

from app.copilot.contracts import (
    CopilotAgentName,
    CopilotAmbiguityLevel,
    CopilotEntityType,
    CopilotEntityV1,
    CopilotIntentType,
    CopilotIntentV1,
    CopilotOutputType,
    CopilotSessionContextV1,
    CopilotTimeHorizon,
)
from app.copilot.entities import CopilotEntityResolver, ResolvedEntity
from app.copilot.policy import contains_prompt_injection, contains_secret
from app.copilot.sources import extract_saved_symbols


class CopilotIntentClassifier:
    def __init__(self, resolver: CopilotEntityResolver | None = None) -> None:
        self.resolver = resolver or CopilotEntityResolver()

    def classify(
        self,
        message: str,
        *,
        screen_context: dict[str, Any] | None = None,
        session: CopilotSessionContextV1 | None = None,
    ) -> CopilotIntentV1:
        normalized = " ".join(message.strip().split())
        lowered = normalized.casefold()
        active = [item.model_dump(mode="json") for item in session.active_entities] if session else []
        resolution = self.resolver.resolve(normalized, screen_context=screen_context, active_entities=active)
        entities = [self._entity_model(item) for item in resolution.entities]
        entity_types = {item.entity_type for item in entities}
        screen_type = str((screen_context or {}).get("screenType") or (screen_context or {}).get("screen_type") or "").casefold()
        related_navigation = self._is_related_navigation(lowered)
        related_entity = self._related_navigation_entity(entities, session) if related_navigation else None
        if related_entity is not None and not any(
            item.entity_type == related_entity.entity_type and item.entity_id == related_entity.entity_id
            for item in entities
        ):
            entities.append(related_entity)
            entity_types.add(related_entity.entity_type)

        intent = CopilotIntentType.UNSUPPORTED_OR_AMBIGUOUS
        sub_intent = "unsupported"
        output = CopilotOutputType.ANSWER
        navigation = False
        decision = False
        personalization = False
        confidence = 0.55

        if contains_prompt_injection(normalized):
            intent, sub_intent, confidence = CopilotIntentType.UNSUPPORTED_OR_AMBIGUOUS, "instruction_override_attempt", 1.0
        elif related_navigation:
            if related_entity is None:
                intent, sub_intent, confidence = (
                    CopilotIntentType.UNSUPPORTED_OR_AMBIGUOUS,
                    "related_navigation_requires_context",
                    0.4,
                )
            else:
                intent, sub_intent, output, navigation, confidence = (
                    CopilotIntentType.APP_NAVIGATION,
                    self._related_navigation_target(related_entity),
                    CopilotOutputType.NAVIGATION,
                    True,
                    0.96,
                )
        elif self._is_follow_up(lowered, session):
            intent, sub_intent, confidence = CopilotIntentType.FOLLOW_UP, self._follow_up_kind(lowered), 0.92 if session else 0.55
        elif self._is_navigation(lowered):
            intent, sub_intent, output, navigation, confidence = CopilotIntentType.APP_NAVIGATION, self._navigation_target(lowered), CopilotOutputType.NAVIGATION, True, 0.96
        elif self._contains(lowered, "portfolio", "holdings", "sector concentration", "portfolio beta", "unrealized p/l"):
            intent, sub_intent, personalization, confidence = CopilotIntentType.PORTFOLIO_QUERY, "portfolio_intelligence", True, 0.98
        elif self._is_educational(lowered):
            intent, sub_intent, output, confidence = CopilotIntentType.EDUCATIONAL_QUERY, "concept_explanation", CopilotOutputType.EDUCATIONAL, 0.93
        elif self._is_session_narrative(lowered):
            intent, sub_intent, confidence = CopilotIntentType.SESSION_NARRATIVE, self._session_sub_intent(lowered), 0.97
        elif self._is_news_query(lowered, entity_types):
            intent = CopilotIntentType.NEWS_QUERY
            sub_intent = self._news_sub_intent(lowered, entity_types)
            personalization = "watchlist" in lowered or "saved stock" in lowered
            confidence = 0.96
        elif self._is_stock_decision(lowered) and (CopilotEntityType.STOCK in entity_types or screen_type == "stock"):
            intent, sub_intent, output, decision, confidence = CopilotIntentType.STOCK_DECISION_SUPPORT, "challenge" if "challenge" in lowered else "actionability", CopilotOutputType.DECISION_SUPPORT, True, 0.96
        elif self._is_comparison(lowered) and entity_types <= {CopilotEntityType.INDEX} and len(entities) >= 2:
            intent, sub_intent, output, confidence = CopilotIntentType.INDEX_ANALYSIS, "comparison", CopilotOutputType.COMPARISON, 0.96
        elif self._is_comparison(lowered) and len([item for item in entities if item.entity_type == CopilotEntityType.STOCK]) >= 2:
            intent, sub_intent, output, confidence = CopilotIntentType.STOCK_COMPARISON, "relative_setup_quality", CopilotOutputType.COMPARISON, 0.97
        elif "watchlist" in lowered or "saved stock" in lowered or screen_type == "watchlist":
            intent, sub_intent, personalization, confidence = CopilotIntentType.WATCHLIST_REVIEW, "attention_review", True, 0.94
        elif "research focus" in lowered or "research subject" in lowered or ("selected" in lowered and CopilotEntityType.THEME in entity_types):
            intent, sub_intent, confidence = CopilotIntentType.RESEARCH_QUERY, "research_focus", 0.96
        elif self._contains(lowered, "invalidate", "invalidation", "main risk", "what are the risks", "risk?"):
            intent, sub_intent, confidence = CopilotIntentType.RISK_QUERY, "thesis_risk", 0.93
        elif self._contains(lowered, "bull case", "bear case", "scenario", "turn the market bearish"):
            intent, sub_intent, confidence = CopilotIntentType.SCENARIO_QUERY, "conditional_paths", 0.95
        elif "report" in lowered or screen_type == "report":
            report_sub_intent = "report_change" if any(value in lowered for value in ("what changed", "since the previous", "since the prior")) else "latest_report"
            intent, sub_intent, confidence = CopilotIntentType.REPORT_QUERY, report_sub_intent, 0.94
        elif self._contains(lowered, "macro", "rates", "oil", "dollar", "gold", "treasury", "credit"):
            intent, sub_intent, confidence = CopilotIntentType.MACRO_QUERY, "cross_asset_context", 0.9
        elif "breadth" in lowered or "participation" in lowered:
            intent, sub_intent, confidence = CopilotIntentType.BREADTH_QUERY, "confirmation", 0.96
        elif self._is_sector_taxonomy_query(lowered):
            # A taxonomy-level question does not need (and must not invent) a
            # specific sector entity.  The sector agent can rank the trusted
            # sector snapshot as a whole.
            intent, sub_intent, confidence = CopilotIntentType.SECTOR_ANALYSIS, "leadership", 0.94
        elif self._is_theme_taxonomy_query(lowered):
            # Likewise, plural theme questions operate on the reviewed theme
            # universe without fabricating a theme selection.
            intent, sub_intent, confidence = CopilotIntentType.THEME_ANALYSIS, "leadership", 0.94
        elif CopilotEntityType.SECTOR in entity_types or screen_type == "sector":
            intent, sub_intent, confidence = CopilotIntentType.SECTOR_ANALYSIS, "leadership", 0.95
        elif CopilotEntityType.THEME in entity_types or screen_type == "theme":
            intent, sub_intent, confidence = CopilotIntentType.THEME_ANALYSIS, "leadership", 0.95
        elif CopilotEntityType.INDEX in entity_types:
            intent, sub_intent, confidence = CopilotIntentType.INDEX_ANALYSIS, "structure", 0.95
        elif CopilotEntityType.STOCK in entity_types or screen_type == "stock":
            intent, sub_intent, confidence = CopilotIntentType.STOCK_ANALYSIS, "setup", 0.94
        elif self._contains(
            lowered,
            "why is the market",
            "why did the market",
            "why did market",
            "driving",
            "what changed",
            "why is today",
            "why weak",
        ):
            intent, sub_intent, confidence = CopilotIntentType.MARKET_EXPLANATION, "evidence_relationships", 0.9
        elif self._contains(lowered, "market condition", "market doing", "market healthy", "risk-on", "risk off", "market state"):
            intent, sub_intent, confidence = CopilotIntentType.MARKET_STATE, "current_posture", 0.94
        elif screen_type in {"home", "market"}:
            intent, sub_intent, confidence = CopilotIntentType.MARKET_STATE, "current_posture", 0.72

        ambiguity = CopilotAmbiguityLevel.NONE
        clarification = None
        if resolution.ambiguous:
            ambiguity, confidence = CopilotAmbiguityLevel.HIGH, min(confidence, 0.45)
            clarification = f"Which {resolution.ambiguous[0]} security did you mean?"
        elif resolution.unresolved and intent in {
            CopilotIntentType.STOCK_ANALYSIS,
            CopilotIntentType.STOCK_COMPARISON,
            CopilotIntentType.STOCK_DECISION_SUPPORT,
            CopilotIntentType.NEWS_QUERY,
            CopilotIntentType.UNSUPPORTED_OR_AMBIGUOUS,
        }:
            intent = CopilotIntentType.UNSUPPORTED_OR_AMBIGUOUS
            sub_intent = "unresolved_security"
            decision = False
            ambiguity, confidence = CopilotAmbiguityLevel.HIGH, min(confidence, 0.4)
            clarification = f"I could not resolve {resolution.unresolved[0]} to a validated security. Which ticker did you mean?"
        elif intent == CopilotIntentType.UNSUPPORTED_OR_AMBIGUOUS:
            if sub_intent == "related_navigation_requires_context":
                ambiguity = CopilotAmbiguityLevel.HIGH
                clarification = (
                    "Which related stock or sector should I open? Ask from an event result "
                    "or name the destination explicitly."
                )
            else:
                ambiguity = CopilotAmbiguityLevel.MODERATE

        if (intent == CopilotIntentType.BREADTH_QUERY or (intent == CopilotIntentType.EDUCATIONAL_QUERY and "breadth" in lowered)) and not any(item.entity_type == CopilotEntityType.METRIC for item in entities):
            entities.append(
                CopilotEntityV1(
                    entity_id="breadth",
                    entity_type=CopilotEntityType.METRIC,
                    display_name="Market Breadth",
                    confidence=1.0,
                    resolution_source="metric_registry",
                )
            )
        if intent == CopilotIntentType.APP_NAVIGATION and not any(item.entity_type == CopilotEntityType.APP_FEATURE for item in entities):
            feature_id = "fear-greed" if sub_intent == "fear_greed" else sub_intent.replace("_", "-")
            entities.append(
                CopilotEntityV1(
                    entity_id=feature_id,
                    entity_type=CopilotEntityType.APP_FEATURE,
                    display_name=feature_id.replace("-", " ").title(),
                    confidence=1.0,
                    resolution_source="route_registry",
                )
            )
        if intent == CopilotIntentType.SCENARIO_QUERY and not any(
            item.entity_type == CopilotEntityType.REPORT_SECTION and item.entity_id == "scenarios"
            for item in entities
        ):
            entities.append(
                CopilotEntityV1(
                    entity_id="scenarios",
                    entity_type=CopilotEntityType.REPORT_SECTION,
                    display_name="Report Scenarios",
                    confidence=1.0,
                    resolution_source="route_registry",
                )
            )

        required, optional = agents_for_intent(intent, session=session)
        if intent == CopilotIntentType.NEWS_QUERY:
            required = [self._stage8_agent(lowered, entity_types, sub_intent)]
            optional = []
        elif intent == CopilotIntentType.SESSION_NARRATIVE:
            required = [self._stage8_agent(lowered, entity_types, sub_intent)]
            optional = []
        elif intent == CopilotIntentType.SECTOR_ANALYSIS and not sectors_from_entities(entities) and sub_intent == "leadership":
            required = [CopilotAgentName.LEADERSHIP]
            optional = [CopilotAgentName.SECTOR, CopilotAgentName.BREADTH]
        elif intent == CopilotIntentType.WATCHLIST_REVIEW and _explicit_empty_saved_list(screen_context or {}):
            required = [CopilotAgentName.WATCHLIST]
            optional = [CopilotAgentName.STOCK]
        elif intent == CopilotIntentType.FOLLOW_UP and session:
            if session.active_intent == CopilotIntentType.STOCK_DECISION_SUPPORT:
                required = [CopilotAgentName.STOCK, CopilotAgentName.RISK]
                optional = [CopilotAgentName.MARKET, CopilotAgentName.BREADTH, CopilotAgentName.RESEARCH]
            elif session.active_intent in {CopilotIntentType.STOCK_ANALYSIS, CopilotIntentType.STOCK_COMPARISON}:
                required = [CopilotAgentName.STOCK]
                optional = [CopilotAgentName.RISK]
        tickers = [item.symbol for item in entities if item.entity_type == CopilotEntityType.STOCK and item.symbol]
        sectors = [item.entity_id for item in entities if item.entity_type == CopilotEntityType.SECTOR]
        themes = [item.entity_id for item in entities if item.entity_type == CopilotEntityType.THEME]
        return CopilotIntentV1(
            intent_id=f"intent-{uuid4().hex[:12]}",
            intent=intent,
            sub_intent=sub_intent,
            entities=entities,
            ticker_symbols=list(dict.fromkeys(tickers)),
            sectors=list(dict.fromkeys(sectors)),
            themes=list(dict.fromkeys(themes)),
            time_horizon=self._time_horizon(lowered, intent),
            requested_output_type=output,
            decision_support_requested=decision,
            personalization_relevant=personalization,
            navigation_requested=navigation,
            ambiguity_level=ambiguity,
            confidence=confidence,
            required_agents=required,
            optional_agents=optional,
            prohibited_assumptions=[
                "Do not infer missing market data.",
                "Do not infer ownership from saved membership.",
                "Do not assert causality without validated attribution.",
                "Do not calculate new engine scores or levels.",
            ],
            unresolved_entities=resolution.unresolved,
            clarification_question=clarification,
        )

    @staticmethod
    def _entity_model(item: ResolvedEntity) -> CopilotEntityV1:
        entity_type = item.entity_type if item.entity_type in {member.value for member in CopilotEntityType} else "app_feature"
        display_name = item.display_name
        if contains_prompt_injection(display_name) or contains_secret(display_name):
            display_name = item.entity_id
        return CopilotEntityV1(
            entity_id=item.entity_id,
            entity_type=entity_type,
            display_name=display_name,
            symbol=item.symbol,
            confidence=item.confidence,
            resolution_source=item.source,
        )

    @staticmethod
    def _contains(text: str, *phrases: str) -> bool:
        return any(phrase in text for phrase in phrases)

    @staticmethod
    def _is_comparison(text: str) -> bool:
        return any(value in text for value in ("compare", " versus ", " vs ", "stronger", "weaker", "which is better"))

    @staticmethod
    def _is_stock_decision(text: str) -> bool:
        return any(value in text for value in ("should i buy", "should i sell", "actionable", "should i wait", "ready to break out", "challenge the", "is this setup confirmed", "is it a buy"))

    @staticmethod
    def _is_educational(text: str) -> bool:
        return bool(re.search(r"^(?:what does|what is|define|teach me|explain)\s+(?:breadth|relative strength|rotation|market regime|support|resistance|volume)\b", text))

    @staticmethod
    def _is_session_narrative(text: str) -> bool:
        return any(
            value in text
            for value in (
                "session narrative",
                "during the session",
                "during today's session",
                "during today’s session",
                "final hour",
                "opening phase",
                "morning recovery",
                "morning reversal",
                "midday reversal",
                "afternoon reversal",
                "lunchtime reversal",
                "intraday structure",
                "vwap reclaim",
                "vwap rejection",
                "premarket session",
                "after-hours session",
            )
        )

    @staticmethod
    def _session_sub_intent(text: str) -> str:
        if "final hour" in text:
            return "final_hour"
        if "premarket" in text:
            return "premarket"
        if "after-hours" in text or "after hours" in text:
            return "after_hours"
        if "vwap" in text:
            return "vwap_context"
        return "session_narrative"

    @staticmethod
    def _is_news_query(text: str, entity_types: set[CopilotEntityType]) -> bool:
        explicit = any(
            value in text
            for value in (
                "latest market news",
                "market news",
                "what moved the market",
                "most important events",
                "material events",
                "what news",
                "which news",
                "news affected",
                "news on",
                "news for",
                "catalyst",
                "fed announcement",
                "fed release",
                "cpi release",
                "economic release",
                "price confirm the news",
                "price confirm the headline",
                "market confirm the news",
                "headline already priced",
                "already priced in",
                "react positively to",
                "react negatively to",
                "reaction broad or concentrated",
                "broad or concentrated",
                "event risk",
                "news risk",
                "catalyst risk",
                "research catalyst",
                "research event",
                "research news",
            )
        )
        event_detail = CopilotEntityType.NEWS_EVENT in entity_types and any(
            value in text for value in ("detail", "source", "correction", "show", "open")
        )
        entity_explanation = bool(entity_types) and bool(
            re.search(r"\bwhy (?:did|is|was|were)\b.*\b(?:fall|fell|drop|dropped|rise|rose|rally|sell off|underperform|outperform)", text)
        )
        return explicit or event_detail or entity_explanation

    @staticmethod
    def _news_sub_intent(text: str, entity_types: set[CopilotEntityType]) -> str:
        if CopilotEntityType.NEWS_EVENT in entity_types:
            return "event_detail"
        if any(
            value in text
            for value in (
                "reaction broad or concentrated",
                "broad or concentrated",
                "broad participation",
                "concentrated reaction",
            )
        ):
            return "reaction_breadth"
        if any(value in text for value in ("event risk", "news risk", "catalyst risk")):
            return "event_risk"
        if any(value in text for value in ("research catalyst", "research event", "research news")):
            return "research_event_context"
        if "compare" in text and "catalyst" in text:
            return "catalyst_comparison"
        if "price confirm" in text or "market confirm" in text or "already priced" in text:
            return "headline_price_contradiction"
        if any(value in text for value in ("fed announcement", "fed release", "cpi release", "economic release", "react positively to", "react negatively to")):
            return "macro_event_reaction"
        if CopilotEntityType.STOCK in entity_types or CopilotEntityType.ETF in entity_types:
            return "security_news"
        if CopilotEntityType.SECTOR in entity_types:
            return "sector_news"
        if CopilotEntityType.THEME in entity_types:
            return "theme_news"
        if CopilotEntityType.INDEX in entity_types:
            return "market_move_explanation"
        if "event" in text and any(value in text for value in ("detail", "source", "correction")):
            return "event_detail"
        if any(value in text for value in ("what moved", "why did", "driving")):
            return "market_move_explanation"
        return "latest_market_news"

    @staticmethod
    def _stage8_agent(
        text: str,
        entity_types: set[CopilotEntityType],
        sub_intent: str,
    ) -> CopilotAgentName:
        if "watchlist" in text or "saved stock" in text:
            return CopilotAgentName.WATCHLIST
        if sub_intent == "reaction_breadth":
            return CopilotAgentName.LEADERSHIP
        if sub_intent == "event_risk":
            return CopilotAgentName.RISK
        if sub_intent == "research_event_context":
            return CopilotAgentName.RESEARCH
        if sub_intent == "macro_event_reaction":
            return CopilotAgentName.MACRO
        if CopilotEntityType.STOCK in entity_types or CopilotEntityType.ETF in entity_types:
            return CopilotAgentName.STOCK
        if CopilotEntityType.SECTOR in entity_types:
            return CopilotAgentName.SECTOR
        if CopilotEntityType.THEME in entity_types:
            return CopilotAgentName.THEME
        if CopilotEntityType.INDEX in entity_types:
            return CopilotAgentName.INDEX
        return CopilotAgentName.MARKET

    @staticmethod
    def _is_navigation(text: str) -> bool:
        navigation_verb = bool(re.search(r"\b(?:open|go to|take me to|where is|where can i find|show the|navigate to)\b", text))
        destination = any(value in text for value in ("fear & greed", "fear and greed", "breadth", "sector rotation", "daily report", "research focus", "settings", "stock detail", "market overview", "indexes", "macro"))
        return navigation_verb and destination

    @staticmethod
    def _is_related_navigation(text: str) -> bool:
        return bool(
            re.search(r"\b(?:open|show|go to|take me to|navigate to)\b", text)
            and "related" in text
            and re.search(r"\b(?:stock|security|sector|theme|screen)\b", text)
        )

    @staticmethod
    def _related_navigation_entity(
        entities: list[CopilotEntityV1],
        session: CopilotSessionContextV1 | None,
    ) -> CopilotEntityV1 | None:
        allowed = {
            CopilotEntityType.STOCK,
            CopilotEntityType.ETF,
            CopilotEntityType.SECTOR,
            CopilotEntityType.THEME,
        }
        candidates = [item for item in entities if item.entity_type in allowed]
        if not candidates and session is not None:
            candidates = [item for item in session.active_entities if item.entity_type in allowed]
        unique = {
            (item.entity_type, item.entity_id): item
            for item in candidates
        }
        return next(iter(unique.values())) if len(unique) == 1 else None

    @staticmethod
    def _related_navigation_target(entity: CopilotEntityV1) -> str:
        if entity.entity_type in {CopilotEntityType.STOCK, CopilotEntityType.ETF}:
            return "stock_detail"
        if entity.entity_type == CopilotEntityType.SECTOR:
            return "sector_detail"
        return "theme_detail"

    @staticmethod
    def _is_sector_taxonomy_query(text: str) -> bool:
        return bool(
            re.search(r"\bsectors?\b", text)
            and any(value in text for value in ("lead", "leading", "lag", "weak", "strong", "rotation", "rank", "best", "worst"))
        )

    @staticmethod
    def _is_theme_taxonomy_query(text: str) -> bool:
        return bool(
            re.search(r"\bthemes?\b", text)
            and any(value in text for value in ("lead", "leading", "lag", "weak", "strong", "rank", "best", "worst", "improv", "deteriorat"))
        )

    @staticmethod
    def _navigation_target(text: str) -> str:
        for phrase, target in (
            ("fear & greed", "fear_greed"), ("fear and greed", "fear_greed"),
            ("research focus", "report_research_focus"), ("daily report", "report"),
            ("sector rotation", "sector_rotation"), ("breadth", "breadth"),
            ("indexes", "indexes"), ("macro", "macro"), ("settings", "settings"),
        ):
            if phrase in text:
                return target
        return "market_overview"

    @staticmethod
    def _is_follow_up(text: str, session: CopilotSessionContextV1 | None) -> bool:
        if not session:
            return False
        compact = text.strip(" .?!")
        return compact in {"why", "show me", "what confirms it", "what invalidates it", "what about risk", "what about volume"} or bool(re.search(r"\b(?:it|that|this stock|that theme)\b", text))

    @staticmethod
    def _follow_up_kind(text: str) -> str:
        if "confirm" in text:
            return "confirmation"
        if "invalidate" in text:
            return "invalidation"
        if "show" in text:
            return "navigation"
        if "risk" in text:
            return "risk"
        return "explanation"

    @staticmethod
    def _time_horizon(text: str, intent: CopilotIntentType) -> CopilotTimeHorizon:
        if any(value in text for value in ("today", "current", "now", "session")):
            return CopilotTimeHorizon.CURRENT_SESSION
        if intent in {CopilotIntentType.NEWS_QUERY, CopilotIntentType.SESSION_NARRATIVE}:
            return CopilotTimeHorizon.CURRENT_SESSION
        if any(value in text for value in ("this week", "short term", "near term")):
            return CopilotTimeHorizon.SHORT_TERM
        if any(value in text for value in ("swing", "medium term", "next month")):
            return CopilotTimeHorizon.MEDIUM_TERM
        if any(value in text for value in ("long term", "year", "investing")):
            return CopilotTimeHorizon.LONG_TERM
        if intent in {CopilotIntentType.REPORT_QUERY, CopilotIntentType.RESEARCH_QUERY, CopilotIntentType.SCENARIO_QUERY}:
            return CopilotTimeHorizon.REPORT_DATE
        return CopilotTimeHorizon.UNSPECIFIED


def agents_for_intent(
    intent: CopilotIntentType,
    *,
    session: CopilotSessionContextV1 | None = None,
) -> tuple[list[CopilotAgentName], list[CopilotAgentName]]:
    mapping: dict[CopilotIntentType, tuple[list[CopilotAgentName], list[CopilotAgentName]]] = {
        CopilotIntentType.NEWS_QUERY: ([CopilotAgentName.MARKET], []),
        CopilotIntentType.SESSION_NARRATIVE: ([CopilotAgentName.MARKET], []),
        CopilotIntentType.MARKET_STATE: ([CopilotAgentName.MARKET], [CopilotAgentName.BREADTH, CopilotAgentName.LEADERSHIP, CopilotAgentName.RISK]),
        CopilotIntentType.MARKET_EXPLANATION: ([CopilotAgentName.MARKET, CopilotAgentName.BREADTH], [CopilotAgentName.LEADERSHIP, CopilotAgentName.RISK, CopilotAgentName.MACRO]),
        CopilotIntentType.INDEX_ANALYSIS: ([CopilotAgentName.INDEX], [CopilotAgentName.MARKET]),
        CopilotIntentType.SECTOR_ANALYSIS: ([CopilotAgentName.SECTOR], [CopilotAgentName.BREADTH, CopilotAgentName.LEADERSHIP]),
        CopilotIntentType.THEME_ANALYSIS: ([CopilotAgentName.THEME], [CopilotAgentName.LEADERSHIP, CopilotAgentName.RESEARCH]),
        CopilotIntentType.STOCK_ANALYSIS: ([CopilotAgentName.STOCK], [CopilotAgentName.MARKET, CopilotAgentName.LEADERSHIP]),
        CopilotIntentType.STOCK_DECISION_SUPPORT: ([CopilotAgentName.STOCK, CopilotAgentName.MARKET, CopilotAgentName.BREADTH, CopilotAgentName.RISK], [CopilotAgentName.LEADERSHIP, CopilotAgentName.RESEARCH]),
        CopilotIntentType.STOCK_COMPARISON: ([CopilotAgentName.STOCK], [CopilotAgentName.MARKET]),
        CopilotIntentType.WATCHLIST_REVIEW: ([CopilotAgentName.WATCHLIST, CopilotAgentName.STOCK], [CopilotAgentName.MARKET, CopilotAgentName.RISK]),
        CopilotIntentType.REPORT_QUERY: ([CopilotAgentName.REPORT], []),
        CopilotIntentType.RISK_QUERY: ([CopilotAgentName.RISK, CopilotAgentName.REPORT], [CopilotAgentName.MARKET]),
        CopilotIntentType.SCENARIO_QUERY: ([CopilotAgentName.REPORT], [CopilotAgentName.RISK]),
        CopilotIntentType.MACRO_QUERY: ([CopilotAgentName.MACRO], [CopilotAgentName.MARKET]),
        CopilotIntentType.BREADTH_QUERY: ([CopilotAgentName.BREADTH], [CopilotAgentName.MARKET]),
        CopilotIntentType.RESEARCH_QUERY: ([CopilotAgentName.RESEARCH, CopilotAgentName.REPORT], []),
        CopilotIntentType.PORTFOLIO_QUERY: ([CopilotAgentName.PORTFOLIO], []),
        CopilotIntentType.APP_NAVIGATION: ([CopilotAgentName.NAVIGATION], []),
        CopilotIntentType.EDUCATIONAL_QUERY: ([CopilotAgentName.EDUCATIONAL], []),
        CopilotIntentType.UNSUPPORTED_OR_AMBIGUOUS: ([], []),
    }
    if intent == CopilotIntentType.FOLLOW_UP and session and session.active_intent:
        try:
            return mapping.get(CopilotIntentType(session.active_intent), ([CopilotAgentName.REPORT], []))
        except ValueError:
            return [CopilotAgentName.REPORT], []
    return mapping.get(intent, ([], []))


def sectors_from_entities(entities: list[CopilotEntityV1]) -> list[str]:
    return [item.entity_id for item in entities if item.entity_type == CopilotEntityType.SECTOR]


def _explicit_empty_saved_list(context: dict[str, Any]) -> bool:
    explicit = "savedSymbols" in context or "saved_symbols" in context
    watchlist = context.get("watchlist")
    explicit = explicit or (isinstance(watchlist, dict) and any(key in watchlist for key in ("symbols", "savedSymbols", "items")))
    return explicit and not extract_saved_symbols(context)
