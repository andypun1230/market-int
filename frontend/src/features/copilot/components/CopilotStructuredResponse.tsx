import { useMemo, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { AppIcon } from '@/components/ui/AppIcon';
import { StatusBadge, type Tone } from '@/components/ui/StatusBadge';
import { Spacing, Theme, Typography } from '@/constants/theme';
import type {
  CopilotActionV1,
  CopilotChatResponse,
  CopilotEvidenceV1,
  CopilotSourceState,
} from '@/features/copilot/types';
import { evidenceFreshnessLabel, providerLabel } from '@/features/trust/confidenceFreshnessPresentation';

export function CopilotStructuredResponse({
  onAction,
  partial = false,
  response,
}: {
  onAction: (action: CopilotActionV1) => void;
  partial?: boolean;
  response: CopilotChatResponse;
}) {
  const reasoning = response.reasoning;
  const sections = response.answerSections;
  const supportingEvidence = (response.evidence ?? []).filter((item) => item.stance !== 'contradicts');
  const opposingEvidence = [
    ...(response.contradictoryEvidence ?? []),
    ...(response.evidence ?? []).filter((item) => item.stance === 'contradicts'),
  ];
  const supportingFactors = reasoning?.supportingFactors?.length
    ? reasoning.supportingFactors.map((item) => item.statement)
    : sections?.evidenceFor?.length ? sections.evidenceFor : sections?.why ?? [];
  const opposingFactors = reasoning?.contradictoryFactors?.length
    ? reasoning.contradictoryFactors.map((item) => item.statement)
    : sections?.evidenceAgainst ?? [];
  const risks = reasoning?.keyRisks?.length
    ? reasoning.keyRisks.map((item) => item.statement)
    : sections?.keyRisks?.length ? sections.keyRisks : sections?.mainCaution ? [sections.mainCaution] : [];
  const confirms = reasoning?.confirmationConditions?.length
    ? reasoning.confirmationConditions.map((item) => item.statement)
    : sections?.whatWouldConfirm?.length ? sections.whatWouldConfirm : sections?.whatWouldChange ?? [];
  const invalidates = reasoning?.invalidationConditions?.length
    ? reasoning.invalidationConditions.map((item) => item.statement)
    : sections?.whatWouldInvalidate ?? [];
  const missing = unique([...(response.missingEvidence ?? []), ...(reasoning?.missingEvidence ?? []), ...(sections?.missingEvidence ?? [])]);
  const contradictions = unique([...(reasoning?.contradictions ?? []), ...opposingFactors]);
  const isChallenge = opposingEvidence.length > 0 || opposingFactors.length > 0 || contradictions.length > 0;

  return (
    <View accessibilityLiveRegion={partial ? 'polite' : 'none'} style={styles.responseCard}>
      <View style={styles.responseTopline}>
        <View style={styles.badgeRow}>
          {reasoning?.stance ? <StatusBadge label={reasoning.stance} showDot={false} tone={stanceTone(reasoning.stance)} /> : null}
          <CopilotConfidence response={response} />
          <CopilotFreshnessBadge sourceState={response.freshnessSummary?.overallState ?? response.grounding.sourceState} />
        </View>
        {response.intent?.intent ? <Text style={styles.intentLabel}>{humanize(response.intent.intent)}</Text> : null}
      </View>

      {partial || response.status === 'partial' ? (
        <CopilotPartialDataNotice message="This answer is partial. Completed sections remain visible; missing evidence is not inferred." />
      ) : null}

      <CopilotDirectAnswer answer={reasoning?.directAnswer || sections?.directAnswer || response.answer} />

      {supportingEvidence.length || supportingFactors.length ? (
        <CopilotEvidenceGroup
          evidence={supportingEvidence}
          fallbackItems={supportingFactors}
          title="Evidence supporting"
          tone="support"
        />
      ) : null}

      {isChallenge ? (
        <View style={styles.challengePanel}>
          <Text style={styles.challengeEyebrow}>CHALLENGE MODE</Text>
          <CopilotEvidenceGroup
            evidence={opposingEvidence}
            fallbackItems={opposingFactors}
            title="Evidence against"
            tone="oppose"
          />
          {contradictions.length ? <CopilotContradiction items={contradictions} /> : null}
        </View>
      ) : null}

      {risks.length ? <CompactList items={risks} title="Key risk" tone="warning" /> : null}

      {confirms.length || invalidates.length ? (
        <CopilotConditionList confirmation={confirms} invalidation={invalidates} />
      ) : null}

      {missing.length ? (
        <CopilotPartialDataNotice
          label="MISSING EVIDENCE"
          message={missing.join(' · ')}
        />
      ) : null}

      {response.warnings?.length ? <CompactList items={response.warnings} title="Data warnings" tone="warning" /> : null}

      {response.actions?.length ? <CopilotDeepLinkActions actions={response.actions} onAction={onAction} /> : null}

      <CopilotSourceList response={response} />
    </View>
  );
}

export function CopilotDirectAnswer({ answer }: { answer: string }) {
  return (
    <View style={styles.directAnswer}>
      <Text style={styles.eyebrow}>DIRECT ANSWER</Text>
      <Text style={styles.directAnswerText}>{answer}</Text>
    </View>
  );
}

export function CopilotConfidence({ response }: { response: CopilotChatResponse }) {
  const level = response.answerConfidence?.level ?? confidenceLevel(response.confidence);
  return <StatusBadge label={`${humanize(level)} confidence`} showDot={false} tone={level === 'high' ? 'success' : level === 'limited' ? 'warning' : 'purple'} />;
}

export function CopilotFreshnessBadge({ sourceState }: { sourceState: CopilotSourceState }) {
  return <StatusBadge label={evidenceFreshnessLabel(sourceState)} tone={freshnessTone(sourceState)} />;
}

export function CopilotPartialDataNotice({
  label = 'PARTIAL DATA',
  message,
}: {
  label?: string;
  message: string;
}) {
  return (
    <View accessibilityRole="alert" style={styles.partialNotice}>
      <Text style={styles.partialLabel}>{label}</Text>
      <Text style={styles.partialText}>{message}</Text>
    </View>
  );
}

export function CopilotEvidenceGroup({
  evidence,
  fallbackItems,
  title,
  tone,
}: {
  evidence: CopilotEvidenceV1[];
  fallbackItems: string[];
  title: string;
  tone: 'support' | 'oppose';
}) {
  const [expanded, setExpanded] = useState(false);
  const rows = expanded ? evidence : evidence.slice(0, 3);
  const fallback = expanded ? fallbackItems : fallbackItems.slice(0, 3);
  return (
    <View style={styles.section}>
      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>{title.toUpperCase()}</Text>
        {evidence.length > 3 || fallbackItems.length > 3 ? (
          <InlineAction label={expanded ? 'Show less' : 'Show all'} onPress={() => setExpanded((current) => !current)} />
        ) : null}
      </View>
      {rows.length ? rows.map((item) => <EvidenceRow evidence={item} key={item.evidenceId} tone={tone} />) : fallback.map((item, index) => (
        <View key={`${title}-${index}`} style={styles.factorRow}>
          <View style={[styles.factorMarker, tone === 'oppose' ? styles.opposeMarker : styles.supportMarker]} />
          <Text style={styles.factorText}>{item}</Text>
        </View>
      ))}
    </View>
  );
}

export function CopilotContradiction({ items }: { items: string[] }) {
  return (
    <View style={styles.contradiction}>
      <Text style={styles.contradictionLabel}>IMPORTANT CONTRADICTION</Text>
      {items.slice(0, 4).map((item, index) => <Text key={`${item}-${index}`} style={styles.contradictionText}>• {item}</Text>)}
    </View>
  );
}

export function CopilotConditionList({
  confirmation,
  invalidation,
}: {
  confirmation: string[];
  invalidation: string[];
}) {
  return (
    <View style={styles.conditionGrid}>
      <View style={[styles.conditionPanel, styles.confirmPanel]}>
        <Text style={styles.confirmLabel}>WHAT CONFIRMS</Text>
        {confirmation.length ? confirmation.slice(0, 5).map((item, index) => <Text key={`${item}-${index}`} style={styles.conditionText}>• {item}</Text>) : <Text style={styles.muted}>No validated confirmation condition is available.</Text>}
      </View>
      <View style={[styles.conditionPanel, styles.invalidatePanel]}>
        <Text style={styles.invalidateLabel}>WHAT INVALIDATES</Text>
        {invalidation.length ? invalidation.slice(0, 5).map((item, index) => <Text key={`${item}-${index}`} style={styles.conditionText}>• {item}</Text>) : <Text style={styles.muted}>No validated invalidation condition is available.</Text>}
      </View>
    </View>
  );
}

export function CopilotDeepLinkActions({
  actions,
  onAction,
}: {
  actions: CopilotActionV1[];
  onAction: (action: CopilotActionV1) => void;
}) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>OPEN IN APP</Text>
      <View style={styles.actionRow}>
        {actions.slice(0, 6).map((action, index) => (
          <Pressable
            accessibilityHint="Opens the cited destination with its current entity and section selected"
            accessibilityLabel={action.entity ? `${action.label} ${action.entity}` : action.label}
            accessibilityRole="button"
            key={action.actionId ?? `${action.label}-${index}`}
            onPress={() => onAction(action)}
            style={({ pressed }) => [styles.deepLinkButton, pressed && styles.pressed]}>
            <Text style={styles.deepLinkText}>{action.entity ? `${action.label} · ${action.entity}` : action.label}</Text>
            <AppIcon name="chevronRight" size={16} />
          </Pressable>
        ))}
      </View>
    </View>
  );
}

