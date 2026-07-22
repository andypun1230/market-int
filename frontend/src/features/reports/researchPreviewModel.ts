import type {
  ReportDocument,
  ReportFigure,
  ReportFigureAnnotation,
  ReportMarketTimelineEntry,
  ReportResearchEvidenceMatrixRow,
  ReportResearchRelationshipEdge,
  ReportResearchRelationshipGraph,
  ReportResearchRelationshipNode,
} from '@/types/market';

export type ReportFigureRendererKind =
  | 'evidence_matrix'
  | 'generic'
  | 'heatmap'
  | 'line'
  | 'market_timeline'
  | 'priority_comparison'
  | 'relative_strength_flow'
  | 'research_chain'
  | 'research_timeline'
  | 'rotation';

const LINE_CHART_TYPES = new Set([
  'breadth_history',
  'breadth_internals',
  'breadth_time_series',
  'line',
  'normalized_multi_asset',
  'price_volume',
  'price_with_volume',
  'ratio',
  'relative_strength',
  'return_profile',
  'risk_history',
  'stock_setup',
]);

const VALID_RESEARCH_RELATIONSHIPS = new Set([
  'benchmark_relationship',
  'relative_performance',
  'sector_hierarchy',
  'theme_hierarchy',
  'validated_supply_chain',
  'validated_taxonomy',
  'user_watchlist_overlap',
]);

const VALID_FIGURE_ANNOTATIONS = new Set([
  'breakout',
  'confirmation',
  'confirmation_arrow',
  'current_thesis',
  'ema',
  'failed_breakout',
  'gap',
  'invalidation',
  'ma',
  'moving_average_label',
  'pivot',
  'previous_report',
  'previous_report_marker',
  'recent_high',
  'recent_low',
  'resistance',
  'risk',
  'support',
  'trendline',
  'volume_expansion',
]);

export type ResearchPreviewModel =
  | { state: 'legacy' }
  | {
      state: 'no_focus';
      executiveAnswer: string;
      message: string;
      partialData: boolean;
      question: string;
    }
  | {
      state: 'focus';
      badge: string;
      evidenceQuality: 'High' | 'Medium' | 'Low' | null;
      evolutionSummary: string | null;
      executiveAnswer: string;
      figureCount: number;
      navigationSectionId: string | null;
      overlapCount: number;
      partialData: boolean;
      personalized: boolean;
      question: string;
      subject: string;
      whySelected: string;
    };

export function buildResearchPreviewModel(document: ReportDocument | null | undefined): ResearchPreviewModel {
  if (!document || (!document.research_focus && !document.research_selection && !document.research_inquiry)) {
    return { state: 'legacy' };
  }
  const partialData = ['partial', 'mixed', 'stale', 'unavailable'].includes(document.source_status);
  const focus = document.research_focus;
  if (!focus) {
    const message = document.research_selection?.no_selection_reason
      ?? 'No standalone research subject met the evidence and materiality threshold for this report.';
    return {
      state: 'no_focus',
      executiveAnswer: document.research_inquiry?.executive_answer ?? message,
      message,
      partialData,
      question: document.research_inquiry?.question ?? 'Did any research subject clear the evidence threshold?',
    };
  }
  const inquiry = document.research_inquiry?.status === 'qualified' ? document.research_inquiry : null;
  const savedSecurityCount = focus.user_relevance.saved_security_symbols.length;
  const overlapCount = savedSecurityCount || Number(focus.user_relevance.exact_saved_group) + Number(focus.user_relevance.saved_parent_group);
  return {
    state: 'focus',
    badge: focus.classification_label,
    evidenceQuality: focus.evidence_quality?.label ?? null,
    evolutionSummary: focus.research_evolution?.what_changed ?? null,
    executiveAnswer: focus.executive_answer ?? inquiry?.executive_answer ?? focus.main_thesis,
    figureCount: focus.figure_ids.length,
    navigationSectionId: document.sections.some((section) => section.section_id === 'research-focus') ? 'research-focus' : null,
    overlapCount,
    partialData,
    personalized: focus.user_relevance.score > 0 && !focus.user_relevance.stale,
    question: focus.question ?? inquiry?.question ?? `Why is ${focus.subject} the highest-priority research subject?`,
    subject: focus.subject,
    whySelected: focus.why_selected[0] ?? focus.main_thesis,
  };
}

export function getReportFigureRendererKind(chartType: string): ReportFigureRendererKind {
  if (chartType === 'heatmap' || chartType === 'leadership_matrix') return 'heatmap';
  if (chartType === 'rotation') return 'rotation';
  if (chartType === 'priority_comparison' || chartType === 'research_priority_tree') return 'priority_comparison';
  if (chartType === 'market_timeline') return 'market_timeline';
  if (chartType === 'evidence_matrix') return 'evidence_matrix';
  if (chartType === 'research_timeline' || chartType === 'decision_framework' || chartType === 'research_evolution') return 'research_timeline';
  if (chartType === 'research_chain' || chartType === 'relationship_map' || chartType === 'sector_influence_map') return 'research_chain';
  if (chartType === 'relative_strength_flow') return 'relative_strength_flow';
  if (LINE_CHART_TYPES.has(chartType)) return 'line';
  return 'generic';
}

export function buildEvidenceMatrixPreviewRows(
  document: ReportDocument,
  figure: ReportFigure,
): ReportResearchEvidenceMatrixRow[] {
  const focusRows = document.research_focus?.evidence_matrix ?? [];
  if (focusRows.length) return focusRows;
  return figure.data_series
    .flatMap((series) => series.points)
    .map(asEvidenceMatrixRow)
    .filter((row): row is ReportResearchEvidenceMatrixRow => row !== null);
}

