from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


QualityState = Literal["live", "cached", "stale", "test", "mixed", "partial", "unavailable"]
ResearchDirection = Literal["leading", "emerging", "weakening", "lagging", "breakdown", "divergence"]
ResearchCategory = Literal["sector", "theme", "industry_group", "security_cluster", "individual_security", "market_divergence", "cross_asset_divergence"]
EvidenceGrade = Literal["High", "Medium", "Low"]
EvidenceStance = Literal["supports", "neutral", "contradicts"]
RelationshipType = Literal[
    "sector_hierarchy",
    "theme_hierarchy",
    "relative_performance",
    "benchmark_relationship",
    "user_watchlist_overlap",
    "validated_taxonomy",
    "validated_supply_chain",
]

SUPPORTED_STAGE6_ANNOTATIONS = {
    "support",
    "resistance",
    "breakout",
    "failed_breakout",
    "gap",
    "pivot",
    "ema",
    "trendline",
    "previous_report",
    "current_thesis",
    "risk",
    "confirmation",
    "invalidation",
    # Stored V7 documents can contain these pre-Stage-6 annotation names.
    "recent_high",
    "recent_low",
    "confirmation_arrow",
    "previous_report_marker",
    "volume_expansion",
    "ma",
    "moving_average_label",
}


class SourceReference(BaseModel):
    source_id: str
    provider: str
    dataset: str
    timestamp: str | None = None
    url: str | None = None
    access_status: str = "available"
    source_type: str = "market_data"
    freshness: str = "current"


class DataQualityState(BaseModel):
    state: QualityState
    completeness: float = Field(ge=0, le=1)
    freshness: str
    transformation: str
    warnings: list[str] = Field(default_factory=list)


class EvidencePoint(BaseModel):
    evidence_id: str
    metric: str
    current_value: float | str | None
    previous_value: float | str | None = None
    change: float | str | None = None
    unit: str | None = None
    timeframe: str
    source_id: str
    timestamp: str | None = None
    freshness: str = "current"
    reliability: str = "supported"
    observation_type: str = "point_in_time"


class AnalyticalClaim(BaseModel):
    claim_id: str
    statement: str
    evidence_ids: list[str]
    counter_evidence_ids: list[str] = Field(default_factory=list)
    interpretation: str
    trader_implication: str
    confidence: str
    evidence_quality: QualityState


class FigureSeries(BaseModel):
    series_id: str
    label: str
    unit: str
    points: list[dict[str, Any]]
    source_id: str
    color: str | None = None
    transformation: str = "none"


class FigureAnnotation(BaseModel):
    annotation_id: str
    annotation_type: str
    label: str
    evidence_id: str
    freshness: str = "current"
    value: float | None = None
    point_index: int | None = None
    date: str | None = None
    detail: str | None = None

    @model_validator(mode="after")
    def reject_speculative_projection(self) -> "FigureAnnotation":
        if "future" in self.annotation_type.lower():
            raise ValueError("figure annotations cannot contain speculative future arrows")
        return self


class FigureSpec(BaseModel):
    figure_id: str
    figure_number: int = 0
    title: str
    subtitle: str
    question_answered: str
    chart_type: str
    timeframe: str
    data_series: list[FigureSeries]
    annotations: list[FigureAnnotation] = Field(default_factory=list)
    reference_lines: list[dict[str, Any]] = Field(default_factory=list)
    source_ids: list[str]
    as_of: str | None = None
    observation: str
    interpretation: str
    confirmation_condition: str
    risk_condition: str
    quality: DataQualityState

    @model_validator(mode="after")
    def validate_sources(self) -> "FigureSpec":
        if not self.source_ids or not self.data_series:
            raise ValueError("figures require sources and visible data series")
        return self


class TableSpec(BaseModel):
    table_id: str
    title: str
    columns: list[str]
    rows: list[dict[str, Any]]
    source_ids: list[str] = Field(default_factory=list)
    as_of: str | None = None
    quality: DataQualityState


class MonitoringCondition(BaseModel):
    condition_id: str
    metric: str
    threshold_or_condition: str
    rationale: str
    action_implication: str
    evidence_ids: list[str]


class ScenarioSpec(BaseModel):
    scenario_id: str
    label: str
    likelihood: str
    required_conditions: list[str]
    confirming_indicators: list[str]
    benchmark_levels: list[str]
    breadth_conditions: list[str]
    risk_conditions: list[str]
    likely_leadership: list[str]
    invalidation: list[str]
    operating_response: str
    position_sizing_implication: str
    evidence_ids: list[str]