export function CopilotSourceList({ response }: { response: CopilotChatResponse }) {
  const [expanded, setExpanded] = useState(false);
  const sources = useMemo(() => unique([
    ...(response.grounding.providers ?? []),
    ...(response.evidence ?? []).map((item) => sourceLabel(item)).filter(Boolean),
    ...(response.contradictoryEvidence ?? []).map((item) => sourceLabel(item)).filter(Boolean),
  ]), [response]);
  const evidenceIds = unique([
    ...(response.grounding.evidenceIds ?? []),
    ...(response.evidence ?? []).map((item) => item.evidenceId),
    ...(response.contradictoryEvidence ?? []).map((item) => item.evidenceId),
  ]);
  const marketDate = response.freshnessSummary?.marketDates[0] ?? response.grounding.marketDate;
  return (
    <View style={styles.sources}>
      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>SOURCES & FRESHNESS</Text>
        <InlineAction label={expanded ? 'Hide' : 'Details'} onPress={() => setExpanded((current) => !current)} />
      </View>
      <Text style={styles.sourceSummary}>
        {marketDate ? `Market date ${marketDate} · ` : ''}{response.grounding.generatedAt ? `Generated ${formatTimestamp(response.grounding.generatedAt)}` : 'Timestamp unavailable'}
      </Text>
      {expanded ? (
        <View style={styles.sourceDetails}>
          <Text style={styles.sourceText}>Context: {response.grounding.contextUsed.join(', ') || 'No app context cited'}</Text>
          <Text style={styles.sourceText}>Providers: {sources.join(', ') || 'Provider unavailable'}</Text>
          <Text style={styles.sourceText}>Evidence IDs: {evidenceIds.join(', ') || 'No evidence IDs supplied'}</Text>
          {response.answerConfidence?.reasons.length ? <Text style={styles.sourceText}>Confidence: {response.answerConfidence.reasons.join(' · ')}</Text> : null}
        </View>
      ) : null}
    </View>
  );
}

