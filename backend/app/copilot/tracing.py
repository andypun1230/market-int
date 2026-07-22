from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from pydantic import Field

from app.copilot.contracts import (
    CopilotContractModel,
    CopilotEvidenceBundleV1,
    CopilotFreshnessState,
    CopilotResponseV1,
)
from app.copilot.policy import SECRET_PATTERNS


TRACE_SCHEMA_VERSION = "stage7-copilot-development-trace-v1"
TRACE_ENV_FLAG = "COPILOT_DEV_TRACES_ENABLED"
TRACE_ENV_DIRECTORY = "COPILOT_DEV_TRACE_DIR"
_SAFE_REQUEST_ID = re.compile(r"[^A-Za-z0-9_.:-]+")
_SENSITIVE_KEY = re.compile(
    r"(?:api[_-]?key|authorization|bearer|cookie|credential|password|secret|session[_-]?token|token|account[_-]?id|customer[_-]?id|member[_-]?id|user[_-]?id)",
    re.IGNORECASE,
)
_EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE_PATTERN = re.compile(
    r"(?<!\w)(?!\d{4}-\d{2}-\d{2}(?:T|\b))\+?\d[\d ()-]{7,}\d(?!\w)"
)
_PRIVATE_IDENTIFIER_PATTERN = re.compile(
    r"\b(?:account|customer|member|user)\s*(?:id|number|#)\s*[:=]?\s*[A-Za-z0-9_-]{4,}\b",
    re.IGNORECASE,
)


class CopilotDevelopmentTraceV1(CopilotContractModel):
    schema_version: str = TRACE_SCHEMA_VERSION
    request_id: str
    timestamp: str
    user_query: str
    normalized_intent: str
    planner_version: str
    selected_agents: list[str] = Field(default_factory=list)
    unused_agents: list[str] = Field(default_factory=list)
    snapshot_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    prompt_versions: dict[str, str] = Field(default_factory=dict)
    model_version: str
    model_calls: int = Field(default=0, ge=0)
    rules_triggered: list[str] = Field(default_factory=list)
    validation_checks_run: list[str] = Field(default_factory=list)
    confidence_adjustments: list[str] = Field(default_factory=list)
    freshness_caps: list[str] = Field(default_factory=list)
    fallbacks: list[str] = Field(default_factory=list)
    deep_links: list[dict[str, Any]] = Field(default_factory=list)
    total_latency_ms: float = Field(ge=0)
    time_to_first_stream_event_ms: float | None = Field(default=None, ge=0)
    per_agent_latency_ms: dict[str, float] = Field(default_factory=dict)
    token_usage: dict[str, int] | None = None
    estimated_cost: dict[str, Any] | None = None
    cache_metrics: dict[str, Any] = Field(default_factory=dict)
    validation_warnings: list[str] = Field(default_factory=list)
    final_status: str
    failure_category: str | None = None
    agent_results: list[dict[str, Any]] = Field(default_factory=list)
    final_response: dict[str, Any]