class SecurityResearchItem(BaseModel):
    security_id: str
    symbol: str
    category: str
    monitoring_bias: str
    setup_state: str
    summary: str
    evidence_ids: list[str]
    figure_id: str | None = None
    confirmation: str
    invalidation: str
    risk_considerations: str
    reason_for_inclusion: str
    source_ids: list[str]
    freshness: str
    actionable: bool
    group: str | None = None
    daily_change: float | None = None
    relative_strength: float | str | None = None
    trend: str | None = None
    volume_condition: str | None = None
    confirmation_level: float | None = None
    invalidation_level: float | None = None
    change_since_previous: str | None = None
    research_classification: str = "Data insufficient"
    focus_relation: str | None = None
    source_timestamp: str | None = None
    why_here: str | None = None
    context: str | None = None
    sector: str | None = None
    themes: list[str] = Field(default_factory=list)
    execution_consideration: str | None = None
    selected_for_research: bool = True


class UserRelevanceEvidence(BaseModel):
    tier: Literal["high", "moderate", "low"] = "low"
    score: float = Field(default=0, ge=0, le=100)
    exact_saved_group: bool = False
    saved_parent_group: bool = False
    saved_security_symbols: list[str] = Field(default_factory=list)
    stale: bool = False
    rationale: list[str] = Field(default_factory=list)


class ResearchCandidateScore(BaseModel):
    total: float = Field(ge=0, le=100)
    materiality_threshold: float = Field(ge=0, le=100)
    weights: dict[str, float]
    dimension_scores: dict[str, float | None]
    weighted_contributions: dict[str, float]
    missing_dimensions: list[str] = Field(default_factory=list)


class ResearchCandidate(BaseModel):
    candidate_id: str
    name: str
    category: ResearchCategory
    direction: ResearchDirection
    current_rank: int | None = None
    previous_rank: int | None = None
    rank_change: int | None = None
    current_relative_strength: float | None = None
    relative_strength_change: float | None = None
    returns: dict[str, float | None] = Field(default_factory=dict)
    breadth: float | None = None
    breadth_change: float | None = None
    participation: float | None = None
    participation_change: float | None = None
    momentum: float | None = None
    volume_confirmation: float | None = None
    persistence: float | None = None
    market_relative_divergence: float | None = None
    qualifying_constituent_count: int = 0
    constituents: list[dict[str, Any]] = Field(default_factory=list)
    taxonomy_chain: list[dict[str, str]] = Field(default_factory=list)
    mapping_type: str = "taxonomy_membership"
    user_relevance: UserRelevanceEvidence = Field(default_factory=UserRelevanceEvidence)
    freshness: str = "unknown"
    source_quality: QualityState = "unavailable"
    data_completeness: float = Field(default=0, ge=0, le=1)
    evidence_ids: list[str] = Field(default_factory=list)
    supported_figure_types: list[str] = Field(default_factory=list)
    disqualifying_conditions: list[str] = Field(default_factory=list)
    score: ResearchCandidateScore


class ResearchSelectionExplanation(BaseModel):
    candidate_id: str
    candidate_name: str
    score: float
    score_difference: float | None = None
    selected: bool = False
    reasons: list[str] = Field(default_factory=list)


class ResearchSelectionDecision(BaseModel):
    selected_candidate_id: str | None = None
    secondary_candidate_id: str | None = None
    materiality_threshold: float
    selected_because: list[str] = Field(default_factory=list)
    no_selection_reason: str | None = None
    competing_candidates: list[ResearchSelectionExplanation] = Field(default_factory=list)
    omitted_candidate_count: int = 0
    user_relevance_contribution: float = 0
    missing_evidence: list[str] = Field(default_factory=list)
    freshness_status: str = "unknown"


class SavedSecurityImpact(BaseModel):
    symbol: str
    group: str
    setup_state: str
    relative_strength: float | str | None = None
    trend: str
    volume_condition: str
    key_level: str
    change_since_previous: str
    relation_to_focus: str
    freshness: str
    reason_to_monitor: str
    evidence_ids: list[str] = Field(default_factory=list)


