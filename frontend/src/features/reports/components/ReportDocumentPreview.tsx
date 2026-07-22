import { useMemo, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import Svg, { Circle, Line, Polyline, Rect, Text as SvgText } from 'react-native-svg';

import { StatusBadge } from '@/components/ui/StatusBadge';
import { Spacing, Theme } from '@/constants/theme';
import { AskCopilotButton } from '@/features/copilot/components/AskCopilotButton';
import { createCopilotContext } from '@/features/copilot/context/buildScreenContext';
import {
  buildEvidenceMatrixPreviewRows,
  buildMarketTimelinePreviewRows,
  buildRelationshipGraphPreview,
  buildResearchPreviewModel,
  getReportFigureRendererKind,
  isRenderableFigureAnnotation,
} from '@/features/reports/researchPreviewModel';
import type { ReportDocument, ReportFigure, ReportResearchSecuritySignal } from '@/types/market';

export function ReportDocumentPreview({
  document,
  initialSectionId,
}: {
  document: ReportDocument;
  initialSectionId?: string;
}) {
  const initialId = document.sections.some((item) => item.section_id === initialSectionId)
    ? initialSectionId!
    : document.sections[0]?.section_id ?? 'cover';
  const selectionKey = `${document.report_id}:${initialSectionId ?? 'default'}`;
  const [selection, setSelection] = useState({ key: selectionKey, sectionId: initialId });
  const activeId = selection.key === selectionKey ? selection.sectionId : initialId;
  const section = document.sections.find((item) => item.section_id === activeId) ?? document.sections[0];
  const figures = useMemo(() => new Map(document.figures.map((item) => [item.figure_id, item])), [document.figures]);
  const claims = useMemo(() => new Map(document.claims.map((item) => [item.claim_id, item])), [document.claims]);
  const researchPreview = useMemo(() => buildResearchPreviewModel(document), [document]);
  if (!section) return null;
  const sectionQuestion = section.question ?? fallbackSectionQuestion(section.section_id, section.title, document);
  const copilotContext = createCopilotContext({
    payload: {
      claimIds: section.claim_ids,
      marketDate: document.market_date,
      reportId: document.report_id,
      researchFocus: document.research_focus,
      sectionId: section.section_id,
      sectionPurpose: section.purpose,
      thesis: document.thesis,
    },
    routeName: '/report',
    screenTitle: `${document.title} · ${section.title}`,
    screenType: 'report',
    sourceState: document.source_status,
  });
  const attachedSecurityFigureIds = new Set(section.security_ids.flatMap((securityId) => {
    const figureId = document.securities.find((item) => item.security_id === securityId)?.figure_id;
    return figureId ? [figureId] : [];
  }));

  return (
    <View style={styles.stack}>
      <AskCopilotButton
        context={copilotContext}
        prompt={section.section_id === 'research-focus'
          ? 'Explain this Research Focus, why it was selected, and what would invalidate it.'
          : `Explain the ${section.title} section and its most important trade-off.`}
      />
      <View style={styles.cover}>
        <View style={styles.metaRow}>
          <Text style={styles.eyebrow}>INSTITUTIONAL MARKET RESEARCH</Text>
          <StatusBadge label={document.source_status} tone={sourceTone(document.source_status)} />
        </View>
        <Text style={styles.title}>{document.title}</Text>
        <Text style={styles.meta}>{document.report_type} · Market date {document.market_date}</Text>
        {researchPreview.state === 'focus' ? (
          <View style={styles.focusBadge}>
            <View style={styles.rowHeader}>
              <Text style={styles.label}>RESEARCH QUESTION</Text>
              {researchPreview.evidenceQuality ? <StatusBadge label={`${researchPreview.evidenceQuality} evidence quality`} tone={evidenceQualityTone(researchPreview.evidenceQuality)} /> : null}
            </View>
            <Text style={styles.focusBadgeTitle}>{researchPreview.question}</Text>
            <Text style={styles.muted}>{researchPreview.executiveAnswer}</Text>
            <Text style={styles.sourceText}>{researchPreview.subject} · {researchPreview.badge} · {researchPreview.overlapCount} saved-item overlap{researchPreview.overlapCount === 1 ? '' : 's'} · {researchPreview.figureCount} figures{researchPreview.partialData ? ' · partial data' : ''}</Text>
          </View>
        ) : researchPreview.state === 'no_focus' ? <View style={styles.focusBadge}><Text style={styles.label}>RESEARCH QUESTION</Text><Text style={styles.focusBadgeTitle}>{researchPreview.question}</Text><Text style={styles.muted}>{researchPreview.executiveAnswer}</Text></View> : null}
        <Text style={styles.posture}>{document.thesis.posture}</Text>
        <Text style={styles.thesis}>{document.thesis.concise_thesis}</Text>
        <View style={styles.summaryRow}>
          <SummaryMetric label="Confidence" value={document.thesis.confidence_label} />
          <SummaryMetric label="Completeness" value={`${Math.round(document.thesis.data_completeness * 100)}%`} />
          <SummaryMetric label="Figures" value={String(document.figure_count)} />
          <SummaryMetric label="Pages" value={`~${document.page_count_estimate}`} />
        </View>
      </View>

      <ScrollView contentContainerStyle={styles.contents} horizontal showsHorizontalScrollIndicator={false}>
        {document.sections.map((item) => (
          <Pressable
            accessibilityRole="tab"
            accessibilityState={{ selected: item.section_id === section.section_id }}
            key={item.section_id}
            onPress={() => setSelection({ key: selectionKey, sectionId: item.section_id })}
            style={({ pressed }) => [styles.contentsButton, item.section_id === section.section_id && styles.contentsButtonActive, pressed && styles.pressed]}>
            <Text style={[styles.contentsNumber, item.section_id === section.section_id && styles.contentsTextActive]}>{String(item.number).padStart(2, '0')}</Text>
            <Text numberOfLines={1} style={[styles.contentsText, item.section_id === section.section_id && styles.contentsTextActive]}>{item.title}</Text>
          </Pressable>
        ))}
      </ScrollView>

      <View style={styles.section}>
        <Text style={styles.sectionNumber}>SECTION {String(section.number).padStart(2, '0')}</Text>
        <Text style={styles.sectionTitle}>{section.title}</Text>
        <View style={styles.sectionQuestion}><Text style={styles.label}>QUESTION</Text><Text style={styles.sectionQuestionText}>{sectionQuestion}</Text></View>
        <Text style={styles.sectionPurpose}>{section.purpose}</Text>
        {section.section_id === 'research-focus' && document.research_focus ? <ResearchFocusSummary document={document} /> : null}
        {section.paragraphs.map((paragraph, index) => <Text key={`${section.section_id}-p-${index}`} style={styles.body}>{paragraph}</Text>)}

        {section.claim_ids.map((claimId) => {
          const claim = claims.get(claimId);
          return claim ? (
            <View key={claimId} style={styles.claim}>
              <Text style={styles.label}>SUPPORTED CLAIM · {claim.confidence.toUpperCase()} CONFIDENCE</Text>
              <Text style={styles.claimText}>{claim.statement}</Text>
              <LabeledText label="Interpretation" value={claim.interpretation} />
              <LabeledText label="Trader implication" value={claim.trader_implication} />
            </View>
          ) : null;
        })}

        {section.table_ids.map((tableId) => {
          const table = document.tables.find((item) => item.table_id === tableId);
          return table ? <DocumentTable key={tableId} table={table} /> : null;
        })}

        {section.figure_ids.map((figureId) => {
          if (attachedSecurityFigureIds.has(figureId)) return null;
          const figure = figures.get(figureId);
          return figure ? <ResearchFigure document={document} key={figureId} figure={figure} /> : null;
        })}

        {section.scenario_ids.length ? <ScenarioList document={document} ids={section.scenario_ids} /> : null}
        {section.security_ids.length ? <SecurityList document={document} figures={figures} ids={section.security_ids} /> : null}
        {section.monitoring_condition_ids.length ? <MonitoringList document={document} ids={section.monitoring_condition_ids} /> : null}
        {section.quality_note ? <LabeledText label="Data limitations" value={section.quality_note} /> : null}
      </View>

      <View style={styles.provenance}>
        <Text style={styles.label}>REPORT ID</Text>
        <Text style={styles.sourceText}>{document.report_id}</Text>
        <Text style={styles.sourceText}>{document.pdf_format_version} · Cutoff {document.data_cutoff}</Text>
      </View>
    </View>
  );
}

function ResearchFigure({ document, figure }: { document: ReportDocument; figure: ReportFigure }) {
  return (
    <View style={styles.figure}>
      <Text style={styles.figureTitle}>Figure {figure.figure_number}. {figure.title}</Text>
      <Text style={styles.figureMeta}>{figure.subtitle} · {figure.timeframe} · As of {figure.as_of ?? 'unavailable'}</Text>
      <View style={styles.figureQuestion}><Text style={styles.label}>QUESTION ANSWERED</Text><Text style={styles.figureQuestionText}>{figure.question_answered}</Text></View>
      <FigureGraphic document={document} figure={figure} />
      <LabeledText label="Observation" value={figure.observation} />
      <LabeledText label="Interpretation" value={figure.interpretation} />
      <View style={styles.conditionRow}>
        <View style={styles.condition}><Text style={styles.confirmLabel}>CONFIRMATION</Text><Text style={styles.conditionText}>{figure.confirmation_condition}</Text></View>
        <View style={styles.condition}><Text style={styles.riskLabel}>RISK</Text><Text style={styles.conditionText}>{figure.risk_condition}</Text></View>
      </View>
      <Text style={styles.sourceText}>Source: {figure.source_ids.join(', ')} · {figure.quality.state} · {Math.round(figure.quality.completeness * 100)}% complete</Text>
    </View>
  );
}

function FigureGraphic({ document, figure }: { document: ReportDocument; figure: ReportFigure }) {
  const renderer = getReportFigureRendererKind(figure.chart_type);
  if (renderer === 'heatmap') return <Heatmap figure={figure} />;
  if (renderer === 'rotation') return <RotationChart figure={figure} />;
  if (renderer === 'priority_comparison') return <PriorityComparison figure={figure} />;
  if (renderer === 'market_timeline') return <MarketTimeline document={document} figure={figure} />;
  if (renderer === 'evidence_matrix') return <EvidenceMatrixGraphic document={document} figure={figure} />;
  if (renderer === 'research_timeline') return <ResearchTimelineGraphic document={document} figure={figure} />;
  if (renderer === 'research_chain') return <ResearchChainGraphic document={document} figure={figure} />;
  if (renderer === 'relative_strength_flow') return <RelativeStrengthFlowGraphic figure={figure} />;
  if (renderer === 'line') return <LineFigure figure={figure} />;
  return <GenericFigureFallback figure={figure} />;
}

function LineFigure({ figure }: { figure: ReportFigure }) {
  const width = 720;
  const height = 250;
  const plot = { left: 40, right: 12, top: 18, bottom: 24 };
  const series = figure.data_series.filter((item) => item.unit !== 'shares').slice(0, 6);
  const values = series.flatMap((item) => item.points.map((point) => numeric(point.value))).filter((value): value is number => value !== null);
  if (values.length < 2) return <UnavailableFigure />;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = Math.max(max - min, Math.abs(max) * 0.02, 0.01);
  const colors = [Theme.colors.accent, '#7A5AF8', Theme.colors.warning, Theme.colors.success, Theme.colors.danger, Theme.colors.textMuted];
  return (
    <View style={styles.chart}>
      <Svg height="100%" preserveAspectRatio="none" viewBox={`0 0 ${width} ${height}`} width="100%">
        {[0, 1, 2, 3, 4].map((line) => <Line key={line} stroke={Theme.colors.border} strokeWidth="1" x1={plot.left} x2={width - plot.right} y1={plot.top + ((height - plot.top - plot.bottom) * line) / 4} y2={plot.top + ((height - plot.top - plot.bottom) * line) / 4} />)}
        {series.map((item, seriesIndex) => {
          const points = item.points.map((point) => numeric(point.value)).map((value, index) => value === null ? null : `${plot.left + (index / Math.max(1, item.points.length - 1)) * (width - plot.left - plot.right)},${plot.top + (1 - (value - min) / range) * (height - plot.top - plot.bottom)}`).filter(Boolean).join(' ');
          return <Polyline fill="none" key={item.series_id} points={points} stroke={item.color ?? colors[seriesIndex]} strokeLinecap="round" strokeLinejoin="round" strokeWidth={seriesIndex === 0 ? 2.6 : 1.7} />;
        })}
        {(figure.reference_lines ?? []).map((reference, index) => {
          const value = numeric(reference.value);
          if (value === null || value < min || value > max || isSuppressedFreshness(reference.freshness)) return null;
          const y = plot.top + (1 - (value - min) / range) * (height - plot.top - plot.bottom);
          const color = annotationColor(reference.annotation_type ?? reference.label ?? 'reference');
          return <Svg key={`reference-${index}`}><Line stroke={color} strokeDasharray="6 4" strokeWidth="1.5" x1={plot.left} x2={width - plot.right} y1={y} y2={y} />{reference.label ? <SvgText fill={color} fontSize="9" fontWeight="700" textAnchor="end" x={width - plot.right - 2} y={Math.max(11, y - 4)}>{reference.label}</SvgText> : null}</Svg>;
        })}
        {(figure.annotations ?? []).filter((annotation) => isRenderableFigureAnnotation(annotation, figure)).map((annotation, annotationIndex) => {
          const value = numeric(annotation.value);
          const pointIndex = annotation.point_index;
          if (value === null || value < min || value > max || isSuppressedFreshness(annotation.freshness)) return null;
          const color = annotationColor(annotation.annotation_type);
          const baseY = plot.top + (1 - (value - min) / range) * (height - plot.top - plot.bottom);
          if (pointIndex === null || pointIndex === undefined) {
            const labelY = Math.max(11, Math.min(height - plot.bottom - 2, baseY - 4 - (annotationIndex % 2) * 11));
            return <Svg key={annotation.annotation_id}><Line stroke={color} strokeDasharray="5 4" strokeWidth="1.4" x1={plot.left} x2={width - plot.right} y1={baseY} y2={baseY} /><SvgText fill={color} fontSize="9" fontWeight="700" textAnchor="end" x={width - plot.right - 2} y={labelY}>{annotation.label}</SvgText></Svg>;
          }
          const longestSeries = Math.max(...series.map((item) => item.points.length), 1);
          const x = plot.left + (pointIndex / Math.max(1, longestSeries - 1)) * (width - plot.left - plot.right);
          const labelX = x > width - 150 ? x - 7 : x + 7;
          const labelY = Math.max(12, Math.min(height - plot.bottom - 2, baseY - 7 - (annotationIndex % 3) * 11));
          return <Svg key={annotation.annotation_id}><Circle cx={x} cy={baseY} fill={color} r="4" /><SvgText fill={color} fontSize="10" fontWeight="700" textAnchor={x > width - 150 ? 'end' : 'start'} x={labelX} y={labelY}>{annotation.label}</SvgText></Svg>;
        })}
      </Svg>
      <View style={styles.legend}>{series.map((item, index) => <View key={item.series_id} style={styles.legendItem}><View style={[styles.legendLine, { backgroundColor: item.color ?? colors[index] }]} /><Text style={styles.legendText}>{item.label}</Text></View>)}</View>
    </View>
  );
}

function PriorityComparison({ figure }: { figure: ReportFigure }) {
  const rows = figure.data_series[0]?.points ?? [];
  const threshold = numeric((figure.reference_lines ?? []).find((item) => item.label === 'Materiality threshold')?.value) ?? 60;
  return <View style={styles.priorityChart}>{rows.map((row, index) => { const value = numeric(row.value) ?? 0; const selected = Boolean(row.selected); return <View key={`${String(row.label)}-${index}`} style={styles.priorityRow}><Text numberOfLines={1} style={[styles.priorityLabel, selected && styles.priorityLabelSelected]}>{String(row.label ?? '')}</Text><View style={styles.priorityTrack}><View style={[styles.priorityThreshold, { left: `${threshold}%` }]} /><View style={[styles.priorityBar, { width: `${Math.max(0, Math.min(100, value))}%` }, selected && styles.priorityBarSelected]} /></View><Text style={styles.priorityValue}>{value.toFixed(1)}</Text></View>; })}</View>;
}

function MarketTimeline({ document, figure }: { document: ReportDocument; figure: ReportFigure }) {
  const rows = buildMarketTimelinePreviewRows(document, figure);
  if (!rows.length) return <UnavailableFigure />;
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false}>
      <View style={styles.timelineCards}>
        {rows.map((row, index) => (
          <View key={`${String(row.market_date)}-${index}`} style={styles.timelineCard}>
            <Text style={styles.timelineDate}>{formatCell(row.market_date)}</Text>
            <Text numberOfLines={2} style={styles.timelineRegime}>{formatCell(row.regime)}</Text>
            <TimelineMetric label="Breadth" value={row.breadth} />
            <TimelineMetric label="Leadership" value={row.primary_leader ?? row.leadership_concentration} />
            <TimelineMetric label="Risk" value={row.risk} />
            <TimelineMetric label="Volatility" value={row.volatility_state} />
            <TimelineMetric label="Research focus" value={row.research_focus} />
          </View>
        ))}
      </View>
    </ScrollView>
  );
}