function EvidenceRow({ evidence, tone }: { evidence: CopilotEvidenceV1; tone: 'support' | 'oppose' }) {
  const value = formatEvidenceValue(evidence);
  return (
    <View style={[styles.evidenceCard, tone === 'oppose' ? styles.evidenceOppose : styles.evidenceSupport]}>
      <View style={styles.evidenceHeader}>
        <View style={styles.evidenceHeading}>
          <Text style={styles.evidenceMetric}>{evidence.metric || evidence.category}</Text>
          {evidence.entity ? <Text style={styles.evidenceEntity}>{evidence.entity}</Text> : null}
        </View>
        {value ? <Text style={styles.evidenceValue}>{value}</Text> : null}
      </View>
      {evidence.currentState ? <Text style={styles.evidenceState}>{evidence.currentState}</Text> : null}
      {evidence.interpretation ? <Text style={styles.evidenceInterpretation}>{evidence.interpretation}</Text> : null}
      <View style={styles.evidenceMetaRow}>
        <CopilotFreshnessBadge sourceState={evidence.freshness.state} />
        <Text style={styles.evidenceMeta}>{evidence.timeframe || evidence.freshness.marketDate || 'Current snapshot'} · {evidence.evidenceId}</Text>
      </View>
    </View>
  );
}

function CompactList({ items, title, tone }: { items: string[]; title: string; tone: 'warning' | 'neutral' }) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title.toUpperCase()}</Text>
      {items.slice(0, 5).map((item, index) => (
        <View key={`${title}-${item}-${index}`} style={styles.factorRow}>
          <View style={[styles.factorMarker, tone === 'warning' ? styles.warningMarker : styles.neutralMarker]} />
          <Text style={styles.factorText}>{item}</Text>
        </View>
      ))}
    </View>
  );
}

function InlineAction({ label, onPress }: { label: string; onPress: () => void }) {
  return (
    <Pressable accessibilityLabel={label} accessibilityRole="button" hitSlop={8} onPress={onPress}>
      <Text style={styles.inlineAction}>{label}</Text>
    </Pressable>
  );
}

