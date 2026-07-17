import { StyleSheet, Text, View } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { StatusBadge, type Tone } from '@/components/ui/StatusBadge';
import { TestDataBadge } from '@/components/ui/TestDataBadge';
import { Spacing, Theme } from '@/constants/theme';
import {
  buildDivergenceAccessibilitySummary,
  buildDivergenceEvidenceRows,
  type DivergenceEvidenceRow,
  type DivergenceSignal,
} from '@/features/sectors/analysis/divergence';

export function DivergenceBadge({ count }: { count: number }) {
  if (!count) {
    return null;
  }
  return <StatusBadge label={`${count} Divergence${count > 1 ? 's' : ''}`} tone="warning" />;
}

export function DivergenceCard({ signals }: { signals: DivergenceSignal[] }) {
  return (
    <DashboardCard title="Divergences" subtitle="Price, breadth, and momentum moving in different directions." accentColor={Theme.colors.warning}>
      <View style={styles.header}>
        <TestDataBadge />
      </View>
      <View style={styles.stack}>
        {signals.length ? (
          signals.map((signal) => (
            <View
              accessibilityLabel={buildDivergenceAccessibilitySummary(signal)}
              accessibilityRole="summary"
              key={signal.id}
              style={styles.signal}
            >
              <View style={styles.signalHeader}>
                <Text style={styles.title}>{signal.title}</Text>
                <View style={styles.badges}>
                  <StatusBadge label={formatSeverity(signal.severity)} tone={getSeverityTone(signal.severity)} />
                  <StatusBadge label={formatDirection(signal.direction)} tone={getDirectionTone(signal.direction)} />
                </View>
              </View>
              <Text style={styles.summary}>{signal.summary}</Text>
              <View style={styles.evidenceStack}>
                {buildDivergenceEvidenceRows(signal).map((row) => (
                  <EvidenceRow key={`${signal.id}-${row.label}`} row={row} />
                ))}
              </View>
              <View style={styles.implication}>
                <Text style={styles.implicationLabel}>What it means</Text>
                <Text style={styles.implicationText}>{signal.implication}</Text>
              </View>
            </View>
          ))
        ) : (
          <Text style={styles.empty}>No rule-based divergences in the current test window.</Text>
        )}
      </View>
    </DashboardCard>
  );
}

function EvidenceRow({ row }: { row: DivergenceEvidenceRow }) {
  return (
    <View style={styles.evidenceRow}>
      <Text style={styles.evidenceLabel}>{row.label}</Text>
      <View style={styles.evidenceValues}>
        <Text style={[styles.evidencePrimary, { color: getEvidenceColor(row.tone) }]}>{row.primary}</Text>
        {row.secondary ? <Text style={styles.evidenceSecondary}>{row.secondary}</Text> : null}
      </View>
    </View>
  );
}

function getSeverityTone(severity: DivergenceSignal['severity']): Tone {
  if (severity === 'high') {
    return 'danger';
  }
  if (severity === 'medium') {
    return 'warning';
  }
  return 'info';
}

function getDirectionTone(direction: DivergenceSignal['direction']): Tone {
  if (direction === 'positive') {
    return 'success';
  }
  if (direction === 'negative') {
    return 'danger';
  }
  return 'warning';
}

function getEvidenceColor(tone: DivergenceEvidenceRow['tone']) {
  if (tone === 'positive') {
    return Theme.colors.success;
  }
  if (tone === 'negative') {
    return Theme.colors.danger;
  }
  if (tone === 'mixed') {
    return Theme.colors.warning;
  }
  return Theme.colors.text;
}

function formatSeverity(severity: DivergenceSignal['severity']) {
  return severity.charAt(0).toUpperCase() + severity.slice(1);
}

function formatDirection(direction: DivergenceSignal['direction']) {
  return direction.charAt(0).toUpperCase() + direction.slice(1);
}

const styles = StyleSheet.create({
  badges: {
    alignItems: 'center',
    flexDirection: 'row',
    flexShrink: 0,
    flexWrap: 'wrap',
    gap: Spacing.one,
    justifyContent: 'flex-end',
  },
  empty: {
    color: Theme.colors.textMuted,
    fontSize: 13,
    fontWeight: '800',
  },
  evidenceLabel: {
    color: Theme.colors.textMuted,
    flex: 1,
    fontSize: 11,
    fontWeight: '800',
  },
  evidencePrimary: {
    fontSize: 12,
    fontWeight: '900',
    textAlign: 'right',
  },
  evidenceRow: {
    alignItems: 'center',
    backgroundColor: Theme.colors.card,
    borderRadius: Theme.radii.small,
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
    paddingHorizontal: Spacing.two,
    paddingVertical: Spacing.one,
  },
  evidenceSecondary: {
    color: Theme.colors.textMuted,
    fontSize: 10,
    fontWeight: '800',
    textAlign: 'right',
  },
  evidenceStack: {
    gap: Spacing.one,
  },
  evidenceValues: {
    alignItems: 'flex-end',
    flexShrink: 0,
    gap: Spacing.half,
    maxWidth: '56%',
  },
  header: {
    marginBottom: Spacing.two,
  },
  implication: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    gap: Spacing.half,
    padding: Spacing.two,
  },
  implicationLabel: {
    color: Theme.colors.textMuted,
    fontSize: 10,
    fontWeight: '900',
    textTransform: 'uppercase',
  },
  implicationText: {
    color: Theme.colors.text,
    fontSize: 12,
    fontWeight: '700',
    lineHeight: 17,
  },
  signal: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    gap: Spacing.one,
    padding: Spacing.two,
  },
  signalHeader: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  stack: {
    gap: Spacing.two,
  },
  summary: {
    color: Theme.colors.text,
    fontSize: 13,
    fontWeight: '700',
    lineHeight: 18,
  },
  title: {
    color: Theme.colors.text,
    flex: 1,
    fontSize: 14,
    fontWeight: '900',
  },
});
