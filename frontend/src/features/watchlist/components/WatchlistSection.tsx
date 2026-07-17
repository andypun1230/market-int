import type { ReactNode } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { Spacing, Theme } from '@/constants/theme';
import { getGroupLabel } from '@/features/watchlist/watchlistClassifier';
import type { ClassifiedWatchlistItem, WatchlistGroup } from '@/features/watchlist/types';

type WatchlistSectionProps = {
  children: ReactNode;
  collapsed: boolean;
  group: WatchlistGroup;
  items: ClassifiedWatchlistItem[];
  onToggleCollapsed: () => void;
};

const GROUP_SUBTITLES: Record<WatchlistGroup, string> = {
  data_unavailable: 'Stocks that cannot currently be evaluated reliably.',
  high_priority: 'Stocks with important setups or near-term signals.',
  momentum: 'Stocks showing constructive momentum without a higher-priority event.',
  needs_attention: 'Stocks with weakening conditions, stale data, or risks.',
  watching: 'Saved stocks without a major active signal.',
};

export function WatchlistSection({
  children,
  collapsed,
  group,
  items,
  onToggleCollapsed,
}: WatchlistSectionProps) {
  if (!items.length) {
    return null;
  }

  const title = getGroupLabel(group);

  return (
    <DashboardCard>
      <Pressable
        accessibilityLabel={`${title}, ${items.length} stocks`}
        accessibilityRole="button"
        accessibilityState={{ expanded: !collapsed }}
        onPress={onToggleCollapsed}
        style={({ pressed }) => [styles.header, pressed && styles.pressed]}
      >
        <View style={styles.headerText}>
          <Text style={styles.title}>{title}</Text>
          <Text style={styles.subtitle}>{GROUP_SUBTITLES[group]}</Text>
        </View>
        <View style={styles.countPill}>
          <Text style={styles.countText}>{items.length}</Text>
        </View>
        <Text style={styles.chevron}>{collapsed ? '›' : '⌄'}</Text>
      </Pressable>
      {!collapsed ? <View style={styles.list}>{children}</View> : null}
    </DashboardCard>
  );
}

const styles = StyleSheet.create({
  chevron: {
    color: Theme.colors.textMuted,
    fontSize: 22,
    fontWeight: '900',
    width: 22,
  },
  countPill: {
    alignItems: 'center',
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    minWidth: 30,
    paddingHorizontal: Spacing.two,
    paddingVertical: Spacing.one,
  },
  countText: {
    color: Theme.colors.text,
    fontSize: 12,
    fontWeight: '900',
  },
  header: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
  },
  headerText: {
    flex: 1,
    gap: Spacing.half,
  },
  list: {
    gap: Spacing.two,
    marginTop: Spacing.twoAndHalf,
  },
  pressed: {
    opacity: 0.78,
  },
  subtitle: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '700',
    lineHeight: 17,
  },
  title: {
    color: Theme.colors.text,
    fontSize: 16,
    fontWeight: '900',
  },
});
