import { StyleSheet, Text, View } from 'react-native';

import { TERMINOLOGY } from '@/architecture/terminologyRegistry';
import { DashboardCard } from '@/components/cards/DashboardCard';
import { AppButton } from '@/components/ui/AppButton';
import { AppIcon } from '@/components/ui/AppIcon';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Spacing, Theme, Typography } from '@/constants/theme';
import { buildDailyBriefing } from '@/features/reports/dailyBriefingModel';
import type { DailyReportRecord } from '@/features/reports/reportLibraryModel';
import { buildResearchPreviewModel } from '@/features/reports/researchPreviewModel';
import { formatLocalizedDate, formatLocalizedDateTime } from '@/features/trust/dateFreshnessPresentation';

export function ReportLandingCard({
  generationMessage,
  isGenerating,
  latestRecord,
  onGenerate,
  onPreview,
}: {
  generationMessage: string | null;
  isGenerating: boolean;
  latestRecord: DailyReportRecord | null;
  onGenerate: () => void;
  onPreview: (record: DailyReportRecord) => void;
}) {
  const reportDocument = latestRecord?.snapshot?.report_document;
  const briefing = latestRecord?.snapshot && !reportDocument ? buildDailyBriefing(latestRecord.snapshot) : null;
  const thesis = reportDocument?.thesis.concise_thesis ?? briefing?.narrative;
  const posture = reportDocument?.thesis.posture ?? briefing?.regime;
  const confidence = reportDocument?.thesis.confidence_label
    ?? (briefing ? `${briefing.confidence.label}${briefing.confidence.score === null ? '' : ` · ${Math.round(briefing.confidence.score)}%`}` : null);
  const researchPreview = buildResearchPreviewModel(reportDocument);
  return (
    <DashboardCard accentColor={Theme.colors.accent} style={styles.card}>
      <View style={styles.header}>
        <View style={styles.eyebrowRow}>
          <AppIcon color={Theme.colors.accent} name="info" size={17} />
          <Text style={styles.eyebrow}>TODAY&apos;S INTELLIGENCE</Text>
        </View>
        <StatusBadge
          label={latestRecord?.snapshot ? TERMINOLOGY.availability.available : TERMINOLOGY.empty.reportNotGenerated}
          tone={latestRecord?.snapshot ? 'success' : 'muted'}
        />
      </View>

      {researchPreview.state === 'focus' ? (
        <View style={styles.researchFocus}>
          <View style={styles.researchHeader}>
            <Text style={styles.researchLabel}>RESEARCH QUESTION</Text>
            {researchPreview.evidenceQuality ? <StatusBadge label={`${researchPreview.evidenceQuality} evidence quality`} tone={evidenceQualityTone(researchPreview.evidenceQuality)} /> : null}
          </View>
          <Text style={styles.researchTitle}>{researchPreview.question}</Text>
          <Text numberOfLines={3} style={styles.researchWhy}>{researchPreview.executiveAnswer}</Text>
          {researchPreview.evolutionSummary ? <Text numberOfLines={2} style={styles.researchEvolution}>Changed: {researchPreview.evolutionSummary}</Text> : null}
          <Text style={styles.researchMeta}>{researchPreview.subject} · {researchPreview.badge} · {researchPreview.overlapCount} saved-item overlap{researchPreview.overlapCount === 1 ? '' : 's'} · {researchPreview.figureCount} figures{researchPreview.partialData ? ' · partial data' : ''}</Text>
        </View>
      ) : researchPreview.state === 'no_focus' ? (
        <View style={styles.researchFocus}>
          <Text style={styles.researchLabel}>RESEARCH QUESTION</Text>
          <Text style={styles.researchTitle}>{researchPreview.question}</Text>
          <Text style={styles.noResearch}>{researchPreview.executiveAnswer}</Text>
        </View>
      ) : null}

      <View style={styles.marketThesis}>
        <Text style={styles.marketThesisLabel}>MARKET THESIS</Text>
        <Text style={styles.thesis} numberOfLines={4}>
          {thesis ?? 'Generate the daily briefing to connect market structure, leadership, risk, and your watchlist into one decision-ready narrative.'}
        </Text>
      </View>

      <View style={styles.metrics}>
        <LandingMetric label="Report Type" value={reportDocument?.report_type ?? 'Daily Briefing'} />
        <LandingMetric label="Market Posture" value={posture ?? TERMINOLOGY.empty.reportNotGenerated} />
        <LandingMetric label="Market Confidence" value={confidence ?? TERMINOLOGY.empty.reportNotGenerated} />
        <LandingMetric label="Research Evidence" value={researchPreview.state === 'focus' && researchPreview.evidenceQuality
          ? `${researchPreview.evidenceQuality} quality · ${researchPreview.figureCount} figures`
          : reportDocument
            ? `${reportDocument.figure_count} figures · ${Math.round(reportDocument.thesis.data_completeness * 100)}% complete`
            : (briefing?.primaryTheme ?? TERMINOLOGY.empty.reportNotGenerated)} />
      </View>

      {reportDocument ? (
        <Text style={styles.documentMeta}>
          Market date {formatLocalizedDate(reportDocument.market_date)} · Generated {formatGeneratedAt(reportDocument.generated_at)} · {reportDocument.source_status} sources · {reportDocument.previous_report_available ? 'Previous comparison available' : 'Baseline report'}
        </Text>
      ) : null}

      <View style={styles.actions}>
        <AppButton
          accessibilityLabel={isGenerating ? 'Generating report' : TERMINOLOGY.actions.generateReport}
          label={isGenerating ? 'Generating report…' : TERMINOLOGY.actions.generateReport}
          leadingIcon={<AppIcon color={Theme.colors.background} name="refresh" size={16} />}
          loading={isGenerating}
          onPress={onGenerate}
          variant="primary"
        />
        {latestRecord?.snapshot ? (
          <AppButton
            accessibilityLabel="Read today's briefing"
            label="Read Research"
            onPress={() => onPreview(latestRecord)}
            trailingIcon={<AppIcon color={Theme.colors.accent} name="chevronRight" size={14} />}
            variant="secondary"
          />
        ) : null}
      </View>
      {generationMessage ? <Text style={styles.progressText}>{generationMessage}</Text> : null}
    </DashboardCard>
  );
}

