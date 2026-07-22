from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import fmean
from typing import Iterable

from app.copilot.evaluation.contracts import (
    EvaluationCandidate,
    EvaluationSuite,
    EvaluationSummary,
    GoldenEvaluationCase,
    IssueSeverity,
    ReleaseResult,
)
from app.copilot.evaluation.evaluator import aggregate_component_scores, evaluate_case
from app.copilot.evaluation.loader import cases_for_suite, load_fixtures
from app.copilot.evaluation.routing import apply_deterministic_routing


def run_suite(
    suite: EvaluationSuite | str = EvaluationSuite.FULL,
    *,
    fixture_root: str | Path | None = None,
    candidate_overrides: dict[str, EvaluationCandidate] | None = None,
    use_runtime_routing: bool = True,
) -> EvaluationSummary:
    """Run a reusable Stage 7 suite and return a typed machine result."""

    selected_suite = EvaluationSuite(suite)
    all_cases = load_fixtures(fixture_root)
    cases = cases_for_suite(all_cases, selected_suite)
    overrides = candidate_overrides or {}
    results = []
    for case in cases:
        candidate = overrides.get(case.fixture_id, case.reference_output)
        if use_runtime_routing and "runtime-routing" in case.tags:
            candidate = apply_deterministic_routing(case, candidate)
        results.append(evaluate_case(case, candidate))

    release_blockers = [
        issue
        for result in results
        for issue in result.issues
        if issue.release_blocking
    ]
    failures = [result for result in results if not result.passed]
    warnings = [
        (result.fixture_id, issue)
        for result in results
        for issue in result.issues
        if issue.severity == IssueSeverity.WARNING
    ]
    # This runner evaluates a checked-in answer against the same checked-in
    # fixture that supplied it (plus classifier/planner routing for tagged
    # cases).  It is useful as a corpus/contract regression check, but it does
    # not execute the production agent pipeline and must never grant release.
    release_result = ReleaseResult.FAIL if failures or release_blockers else ReleaseResult.NON_RELEASE

    routing_cases = [result for case, result in zip(cases, results) if EvaluationSuite.ROUTING in case.suites]
    performance_cases = [result for case, result in zip(cases, results) if EvaluationSuite.PERFORMANCE in case.suites]
    return EvaluationSummary(
        evaluation_mode=(
            "offline-frozen-with-deterministic-routing"
            if use_runtime_routing
            else "offline-frozen-reference-only"
        ),
        suite=selected_suite,
        generated_at=datetime.now(timezone.utc).isoformat(),
        result=release_result,
        fixture_count=len(results),
        passed_count=len(results) - len(failures),
        failed_count=len(failures),
        release_blocker_count=len(release_blockers),
        category_counts=dict(sorted(Counter(case.category.value for case in cases).items())),
        suite_counts={
            item.value: sum(item in case.suites for case in all_cases)
            for item in EvaluationSuite
        },
        component_scores=aggregate_component_scores(results),
        routing_metrics=_routing_metrics(routing_cases),
        performance_metrics=_performance_metrics(performance_cases),
        case_results=results,
        failures=[
            {
                "fixture_id": result.fixture_id,
                "issues": [
                    issue.model_dump(mode="json")
                    for issue in result.issues
                    if issue.severity == IssueSeverity.ERROR
                ],
            }
            for result in failures
        ],
        warnings=[
            {"fixture_id": fixture_id, "issue": issue.model_dump(mode="json")}
            for fixture_id, issue in warnings
        ],
        release_bearing=False,
        limitations=[
            (
                "Reference mode compares checked-in candidates with their own frozen expectations; "
                "it is a non-release-bearing corpus and validator contract check."
            ),
            (
                "Deterministic routing mode executes only the intent classifier and planner adapter; "
                "it does not execute specialist agents, collection, synthesis, or response validation."
                if use_runtime_routing
                else "Reference-only mode does not execute any production Copilot pipeline boundary."
            ),
        ],
    )


def write_machine_result(summary: EvaluationSummary, output: str | Path) -> Path:
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(summary.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return target


def render_text_summary(summary: EvaluationSummary) -> str:
    return "\n".join((
        f"Stage 7 {summary.suite.value} evaluation: {summary.result.value}",
        f"Release-bearing: {'yes' if summary.release_bearing else 'no'}",
        f"Cases: {summary.passed_count}/{summary.fixture_count} passed; release blockers: {summary.release_blocker_count}",
        "Components: " + ", ".join(f"{name}={score:.3f}" for name, score in summary.component_scores.items()),
        "Routing: " + ", ".join(f"{name}={value:.3f}" for name, value in summary.routing_metrics.items()),
        "Performance: " + ", ".join(f"{name}={value:.3f}" for name, value in summary.performance_metrics.items()),
    ))


def _routing_metrics(results) -> dict[str, float]:
    if not results:
        return {
            "intent_accuracy": 0.0,
            "required_agent_recall": 0.0,
            "unnecessary_agent_rate": 0.0,
            "invalid_route_rate": 0.0,
            "average_agent_count": 0.0,
            "fallback_rate": 0.0,
        }
    total_agents = sum(item.metrics["agent_count"] for item in results)
    return {
        "intent_accuracy": round(fmean(item.metrics["intent_match"] for item in results), 6),
        "required_agent_recall": round(fmean(item.metrics["required_agent_recall"] for item in results), 6),
        "unnecessary_agent_rate": round(
            sum(item.metrics["unnecessary_agent_count"] for item in results) / max(1.0, total_agents),
            6,
        ),
        "invalid_route_rate": round(
            sum(any(issue.code in {"deep_link_mismatch", "unregistered_deep_link"} for issue in item.issues) for item in results)
            / len(results),
            6,
        ),
        "average_agent_count": round(total_agents / len(results), 6),
        "fallback_rate": round(
            sum(any(issue.code in {"wrong_intent", "missing_required_agent"} for issue in item.issues) for item in results)
            / len(results),
            6,
        ),
    }


def _performance_metrics(results) -> dict[str, float]:
    if not results:
        return {
            "mean_latency_ms": 0.0,
            "p50_latency_ms": 0.0,
            "p95_latency_ms": 0.0,
            "max_latency_ms": 0.0,
            "mean_model_calls": 0.0,
        }
    latencies = [item.metrics["latency_ms"] for item in results]
    return {
        "mean_latency_ms": round(fmean(latencies), 6),
        "p50_latency_ms": round(_percentile(latencies, 0.50), 6),
        "p95_latency_ms": round(_percentile(latencies, 0.95), 6),
        "max_latency_ms": round(max(latencies), 6),
        "mean_model_calls": round(fmean(item.metrics["model_calls"] for item in results), 6),
    }


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight
