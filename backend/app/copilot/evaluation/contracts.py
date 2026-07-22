from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.copilot.contracts import (
    CopilotAgentName,
    CopilotDestination,
    CopilotFreshnessState,
    CopilotIntentType,
)


EVALUATOR_VERSION = "stage7-evaluator-v1"
FIXTURE_SCHEMA_VERSION = "stage7-golden-case-v1"
RESULT_SCHEMA_VERSION = "stage7-evaluation-result-v1"


class EvaluationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=False)


class EvaluationSuite(str, Enum):
    GOLDEN = "golden"
    ROUTING = "routing"
    PERFORMANCE = "performance"
    SAFETY = "safety"
    FULL = "full"


class EvaluationCategory(str, Enum):
    MARKET = "market"
    BREADTH = "breadth"
    LEADERSHIP = "leadership"
    SECTOR = "sector"
    THEME = "theme"
    MACRO = "macro"
    RISK = "risk"
    STOCK = "stock"
    WATCHLIST = "watchlist"
    RESEARCH = "research"
    REPORT = "report"
    NAVIGATION = "navigation"
    ROUTING = "routing"
    SYNTHESIS = "synthesis"
    EDUCATIONAL = "educational"
    PORTFOLIO = "portfolio"
    FAILURE_INJECTION = "failure_injection"


class ContradictionExpectation(str, Enum):
    NONE = "none_expected"
    PRESERVE = "must_preserve"
    DISCLOSE_MISSING = "disclose_if_unavailable"


class ClaimType(str, Enum):
    OBSERVATION = "observation"
    CONCLUSION = "conclusion"
    CONTRADICTION = "contradiction"
    CONFIRMATION = "confirmation"
    INVALIDATION = "invalidation"
    LIMITATION = "limitation"
    PROXY = "proxy"


class IssueSeverity(str, Enum):
    WARNING = "warning"
    ERROR = "error"


class ReleaseResult(str, Enum):
    NON_RELEASE = "NON-RELEASE"
    PASS = "PASS"
    PASS_WITH_CONDITIONS = "PASS WITH CONDITIONS"
    FAIL = "FAIL"


class ConfidenceRange(EvaluationModel):
    minimum: float = Field(ge=0, le=1)
    maximum: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def ordered(self) -> "ConfidenceRange":
        if self.minimum > self.maximum:
            raise ValueError("confidence minimum must not exceed maximum")
        return self


class AgentSelectionExpectation(EvaluationModel):
    required: list[CopilotAgentName] = Field(default_factory=list)
    optional: list[CopilotAgentName] = Field(default_factory=list)
    forbidden: list[CopilotAgentName] = Field(default_factory=list)
    maximum_agent_count: int = Field(default=8, ge=0, le=20)

    @model_validator(mode="after")
    def disjoint(self) -> "AgentSelectionExpectation":
        required, optional, forbidden = map(set, (self.required, self.optional, self.forbidden))
        if required & optional or required & forbidden or optional & forbidden:
            raise ValueError("required, optional, and forbidden agents must be disjoint")
        if len(required) > self.maximum_agent_count:
            raise ValueError("maximum agent count cannot be below required agent count")
        return self


class FrozenEntity(EvaluationModel):
    entity_type: str
    entity_id: str
    display_name: str
    symbol: str | None = None
    confidence: float = Field(default=1.0, ge=0, le=1)


class FrozenEvidence(EvaluationModel):
    evidence_id: str
    snapshot_id: str
    category: str
    entity: str
    metric: str
    value: Any = None
    freshness: CopilotFreshnessState
    source: str
    supports: list[str] = Field(default_factory=list)
    contradicts: list[str] = Field(default_factory=list)


class FrozenInput(EvaluationModel):
    question: str
    as_of: str
    evidence: list[FrozenEvidence] = Field(default_factory=list)
    resolved_entities: list[FrozenEntity] = Field(default_factory=list)
    unresolved_entities: list[str] = Field(default_factory=list)
    ambiguous_entities: list[str] = Field(default_factory=list)
    screen_context: dict[str, Any] = Field(default_factory=dict)
    session_context: dict[str, Any] | None = None
    failure_injection: str | None = None

    @model_validator(mode="after")
    def unique_evidence(self) -> "FrozenInput":
        evidence_ids = [item.evidence_id for item in self.evidence]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("frozen evidence IDs must be unique within a fixture")
        return self


class CandidateClaim(EvaluationModel):
    text: str
    evidence_ids: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    claim_type: ClaimType = ClaimType.OBSERVATION