function formatGeneratedAt(value: string) {
  return formatLocalizedDateTime(value);
}

function LandingMetric({ label, value, warning = false }: { label: string; value: string; warning?: boolean }) {
  return (
    <View style={styles.metric}>
      <Text style={styles.metricLabel}>{label}</Text>
      <Text numberOfLines={2} style={[styles.metricValue, warning && styles.warningValue]}>{value}</Text>
    </View>
  );
}

function evidenceQualityTone(value: 'High' | 'Medium' | 'Low'): 'success' | 'warning' | 'danger' {
  if (value === 'High') return 'success';
  if (value === 'Medium') return 'warning';
  return 'danger';
}

const styles = StyleSheet.create({
  actions: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.two, marginTop: Spacing.three },
  card: { backgroundColor: Theme.colors.cardElevated },
  documentMeta: { color: Theme.colors.textMuted, fontSize: Typography.caption.fontSize, fontWeight: Typography.weights.emphasis, lineHeight: 16, marginTop: Spacing.two },
  eyebrow: { color: Theme.colors.accent, fontSize: Typography.caption.fontSize, fontWeight: Typography.weights.strong },
  eyebrowRow: { alignItems: 'center', flexDirection: 'row', gap: Spacing.two },
  header: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between', marginBottom: Spacing.twoAndHalf },
  metric: { borderTopColor: Theme.colors.border, borderTopWidth: 1, flexBasis: '47%', gap: Spacing.one, minWidth: 140, paddingTop: Spacing.two },
  metricLabel: { color: Theme.colors.textMuted, fontSize: Typography.caption.fontSize, fontWeight: Typography.weights.strong },
  metricValue: { color: Theme.colors.text, fontSize: Typography.body.fontSize, fontWeight: Typography.weights.strong, lineHeight: 19 },
  metrics: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.three, marginTop: Spacing.three },
  marketThesis: { gap: Spacing.one, marginTop: Spacing.three },
  marketThesisLabel: { color: Theme.colors.textMuted, fontSize: Typography.chartLabel.fontSize, fontWeight: Typography.weights.strong },
  progressText: { color: Theme.colors.textMuted, fontSize: Typography.small.fontSize, fontWeight: Typography.weights.emphasis, marginTop: Spacing.two },
  noResearch: { color: Theme.colors.textMuted, fontSize: Typography.small.fontSize, lineHeight: 18, marginTop: Spacing.two },
  researchFocus: { backgroundColor: Theme.colors.background, borderColor: Theme.colors.border, borderRadius: Theme.radii.small, borderWidth: 1, gap: Spacing.one, marginTop: Spacing.three, padding: Spacing.twoAndHalf },
  researchHeader: { alignItems: 'center', flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.two, justifyContent: 'space-between' },
  researchLabel: { color: Theme.colors.accent, fontSize: Typography.chartLabel.fontSize, fontWeight: Typography.weights.strong },
  researchEvolution: { color: Theme.colors.warning, fontSize: Typography.caption.fontSize, fontWeight: Typography.weights.strong, lineHeight: 16 },
  researchMeta: { color: Theme.colors.textMuted, fontSize: Typography.caption.fontSize, fontWeight: Typography.weights.emphasis },
  researchTitle: { color: Theme.colors.text, fontSize: Typography.supportTitle.fontSize, fontWeight: Typography.weights.strong },
  researchWhy: { color: Theme.colors.text, fontSize: Typography.small.fontSize, lineHeight: 18 },
  thesis: { color: Theme.colors.text, fontSize: Typography.supportTitle.fontSize, fontWeight: Typography.weights.emphasis, lineHeight: 24 },
  warningValue: { color: Theme.colors.warning },
});
