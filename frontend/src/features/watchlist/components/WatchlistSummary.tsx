import { StyleSheet, Text, View } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { Spacing, Theme } from '@/constants/theme';
import { buildWatchlistDecisionBrief } from '@/features/watchlist/watchlistDecision';
import type { ClassifiedWatchlistItem } from '@/features/watchlist/types';

export function WatchlistBrief({ items }: { items: ClassifiedWatchlistItem[] }) {
  const brief = buildWatchlistDecisionBrief(items);
  return (
    <DashboardCard style={styles.card}>
      <View style={styles.headerRow}>
        <View style={styles.titleBlock}>
          <Text style={styles.title}>Today&apos;s Watchlist Brief</Text>
          <Text style={styles.subtitle}>Where today&apos;s attention is concentrated</Text>
        </View>
        <Text style={styles.count}>{items.length} stocks</Text>
      </View>
      <View style={styles.metrics}>
        <BriefMetric
          detail={symbolSummary(brief.immediateSymbols)}
          label="Action now"
          tone="danger"
          value={brief.immediateCount}
        />
        <BriefMetric
          detail={symbolSummary(brief.improvingSymbols)}
          label="Improving"
          tone="success"
          value={brief.improvingCount}
        />
        <BriefMetric
          detail={symbolSummary(brief.deterioratingSymbols)}
          label="Deteriorating"
          tone="warning"
          value={brief.deterioratingCount}
        />
      </View>
      {brief.staleCount ? (
        <View style={styles.staleWarning}>
          <Text style={styles.staleIcon}>!</Text>
          <Text style={styles.staleText}>
            {brief.staleCount} {brief.staleCount === 1 ? 'stock has' : 'stocks have'} stale data. Refresh before acting.
          </Text>
        </View>
      ) : null}
    </DashboardCard>
  );
}

function BriefMetric({
  detail,
  label,
  tone,
  value,
}: {
  detail: string;
  label: string;
  tone: 'danger' | 'success' | 'warning';
  value: number;
}) {
  return (
    <View style={styles.metric}>
      <View style={styles.metricTop}>
        <View style={[styles.toneDot, { backgroundColor: Theme.colors[tone] }]} />
        <Text style={styles.metricLabel}>{label}</Text>
      </View>
      <Text style={[styles.metricValue, { color: Theme.colors[tone] }]}>{value}</Text>
      <Text numberOfLines={1} style={styles.metricDetail}>{detail}</Text>
    </View>
  );
}

function symbolSummary(symbols: string[]) {
  return symbols.length ? symbols.join(', ') : 'None';
}

const styles = StyleSheet.create({
  card: {
    padding: Spacing.twoAndHalf,
  },
  count: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '900',
    textTransform: 'uppercase',
  },
  headerRow: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  metric: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    flex: 1,
    minWidth: 0,
    padding: Spacing.two,
  },
  metricDetail: {
    color: Theme.colors.textMuted,
    fontSize: 10,
    fontWeight: '800',
    marginTop: Spacing.half,
  },
  metricLabel: {
    color: Theme.colors.textMuted,
    fontSize: 10,
    fontWeight: '900',
    textTransform: 'uppercase',
  },
  metrics: {
    flexDirection: 'row',
    gap: Spacing.one,
    marginTop: Spacing.two,
  },
  metricTop: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.one,
  },
  metricValue: {
    fontSize: 22,
    fontWeight: '900',
    lineHeight: 26,
    marginTop: Spacing.half,
  },
  staleIcon: {
    color: Theme.colors.warning,
    fontSize: 12,
    fontWeight: '900',
  },
  staleText: {
    color: Theme.colors.warning,
    flex: 1,
    fontSize: 11,
    fontWeight: '800',
  },
  staleWarning: {
    alignItems: 'center',
    backgroundColor: Theme.colors.warningSoft,
    borderColor: Theme.colors.warning,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    flexDirection: 'row',
    gap: Spacing.one,
    marginTop: Spacing.two,
    paddingHorizontal: Spacing.two,
    paddingVertical: Spacing.one,
  },
  subtitle: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '700',
  },
  title: {
    color: Theme.colors.text,
    fontSize: 15,
    fontWeight: '900',
  },
  titleBlock: {
    gap: Spacing.half,
  },
  toneDot: {
    borderRadius: Theme.radii.pill,
    height: 6,
    width: 6,
  },
});