function TimelineMetric({ label, value }: { label: string; value: unknown }) {
  return <View style={styles.timelineMetric}><Text style={styles.timelineMetricLabel}>{label}</Text><Text numberOfLines={2} style={styles.timelineMetricValue}>{formatCell(value)}</Text></View>;
}

function RotationChart({ figure }: { figure: ReportFigure }) {
  const width = 720;
  const height = 270;
  const points = figure.data_series.flatMap((item) => item.points.flatMap((point) => [numeric(point.x), numeric(point.y)])).filter((value): value is number => value !== null);
  if (!points.length) return <UnavailableFigure />;
  const distance = Math.max(5, ...points.map((value) => Math.abs(value - 100))) * 1.12;
  const low = 100 - distance;
  const span = distance * 2;
  const colors = [Theme.colors.accent, '#7A5AF8', Theme.colors.warning, Theme.colors.success, Theme.colors.danger, '#475467'];
  const mapX = (value: number) => 35 + ((value - low) / span) * 650;
  const mapY = (value: number) => 18 + (1 - (value - low) / span) * 220;
  return (
    <View style={styles.rotationChart}>
      <Svg height="100%" viewBox={`0 0 ${width} ${height}`} width="100%">
        <Rect fill="#ECFDF3" height="110" width="325" x="360" y="18" /><Rect fill="#EFF8FF" height="110" width="325" x="35" y="18" />
        <Rect fill="#FFF4ED" height="110" width="325" x="360" y="128" /><Rect fill="#FEF3F2" height="110" width="325" x="35" y="128" />
        <Line stroke={Theme.colors.border} x1="360" x2="360" y1="18" y2="238" /><Line stroke={Theme.colors.border} x1="35" x2="685" y1="128" y2="128" />
        <SvgText fill={Theme.colors.textMuted} fontSize="11" fontWeight="700" x="43" y="34">IMPROVING</SvgText><SvgText fill={Theme.colors.textMuted} fontSize="11" fontWeight="700" textAnchor="end" x="677" y="34">LEADING</SvgText>
        <SvgText fill={Theme.colors.textMuted} fontSize="11" fontWeight="700" x="43" y="229">LAGGING</SvgText><SvgText fill={Theme.colors.textMuted} fontSize="11" fontWeight="700" textAnchor="end" x="677" y="229">WEAKENING</SvgText>
        {figure.data_series.slice(0, 8).map((item, index) => {
          const valid = item.points.map((point) => ({ x: numeric(point.x), y: numeric(point.y) })).filter((point): point is { x: number; y: number } => point.x !== null && point.y !== null);
          const coordinates = valid.map((point) => `${mapX(point.x)},${mapY(point.y)}`).join(' ');
          const latest = valid[valid.length - 1];
          return <Svg key={item.series_id}><Polyline fill="none" points={coordinates} stroke={colors[index % colors.length]} strokeWidth="2" />{latest ? <Circle cx={mapX(latest.x)} cy={mapY(latest.y)} fill={colors[index % colors.length]} r="4" /> : null}{latest ? <SvgText fill={Theme.colors.text} fontSize="10" fontWeight="700" x={mapX(latest.x) + 7} y={mapY(latest.y) + 3}>{item.label}</SvgText> : null}</Svg>;
        })}
      </Svg>
    </View>
  );
}

