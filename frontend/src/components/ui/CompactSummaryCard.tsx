import type { ReactNode } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { AppIcon } from '@/components/ui/AppIcon';
import { Spacing, Theme, Typography } from '@/constants/theme';
import { getToneColors, type Tone } from '@/components/ui/StatusBadge';

type CompactMetric = {
  label: string;
  tone?: Tone;
  value: string | number;
};

type CompactSummaryCardProps = {
  actionLabel?: string;
  badges?: ReactNode[];
  children?: ReactNode;
  onPress?: () => void;
  primaryMetric?: CompactMetric;
  secondaryMetric?: CompactMetric;
  subtitle?: string;
  title: string;
};

export function CompactSummaryCard({
  actionLabel = 'View Details',
  badges,
  children,
  onPress,
  primaryMetric,
  secondaryMetric,
  subtitle,
  title,
}: CompactSummaryCardProps) {
  const content = (
    <>
      <View style={styles.header}>
        <View style={styles.copy}>
          <Text numberOfLines={1} style={styles.title}>{title}</Text>
          {subtitle ? <Text numberOfLines={2} style={styles.subtitle}>{subtitle}</Text> : null}
        </View>
        <View style={styles.metrics}>
          {primaryMetric ? <Metric metric={primaryMetric} /> : null}
          {secondaryMetric ? <Metric metric={secondaryMetric} compact /> : null}
        </View>
      </View>

      {badges?.length ? <View style={styles.badges}>{badges}</View> : null}
      {children ? <View style={styles.children}>{children}</View> : null}

      {onPress ? (
      <View style={styles.actionRow}>
          <Text numberOfLines={1} style={styles.actionText}>{actionLabel}</Text>
          <AppIcon color={Theme.colors.accent} name="chevronRight" size={16} />
        </View>
      ) : null}
    </>
  );

  if (onPress) {
    return (
      <Pressable
        accessibilityRole="button"
        onPress={onPress}
        style={({ pressed }) => [styles.card, pressed && styles.cardPressed]}>
        {content}
      </Pressable>
    );
  }

  return (
    <View style={styles.card}>
      {content}
    </View>
  );
}

function Metric({ compact = false, metric }: { compact?: boolean; metric: CompactMetric }) {
  const colors = getToneColors(metric.tone ?? 'muted');

  return (
    <View style={styles.metric}>
      <Text style={styles.metricLabel}>{metric.label}</Text>
      <Text
        numberOfLines={1}
        style={[
          compact ? styles.metricValueCompact : styles.metricValue,
          metric.tone ? { color: colors.text } : null,
        ]}>
        {metric.value}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: Theme.colors.card,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.card,
    borderWidth: 1,
    gap: Spacing.twoAndHalf,
    padding: Spacing.twoAndHalf,
  },
  cardPressed: {
    opacity: 0.82,
  },
  header: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  copy: {
    flex: 1,
    gap: Spacing.one,
  },
  title: {
    color: Theme.colors.text,
    fontSize: Typography.toolbarTitle.fontSize,
    fontWeight: Typography.weights.strong,
  },
  subtitle: {
    color: Theme.colors.textMuted,
    fontSize: Typography.control.fontSize,
    fontWeight: Typography.weights.emphasis,
    lineHeight: 18,
  },
  metrics: {
    alignItems: 'flex-end',
    gap: Spacing.one,
    maxWidth: 98,
  },
  metric: {
    alignItems: 'flex-end',
  },
  metricLabel: {
    color: Theme.colors.textMuted,
    fontSize: Typography.chartLabel.fontSize,
    fontWeight: Typography.weights.strong,
    textTransform: 'uppercase',
  },
  metricValue: {
    color: Theme.colors.text,
    fontSize: Typography.sectionHero.fontSize,
    fontWeight: Typography.weights.strong,
    marginTop: Spacing.half,
  },
  metricValueCompact: {
    color: Theme.colors.text,
    fontSize: Typography.body.fontSize,
    fontWeight: Typography.weights.strong,
    marginTop: Spacing.half,
  },
  badges: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.one,
  },
  children: {
    gap: Spacing.two,
  },
  actionRow: {
    alignItems: 'center',
    backgroundColor: Theme.colors.accentSoft,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    flexDirection: 'row',
    justifyContent: 'space-between',
    minHeight: 44,
    paddingHorizontal: Spacing.twoAndHalf,
    paddingVertical: Spacing.one,
  },
  actionText: {
    color: Theme.colors.accent,
    flex: 1,
    fontSize: Typography.control.fontSize,
    fontWeight: Typography.weights.strong,
  },
});