class ResearchEvidenceQuality(BaseModel):
    label: EvidenceGrade
    freshness: EvidenceGrade
    breadth: EvidenceGrade
    participation: EvidenceGrade
    completeness: EvidenceGrade
    consistency: EvidenceGrade
    rationale: list[str]
    evidence_ids: list[str]


class EvidenceMatrixRow(BaseModel):
    dimension: str
    finding: str
    stance: EvidenceStance
    implication: str
    evidence_ids: list[str]


class ResearchRelationshipNode(BaseModel):
    node_id: str
    label: str
    node_type: str
    depth: int = Field(ge=0, le=8)


class ResearchRelationshipEdge(BaseModel):
    relationship_id: str
    source_node_id: str
    target_node_id: str
    relationship_type: RelationshipType
    label: str
    mapping_source: str
    structured_data: bool = False
    evidence_ids: list[str]

    @model_validator(mode="after")
    def validate_supply_chain(self) -> "ResearchRelationshipEdge":
        if self.relationship_type == "validated_supply_chain" and (
            not self.structured_data or not self.mapping_source.strip()
        ):
            raise ValueError("supply-chain relationships require an explicit structured mapping source")
        return self


class ResearchRelationshipGraph(BaseModel):
    nodes: list[ResearchRelationshipNode]
    edges: list[ResearchRelationshipEdge]

    @model_validator(mode="after")
    def validate_graph(self) -> "ResearchRelationshipGraph":
        node_ids = [item.node_id for item in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("research relationship graph node IDs must be unique")
        known = set(node_ids)
        edge_ids = [item.relationship_id for item in self.edges]
        if len(edge_ids) != len(set(edge_ids)):
            raise ValueError("research relationship graph edge IDs must be unique")
        for edge in self.edges:
            if edge.source_node_id not in known or edge.target_node_id not in known:
                raise ValueError("research relationship graph edge references an unknown node")
        return self


class ResearchSecuritySignal(BaseModel):
    symbol: str
    role: Literal["leader", "laggard"]
    metric_label: str
    metric_value: float | str | None = None
    timeframe: str
    reason: str
    saved: bool = False
    evidence_ids: list[str]


class ResearchEvolution(BaseModel):
    previous_report_date: str | None = None
    yesterday: str
    today: str
    tomorrow: str
    what_changed: str
    research_follow_up: str
    previous_focus: str | None = None
    current_focus: str
    status: str
    evidence_ids: list[str]


class ResearchInquiry(BaseModel):
    status: Literal["qualified", "no_focus"]
    question: str
    executive_answer: str
    evidence_ids: list[str] = Field(default_factory=list)


class ResearchFocus(BaseModel):
    candidate_id: str
    subject: str
    category: ResearchCategory
    direction: ResearchDirection
    priority_score: float
    classification_label: str
    user_relevance: UserRelevanceEvidence
    main_thesis: str
    counter_thesis: str
    why_selected: list[str]
    key_evidence: list[str]
    confirmation_conditions: list[str]
    invalidation_conditions: list[str]
    prose_sections: dict[str, str]
    figure_ids: list[str]
    affected_securities: list[SavedSecurityImpact] = Field(default_factory=list)
    taxonomy_chain: list[dict[str, str]] = Field(default_factory=list)
    evidence_ids: list[str]
    limitations: list[str] = Field(default_factory=list)
    question: str = ""
    executive_answer: str = ""
    evidence_quality: ResearchEvidenceQuality | None = None
    evidence_matrix: list[EvidenceMatrixRow] = Field(default_factory=list)
    relationship_graph: ResearchRelationshipGraph | None = None
    leading_securities: list[ResearchSecuritySignal] = Field(default_factory=list)
    lagging_securities: list[ResearchSecuritySignal] = Field(default_factory=list)
    execution_implications: list[str] = Field(default_factory=list)
    conclusion_change_conditions: list[str] = Field(default_factory=list)
    research_evolution: ResearchEvolution | None = None


class SecondaryResearchNote(BaseModel):
    candidate_id: str
    subject: str
    direction: ResearchDirection
    summary: str
    evidence_ids: list[str]


class MarketTimelineEntry(BaseModel):
    market_date: str
    regime: str | None = None
    market_health: float | None = None
    breadth: float | None = None
    leadership_concentration: float | None = None
    risk: float | None = None
    volatility_state: str | None = None
    primary_leader: str | None = None
    primary_laggard: str | None = None
    research_focus: str | None = None


class ReportThesis(BaseModel):
    posture: str
    concise_thesis: str
    previous_thesis: str | None = None
    thesis_change: str
    supporting_evidence_ids: list[str]
    contradictory_evidence_ids: list[str]
    confirmation_conditions: list[str]
    invalidation_conditions: list[str]
    confidence_label: str
    data_completeness: float = Field(ge=0, le=1)


class ReportSection(BaseModel):
    section_id: str
    number: int
    title: str
    purpose: str
    paragraphs: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)
    figure_ids: list[str] = Field(default_factory=list)
    table_ids: list[str] = Field(default_factory=list)
    scenario_ids: list[str] = Field(default_factory=list)
    security_ids: list[str] = Field(default_factory=list)
    monitoring_condition_ids: list[str] = Field(default_factory=list)
    quality_note: str | None = None
    question: str | None = None