function Heatmap({ figure }: { figure: ReportFigure }) {
  const rows = figure.data_series[0]?.points ?? [];
  const periods = ['1d', '1w', '1m', '3m', '6m', '1y'].filter((period) => rows.some((row) => row[period] !== null && row[period] !== undefined));
  return <ScrollView horizontal><View style={styles.heatmap}><View style={styles.heatRow}><Text style={styles.heatLabel}>Sector</Text>{periods.map((period) => <Text key={period} style={styles.heatCellHeader}>{period.toUpperCase()}</Text>)}</View>{rows.map((row, index) => <View key={`${String(row.label)}-${index}`} style={styles.heatRow}><Text numberOfLines={1} style={styles.heatLabel}>{String(row.label ?? '')}</Text>{periods.map((period) => { const value = numeric(row[period]); return <View key={period} style={[styles.heatCell, { backgroundColor: heatColor(value) }]}><Text style={styles.heatValue}>{value === null ? '—' : `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`}</Text></View>; })}</View>)}</View></ScrollView>;
}

function EvidenceMatrixGraphic({ document, figure }: { document: ReportDocument; figure: ReportFigure }) {
  const rows = buildEvidenceMatrixPreviewRows(document, figure);
  if (!rows.length) return <UnavailableFigure />;
  const columns = [
    { label: 'Supports', stance: 'supports' as const, tone: styles.evidenceSupports },
    { label: 'Neutral', stance: 'neutral' as const, tone: styles.evidenceNeutral },
    { label: 'Contradicts', stance: 'contradicts' as const, tone: styles.evidenceContradicts },
  ];
  return (
    <View style={styles.evidenceMatrix}>
      {columns.map((column) => {
        const items = rows.filter((item) => item.stance === column.stance);
        return (
          <View key={column.stance} style={[styles.evidenceColumn, column.tone]}>
            <Text style={styles.evidenceColumnTitle}>{column.label.toUpperCase()} · {items.length}</Text>
            {items.length ? items.map((item, index) => (
              <View key={`${item.dimension}-${index}`} style={styles.evidenceItem}>
                <Text style={styles.evidenceDimension}>{item.dimension}</Text>
                <Text style={styles.evidenceFinding}>{item.finding}</Text>
                <Text style={styles.evidenceImplication}>{item.implication}</Text>
              </View>
            )) : <Text style={styles.muted}>No validated evidence in this stance.</Text>}
          </View>
        );
      })}
    </View>
  );
}

