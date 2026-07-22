import {
  buildEvidenceMatrixPreviewRows,
  buildMarketTimelinePreviewRows,
  buildRelationshipGraphPreview,
  buildResearchPreviewModel,
  getReportFigureRendererKind,
  isRenderableFigureAnnotation,
} from '../src/features/reports/researchPreviewModel';
import type { ReportDocument, ReportFigure } from '../src/types/market';

function assert(condition: unknown, message: string) {
  if (!condition) throw new Error(message);
}

function document(overrides: Partial<ReportDocument> = {}): ReportDocument {
  return {
    document_version: 'report-document-v1',
    report_id: 'v7-test',
    pdf_format_version: 'daily-report-pdf-v7',
    title: 'Daily Market Intelligence Briefing',
    report_type: 'After Close',
    market_date: '2026-07-21',
    generated_at: '2026-07-21T21:00:00Z',
    data_cutoff: '2026-07-21T21:00:00Z',
    timezone: 'America/New_York',
    source_status: 'live',
    thesis: { posture: 'Selective', concise_thesis: 'Test', thesis_change: 'Baseline', confirmation_conditions: [], invalidation_conditions: [], confidence_label: 'Moderate', data_completeness: 1 },
    sections: [{ section_id: 'research-focus', number: 6, title: 'Dynamic Research Focus', purpose: 'Explain selection.', paragraphs: [], claim_ids: [], figure_ids: ['one', 'two'], table_ids: [], scenario_ids: [], security_ids: [], monitoring_condition_ids: [] }],
    claims: [], figures: [], tables: [], sources: [], scenarios: [], securities: [], monitoring_conditions: [], limitations: [],
    page_count_estimate: 18, figure_count: 2, approximate_word_count: 4000, previous_report_available: false,
    research_selection: { selected_candidate_id: 'theme:cybersecurity', materiality_threshold: 60, selected_because: ['Highest qualified score.'], omitted_candidate_count: 2, user_relevance_contribution: 15, missing_evidence: [], freshness_status: '2026-07-21' },
    research_focus: {
      candidate_id: 'theme:cybersecurity', subject: 'Cybersecurity', category: 'theme', direction: 'leading', priority_score: 74,
      classification_label: 'Leading',
      user_relevance: { tier: 'high', score: 100, exact_saved_group: true, saved_parent_group: false, saved_security_symbols: ['CRWD', 'PANW'], stale: false, rationale: [] },
      main_thesis: 'Grounded thesis.', counter_thesis: 'Grounded counter-thesis.', why_selected: ['Highest qualified score.'], key_evidence: [], confirmation_conditions: [], invalidation_conditions: [], prose_sections: {}, figure_ids: ['one', 'two'], affected_securities: [], taxonomy_chain: [], evidence_ids: [], limitations: [],
    },
    ...overrides,
  };
}

const focus = buildResearchPreviewModel(document());
assert(focus.state === 'focus', 'V7 focus renders the focus preview state');
assert(focus.state !== 'focus' || focus.subject === 'Cybersecurity', 'focus subject is preserved');
assert(focus.state !== 'focus' || focus.overlapCount === 2, 'saved overlap is counted');
assert(focus.state !== 'focus' || focus.figureCount === 2, 'research figures are counted');
assert(focus.state !== 'focus' || focus.navigationSectionId === 'research-focus', 'focus navigation resolves to the shared document section');

const noFocus = buildResearchPreviewModel(document({ research_focus: null, research_selection: { materiality_threshold: 60, selected_because: [], no_selection_reason: 'No qualified focus.', omitted_candidate_count: 3, user_relevance_contribution: 0, missing_evidence: ['breadth'], freshness_status: 'insufficient' } }));
assert(noFocus.state === 'no_focus' && noFocus.message === 'No qualified focus.', 'no-focus fallback uses the document decision');

const partial = buildResearchPreviewModel(document({ source_status: 'partial' }));
assert(partial.state === 'focus' && partial.partialData, 'partial source state is visible in the preview model');

const legacy = buildResearchPreviewModel(document({ pdf_format_version: 'daily-report-pdf-v6', research_focus: undefined, research_selection: undefined }));
assert(legacy.state === 'legacy', 'legacy report remains renderable without V7 research fields');