class ReportDocument(BaseModel):
    document_version: str = "report-document-v1"
    report_id: str
    pdf_format_version: str
    title: str
    report_type: str
    market_date: str
    generated_at: str
    data_cutoff: str
    timezone: str
    source_status: QualityState
    thesis: ReportThesis
    sections: list[ReportSection]
    evidence: list[EvidencePoint]
    claims: list[AnalyticalClaim]
    figures: list[FigureSpec]
    tables: list[TableSpec]
    sources: list[SourceReference]
    scenarios: list[ScenarioSpec]
    securities: list[SecurityResearchItem]
    monitoring_conditions: list[MonitoringCondition]
    limitations: list[str]
    page_count_estimate: int
    figure_count: int
    approximate_word_count: int
    previous_report_available: bool
    research_candidates: list[ResearchCandidate] = Field(default_factory=list)
    research_selection: ResearchSelectionDecision | None = None
    research_focus: ResearchFocus | None = None
    secondary_research_note: SecondaryResearchNote | None = None
    market_timeline: list[MarketTimelineEntry] = Field(default_factory=list)
    research_inquiry: ResearchInquiry | None = None

    @model_validator(mode="after")
    def validate_registry_integrity(self) -> "ReportDocument":
        evidence_ids = {item.evidence_id for item in self.evidence}
        source_ids = {item.source_id for item in self.sources}
        figure_ids = {item.figure_id for item in self.figures}
        candidate_ids = {item.candidate_id for item in self.research_candidates}
        if len(figure_ids) != len(self.figures):
            raise ValueError("figure IDs must be unique")
        for claim in self.claims:
            if not set(claim.evidence_ids + claim.counter_evidence_ids).issubset(evidence_ids):
                raise ValueError(f"claim {claim.claim_id} references unknown evidence")
        for figure in self.figures:
            if not set(figure.source_ids).issubset(source_ids):
                raise ValueError(f"figure {figure.figure_id} references unknown sources")
            for annotation in figure.annotations:
                if annotation.evidence_id not in evidence_ids:
                    raise ValueError(f"figure {figure.figure_id} annotation references unknown evidence")
                if self.document_version == "report-document-v2":
                    if annotation.annotation_type not in SUPPORTED_STAGE6_ANNOTATIONS:
                        raise ValueError(f"figure {figure.figure_id} has an unsupported Stage 6 annotation type")
                    max_points = max((len(series.points) for series in figure.data_series), default=0)
                    if annotation.point_index is not None and not 0 <= annotation.point_index < max_points:
                        raise ValueError(f"figure {figure.figure_id} annotation falls outside observed history")
                    if annotation.date and figure.as_of and annotation.date[:10] > figure.as_of[:10]:
                        raise ValueError(f"figure {figure.figure_id} annotation occurs after the figure as-of date")
            if self.pdf_format_version == "daily-report-pdf-v7":
                for reference in figure.reference_lines:
                    reference_evidence_id = reference.get("evidence_id")
                    if not reference_evidence_id or reference_evidence_id not in evidence_ids:
                        raise ValueError(f"V7 figure {figure.figure_id} reference line requires known evidence")
                    if str(reference.get("freshness") or "").lower() in {"stale", "unavailable"}:
                        raise ValueError(f"V7 figure {figure.figure_id} cannot display a stale reference line")
        for security in self.securities:
            if security.figure_id and security.figure_id not in figure_ids:
                raise ValueError(f"security {security.security_id} references unknown figure")
        if self.figure_count != len(self.figures):
            raise ValueError("figure count does not match registry")
        for candidate in self.research_candidates:
            if not set(candidate.evidence_ids).issubset(evidence_ids):
                raise ValueError(f"research candidate {candidate.candidate_id} references unknown evidence")
        if self.research_selection and self.research_selection.selected_candidate_id:
            if self.research_selection.selected_candidate_id not in candidate_ids:
                raise ValueError("research selection references unknown candidate")
        if self.research_focus:
            if self.research_focus.candidate_id not in candidate_ids:
                raise ValueError("research focus references unknown candidate")
            if not set(self.research_focus.evidence_ids).issubset(evidence_ids):
                raise ValueError("research focus references unknown evidence")
            if not set(self.research_focus.figure_ids).issubset(figure_ids):
                raise ValueError("research focus references unknown figures")
            for affected in self.research_focus.affected_securities:
                if not set(affected.evidence_ids).issubset(evidence_ids):
                    raise ValueError(f"affected security {affected.symbol} references unknown evidence")
            if self.pdf_format_version == "daily-report-pdf-v7" and len(self.research_focus.figure_ids) < 2:
                raise ValueError("V7 research focus requires at least two figures")
            if self.research_focus.evidence_quality and not set(self.research_focus.evidence_quality.evidence_ids).issubset(evidence_ids):
                raise ValueError("research evidence quality references unknown evidence")
            for row in self.research_focus.evidence_matrix:
                if not row.evidence_ids or not set(row.evidence_ids).issubset(evidence_ids):
                    raise ValueError(f"research evidence matrix row {row.dimension} references unknown evidence")
            if self.research_focus.relationship_graph:
                for edge in self.research_focus.relationship_graph.edges:
                    if not edge.evidence_ids or not set(edge.evidence_ids).issubset(evidence_ids):
                        raise ValueError(f"research relationship {edge.relationship_id} references unknown evidence")
            for signal in [*self.research_focus.leading_securities, *self.research_focus.lagging_securities]:
                if not signal.evidence_ids or not set(signal.evidence_ids).issubset(evidence_ids):
                    raise ValueError(f"research security signal {signal.symbol} references unknown evidence")
            if self.research_focus.research_evolution and not set(self.research_focus.research_evolution.evidence_ids).issubset(evidence_ids):
                raise ValueError("research evolution references unknown evidence")
        if self.research_inquiry and not set(self.research_inquiry.evidence_ids).issubset(evidence_ids):
            raise ValueError("research inquiry references unknown evidence")
        if self.document_version == "report-document-v2":
            if not self.research_inquiry:
                raise ValueError("Stage 6 documents require a research inquiry")
            if not self.research_inquiry.question.rstrip().endswith("?"):
                raise ValueError("Stage 6 research inquiry must be phrased as a question")
            for section in self.sections:
                if not section.question or not section.question.rstrip().endswith("?"):
                    raise ValueError(f"Stage 6 section {section.section_id} must begin with a question")
            if self.research_focus:
                focus = self.research_focus
                if self.research_inquiry.status != "qualified":
                    raise ValueError("a qualified focus requires a qualified research inquiry")
                if not focus.question.rstrip().endswith("?") or not focus.executive_answer.strip():
                    raise ValueError("Stage 6 research focus requires a question and executive answer")
                if not focus.main_thesis.strip() or not focus.counter_thesis.strip():
                    raise ValueError("Stage 6 research focus requires a main thesis and counter-thesis")
                if not focus.evidence_ids:
                    raise ValueError("Stage 6 research focus requires registered focus evidence")
                required_focus_collections = {
                    "selection reasons": focus.why_selected,
                    "key evidence": focus.key_evidence,
                    "confirmation conditions": focus.confirmation_conditions,
                    "invalidation conditions": focus.invalidation_conditions,
                }
                for label, values in required_focus_collections.items():
                    if not values or not all(value.strip() for value in values):
                        raise ValueError(f"Stage 6 research focus requires non-empty {label}")
                if not focus.evidence_quality or not focus.evidence_matrix or not focus.relationship_graph:
                    raise ValueError("Stage 6 research focus requires evidence quality, a matrix, and a relationship graph")
                if not focus.execution_implications or not focus.conclusion_change_conditions or not focus.research_evolution:
                    raise ValueError("Stage 6 research focus requires execution and continuity fields")
            elif self.research_inquiry.status != "no_focus":
                raise ValueError("a Stage 6 document without a focus must use the no-focus inquiry state")
        return self