function ResearchTimelineGraphic({ document, figure }: { document: ReportDocument; figure: ReportFigure }) {
  if (figure.chart_type === 'research_timeline') return <MarketTimeline document={document} figure={figure} />;
  const evolution = document.research_focus?.research_evolution;
  const figurePhases = figure.data_series.flatMap((series) => series.points).map((point, index) => ({
    label: String(point.stage ?? point.phase ?? point.label ?? `Step ${index + 1}`),
    text: String(point.text ?? point.finding ?? point.value ?? point.detail ?? ''),
    tone: String(point.tone ?? 'neutral'),
  })).filter((item) => item.text);
  const phases = figure.chart_type === 'decision_framework' && figurePhases.length
    ? figurePhases
    : evolution
      ? [
        { label: 'Yesterday', text: evolution.yesterday },
        { label: 'Today', text: evolution.today },
        { label: 'Tomorrow', text: evolution.tomorrow },
      ]
      : figurePhases;
  if (!phases.length) return <UnavailableFigure />;
  return (
    <View style={styles.researchTimeline}>
      <View style={styles.researchTimelinePhases}>
        {phases.map((phase, index) => (
          <View key={`${phase.label}-${index}`} style={styles.researchTimelineStep}>
            <Text style={styles.researchTimelineLabel}>{phase.label.toUpperCase()}</Text>
            <Text style={styles.researchTimelineText}>{phase.text}</Text>
          </View>
        ))}
      </View>
      {evolution?.what_changed ? <LabeledText label="What changed" value={evolution.what_changed} /> : null}
      {evolution?.research_follow_up ? <LabeledText label="Research follow-up" value={evolution.research_follow_up} /> : null}
    </View>
  );
}

function ResearchChainGraphic({ document, figure }: { document: ReportDocument; figure: ReportFigure }) {
  const { nodes, edges } = buildRelationshipGraphPreview(document, figure);
  if (!nodes.length || !edges.length) return <UnavailableFigure />;
  const nodesById = new Map(nodes.map((node) => [node.node_id, node]));
  const sourceNodes = nodes
    .filter((node) => edges.some((edge) => edge.source_node_id === node.node_id))
    .sort((left, right) => left.depth - right.depth || left.label.localeCompare(right.label));
  return (
    <View accessibilityLabel={`Validated research chain with ${nodes.length} nodes and ${edges.length} relationships`} style={styles.researchChain}>
      {sourceNodes.map((source) => {
        const outgoing = edges.filter((edge) => edge.source_node_id === source.node_id);
        return (
          <View key={source.node_id} style={styles.researchChainBranch}>
            <ResearchChainNode label={source.label} nodeType={source.node_type} source />
            <View style={styles.researchChainTargets}>
              {outgoing.map((edge) => {
                const target = nodesById.get(edge.target_node_id);
                if (!target) return null;
                return (
                  <View accessibilityLabel={`${source.label}, ${edge.label}, ${target.label}`} key={edge.relationship_id} style={styles.researchChainRelationship}>
                    <Text style={styles.researchChainArrow}>→</Text>
                    <View style={styles.researchChainEdge}>
                      <Text style={styles.researchChainEdgeLabel}>{edge.label}</Text>
                      <Text numberOfLines={2} style={styles.researchChainMapping}>{edge.relationship_type.replaceAll('_', ' ')} · {edge.mapping_source}</Text>
                    </View>
                    <ResearchChainNode label={target.label} nodeType={target.node_type} />
                  </View>
                );
              })}
            </View>
          </View>
        );
      })}
      <Text style={styles.sourceText}>Only evidence-linked structured mappings are shown. Supply-chain edges require structured validation.</Text>
    </View>
  );
}

function ResearchChainNode({ label, nodeType, source = false }: { label: string; nodeType: string; source?: boolean }) {
  return <View style={[styles.researchChainNode, source && styles.researchChainSourceNode]}><Text style={styles.researchChainNodeType}>{nodeType.toUpperCase()}</Text><Text style={styles.researchChainNodeLabel}>{label}</Text></View>;
}

function RelativeStrengthFlowGraphic({ figure }: { figure: ReportFigure }) {
  const points = figure.data_series.flatMap((series) => series.points.map((point) => ({
    label: formatCell(point.label ?? point.timeframe ?? point.period),
    kind: typeof point.kind === 'string' ? point.kind : null,
    value: numeric(point.value),
  }))).filter((point): point is { label: string; kind: string | null; value: number } => point.value !== null);
  if (!points.length) return <UnavailableFigure />;
  const scale = Math.max(...points.map((point) => Math.abs(point.value)), 1);
  return (
    <View accessibilityLabel={`Relative-strength flow across ${points.length} supported horizons`} style={styles.relativeFlow}>
      {points.map((point, index) => {
        const width = Math.max(2, (Math.abs(point.value) / scale) * 50);
        const positive = point.value >= 0;
        return (
          <View key={`${point.label}-${index}`} style={styles.relativeFlowRow}>
            <View style={styles.relativeFlowLabelWrap}>
              <Text style={styles.relativeFlowLabel}>{point.label}</Text>
              {point.kind ? <Text style={styles.relativeFlowKind}>{point.kind.replaceAll('_', ' ')}</Text> : null}
            </View>
            <View style={styles.relativeFlowTrack}>
              <View style={styles.relativeFlowCenter} />
              <View style={[
                styles.relativeFlowBar,
                { backgroundColor: positive ? Theme.colors.success : Theme.colors.danger, left: positive ? '50%' : `${50 - width}%`, width: `${width}%` },
              ]} />
            </View>
            <Text style={[styles.relativeFlowValue, { color: positive ? Theme.colors.success : Theme.colors.danger }]}>{point.value >= 0 ? '+' : ''}{point.value.toFixed(1)}</Text>
          </View>
        );
      })}
      <Text style={styles.sourceText}>Bars show supported direction by horizon. They do not extend beyond the current evidence window.</Text>
    </View>
  );
}

function GenericFigureFallback({ figure }: { figure: ReportFigure }) {
  const rows = figure.data_series.flatMap((series) => series.points.map((point, index) => ({
    key: `${series.series_id}-${index}`,
    label: firstText(point.label, point.stage, point.symbol, point.market_date, series.label),
    value: firstText(point.text, point.finding, point.detail, point.value, point.status),
  }))).filter((row) => row.label || row.value).slice(0, 8);
  if (!rows.length) return <UnavailableFigure />;
  return (
    <View accessibilityLabel={`Evidence summary fallback for ${figure.chart_type}`} style={styles.genericFigure}>
      <Text style={styles.genericFigureNotice}>Structured preview · {figure.chart_type.replaceAll('_', ' ')}</Text>
      {rows.map((row) => <View key={row.key} style={styles.genericFigureRow}><Text style={styles.genericFigureLabel}>{row.label ?? 'Evidence'}</Text><Text style={styles.genericFigureValue}>{row.value ?? 'Available in the PDF figure'}</Text></View>)}
    </View>
  );
}