function confidenceLevel(confidence: number) {
  return confidence >= 80 ? 'high' : confidence < 55 ? 'limited' : 'moderate';
}

function sourceLabel(evidence: CopilotEvidenceV1) {
  const { dataset, provider } = evidence.source;
  const displayProvider = providerLabel(provider);
  return dataset && dataset !== 'app-engine' ? `${displayProvider} / ${dataset}` : displayProvider;
}

function freshnessTone(state: CopilotSourceState): Tone {
  if (state === 'live') return 'success';
  if (state === 'cached' || state === 'mixed') return 'info';
  if (state === 'stale' || state === 'test' || state === 'mock' || state === 'partial' || state === 'delayed') return 'warning';
  return 'muted';
}

function stanceTone(stance: string): Tone {
  const normalized = stance.toLowerCase();
  if (normalized.includes('actionable') || normalized.includes('constructive')) return 'success';
  if (normalized.includes('avoid') || normalized.includes('defensive')) return 'danger';
  if (normalized.includes('wait') || normalized.includes('cautious')) return 'warning';
  return 'info';
}

function formatEvidenceValue(evidence: CopilotEvidenceV1) {
  if (evidence.value === null || evidence.value === undefined || evidence.value === '') return '';
  const formatted = typeof evidence.value === 'number'
    ? Number.isInteger(evidence.value) ? String(evidence.value) : evidence.value.toFixed(2)
    : String(evidence.value);
  return `${formatted}${evidence.unit ? ` ${evidence.unit}` : ''}`;
}

