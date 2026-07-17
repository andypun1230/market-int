import { StyleSheet, Text, View } from 'react-native';

import { Spacing, Theme } from '@/constants/theme';

export type Tone = 'success' | 'warning' | 'danger' | 'info' | 'muted' | 'purple';

type StatusBadgeProps = {
  label: string;
  showDot?: boolean;
  tone?: Tone;
};

export function StatusBadge({ label, showDot = true, tone = 'muted' }: StatusBadgeProps) {
  const colors = getToneColors(tone);

  return (
    <View style={[styles.badge, { backgroundColor: colors.background, borderColor: colors.border }]}>
      {showDot ? <View style={[styles.dot, { backgroundColor: colors.text }]} /> : null}
      <Text numberOfLines={1} style={[styles.label, { color: colors.text }]}>{label}</Text>
    </View>
  );
}

export function getToneColors(tone: Tone) {
  switch (tone) {
    case 'success':
      return {
        background: Theme.colors.successSoft,
        border: Theme.colors.success,
        text: Theme.colors.success,
      };
    case 'warning':
      return {
        background: Theme.colors.warningSoft,
        border: Theme.colors.warning,
        text: Theme.colors.warning,
      };
    case 'danger':
      return {
        background: Theme.colors.dangerSoft,
        border: Theme.colors.danger,
        text: Theme.colors.danger,
      };
    case 'info':
      return {
        background: Theme.colors.accentSoft,
        border: Theme.colors.accent,
        text: Theme.colors.accent,
      };
    case 'purple':
      return {
        background: Theme.colors.purpleSoft,
        border: Theme.colors.purple,
        text: Theme.colors.purple,
      };
    default:
      return {
        background: Theme.colors.cardMuted,
        border: Theme.colors.border,
        text: Theme.colors.textMuted,
      };
  }
}

const styles = StyleSheet.create({
  badge: {
    alignItems: 'center',
    alignSelf: 'flex-start',
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    flexDirection: 'row',
    gap: Spacing.one,
    maxWidth: '100%',
    paddingHorizontal: Spacing.two,
    paddingVertical: 5,
  },
  dot: {
    borderRadius: 3,
    height: 6,
    width: 6,
  },
  label: {
    flexShrink: 1,
    fontSize: 11,
    fontWeight: '900',
  },
});
