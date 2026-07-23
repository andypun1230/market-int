import type { ReactNode } from 'react';
import { useMemo, useState } from 'react';
import { AccessibilityInfo, Pressable, StyleSheet, Text, View } from 'react-native';

import { DetailModal } from '@/components/ui/DetailModal';
import { AppIcon } from '@/components/ui/AppIcon';
import { Spacing, Theme, Typography } from '@/constants/theme';
import {
  getSortLabel,
  type ListControlOption,
  type WatchlistCategory,
  type WatchlistListFilter,
  type WatchlistListSort,
  type WatchlistViewMode,
} from '@/features/watchlist/watchlistListControls';

type WatchlistListControlsProps = {
  activeCategory: WatchlistCategory;
  activeFilters: WatchlistListFilter[];
  availableFilterOptions: ListControlOption[];
  availableSortOptions: ListControlOption[];
  currentSort: WatchlistListSort;
  getResultCount: (filters: WatchlistListFilter[]) => number;
  onApply: (value: { filters: WatchlistListFilter[]; sort: WatchlistListSort; viewMode: WatchlistViewMode }) => void;
  onReset: () => void;
  resultCount: number;
  totalCount: number;
  viewMode: WatchlistViewMode;
};

export function WatchlistListControls({
  activeCategory,
  activeFilters,
  availableFilterOptions,
  availableSortOptions,
  currentSort,
  getResultCount,
  onApply,
  onReset,
  resultCount,
  totalCount,
  viewMode,
}: WatchlistListControlsProps) {
  const [visible, setVisible] = useState(false);
  const [draftSort, setDraftSort] = useState(currentSort);
  const [draftFilters, setDraftFilters] = useState<WatchlistListFilter[]>(activeFilters);
  const [draftViewMode, setDraftViewMode] = useState(viewMode);
  const sortLabel = getSortLabel(availableSortOptions, currentSort);
  const categoryLabel = activeCategory;
  const resultLabel = (count: number) => `${count} ${count === 1 ? singularCategory(activeCategory) : activeCategory}`;
  const draftResultCount = useMemo(() => getResultCount(draftFilters), [draftFilters, getResultCount]);

  const open = () => {
    setDraftSort(currentSort);
    setDraftFilters(activeFilters);
    setDraftViewMode(viewMode);
    setVisible(true);
  };

  const apply = () => {
    onApply({ filters: draftFilters, sort: draftSort, viewMode: draftViewMode });
    setVisible(false);
    AccessibilityInfo.announceForAccessibility(`${resultLabel(draftResultCount)} shown.`);
  };

  const clearFilters = () => {
    onApply({ filters: [], sort: currentSort, viewMode });
    AccessibilityInfo.announceForAccessibility(`${resultLabel(totalCount)} shown. Filters cleared.`);
  };

  return (
    <>
      <View style={styles.wrapper}>
        <View style={styles.controlRow}>
          <Pressable
            accessibilityLabel={`Sort and filter ${categoryLabel}, current sort ${sortLabel}, ${activeFilters.length} active filters`}
            accessibilityRole="button"
            accessibilityState={{ selected: activeFilters.length > 0 }}
            onPress={open}
            style={({ pressed }) => [styles.controlButton, styles.combinedButton, activeFilters.length > 0 && styles.activeButton, pressed && styles.pressed]}>
            <View style={styles.combinedButtonContent}>
              <Text numberOfLines={1} style={[styles.controlText, activeFilters.length > 0 && styles.activeText]}>Sort & Filter</Text>
              <Text numberOfLines={1} style={styles.sortSummary}>· {sortLabel}</Text>
              {activeFilters.length ? (
                <View style={styles.filterCount}>
                  <Text style={styles.filterCountText}>{activeFilters.length}</Text>
                </View>
              ) : null}
            </View>
            <AppIcon name="chevronDown" size={17} />
          </Pressable>
          <Pressable
            accessibilityLabel={`Switch to ${viewMode === 'detailed' ? 'compact' : 'detailed'} view`}
            accessibilityRole="button"
            onPress={() => onApply({ filters: activeFilters, sort: currentSort, viewMode: viewMode === 'detailed' ? 'compact' : 'detailed' })}
            style={({ pressed }) => [styles.viewButton, pressed && styles.pressed]}>
            <AppIcon name="compactList" size={18} />
          </Pressable>
        </View>
        <View style={styles.contextRow}>
          <Text accessibilityLiveRegion="polite" style={styles.resultText}>
            {activeFilters.length ? `${resultCount} of ${resultLabel(totalCount)}` : resultLabel(resultCount)}
          </Text>
          {activeFilters.length ? (
            <Pressable accessibilityLabel={`Clear all ${categoryLabel} filters`} accessibilityRole="button" onPress={clearFilters} hitSlop={8}>
              <Text style={styles.clearText}>Clear filters</Text>
            </Pressable>
          ) : null}
        </View>
      </View>

      <DetailModal
        onClose={() => setVisible(false)}
        subtitle={`${draftResultCount} of ${resultLabel(totalCount)}`}
        title="Sort and filter"
        visible={visible}>
        <ControlSection title="Sort by">
          {availableSortOptions.map((option) => (
            <SelectionRow
              key={option.key}
              label={option.label}
              onPress={() => setDraftSort(option.key as WatchlistListSort)}
              selected={draftSort === option.key}
              type="radio"
            />
          ))}
        </ControlSection>

        <ControlSection title="Filters">
          {groupFilterOptions(availableFilterOptions).map(([dimension, options]) => (
            <View key={dimension} style={styles.filterGroup}>
              <Text style={styles.filterGroupLabel}>{formatDimension(dimension)}</Text>
              {options.map((option) => (
                <SelectionRow
                  key={option.key}
                  label={option.label}
                  onPress={() => setDraftFilters((current) => current.includes(option.key as WatchlistListFilter)
                    ? current.filter((filter) => filter !== option.key)
                    : [...current, option.key as WatchlistListFilter])}
                  selected={draftFilters.includes(option.key as WatchlistListFilter)}
                  type="checkbox"
                />
              ))}
            </View>
          ))}
        </ControlSection>

        <ControlSection title="View">
          <View style={styles.viewModeRow}>
            {(['compact', 'detailed'] as const).map((mode) => (
              <Pressable
                accessibilityLabel={`${mode} watchlist view`}
                accessibilityRole="radio"
                accessibilityState={{ checked: draftViewMode === mode }}
                key={mode}
                onPress={() => setDraftViewMode(mode)}
                style={({ pressed }) => [styles.viewModeButton, draftViewMode === mode && styles.viewModeSelected, pressed && styles.pressed]}>
                <Text style={[styles.viewModeText, draftViewMode === mode && styles.activeText]}>{capitalize(mode)}</Text>
              </Pressable>
            ))}
          </View>
        </ControlSection>

        <View style={styles.footer}>
          <Pressable
            accessibilityLabel={`Reset ${categoryLabel} list controls`}
            accessibilityRole="button"
            onPress={() => {
              onReset();
              setVisible(false);
              AccessibilityInfo.announceForAccessibility(`${capitalize(categoryLabel)} list controls reset.`);
            }}
            style={({ pressed }) => [styles.resetButton, pressed && styles.pressed]}>
            <Text style={styles.resetText}>Reset</Text>
          </Pressable>
          <Pressable accessibilityLabel={`Apply ${categoryLabel} list controls`} accessibilityRole="button" onPress={apply} style={({ pressed }) => [styles.applyButton, pressed && styles.pressed]}>
            <Text style={styles.applyText}>Apply · {draftResultCount}</Text>
          </Pressable>
        </View>
      </DetailModal>
    </>
  );
}

