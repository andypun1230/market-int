import { useMemo, useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { DetailModal } from '@/components/ui/DetailModal';
import { EmptyState } from '@/components/ui/EmptyState';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { TestDataBadge } from '@/components/ui/TestDataBadge';
import { Spacing, Theme } from '@/constants/theme';
import type { SectorThemeTestItem, TestHeatmapInterval } from '@/data/sectorTabTestData';
import { searchSectorThemeItems } from '@/features/sectors/analysis/search';
import { buildWatchlistKey } from '@/features/watchlist/store';

type SectorThemeSearchModalProps = {
  interval: TestHeatmapInterval;
  isVisible: boolean;
  items: SectorThemeTestItem[];
  onClose: () => void;
  onOpenItem: (item: SectorThemeTestItem) => void;
  onToggleWatchlist: (item: SectorThemeTestItem) => void;
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
    <DetailModal visible={isVisible} title="Search Sectors & Themes" subtitle="Search test sectors, themes, and associated tickers." onClose={onClose}>
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
        <EmptyState title="No sectors or themes found" message="Try another sector, theme, or ticker keyword." />
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
  items: SectorThemeTestItem[];
  onOpenItem: (item: SectorThemeTestItem) => void;
  onToggleWatchlist: (item: SectorThemeTestItem) => void;
  title: string;
  watchlistKeys: Set<string>;
}) {
  return (
    <DashboardCard title={title}>
      <View style={styles.results}>
        {items.map((item) => {
          const saved = watchlistKeys.has(buildWatchlistKey(item.type, item.id));
          return (
            <Pressable
              accessibilityLabel={`Open ${item.name}`}
              accessibilityRole="button"
              key={`${item.type}-${item.id}`}
              onPress={() => onOpenItem(item)}
              style={({ pressed }) => [styles.resultRow, pressed && styles.pressed]}>
              <View style={styles.resultMain}>
                <View style={styles.resultHeader}>
                  <Text style={styles.resultName}>{item.name}</Text>
                  <StatusBadge label={item.type === 'sector' ? 'Sector' : 'Theme'} tone={item.type === 'sector' ? 'info' : 'purple'} />
                </View>
                <Text style={styles.resultMeta}>
                  {capitalize(item.quadrant)} · {formatPercent(item.returns[interval])}
                </Text>
                <TestDataBadge />
              </View>
              <Pressable
                accessibilityLabel={`${saved ? 'Remove' : 'Add'} ${item.name} Watchlist`}
                accessibilityRole="button"
                hitSlop={8}
                onPress={(event) => {
                  event.stopPropagation();
                  onToggleWatchlist(item);
                }}
                style={styles.saveButton}>
                <Text style={[styles.saveText, saved && styles.saveTextActive]}>{saved ? 'Saved' : 'Add'}</Text>
              </Pressable>
            </Pressable>
          );
        })}
      </View>
    </DashboardCard>
  );
}

function capitalize(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function formatPercent(value: number) {
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
    fontSize: 12,
    fontWeight: '900',
  },
  pressed: {
    opacity: 0.78,
  },
  resultHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
  },
  resultMain: {
    flex: 1,
    gap: Spacing.one,
  },
  resultMeta: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '800',
  },
  resultName: {
    color: Theme.colors.text,
    flex: 1,
    fontSize: 15,
    fontWeight: '900',
  },
  resultRow: {
    alignItems: 'center',
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    flexDirection: 'row',
    gap: Spacing.two,
    padding: Spacing.two,
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
  },
  saveText: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '900',
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
    fontSize: 15,
    fontWeight: '800',
    minHeight: 48,
    paddingHorizontal: Spacing.twoAndHalf,
  },
});
