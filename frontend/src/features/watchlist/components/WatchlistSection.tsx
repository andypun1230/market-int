import type { ReactNode } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { AppIcon } from '@/components/ui/AppIcon';
import { Spacing, Theme, Typography } from '@/constants/theme';
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
  action_now: {
    accent: Theme.colors.danger,
    subtitle: 'Fresh trading setups with an active trigger.',
    title: 'Action Now',
  },
  improving: {
    accent: Theme.colors.accent,
    subtitle: 'Momentum and relative strength are improving.',
    title: 'Improving',
  },
  weakening: {
    accent: Theme.colors.warning,
    subtitle: 'Trading evidence is deteriorating or support has weakened.',
    title: 'Weakening',
  },
  monitor: {
    accent: Theme.colors.textMuted,
    subtitle: 'No current trading trigger; continue monitoring.',
    title: 'Monitor',
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
        <AppIcon name={collapsed ? 'chevronRight' : 'chevronDown'} size={17} />
      </Pressable>
      {!collapsed ? <View style={styles.list}>{children}</View> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  chevron: {
    color: Theme.colors.textMuted,
    fontSize: Typography.sectionHero.fontSize,
    fontWeight: Typography.weights.strong,
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
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.strong,
  },
  header: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
    minHeight: 44,
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
    fontSize: Typography.caption.fontSize,
    fontWeight: Typography.weights.emphasis,
    lineHeight: 15,
  },
  title: {
    color: Theme.colors.text,
    fontSize: Typography.supportTitle.fontSize,
    fontWeight: Typography.weights.strong,
  },
});
