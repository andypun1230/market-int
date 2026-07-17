import { Pressable, StyleSheet, Text, View } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { Spacing, Theme } from '@/constants/theme';
import {
  DEFAULT_SECTOR_THEME_FILTERS,
  type SectorThemeFilters,
  type SortMode,
} from '@/features/sectors/analysis/filters';

type SectorThemeFilterPanelProps = {
  filters: SectorThemeFilters;
  onChange: (filters: SectorThemeFilters) => void;
};

const QUADRANTS = ['all', 'leading', 'improving', 'weakening', 'lagging'] as const;
const PERFORMANCE = ['all', 'positive', 'negative', 'nearZero'] as const;
const BREADTH = ['all', 'Broad', 'Healthy', 'Selective', 'Narrow', 'Deteriorating'] as const;
const FAVOURITES = ['all', 'only', 'first'] as const;
const SORTS: SortMode[] = [
  'highestReturn',
  'lowestReturn',
  'strongestRelativeStrength',
  'strongestRelativeMomentum',
  'bestBreadth',
  'highestConcentration',
  'lowestConcentration',
  'alphabetical',
];

export function SectorThemeFilterPanel({ filters, onChange }: SectorThemeFilterPanelProps) {
  return (
    <DashboardCard title="Filter & Sort" subtitle="Applies to the currently selected Sector tab panel." accentColor={Theme.colors.accent}>
      <View style={styles.stack}>
        <OptionGroup
          label="Quadrant"
          options={QUADRANTS}
          selected={filters.quadrant}
          onSelect={(quadrant) => onChange({ ...filters, quadrant })}
        />
        <OptionGroup
          label="Performance"
          options={PERFORMANCE}
          selected={filters.performance}
          onSelect={(performance) => onChange({ ...filters, performance })}
        />
        <OptionGroup
          label="Breadth"
          options={BREADTH}
          selected={filters.breadth}
          onSelect={(breadth) => onChange({ ...filters, breadth })}
        />
        <OptionGroup
          label="Watchlist"
          options={FAVOURITES}
          selected={filters.favouriteMode}
          onSelect={(favouriteMode) => onChange({ ...filters, favouriteMode })}
        />
        <OptionGroup
          label="Sort"
          options={SORTS}
          selected={filters.sortMode}
          onSelect={(sortMode) => onChange({ ...filters, sortMode })}
        />
        <Pressable
          accessibilityRole="button"
          onPress={() => onChange(DEFAULT_SECTOR_THEME_FILTERS)}
          style={({ pressed }) => [styles.resetButton, pressed && styles.pressed]}>
          <Text style={styles.resetText}>Reset Filters</Text>
        </Pressable>
      </View>
    </DashboardCard>
  );
}

function OptionGroup<T extends string>({
  label,
  onSelect,
  options,
  selected,
}: {
  label: string;
  onSelect: (value: T) => void;
  options: readonly T[];
  selected: T;
}) {
  return (
    <View style={styles.group}>
      <Text style={styles.groupLabel}>{label}</Text>
      <View style={styles.options}>
        {options.map((option) => {
          const active = option === selected;
          return (
            <Pressable
              accessibilityRole="button"
              accessibilityState={{ selected: active }}
              key={option}
              onPress={() => onSelect(option)}
              style={({ pressed }) => [styles.option, active && styles.optionActive, pressed && styles.pressed]}>
              <Text style={[styles.optionText, active && styles.optionTextActive]}>{formatOption(option)}</Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

function formatOption(value: string) {
  return value
    .replace(/([A-Z])/g, ' $1')
    .replace(/^./, (match) => match.toUpperCase())
    .replace('Near Zero', 'Near Zero')
    .replace('All', 'All')
    .replace('Only', 'Saved Only')
    .replace('First', 'Saved First');
}

const styles = StyleSheet.create({
  group: {
    gap: Spacing.one,
  },
  groupLabel: {
    color: Theme.colors.text,
    fontSize: 13,
    fontWeight: '900',
  },
  option: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    paddingHorizontal: Spacing.two,
    paddingVertical: 6,
  },
  optionActive: {
    backgroundColor: Theme.colors.accentSoft,
    borderColor: Theme.colors.accent,
  },
  optionText: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '900',
  },
  optionTextActive: {
    color: Theme.colors.accent,
  },
  options: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.one,
  },
  pressed: {
    opacity: 0.78,
  },
  resetButton: {
    alignItems: 'center',
    alignSelf: 'flex-start',
    backgroundColor: Theme.colors.warningSoft,
    borderColor: Theme.colors.warning,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    minHeight: 44,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.two,
  },
  resetText: {
    color: Theme.colors.warning,
    fontSize: 12,
    fontWeight: '900',
  },
  stack: {
    gap: Spacing.three,
  },
});