function ControlSection({ children, title }: { children: ReactNode; title: string }) {
  return <View style={styles.section}><Text style={styles.sectionTitle}>{title}</Text>{children}</View>;
}

function SelectionRow({ label, onPress, selected, type }: { label: string; onPress: () => void; selected: boolean; type: 'checkbox' | 'radio' }) {
  return (
    <Pressable
      accessibilityLabel={label}
      accessibilityRole={type}
      accessibilityState={{ checked: selected }}
      onPress={onPress}
      style={({ pressed }) => [styles.selectionRow, pressed && styles.pressed]}>
      <View style={[type === 'radio' ? styles.radio : styles.checkbox, selected && styles.selectionSelected]}>
        {selected ? (
          <View style={type === 'radio' ? styles.radioDot : styles.checkMark}>
            {type === 'checkbox' ? <AppIcon color={Theme.colors.background} name="check" size={13} /> : null}
          </View>
        ) : null}
      </View>
      <Text style={[styles.selectionLabel, selected && styles.activeText]}>{label}</Text>
    </Pressable>
  );
}

function groupFilterOptions(options: ListControlOption[]) {
  const groups = new Map<string, ListControlOption[]>();
  options.forEach((option) => {
    const dimension = option.dimension ?? 'other';
    groups.set(dimension, [...(groups.get(dimension) ?? []), option]);
  });
  return [...groups.entries()];
}

function formatDimension(value: string) {
  if (value === 'relative_strength') return 'Relative strength';
  return capitalize(value);
}

function capitalize(value: string) {
  return `${value.charAt(0).toUpperCase()}${value.slice(1)}`;
}

function singularCategory(category: WatchlistCategory) {
  if (category === 'stocks') return 'stock';
  if (category === 'sectors') return 'sector';
  return 'theme';
}

