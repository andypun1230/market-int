import type { ReactNode } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { AppIcon } from '@/components/ui/AppIcon';
import { DashboardCard } from '@/components/cards/DashboardCard';
import { Spacing, Theme, Typography } from '@/constants/theme';
import { getSectorThemeGroupLabel } from '@/features/watchlist/sectorThemeClassifier';
import type { ClassifiedSectorThemeItem } from '@/features/watchlist/sectorThemeSort';
import type { SectorThemeGroup } from '@/features/watchlist/types';

type SectorThemeSectionProps = {
  children: ReactNode;
  collapsed: boolean;
  group: SectorThemeGroup;
  items: ClassifiedSectorThemeItem[];
  onToggleCollapsed: () => void;
};

const SUBTITLES: Record<SectorThemeGroup, string> = {
  data_unavailable: 'Not enough reliable data to classify.',
  improving: 'Momentum or participation is strengthening.',
  leading: 'Strong relative performance and leadership.',
  watching: 'Saved groups without a strong active signal.',
  weakening: 'Leadership or momentum is deteriorating.',
};

export function SectorThemeSection({
  children,
  collapsed,
  group,
  items,
  onToggleCollapsed,
}: SectorThemeSectionProps) {
  if (!items.length) {
    return null;
  }

  const title = getSectorThemeGroupLabel(group);

  return (
    <DashboardCard>
      <Pressable
        accessibilityLabel={`${title}, ${items.length} saved groups`}
        accessibilityRole="button"
        accessibilityState={{ expanded: !collapsed }}
        onPress={onToggleCollapsed}
        style={({ pressed }) => [styles.header, pressed && styles.pressed]}>
        <View style={styles.headerText}>
          <Text style={styles.title}>{title}</Text>
          <Text numberOfLines={1} style={styles.subtitle}>{SUBTITLES[group]}</Text>
        </View>
        <View style={styles.countPill}>
          <Text style={styles.countText}>{items.length}</Text>
        </View>
        <AppIcon name={collapsed ? 'chevronRight' : 'chevronDown'} size={17} />
      </Pressable>
      {!collapsed ? <View style={styles.list}>{children}</View> : null}
    </DashboardCard>
  );
}

const styles = StyleSheet.create({
  chevron: {
    color: Theme.colors.textMuted,
    fontSize: Typography.sectionHero.fontSize,
    fontWeight: Typography.weights.strong,
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
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.strong,
  },
  header: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
  },
  headerText: {
    flex: 1,
    gap: Spacing.half,
    minWidth: 0,
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
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.emphasis,
    lineHeight: 17,
  },
  title: {
    color: Theme.colors.text,
    fontSize: Typography.supportTitle.fontSize,
    fontWeight: Typography.weights.strong,
  },
});