function ResearchFocusSummary({ document }: { document: ReportDocument }) {
  const focus = document.research_focus;
  if (!focus) return null;
  const question = focus.question ?? document.research_inquiry?.question;
  const executiveAnswer = focus.executive_answer ?? document.research_inquiry?.executive_answer;
  return (
    <View style={styles.focusSummary}>
      <View style={styles.rowHeader}>
        <View><Text style={styles.label}>PRIMARY RESEARCH SUBJECT</Text><Text style={styles.focusTitle}>{focus.subject}</Text></View>
        <StatusBadge label={focus.classification_label} tone={['Leading', 'Emerging'].includes(focus.classification_label) ? 'success' : 'warning'} />
      </View>
      <View style={styles.summaryRow}>
        <SummaryMetric label="Priority score" value={focus.priority_score.toFixed(1)} />
        <SummaryMetric label="User relevance" value={focus.user_relevance.tier} />
        <SummaryMetric label="Saved overlap" value={String(focus.user_relevance.saved_security_symbols.length)} />
        <SummaryMetric label="Evidence quality" value={focus.evidence_quality?.label ?? 'Not scored'} />
      </View>
      {question ? <LabeledText label="Research question" value={question} /> : null}
      {executiveAnswer ? <View style={styles.executiveAnswer}><Text style={styles.label}>EXECUTIVE ANSWER</Text><Text style={styles.executiveAnswerText}>{executiveAnswer}</Text></View> : null}
      {focus.evidence_quality ? (
        <View style={styles.evidenceQuality}>
          <View style={styles.rowHeader}><Text style={styles.label}>EVIDENCE QUALITY</Text><StatusBadge label={focus.evidence_quality.label} tone={evidenceQualityTone(focus.evidence_quality.label)} /></View>
          <View style={styles.evidenceQualityGrid}>
            <QualityDimension label="Freshness" value={focus.evidence_quality.freshness} />
            <QualityDimension label="Breadth" value={focus.evidence_quality.breadth} />
            <QualityDimension label="Participation" value={focus.evidence_quality.participation} />
            <QualityDimension label="Completeness" value={focus.evidence_quality.completeness} />
            <QualityDimension label="Consistency" value={focus.evidence_quality.consistency} />
          </View>
          {focus.evidence_quality.rationale.slice(0, 2).map((item, index) => <Text key={`${item}-${index}`} style={styles.muted}>{item}</Text>)}
        </View>
      ) : null}
      <LabeledText label="Main thesis" value={focus.main_thesis} />
      <LabeledText label="Counter-thesis" value={focus.counter_thesis} />
      {(focus.leading_securities?.length || focus.lagging_securities?.length) ? (
        <View style={styles.signalColumns}>
          <ResearchSecuritySignals label="Leading stocks" signals={focus.leading_securities ?? []} tone="success" />
          <ResearchSecuritySignals label="Lagging stocks" signals={focus.lagging_securities ?? []} tone="danger" />
        </View>
      ) : null}
      {focus.execution_implications?.length ? <BulletList items={focus.execution_implications} label="Execution implications" tone="accent" /> : null}
      {focus.conclusion_change_conditions?.length ? <BulletList items={focus.conclusion_change_conditions} label="What changes the conclusion" tone="danger" /> : null}
      {focus.research_evolution ? <LabeledText label="Research follow-up" value={focus.research_evolution.research_follow_up} /> : null}
      {focus.taxonomy_chain.length ? <View style={styles.labeled}><Text style={styles.label}>VALIDATED TAXONOMY CHAIN</Text><Text style={styles.body}>{focus.taxonomy_chain.map((item) => `${item.level}: ${item.name}`).join(' → ')}</Text></View> : null}
      {focus.affected_securities.length ? <View style={styles.listStack}><Text style={styles.label}>SAVED SECURITIES AFFECTED</Text>{focus.affected_securities.map((item) => <View key={item.symbol} style={styles.researchRow}><View style={styles.rowHeader}><Text style={styles.securitySymbol}>{item.symbol}</Text><StatusBadge label={item.relation_to_focus} tone="muted" /></View><Text style={styles.body}>{item.setup_state} · {item.trend} · {item.volume_condition}</Text><LabeledText label="Key level" value={item.key_level} /><LabeledText label="Reason to monitor" value={item.reason_to_monitor} /></View>)}</View> : null}
    </View>
  );
}

function DocumentTable({ table }: { table: ReportDocument['tables'][number] }) {
  return (
    <View style={styles.documentTable}>
      <Text style={styles.rowTitle}>{table.title}</Text>
      <ScrollView horizontal>
        <View>
          <View style={[styles.documentTableRow, styles.documentTableHeader]}>{table.columns.map((column) => <Text key={column} style={styles.documentTableHeaderCell}>{column}</Text>)}</View>
          {table.rows.map((row, index) => <View key={index} style={styles.documentTableRow}>{table.columns.map((column) => <Text key={column} style={styles.documentTableCell}>{formatCell(row[column])}</Text>)}</View>)}
        </View>
      </ScrollView>
    </View>
  );
}

function ScenarioList({ document, ids }: { document: ReportDocument; ids: string[] }) {
  return <View style={styles.listStack}>{ids.map((id) => { const item = document.scenarios.find((scenario) => scenario.scenario_id === id); return item ? <View key={id} style={styles.researchRow}><View style={styles.rowHeader}><Text style={styles.rowTitle}>{item.label}</Text><StatusBadge label={item.likelihood} tone="muted" /></View><LabeledText label="Required conditions" value={item.required_conditions.join(' ')} /><LabeledText label="Invalidation" value={item.invalidation.join(' ')} /><LabeledText label="Operating response" value={item.operating_response} /></View> : null; })}</View>;
}

function SecurityList({ document, figures, ids }: { document: ReportDocument; figures: Map<string, ReportFigure>; ids: string[] }) {
  return (
    <View style={styles.listStack}>
      {ids.map((id) => {
        const item = document.securities.find((security) => security.security_id === id);
        if (!item) return null;
        const figure = item.figure_id ? figures.get(item.figure_id) : null;
        const context = [item.sector, item.group, ...(item.themes ?? [])].filter((value): value is string => Boolean(value));
        return (
          <View key={id} style={[styles.securityResearch, item.selected_for_research && styles.securityResearchSelected]}>
            <View style={styles.rowHeader}>
              <View><Text style={styles.securitySymbol}>{item.symbol}</Text><Text style={styles.rowTitle}>{item.category} · {item.setup_state}</Text></View>
              <StatusBadge label={item.selected_for_research ? 'Selected research' : item.actionable ? 'Actionable' : 'Monitoring'} tone={item.selected_for_research || item.actionable ? 'success' : 'warning'} />
            </View>
            {item.why_here ? <LabeledText label="Why here" value={item.why_here} /> : null}
            <Text style={styles.body}>{item.summary}</Text>
            {item.context ? <LabeledText label="Market context" value={item.context} /> : null}
            <LabeledText label="Sector and theme" value={context.length ? context.join(' · ') : 'Validated mapping unavailable'} />
            <View style={styles.securityMetrics}>
              <SummaryMetric label="Relative strength" value={formatCell(item.relative_strength)} />
              <SummaryMetric label="Trend" value={item.trend ?? 'Unavailable'} />
              <SummaryMetric label="Volume" value={item.volume_condition ?? 'Unavailable'} />
              <SummaryMetric label="Classification" value={item.research_classification ?? 'Data insufficient'} />
            </View>
            {figure ? <ResearchFigure document={document} figure={figure} /> : null}
            {item.change_since_previous ? <LabeledText label="What changed" value={item.change_since_previous} /> : null}
            <View style={styles.conditionRow}>
              <View style={styles.condition}><Text style={styles.confirmLabel}>CONFIRMATION</Text><Text style={styles.conditionText}>{item.confirmation}</Text></View>
              <View style={styles.condition}><Text style={styles.riskLabel}>INVALIDATION</Text><Text style={styles.conditionText}>{item.invalidation}</Text></View>
            </View>
            <LabeledText label="Risk" value={item.risk_considerations} />
            {item.execution_consideration ? <LabeledText label="Execution consideration" value={item.execution_consideration} /> : null}
            <Text style={styles.sourceText}>Source: {item.source_timestamp ?? item.freshness}</Text>
          </View>
        );
      })}
    </View>
  );
}

