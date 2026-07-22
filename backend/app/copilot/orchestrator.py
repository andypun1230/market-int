from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Iterable, Iterator
from uuid import uuid4

from app.copilot.actions import build_action
from app.copilot.agents import AgentExecutionContext
from app.copilot.collector import CopilotEvidenceCollector
from app.copilot.contracts import (
    CopilotActionV1,
    CopilotAnswerConfidenceV1,
    CopilotAnswerSectionsV1,
    CopilotConfidenceLabel,
    CopilotDestination,
    CopilotEvidenceBundleV1,
    CopilotFreshnessSummaryV1,
    CopilotFreshnessState,
    CopilotGroundingV1,
    CopilotIntentType,
    CopilotResponseStatus,
    CopilotResponseV1,
    CopilotSessionContextV1,
    CopilotStreamEventType,
    CopilotStreamEventV1,
    CopilotValidationResultV1,
    CopilotValidationStatus,
)
from app.copilot.intent import CopilotIntentClassifier
from app.copilot.planner import CopilotPlanner
from app.copilot.reasoning import CopilotReasoningEngine
from app.copilot.sessions import CopilotSessionStore, coerce_session_context, get_copilot_session_store
from app.copilot.tracing import CopilotTraceRecorder
from app.copilot.validation import CopilotResponseValidator


logger = logging.getLogger(__name__)