export function buildMarketTimelinePreviewRows(
  document: ReportDocument,
  figure: ReportFigure,
): ReportMarketTimelineEntry[] {
  const figureRows = figure.data_series
    .flatMap((series) => series.points)
    .map(asMarketTimelineEntry)
    .filter((row): row is ReportMarketTimelineEntry => row !== null);
  return (figureRows.length ? figureRows : document.market_timeline ?? []).slice(-10);
}

export function buildRelationshipGraphPreview(
  document: ReportDocument,
  figure: ReportFigure,
): ReportResearchRelationshipGraph {
  const supplied = document.research_focus?.relationship_graph;
  const nodes = (supplied?.nodes.length ? supplied.nodes : figure.data_series
    .filter((series) => series.unit === 'relationship_nodes')
    .flatMap((series) => series.points)
    .map(asRelationshipNode)
    .filter((node): node is ReportResearchRelationshipNode => node !== null));
  const nodeIds = new Set(nodes.map((node) => node.node_id));
  const edges = (supplied?.edges.length ? supplied.edges : figure.data_series
    .filter((series) => series.unit === 'relationship_edges')
    .flatMap((series) => series.points)
    .map(asRelationshipEdge)
    .filter((edge): edge is ReportResearchRelationshipEdge => edge !== null))
    .filter((edge) => nodeIds.has(edge.source_node_id) && nodeIds.has(edge.target_node_id))
    .filter(isRenderableResearchRelationship);
  return { nodes, edges };
}

export function isRenderableResearchRelationship(edge: ReportResearchRelationshipEdge) {
  if (!VALID_RESEARCH_RELATIONSHIPS.has(edge.relationship_type)) return false;
  if (!edge.evidence_ids.length || !edge.mapping_source.trim()) return false;
  if (edge.relationship_type === 'validated_supply_chain') return edge.structured_data;
  return true;
}

export function isRenderableFigureAnnotation(annotation: ReportFigureAnnotation, figure: ReportFigure) {
  if (!VALID_FIGURE_ANNOTATIONS.has(annotation.annotation_type) || !annotation.evidence_id.trim()) return false;
  const maximumPointCount = Math.max(0, ...figure.data_series.map((series) => series.points.length));
  if (annotation.point_index !== null && annotation.point_index !== undefined) {
    if (!Number.isInteger(annotation.point_index) || annotation.point_index < 0 || annotation.point_index >= maximumPointCount) return false;
  }
  if (annotation.date && figure.as_of && annotation.date.slice(0, 10) > figure.as_of.slice(0, 10)) return false;
  return true;
}

function asEvidenceMatrixRow(point: Record<string, unknown>): ReportResearchEvidenceMatrixRow | null {
  const stance = point.stance;
  if (stance !== 'supports' && stance !== 'neutral' && stance !== 'contradicts') return null;
  const dimension = stringValue(point.dimension);
  const finding = stringValue(point.finding);
  const implication = stringValue(point.implication);
  if (!dimension || !finding || !implication) return null;
  return {
    dimension,
    finding,
    stance,
    implication,
    evidence_ids: stringArray(point.evidence_ids),
  };
}

function asRelationshipNode(point: Record<string, unknown>): ReportResearchRelationshipNode | null {
  const nodeId = stringValue(point.node_id);
  const label = stringValue(point.label);
  const nodeType = stringValue(point.node_type);
  const depth = numberValue(point.depth);
  if (!nodeId || !label || !nodeType || depth === null) return null;
  return { node_id: nodeId, label, node_type: nodeType, depth };
}

function asRelationshipEdge(point: Record<string, unknown>): ReportResearchRelationshipEdge | null {
  const relationshipId = stringValue(point.relationship_id);
  const sourceNodeId = stringValue(point.source_node_id);
  const targetNodeId = stringValue(point.target_node_id);
  const relationshipType = stringValue(point.relationship_type);
  const label = stringValue(point.label);
  const mappingSource = stringValue(point.mapping_source);
  if (!relationshipId || !sourceNodeId || !targetNodeId || !relationshipType || !label || !mappingSource) return null;
  return {
    relationship_id: relationshipId,
    source_node_id: sourceNodeId,
    target_node_id: targetNodeId,
    relationship_type: relationshipType,
    label,
    mapping_source: mappingSource,
    structured_data: point.structured_data === true,
    evidence_ids: stringArray(point.evidence_ids),
  };
}

function asMarketTimelineEntry(point: Record<string, unknown>): ReportMarketTimelineEntry | null {
  const marketDate = stringValue(point.market_date);
  if (!marketDate) return null;
  return {
    market_date: marketDate,
    regime: optionalString(point.regime),
    market_health: numberValue(point.market_health),
    breadth: numberValue(point.breadth),
    leadership_concentration: numberValue(point.leadership_concentration),
    risk: numberValue(point.risk),
    volatility_state: optionalString(point.volatility_state),
    primary_leader: optionalString(point.primary_leader),
    primary_laggard: optionalString(point.primary_laggard),
    research_focus: optionalString(point.research_focus),
  };
}

function stringValue(value: unknown) {
  return typeof value === 'string' && value.trim() ? value.trim() : null;
}

function numberValue(value: unknown) {
  const parsed = typeof value === 'number'
    ? value
    : typeof value === 'string' && value.trim()
      ? Number(value)
      : Number.NaN;
  return Number.isFinite(parsed) ? parsed : null;
}

function optionalString(value: unknown) {
  return typeof value === 'string' && value.trim() ? value.trim() : null;
}

function stringArray(value: unknown) {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string' && Boolean(item.trim())) : [];
}