const baseFocus = document().research_focus!;
const stage6 = buildResearchPreviewModel(document({
  research_inquiry: {
    status: 'qualified',
    question: 'Why is Cybersecurity outperforming despite weak breadth?',
    executive_answer: 'Relative performance is persistent, but participation keeps the conclusion conditional.',
    evidence_ids: ['relative-performance', 'theme-breadth'],
  },
  research_focus: {
    ...baseFocus,
    question: 'Why is Cybersecurity outperforming despite weak breadth?',
    executive_answer: 'Relative performance is persistent, but participation keeps the conclusion conditional.',
    evidence_quality: {
      label: 'Medium', freshness: 'High', breadth: 'Low', participation: 'Medium', completeness: 'High', consistency: 'Medium',
      rationale: ['Current returns are complete; breadth is narrow.'], evidence_ids: ['relative-performance', 'theme-breadth'],
    },
    research_evolution: {
      yesterday: 'Leadership was emerging.', today: 'Leadership is established.', tomorrow: 'Breadth must improve.',
      what_changed: 'The one-month relative return strengthened.', research_follow_up: 'Recheck constituent breadth.',
      current_focus: 'Cybersecurity', status: 'strengthening', evidence_ids: ['relative-performance'],
    },
  },
}));
assert(stage6.state === 'focus' && stage6.question === 'Why is Cybersecurity outperforming despite weak breadth?', 'Stage 6 uses the explicit research question');
assert(stage6.state === 'focus' && stage6.executiveAnswer.startsWith('Relative performance'), 'Stage 6 uses the executive answer rather than generic thesis copy');
assert(stage6.state === 'focus' && stage6.evidenceQuality === 'Medium', 'evidence quality is presented as quality, not probability');
assert(stage6.state === 'focus' && stage6.evolutionSummary === 'The one-month relative return strengthened.', 'research evolution is exposed on the landing preview');

const inquiryOnly = buildResearchPreviewModel(document({
  research_focus: undefined,
  research_selection: undefined,
  research_inquiry: {
    status: 'no_focus',
    question: 'Did any research subject clear the evidence threshold?',
    executive_answer: 'No subject passed the materiality and figure gates.',
    evidence_ids: [],
  },
}));
assert(inquiryOnly.state === 'no_focus', 'a Stage 6 no-focus inquiry renders without requiring a V7 selection object');
assert(inquiryOnly.state !== 'no_focus' || inquiryOnly.executiveAnswer.includes('No subject passed'), 'the no-focus executive answer is preserved');

assert(getReportFigureRendererKind('research_chain') === 'research_chain', 'research-chain diagrams have an explicit renderer');
assert(getReportFigureRendererKind('sector_influence_map') === 'research_chain', 'sector-influence maps use the validated relationship renderer');
assert(getReportFigureRendererKind('relationship_map') === 'research_chain', 'relationship maps use the validated relationship renderer');
assert(getReportFigureRendererKind('evidence_matrix') === 'evidence_matrix', 'evidence matrices have an explicit renderer');
assert(getReportFigureRendererKind('leadership_matrix') === 'heatmap', 'leadership matrices use the explicit matrix renderer');
assert(getReportFigureRendererKind('research_timeline') === 'research_timeline', 'research timelines have an explicit renderer');
assert(getReportFigureRendererKind('relative_strength_flow') === 'relative_strength_flow', 'relative-strength flow uses its own renderer');
assert(getReportFigureRendererKind('research_priority_tree') === 'priority_comparison', 'research priority trees alias to the deterministic comparison renderer');
assert(getReportFigureRendererKind('decision_framework') === 'research_timeline', 'decision frameworks alias to the timeline renderer');
assert(getReportFigureRendererKind('research_evolution') === 'research_timeline', 'research-evolution figures use the decision/timeline renderer');
assert(getReportFigureRendererKind('future_chart_type') === 'generic', 'unknown future chart types use a safe structured fallback');

function figure(unit: string, points: Record<string, unknown>[], chartType = 'evidence_matrix'): ReportFigure {
  return {
    figure_id: `figure-${chartType}`, figure_number: 1, title: 'Test figure', subtitle: 'Test', question_answered: 'What does the evidence show?',
    chart_type: chartType, timeframe: 'Current report',
    data_series: [{ series_id: `series-${unit}`, label: 'Test', unit, points, source_id: 'source' }],
    source_ids: ['source'], observation: 'Observation', interpretation: 'Interpretation', confirmation_condition: 'Confirm', risk_condition: 'Risk',
    quality: { state: 'live', completeness: 1, freshness: 'current', transformation: 'test' },
  };
}

const evidenceFigure = figure('evidence_matrix', [
  { dimension: 'Relative performance', finding: 'Positive versus SPY.', stance: 'supports', implication: 'Leadership is market-relative.', evidence_ids: ['rs'] },
  { dimension: 'Unsupported', finding: 'Invalid stance is omitted.', stance: 'positive', implication: 'None.', evidence_ids: ['bad'] },
]);
const evidenceRows = buildEvidenceMatrixPreviewRows(document({ research_focus: { ...baseFocus, evidence_matrix: [] } }), evidenceFigure);
assert(evidenceRows.length === 1 && evidenceRows[0]?.stance === 'supports', 'figure-backed evidence matrices admit only supported stance values');

