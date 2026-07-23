import { useMemo, useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { DetailModal } from '@/components/ui/DetailModal';
import { EmptyState } from '@/components/ui/EmptyState';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { TestDataBadge } from '@/components/ui/TestDataBadge';
import { Spacing, Theme, Typography } from '@/constants/theme';
import type { TestHeatmapInterval } from '@/data/sectorTabTestData';
import { searchSectorThemeItems } from '@/features/sectors/analysis/search';
import type { SectorThemeSearchItem } from '@/features/sectors/sectorThemeSearchModel';
import { buildWatchlistKey } from '@/features/watchlist/store';

type SectorThemeSearchModalProps = {
  interval: TestHeatmapInterval;
  isVisible: boolean;
  items: SectorThemeSearchItem[];
  onClose: () => void;
  onOpenItem: (item: SectorThemeSearchItem) => void;
  onToggleWatchlist: (item: SectorThemeSearchItem) => void;
  watchlistKeys: Set<string>;
};

export function SectorThemeSearchModal({
  interval,
  isVisible,
  items,
  onClose,
  onOpenItem,
  onToggleWatchlist,
  watchlistKeys,
}: SectorThemeSearchModalProps) {
  const [query, setQuery] = useState('');
  const results = useMemo(() => searchSectorThemeItems(items, query), [items, query]);
  const sectors = results.filter((item) => item.type === 'sector');
  const themes = results.filter((item) => item.type === 'theme');

  return (
    <DetailModal visible={isVisible} title="Search Sectors & Themes" subtitle="Search canonical sectors, themes, and associated tickers." onClose={onClose}>
      <DashboardCard>
        <TextInput
          accessibilityLabel="Search sectors and themes"
          autoCapitalize="none"
          autoCorrect={false}
          onChangeText={setQuery}
          placeholder="Search sectors and themes"
          placeholderTextColor={Theme.colors.textMuted}
          style={styles.searchInput}
          value={query}
        />
        {query ? (
          <Pressable accessibilityRole="button" onPress={() => setQuery('')} style={styles.clearButton}>
            <Text style={styles.clearText}>Clear Search</Text>
          </Pressable>
        ) : null}
      </DashboardCard>

      {query.trim() && !results.length ? (
        <EmptyState
          title={`No results for “${query.trim()}”`}
          message="Try another sector, theme, or ticker keyword."
          stateType="no_search_results"
        />
      ) : null}

      {sectors.length ? (
        <ResultGroup
          interval={interval}
          items={sectors}
          onOpenItem={onOpenItem}
          onToggleWatchlist={onToggleWatchlist}
          title="Sectors"
          watchlistKeys={watchlistKeys}
        />
      ) : null}

      {themes.length ? (
        <ResultGroup
          interval={interval}
          items={themes}
          onOpenItem={onOpenItem}
          onToggleWatchlist={onToggleWatchlist}
          title="Themes"
          watchlistKeys={watchlistKeys}
        />
      ) : null}
    </DetailModal>
  );
}

function ResultGroup({
  interval,
  items,
  onOpenItem,
  onToggleWatchlist,
  title,
  watchlistKeys,
}: {
  interval: TestHeatmapInterval;
  items: SectorThemeSearchItem[];
  onOpenItem: (item: SectorThemeSearchItem) => void;
  onToggleWatchlist: (item: SectorThemeSearchItem) => void;
  title: string;
  watchlistKeys: Set<string>;
}) {
  return (
    <DashboardCard title={title}>
      <View style={styles.results}>
        {items.map((item) => {
          const saved = watchlistKeys.has(buildWatchlistKey(item.type, item.id));
          return (
            <View key={`${item.type}-${item.id}`} style={styles.resultRow}>
              <Pressable
                accessibilityLabel={`Open ${item.name}`}
                accessibilityRole="button"
                onPress={() => onOpenItem(item)}
                style={({ pressed }) => [styles.resultAction, pressed && styles.pressed]}>
                <View style={styles.resultMain}>
                <View style={styles.resultHeader}>
                  <Text style={styles.resultName}>{item.name}</Text>
                  <StatusBadge label={item.type === 'sector' ? 'Sector' : 'Theme'} tone={item.type === 'sector' ? 'info' : 'purple'} />
                </View>
                <Text style={styles.resultMeta}>
                  {item.status} · {formatPercent(item.values[interval])}
                </Text>
                {item.sourceState === 'test' ? <TestDataBadge /> : null}
                </View>
              </Pressable>
              <Pressable
                accessibilityLabel={`${saved ? 'Remove' : 'Add'} ${item.name} Watchlist`}
                accessibilityRole="button"
                onPress={() => onToggleWatchlist(item)}
                style={styles.saveButton}>
                <Text style={[styles.saveText, saved && styles.saveTextActive]}>{saved ? 'Saved' : 'Add'}</Text>
              </Pressable>
            </View>
          );
        })}
      </View>
    </DashboardCard>
  );
}

function formatPercent(value: number | null) {
  if (value === null || !Number.isFinite(value)) return 'N/A';
  const prefix = value > 0 ? '+' : '';
  return `${prefix}${value.toFixed(2)}%`;
}

const styles = StyleSheet.create({
  clearButton: {
    alignSelf: 'flex-start',
    marginTop: Spacing.two,
  },
  clearText: {
    color: Theme.colors.accent,
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.strong,
  },
  pressed: {
    opacity: 0.78,
  },
  resultHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
  },
  resultAction: {
    flex: 1,
    minHeight: 60,
    padding: Spacing.two,
  },
  resultMain: {
    flex: 1,
    gap: Spacing.one,
  },
  resultMeta: {
    color: Theme.colors.textMuted,
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.strong,
  },
  resultName: {
    color: Theme.colors.text,
    flex: 1,
    fontSize: Typography.bodyLarge.fontSize,
    fontWeight: Typography.weights.strong,
  },
  resultRow: {
    alignItems: 'center',
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    flexDirection: 'row',
    gap: Spacing.one,
    overflow: 'hidden',
  },
  results: {
    gap: Spacing.two,
  },
  saveButton: {
    alignItems: 'center',
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    minHeight: 44,
    minWidth: 64,
    justifyContent: 'center',
    marginRight: Spacing.two,
  },
  saveText: {
    color: Theme.colors.textMuted,
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.strong,
  },
  saveTextActive: {
    color: Theme.colors.warning,
  },
  searchInput: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    color: Theme.colors.text,
    fontSize: Typography.bodyLarge.fontSize,
    fontWeight: Typography.weights.strong,
    minHeight: 48,
    paddingHorizontal: Spacing.twoAndHalf,
  },
});
