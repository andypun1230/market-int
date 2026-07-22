from __future__ import annotations

from uuid import uuid4

from app.copilot.contracts import (
    CopilotAgentName,
    CopilotDestination,
    CopilotEvidenceCategory,
    CopilotEvidenceRequirementV1,
    CopilotFreshnessRequirementV1,
    CopilotFreshnessState,
    CopilotIntentType,
    CopilotIntentV1,
    CopilotPlanStepV1,
    CopilotPlanV1,
)


AGENT_CATEGORY = {
    CopilotAgentName.MARKET: CopilotEvidenceCategory.MARKET,
    CopilotAgentName.INDEX: CopilotEvidenceCategory.INDEX,
    CopilotAgentName.BREADTH: CopilotEvidenceCategory.BREADTH,
    CopilotAgentName.LEADERSHIP: CopilotEvidenceCategory.LEADERSHIP,
    CopilotAgentName.SECTOR: CopilotEvidenceCategory.SECTOR,
    CopilotAgentName.THEME: CopilotEvidenceCategory.THEME,
    CopilotAgentName.MACRO: CopilotEvidenceCategory.MACRO,
    CopilotAgentName.RISK: CopilotEvidenceCategory.RISK,
    CopilotAgentName.STOCK: CopilotEvidenceCategory.TECHNICAL,
    CopilotAgentName.WATCHLIST: CopilotEvidenceCategory.WATCHLIST,
    CopilotAgentName.REPORT: CopilotEvidenceCategory.REPORT,
    CopilotAgentName.RESEARCH: CopilotEvidenceCategory.RESEARCH,
    CopilotAgentName.NAVIGATION: CopilotEvidenceCategory.NAVIGATION,
    CopilotAgentName.EDUCATIONAL: CopilotEvidenceCategory.EDUCATIONAL,
    CopilotAgentName.PORTFOLIO: CopilotEvidenceCategory.PORTFOLIO,
}


class CopilotPlanner:
    def build(self, intent: CopilotIntentV1) -> CopilotPlanV1:
        # Optional agents are declared for a deliberate fallback/expansion,
        # but the default plan executes only the engines necessary to answer
        # the classified question.
        agents = list(dict.fromkeys(intent.required_agents))
        navigation = intent.intent == CopilotIntentType.APP_NAVIGATION
        simple = intent.intent in {
            CopilotIntentType.APP_NAVIGATION,
            CopilotIntentType.EDUCATIONAL_QUERY,
            CopilotIntentType.PORTFOLIO_QUERY,
            CopilotIntentType.REPORT_QUERY,
        }
        latency = 500 if navigation else 1200 if simple else 8000 if len(agents) >= 4 else 3000
        steps = [
            CopilotPlanStepV1(
                step_id=f"step-{index}-{agent.value}",
                order=index,
                agent=agent,
                required=agent in intent.required_agents,
                parallel_group=1,
                timeout_ms=min(3000, max(250, latency - 200)),
                purpose=f"Collect validated {evidence_category_for(agent, intent.intent).value} evidence.",
            )
            for index, agent in enumerate(agents, start=1)
        ]
        evidence_requirements = [
            CopilotEvidenceRequirementV1(
                category=evidence_category_for(agent, intent.intent),
                required=agent in intent.required_agents and agent not in {CopilotAgentName.NAVIGATION, CopilotAgentName.EDUCATIONAL, CopilotAgentName.PORTFOLIO},
                entities=[item.entity_id for item in intent.entities],
                minimum_items=0 if agent in {CopilotAgentName.NAVIGATION, CopilotAgentName.EDUCATIONAL, CopilotAgentName.PORTFOLIO} else 1,
            )
            for agent in agents
        ]
        destinations = destinations_for_intent(intent)
        allowed_states = [
            CopilotFreshnessState.LIVE,
            CopilotFreshnessState.DELAYED,
            CopilotFreshnessState.CACHED,
            CopilotFreshnessState.PARTIAL,
            CopilotFreshnessState.MIXED,
            CopilotFreshnessState.STALE,
            CopilotFreshnessState.TEST,
        ]
        return CopilotPlanV1(
            plan_id=f"plan-{uuid4().hex[:12]}",
            intent_id=intent.intent_id,
            ordered_steps=steps,
            required_agents=intent.required_agents,
            optional_agents=intent.optional_agents,
            dependencies={item.step_id: item.depends_on for item in steps},
            required_entities=[item.entity_id for item in intent.entities],
            evidence_requirements=evidence_requirements,
            freshness_requirements=CopilotFreshnessRequirementV1(
                allowed_states=allowed_states,
                maximum_age_seconds=600 if intent.decision_support_requested else None,
                actionability_requires_current=intent.decision_support_requested,
            ),
            response_template=response_template(intent.intent),
            deep_link_requirements=destinations,
            fallback_rules=[
                "Return partial evidence when optional agents fail.",
                "Return insufficient evidence when required evidence is unavailable.",
                "Never promote stale, test, or partial evidence to actionable.",
            ],
            maximum_latency_ms=latency,
            parallel_execution_allowed=len(steps) > 1,
        )


