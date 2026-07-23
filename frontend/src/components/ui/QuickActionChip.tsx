import type { ReactNode } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { getToneColors, type Tone } from '@/components/ui/StatusBadge';
import { Spacing, Theme, Typography } from '@/constants/theme';

type QuickActionChipProps = {
  icon?: ReactNode;
  label: string;
  onPress?: () => void;
  tone?: Tone;
};

export function QuickActionChip({
  icon,
  label,
  onPress,
  tone = 'muted',
}: QuickActionChipProps) {
  const colors = getToneColors(tone);
  const content = (
    <>
      {icon ? <View style={styles.icon}>{icon}</View> : null}
      <Text numberOfLines={1} style={[styles.label, { color: colors.text }]}>{label}</Text>
    </>
  );

  if (onPress) {
    return (
      <Pressable
        accessibilityRole="button"
        hitSlop={6}
        onPress={onPress}
        style={({ pressed }) => [
          styles.chip,
          { backgroundColor: colors.background, borderColor: colors.border },
          pressed && styles.pressed,
        ]}>
        {content}
      </Pressable>
    );
  }

  return (
    <View style={[styles.chip, { backgroundColor: colors.background, borderColor: colors.border }]}>
      {content}
    </View>
  );
}

const styles = StyleSheet.create({
  chip: {
    alignItems: 'center',
    alignSelf: 'flex-start',
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    flexDirection: 'row',
    gap: Spacing.one,
    minHeight: 44,
    paddingHorizontal: Spacing.twoAndHalf,
    paddingVertical: Spacing.two,
  },
  pressed: {
    opacity: 0.78,
  },
  icon: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  label: {
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.strong,
  },
});