class InstitutionalCopilotOrchestrator:
    """Typed Stage 7 pipeline with injectable deterministic boundaries."""

    def __init__(
        self,
        *,
        classifier: CopilotIntentClassifier | None = None,
        planner: CopilotPlanner | None = None,
        collector: CopilotEvidenceCollector | None = None,
        reasoning_engine: CopilotReasoningEngine | None = None,
        validator: CopilotResponseValidator | None = None,
        session_store: CopilotSessionStore | None = None,
        trace_recorder: CopilotTraceRecorder | None = None,
    ) -> None:
        self.classifier = classifier or CopilotIntentClassifier()
        self.planner = planner or CopilotPlanner()
        self.collector = collector or CopilotEvidenceCollector()
        self.reasoning_engine = reasoning_engine or CopilotReasoningEngine()
        self.validator = validator or CopilotResponseValidator()
        self.session_store = session_store or get_copilot_session_store()
        self.trace_recorder = trace_recorder

    def answer(
        self,
        *,
        message: str,
        context: dict[str, Any] | None = None,
        request_id: str | None = None,
        thread_id: str | None = None,
        session_context: CopilotSessionContextV1 | dict[str, Any] | None = None,
    ) -> CopilotResponseV1:
        request_started = perf_counter()
        question = _sanitize_message(message)
        request_id = _request_id(request_id)
        thread = str(thread_id or "unresolved")
        intent = None
        plan = None
        try:
            thread, session, intent, plan = self._classify_and_plan(
                question=question,
                context=context or {},
                thread_id=thread_id,
                session_context=session_context,
            )
            return self._complete(
                request_id=request_id,
                question=question,
                context=context or {},
                thread_id=thread,
                session=session,
                intent=intent,
                plan=plan,
                request_started=request_started,
            )
        except Exception as exc:
            self._record_failure_trace(
                request_id=request_id,
                question=question,
                failure=exc,
                request_started=request_started,
                intent=intent,
                plan=plan,
            )
            logger.warning(
                "institutional_copilot_failed",
                extra={
                    "copilot_event": {
                        "request_id": request_id,
                        "plan_id": getattr(plan, "plan_id", None),
                        "thread_id": thread,
                        "intent": getattr(getattr(intent, "intent", None), "value", None),
                        "failure_category": type(exc).__name__,
                    }
                },
            )
            raise

    def iter_stream_events(
        self,
        *,
        message: str,
        context: dict[str, Any] | None = None,
        request_id: str | None = None,
        thread_id: str | None = None,
        session_context: CopilotSessionContextV1 | dict[str, Any] | None = None,
    ) -> Iterator[CopilotStreamEventV1]:
        request_started = perf_counter()
        question = _sanitize_message(message)
        request_id = _request_id(request_id)
        sequence = 0
        intent = None
        plan = None
        time_to_first_stream_event_ms = None

        def event(event_type: CopilotStreamEventType, payload: dict[str, Any]) -> CopilotStreamEventV1:
            nonlocal sequence
            sequence += 1
            return CopilotStreamEventV1(
                event_id=f"{request_id}:{sequence:02d}",
                type=event_type,
                request_id=request_id,
                payload=payload,
            )

        try:
            thread, session, intent, plan = self._classify_and_plan(
                question=question,
                context=context or {},
                thread_id=thread_id,
                session_context=session_context,
            )
            time_to_first_stream_event_ms = round((perf_counter() - request_started) * 1000, 3)
            yield event(CopilotStreamEventType.START, {"threadId": thread, "schemaVersion": "copilot-stream-v1"})
            yield event(CopilotStreamEventType.INTENT, {"intent": intent.model_dump(mode="json", by_alias=True)})
            yield event(CopilotStreamEventType.PLAN, {"plan": plan.model_dump(mode="json", by_alias=True)})
            response = self._complete(
                request_id=request_id,
                question=question,
                context=context or {},
                thread_id=thread,
                session=session,
                intent=intent,
                plan=plan,
                request_started=request_started,
                time_to_first_stream_event_ms=time_to_first_stream_event_ms,
            )
            yield event(
                CopilotStreamEventType.DIRECT_ANSWER,
                {
                    "directAnswer": response.reasoning.direct_answer,
                    "stance": response.reasoning.stance.value,
                    "confidenceLabel": response.reasoning.confidence_label.value,
                },
            )
            yield event(
                CopilotStreamEventType.EVIDENCE,
                {"evidence": [item.model_dump(mode="json", by_alias=True) for item in response.evidence]},
            )
            yield event(
                CopilotStreamEventType.CONTRADICTION,
                {"factors": [item.model_dump(mode="json", by_alias=True) for item in response.reasoning.contradictory_factors]},
            )
            yield event(
                CopilotStreamEventType.CONDITIONS,
                {
                    "confirmation": [item.model_dump(mode="json", by_alias=True) for item in response.reasoning.confirmation_conditions],
                    "invalidation": [item.model_dump(mode="json", by_alias=True) for item in response.reasoning.invalidation_conditions],
                },
            )
            yield event(
                CopilotStreamEventType.ACTIONS,
                {"actions": [item.model_dump(mode="json", by_alias=True) for item in response.actions]},
            )
            yield event(CopilotStreamEventType.FOLLOW_UPS, {"suggestedFollowUps": response.suggested_follow_ups})
            yield event(
                CopilotStreamEventType.COMPLETE,
                {"response": response.model_dump(mode="json", by_alias=True)},
            )
        except Exception as exc:
            self._record_failure_trace(
                request_id=request_id,
                question=question,
                failure=exc,
                request_started=request_started,
                intent=intent,
                plan=plan,
                time_to_first_stream_event_ms=time_to_first_stream_event_ms,
            )
            logger.warning(
                "institutional_copilot_stream_failed",
                extra={
                    "copilot_event": {
                        "request_id": request_id,
                        "failure_category": type(exc).__name__,
                    }
                },
            )
            yield event(
                CopilotStreamEventType.ERROR,
                {
                    "code": "copilot_pipeline_failed",
                    "message": "The Copilot could not complete this request safely.",
                    "retryable": type(exc).__name__ in {"TimeoutError", "ConnectionError"},
                },
            )

    def _record_failure_trace(
        self,
        *,
        request_id: str,
        question: str,
        failure: Exception,
        request_started: float,
        intent: Any = None,
        plan: Any = None,
        time_to_first_stream_event_ms: float | None = None,
    ) -> None:
        recorder = self.trace_recorder or CopilotTraceRecorder()
        if not recorder.enabled:
            return
        try:
            recorder.record_failure(
                request_id=request_id,
                question=question,
                failure_category=type(failure).__name__,
                total_latency_ms=(perf_counter() - request_started) * 1000,
                timestamp=datetime.now(timezone.utc).isoformat(),
                intent=intent,
                plan=plan,
                time_to_first_stream_event_ms=time_to_first_stream_event_ms,
            )
        except Exception as trace_exc:
            logger.warning(
                "institutional_copilot_failure_trace_failed",
                extra={
                    "copilot_event": {
                        "request_id": request_id,
                        "failure_category": type(trace_exc).__name__,
                    }
                },
            )

    # Alias for callers that prefer a shorter streaming API.
    stream = iter_stream_events

    def _classify_and_plan(
        self,
        *,
        question: str,
        context: dict[str, Any],
        thread_id: str | None,
        session_context: CopilotSessionContextV1 | dict[str, Any] | None,
    ) -> tuple[str, CopilotSessionContextV1 | None, Any, Any]:
        explicit = coerce_session_context(session_context, thread_id=thread_id)
        thread = _thread_id(thread_id or (explicit.thread_id if explicit else None))
        session = self.session_store.resolve(thread, explicit)
        intent = self.classifier.classify(question, screen_context=context, session=session)
        plan = self.planner.build(intent)
        return thread, session, intent, plan

    def _complete(
        self,
        *,
        request_id: str,
        question: str,
        context: dict[str, Any],
        thread_id: str,
        session: CopilotSessionContextV1 | None,
        intent: Any,
        plan: Any,
        request_started: float | None = None,
        time_to_first_stream_event_ms: float | None = None,
    ) -> CopilotResponseV1:
        request_started = request_started if request_started is not None else perf_counter()
        execution = AgentExecutionContext(
            request_id=request_id,
            question=question,
            intent=intent,
            plan=plan,
            client_context=context,
        )
        bundle = self.collector.collect(execution)
        reasoning = self.reasoning_engine.synthesize(bundle, session=session)
        actions = self._build_actions(intent=intent, plan=plan, bundle=bundle, reasoning=reasoning)
        validation = self.validator.validate(
            question=question,
            intent=intent,
            bundle=bundle,
            reasoning=reasoning,
            actions=actions,
        )
        quarantined = False
        if validation.status == CopilotValidationStatus.FAILED:
            original_issues = list(validation.issues)
            reasoning = self.validator.safe_fallback(
                intent=intent,
                bundle=bundle,
                issues=original_issues,
            )
            # Prompt-injection/ambiguous fallbacks do not carry navigation
            # actions inferred from hostile or unresolved text.
            if intent.intent == CopilotIntentType.UNSUPPORTED_OR_AMBIGUOUS:
                actions = []
            second = self.validator.validate(
                question=question,
                intent=intent,
                bundle=bundle,
                reasoning=reasoning,
                actions=actions,
            )
            if second.status == CopilotValidationStatus.FAILED:
                # A synthesis-only defect can be replaced while preserving a
                # valid evidence bundle.  A second failure means the bundle,
                # request, source lineage, or action set itself is unsafe.  In
                # that case fail closed: no invalid evidence or deep link is
                # exposed under a cosmetically relabelled fallback status.
                quarantined = True
                second_issues = list(second.issues)
                bundle = _quarantined_bundle(bundle)
                actions = []
                reasoning = self.validator.safe_fallback(
                    intent=intent,
                    bundle=bundle,
                    issues=[*original_issues, *second_issues],
                )
                third = self.validator.validate(
                    question="Quarantined request omitted.",
                    intent=intent,
                    bundle=bundle,
                    reasoning=reasoning,
                    actions=actions,
                )
                validation = third.model_copy(
                    update={
                        "status": CopilotValidationStatus.FALLBACK,
                        "fallback_used": True,
                        "issues": _dedupe_validation_issues(
                            [*original_issues, *second_issues, *third.issues]
                        ),
                    }
                )
            else:
                validation = second.model_copy(
                    update={
                        "status": CopilotValidationStatus.FALLBACK,
                        "fallback_used": True,
                        "issues": _dedupe_validation_issues([*original_issues, *second.issues]),
                    }
                )
        status = _response_status(intent.intent, bundle.freshness_summary.overall_state, validation)
        sections = _answer_sections(reasoning, bundle.warnings)
        confidence_number = _confidence_number(reasoning.confidence_label, bundle.freshness_summary.overall_state)
        confidence_reasons = [
            f"Intent confidence: {round(intent.confidence * 100)}%.",
            f"Evidence freshness: {bundle.freshness_summary.overall_state.value}.",
        ]
        if reasoning.missing_evidence:
            confidence_reasons.append("Some required evidence is unavailable.")
        follow_ups = _suggested_follow_ups(intent.intent)
        generated_at = datetime.now(timezone.utc).isoformat()
        response = CopilotResponseV1(
            request_id=request_id,
            plan_id=plan.plan_id,
            thread_id=thread_id,
            status=status,
            answer=_render_answer(reasoning),
            answer_sections=sections,
            grounding=CopilotGroundingV1(
                context_used=list(dict.fromkeys(item.dataset for item in bundle.source_summary)),
                source_state=bundle.freshness_summary.overall_state,
                generated_at=generated_at,
                evidence_ids=[item.evidence_id for item in bundle.evidence],
            ),
            suggested_follow_ups=follow_ups,
            confidence=confidence_number,
            answer_confidence=CopilotAnswerConfidenceV1(level=reasoning.confidence_label, reasons=confidence_reasons),
            generated_by="institutional-copilot-v1-deterministic",
            disclaimer="Educational market decision support only; verify current data and apply your own risk constraints.",
            intent=intent,
            plan=plan,
            reasoning=reasoning,
            evidence=bundle.evidence,
            actions=actions,
            warnings=list(dict.fromkeys([*bundle.warnings, *reasoning.missing_evidence])),
            freshness_summary=bundle.freshness_summary,
            validation=validation,
            agent_timings_ms={result.agent.value: result.duration_ms for result in bundle.agent_results},
            retry_count=0,
            failure_categories=list(
                dict.fromkeys(
                    [
                        *(
                            ["validation_quarantine"]
                            if quarantined
                            else []
                        ),
                        *[
                            result.failure_category
                            or (
                                f"{result.agent.value}:{result.status.value}"
                                if result.status.value in {"failed", "unavailable"}
                                else ""
                            )
                            for result in bundle.agent_results
                            if result.failure_category or result.status.value in {"failed", "unavailable"}
                        ],
                    ]
                )
            ),
        )
        logger.info(
            "institutional_copilot_completed",
            extra={
                "copilot_event": {
                    "request_id": request_id,
                    "plan_id": plan.plan_id,
                    "thread_id": thread_id,
                    "intent": intent.intent.value,
                    "status": response.status.value,
                    "validation_status": validation.status.value,
                    "agent_timings_ms": response.agent_timings_ms,
                    "evidence_count": len(bundle.evidence),
                    "retry_count": response.retry_count,
                    "failure_categories": response.failure_categories,
                }
            },
        )
        recorder = self.trace_recorder or CopilotTraceRecorder()
        if recorder.enabled:
            try:
                recorder.record(
                    question=question,
                    bundle=bundle,
                    response=response,
                    total_latency_ms=(perf_counter() - request_started) * 1000,
                    timestamp=generated_at,
                    time_to_first_stream_event_ms=time_to_first_stream_event_ms,
                )
            except Exception as exc:
                # Development tracing must never make the user-facing Copilot
                # fail. Production logs retain only operational identifiers.
                logger.warning(
                    "institutional_copilot_trace_failed",
                    extra={
                        "copilot_event": {
                            "request_id": request_id,
                            "failure_category": type(exc).__name__,
                        }
                    },
                )
        report_id = next((item.raw_engine_reference for item in bundle.source_summary if item.dataset == "ReportDocument"), None)
        self.session_store.save(
            thread_id=thread_id,
            intent=intent,
            reasoning=reasoning,
            evidence_ids=[item.evidence_id for item in bundle.evidence],
            current_screen=str(context.get("screenType") or context.get("screen_type") or "") or None,
            current_route=str(context.get("routeName") or context.get("route") or "") or None,
            latest_report_id=report_id,
            previous_context=session,
            reject_stale=True,
        )
        return response

    @staticmethod
    def _build_actions(*, intent: Any, plan: Any, bundle: Any, reasoning: Any) -> list[CopilotActionV1]:
        destinations = list(plan.deep_link_requirements)
        if not destinations:
            destinations = list(reasoning.recommended_app_destinations or bundle.deep_link_targets)
        actions: list[CopilotActionV1] = []
        stock_destinations = {
            CopilotDestination.STOCK_DETAIL,
            CopilotDestination.STOCK_TECHNICAL,
            CopilotDestination.STOCK_SIGNALS,
            CopilotDestination.STOCK_RISK,
        }
        for destination in destinations[:6]:
            if destination in stock_destinations:
                for symbol in intent.ticker_symbols[:4]:
                    action = build_action(destination, entity=symbol)
                    if action:
                        actions.append(action)
                continue
            entity = None
            if destination == CopilotDestination.SECTOR_DETAIL and intent.sectors:
                entity = intent.sectors[0]
            elif destination == CopilotDestination.THEME_DETAIL and intent.themes:
                entity = intent.themes[0]
            elif destination in {
                CopilotDestination.REPORT_RESEARCH_FOCUS,
                CopilotDestination.REPORT_SCENARIOS,
                CopilotDestination.REPORT_WATCHLIST,
            }:
                entity = "latest"
            elif destination == CopilotDestination.REPORT and intent.intent == CopilotIntentType.REPORT_QUERY:
                entity = "latest"
            action = build_action(destination, entity=entity)
            if action:
                actions.append(action)
        deduped: dict[str, CopilotActionV1] = {}
        for action in actions:
            deduped.setdefault(action.action_id, action)
        return list(deduped.values())[:8]


