import { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Spacing, Theme } from '@/constants/theme';
import {
  normalizeWatchlistId,
  useWatchlist,
  type WatchlistItemType,
} from '@/features/watchlist/store';

type WatchlistBookmarkButtonProps = {
  id: string;
  name: string;
  type: WatchlistItemType;
};

export function WatchlistBookmarkButton({ id, name, type }: WatchlistBookmarkButtonProps) {
  const watchlist = useWatchlist();
  const [saving, setSaving] = useState(false);
  const normalizedId = normalizeWatchlistId(type, id);
  const saved = watchlist.isInWatchlist(type, normalizedId);
  const disabled = !normalizedId || saving;

  const handlePress = () => {
    if (!normalizedId) {
      return;
    }
    setSaving(true);
    if (type === 'stock') {
      watchlist.toggleWatchlistItem({ id: normalizedId, name, ticker: normalizedId, type });
    } else {
      watchlist.toggleWatchlistItem({ id: normalizedId, name, type });
    }
    setTimeout(() => setSaving(false), 120);
  };

  return (
    <View style={styles.container}>
      <Pressable
        accessibilityLabel={`${saved ? 'Remove' : 'Add'} ${name} watchlist`}
        accessibilityRole="button"
        disabled={disabled}
        onPress={handlePress}
        style={({ pressed }) => [
          styles.button,
          saved && styles.activeButton,
          disabled && styles.disabled,
          pressed && styles.pressed,
        ]}>
        <Text style={[styles.icon, saved && styles.activeText]}>{saved ? '★' : '☆'}</Text>
        <Text style={[styles.text, saved && styles.activeText]}>{saving ? 'Saving...' : saved ? 'Saved' : 'Save'}</Text>
      </Pressable>
      {watchlist.storageError ? <Text style={styles.errorText}>{watchlist.storageError}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  activeButton: {
    borderColor: Theme.colors.warning,
  },
  activeText: {
    color: Theme.colors.warning,
  },
  button: {
    alignItems: 'center',
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    flexDirection: 'row',
    gap: Spacing.one,
    justifyContent: 'center',
    minHeight: 44,
    paddingHorizontal: Spacing.twoAndHalf,
  },
  container: {
    alignItems: 'flex-start',
    gap: Spacing.one,
  },
  disabled: {
    opacity: 0.55,
  },
  errorText: {
    color: Theme.colors.warning,
    fontSize: 11,
    fontWeight: '800',
    maxWidth: 220,
  },
  icon: {
    color: Theme.colors.textMuted,
    fontSize: 14,
    fontWeight: '900',
  },
  pressed: {
    opacity: 0.78,
  },
  text: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '900',
  },
});