const styles = StyleSheet.create({
  activeButton: { backgroundColor: Theme.colors.accentSoft, borderColor: Theme.colors.accent },
  activeText: { color: Theme.colors.accent },
  applyButton: { alignItems: 'center', backgroundColor: Theme.colors.accent, borderRadius: Theme.radii.small, flex: 1, justifyContent: 'center', minHeight: 48, paddingHorizontal: Spacing.three },
  applyText: { color: Theme.colors.background, fontSize: Typography.body.fontSize, fontWeight: Typography.weights.strong },
  checkbox: { alignItems: 'center', borderColor: Theme.colors.border, borderRadius: 5, borderWidth: 1, height: 20, justifyContent: 'center', width: 20 },
  checkMark: { alignItems: 'center', justifyContent: 'center' },
  clearText: { color: Theme.colors.accent, fontSize: Typography.caption.fontSize, fontWeight: Typography.weights.strong },
  combinedButton: { flex: 1, justifyContent: 'center', minWidth: 0, position: 'relative' },
  combinedButtonContent: { alignItems: 'center', flexDirection: 'row', gap: Spacing.one, justifyContent: 'center', minWidth: 0 },
  contextRow: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between', minHeight: 18 },
  controlButton: { alignItems: 'center', backgroundColor: Theme.colors.backgroundMuted, borderColor: Theme.colors.border, borderRadius: Theme.radii.small, borderWidth: 1, flexDirection: 'row', gap: Spacing.one, justifyContent: 'center', minHeight: 44, paddingHorizontal: Spacing.two },
  controlRow: { flexDirection: 'row', gap: Spacing.one },
  controlText: { color: Theme.colors.textMuted, fontSize: Typography.small.fontSize, fontWeight: Typography.weights.strong },
  disclosure: { color: Theme.colors.textMuted, fontSize: Typography.supportTitle.fontSize, fontWeight: Typography.weights.strong, position: 'absolute', right: Spacing.two },
  filterGroup: { gap: Spacing.half },
  filterGroupLabel: { color: Theme.colors.textMuted, fontSize: Typography.chartLabel.fontSize, fontWeight: Typography.weights.strong, marginTop: Spacing.one, textTransform: 'uppercase' },
  filterCount: { alignItems: 'center', backgroundColor: Theme.colors.accent, borderRadius: Theme.radii.pill, height: 20, justifyContent: 'center', minWidth: 20, paddingHorizontal: Spacing.one },
  filterCountText: { color: Theme.colors.background, fontSize: Typography.chartLabel.fontSize, fontWeight: Typography.weights.strong },
  footer: { flexDirection: 'row', gap: Spacing.two },
  pressed: { opacity: 0.72 },
  radio: { alignItems: 'center', borderColor: Theme.colors.border, borderRadius: 10, borderWidth: 1, height: 20, justifyContent: 'center', width: 20 },
  radioDot: { backgroundColor: Theme.colors.background, borderRadius: 4, height: 8, width: 8 },
  resetButton: { alignItems: 'center', borderColor: Theme.colors.border, borderRadius: Theme.radii.small, borderWidth: 1, justifyContent: 'center', minHeight: 48, paddingHorizontal: Spacing.three },
  resetText: { color: Theme.colors.text, fontSize: Typography.body.fontSize, fontWeight: Typography.weights.strong },
  resultText: { color: Theme.colors.textMuted, fontSize: Typography.caption.fontSize, fontWeight: Typography.weights.strong },
  section: { gap: Spacing.one },
  sectionTitle: { color: Theme.colors.text, fontSize: Typography.bodyLarge.fontSize, fontWeight: Typography.weights.strong, marginBottom: Spacing.one },
  selectionLabel: { color: Theme.colors.text, flex: 1, fontSize: Typography.control.fontSize, fontWeight: Typography.weights.strong },
  selectionRow: { alignItems: 'center', flexDirection: 'row', gap: Spacing.two, minHeight: 44 },
  selectionSelected: { backgroundColor: Theme.colors.accent, borderColor: Theme.colors.accent },
  sortSummary: { color: Theme.colors.textMuted, flexShrink: 1, fontSize: Typography.caption.fontSize, fontWeight: Typography.weights.strong, minWidth: 0 },
  viewButton: { alignItems: 'center', backgroundColor: Theme.colors.backgroundMuted, borderColor: Theme.colors.border, borderRadius: Theme.radii.small, borderWidth: 1, height: 44, justifyContent: 'center', width: 44 },
  viewIcon: { color: Theme.colors.textMuted, fontSize: Typography.toolbarTitle.fontSize, fontWeight: Typography.weights.strong },
  viewModeButton: { alignItems: 'center', backgroundColor: Theme.colors.backgroundMuted, borderColor: Theme.colors.border, borderRadius: Theme.radii.small, borderWidth: 1, flex: 1, justifyContent: 'center', minHeight: 44 },
  viewModeRow: { flexDirection: 'row', gap: Spacing.one },
  viewModeSelected: { backgroundColor: Theme.colors.accentSoft, borderColor: Theme.colors.accent },
  viewModeText: { color: Theme.colors.textMuted, fontSize: Typography.control.fontSize, fontWeight: Typography.weights.strong },
  wrapper: { gap: Spacing.half },
});
