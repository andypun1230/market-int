import { StyleSheet, Text, View } from 'react-native';

import { Spacing, Theme } from '@/constants/theme';

type AnalysisSectionHeaderProps = {
  badge?: React.ReactNode;
  controls?: React.ReactNode;
  description?: string;
  title?: string;
};

export function AnalysisSectionHeader({
  badge,
  controls,
  description,
  title,
}: AnalysisSectionHeaderProps) {
  if (!title && !description && !badge && !controls) {
    return null;
  }

  return (
    <View style={styles.container}>
      {title || description || badge ? (
        <View style={styles.textRow}>
          <View style={styles.titleBlock}>
            {title ? <Text style={styles.title}>{title}</Text> : null}
            {description ? <Text style={styles.description}>{description}</Text> : null}
          </View>
          {badge ? <View style={styles.badgeSlot}>{badge}</View> : null}
        </View>
      ) : null}
      {controls ? <View style={styles.controls}>{controls}</View> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  badgeSlot: {
    alignItems: 'flex-end',
    flexShrink: 0,
  },
  container: {
    gap: Spacing.two,
    marginBottom: Spacing.two,
  },
  controls: {
    gap: Spacing.two,
  },
  description: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '800',
    lineHeight: 17,
  },
  textRow: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  title: {
    color: Theme.colors.text,
    fontSize: 14,
    fontWeight: '900',
  },
  titleBlock: {
    flex: 1,
    gap: Spacing.half,
  },
});
