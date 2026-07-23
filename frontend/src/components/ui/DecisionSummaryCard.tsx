import { useState } from 'react';
import { Pressable, StyleSheet, Text, View, useWindowDimensions } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { availabilityLabel, confidenceLabel, FreshnessText, freshnessLabel } from '@/components/ui/ConfidenceFreshness';
import { ExpandableSection } from '@/components/ui/ExpandableSection';
import { StatusBadge, type Tone } from '@/components/ui/StatusBadge';
import { Spacing, Theme, Typography } from '@/constants/theme';
import type { DecisionSummary } from '@/features/trust/decisionSummary';

export function DecisionSummaryCard({ onPress, summary }: { onPress?: () => void; summary: DecisionSummary }) {
  const { width } = useWindowDimensions();
  const [measuredWidth, setMeasuredWidth] = useState<number | null>(null);
  const compact = Math.min(width, measuredWidth ?? width) < 560;
  const fields = [
    ['What changed', summary.whatChanged],
    ['Preferred posture', summary.preferredAction],
    ['Main risk', summary.mainRisk],
    ['Invalidation', summary.invalidation],
    ['What would change this view', summary.whatWouldChange],
  ].filter((item): item is [string, string] => Boolean(item[1]));
  const primaryContent = (
    <View accessibilityLabel={`${summary.title}. Current state: ${summary.currentState}. ${confidenceLabel({ confidence: summary.confidence, fallback: summary.confidenceLabel })}. ${freshnessLabel(summary.freshness)}.`} style={styles.stack}>
      <View style={[styles.header, compact && styles.headerCompact]}>
        <Text style={styles.state}>{summary.currentState}</Text>
        <View style={[styles.badges, compact && styles.badgesCompact]}>
          <StatusBadge label={confidenceLabel({ confidence: summary.confidence, fallback: summary.confidenceLabel })} tone={summary.confidence === null ? 'muted' : 'info'} />
          <StatusBadge label={availabilityLabel(summary.availability)} tone={availabilityTone(summary.availability)} />
        </View>
      </View>
      <View style={[styles.fields, compact && styles.fieldsCompact]}>
        {fields.map(([label, value]) => (
          <View key={label} style={[styles.field, compact && styles.fieldCompact]}>
            <Text style={styles.label}>{label}</Text>
            <Text style={styles.value}>{value}</Text>
          </View>
        ))}
      </View>
      {summary.contradiction ? <Text style={styles.contradiction}>{summary.contradiction}</Text> : null}
      <View style={styles.footer}>
        <FreshnessText value={summary.freshness} />
        {summary.evidence ? <Text style={styles.freshness}>{summary.evidence.availableCount}/{summary.evidence.totalCount} evidence classes usable</Text> : null}
      </View>
    </View>
  );
  return (
    <DashboardCard title={summary.title} accentColor={availabilityTone(summary.availability) === 'success' ? Theme.colors.success : Theme.colors.accent}>
      <View onLayout={(event) => setMeasuredWidth(event.nativeEvent.layout.width)} style={styles.stack}>
        {onPress ? (
          <Pressable accessibilityLabel={`Open details. ${summary.title}: ${summary.currentState}`} accessibilityRole="button" onPress={onPress}>
            {primaryContent}
          </Pressable>
        ) : primaryContent}
        {summary.methodology.length || summary.evidence ? (
          <ExpandableSection title="Evidence & methodology" summary="Sources, coverage, and limitations">
            <View style={styles.stack}>
              {summary.evidence?.classes.map((item) => (
                <Text key={item.id} style={styles.methodology}>{item.label}: {item.conclusion ?? 'Unavailable'} · {item.availability}</Text>
              ))}
              {summary.methodology.map((item) => <Text key={item} style={styles.methodology}>• {item}</Text>)}
            </View>
          </ExpandableSection>
        ) : null}
      </View>
    </DashboardCard>
  );
}

function availabilityTone(value: DecisionSummary['availability']): Tone {
  if (value === 'available' || value === 'live') return 'success';
  if (value === 'failed' || value === 'unavailable') return 'danger';
  if (value === 'loading') return 'muted';
  return 'warning';
}

const styles = StyleSheet.create({
  badges: { alignItems: 'flex-end', gap: Spacing.one },
  badgesCompact: { alignItems: 'flex-start' },
  contradiction: { backgroundColor: Theme.colors.warningSoft, borderRadius: Theme.radii.small, color: Theme.colors.warning, fontSize: Typography.small.fontSize, fontWeight: Typography.weights.strong, lineHeight: 18, padding: Spacing.two },
  field: { backgroundColor: Theme.colors.cardMuted, borderRadius: Theme.radii.small, flexBasis: '47%', flexGrow: 1, gap: Spacing.half, padding: Spacing.two },
  fieldCompact: { flexBasis: 'auto', width: '100%' },
  fields: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.one },
  fieldsCompact: { flexDirection: 'column' },
  footer: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.two, justifyContent: 'space-between' },
  freshness: { color: Theme.colors.textMuted, fontSize: Typography.caption.fontSize, fontWeight: Typography.weights.strong },
  header: { alignItems: 'flex-start', flexDirection: 'row', gap: Spacing.two, justifyContent: 'space-between' },
  headerCompact: { flexDirection: 'column' },
  label: { color: Theme.colors.textMuted, fontSize: Typography.chartLabel.fontSize, fontWeight: Typography.weights.strong, textTransform: 'uppercase' },
  methodology: { color: Theme.colors.textMuted, fontSize: Typography.small.fontSize, fontWeight: Typography.weights.emphasis, lineHeight: 18 },
  stack: { gap: Spacing.two },
  state: { color: Theme.colors.text, flex: 1, fontSize: Typography.decisionState.fontSize, fontWeight: Typography.weights.heavy, lineHeight: Typography.decisionState.lineHeight },
  value: { color: Theme.colors.text, fontSize: Typography.small.fontSize, fontWeight: Typography.weights.strong, lineHeight: 18 },
});
