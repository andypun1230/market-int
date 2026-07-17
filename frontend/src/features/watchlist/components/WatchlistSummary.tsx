import { StyleSheet, Text, View } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { Spacing, Theme } from '@/constants/theme';
import type { ClassifiedWatchlistItem } from '@/features/watchlist/types';

type WatchlistSummaryProps = {
  items: ClassifiedWatchlistItem[];
};

export function WatchlistSummary({ items }: WatchlistSummaryProps) {
  const validMoves = items
    .map((item) => item.item.change_percent)
    .filter((value): value is number => typeof value === 'number');
  const advancing = validMoves.filter((value) => value > 0).length;
  const declining = validMoves.filter((value) => value < 0).length;
  const averageMove = validMoves.length
    ? validMoves.reduce((sum, value) => sum + value, 0) / validMoves.length
    : null;
  const needsAttention = items.filter((item) => item.classification.group === 'needs_attention').length;
  const highPriority = items.filter((item) => item.classification.group === 'high_priority').length;

  return (
    <DashboardCard style={styles.card}>
      <View style={styles.headerRow}>
        <View>
          <Text style={styles.title}>Watchlist Dashboard</Text>
          <Text style={styles.subtitle}>Average move, not portfolio performance</Text>
        </View>
        <Text style={styles.count}>{items.length} Stocks</Text>
      </View>
      <View style={styles.metricRow}>
        <CompactMetric label="Avg" tone={getMoveTone(averageMove)} value={averageMove === null ? 'N/A' : formatPercent(averageMove)} />
        <CompactMetric label="Adv" tone="success" value={advancing} />
        <CompactMetric label="Dec" tone="danger" value={declining} />
        <CompactMetric label="Attention" tone={needsAttention ? 'warning' : 'muted'} value={needsAttention} />
        <CompactMetric label="Priority" tone={highPriority ? 'info' : 'muted'} value={highPriority} />
      </View>
    </DashboardCard>
  );
}

function CompactMetric({
  label,
  tone,
  value,
}: {
  label: string;
  tone: 'danger' | 'info' | 'muted' | 'success' | 'warning';
  value: number | string;
}) {
  return (
    <View style={styles.metric}>
      <Text style={styles.metricLabel}>{label}</Text>
      <Text numberOfLines={1} style={[styles.metricValue, { color: getToneColor(tone) }]}>{value}</Text>
    </View>
  );
}

function formatPercent(value: number) {
  const prefix = value > 0 ? '+' : '';
  return `${prefix}${value.toFixed(2)}%`;
}

function getMoveTone(value: number | null) {
  if (value === null) {
    return 'muted';
  }
  if (value > 0) {
    return 'success';
  }
  if (value < 0) {
    return 'danger';
  }
  return 'muted';
}

function getToneColor(tone: 'danger' | 'info' | 'muted' | 'success' | 'warning') {
  switch (tone) {
    case 'danger':
      return Theme.colors.danger;
    case 'info':
      return Theme.colors.accent;
    case 'success':
      return Theme.colors.success;
    case 'warning':
      return Theme.colors.warning;
    case 'muted':
      return Theme.colors.textMuted;
  }
}

const styles = StyleSheet.create({
  card: {
    padding: Spacing.twoAndHalf,
  },
  count: {
    color: Theme.colors.accent,
    fontSize: 12,
    fontWeight: '900',
  },
  headerRow: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
    marginBottom: Spacing.two,
  },
  metric: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    flex: 1,
    minWidth: 0,
    paddingHorizontal: Spacing.one,
    paddingVertical: Spacing.one,
  },
  metricLabel: {
    color: Theme.colors.textMuted,
    fontSize: 9,
    fontWeight: '900',
    textTransform: 'uppercase',
  },
  metricRow: {
    flexDirection: 'row',
    gap: Spacing.one,
  },
  metricValue: {
    fontSize: 12,
    fontWeight: '900',
    marginTop: Spacing.half,
  },
  subtitle: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '700',
    lineHeight: 15,
  },
  title: {
    color: Theme.colors.text,
    fontSize: 14,
    fontWeight: '900',
  },
});
