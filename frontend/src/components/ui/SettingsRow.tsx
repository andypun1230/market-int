import type { ReactNode } from 'react';
import { Pressable, StyleSheet, Switch, Text, View } from 'react-native';

import { AppIcon } from '@/components/ui/AppIcon';
import { Spacing, Theme, Typography } from '@/constants/theme';

type SettingsRowProps = {
  badge?: ReactNode;
  description?: string;
  disabled?: boolean;
  onPress?: () => void;
  onValueChange?: (value: boolean) => void;
  title: string;
  value?: ReactNode;
  switchValue?: boolean;
};

export function SettingsRow({
  badge,
  description,
  disabled = false,
  onPress,
  onValueChange,
  title,
  value,
  switchValue,
}: SettingsRowProps) {
  const isSwitch = typeof switchValue === 'boolean' && onValueChange;
  const row = (
    <View style={[styles.row, disabled && styles.disabled]}>
      <View style={styles.copy}>
        <View style={styles.titleRow}>
          <Text style={styles.title}>{title}</Text>
          {badge}
        </View>
        {description ? <Text style={styles.description}>{description}</Text> : null}
      </View>
      {isSwitch ? (
        <Switch
          accessibilityLabel={title}
          disabled={disabled}
          ios_backgroundColor={Theme.colors.cardMuted}
          onValueChange={onValueChange}
          thumbColor={switchValue ? Theme.colors.accent : Theme.colors.textMuted}
          trackColor={{ false: Theme.colors.cardMuted, true: Theme.colors.accentSoft }}
          style={styles.switchControl}
          value={switchValue}
        />
      ) : (
        <View style={styles.valueRow}>
          {typeof value === 'string' || typeof value === 'number' ? (
            <Text numberOfLines={1} style={styles.value}>{value}</Text>
          ) : value}
          {onPress ? <AppIcon name="chevronRight" size={18} /> : null}
        </View>
      )}
    </View>
  );

  if (!onPress || disabled || isSwitch) {
    return row;
  }

  return (
    <Pressable
      accessibilityLabel={description ? `${title}. ${description}` : title}
      accessibilityRole="button"
      onPress={onPress}
      style={({ pressed }) => pressed && styles.pressed}>
      {row}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  copy: {
    flex: 1,
    gap: Spacing.half,
  },
  description: {
    color: Theme.colors.textMuted,
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.emphasis,
    lineHeight: 17,
  },
  disabled: {
    opacity: 0.55,
  },
  pressed: {
    opacity: 0.78,
  },
  switchControl: {
    minHeight: Theme.accessibility.minimumTouchTarget,
    minWidth: Theme.accessibility.minimumTouchTarget,
  },
  row: {
    alignItems: 'center',
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    flexDirection: 'row',
    gap: Spacing.two,
    minHeight: 64,
    paddingHorizontal: Spacing.twoAndHalf,
    paddingVertical: Spacing.two,
  },
  title: {
    color: Theme.colors.text,
    flexShrink: 1,
    fontSize: Typography.body.fontSize,
    fontWeight: Typography.weights.strong,
  },
  titleRow: {
    alignItems: 'center',
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  value: {
    color: Theme.colors.textMuted,
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.strong,
    maxWidth: 112,
  },
  valueRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.one,
  },
});
