import type { ReactNode } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { Spacing, Theme, Typography } from '@/constants/theme';

interface SummaryTileProps {
  label: string;
  value: string | number;
  valueColor?: string;
  icon?: ReactNode;
}

export function SummaryTile({ icon, label, value, valueColor }: SummaryTileProps) {
  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text numberOfLines={1} style={styles.label}>{label}</Text>
        {icon ? <View style={styles.icon}>{icon}</View> : null}
      </View>
      <Text numberOfLines={2} style={[styles.value, valueColor ? { color: valueColor } : null]}>
        {value}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    flexGrow: 1,
    minWidth: '47%',
    padding: Spacing.twoAndHalf,
  },
  header: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
    marginBottom: Spacing.one,
  },
  label: {
    color: Theme.colors.textMuted,
    flex: 1,
    fontSize: Typography.caption.fontSize,
    fontWeight: Typography.weights.strong,
    textTransform: 'uppercase',
  },
  icon: {
    flexShrink: 0,
  },
  value: {
    color: Theme.colors.text,
    fontSize: Typography.bodyLarge.fontSize,
    fontWeight: Typography.weights.strong,
    lineHeight: 20,
  },
});