def _sanitize_message(message: str) -> str:
    value = " ".join(str(message or "").strip().split())
    if not value:
        raise ValueError("Message is required.")
    return value[:4000]


def _quarantined_bundle(bundle: CopilotEvidenceBundleV1) -> CopilotEvidenceBundleV1:
    warning = "Collected evidence was quarantined because response validation did not pass."
    return bundle.model_copy(
        update={
            "question": "[untrusted request omitted]",
            "agent_results": [],
            "evidence": [],
            "supporting_evidence_ids": [],
            "contradictory_evidence_ids": [],
            "unavailable_evidence": [warning],
            "freshness_summary": CopilotFreshnessSummaryV1(
                overall_state=CopilotFreshnessState.UNAVAILABLE,
                unavailable_count=1,
                warnings=[warning],
            ),
            "source_summary": [],
            "deep_link_targets": [],
            "warnings": list(dict.fromkeys([*bundle.warnings, warning])),
        }
    )


def _dedupe_validation_issues(values: Iterable[Any]) -> list[Any]:
    result: list[Any] = []
    seen: set[tuple[str, str, str]] = set()
    for item in values:
        key = (item.check.value, item.severity.value, item.message)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _request_id(value: str | None) -> str:
    if value:
        sanitized = "".join(character for character in str(value) if character.isalnum() or character in "-_:.")[:128]
        if sanitized:
            return sanitized
    return f"copilot-{uuid4().hex[:16]}"


