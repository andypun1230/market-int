import { SymbolView } from 'expo-symbols';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Spacing, Theme } from '@/constants/theme';
import { buildDailyBriefing } from '@/features/reports/dailyBriefingModel';
import type { DailyReportRecord } from '@/features/reports/reportLibraryModel';
import { buildResearchPreviewModel } from '@/features/reports/researchPreviewModel';

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
          <SymbolView name="newspaper.fill" size={17} tintColor={Theme.colors.accent} weight="bold" />
          <Text style={styles.eyebrow}>TODAY&apos;S INTELLIGENCE</Text>
        </View>
        <StatusBadge
          label={latestRecord?.snapshot ? 'Ready' : 'Not generated'}
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
        <LandingMetric label="Market Posture" value={posture ?? 'Awaiting report'} />
        <LandingMetric label="Market Confidence" value={confidence ?? 'Awaiting report'} />
        <LandingMetric label="Research Evidence" value={researchPreview.state === 'focus' && researchPreview.evidenceQuality
          ? `${researchPreview.evidenceQuality} quality · ${researchPreview.figureCount} figures`
          : reportDocument
            ? `${reportDocument.figure_count} figures · ${Math.round(reportDocument.thesis.data_completeness * 100)}% complete`
            : (briefing?.primaryTheme ?? 'Awaiting report')} />
      </View>

      {reportDocument ? (
        <Text style={styles.documentMeta}>
          {reportDocument.market_date} · Generated {formatGeneratedAt(reportDocument.generated_at)} · {reportDocument.source_status} sources · {reportDocument.previous_report_available ? 'Previous comparison available' : 'Baseline report'}
        </Text>
      ) : null}

      <View style={styles.actions}>
        <Pressable
          accessibilityLabel={isGenerating ? 'Generating updated brief' : 'Generate updated brief'}
          accessibilityRole="button"
          disabled={isGenerating}
          onPress={onGenerate}
          style={({ pressed }) => [styles.primaryAction, pressed && styles.pressed, isGenerating && styles.disabled]}>
          <SymbolView name="arrow.clockwise" size={16} tintColor={Theme.colors.background} weight="bold" />
          <Text style={styles.primaryActionText}>{isGenerating ? 'Building Research…' : 'Generate Updated Research'}</Text>
        </Pressable>
        {latestRecord?.snapshot ? (
          <Pressable
            accessibilityLabel="Read today's briefing"
            accessibilityRole="button"
            onPress={() => onPreview(latestRecord)}
            style={({ pressed }) => [styles.secondaryAction, pressed && styles.pressed]}>
            <Text style={styles.secondaryActionText}>Read Research</Text>
            <SymbolView name="chevron.right" size={14} tintColor={Theme.colors.accent} weight="bold" />
          </Pressable>
        ) : null}
      </View>
      {generationMessage ? <Text style={styles.progressText}>{generationMessage}</Text> : null}
    </DashboardCard>
  );
}

function formatGeneratedAt(value: string) {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(parsed);
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
  disabled: { opacity: 0.55 },
  documentMeta: { color: Theme.colors.textMuted, fontSize: 11, fontWeight: '700', lineHeight: 16, marginTop: Spacing.two },
  eyebrow: { color: Theme.colors.accent, fontSize: 11, fontWeight: '900' },
  eyebrowRow: { alignItems: 'center', flexDirection: 'row', gap: Spacing.two },
  header: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between', marginBottom: Spacing.twoAndHalf },
  metric: { borderTopColor: Theme.colors.border, borderTopWidth: 1, flexBasis: '47%', gap: Spacing.one, minWidth: 140, paddingTop: Spacing.two },
  metricLabel: { color: Theme.colors.textMuted, fontSize: 11, fontWeight: '800' },
  metricValue: { color: Theme.colors.text, fontSize: 14, fontWeight: '900', lineHeight: 19 },
  metrics: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.three, marginTop: Spacing.three },
  marketThesis: { gap: Spacing.one, marginTop: Spacing.three },
  marketThesisLabel: { color: Theme.colors.textMuted, fontSize: 10, fontWeight: '900' },
  pressed: { opacity: 0.75 },
  primaryAction: { alignItems: 'center', backgroundColor: Theme.colors.accent, borderRadius: Theme.radii.small, flexDirection: 'row', gap: Spacing.two, minHeight: 44, paddingHorizontal: Spacing.three },
  primaryActionText: { color: Theme.colors.background, fontSize: 13, fontWeight: '900' },
  progressText: { color: Theme.colors.textMuted, fontSize: 12, fontWeight: '700', marginTop: Spacing.two },
  noResearch: { color: Theme.colors.textMuted, fontSize: 12, lineHeight: 18, marginTop: Spacing.two },
  researchFocus: { backgroundColor: Theme.colors.background, borderColor: Theme.colors.border, borderRadius: Theme.radii.small, borderWidth: 1, gap: Spacing.one, marginTop: Spacing.three, padding: Spacing.twoAndHalf },
  researchHeader: { alignItems: 'center', flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.two, justifyContent: 'space-between' },
  researchLabel: { color: Theme.colors.accent, fontSize: 10, fontWeight: '900' },
  researchEvolution: { color: Theme.colors.warning, fontSize: 11, fontWeight: '800', lineHeight: 16 },
  researchMeta: { color: Theme.colors.textMuted, fontSize: 11, fontWeight: '700' },
  researchTitle: { color: Theme.colors.text, fontSize: 16, fontWeight: '900' },
  researchWhy: { color: Theme.colors.text, fontSize: 12, lineHeight: 18 },
  secondaryAction: { alignItems: 'center', borderColor: Theme.colors.border, borderRadius: Theme.radii.small, borderWidth: 1, flexDirection: 'row', gap: Spacing.two, minHeight: 44, paddingHorizontal: Spacing.three },
  secondaryActionText: { color: Theme.colors.accent, fontSize: 13, fontWeight: '900' },
  thesis: { color: Theme.colors.text, fontSize: 16, fontWeight: '700', lineHeight: 24 },
  warningValue: { color: Theme.colors.warning },
});
