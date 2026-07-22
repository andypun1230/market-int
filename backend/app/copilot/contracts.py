from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part[:1].upper() + part[1:] for part in tail)


class CopilotContractModel(BaseModel):
    # Keep enum instances in Python so the planner/orchestrator can use the
    # typed contract directly.  Pydantic/FastAPI still emit their string
    # values when serialising in JSON mode.
    model_config = ConfigDict(alias_generator=_camel, populate_by_name=True, extra="forbid")


class CopilotIntentType(str, Enum):
    MARKET_STATE = "MARKET_STATE"
    MARKET_EXPLANATION = "MARKET_EXPLANATION"
    INDEX_ANALYSIS = "INDEX_ANALYSIS"
    SECTOR_ANALYSIS = "SECTOR_ANALYSIS"
    THEME_ANALYSIS = "THEME_ANALYSIS"
    STOCK_ANALYSIS = "STOCK_ANALYSIS"
    STOCK_DECISION_SUPPORT = "STOCK_DECISION_SUPPORT"
    STOCK_COMPARISON = "STOCK_COMPARISON"
    WATCHLIST_REVIEW = "WATCHLIST_REVIEW"
    REPORT_QUERY = "REPORT_QUERY"
    RISK_QUERY = "RISK_QUERY"
    SCENARIO_QUERY = "SCENARIO_QUERY"
    MACRO_QUERY = "MACRO_QUERY"
    BREADTH_QUERY = "BREADTH_QUERY"
    RESEARCH_QUERY = "RESEARCH_QUERY"
    PORTFOLIO_QUERY = "PORTFOLIO_QUERY"
    APP_NAVIGATION = "APP_NAVIGATION"
    EDUCATIONAL_QUERY = "EDUCATIONAL_QUERY"
    FOLLOW_UP = "FOLLOW_UP"
    UNSUPPORTED_OR_AMBIGUOUS = "UNSUPPORTED_OR_AMBIGUOUS"


class CopilotOutputType(str, Enum):
    ANSWER = "answer"
    COMPARISON = "comparison"
    DECISION_SUPPORT = "decision_support"
    NAVIGATION = "navigation"
    EDUCATIONAL = "educational"


class CopilotAmbiguityLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class CopilotTimeHorizon(str, Enum):
    CURRENT_SESSION = "current_session"
    SHORT_TERM = "short_term"
    MEDIUM_TERM = "medium_term"
    LONG_TERM = "long_term"
    REPORT_DATE = "report_date"
    UNSPECIFIED = "unspecified"


class CopilotEntityType(str, Enum):
    STOCK = "stock"
    ETF = "etf"
    INDEX = "index"
    SECTOR = "sector"
    THEME = "theme"
    REPORT = "report"
    REPORT_SECTION = "report_section"
    APP_FEATURE = "app_feature"
    METRIC = "metric"


class CopilotAgentName(str, Enum):
    MARKET = "market"
    INDEX = "index"
    BREADTH = "breadth"
    LEADERSHIP = "leadership"
    SECTOR = "sector"
    THEME = "theme"
    MACRO = "macro"
    RISK = "risk"
    STOCK = "stock"
    WATCHLIST = "watchlist"
    REPORT = "report"
    RESEARCH = "research"
    NAVIGATION = "navigation"
    EDUCATIONAL = "educational"
    PORTFOLIO = "portfolio"


class CopilotAgentStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    STALE = "stale"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


class CopilotFreshnessState(str, Enum):
    LIVE = "live"
    DELAYED = "delayed"
    CACHED = "cached"
    STALE = "stale"
    TEST = "test"
    PARTIAL = "partial"
    MIXED = "mixed"
    UNAVAILABLE = "unavailable"