def _thread_id(value: str | None) -> str:
    if value:
        sanitized = "".join(character for character in str(value) if character.isalnum() or character in "-_:.")[:128]
        if sanitized:
            return sanitized
    return f"thread-{uuid4().hex[:16]}"


def institutional_copilot_enabled() -> bool:
    """Runtime feature gate; defaults on to preserve the existing route."""

    return os.getenv("COPILOT_V1_ENABLED", "true").strip().casefold() in {"1", "true", "yes", "on"}


def _response_status(intent: CopilotIntentType, freshness: CopilotFreshnessState, validation: CopilotValidationResultV1) -> CopilotResponseStatus:
    if intent in {CopilotIntentType.EDUCATIONAL_QUERY, CopilotIntentType.APP_NAVIGATION}:
        return CopilotResponseStatus.COMPLETE
    if intent in {CopilotIntentType.UNSUPPORTED_OR_AMBIGUOUS, CopilotIntentType.PORTFOLIO_QUERY}:
        return CopilotResponseStatus.UNAVAILABLE
    if freshness == CopilotFreshnessState.UNAVAILABLE:
        return CopilotResponseStatus.UNAVAILABLE
    if freshness == CopilotFreshnessState.STALE:
        return CopilotResponseStatus.STALE
    if freshness in {CopilotFreshnessState.PARTIAL, CopilotFreshnessState.MIXED}:
        return CopilotResponseStatus.PARTIAL
    if validation.status == CopilotValidationStatus.FALLBACK:
        return CopilotResponseStatus.PARTIAL
    return CopilotResponseStatus.COMPLETE