class EvaluationCandidate(EvaluationModel):
    output_schema_version: str = "institutional-copilot-response-v1"
    intent: CopilotIntentType
    selected_agents: list[CopilotAgentName] = Field(default_factory=list)
    conclusion_class: str
    confidence: float = Field(ge=0, le=1)
    cited_evidence: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    freshness: CopilotFreshnessState
    deep_links: list[CopilotDestination] = Field(default_factory=list)
    claims: list[CandidateClaim] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    actionable: bool = False
    latency_ms: float = Field(default=0, ge=0)
    model_calls: int = Field(default=0, ge=0)
    # Runtime-only diagnostics are carried in CaseEvaluationResult.observations
    # for machine output.  Excluding these defaults here keeps the permanent
    # 165-case JSONL corpus byte-stable when its generator serialises a
    # reference candidate.
    agent_latency_ms: dict[str, float] = Field(default_factory=dict, exclude=True)
    validation_status: str | None = Field(default=None, exclude=True)
    fallback_used: bool = Field(default=False, exclude=True)
    response_status: str | None = Field(default=None, exclude=True)
    failure_categories: list[str] = Field(default_factory=list, exclude=True)


class GoldenEvaluationCase(EvaluationModel):
    schema_version: str = FIXTURE_SCHEMA_VERSION
    fixture_id: str
    description: str
    category: EvaluationCategory
    suites: list[EvaluationSuite]
    tags: list[str] = Field(default_factory=list)
    frozen_input: FrozenInput
    expected_intent: CopilotIntentType
    acceptable_secondary_intents: list[CopilotIntentType] = Field(default_factory=list)
    expected_agent_selection: AgentSelectionExpectation
    expected_structured_conclusion: list[str] = Field(min_length=1)
    required_evidence: list[str] = Field(default_factory=list)
    forbidden_evidence: list[str] = Field(default_factory=list)
    expected_contradiction_handling: ContradictionExpectation
    expected_freshness_state: CopilotFreshnessState
    allowed_confidence_range: ConfidenceRange
    expected_deep_links: list[CopilotDestination] = Field(default_factory=list)
    forbidden_claims: list[str] = Field(default_factory=list)
    context_required: bool = False
    rationale: str
    latency_budget_ms: float = Field(default=8000, gt=0)
    model_call_budget: int = Field(default=0, ge=0)
    reference_output: EvaluationCandidate

    @model_validator(mode="after")
    def validate_references(self) -> "GoldenEvaluationCase":
        known = {item.evidence_id for item in self.frozen_input.evidence}
        required, forbidden = set(self.required_evidence), set(self.forbidden_evidence)
        if required - known:
            raise ValueError("required evidence must exist in frozen input")
        if required & forbidden:
            raise ValueError("evidence cannot be both required and forbidden")
        if EvaluationSuite.FULL not in self.suites:
            raise ValueError("every case must participate in the full suite")
        if self.context_required and not self.frozen_input.session_context:
            raise ValueError("context-required cases need frozen session context")
        return self


class EvaluationIssue(EvaluationModel):
    code: str
    component: str
    severity: IssueSeverity
    release_blocking: bool
    message: str


class CaseEvaluationResult(EvaluationModel):
    fixture_id: str
    category: EvaluationCategory
    suites: list[EvaluationSuite]
    passed: bool
    weighted_quality_score: float = Field(ge=0, le=1)
    component_scores: dict[str, float]
    issues: list[EvaluationIssue] = Field(default_factory=list)
    metrics: dict[str, float] = Field(default_factory=dict)
    observed_candidate: EvaluationCandidate | None = None
    observations: dict[str, Any] = Field(default_factory=dict)


class EvaluationSummary(EvaluationModel):
    schema_version: str = RESULT_SCHEMA_VERSION
    evaluator_version: str = EVALUATOR_VERSION
    evaluation_mode: str = "offline-frozen-with-deterministic-routing"
    suite: EvaluationSuite
    generated_at: str
    result: ReleaseResult
    fixture_count: int
    passed_count: int
    failed_count: int
    release_blocker_count: int
    category_counts: dict[str, int]
    suite_counts: dict[str, int]
    component_scores: dict[str, float]
    routing_metrics: dict[str, float]
    performance_metrics: dict[str, float]
    case_results: list[CaseEvaluationResult]
    failures: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[dict[str, Any]] = Field(default_factory=list)
    release_bearing: bool = False
    limitations: list[str] = Field(default_factory=list)
    runtime_coverage: dict[str, Any] = Field(default_factory=dict)
    agent_performance_metrics: dict[str, dict[str, float]] = Field(default_factory=dict)