function MonitoringList({ document, ids }: { document: ReportDocument; ids: string[] }) {
  return <View style={styles.listStack}>{ids.map((id) => { const item = document.monitoring_conditions.find((condition) => condition.condition_id === id); return item ? <View key={id} style={styles.monitorRow}><Text style={styles.rowTitle}>{item.metric}</Text><Text style={styles.body}>{item.threshold_or_condition}</Text><Text style={styles.muted}>{item.rationale}</Text><Text style={styles.action}>{item.action_implication}</Text></View> : null; })}</View>;
}

function QualityDimension({ label, value }: { label: string; value: 'High' | 'Medium' | 'Low' }) {
  return <View style={styles.qualityDimension}><Text style={styles.qualityDimensionLabel}>{label}</Text><Text style={[styles.qualityDimensionValue, { color: evidenceQualityColor(value) }]}>{value}</Text></View>;
}

function ResearchSecuritySignals({ label, signals, tone }: { label: string; signals: ReportResearchSecuritySignal[]; tone: 'success' | 'danger' }) {
  return (
    <View style={styles.signalColumn}>
      <Text style={[styles.label, { color: tone === 'success' ? Theme.colors.success : Theme.colors.danger }]}>{label.toUpperCase()}</Text>
      {signals.length ? signals.map((signal) => (
        <View key={`${signal.symbol}-${signal.role}`} style={styles.signalRow}>
          <View style={styles.rowHeader}><Text style={styles.signalSymbol}>{signal.symbol}</Text><Text style={styles.signalMetric}>{signal.metric_label}: {formatCell(signal.metric_value)}</Text></View>
          <Text style={styles.muted}>{signal.reason}</Text>
        </View>
      )) : <Text style={styles.muted}>No validated securities.</Text>}
    </View>
  );
}

function BulletList({ items, label, tone }: { items: string[]; label: string; tone: 'accent' | 'danger' }) {
  const color = tone === 'danger' ? Theme.colors.danger : Theme.colors.accent;
  return <View style={styles.labeled}><Text style={[styles.label, { color }]}>{label.toUpperCase()}</Text>{items.map((item, index) => <View key={`${item}-${index}`} style={styles.bulletRow}><View style={[styles.bullet, { backgroundColor: color }]} /><Text style={styles.body}>{item}</Text></View>)}</View>;
}

function LabeledText({ label, value }: { label: string; value: string }) { return <View style={styles.labeled}><Text style={styles.label}>{label.toUpperCase()}</Text><Text style={styles.body}>{value}</Text></View>; }
function SummaryMetric({ label, value }: { label: string; value: string }) { return <View style={styles.summaryMetric}><Text style={styles.label}>{label.toUpperCase()}</Text><Text style={styles.summaryValue}>{value}</Text></View>; }
function UnavailableFigure() { return <View style={styles.unavailable}><Text style={styles.muted}>Qualified figure data unavailable</Text></View>; }
function numeric(value: unknown) { const parsed = typeof value === 'number' ? value : Number(value); return Number.isFinite(parsed) ? parsed : null; }
function heatColor(value: number | null) { if (value === null) return Theme.colors.card; if (value >= 0) return value > 3 ? '#A6F4C5' : '#D1FADF'; return value < -3 ? '#FECDCA' : '#FEE4E2'; }
function formatCell(value: unknown) { if (value === null || value === undefined || value === '') return '—'; if (typeof value === 'number') return Number.isInteger(value) ? String(value) : value.toFixed(2); return String(value); }
function sourceTone(value: string): 'success' | 'warning' | 'danger' | 'muted' { if (value === 'live') return 'success'; if (value === 'unavailable') return 'danger'; if (value === 'test') return 'muted'; return 'warning'; }
function evidenceQualityTone(value: 'High' | 'Medium' | 'Low'): 'success' | 'warning' | 'danger' { if (value === 'High') return 'success'; if (value === 'Medium') return 'warning'; return 'danger'; }
function evidenceQualityColor(value: 'High' | 'Medium' | 'Low') { if (value === 'High') return Theme.colors.success; if (value === 'Medium') return Theme.colors.warning; return Theme.colors.danger; }
function isSuppressedFreshness(value: string | null | undefined) { return Boolean(value && /stale|unavailable|missing|unknown|invalid/i.test(value)); }
function annotationColor(value: string) { if (/risk|invalid|failed/i.test(value)) return Theme.colors.danger; if (/confirm|breakout/i.test(value)) return Theme.colors.success; if (/support|ema|pivot|previous/i.test(value)) return Theme.colors.accent; if (/resistance|gap/i.test(value)) return Theme.colors.warning; return Theme.colors.textMuted; }
function firstText(...values: unknown[]) { for (const value of values) { if (typeof value === 'string' && value.trim()) return value.trim(); if (typeof value === 'number' && Number.isFinite(value)) return String(value); } return null; }

function fallbackSectionQuestion(sectionId: string, title: string, document: ReportDocument) {
  const fixed: Record<string, string> = {
    cover: 'What is the current market thesis, and what would invalidate it?',
    'executive-summary': 'Why does the current evidence support this market posture?',
    'index-structure': 'Does major-index structure confirm a durable trend?',
    breadth: 'Is participation broad enough to confirm benchmark price?',
    leadership: 'Where is leadership strengthening, weakening, or becoming concentrated?',
    'research-focus': document.research_focus?.question ?? document.research_inquiry?.question ?? 'Did any research subject clear the evidence threshold?',
    macro: 'Do cross-asset proxies confirm or contradict the equity posture?',
    risk: 'Which risks could overturn the thesis first?',
    scenarios: 'Which evidence conditions distinguish the next plausible market paths?',
    watchlist: 'Which saved securities deserve research attention, and why now?',
    'operating-plan': 'What should be monitored next, and how should the response change?',
    methodology: 'How reliable, fresh, and complete is the evidence behind this report?',
  };
  return fixed[sectionId] ?? `What does ${title.toLowerCase()} explain about the current market?`;
}

