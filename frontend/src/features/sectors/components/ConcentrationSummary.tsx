import { StyleSheet, Text, View } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { ProgressBar } from '@/components/ui/ProgressBar';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { TestDataBadge } from '@/components/ui/TestDataBadge';
import { Spacing, Theme, Typography } from '@/constants/theme';
import type { LeadershipConcentration } from '@/features/sectors/analysis/concentration';

export function ConcentrationSummary({ concentration }: { concentration: LeadershipConcentration }) {
  return (
    <DashboardCard
      title="Leadership Concentration"
      subtitle="Shows whether performance is supported by many constituents or only a few large contributors."
      accentColor={Theme.colors.purple}>
      <View style={styles.header}>
        <StatusBadge label={concentration.label} tone={getTone(concentration.label)} />
        <TestDataBadge />
      </View>

      <View style={styles.stack}>
        <ProgressBar label="Top 1 Contribution" value={concentration.top1ContributionPercent} tone={getTone(concentration.label)} />
        <ProgressBar label="Top 3 Contribution" value={concentration.top3ContributionPercent} tone={getTone(concentration.label)} />
        <ProgressBar label="Top 5 Contribution" value={concentration.top5ContributionPercent} tone={getTone(concentration.label)} />
      </View>

      <View style={styles.metricGrid}>
        <Metric label="Weighted Return" value={formatPercent(concentration.weightedReturn)} />
        <Metric label="Equal Weight Return" value={formatPercent(concentration.equalWeightReturn)} />
        <Metric label="Median Return" value={formatPercent(concentration.medianConstituentReturn)} />
        <Metric label="Outperforming" value={`${concentration.percentOutperformingGroup.toFixed(1)}%`} />
      </View>

      <View style={styles.contributorList}>
        <Text style={styles.sectionTitle}>Top Contributors</Text>
        {concentration.topContributors.map((item) => (
          <View key={item.ticker} style={styles.contributorRow}>
            <Text style={styles.ticker}>{item.ticker}</Text>
            <Text style={styles.contributorText}>
              Weight {item.weight.toFixed(1)}% · Return {formatPercent(item.return1M)} · Contribution {item.contributionShare.toFixed(1)}%
            </Text>
          </View>
        ))}
      </View>
    </DashboardCard>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.metric}>
      <Text style={styles.metricLabel}>{label}</Text>
      <Text style={styles.metricValue}>{value}</Text>
    </View>
  );
}

function getTone(label: LeadershipConcentration['label']) {
  if (label === 'Broad') {
    return 'success';
  }
  if (label === 'Moderate') {
    return 'info';
  }
  if (label === 'Concentrated') {
    return 'warning';
  }
  return 'danger';
}

function formatPercent(value: number) {
  const prefix = value > 0 ? '+' : '';
  return `${prefix}${value.toFixed(2)}%`;
}

const styles = StyleSheet.create({
  contributorList: {
    gap: Spacing.two,
    marginTop: Spacing.three,
  },
  contributorRow: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    gap: 2,
    padding: Spacing.two,
  },
  contributorText: {
    color: Theme.colors.textMuted,
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.strong,
  },
  header: {
    alignItems: 'center',
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
    marginBottom: Spacing.three,
  },
  metric: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    flexBasis: '47%',
    flexGrow: 1,
    gap: 2,
    padding: Spacing.two,
  },
  metricGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
    marginTop: Spacing.three,
  },
  metricLabel: {
    color: Theme.colors.textMuted,
    fontSize: Typography.chartLabel.fontSize,
    fontWeight: Typography.weights.strong,
    textTransform: 'uppercase',
  },
  metricValue: {
    color: Theme.colors.text,
    fontSize: Typography.body.fontSize,
    fontWeight: Typography.weights.strong,
  },
  sectionTitle: {
    color: Theme.colors.text,
    fontSize: Typography.control.fontSize,
    fontWeight: Typography.weights.strong,
  },
  stack: {
    gap: Spacing.two,
  },
  ticker: {
    color: Theme.colors.text,
    fontSize: Typography.control.fontSize,
    fontWeight: Typography.weights.strong,
  },
});