class CopilotEvidenceCategory(str, Enum):
    MARKET = "market"
    INDEX = "index"
    BREADTH = "breadth"
    LEADERSHIP = "leadership"
    SECTOR = "sector"
    THEME = "theme"
    MACRO = "macro"
    RISK = "risk"
    TECHNICAL = "technical"
    SIGNAL = "signal"
    WATCHLIST = "watchlist"
    REPORT = "report"
    RESEARCH = "research"
    NAVIGATION = "navigation"
    EDUCATIONAL = "educational"
    PORTFOLIO = "portfolio"


class CopilotInterpretationClass(str, Enum):
    OBSERVED_FACT = "observed_fact"
    ENGINE_CONCLUSION = "engine_conclusion"
    COPILOT_SYNTHESIS = "copilot_synthesis"
    MISSING_EVIDENCE = "missing_evidence"
    CONTRADICTION = "contradiction"


class CopilotConfidenceLabel(str, Enum):
    HIGH = "high"
    MODERATE = "moderate"
    LIMITED = "limited"


class CopilotStance(str, Enum):
    CONSTRUCTIVE = "constructive"
    SELECTIVELY_CONSTRUCTIVE = "selectively_constructive"
    NEUTRAL = "neutral"
    CAUTIOUS = "cautious"
    DEFENSIVE = "defensive"
    ACTIONABLE = "actionable"
    NEARLY_ACTIONABLE = "nearly_actionable"
    WAIT_FOR_CONFIRMATION = "wait_for_confirmation"
    MONITOR = "monitor"
    AVOID_FOR_NOW = "avoid_for_now"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    STRONGER = "stronger"
    WEAKER = "weaker"
    MIXED = "mixed"
    DEPENDS_ON_HORIZON = "depends_on_horizon"


class CopilotResponseStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    STALE = "stale"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


class CopilotActionType(str, Enum):
    NAVIGATE = "navigate"
    OPEN_ENTITY = "open_entity"
    OPEN_REPORT_SECTION = "open_report_section"


class CopilotDestination(str, Enum):
    HOME = "home"
    MARKET_OVERVIEW = "market_overview"
    INDEXES = "indexes"
    BREADTH = "breadth"
    HEALTH = "health"
    FEAR_GREED = "fear_greed"
    INSTITUTIONS = "institutions"
    MACRO = "macro"
    SECTOR_ROTATION = "sector_rotation"
    SECTOR_DETAIL = "sector_detail"
    THEME_DETAIL = "theme_detail"
    LEADERSHIP = "leadership"
    STOCK_DETAIL = "stock_detail"
    STOCK_TECHNICAL = "stock_technical"
    STOCK_SIGNALS = "stock_signals"
    STOCK_RISK = "stock_risk"
    WATCHLIST = "watchlist"
    REPORT = "report"
    REPORT_RESEARCH_FOCUS = "report_research_focus"
    REPORT_SCENARIOS = "report_scenarios"
    REPORT_WATCHLIST = "report_watchlist"
    SETTINGS = "settings"


class CopilotValidationStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    FALLBACK = "fallback"


class CopilotValidationCheck(str, Enum):
    AGENT_CONTRACT = "agent_contract"
    EVIDENCE_REFERENCES = "evidence_references"
    NUMERICAL_CLAIMS = "numerical_claims"
    TICKERS = "tickers"
    SOURCES = "sources"
    REPORT_LINEAGE = "report_lineage"
    CAUSALITY = "causality"
    PROXY_LABELING = "proxy_labeling"
    CONFIRMED_CLAIMS = "confirmed_claims"
    CONDITION_COHERENCE = "condition_coherence"
    CONTRADICTION_PRESERVATION = "contradiction_preservation"
    CONFIDENCE_FRESHNESS = "confidence_freshness"
    FRESHNESS_LANGUAGE = "freshness_language"
    HIGH_RISK_LANGUAGE = "high_risk_language"
    OWNERSHIP = "ownership"
    STALE_ACTIONABILITY = "stale_actionability"
    RECOMMENDATION = "recommendation"
    PROMPT_INJECTION = "prompt_injection"
    ACTIONS = "actions"