const styles = StyleSheet.create({
  action: { color: Theme.colors.accent, fontSize: 13, fontWeight: '800', lineHeight: 19 },
  body: { color: Theme.colors.text, fontSize: 14, lineHeight: 21 },
  bullet: { borderRadius: Theme.radii.pill, height: 6, marginTop: 7, width: 6 },
  bulletRow: { alignItems: 'flex-start', flexDirection: 'row', gap: Spacing.two },
  chart: { backgroundColor: Theme.colors.background, height: 230, marginTop: Spacing.two, position: 'relative' },
  claim: { borderBottomColor: Theme.colors.border, borderBottomWidth: 1, borderTopColor: Theme.colors.border, borderTopWidth: 1, gap: Spacing.two, marginTop: Spacing.two, paddingVertical: Spacing.three },
  claimText: { color: Theme.colors.text, fontSize: 15, fontWeight: '800', lineHeight: 22 },
  condition: { flex: 1, gap: Spacing.one, minWidth: 160 },
  conditionRow: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.three },
  conditionText: { color: Theme.colors.text, fontSize: 12, lineHeight: 18 },
  confirmLabel: { color: Theme.colors.success, fontSize: 10, fontWeight: '900' },
  contents: { gap: Spacing.one, paddingVertical: Spacing.one },
  contentsButton: { alignItems: 'center', borderBottomColor: Theme.colors.border, borderBottomWidth: 2, flexDirection: 'row', gap: Spacing.one, minHeight: 42, paddingHorizontal: Spacing.two },
  contentsButtonActive: { borderBottomColor: Theme.colors.accent },
  contentsNumber: { color: Theme.colors.textMuted, fontSize: 10, fontWeight: '900' },
  contentsText: { color: Theme.colors.textMuted, fontSize: 12, fontWeight: '800', maxWidth: 150 },
  contentsTextActive: { color: Theme.colors.accent },
  cover: { borderBottomColor: Theme.colors.border, borderBottomWidth: 1, gap: Spacing.two, paddingBottom: Spacing.three },
  documentTable: { gap: Spacing.two, marginTop: Spacing.three },
  documentTableCell: { color: Theme.colors.text, fontSize: 10, lineHeight: 15, padding: Spacing.one, width: 125 },
  documentTableHeader: { backgroundColor: Theme.colors.text },
  documentTableHeaderCell: { color: Theme.colors.background, fontSize: 10, fontWeight: '900', padding: Spacing.one, width: 125 },
  documentTableRow: { borderBottomColor: Theme.colors.border, borderBottomWidth: 1, flexDirection: 'row' },
  evidenceColumn: { borderRadius: Theme.radii.small, flex: 1, gap: Spacing.two, minWidth: 190, padding: Spacing.twoAndHalf },
  evidenceColumnTitle: { color: Theme.colors.text, fontSize: 10, fontWeight: '900' },
  evidenceContradicts: { backgroundColor: Theme.colors.dangerSoft, borderColor: Theme.colors.danger, borderWidth: 1 },
  evidenceDimension: { color: Theme.colors.text, fontSize: 12, fontWeight: '900' },
  evidenceFinding: { color: Theme.colors.text, fontSize: 11, lineHeight: 16 },
  evidenceImplication: { color: Theme.colors.textMuted, fontSize: 10, lineHeight: 15 },
  evidenceItem: { borderTopColor: Theme.colors.border, borderTopWidth: 1, gap: Spacing.one, paddingTop: Spacing.two },
  evidenceMatrix: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.two, marginTop: Spacing.two },
  evidenceNeutral: { backgroundColor: Theme.colors.card, borderColor: Theme.colors.border, borderWidth: 1 },
  evidenceQuality: { backgroundColor: Theme.colors.background, borderColor: Theme.colors.border, borderRadius: Theme.radii.small, borderWidth: 1, gap: Spacing.two, padding: Spacing.two },
  evidenceQualityGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.one },
  evidenceSupports: { backgroundColor: Theme.colors.successSoft, borderColor: Theme.colors.success, borderWidth: 1 },
  eyebrow: { color: Theme.colors.accent, fontSize: 10, fontWeight: '900' },
  executiveAnswer: { backgroundColor: Theme.colors.accentSoft, borderLeftColor: Theme.colors.accent, borderLeftWidth: 3, gap: Spacing.one, padding: Spacing.twoAndHalf },
  executiveAnswerText: { color: Theme.colors.text, fontSize: 15, fontWeight: '800', lineHeight: 22 },
  figure: { borderBottomColor: Theme.colors.border, borderBottomWidth: 1, gap: Spacing.two, paddingVertical: Spacing.three },
  figureMeta: { color: Theme.colors.textMuted, fontSize: 11, lineHeight: 16 },
  figureQuestion: { backgroundColor: Theme.colors.card, borderLeftColor: Theme.colors.accent, borderLeftWidth: 2, gap: Spacing.one, padding: Spacing.two },
  figureQuestionText: { color: Theme.colors.text, fontSize: 12, fontWeight: '800', lineHeight: 17 },
  figureTitle: { color: Theme.colors.text, fontSize: 16, fontWeight: '900', lineHeight: 21 },
  focusBadge: { backgroundColor: Theme.colors.background, borderColor: Theme.colors.border, borderRadius: Theme.radii.small, borderWidth: 1, gap: Spacing.one, marginTop: Spacing.two, padding: Spacing.two },
  focusBadgeTitle: { color: Theme.colors.text, fontSize: 15, fontWeight: '900' },
  focusSummary: { backgroundColor: Theme.colors.cardElevated, borderColor: Theme.colors.border, borderRadius: Theme.radii.small, borderWidth: 1, gap: Spacing.three, marginBottom: Spacing.two, padding: Spacing.three },
  focusTitle: { color: Theme.colors.text, fontSize: 20, fontWeight: '900' },
  genericFigure: { backgroundColor: Theme.colors.background, borderColor: Theme.colors.border, borderRadius: Theme.radii.small, borderWidth: 1, gap: Spacing.one, marginTop: Spacing.two, padding: Spacing.two },
  genericFigureLabel: { color: Theme.colors.text, flex: 1, fontSize: 11, fontWeight: '900' },
  genericFigureNotice: { color: Theme.colors.textMuted, fontSize: 10, fontWeight: '900', marginBottom: Spacing.one, textTransform: 'uppercase' },
  genericFigureRow: { borderTopColor: Theme.colors.border, borderTopWidth: 1, flexDirection: 'row', gap: Spacing.two, paddingVertical: Spacing.two },
  genericFigureValue: { color: Theme.colors.textMuted, flex: 2, fontSize: 11, lineHeight: 16 },
  heatCell: { alignItems: 'center', height: 32, justifyContent: 'center', width: 68 },
  heatCellHeader: { color: Theme.colors.textMuted, fontSize: 10, fontWeight: '900', textAlign: 'center', width: 68 },
  heatLabel: { color: Theme.colors.text, fontSize: 11, fontWeight: '800', width: 130 },
  heatRow: { alignItems: 'center', flexDirection: 'row', gap: 2 },
  heatValue: { color: '#101828', fontSize: 10, fontWeight: '800' },
  heatmap: { gap: 2, paddingVertical: Spacing.two },
  label: { color: Theme.colors.textMuted, fontSize: 10, fontWeight: '900' },
  labeled: { gap: Spacing.one },
  legend: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.two, left: Spacing.two, position: 'absolute', top: 0 },
  legendItem: { alignItems: 'center', flexDirection: 'row', gap: 4 },
  legendLine: { height: 2, width: 12 },
  legendText: { color: Theme.colors.textMuted, fontSize: 9, fontWeight: '700' },
  listStack: { gap: Spacing.three, marginTop: Spacing.two },
  meta: { color: Theme.colors.textMuted, fontSize: 12, fontWeight: '700' },
  metaRow: { alignItems: 'center', flexDirection: 'row', gap: Spacing.two, justifyContent: 'space-between' },
  monitorRow: { borderBottomColor: Theme.colors.border, borderBottomWidth: 1, gap: Spacing.two, paddingBottom: Spacing.three },
  muted: { color: Theme.colors.textMuted, fontSize: 12, lineHeight: 18 },
  posture: { color: Theme.colors.success, fontSize: 13, fontWeight: '900', marginTop: Spacing.one },
  pressed: { opacity: 0.7 },
  priorityBar: { backgroundColor: Theme.colors.textMuted, height: '100%' },
  priorityBarSelected: { backgroundColor: Theme.colors.accent },
  priorityChart: { gap: Spacing.two, marginTop: Spacing.two },
  priorityLabel: { color: Theme.colors.textMuted, fontSize: 11, width: 120 },
  priorityLabelSelected: { color: Theme.colors.text, fontWeight: '900' },
  priorityRow: { alignItems: 'center', flexDirection: 'row', gap: Spacing.two },
  priorityThreshold: { backgroundColor: Theme.colors.warning, height: 18, position: 'absolute', width: 2, zIndex: 2 },
  priorityTrack: { backgroundColor: Theme.colors.border, height: 18, overflow: 'hidden', position: 'relative', width: 280 },
  priorityValue: { color: Theme.colors.text, fontSize: 11, fontWeight: '900', width: 38 },
  provenance: { borderTopColor: Theme.colors.border, borderTopWidth: 1, gap: Spacing.one, paddingTop: Spacing.three },
  qualityDimension: { backgroundColor: Theme.colors.card, borderRadius: Theme.radii.small, gap: 2, minWidth: 92, padding: Spacing.two },
  qualityDimensionLabel: { color: Theme.colors.textMuted, fontSize: 9, fontWeight: '800' },
  qualityDimensionValue: { fontSize: 12, fontWeight: '900' },
  relativeFlow: { gap: Spacing.two, marginTop: Spacing.two },
  relativeFlowBar: { height: 16, position: 'absolute', top: 2 },
  relativeFlowCenter: { backgroundColor: Theme.colors.textMuted, height: 20, left: '50%', position: 'absolute', top: 0, width: 1 },
  relativeFlowKind: { color: Theme.colors.textMuted, fontSize: 8, textTransform: 'uppercase' },
  relativeFlowLabel: { color: Theme.colors.text, fontSize: 11, fontWeight: '800' },
  relativeFlowLabelWrap: { width: 110 },
  relativeFlowRow: { alignItems: 'center', flexDirection: 'row', gap: Spacing.two },
  relativeFlowTrack: { backgroundColor: Theme.colors.card, height: 20, overflow: 'hidden', position: 'relative', width: 280 },
  relativeFlowValue: { fontSize: 11, fontWeight: '900', textAlign: 'right', width: 48 },
  researchChain: { backgroundColor: Theme.colors.background, borderRadius: Theme.radii.small, gap: Spacing.one, marginTop: Spacing.two, padding: Spacing.twoAndHalf },
  researchChainArrow: { color: Theme.colors.accent, fontSize: 18, fontWeight: '900', lineHeight: 22 },
  researchChainBranch: { borderBottomColor: Theme.colors.border, borderBottomWidth: 1, gap: Spacing.two, paddingBottom: Spacing.two },
  researchChainEdge: { flex: 1, gap: 2, minWidth: 120 },
  researchChainEdgeLabel: { color: Theme.colors.text, fontSize: 10, fontWeight: '900' },
  researchChainMapping: { color: Theme.colors.textMuted, fontSize: 8, lineHeight: 12, textTransform: 'capitalize' },
  researchChainNode: { backgroundColor: Theme.colors.cardElevated, borderColor: Theme.colors.border, borderRadius: Theme.radii.small, borderWidth: 1, gap: 2, minWidth: 115, padding: Spacing.two },
  researchChainNodeLabel: { color: Theme.colors.text, fontSize: 11, fontWeight: '900' },
  researchChainNodeType: { color: Theme.colors.accent, fontSize: 8, fontWeight: '900' },
  researchChainRelationship: { alignItems: 'center', flexDirection: 'row', gap: Spacing.two },
  researchChainSourceNode: { alignSelf: 'flex-start', borderColor: Theme.colors.accent, minWidth: 150 },
  researchChainTargets: { gap: Spacing.two, paddingLeft: Spacing.two },
  researchRow: { borderBottomColor: Theme.colors.border, borderBottomWidth: 1, gap: Spacing.two, paddingBottom: Spacing.three },
  researchTimeline: { backgroundColor: Theme.colors.background, borderRadius: Theme.radii.small, gap: Spacing.three, marginTop: Spacing.two, padding: Spacing.twoAndHalf },
  researchTimelineLabel: { color: Theme.colors.accent, fontSize: 9, fontWeight: '900' },
  researchTimelinePhases: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.two },
  researchTimelineStep: { backgroundColor: Theme.colors.cardElevated, borderTopColor: Theme.colors.accent, borderTopWidth: 3, flex: 1, gap: Spacing.one, minWidth: 150, padding: Spacing.two },
  researchTimelineText: { color: Theme.colors.text, fontSize: 11, lineHeight: 16 },
  riskLabel: { color: Theme.colors.danger, fontSize: 10, fontWeight: '900' },
  rotationChart: { backgroundColor: Theme.colors.background, height: 250, marginTop: Spacing.two },
  rowHeader: { alignItems: 'center', flexDirection: 'row', gap: Spacing.two, justifyContent: 'space-between' },
  rowTitle: { color: Theme.colors.text, fontSize: 14, fontWeight: '900' },
  section: { gap: Spacing.two, paddingTop: Spacing.three },
  sectionNumber: { color: Theme.colors.accent, fontSize: 10, fontWeight: '900' },
  sectionPurpose: { color: Theme.colors.textMuted, fontSize: 13, lineHeight: 19 },
  sectionQuestion: { backgroundColor: Theme.colors.accentSoft, borderLeftColor: Theme.colors.accent, borderLeftWidth: 3, gap: Spacing.one, padding: Spacing.twoAndHalf },
  sectionQuestionText: { color: Theme.colors.text, fontSize: 16, fontWeight: '900', lineHeight: 22 },
  sectionTitle: { color: Theme.colors.text, fontSize: 23, fontWeight: '900', lineHeight: 28 },
  securityMetrics: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.two },
  securityResearch: { backgroundColor: Theme.colors.card, borderColor: Theme.colors.border, borderRadius: Theme.radii.small, borderWidth: 1, gap: Spacing.three, padding: Spacing.three },
  securityResearchSelected: { borderColor: Theme.colors.accent, borderWidth: 2 },
  securitySymbol: { color: Theme.colors.accent, fontSize: 18, fontWeight: '900' },
  signalColumn: { backgroundColor: Theme.colors.background, borderRadius: Theme.radii.small, flex: 1, gap: Spacing.two, minWidth: 220, padding: Spacing.two },
  signalColumns: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.two },
  signalMetric: { color: Theme.colors.textMuted, fontSize: 10, fontWeight: '800' },
  signalRow: { borderTopColor: Theme.colors.border, borderTopWidth: 1, gap: Spacing.one, paddingTop: Spacing.two },
  signalSymbol: { color: Theme.colors.text, fontSize: 13, fontWeight: '900' },
  sourceText: { color: Theme.colors.textMuted, fontSize: 10, lineHeight: 15 },
  stack: { gap: Spacing.three },
  summaryMetric: { flexBasis: '22%', gap: 3, minWidth: 80 },
  summaryRow: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.three, marginTop: Spacing.one },
  summaryValue: { color: Theme.colors.text, fontSize: 14, fontWeight: '900' },
  thesis: { color: Theme.colors.text, fontSize: 16, fontWeight: '700', lineHeight: 24 },
  timelineCard: { backgroundColor: Theme.colors.card, borderColor: Theme.colors.border, borderRadius: Theme.radii.small, borderWidth: 1, gap: Spacing.one, minHeight: 190, padding: Spacing.two, width: 155 },
  timelineCards: { flexDirection: 'row', gap: Spacing.two, paddingVertical: Spacing.two },
  timelineDate: { color: Theme.colors.accent, fontSize: 10, fontWeight: '900' },
  timelineMetric: { borderTopColor: Theme.colors.border, borderTopWidth: 1, gap: 2, paddingTop: Spacing.one },
  timelineMetricLabel: { color: Theme.colors.textMuted, fontSize: 8, fontWeight: '900', textTransform: 'uppercase' },
  timelineMetricValue: { color: Theme.colors.text, fontSize: 10, fontWeight: '700', lineHeight: 13 },
  timelineRegime: { color: Theme.colors.text, fontSize: 12, fontWeight: '900', minHeight: 30 },
  timeline: { minWidth: 770 },
  timelineCell: { color: Theme.colors.text, fontSize: 10, lineHeight: 14, padding: Spacing.one, width: 110 },
  timelineHeader: { color: Theme.colors.background, fontSize: 10, fontWeight: '900', padding: Spacing.one, width: 110 },
  timelineRow: { backgroundColor: Theme.colors.card, borderBottomColor: Theme.colors.border, borderBottomWidth: 1, flexDirection: 'row' },
  title: { color: Theme.colors.text, fontSize: 25, fontWeight: '900', lineHeight: 30 },
  unavailable: { alignItems: 'center', backgroundColor: Theme.colors.card, height: 160, justifyContent: 'center', marginTop: Spacing.two },
});
