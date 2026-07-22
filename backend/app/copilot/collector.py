from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, wait
from typing import Iterable

from app.copilot.agents import AgentExecutionContext, CopilotAgentRegistry
from app.copilot.contracts import (
    AgentResultV1,
    CopilotAgentName,
    CopilotAgentStatus,
    CopilotEvidenceBundleV1,
    CopilotEvidenceV1,
    CopilotFreshnessState,
    CopilotFreshnessSummaryV1,
    CopilotFreshnessV1,
    CopilotPlanStepV1,
)
from app.copilot.sources import aggregate_source_states


class CopilotEvidenceCollector:
    """Execute the bounded plan and merge typed results deterministically."""

    def __init__(self, registry: CopilotAgentRegistry | None = None, *, maximum_workers: int = 4) -> None:
        self.registry = registry or CopilotAgentRegistry()
        self.maximum_workers = max(1, min(8, maximum_workers))

    def collect(self, context: AgentExecutionContext) -> CopilotEvidenceBundleV1:
        steps = list(context.plan.ordered_steps)
        results: list[AgentResultV1] = []
        if steps:
            worker_count = min(self.maximum_workers, len(steps))
            executor = ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="copilot-agent")
            try:
                futures = {executor.submit(self.registry.execute, step.agent, context): step for step in steps}
                plan_timeout_ms = min(
                    context.plan.maximum_latency_ms,
                    max(step.timeout_ms for step in steps),
                )
                done, pending = wait(futures, timeout=plan_timeout_ms / 1000)
                completed_by_agent: dict[CopilotAgentName, AgentResultV1] = {}
                for future in done:
                    step = futures[future]
                    try:
                        completed_by_agent[CopilotAgentName(step.agent)] = future.result()
                    except Exception as exc:
                        completed_by_agent[CopilotAgentName(step.agent)] = _failed_result(
                            step.agent,
                            message=f"{CopilotAgentName(step.agent).value} failed safely: {type(exc).__name__}.",
                            failure_category=type(exc).__name__,
                        )
                for future in pending:
                    step = futures[future]
                    future.cancel()
                    completed_by_agent[CopilotAgentName(step.agent)] = _failed_result(
                        step.agent,
                        message=f"{CopilotAgentName(step.agent).value} exceeded the bounded plan latency.",
                        failure_category="timeout",
                    )
                results = [completed_by_agent[CopilotAgentName(step.agent)] for step in steps]
            finally:
                # Context-manager shutdown waits for already-running calls and
                # would silently defeat the plan latency.  Durable adapters
                # receive no cancellation-unsafe mutation authority, so the
                # request may return its partial result without waiting.
                executor.shutdown(wait=False, cancel_futures=True)

        evidence = _dedupe_evidence(item for result in results for item in result.evidence)
        source_summary = _dedupe_sources(
            [
                *(item for result in results for item in result.source_references),
                *(item.source for item in evidence),
            ]
        )
        missing = [item for result in results for item in result.missing_data]
        warnings = [item for result in results for item in [*result.warnings, *result.freshness.warnings]]
        by_category = {item.category for item in evidence}
        confirmed_empty_watchlist = any(
            result.agent == CopilotAgentName.WATCHLIST
            and result.metrics.get("membership_state") == "empty"
            for result in results
        )
        for requirement in context.plan.evidence_requirements:
            if requirement.required and requirement.minimum_items > 0:
                if requirement.category.value == "watchlist" and confirmed_empty_watchlist:
                    # A typed, confirmed empty membership is a complete result;
                    # it naturally has no per-symbol evidence rows.
                    continue
                count = sum(item.category == requirement.category for item in evidence)
                if count < requirement.minimum_items:
                    missing.append(f"Required {requirement.category.value} evidence is unavailable.")
        freshness_summary = _freshness_summary(results)
        if freshness_summary.overall_state in {
            CopilotFreshnessState.STALE,
            CopilotFreshnessState.TEST,
            CopilotFreshnessState.PARTIAL,
            CopilotFreshnessState.MIXED,
            CopilotFreshnessState.UNAVAILABLE,
        }:
            warnings.append(f"Evidence freshness is {freshness_summary.overall_state.value}; conclusions are constrained accordingly.")
        contradictory_ids = [
            item.evidence_id
            for item in evidence
            if item.contradicts_claim_ids or item.interpretation_class == "contradiction"
        ]
        targets = list(dict.fromkeys(target for result in results for target in result.deep_link_targets))
        return CopilotEvidenceBundleV1(
            request_id=context.request_id,
            question=context.question,
            intent=context.intent,
            plan=context.plan,
            agent_results=results,
            evidence=evidence,
            supporting_evidence_ids=[item.evidence_id for item in evidence if item.evidence_id not in contradictory_ids],
            contradictory_evidence_ids=contradictory_ids,
            unavailable_evidence=list(dict.fromkeys(missing)),
            freshness_summary=freshness_summary,
            source_summary=source_summary,
            deep_link_targets=targets,
            warnings=list(dict.fromkeys(value for value in warnings if value)),
        )


def _failed_result(agent: CopilotAgentName | str, *, message: str, failure_category: str) -> AgentResultV1:
    return AgentResultV1(
        agent=CopilotAgentName(agent),
        status=CopilotAgentStatus.FAILED,
        freshness=CopilotFreshnessV1(
            state=CopilotFreshnessState.UNAVAILABLE,
            completeness=0,
            provider="unavailable",
            warnings=[message],
        ),
        warnings=[message],
        missing_data=[message],
        failure_category=failure_category,
    )


def _dedupe_evidence(values: Iterable[CopilotEvidenceV1]) -> list[CopilotEvidenceV1]:
    result: dict[str, CopilotEvidenceV1] = {}
    for value in values:
        result.setdefault(value.evidence_id, value)
    return list(result.values())


def _dedupe_sources(values: Iterable) -> list:
    result = {}
    for value in values:
        result.setdefault(value.source_id, value)
    return list(result.values())


def _freshness_summary(results: list[AgentResultV1]) -> CopilotFreshnessSummaryV1:
    states = [result.freshness.state for result in results]
    overall = CopilotFreshnessState(aggregate_source_states(states)) if states else CopilotFreshnessState.UNAVAILABLE
    market_dates = sorted({result.freshness.market_date for result in results if result.freshness.market_date})
    generated = sorted({result.freshness.generated_at for result in results if result.freshness.generated_at})
    warnings = list(dict.fromkeys(warning for result in results for warning in result.freshness.warnings))
    current_states = {CopilotFreshnessState.LIVE, CopilotFreshnessState.DELAYED, CopilotFreshnessState.CACHED}
    return CopilotFreshnessSummaryV1(
        overall_state=overall,
        market_dates=market_dates,
        generated_timestamps=generated,
        current_count=sum(state in current_states for state in states),
        stale_count=sum(state == CopilotFreshnessState.STALE for state in states),
        partial_count=sum(state in {CopilotFreshnessState.PARTIAL, CopilotFreshnessState.MIXED} for state in states),
        unavailable_count=sum(state == CopilotFreshnessState.UNAVAILABLE for state in states),
        test_count=sum(state == CopilotFreshnessState.TEST for state in states),
        warnings=warnings,
    )
