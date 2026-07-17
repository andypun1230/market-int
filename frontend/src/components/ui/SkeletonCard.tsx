import { StyleSheet, View } from 'react-native';

import { Spacing, Theme } from '@/constants/theme';

type SkeletonCardProps = {
  compact?: boolean;
  rows?: number;
  title?: boolean;
};

export function SkeletonCard({ compact = false, rows = 3, title = true }: SkeletonCardProps) {
  return (
    <View style={[styles.card, compact && styles.compactCard]}>
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
    backgroundColor: Theme.colors.card,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.card,
    borderWidth: 1,
    gap: Spacing.three,
    padding: Spacing.three,
  },
  compactCard: {
    gap: Spacing.two,
    padding: Spacing.twoAndHalf,
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
});