class CopilotValidationSeverity(str, Enum):
    WARNING = "warning"
    ERROR = "error"


class CopilotStreamEventType(str, Enum):
    START = "start"
    INTENT = "intent"
    PLAN = "plan"
    DIRECT_ANSWER = "direct_answer"
    EVIDENCE = "evidence"
    CONTRADICTION = "contradiction"
    CONDITIONS = "conditions"
    ACTIONS = "actions"
    FOLLOW_UPS = "follow_ups"
    COMPLETE = "complete"
    ERROR = "error"


class CopilotEntityV1(CopilotContractModel):
    entity_id: str
    entity_type: CopilotEntityType
    display_name: str
    symbol: str | None = None
    confidence: float = Field(default=1.0, ge=0, le=1)
    resolution_source: str = "registry"


class CopilotIntentV1(CopilotContractModel):
    schema_version: str = "copilot-intent-v1"
    intent_id: str
    intent: CopilotIntentType
    sub_intent: str
    entities: list[CopilotEntityV1] = Field(default_factory=list)
    ticker_symbols: list[str] = Field(default_factory=list)
    sectors: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    time_horizon: CopilotTimeHorizon = CopilotTimeHorizon.UNSPECIFIED
    requested_output_type: CopilotOutputType = CopilotOutputType.ANSWER
    decision_support_requested: bool = False
    personalization_relevant: bool = False
    navigation_requested: bool = False
    ambiguity_level: CopilotAmbiguityLevel = CopilotAmbiguityLevel.NONE
    confidence: float = Field(ge=0, le=1)
    required_agents: list[CopilotAgentName] = Field(default_factory=list)
    optional_agents: list[CopilotAgentName] = Field(default_factory=list)
    prohibited_assumptions: list[str] = Field(default_factory=list)
    unresolved_entities: list[str] = Field(default_factory=list)
    clarification_question: str | None = None


class CopilotEvidenceRequirementV1(CopilotContractModel):
    category: CopilotEvidenceCategory
    required: bool = True
    entities: list[str] = Field(default_factory=list)
    minimum_items: int = Field(default=1, ge=0, le=100)


class CopilotFreshnessRequirementV1(CopilotContractModel):
    allowed_states: list[CopilotFreshnessState]
    maximum_age_seconds: int | None = Field(default=None, ge=0)
    actionability_requires_current: bool = False


class CopilotPlanStepV1(CopilotContractModel):
    step_id: str
    order: int = Field(ge=1)
    agent: CopilotAgentName
    depends_on: list[str] = Field(default_factory=list)
    required: bool = True
    parallel_group: int = Field(default=1, ge=1)
    timeout_ms: int = Field(default=1500, ge=50, le=30_000)
    purpose: str


class CopilotPlanV1(CopilotContractModel):
    schema_version: str = "copilot-plan-v1"
    plan_id: str
    intent_id: str
    ordered_steps: list[CopilotPlanStepV1]
    required_agents: list[CopilotAgentName]
    optional_agents: list[CopilotAgentName] = Field(default_factory=list)
    dependencies: dict[str, list[str]] = Field(default_factory=dict)
    required_entities: list[str] = Field(default_factory=list)
    evidence_requirements: list[CopilotEvidenceRequirementV1] = Field(default_factory=list)
    freshness_requirements: CopilotFreshnessRequirementV1
    response_template: str
    deep_link_requirements: list[CopilotDestination] = Field(default_factory=list)
    fallback_rules: list[str] = Field(default_factory=list)
    maximum_latency_ms: int = Field(default=8000, ge=100, le=30_000)
    parallel_execution_allowed: bool = True

    @model_validator(mode="after")
    def validate_steps(self) -> "CopilotPlanV1":
        ids = [item.step_id for item in self.ordered_steps]
        if len(ids) != len(set(ids)):
            raise ValueError("plan step IDs must be unique")
        if set(self.required_agents) - {item.agent for item in self.ordered_steps}:
            raise ValueError("required agents must have plan steps")
        return self


