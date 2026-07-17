import { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { StatusBadge } from '@/components/ui/StatusBadge';
import { TEST_HEATMAP_INTERVALS, type TestHeatmapInterval } from '@/data/sectorTabTestData';
import { Spacing, Theme } from '@/constants/theme';
import {
  getSectorThemeSortLabel,
  SECTOR_THEME_SORT_OPTIONS,
} from '@/features/watchlist/sectorThemeSort';
import type { SectorThemeSortMode, SectorThemeTypeFilter } from '@/features/watchlist/types';

const TYPE_OPTIONS: { key: SectorThemeTypeFilter; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'sector', label: 'Sectors' },
  { key: 'theme', label: 'Themes' },
];
const PERIOD_OPTIONS = TEST_HEATMAP_INTERVALS.map((interval) => ({ key: interval, label: interval }));

type SectorThemeToolbarProps = {
  itemCount: number;
  onPeriodChange: (period: TestHeatmapInterval) => void;
  onSortChange: (sortMode: SectorThemeSortMode) => void;
  onTypeChange: (typeFilter: SectorThemeTypeFilter) => void;
  period: TestHeatmapInterval;
  sortMode: SectorThemeSortMode;
  typeFilter: SectorThemeTypeFilter;
};

export function SectorThemeToolbar({
  itemCount,
  onPeriodChange,
  onSortChange,
  onTypeChange,
  period,
  sortMode,
  typeFilter,
}: SectorThemeToolbarProps) {
  const [openMenu, setOpenMenu] = useState<'type' | 'period' | 'sort' | null>(null);

  return (
    <View style={styles.container}>
      <View style={styles.summaryRow}>
        <StatusBadge label={`${itemCount} saved`} showDot={false} tone="info" />
        <View style={styles.sourceBadge}>
          <Text style={styles.sourceText}>Demo data</Text>
        </View>
      </View>
      <View style={styles.controlRow}>
        <MenuButton
          label={getTypeLabel(typeFilter)}
          menuKey="type"
          openMenu={openMenu}
          setOpenMenu={setOpenMenu}
        />
        <MenuButton
          label={period}
          menuKey="period"
          openMenu={openMenu}
          setOpenMenu={setOpenMenu}
        />
        <MenuButton
          label={getSectorThemeSortLabel(sortMode)}
          menuKey="sort"
          openMenu={openMenu}
          setOpenMenu={setOpenMenu}
        />
      </View>
      {openMenu === 'type' ? (
        <OptionMenu
          options={TYPE_OPTIONS}
          selectedKey={typeFilter}
          onSelect={(value) => {
            onTypeChange(value as SectorThemeTypeFilter);
            setOpenMenu(null);
          }}
        />
      ) : null}
      {openMenu === 'period' ? (
        <OptionMenu
          options={PERIOD_OPTIONS}
          selectedKey={period}
          onSelect={(value) => {
            onPeriodChange(value as TestHeatmapInterval);
            setOpenMenu(null);
          }}
        />
      ) : null}
      {openMenu === 'sort' ? (
        <OptionMenu
          options={SECTOR_THEME_SORT_OPTIONS}
          selectedKey={sortMode}
          onSelect={(value) => {
            onSortChange(value as SectorThemeSortMode);
            setOpenMenu(null);
          }}
        />
      ) : null}
    </View>
  );
}

function MenuButton({
  label,
  menuKey,
  openMenu,
  setOpenMenu,
}: {
  label: string;
  menuKey: 'type' | 'period' | 'sort';
  openMenu: 'type' | 'period' | 'sort' | null;
  setOpenMenu: (value: 'type' | 'period' | 'sort' | null) => void;
}) {
  const open = openMenu === menuKey;
  return (
    <Pressable
      accessibilityLabel={`Open ${menuKey} menu, currently ${label}`}
      accessibilityRole="button"
      accessibilityState={{ expanded: open }}
      onPress={() => setOpenMenu(open ? null : menuKey)}
      style={({ pressed }) => [styles.controlButton, pressed && styles.pressed]}>
      <Text numberOfLines={1} style={styles.controlText}>{label}</Text>
      <Text style={styles.chevron}>{open ? '⌃' : '⌄'}</Text>
    </Pressable>
  );
}

function OptionMenu({
  onSelect,
  options,
  selectedKey,
}: {
  onSelect: (value: string) => void;
  options: { key: string; label: string }[];
  selectedKey: string;
}) {
  return (
    <View style={styles.optionMenu}>
      {options.map((option) => {
        const selected = option.key === selectedKey;
        return (
          <Pressable
            accessibilityLabel={`Select ${option.label}`}
            accessibilityRole="button"
            accessibilityState={{ selected }}
            key={option.key}
            onPress={() => onSelect(option.key)}
            style={({ pressed }) => [
              styles.optionRow,
              selected && styles.optionRowSelected,
              pressed && styles.pressed,
            ]}>
            <Text style={[styles.optionText, selected && styles.optionTextSelected]}>{option.label}</Text>
            {selected ? <Text style={styles.check}>✓</Text> : null}
          </Pressable>
        );
      })}
    </View>
  );
}

function getTypeLabel(typeFilter: SectorThemeTypeFilter) {
  switch (typeFilter) {
    case 'sector':
      return 'Sectors';
    case 'theme':
      return 'Themes';
    case 'all':
      return 'All';
  }
}

const styles = StyleSheet.create({
  check: {
    color: Theme.colors.accent,
    fontSize: 14,
    fontWeight: '900',
  },
  chevron: {
    color: Theme.colors.textMuted,
    fontSize: 15,
    fontWeight: '900',
  },
  container: {
    gap: Spacing.two,
  },
  controlButton: {
    alignItems: 'center',
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    flex: 1,
    flexDirection: 'row',
    gap: Spacing.one,
    minHeight: 42,
    minWidth: 0,
    paddingHorizontal: Spacing.two,
  },
  controlRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.one,
  },
  controlText: {
    color: Theme.colors.text,
    flex: 1,
    fontSize: 12,
    fontWeight: '900',
  },
  optionMenu: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    overflow: 'hidden',
  },
  optionRow: {
    alignItems: 'center',
    borderBottomColor: Theme.colors.border,
    borderBottomWidth: 1,
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
    minHeight: 40,
    paddingHorizontal: Spacing.twoAndHalf,
  },
  optionRowSelected: {
    backgroundColor: Theme.colors.accentSoft,
  },
  optionText: {
    color: Theme.colors.textMuted,
    flex: 1,
    fontSize: 13,
    fontWeight: '800',
  },
  optionTextSelected: {
    color: Theme.colors.text,
  },
  pressed: {
    opacity: 0.78,
  },
  sourceBadge: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    paddingHorizontal: Spacing.two,
    paddingVertical: Spacing.one,
  },
  sourceText: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '900',
  },
  summaryRow: {
    alignItems: 'center',
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
});