function formatTimestamp(value: string) {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

function humanize(input: string) {
  return input.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function unique(items: string[]) {
  return [...new Set(items.map((item) => item.trim()).filter(Boolean))];
}

const styles = StyleSheet.create({
  actionRow: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.one },
  badgeRow: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.one },
  challengeEyebrow: { color: Theme.colors.warning, fontSize: Typography.caption.fontSize, fontWeight: Typography.weights.strong, letterSpacing: 0.7 },
  challengePanel: { backgroundColor: Theme.colors.warningSoft, borderColor: Theme.colors.warning, borderRadius: Theme.radii.small, borderWidth: 1, gap: Spacing.two, padding: Spacing.twoAndHalf },
  conditionGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.two },
  conditionPanel: { borderRadius: Theme.radii.small, borderWidth: 1, flexBasis: 260, flexGrow: 1, gap: Spacing.one, padding: Spacing.twoAndHalf },
  conditionText: { color: Theme.colors.text, fontSize: Typography.control.fontSize, fontWeight: Typography.weights.emphasis, lineHeight: 19 },
  confirmLabel: { color: Theme.colors.success, fontSize: Typography.caption.fontSize, fontWeight: Typography.weights.strong },
  confirmPanel: { backgroundColor: Theme.colors.successSoft, borderColor: Theme.colors.success },
  contradiction: { backgroundColor: Theme.colors.dangerSoft, borderLeftColor: Theme.colors.danger, borderLeftWidth: 3, borderRadius: Theme.radii.small, gap: Spacing.one, padding: Spacing.two },
  contradictionLabel: { color: Theme.colors.danger, fontSize: Typography.caption.fontSize, fontWeight: Typography.weights.strong },
  contradictionText: { color: Theme.colors.text, fontSize: Typography.control.fontSize, fontWeight: Typography.weights.emphasis, lineHeight: 19 },
  deepLinkArrow: { color: Theme.colors.accent, fontSize: Typography.sectionTitle.fontSize, fontWeight: Typography.weights.strong },
  deepLinkButton: { alignItems: 'center', backgroundColor: Theme.colors.card, borderColor: Theme.colors.accent, borderRadius: Theme.radii.pill, borderWidth: 1, flexDirection: 'row', gap: Spacing.one, minHeight: 38, paddingHorizontal: Spacing.twoAndHalf, paddingVertical: Spacing.one },
  deepLinkText: { color: Theme.colors.accent, fontSize: Typography.small.fontSize, fontWeight: Typography.weights.strong },
  directAnswer: { borderLeftColor: Theme.colors.purple, borderLeftWidth: 3, gap: Spacing.one, paddingLeft: Spacing.twoAndHalf },
  directAnswerText: { color: Theme.colors.text, fontSize: Typography.supportTitle.fontSize, fontWeight: Typography.weights.strong, lineHeight: 24 },
  evidenceCard: { borderRadius: Theme.radii.small, borderWidth: 1, gap: Spacing.one, padding: Spacing.two },
  evidenceEntity: { color: Theme.colors.textMuted, fontSize: Typography.caption.fontSize, fontWeight: Typography.weights.strong },
  evidenceHeading: { flex: 1, gap: 2, minWidth: 0 },
  evidenceHeader: { alignItems: 'flex-start', flexDirection: 'row', gap: Spacing.two, justifyContent: 'space-between' },
  evidenceInterpretation: { color: Theme.colors.text, fontSize: Typography.control.fontSize, fontWeight: Typography.weights.emphasis, lineHeight: 19 },
  evidenceMeta: { color: Theme.colors.textMuted, flex: 1, fontSize: Typography.chartLabel.fontSize, fontWeight: Typography.weights.emphasis },
  evidenceMetaRow: { alignItems: 'center', flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.one },
  evidenceMetric: { color: Theme.colors.text, fontSize: Typography.control.fontSize, fontWeight: Typography.weights.strong },
  evidenceOppose: { backgroundColor: Theme.colors.dangerSoft, borderColor: Theme.colors.danger },
  evidenceState: { color: Theme.colors.textMuted, fontSize: Typography.small.fontSize, fontWeight: Typography.weights.strong },
  evidenceSupport: { backgroundColor: Theme.colors.successSoft, borderColor: Theme.colors.success },
  evidenceValue: { color: Theme.colors.text, fontSize: Typography.body.fontSize, fontWeight: Typography.weights.strong },
  eyebrow: { color: Theme.colors.purple, fontSize: Typography.caption.fontSize, fontWeight: Typography.weights.strong, letterSpacing: 0.7 },
  factorMarker: { borderRadius: 3, height: 6, marginTop: 7, width: 6 },
  factorRow: { alignItems: 'flex-start', flexDirection: 'row', gap: Spacing.one },
  factorText: { color: Theme.colors.text, flex: 1, fontSize: Typography.control.fontSize, fontWeight: Typography.weights.emphasis, lineHeight: 19 },
  inlineAction: { color: Theme.colors.accent, fontSize: Typography.caption.fontSize, fontWeight: Typography.weights.strong },
  intentLabel: { color: Theme.colors.textMuted, fontSize: Typography.chartLabel.fontSize, fontWeight: Typography.weights.strong },
  invalidateLabel: { color: Theme.colors.danger, fontSize: Typography.caption.fontSize, fontWeight: Typography.weights.strong },
  invalidatePanel: { backgroundColor: Theme.colors.dangerSoft, borderColor: Theme.colors.danger },
  muted: { color: Theme.colors.textMuted, fontSize: Typography.small.fontSize, fontWeight: Typography.weights.emphasis, lineHeight: 18 },
  neutralMarker: { backgroundColor: Theme.colors.textMuted },
  opposeMarker: { backgroundColor: Theme.colors.danger },
  partialLabel: { color: Theme.colors.warning, fontSize: Typography.caption.fontSize, fontWeight: Typography.weights.strong },
  partialNotice: { backgroundColor: Theme.colors.warningSoft, borderColor: Theme.colors.warning, borderRadius: Theme.radii.small, borderWidth: 1, gap: 4, padding: Spacing.two },
  partialText: { color: Theme.colors.text, fontSize: Typography.small.fontSize, fontWeight: Typography.weights.emphasis, lineHeight: 18 },
  pressed: { opacity: 0.74 },
  responseCard: { backgroundColor: Theme.colors.cardMuted, borderColor: Theme.colors.border, borderRadius: Theme.radii.card, borderWidth: 1, gap: Spacing.three, padding: Spacing.three },
  responseTopline: { alignItems: 'flex-start', flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.two, justifyContent: 'space-between' },
  section: { gap: Spacing.two },
  sectionHeader: { alignItems: 'center', flexDirection: 'row', gap: Spacing.two, justifyContent: 'space-between' },
  sectionTitle: { color: Theme.colors.textMuted, fontSize: Typography.caption.fontSize, fontWeight: Typography.weights.strong, letterSpacing: 0.5 },
  sourceDetails: { gap: Spacing.one },
  sourceSummary: { color: Theme.colors.textMuted, fontSize: Typography.caption.fontSize, fontWeight: Typography.weights.emphasis },
  sourceText: { color: Theme.colors.textMuted, fontSize: Typography.caption.fontSize, fontWeight: Typography.weights.emphasis, lineHeight: 16 },
  sources: { borderTopColor: Theme.colors.border, borderTopWidth: 1, gap: Spacing.one, paddingTop: Spacing.two },
  supportMarker: { backgroundColor: Theme.colors.success },
  warningMarker: { backgroundColor: Theme.colors.warning },
});
