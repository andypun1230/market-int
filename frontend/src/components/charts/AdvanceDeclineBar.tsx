import type { DimensionValue } from 'react-native';
import { StyleSheet, Text, View } from 'react-native';

import { Spacing, Theme, Typography } from '@/constants/theme';
import type { SectorBreadthSnapshot } from '@/data/sectorTabTestData';

export function AdvanceDeclineBar({ breadth }: { breadth: SectorBreadthSnapshot }) {
  const advancingWidth = toWidth(breadth.advancing, breadth.totalStocks);
  const decliningWidth = toWidth(breadth.declining, breadth.totalStocks);
  const unchangedWidth = toWidth(breadth.unchanged, breadth.totalStocks);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Advancers vs Decliners</Text>
      <View
        accessibilityLabel={`Advancing ${breadth.advancing}, declining ${breadth.declining}, unchanged ${breadth.unchanged}`}
        style={styles.track}>
        <View style={[styles.segment, styles.advancing, { width: advancingWidth }]} />
        <View style={[styles.segment, styles.declining, { width: decliningWidth }]} />
        <View style={[styles.segment, styles.unchanged, { width: unchangedWidth }]} />
      </View>
      <View style={styles.countGrid}>
        <Count label="Advancing" value={breadth.advancing} color={Theme.colors.success} />
        <Count label="Declining" value={breadth.declining} color={Theme.colors.danger} />
        <Count label="Unchanged" value={breadth.unchanged} color={Theme.colors.textMuted} />
        <Count label="A/D Ratio" value={breadth.advanceDeclineRatio?.toFixed(2) ?? 'N/A'} color={Theme.colors.accent} />
        <Count label="Total Analysed" value={breadth.totalStocks} color={Theme.colors.text} />
      </View>
    </View>
  );
}

function Count({ color, label, value }: { color: string; label: string; value: number | string }) {
  return (
    <View style={styles.countItem}>
      <Text style={styles.countLabel}>{label}</Text>
      <Text style={[styles.countValue, { color }]}>{value}</Text>
    </View>
  );
}

function toWidth(value: number, total: number) {
  if (total <= 0) {
    return '0%' as DimensionValue;
  }
  return `${Math.max(0, Math.min(100, value / total * 100))}%` as DimensionValue;
}

const styles = StyleSheet.create({
  advancing: {
    backgroundColor: Theme.colors.success,
  },
  container: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    gap: Spacing.two,
    padding: Spacing.three,
  },
  countGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  countItem: {
    flexBasis: '30%',
    flexGrow: 1,
    gap: 2,
  },
  countLabel: {
    color: Theme.colors.textMuted,
    fontSize: Typography.chartLabel.fontSize,
    fontWeight: Typography.weights.strong,
    textTransform: 'uppercase',
  },
  countValue: {
    fontSize: Typography.bodyLarge.fontSize,
    fontWeight: Typography.weights.strong,
  },
  declining: {
    backgroundColor: Theme.colors.danger,
  },
  segment: {
    height: 12,
  },
  title: {
    color: Theme.colors.text,
    fontSize: Typography.body.fontSize,
    fontWeight: Typography.weights.strong,
  },
  track: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderRadius: Theme.radii.pill,
    flexDirection: 'row',
    height: 12,
    overflow: 'hidden',
  },
  unchanged: {
    backgroundColor: Theme.colors.textMuted,
  },
});
