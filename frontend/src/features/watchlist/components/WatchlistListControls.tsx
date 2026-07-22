import type { ReactNode } from 'react';
import { useMemo, useState } from 'react';
import { AccessibilityInfo, Platform, Pressable, StyleSheet, Text, View } from 'react-native';
import { SymbolView } from 'expo-symbols';

import { DetailModal } from '@/components/ui/DetailModal';
import { Spacing, Theme } from '@/constants/theme';
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
            <Text style={styles.disclosure}>⌄</Text>
          </Pressable>
          <Pressable
            accessibilityLabel={`Switch to ${viewMode === 'detailed' ? 'compact' : 'detailed'} view`}
            accessibilityRole="button"
            onPress={() => onApply({ filters: activeFilters, sort: currentSort, viewMode: viewMode === 'detailed' ? 'compact' : 'detailed' })}
            style={({ pressed }) => [styles.viewButton, pressed && styles.pressed]}>
            {Platform.OS === 'web' ? (
              <Text style={styles.viewIcon}>{viewMode === 'compact' ? '☷' : '≡'}</Text>
            ) : (
              <SymbolView
                name={(viewMode === 'compact'
                  ? { android: 'view_agenda', ios: 'rectangle.grid.1x2', web: 'rectangle.grid.1x2' }
                  : { android: 'view_headline', ios: 'list.bullet', web: 'list.bullet' }) as never}
                size={18}
                tintColor={Theme.colors.textMuted}
                weight="bold"
              />
            )}
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
        {selected ? <View style={type === 'radio' ? styles.radioDot : styles.checkMark}><Text style={styles.checkText}>{type === 'checkbox' ? '✓' : ''}</Text></View> : null}
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
  applyText: { color: Theme.colors.background, fontSize: 14, fontWeight: '900' },
  checkbox: { alignItems: 'center', borderColor: Theme.colors.border, borderRadius: 5, borderWidth: 1, height: 20, justifyContent: 'center', width: 20 },
  checkMark: { alignItems: 'center', justifyContent: 'center' },
  checkText: { color: Theme.colors.background, fontSize: 13, fontWeight: '900', lineHeight: 14 },
  clearText: { color: Theme.colors.accent, fontSize: 11, fontWeight: '900' },
  combinedButton: { flex: 1, justifyContent: 'center', minWidth: 0, position: 'relative' },
  combinedButtonContent: { alignItems: 'center', flexDirection: 'row', gap: Spacing.one, justifyContent: 'center', minWidth: 0 },
  contextRow: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between', minHeight: 18 },
  controlButton: { alignItems: 'center', backgroundColor: Theme.colors.backgroundMuted, borderColor: Theme.colors.border, borderRadius: Theme.radii.small, borderWidth: 1, flexDirection: 'row', gap: Spacing.one, justifyContent: 'center', minHeight: 42, paddingHorizontal: Spacing.two },
  controlRow: { flexDirection: 'row', gap: Spacing.one },
  controlText: { color: Theme.colors.textMuted, fontSize: 12, fontWeight: '900' },
  disclosure: { color: Theme.colors.textMuted, fontSize: 16, fontWeight: '900', position: 'absolute', right: Spacing.two },
  filterGroup: { gap: Spacing.half },
  filterGroupLabel: { color: Theme.colors.textMuted, fontSize: 10, fontWeight: '900', marginTop: Spacing.one, textTransform: 'uppercase' },
  filterCount: { alignItems: 'center', backgroundColor: Theme.colors.accent, borderRadius: Theme.radii.pill, height: 20, justifyContent: 'center', minWidth: 20, paddingHorizontal: Spacing.one },
  filterCountText: { color: Theme.colors.background, fontSize: 10, fontWeight: '900' },
  footer: { flexDirection: 'row', gap: Spacing.two },
  pressed: { opacity: 0.72 },
  radio: { alignItems: 'center', borderColor: Theme.colors.border, borderRadius: 10, borderWidth: 1, height: 20, justifyContent: 'center', width: 20 },
  radioDot: { backgroundColor: Theme.colors.background, borderRadius: 4, height: 8, width: 8 },
  resetButton: { alignItems: 'center', borderColor: Theme.colors.border, borderRadius: Theme.radii.small, borderWidth: 1, justifyContent: 'center', minHeight: 48, paddingHorizontal: Spacing.three },
  resetText: { color: Theme.colors.text, fontSize: 14, fontWeight: '900' },
  resultText: { color: Theme.colors.textMuted, fontSize: 11, fontWeight: '800' },
  section: { gap: Spacing.one },
  sectionTitle: { color: Theme.colors.text, fontSize: 15, fontWeight: '900', marginBottom: Spacing.one },
  selectionLabel: { color: Theme.colors.text, flex: 1, fontSize: 13, fontWeight: '800' },
  selectionRow: { alignItems: 'center', flexDirection: 'row', gap: Spacing.two, minHeight: 44 },
  selectionSelected: { backgroundColor: Theme.colors.accent, borderColor: Theme.colors.accent },
  sortSummary: { color: Theme.colors.textMuted, flexShrink: 1, fontSize: 11, fontWeight: '800', minWidth: 0 },
  viewButton: { alignItems: 'center', backgroundColor: Theme.colors.backgroundMuted, borderColor: Theme.colors.border, borderRadius: Theme.radii.small, borderWidth: 1, height: 42, justifyContent: 'center', width: 42 },
  viewIcon: { color: Theme.colors.textMuted, fontSize: 19, fontWeight: '900' },
  viewModeButton: { alignItems: 'center', backgroundColor: Theme.colors.backgroundMuted, borderColor: Theme.colors.border, borderRadius: Theme.radii.small, borderWidth: 1, flex: 1, justifyContent: 'center', minHeight: 44 },
  viewModeRow: { flexDirection: 'row', gap: Spacing.one },
  viewModeSelected: { backgroundColor: Theme.colors.accentSoft, borderColor: Theme.colors.accent },
  viewModeText: { color: Theme.colors.textMuted, fontSize: 13, fontWeight: '900' },
  wrapper: { gap: Spacing.half },
});