class CopilotFreshnessV1(CopilotContractModel):
    state: CopilotFreshnessState
    market_date: str | None = None
    generated_at: str | None = None
    observed_at: str | None = None
    expires_at: str | None = None
    age_seconds: float | None = Field(default=None, ge=0)
    completeness: float = Field(default=0, ge=0, le=1)
    provider: str = "unavailable"
    warnings: list[str] = Field(default_factory=list)


class CopilotSourceReferenceV1(CopilotContractModel):
    source_id: str
    provider: str
    dataset: str
    generated_at: str | None = None
    market_date: str | None = None
    raw_engine_reference: str | None = None


class CopilotLevelV1(CopilotContractModel):
    label: str
    value: float | str
    unit: str | None = None
    evidence_id: str


class CopilotEvidenceV1(CopilotContractModel):
    schema_version: str = "copilot-evidence-v1"
    evidence_id: str
    category: CopilotEvidenceCategory
    entity: str
    metric: str
    value: Any = None
    unit: str | None = None
    current_state: str | None = None
    prior_value: Any = None
    change: Any = None
    timeframe: str = "current"
    interpretation_class: CopilotInterpretationClass
    source: CopilotSourceReferenceV1
    freshness: CopilotFreshnessV1
    confidence: CopilotConfidenceLabel = CopilotConfidenceLabel.MODERATE
    deep_link: str | None = None
    report_reference: str | None = None
    supports_claim_ids: list[str] = Field(default_factory=list)
    contradicts_claim_ids: list[str] = Field(default_factory=list)


class AgentResultV1(CopilotContractModel):
    schema_version: str = "copilot-agent-result-v1"
    agent: CopilotAgentName
    status: CopilotAgentStatus
    observations: list[str] = Field(default_factory=list)
    conclusions: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    levels: list[CopilotLevelV1] = Field(default_factory=list)
    source_references: list[CopilotSourceReferenceV1] = Field(default_factory=list)
    evidence: list[CopilotEvidenceV1] = Field(default_factory=list)
    freshness: CopilotFreshnessV1
    deep_link_targets: list[CopilotDestination] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    missing_data: list[str] = Field(default_factory=list)
    duration_ms: float = Field(default=0, ge=0)
    failure_category: str | None = None


class CopilotFreshnessSummaryV1(CopilotContractModel):
    overall_state: CopilotFreshnessState
    market_dates: list[str] = Field(default_factory=list)
    generated_timestamps: list[str] = Field(default_factory=list)
    current_count: int = Field(default=0, ge=0)
    stale_count: int = Field(default=0, ge=0)
    partial_count: int = Field(default=0, ge=0)
    unavailable_count: int = Field(default=0, ge=0)
    test_count: int = Field(default=0, ge=0)
    warnings: list[str] = Field(default_factory=list)


class CopilotEvidenceBundleV1(CopilotContractModel):
    schema_version: str = "copilot-evidence-bundle-v1"
    request_id: str
    question: str
    intent: CopilotIntentV1
    plan: CopilotPlanV1
    agent_results: list[AgentResultV1]
    evidence: list[CopilotEvidenceV1]
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    contradictory_evidence_ids: list[str] = Field(default_factory=list)
    unavailable_evidence: list[str] = Field(default_factory=list)
    freshness_summary: CopilotFreshnessSummaryV1
    source_summary: list[CopilotSourceReferenceV1] = Field(default_factory=list)
    deep_link_targets: list[CopilotDestination] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CopilotReasoningFactorV1(CopilotContractModel):
    statement: str
    evidence_ids: list[str]


