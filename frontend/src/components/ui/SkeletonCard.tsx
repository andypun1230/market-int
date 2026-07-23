import { StyleSheet, View } from 'react-native';

import { CARD_SURFACE } from '@/components/cards/DashboardCard';
import { Spacing, Theme } from '@/constants/theme';

type SkeletonCardProps = {
  compact?: boolean;
  rows?: number;
  structure?: 'summary' | 'chart' | 'list' | 'detail';
  title?: boolean;
};

export function SkeletonCard({ compact = false, rows = 3, structure = 'summary', title = true }: SkeletonCardProps) {
  return (
    <View style={[styles.card, styles[structure], compact && styles.compactCard]}>
      {title ? (
        <View style={styles.titleBlock}>
          <View style={styles.titleLine} />
          <View style={styles.subtitleLine} />
        </View>
      ) : null}
      <View style={styles.rowStack}>
        {Array.from({ length: rows }).map((_, index) => (
          <View
            key={index}
            style={[
              styles.row,
              compact && styles.compactRow,
              index === rows - 1 && styles.shortRow,
            ]}
          />
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    ...CARD_SURFACE,
    gap: Spacing.three,
    padding: Spacing.three,
  },
  chart: {
    minHeight: 320,
  },
  compactCard: {
    gap: Spacing.two,
    padding: Spacing.twoAndHalf,
  },
  detail: {
    minHeight: 260,
  },
  list: {
    minHeight: 180,
  },
  titleBlock: {
    gap: Spacing.two,
  },
  titleLine: {
    backgroundColor: Theme.colors.cardElevated,
    borderRadius: Theme.radii.small,
    height: 16,
    width: '48%',
  },
  subtitleLine: {
    backgroundColor: Theme.colors.cardMuted,
    borderRadius: Theme.radii.small,
    height: 10,
    width: '72%',
  },
  rowStack: {
    gap: Spacing.two,
  },
  row: {
    backgroundColor: Theme.colors.cardMuted,
    borderRadius: Theme.radii.small,
    height: 13,
    width: '100%',
  },
  compactRow: {
    height: 10,
  },
  shortRow: {
    width: '58%',
  },
  summary: {
    minHeight: 180,
  },
});
