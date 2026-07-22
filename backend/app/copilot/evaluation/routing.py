from __future__ import annotations

from time import perf_counter
from typing import Any

from app.copilot.contracts import (
    CopilotEntityV1,
    CopilotSessionContextV1,
)
from app.copilot.entities import EntityResolution, ResolvedEntity
from app.copilot.evaluation.contracts import EvaluationCandidate, GoldenEvaluationCase
from app.copilot.intent import CopilotIntentClassifier
from app.copilot.planner import CopilotPlanner


class FrozenCaseResolver:
    """Case-bound entity resolver with no storage or provider dependency."""

    def __init__(self, case: GoldenEvaluationCase) -> None:
        self.case = case

    def resolve(
        self,
        message: str,
        *,
        screen_context: dict[str, Any] | None = None,
        active_entities=(),
    ) -> EntityResolution:
        del message, screen_context, active_entities
        result = EntityResolution()
        result.entities = [
            ResolvedEntity(
                item.entity_type,
                item.entity_id,
                item.display_name,
                symbol=item.symbol,
                confidence=item.confidence,
                source="stage7-frozen-fixture",
            )
            for item in self.case.frozen_input.resolved_entities
        ]
        result.unresolved = list(self.case.frozen_input.unresolved_entities)
        result.ambiguous = list(self.case.frozen_input.ambiguous_entities)
        return result


def _session(case: GoldenEvaluationCase) -> CopilotSessionContextV1 | None:
    raw = case.frozen_input.session_context
    if not raw:
        return None
    entities = [
        CopilotEntityV1(
            entity_id=str(item["entity_id"]),
            entity_type=str(item["entity_type"]),
            display_name=str(item.get("display_name") or item["entity_id"]),
            symbol=item.get("symbol"),
            resolution_source="stage7-frozen-session",
        )
        for item in raw.get("active_entities", [])
    ]
    return CopilotSessionContextV1(
        thread_id=str(raw.get("thread_id") or f"eval-{case.fixture_id}"),
        active_entities=entities,
        active_intent=raw.get("active_intent"),
        latest_referenced_stock=raw.get("latest_referenced_stock"),
        latest_referenced_sector_or_theme=raw.get("latest_referenced_sector_or_theme"),
        latest_report_id=raw.get("latest_report_id"),
        latest_thesis=raw.get("latest_thesis"),
        unresolved_question=raw.get("unresolved_question"),
        previous_answer_stance=raw.get("previous_answer_stance"),
        relevant_evidence_ids=raw.get("relevant_evidence_ids", []),
        current_screen=raw.get("current_screen"),
        current_route=raw.get("current_route"),
        updated_at=str(raw.get("updated_at") or case.frozen_input.as_of),
    )


def apply_deterministic_routing(
    case: GoldenEvaluationCase,
    candidate: EvaluationCandidate | None = None,
) -> EvaluationCandidate:
    """Replace reference routing fields with current deterministic output."""

    reference = candidate or case.reference_output
    classifier = CopilotIntentClassifier(resolver=FrozenCaseResolver(case))
    started = perf_counter()
    intent = classifier.classify(
        case.frozen_input.question,
        screen_context=case.frozen_input.screen_context,
        session=_session(case),
    )
    plan = CopilotPlanner().build(intent)
    latency_ms = (perf_counter() - started) * 1000
    return reference.model_copy(
        update={
            "intent": intent.intent,
            "selected_agents": [step.agent for step in plan.ordered_steps],
            "deep_links": list(plan.deep_link_requirements),
            "latency_ms": latency_ms,
        },
        deep=True,
    )