class CopilotReasoningV1(CopilotContractModel):
    schema_version: str = "copilot-reasoning-v1"
    direct_answer: str
    stance: CopilotStance
    confidence_label: CopilotConfidenceLabel
    thesis: str
    supporting_factors: list[CopilotReasoningFactorV1] = Field(default_factory=list)
    contradictory_factors: list[CopilotReasoningFactorV1] = Field(default_factory=list)
    key_risks: list[CopilotReasoningFactorV1] = Field(default_factory=list)
    confirmation_conditions: list[CopilotReasoningFactorV1] = Field(default_factory=list)
    invalidation_conditions: list[CopilotReasoningFactorV1] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    personalization_note: str | None = None
    related_research: list[str] = Field(default_factory=list)
    recommended_app_destinations: list[CopilotDestination] = Field(default_factory=list)
    disclaimer_class: str = "educational_market_decision_support"


class CopilotActionV1(CopilotContractModel):
    action_id: str
    label: str
    action_type: CopilotActionType
    destination_id: CopilotDestination
    route: str
    tab: str | None = None
    sub_tab: str | None = None
    section_id: str | None = None
    entity: str | None = None
    highlight_target: str | None = None
    parameters: dict[str, str] = Field(default_factory=dict)


class CopilotSessionContextV1(CopilotContractModel):
    schema_version: str = "copilot-session-context-v1"
    thread_id: str
    active_entities: list[CopilotEntityV1] = Field(default_factory=list)
    active_intent: CopilotIntentType | None = None
    latest_referenced_stock: str | None = None
    latest_referenced_sector_or_theme: str | None = None
    latest_report_id: str | None = None
    latest_thesis: str | None = None
    unresolved_question: str | None = None
    previous_answer_stance: CopilotStance | None = None
    relevant_evidence_ids: list[str] = Field(default_factory=list)
    current_screen: str | None = None
    current_route: str | None = None
    updated_at: str


class CopilotValidationIssueV1(CopilotContractModel):
    check: CopilotValidationCheck
    severity: CopilotValidationSeverity
    message: str


class CopilotValidationResultV1(CopilotContractModel):
    status: CopilotValidationStatus
    checks_run: list[CopilotValidationCheck]
    issues: list[CopilotValidationIssueV1] = Field(default_factory=list)
    fallback_used: bool = False


class CopilotGroundingV1(CopilotContractModel):
    context_used: list[str] = Field(default_factory=list)
    source_state: CopilotFreshnessState
    generated_at: str
    evidence_ids: list[str] = Field(default_factory=list)


class CopilotAnswerSectionsV1(CopilotContractModel):
    direct_answer: str
    why: list[str] = Field(default_factory=list)
    evidence_for: list[str] = Field(default_factory=list)
    evidence_against: list[str] = Field(default_factory=list)
    main_caution: str | None = None
    what_would_confirm: list[str] = Field(default_factory=list)
    what_would_invalidate: list[str] = Field(default_factory=list)
    what_would_change: list[str] = Field(default_factory=list)


class CopilotAnswerConfidenceV1(CopilotContractModel):
    level: CopilotConfidenceLabel
    reasons: list[str] = Field(default_factory=list)


class CopilotResponseV1(CopilotContractModel):
    schema_version: str = "institutional-copilot-response-v1"
    request_id: str
    plan_id: str
    thread_id: str
    status: CopilotResponseStatus
    answer: str
    answer_sections: CopilotAnswerSectionsV1
    grounding: CopilotGroundingV1
    suggested_follow_ups: list[str] = Field(default_factory=list)
    confidence: int = Field(ge=0, le=100)
    answer_confidence: CopilotAnswerConfidenceV1
    generated_by: str
    disclaimer: str
    intent: CopilotIntentV1
    plan: CopilotPlanV1
    reasoning: CopilotReasoningV1
    evidence: list[CopilotEvidenceV1]
    actions: list[CopilotActionV1] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    freshness_summary: CopilotFreshnessSummaryV1
    validation: CopilotValidationResultV1
    agent_timings_ms: dict[str, float] = Field(default_factory=dict)
    retry_count: int = Field(default=0, ge=0)
    failure_categories: list[str] = Field(default_factory=list)


class CopilotStreamEventV1(CopilotContractModel):
    event_id: str
    type: CopilotStreamEventType
    request_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
