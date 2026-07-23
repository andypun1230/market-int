import React from 'react';
import { Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { AppIcon } from '@/components/ui/AppIcon';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { TestDataBadge } from '@/components/ui/TestDataBadge';
import { Spacing, Theme, Typography } from '@/constants/theme';
import type { SectorThemeTestItem, TestHeatmapInterval } from '@/data/sectorTabTestData';
import {
  addComparisonItem,
  buildComparisonRows,
  canCompare,
  rankComparisonMetrics,
  removeComparisonItem,
} from '@/features/sectors/analysis/comparison';
import { buildWatchlistKey } from '@/features/watchlist/store';

type SectorThemeComparisonViewProps = {
  favourites: Set<string>;
  items: SectorThemeTestItem[];
  onToggleFavourite: (item: SectorThemeTestItem) => void;
  selectedItems: SectorThemeTestItem[];
  setSelectedItems: (items: SectorThemeTestItem[]) => void;
};

const INTERVALS: TestHeatmapInterval[] = ['1D', '1W', '1M', '3M', '6M', '1Y'];

export function SectorThemeComparisonView({
  favourites,
  items,
  onToggleFavourite,
  selectedItems,
  setSelectedItems,
}: SectorThemeComparisonViewProps) {
  const [query, setQuery] = React.useState('');
  const [typeFilter, setTypeFilter] = React.useState<'all' | 'sector' | 'theme'>('all');
  const [favouritesFirst, setFavouritesFirst] = React.useState(true);
  const normalizedQuery = query.trim().toLowerCase();
  const candidates = items
    .filter((item) => typeFilter === 'all' || item.type === typeFilter)
    .filter((item) => !normalizedQuery || item.name.toLowerCase().includes(normalizedQuery))
    .sort((a, b) => {
      if (favouritesFirst) {
        const favCompare =
          Number(favourites.has(buildWatchlistKey(b.type, b.id))) -
          Number(favourites.has(buildWatchlistKey(a.type, a.id)));
        if (favCompare !== 0) {
          return favCompare;
        }
      }
      return a.name.localeCompare(b.name);
    });
  const scorecard = rankComparisonMetrics(selectedItems);
  const rows = buildComparisonRows(selectedItems, INTERVALS);

  return (
    <View style={styles.stack}>
      <DashboardCard title="Compare Sectors & Themes" subtitle="Select two or three items. Values are deterministic test data." accentColor={Theme.colors.accent}>
        <View style={styles.headerRow}>
          <TestDataBadge />
          <Pressable
            accessibilityRole="button"
            onPress={() => setFavouritesFirst((value) => !value)}
            style={styles.smallButton}>
            <Text style={styles.smallButtonText}>{favouritesFirst ? 'Saved First' : 'Natural Sort'}</Text>
          </Pressable>
        </View>
        <TextInput
          autoCapitalize="none"
          onChangeText={setQuery}
          placeholder="Search sectors or themes..."
          placeholderTextColor={Theme.colors.textMuted}
          style={styles.search}
          value={query}
        />
        <View style={styles.filterRow}>
          {(['all', 'sector', 'theme'] as const).map((option) => (
            <Pressable
              accessibilityRole="button"
              accessibilityState={{ selected: typeFilter === option }}
              key={option}
              onPress={() => setTypeFilter(option)}
              style={[styles.typeChip, typeFilter === option && styles.typeChipActive]}>
              <Text style={[styles.typeChipText, typeFilter === option && styles.typeChipTextActive]}>{option}</Text>
            </Pressable>
          ))}
        </View>
        <View style={styles.selectedRow}>
          {selectedItems.length ? selectedItems.map((item) => (
            <Pressable key={`${item.type}-${item.id}`} onPress={() => setSelectedItems(removeComparisonItem(selectedItems, item))} style={styles.selectedChip}>
              <Text style={styles.selectedChipText}>{item.name}</Text>
              <AppIcon color={Theme.colors.accent} name="close" size={12} />
            </Pressable>
          )) : <Text style={styles.emptyText}>Select at least two items.</Text>}
        </View>
        <ScrollView style={styles.candidateList}>
          {candidates.map((item) => {
            const selected = selectedItems.some((current) => current.type === item.type && current.id === item.id);
            const disabled = !selected && selectedItems.length >= 3;
            return (
              <Pressable
                accessibilityRole="button"
                disabled={disabled}
                key={`${item.type}-${item.id}`}
                onPress={() => setSelectedItems(selected ? removeComparisonItem(selectedItems, item) : addComparisonItem(selectedItems, item))}
                style={[styles.candidateRow, selected && styles.candidateRowActive, disabled && styles.disabled]}>
                <View style={styles.candidateMain}>
                  <Text style={styles.candidateName}>{item.name}</Text>
                  <Text style={styles.candidateMeta}>{item.type === 'sector' ? 'Sector' : 'Theme'} · {item.quadrant}</Text>
                </View>
                <Pressable
                  accessibilityLabel={`${favourites.has(buildWatchlistKey(item.type, item.id)) ? 'Remove' : 'Add'} ${item.name} watchlist`}
                  accessibilityRole="button"
                  hitSlop={8}
                  onPress={(event) => {
                    event.stopPropagation();
                    onToggleFavourite(item);
                  }}>
                  <AppIcon
                    color={favourites.has(buildWatchlistKey(item.type, item.id)) ? Theme.colors.warning : Theme.colors.textMuted}
                    name={favourites.has(buildWatchlistKey(item.type, item.id)) ? 'saved' : 'savedOutline'}
                    size={20}
                  />
                </Pressable>
              </Pressable>
            );
          })}
        </ScrollView>
      </DashboardCard>

      {canCompare(selectedItems) && scorecard ? (
        <>
          <DashboardCard title="Comparison Scorecard" accentColor={Theme.colors.success}>
            <View style={styles.scoreGrid}>
              <Score label="Strongest current test performance" value={scorecard.strongestPerformance.name} />
              <Score label="Broadest participation" value={scorecard.bestBreadth.name} />
              <Score label="Strongest relative momentum" value={scorecard.bestRotation.name} />
              <Score label="Lowest leadership concentration" value={scorecard.lowestConcentrationRisk.name} />
            </View>
          </DashboardCard>
          <DashboardCard title="Comparison Metrics" accentColor={Theme.colors.purple}>
            <ScrollView horizontal showsHorizontalScrollIndicator={false}>
              <View>
                <View style={styles.tableRow}>
                  <Text style={[styles.tableCell, styles.metricColumn]}>Metric</Text>
                  {selectedItems.map((item) => (
                    <Text key={`${item.type}-${item.id}`} style={styles.tableCell}>{item.name}</Text>
                  ))}
                </View>
                {rows.map((row) => (
                  <View key={row.label} style={styles.tableRow}>
                    <Text style={[styles.tableCell, styles.metricColumn]}>{row.label}</Text>
                    {row.values.map((value, index) => (
                      <Text key={`${row.label}-${selectedItems[index]?.id}`} style={styles.tableCell}>{value}</Text>
                    ))}
                  </View>
                ))}
              </View>
            </ScrollView>
          </DashboardCard>
        </>
      ) : (
        <DashboardCard>
          <View style={styles.headerRow}>
            <StatusBadge label="Select 2-3 items" tone="info" />
            <TestDataBadge />
          </View>
          <Text style={styles.emptyText}>The comparison table appears after selecting at least two items.</Text>
        </DashboardCard>
      )}
    </View>
  );
}

function Score({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.scoreItem}>
      <Text style={styles.scoreLabel}>{label}</Text>
      <Text style={styles.scoreValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  candidateList: {
    maxHeight: 230,
  },
  candidateMain: {
    flex: 1,
  },
  candidateMeta: {
    color: Theme.colors.textMuted,
    fontSize: Typography.caption.fontSize,
    fontWeight: Typography.weights.strong,
  },
  candidateName: {
    color: Theme.colors.text,
    fontSize: Typography.body.fontSize,
    fontWeight: Typography.weights.strong,
  },
  candidateRow: {
    alignItems: 'center',
    borderBottomColor: Theme.colors.border,
    borderBottomWidth: 1,
    flexDirection: 'row',
    gap: Spacing.two,
    paddingVertical: Spacing.two,
  },
  candidateRowActive: {
    backgroundColor: Theme.colors.accentSoft,
  },
  disabled: {
    opacity: 0.45,
  },
  emptyText: {
    color: Theme.colors.textMuted,
    fontSize: Typography.control.fontSize,
    fontWeight: Typography.weights.strong,
  },
  filterRow: {
    flexDirection: 'row',
    gap: Spacing.one,
  },
  headerRow: {
    alignItems: 'center',
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
    justifyContent: 'space-between',
    marginBottom: Spacing.two,
  },
  metricColumn: {
    color: Theme.colors.textMuted,
    width: 150,
  },
  scoreGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  scoreItem: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    flexBasis: '47%',
    flexGrow: 1,
    gap: 3,
    padding: Spacing.two,
  },
  scoreLabel: {
    color: Theme.colors.textMuted,
    fontSize: Typography.chartLabel.fontSize,
    fontWeight: Typography.weights.strong,
    textTransform: 'uppercase',
  },
  scoreValue: {
    color: Theme.colors.text,
    fontSize: Typography.body.fontSize,
    fontWeight: Typography.weights.strong,
  },
  search: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    color: Theme.colors.text,
    fontSize: Typography.body.fontSize,
    fontWeight: Typography.weights.strong,
    minHeight: 44,
    paddingHorizontal: Spacing.two,
  },
  selectedChip: {
    alignItems: 'center',
    backgroundColor: Theme.colors.accentSoft,
    borderColor: Theme.colors.accent,
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    flexDirection: 'row',
    gap: Spacing.one,
    paddingHorizontal: Spacing.two,
    paddingVertical: 6,
  },
  selectedChipText: {
    color: Theme.colors.accent,
    fontSize: Typography.caption.fontSize,
    fontWeight: Typography.weights.strong,
  },
  selectedRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.one,
  },
  smallButton: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    paddingHorizontal: Spacing.two,
    paddingVertical: 7,
  },
  smallButtonText: {
    color: Theme.colors.textMuted,
    fontSize: Typography.caption.fontSize,
    fontWeight: Typography.weights.strong,
  },
  stack: {
    gap: Spacing.three,
  },
  tableCell: {
    color: Theme.colors.text,
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.strong,
    padding: Spacing.two,
    width: 124,
  },
  tableRow: {
    borderBottomColor: Theme.colors.border,
    borderBottomWidth: 1,
    flexDirection: 'row',
  },
  typeChip: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    paddingHorizontal: Spacing.two,
    paddingVertical: 6,
  },
  typeChipActive: {
    backgroundColor: Theme.colors.accentSoft,
    borderColor: Theme.colors.accent,
  },
  typeChipText: {
    color: Theme.colors.textMuted,
    fontSize: Typography.caption.fontSize,
    fontWeight: Typography.weights.strong,
    textTransform: 'capitalize',
  },
  typeChipTextActive: {
    color: Theme.colors.accent,
  },
});
