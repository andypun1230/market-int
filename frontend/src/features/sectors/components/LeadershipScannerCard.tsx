import { Pressable, StyleSheet, Text, View } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { TestDataBadge } from '@/components/ui/TestDataBadge';
import { Spacing, Theme } from '@/constants/theme';
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
                  <Text style={[styles.star, isFavourite(result.item) && styles.starActive]}>
                    {isFavourite(result.item) ? '★' : '☆'}
                  </Text>
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
    fontSize: 13,
    fontWeight: '900',
  },
  name: {
    color: Theme.colors.text,
    flex: 1,
    fontSize: 15,
    fontWeight: '900',
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
    fontSize: 12,
    fontWeight: '800',
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
    fontSize: 20,
    fontWeight: '900',
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
    fontSize: 10,
    fontWeight: '900',
    textTransform: 'uppercase',
  },
  stack: {
    gap: Spacing.two,
  },
  star: {
    color: Theme.colors.textMuted,
    fontSize: 18,
    fontWeight: '900',
  },
  starActive: {
    color: Theme.colors.warning,
  },
});