const graphFigure: ReportFigure = {
  ...figure('relationship_nodes', [
    { node_id: 'benchmark:spy', label: 'SPY', node_type: 'benchmark', depth: 0 },
    { node_id: 'theme:cyber', label: 'Cybersecurity', node_type: 'theme', depth: 1 },
    { node_id: 'security:crwd', label: 'CRWD', node_type: 'security', depth: 2 },
  ], 'research_chain'),
  data_series: [
    figure('relationship_nodes', [
      { node_id: 'benchmark:spy', label: 'SPY', node_type: 'benchmark', depth: 0 },
      { node_id: 'theme:cyber', label: 'Cybersecurity', node_type: 'theme', depth: 1 },
      { node_id: 'security:crwd', label: 'CRWD', node_type: 'security', depth: 2 },
    ]).data_series[0]!,
    figure('relationship_edges', [
      { relationship_id: 'benchmark-theme', source_node_id: 'benchmark:spy', target_node_id: 'theme:cyber', relationship_type: 'benchmark_relationship', label: 'Relative performance', mapping_source: 'frozen benchmark metric', structured_data: false, evidence_ids: ['rs'] },
      { relationship_id: 'causal', source_node_id: 'theme:cyber', target_node_id: 'security:crwd', relationship_type: 'causal_inference', label: 'Unsupported causality', mapping_source: 'narrative', structured_data: false, evidence_ids: ['bad'] },
      { relationship_id: 'supply-unstructured', source_node_id: 'theme:cyber', target_node_id: 'security:crwd', relationship_type: 'validated_supply_chain', label: 'Supplier', mapping_source: 'commentary', structured_data: false, evidence_ids: ['supply'] },
      { relationship_id: 'supply-structured', source_node_id: 'theme:cyber', target_node_id: 'security:crwd', relationship_type: 'validated_supply_chain', label: 'Supplier', mapping_source: 'structured relationship registry', structured_data: true, evidence_ids: ['supply-verified'] },
      { relationship_id: 'saved-overlap', source_node_id: 'security:crwd', target_node_id: 'theme:cyber', relationship_type: 'user_watchlist_overlap', label: 'Saved overlap', mapping_source: 'frozen research preferences', structured_data: false, evidence_ids: ['saved'] },
    ]).data_series[0]!,
  ],
};
const graph = buildRelationshipGraphPreview(document({ research_focus: { ...baseFocus, relationship_graph: null } }), graphFigure);
assert(graph.nodes.length === 3, 'validated graph nodes are read from figure data when no focus graph is supplied');
assert(graph.edges.length === 3, 'relationship preview omits unknown relationship types and unstructured supply-chain claims');
assert(graph.edges.some((edge) => edge.relationship_id === 'supply-structured'), 'structured evidence-linked supply-chain relationships remain renderable');
assert(graph.edges.some((edge) => edge.relationship_id === 'saved-overlap'), 'the backend user-watchlist relationship contract remains renderable');

const timelineFigure = figure('timeline', Array.from({ length: 12 }, (_, index) => ({
  market_date: `2026-07-${String(index + 1).padStart(2, '0')}`,
  regime: index > 8 ? 'Selective' : 'Constructive',
  breadth: 40 + index,
  risk: 60 - index,
  research_focus: index === 11 ? 'Cybersecurity' : 'No standalone focus',
})), 'research_timeline');
const timelineRows = buildMarketTimelinePreviewRows(document(), timelineFigure);
assert(timelineRows.length === 10, 'the research timeline is capped at the latest ten compatible reports');
assert(timelineRows[0]?.market_date === '2026-07-03' && timelineRows[9]?.research_focus === 'Cybersecurity', 'the research timeline preserves chronology and focus continuity');

const annotatedFigure = { ...figure('price', [{ value: 100 }, { value: 102 }], 'stock_setup'), as_of: '2026-07-21' };
assert(isRenderableFigureAnnotation({ annotation_id: 'support', annotation_type: 'support', label: 'Support', evidence_id: 'support-evidence', freshness: 'current', value: 100, point_index: 0 }, annotatedFigure), 'validated observed annotations remain renderable');
assert(!isRenderableFigureAnnotation({ annotation_id: 'future', annotation_type: 'confirmation', label: 'Future confirmation', evidence_id: 'future-evidence', freshness: 'current', value: 110, point_index: 1, date: '2026-07-22' }, annotatedFigure), 'annotations after the figure as-of date are never rendered');
assert(!isRenderableFigureAnnotation({ annotation_id: 'unsupported', annotation_type: 'future_arrow', label: 'Forecast', evidence_id: 'forecast-evidence', freshness: 'current', value: 110, point_index: 1 }, annotatedFigure), 'unsupported speculative annotation types are never rendered');
