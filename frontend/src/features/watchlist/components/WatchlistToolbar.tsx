import { useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { AppButton } from '@/components/ui/AppButton';
import { AppIcon } from '@/components/ui/AppIcon';
import { Spacing, Theme, Typography } from '@/constants/theme';
import { getSortLabel, WATCHLIST_SORT_OPTIONS } from '@/features/watchlist/watchlistSort';
import type { WatchlistSortMode } from '@/features/watchlist/types';

type WatchlistToolbarProps = {
  canAdd: boolean;
  inputError: string | null;
  onAdd: () => void;
  onQueryChange: (value: string) => void;
  onRefresh: () => void;
  onSortChange: (sortMode: WatchlistSortMode) => void;
  query: string;
  refreshing: boolean;
  sortMode: WatchlistSortMode;
};

export function WatchlistToolbar({
  canAdd,
  inputError,
  onAdd,
  onQueryChange,
  onRefresh,
  onSortChange,
  query,
  refreshing,
  sortMode,
}: WatchlistToolbarProps) {
  const [sortMenuOpen, setSortMenuOpen] = useState(false);

  const handleSortChange = (nextSortMode: WatchlistSortMode) => {
    onSortChange(nextSortMode);
    setSortMenuOpen(false);
  };

  return (
    <View style={styles.container}>
      <View style={styles.searchRow}>
        <TextInput
          accessibilityLabel="Search or add ticker"
          autoCapitalize="characters"
          autoCorrect={false}
          onChangeText={(value) => onQueryChange(value.toUpperCase())}
          onSubmitEditing={onAdd}
          placeholder="Search or add ticker"
          placeholderTextColor={Theme.colors.textMuted}
          returnKeyType="done"
          style={styles.searchInput}
          value={query}
        />
        <AppButton
          accessibilityLabel="Add ticker to stock watchlist"
          disabled={!canAdd}
          label="Add ticker"
          leadingIcon={<AppIcon color={Theme.colors.background} name="add" size={20} />}
          onPress={onAdd}
          style={styles.iconButton}
          variant="primary"
        />
        <AppButton
          accessibilityLabel="Refresh watchlist"
          label="Refresh watchlist"
          leadingIcon={<AppIcon color={Theme.colors.text} name="refresh" size={19} />}
          loading={refreshing}
          onPress={onRefresh}
          style={styles.refreshButton}
          variant="icon"
        />
      </View>
      {inputError ? <Text style={styles.errorText}>{inputError}</Text> : null}
      <View style={styles.toolbarRow}>
        <Pressable
          accessibilityLabel={`Sort watchlist by ${getSortLabel(sortMode)}`}
          accessibilityRole="button"
          accessibilityState={{ expanded: sortMenuOpen }}
          onPress={() => setSortMenuOpen((current) => !current)}
          style={({ pressed }) => [styles.sortButton, pressed && styles.pressed]}>
          <Text numberOfLines={1} style={styles.sortLabel}>Sort: {getSortLabel(sortMode)}</Text>
          <AppIcon name={sortMenuOpen ? 'chevronUp' : 'chevronDown'} size={18} />
        </Pressable>
      </View>
      {sortMenuOpen ? (
        <View style={styles.sortMenu}>
          {WATCHLIST_SORT_OPTIONS.map((option) => {
            const selected = option.key === sortMode;
            return (
              <Pressable
                accessibilityLabel={`Sort by ${option.label}`}
                accessibilityRole="button"
                accessibilityState={{ checked: selected }}
                key={option.key}
                onPress={() => handleSortChange(option.key)}
                style={({ pressed }) => [
                  styles.sortMenuItem,
                  selected && styles.sortMenuItemSelected,
                  pressed && styles.pressed,
                ]}>
                <Text style={[styles.sortMenuText, selected && styles.sortMenuTextSelected]}>{option.label}</Text>
                {selected ? <AppIcon color={Theme.colors.accent} name="check" size={15} /> : null}
              </Pressable>
            );
          })}
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: Spacing.two,
  },
  errorText: {
    color: Theme.colors.warning,
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.strong,
  },
  iconButton: {
    alignItems: 'center',
    backgroundColor: Theme.colors.accent,
    borderRadius: Theme.radii.small,
    height: 48,
    justifyContent: 'center',
    width: 48,
  },
  pressed: {
    opacity: 0.78,
  },
  refreshButton: {
    alignItems: 'center',
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    height: 48,
    justifyContent: 'center',
    width: 48,
  },
  searchInput: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    color: Theme.colors.text,
    flex: 1,
    fontSize: Typography.supportTitle.fontSize,
    fontWeight: Typography.weights.strong,
    minHeight: 48,
    paddingHorizontal: Spacing.twoAndHalf,
  },
  searchRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
  },
  sortButton: {
    alignItems: 'center',
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    flexDirection: 'row',
    gap: Spacing.one,
    minHeight: 44,
    paddingHorizontal: Spacing.twoAndHalf,
  },
  sortLabel: {
    color: Theme.colors.text,
    flex: 1,
    fontSize: Typography.control.fontSize,
    fontWeight: Typography.weights.strong,
  },
  sortMenu: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    overflow: 'hidden',
  },
  sortMenuItem: {
    alignItems: 'center',
    borderBottomColor: Theme.colors.border,
    borderBottomWidth: 1,
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
    minHeight: 44,
    paddingHorizontal: Spacing.twoAndHalf,
  },
  sortMenuItemSelected: {
    backgroundColor: Theme.colors.accentSoft,
  },
  sortMenuText: {
    color: Theme.colors.textMuted,
    flex: 1,
    fontSize: Typography.control.fontSize,
    fontWeight: Typography.weights.strong,
  },
  sortMenuTextSelected: {
    color: Theme.colors.text,
  },
  toolbarRow: {
    alignItems: 'center',
    flexDirection: 'row',
  },
});