class CopilotTraceRecorder:
    """Opt-in, development-only trace persistence.

    Production structured logs deliberately omit the raw query. A full trace
    is written only when a recorder is explicitly enabled or a trace directory
    is configured. Sensitive keys and secret-like text are redacted before the
    trace reaches disk.
    """

    def __init__(
        self,
        directory: str | Path | None = None,
        *,
        enabled: bool | None = None,
    ) -> None:
        configured_directory = directory or os.getenv(TRACE_ENV_DIRECTORY)
        self.directory = Path(configured_directory) if configured_directory else _default_trace_directory()
        if enabled is None:
            enabled = bool(configured_directory) or _truthy(os.getenv(TRACE_ENV_FLAG, "false"))
        self.enabled = bool(enabled)

    def record(
        self,
        *,
        question: str,
        bundle: CopilotEvidenceBundleV1,
        response: CopilotResponseV1,
        total_latency_ms: float,
        timestamp: str,
        time_to_first_stream_event_ms: float | None = None,
    ) -> Path | None:
        if not self.enabled:
            return None
        trace = build_development_trace(
            question=question,
            bundle=bundle,
            response=response,
            total_latency_ms=total_latency_ms,
            timestamp=timestamp,
            time_to_first_stream_event_ms=time_to_first_stream_event_ms,
        )
        return self._write(trace)

    def record_failure(
        self,
        *,
        request_id: str,
        question: str,
        failure_category: str,
        total_latency_ms: float,
        timestamp: str,
        intent: Any = None,
        plan: Any = None,
        time_to_first_stream_event_ms: float | None = None,
    ) -> Path | None:
        """Persist an inspectable trace even when the pipeline raises early."""

        if not self.enabled:
            return None
        selected_agents = [
            step.agent.value
            for step in list(getattr(plan, "ordered_steps", []) or [])
        ]
        normalized_intent = getattr(getattr(intent, "intent", None), "value", "unavailable")
        trace = CopilotDevelopmentTraceV1(
            request_id=request_id,
            timestamp=timestamp,
            user_query=redact_trace_text(question),
            normalized_intent=normalized_intent,
            planner_version=str(getattr(plan, "schema_version", "unavailable")),
            selected_agents=selected_agents,
            unused_agents=[],
            snapshot_ids=[],
            evidence_ids=[],
            prompt_versions={agent: "not-applicable-deterministic-v1" for agent in selected_agents},
            model_version="institutional-copilot-v1-deterministic",
            model_calls=0,
            rules_triggered=[],
            validation_checks_run=[],
            confidence_adjustments=[],
            freshness_caps=[],
            fallbacks=[f"pipeline_exception:{failure_category}"],
            deep_links=[],
            total_latency_ms=max(0, round(float(total_latency_ms), 3)),
            time_to_first_stream_event_ms=time_to_first_stream_event_ms,
            per_agent_latency_ms={},
            token_usage=None,
            estimated_cost=None,
            cache_metrics={
                "cacheTelemetryAvailable": False,
                "cacheHitRate": None,
                "sourceStateCounts": {},
            },
            validation_warnings=["The pipeline failed before a validated response was available."],
            final_status="failed",
            failure_category=failure_category,
            agent_results=[],
            final_response={"status": "failed", "failureCategory": failure_category},
        )
        return self._write(trace)

    def _write(self, trace: CopilotDevelopmentTraceV1) -> Path:
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.directory / f"{safe_request_id(trace.request_id)}.json"
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(trace.model_dump(mode="json", by_alias=True), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
        return path


def build_development_trace(
    *,
    question: str,
    bundle: CopilotEvidenceBundleV1,
    response: CopilotResponseV1,
    total_latency_ms: float,
    timestamp: str,
    time_to_first_stream_event_ms: float | None = None,
) -> CopilotDevelopmentTraceV1:
    selected_agents = [step.agent.value for step in response.plan.ordered_steps]
    unused_agents = [
        agent.value
        for agent in response.intent.optional_agents
        if agent.value not in selected_agents
    ]
    snapshots = [
        source.raw_engine_reference or source.source_id
        for source in bundle.source_summary
        if source.raw_engine_reference or source.source_id
    ]
    issue_checks = [issue.check.value for issue in response.validation.issues]
    # A check that ran is not necessarily a rule that triggered.  Keep both
    # dimensions explicit so a clean response does not falsely report every
    # safety rule as activated.
    rules = list(dict.fromkeys(issue_checks))
    checks_run = [check.value for check in response.validation.checks_run]
    constrained_states = {
        CopilotFreshnessState.STALE,
        CopilotFreshnessState.TEST,
        CopilotFreshnessState.PARTIAL,
        CopilotFreshnessState.MIXED,
        CopilotFreshnessState.UNAVAILABLE,
    }
    freshness_caps: list[str] = []
    confidence_adjustments: list[str] = []
    if response.freshness_summary.overall_state in constrained_states:
        state = response.freshness_summary.overall_state.value
        freshness_caps.append(f"{state}:non_actionable")
        confidence_adjustments.append(
            f"freshness:{state}->confidence:{response.reasoning.confidence_label.value}"
        )
    fallbacks = list(response.failure_categories)
    if response.validation.fallback_used:
        fallbacks.append("response_validation_fallback")
    source_state_counts: dict[str, int] = {}
    for result in bundle.agent_results:
        state = result.freshness.state.value
        source_state_counts[state] = source_state_counts.get(state, 0) + 1
    cache_metrics = {
        # Freshness labels do not tell us whether an internal cache lookup hit.
        # Leave the cache rate unknown until the source adapters expose actual
        # cache telemetry.
        "cacheTelemetryAvailable": False,
        "cacheHitRate": None,
        "sourceStateCounts": source_state_counts,
        "duplicateSnapshotReferences": len(snapshots) - len(set(snapshots)),
        "duplicateEvidenceReferences": len(response.evidence) - len({item.evidence_id for item in response.evidence}),
    }
    private_terms = _private_trace_terms(bundle)
    return CopilotDevelopmentTraceV1(
        request_id=response.request_id,
        timestamp=timestamp,
        user_query=redact_trace_text(question, private_terms=private_terms),
        normalized_intent=response.intent.intent.value,
        planner_version=response.plan.schema_version,
        selected_agents=selected_agents,
        unused_agents=unused_agents,
        snapshot_ids=list(dict.fromkeys(snapshots)),
        evidence_ids=[item.evidence_id for item in response.evidence],
        prompt_versions={agent: "not-applicable-deterministic-v1" for agent in selected_agents},
        model_version=response.generated_by,
        model_calls=0,
        rules_triggered=rules,
        validation_checks_run=checks_run,
        confidence_adjustments=confidence_adjustments,
        freshness_caps=freshness_caps,
        fallbacks=list(dict.fromkeys(fallbacks)),
        deep_links=[
            sanitize_trace_value(action.model_dump(mode="json", by_alias=True), private_terms=private_terms)
            for action in response.actions
        ],
        total_latency_ms=max(0, round(float(total_latency_ms), 3)),
        time_to_first_stream_event_ms=time_to_first_stream_event_ms,
        per_agent_latency_ms=response.agent_timings_ms,
        token_usage=None,
        estimated_cost=None,
        cache_metrics=cache_metrics,
        validation_warnings=[issue.message for issue in response.validation.issues],
        final_status=response.status.value,
        agent_results=[
            sanitize_trace_value(result.model_dump(mode="json", by_alias=True), private_terms=private_terms)
            for result in bundle.agent_results
        ],
        final_response=sanitize_trace_value(
            response.model_dump(mode="json", by_alias=True),
            private_terms=private_terms,
        ),
    )


def load_development_trace(
    request_id: str,
    *,
    directory: str | Path | None = None,
) -> CopilotDevelopmentTraceV1:
    root = Path(directory) if directory else Path(os.getenv(TRACE_ENV_DIRECTORY) or _default_trace_directory())
    path = root / f"{safe_request_id(request_id)}.json"
    return CopilotDevelopmentTraceV1.model_validate_json(path.read_text(encoding="utf-8"))


def safe_request_id(value: str) -> str:
    sanitized = _SAFE_REQUEST_ID.sub("-", str(value or "")).strip("-.")[:128]
    if not sanitized:
        raise ValueError("A valid request ID is required.")
    return sanitized


def redact_trace_text(value: str, *, private_terms: set[str] | None = None) -> str:
    text = str(value or "")[:4000]
    for pattern in SECRET_PATTERNS:
        text = re.sub(pattern, "[REDACTED]", text, flags=re.IGNORECASE)
    text = _EMAIL_PATTERN.sub("[REDACTED_EMAIL]", text)
    text = _PHONE_PATTERN.sub("[REDACTED_PHONE]", text)
    text = _PRIVATE_IDENTIFIER_PATTERN.sub("[REDACTED_IDENTIFIER]", text)
    for term in sorted(private_terms or set(), key=len, reverse=True):
        if not term:
            continue
        digest = hashlib.sha256(term.casefold().encode("utf-8")).hexdigest()[:8]
        text = re.sub(
            rf"(?<![A-Za-z0-9]){re.escape(term)}(?![A-Za-z0-9])",
            f"[PRIVATE:{digest}]",
            text,
            flags=re.IGNORECASE,
        )
    return text


def sanitize_trace_value(
    value: Any,
    *,
    depth: int = 0,
    private_terms: set[str] | None = None,
) -> Any:
    if depth > 12:
        return "[TRUNCATED]"
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if _SENSITIVE_KEY.search(str(key)):
                result[str(key)] = "[REDACTED]"
            else:
                result[str(key)] = sanitize_trace_value(
                    item,
                    depth=depth + 1,
                    private_terms=private_terms,
                )
        return result
    if isinstance(value, (list, tuple)):
        return [
            sanitize_trace_value(item, depth=depth + 1, private_terms=private_terms)
            for item in value[:500]
        ]
    if isinstance(value, str):
        return redact_trace_text(value, private_terms=private_terms)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return redact_trace_text(str(value), private_terms=private_terms)


def _private_trace_terms(bundle: CopilotEvidenceBundleV1) -> set[str]:
    return {
        item.entity.strip()
        for item in bundle.evidence
        if item.entity.strip()
        and (
            item.category.value == "watchlist"
            or "saved membership" in item.metric.casefold()
            or item.source.provider == "client_local_membership"
        )
    }


def _default_trace_directory() -> Path:
    return Path(__file__).resolve().parents[3] / "artifacts" / "stage7" / "traces"


def _truthy(value: str) -> bool:
    return str(value or "").strip().casefold() in {"1", "true", "yes", "on"}


def _summary(trace: CopilotDevelopmentTraceV1) -> dict[str, Any]:
    return {
        "requestId": trace.request_id,
        "timestamp": trace.timestamp,
        "intent": trace.normalized_intent,
        "selectedAgents": trace.selected_agents,
        "snapshotIds": trace.snapshot_ids,
        "evidenceCount": len(trace.evidence_ids),
        "totalLatencyMs": trace.total_latency_ms,
        "perAgentLatencyMs": trace.per_agent_latency_ms,
        "fallbacks": trace.fallbacks,
        "validationWarnings": trace.validation_warnings,
        "deepLinks": trace.deep_links,
        "finalStatus": trace.final_status,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect an opt-in Stage 7 Copilot development trace.")
    parser.add_argument("request_id", help="Request ID recorded by the Copilot trace recorder.")
    parser.add_argument("--trace-dir", help="Trace directory; defaults to COPILOT_DEV_TRACE_DIR or artifacts/stage7/traces.")
    parser.add_argument("--full", action="store_true", help="Print the full redacted trace instead of a compact summary.")
    args = parser.parse_args(argv)
    trace = load_development_trace(args.request_id, directory=args.trace_dir)
    payload = trace.model_dump(mode="json", by_alias=True) if args.full else _summary(trace)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