def _answer_sections(reasoning: Any, warnings: list[str]) -> CopilotAnswerSectionsV1:
    supporting = [factor.statement for factor in reasoning.supporting_factors]
    opposing = [factor.statement for factor in reasoning.contradictory_factors]
    risks = [factor.statement for factor in reasoning.key_risks]
    confirmation = [factor.statement for factor in reasoning.confirmation_conditions]
    invalidation = [factor.statement for factor in reasoning.invalidation_conditions]
    caution = risks[0] if risks else (reasoning.missing_evidence[0] if reasoning.missing_evidence else (warnings[0] if warnings else None))
    return CopilotAnswerSectionsV1(
        direct_answer=reasoning.direct_answer,
        why=supporting[:6],
        evidence_for=supporting[:6],
        evidence_against=opposing[:6],
        main_caution=caution,
        what_would_confirm=confirmation[:6],
        what_would_invalidate=invalidation[:6],
        what_would_change=[*confirmation[:3], *invalidation[:3]],
    )


def _render_answer(reasoning: Any) -> str:
    parts = [reasoning.direct_answer]
    if reasoning.supporting_factors:
        parts.append("Why: " + " ".join(factor.statement for factor in reasoning.supporting_factors[:3]))
    if reasoning.contradictory_factors:
        parts.append("Counter-evidence: " + " ".join(factor.statement for factor in reasoning.contradictory_factors[:2]))
    if reasoning.missing_evidence:
        parts.append("Missing evidence: " + " ".join(reasoning.missing_evidence[:3]))
    return "\n\n".join(parts)


