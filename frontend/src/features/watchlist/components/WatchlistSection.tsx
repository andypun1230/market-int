import type { ReactNode } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Spacing, Theme } from '@/constants/theme';
import type { WatchlistDecisionGroup } from '@/features/watchlist/watchlistDecision';
import type { ClassifiedWatchlistItem } from '@/features/watchlist/types';

type WatchlistSectionProps = {
  children: ReactNode;
  collapsed: boolean;
  group: WatchlistDecisionGroup;
  items: ClassifiedWatchlistItem[];
  onToggleCollapsed: () => void;
};

const SECTION_META: Record<WatchlistDecisionGroup, { accent: string; subtitle: string; title: string }> = {
  action_required: {
    accent: Theme.colors.danger,
    subtitle: 'Breakouts, warnings, and data issues that need a decision.',
    title: '🔥 Action Required',
  },
  watching_closely: {
    accent: Theme.colors.accent,
    subtitle: 'Improving or developing setups worth monitoring closely.',
    title: '👀 Watching Closely',
  },
  stable_waiting: {
    accent: Theme.colors.textMuted,
    subtitle: 'Quiet setups waiting for a clearer trigger.',
    title: '⏸ Stable / Waiting',
  },
};

export function WatchlistSection({ children, collapsed, group, items, onToggleCollapsed }: WatchlistSectionProps) {
  if (!items.length) return null;
  const meta = SECTION_META[group];
  return (
    <View style={[styles.section, { borderTopColor: meta.accent }]}>
      <Pressable
        accessibilityLabel={`${meta.title}, ${items.length} stocks`}
        accessibilityRole="button"
        accessibilityState={{ expanded: !collapsed }}
        onPress={onToggleCollapsed}
        style={({ pressed }) => [styles.header, pressed && styles.pressed]}>
        <View style={styles.headerText}>
          <Text style={styles.title}>{meta.title}</Text>
          <Text style={styles.subtitle}>{meta.subtitle}</Text>
        </View>
        <View style={[styles.countPill, { borderColor: meta.accent }]}>
          <Text style={[styles.countText, { color: meta.accent }]}>{items.length}</Text>
        </View>
        <Text style={styles.chevron}>{collapsed ? '›' : '⌄'}</Text>
      </Pressable>
      {!collapsed ? <View style={styles.list}>{children}</View> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  chevron: {
    color: Theme.colors.textMuted,
    fontSize: 22,
    fontWeight: '900',
    width: 20,
  },
  countPill: {
    alignItems: 'center',
    backgroundColor: Theme.colors.backgroundMuted,
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    minWidth: 30,
    paddingHorizontal: Spacing.two,
    paddingVertical: Spacing.one,
  },
  countText: {
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
    gap: Spacing.one,
    marginTop: Spacing.two,
  },
  pressed: {
    opacity: 0.78,
  },
  section: {
    borderTopWidth: 2,
    paddingTop: Spacing.two,
  },
  subtitle: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '700',
    lineHeight: 15,
  },
  title: {
    color: Theme.colors.text,
    fontSize: 16,
    fontWeight: '900',
  },
});
