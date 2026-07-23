import { Pressable, StyleSheet, Text, View } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { AppIcon } from '@/components/ui/AppIcon';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { TestDataBadge } from '@/components/ui/TestDataBadge';
import { Spacing, Theme, Typography } from '@/constants/theme';
import type { ScannerResult } from '@/features/sectors/analysis/scanners';
import { SectionEmptyState } from '@/features/sectors/components/SectionState';

type LeadershipScannerCardProps = {
  description: string;
  onPressItem: (item: ScannerResult['item']) => void;
  onToggleFavourite: (item: ScannerResult['item']) => void;
  results: ScannerResult[];
  title: string;
  isFavourite: (item: ScannerResult['item']) => boolean;
};

export function LeadershipScannerCard({
  description,
  isFavourite,
  onPressItem,
  onToggleFavourite,
  results,
  title,
}: LeadershipScannerCardProps) {
  return (
    <DashboardCard title={title} subtitle={description} accentColor={Theme.colors.accent}>
      <View style={styles.header}>
        <TestDataBadge />
      </View>
      <View style={styles.stack}>
        {results.length ? (
          results.map((result) => (
            <Pressable
              accessibilityLabel={`Open ${result.item.name} scanner detail`}
              accessibilityRole="button"
              key={`${title}-${result.item.type}-${result.item.id}`}
              onPress={() => onPressItem(result.item)}
              style={({ pressed }) => [styles.row, pressed && styles.pressed]}>
              <View style={styles.rowMain}>
                <View style={styles.nameRow}>
                  <Text style={styles.name}>{result.item.name}</Text>
                  <StatusBadge label={result.item.type === 'sector' ? 'Sector' : 'Theme'} tone="muted" />
                </View>
                <Text style={styles.label}>{result.label}</Text>
                <Text style={styles.reasons}>{result.reasons.slice(0, 2).join(' · ')}</Text>
              </View>
              <View style={styles.scoreBlock}>
                <Text style={styles.score}>{result.score}</Text>
                <Text style={styles.scoreLabel}>Score</Text>
                <Pressable
                  accessibilityLabel={`${isFavourite(result.item) ? 'Remove' : 'Add'} ${result.item.name} watchlist`}
                  accessibilityRole="button"
                  hitSlop={8}
                  onPress={(event) => {
                    event.stopPropagation();
                    onToggleFavourite(result.item);
                  }}>
                  <AppIcon
                    color={isFavourite(result.item) ? Theme.colors.warning : Theme.colors.textMuted}
                    name={isFavourite(result.item) ? 'saved' : 'savedOutline'}
                    size={18}
                  />
                </Pressable>
              </View>
            </Pressable>
          ))
        ) : (
          <SectionEmptyState
            message="No groups match this scanner in the current test window."
            title="No scanner results"
          />
        )}
      </View>
    </DashboardCard>
  );
}

const styles = StyleSheet.create({
  header: {
    marginBottom: Spacing.two,
  },
  label: {
    color: Theme.colors.text,
    fontSize: Typography.control.fontSize,
    fontWeight: Typography.weights.strong,
  },
  name: {
    color: Theme.colors.text,
    flex: 1,
    fontSize: Typography.bodyLarge.fontSize,
    fontWeight: Typography.weights.strong,
  },
  nameRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
  },
  pressed: {
    opacity: 0.78,
  },
  reasons: {
    color: Theme.colors.textMuted,
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.strong,
  },
  row: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    flexDirection: 'row',
    gap: Spacing.two,
    padding: Spacing.two,
  },
  rowMain: {
    flex: 1,
    gap: Spacing.one,
  },
  score: {
    color: Theme.colors.accent,
    fontSize: Typography.detailTitle.fontSize,
    fontWeight: Typography.weights.strong,
    textAlign: 'center',
  },
  scoreBlock: {
    alignItems: 'center',
    gap: Spacing.one,
    justifyContent: 'center',
    minWidth: 58,
  },
  scoreLabel: {
    color: Theme.colors.textMuted,
    fontSize: Typography.chartLabel.fontSize,
    fontWeight: Typography.weights.strong,
    textTransform: 'uppercase',
  },
  stack: {
    gap: Spacing.two,
  },
});