def _confidence_number(label: CopilotConfidenceLabel, freshness: CopilotFreshnessState) -> int:
    base = {
        CopilotConfidenceLabel.HIGH: 84,
        CopilotConfidenceLabel.MODERATE: 68,
        CopilotConfidenceLabel.LIMITED: 42,
    }[CopilotConfidenceLabel(label)]
    if freshness in {CopilotFreshnessState.STALE, CopilotFreshnessState.TEST}:
        base = min(base, 45)
    elif freshness in {CopilotFreshnessState.PARTIAL, CopilotFreshnessState.MIXED}:
        base = min(base, 58)
    elif freshness == CopilotFreshnessState.UNAVAILABLE:
        base = min(base, 25)
    return base


def _suggested_follow_ups(intent: CopilotIntentType) -> list[str]:
    mapping = {
        CopilotIntentType.NEWS_QUERY: [
            "Did price confirm that event?",
            "Open the related market or security screen.",
        ],
        CopilotIntentType.SESSION_NARRATIVE: [
            "Which session evidence was contradictory?",
            "What session evidence is missing?",
        ],
        CopilotIntentType.MARKET_STATE: ["Does breadth confirm that?", "Which sectors are leading?"],
        CopilotIntentType.MARKET_EXPLANATION: ["What would invalidate that thesis?", "Which sectors are leading?"],
        CopilotIntentType.STOCK_ANALYSIS: ["What confirms it?", "What would invalidate it?", "Show me."],
        CopilotIntentType.STOCK_DECISION_SUPPORT: ["Challenge the opposing case.", "What confirms it?", "Show me."],
        CopilotIntentType.REPORT_QUERY: ["What would invalidate the report thesis?", "Open Research Focus."],
        CopilotIntentType.RESEARCH_QUERY: ["What is the counter-thesis?", "What would confirm it?"],
    }
    return mapping.get(CopilotIntentType(intent), [])


_ORCHESTRATOR: InstitutionalCopilotOrchestrator | None = None


def get_institutional_copilot_orchestrator() -> InstitutionalCopilotOrchestrator:
    global _ORCHESTRATOR
    if _ORCHESTRATOR is None:
        _ORCHESTRATOR = InstitutionalCopilotOrchestrator()
    return _ORCHESTRATOR


def answer_institutional_copilot(**kwargs: Any) -> CopilotResponseV1:
    return get_institutional_copilot_orchestrator().answer(**kwargs)


def stream_institutional_copilot(**kwargs: Any) -> Iterable[CopilotStreamEventV1]:
    return get_institutional_copilot_orchestrator().iter_stream_events(**kwargs)