def response_template(intent: CopilotIntentType) -> str:
    if intent == CopilotIntentType.NEWS_QUERY:
        return "news_intelligence"
    if intent == CopilotIntentType.SESSION_NARRATIVE:
        return "session_narrative"
    if intent == CopilotIntentType.APP_NAVIGATION:
        return "navigation"
    if intent == CopilotIntentType.STOCK_DECISION_SUPPORT:
        return "decision_challenge"
    if intent in {CopilotIntentType.STOCK_COMPARISON, CopilotIntentType.INDEX_ANALYSIS}:
        return "comparison"
    if intent == CopilotIntentType.MARKET_STATE:
        return "market_posture"
    return "grounded_answer"


def destinations_for_intent(intent: CopilotIntentV1) -> list[CopilotDestination]:
    value = CopilotIntentType(intent.intent)
    mapping = {
        CopilotIntentType.NEWS_QUERY: _stage8_destinations(intent),
        CopilotIntentType.SESSION_NARRATIVE: _stage8_destinations(intent),
        CopilotIntentType.MARKET_STATE: [CopilotDestination.MARKET_OVERVIEW],
        CopilotIntentType.MARKET_EXPLANATION: [CopilotDestination.MARKET_OVERVIEW],
        CopilotIntentType.INDEX_ANALYSIS: [CopilotDestination.INDEXES],
        CopilotIntentType.SECTOR_ANALYSIS: [CopilotDestination.SECTOR_DETAIL if intent.sectors else CopilotDestination.LEADERSHIP],
        CopilotIntentType.THEME_ANALYSIS: [CopilotDestination.THEME_DETAIL],
        CopilotIntentType.STOCK_ANALYSIS: [CopilotDestination.STOCK_DETAIL],
        CopilotIntentType.STOCK_DECISION_SUPPORT: [CopilotDestination.STOCK_TECHNICAL, CopilotDestination.STOCK_RISK],
        CopilotIntentType.STOCK_COMPARISON: [CopilotDestination.STOCK_DETAIL],
        CopilotIntentType.WATCHLIST_REVIEW: [CopilotDestination.WATCHLIST],
        CopilotIntentType.REPORT_QUERY: [CopilotDestination.REPORT],
        CopilotIntentType.RISK_QUERY: [CopilotDestination.STOCK_RISK if intent.ticker_symbols else CopilotDestination.REPORT],
        CopilotIntentType.SCENARIO_QUERY: [CopilotDestination.REPORT_SCENARIOS],
        CopilotIntentType.MACRO_QUERY: [CopilotDestination.MACRO],
        CopilotIntentType.BREADTH_QUERY: [CopilotDestination.BREADTH],
        CopilotIntentType.RESEARCH_QUERY: [CopilotDestination.REPORT_RESEARCH_FOCUS],
        CopilotIntentType.PORTFOLIO_QUERY: [CopilotDestination.WATCHLIST],
        CopilotIntentType.APP_NAVIGATION: [navigation_destination(intent.sub_intent)],
        CopilotIntentType.EDUCATIONAL_QUERY: [CopilotDestination.BREADTH] if any(item.entity_id == "breadth" for item in intent.entities) else [],
    }
    return mapping.get(value, [])


def evidence_category_for(
    agent: CopilotAgentName,
    intent: CopilotIntentType,
) -> CopilotEvidenceCategory:
    if intent == CopilotIntentType.NEWS_QUERY:
        return CopilotEvidenceCategory.NEWS
    if intent == CopilotIntentType.SESSION_NARRATIVE:
        return CopilotEvidenceCategory.SESSION
    return AGENT_CATEGORY[agent]


def _stage8_destinations(intent: CopilotIntentV1) -> list[CopilotDestination]:
    if intent.sub_intent == "reaction_breadth":
        return [CopilotDestination.LEADERSHIP]
    if intent.sub_intent == "event_risk":
        return [
            CopilotDestination.STOCK_RISK
            if intent.ticker_symbols
            else CopilotDestination.HEALTH
        ]
    if intent.sub_intent == "research_event_context":
        return [CopilotDestination.REPORT_RESEARCH_FOCUS]
    entity_types = {item.entity_type.value for item in intent.entities}
    if "stock" in entity_types or "etf" in entity_types:
        return [CopilotDestination.STOCK_DETAIL]
    if "sector" in entity_types:
        return [CopilotDestination.SECTOR_DETAIL]
    if "theme" in entity_types:
        return [CopilotDestination.THEME_DETAIL]
    if "index" in entity_types:
        return [CopilotDestination.INDEXES]
    if intent.personalization_relevant:
        return [CopilotDestination.WATCHLIST]
    if intent.sub_intent == "macro_event_reaction":
        return [CopilotDestination.MACRO]
    return [CopilotDestination.MARKET_OVERVIEW]


def navigation_destination(target: str) -> CopilotDestination:
    try:
        return CopilotDestination(target)
    except ValueError:
        return CopilotDestination.MARKET_OVERVIEW
