import { PropsWithChildren } from 'react';
import { ColorValue, StyleSheet, Text, View, ViewStyle } from 'react-native';

import { Spacing, Theme } from '@/constants/theme';

type DashboardCardProps = PropsWithChildren<{
  title?: string;
  subtitle?: string;
  accentColor?: ColorValue;
  style?: ViewStyle;
}>;

export function DashboardCard({
  accentColor,
  children,
  title,
  subtitle,
  style,
}: DashboardCardProps) {
  return (
    <View style={[styles.card, style]}>
      {accentColor ? <View style={[styles.accent, { backgroundColor: accentColor }]} /> : null}
      {(title || subtitle) && (
        <View style={styles.header}>
          {title ? <Text style={styles.title}>{title}</Text> : null}
          {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
        </View>
      )}
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: Theme.colors.card,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.card,
    borderWidth: 1,
    overflow: 'hidden',
    padding: Spacing.three,
  },
  accent: {
    height: 3,
    left: 0,
    position: 'absolute',
    right: 0,
    top: 0,
  },
  header: {
    gap: Spacing.one,
    marginBottom: Spacing.twoAndHalf,
  },
  title: {
    color: Theme.colors.text,
    fontSize: 17,
    fontWeight: '700',
  },
  subtitle: {
    color: Theme.colors.textMuted,
    fontSize: 13,
    lineHeight: 18,
  },
});
