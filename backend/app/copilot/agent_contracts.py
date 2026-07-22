from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.copilot.contracts import (
    AgentResultV1,
    CopilotAgentName,
    CopilotAgentStatus,
    CopilotConfidenceLabel,
    CopilotFreshnessState,
    CopilotInterpretationClass,
)


AGENT_MANIFEST_PATH = Path(__file__).with_name("agent_manifest.json")


class AgentFreshnessContractV1(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    allowed_states: list[CopilotFreshnessState] = Field(alias="allowedStates")
    maximum_age_source: str = Field(alias="maximumAgeSource")
    stale_actionability: str = Field(alias="staleActionability")


class AgentAvailabilityContractV1(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    missing_input: str = Field(alias="missingInput")
    partial_input: str = Field(alias="partialInput")
    exception: str


class CopilotAgentContractV1(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    agent: CopilotAgentName = Field(alias="id")
    contract_version: str = Field(alias="contractVersion")
    accepted_input_schema: str = Field(alias="acceptedInputSchema")
    output_schema: str = Field(alias="outputSchema")
    allowed_evidence_categories: list[str] = Field(alias="allowedEvidenceCategories")
    allowed_destinations: list[str] = Field(alias="allowedDestinations")
    deterministic: bool
    model_dependent: bool = Field(alias="modelDependent")
    required_freshness: AgentFreshnessContractV1 = Field(alias="requiredFreshness")
    availability_behavior: AgentAvailabilityContractV1 = Field(alias="availabilityBehavior")
    prompt_version: str | None = Field(alias="promptVersion")
    model_version: str | None = Field(alias="modelVersion")


class AgentContractIssueV1(BaseModel):
    code: str
    severity: Literal["warning", "error"]
    message: str


class AgentContractValidationV1(BaseModel):
    schema_version: str = "stage7-agent-contract-validation-v1"
    agent: CopilotAgentName
    contract_version: str
    status: Literal["passed", "failed"]
    issues: list[AgentContractIssueV1] = Field(default_factory=list)


@lru_cache(maxsize=1)
def load_agent_contracts(path: str | Path | None = None) -> dict[CopilotAgentName, CopilotAgentContractV1]:
    selected = Path(path) if path else AGENT_MANIFEST_PATH
    payload = json.loads(selected.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "stage7-agent-manifest-v1":
        raise ValueError("Unsupported Stage 7 agent manifest schema.")
    contracts = [CopilotAgentContractV1.model_validate(item) for item in payload.get("agents", [])]
    by_agent = {item.agent: item for item in contracts}
    if len(by_agent) != len(contracts) or set(by_agent) != set(CopilotAgentName):
        raise ValueError("Stage 7 agent manifest must cover every runtime agent exactly once.")
    return by_agent


def validate_agent_result(
    result: AgentResultV1,
    *,
    contract: CopilotAgentContractV1 | None = None,
) -> AgentContractValidationV1:
    selected = contract or load_agent_contracts()[result.agent]
    issues: list[AgentContractIssueV1] = []

    def add(code: str, severity: Literal["warning", "error"], message: str) -> None:
        issues.append(AgentContractIssueV1(code=code, severity=severity, message=message))

    if result.agent != selected.agent:
        add("agent_mismatch", "error", "The output agent does not match the selected validation contract.")
    if result.schema_version != selected.contract_version:
        add("schema_version", "error", "The agent output schema version does not match its manifest contract.")
    if result.freshness.state not in selected.required_freshness.allowed_states:
        add("freshness_state", "error", "The output freshness state is not allowed by the agent contract.")

    allowed_categories = set(selected.allowed_evidence_categories)
    unexpected_categories = sorted({item.category.value for item in result.evidence} - allowed_categories)
    if unexpected_categories:
        add("evidence_category", "error", "The agent emitted evidence outside its allowed categories.")
    allowed_destinations = set(selected.allowed_destinations)
    unexpected_destinations = sorted({item.value for item in result.deep_link_targets} - allowed_destinations)
    if unexpected_destinations:
        add("destination", "error", "The agent emitted a deep link outside its manifest contract.")

    evidence_ids = [item.evidence_id for item in result.evidence]
    if len(evidence_ids) != len(set(evidence_ids)):
        add("evidence_id", "error", "Agent evidence IDs must be unique.")
    known_evidence = set(evidence_ids)
    for level in result.levels:
        if level.evidence_id not in known_evidence:
            add("level_reference", "error", "An agent level references evidence outside the agent result.")
    confirmation_ids = {
        item.evidence_id
        for item in result.levels
        if any(term in item.label.casefold() for term in ("confirm", "breakout", "resistance"))
    }
    invalidation_ids = {
        item.evidence_id
        for item in result.levels
        if any(term in item.label.casefold() for term in ("invalid", "risk", "stop", "support"))
    }
    if confirmation_ids.intersection(invalidation_ids):
        add("condition_collision", "error", "One evidence item cannot be both confirmation and invalidation.")

    constrained = result.freshness.state in {
        CopilotFreshnessState.STALE,
        CopilotFreshnessState.TEST,
        CopilotFreshnessState.PARTIAL,
        CopilotFreshnessState.MIXED,
        CopilotFreshnessState.UNAVAILABLE,
    }
    if constrained and any(item.confidence == CopilotConfidenceLabel.HIGH for item in result.evidence):
        add("confidence_cap", "error", "Constrained evidence cannot retain high confidence.")
    if result.status == CopilotAgentStatus.COMPLETE and constrained:
        add("status_freshness", "error", "A complete agent status cannot conceal constrained freshness.")
    if result.status in {CopilotAgentStatus.UNAVAILABLE, CopilotAgentStatus.FAILED}:
        if result.evidence:
            add("unavailable_evidence", "error", "Unavailable or failed agents cannot expose factual evidence as complete output.")
        educational_definition = (
            selected.agent == CopilotAgentName.EDUCATIONAL
            and bool(result.conclusions)
            and result.freshness.provider == "copilot_glossary"
        )
        if not educational_definition and not (result.missing_data or result.warnings or result.freshness.warnings):
            add("unavailable_disclosure", "error", "Unavailable or failed agents must disclose the limitation.")
    if result.status == CopilotAgentStatus.FAILED and not result.failure_category:
        add("failure_category", "error", "Failed agent output must include a failure category.")

    source_ids = [item.source_id for item in result.source_references]
    if len(source_ids) != len(set(source_ids)):
        add("source_id", "error", "Agent source references must be unique.")
    for item in result.evidence:
        if not item.source.source_id or not item.source.dataset or not item.source.provider:
            add("source_lineage", "error", "Every evidence item must retain embedded source lineage.")
        if (
            result.freshness.market_date
            and item.freshness.market_date
            and result.freshness.market_date != item.freshness.market_date
            and result.freshness.state != CopilotFreshnessState.MIXED
        ):
            add("snapshot_date", "error", "Evidence belongs to a market date unrelated to the agent result.")
        if item.interpretation_class == CopilotInterpretationClass.CONTRADICTION and not item.contradicts_claim_ids:
            add("contradiction_link", "warning", "Contradictory evidence has no claim-level contradiction link.")

    if (
        result.status not in {CopilotAgentStatus.UNAVAILABLE, CopilotAgentStatus.FAILED}
        and result.freshness.generated_at is None
    ):
        add("generated_timestamp", "warning", "Available agent output should retain a generated timestamp.")

    deduped: dict[tuple[str, str, str], AgentContractIssueV1] = {}
    for issue in issues:
        deduped.setdefault((issue.code, issue.severity, issue.message), issue)
    final_issues = list(deduped.values())
    return AgentContractValidationV1(
        agent=result.agent,
        contract_version=selected.contract_version,
        status="failed" if any(issue.severity == "error" for issue in final_issues) else "passed",
        issues=final_issues,
    )
