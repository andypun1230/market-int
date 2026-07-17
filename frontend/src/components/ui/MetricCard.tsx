import { Pressable, StyleSheet, Text, View } from 'react-native';

import { getToneColors, type Tone } from '@/components/ui/StatusBadge';
import { Spacing, Theme } from '@/constants/theme';

type MetricCardProps = {
  change?: string;
  onPress?: () => void;
  subtitle?: string;
  title: string;
  tone?: Tone;
  value: string | number;
};

export function MetricCard({
  change,
  onPress,
  subtitle,
  title,
  tone = 'muted',
  value,
}: MetricCardProps) {
  const colors = getToneColors(tone);
  const content = (
    <>
      <View style={styles.header}>
        <Text numberOfLines={1} style={styles.title}>{title}</Text>
        {change ? <Text style={[styles.change, { color: colors.text }]}>{change}</Text> : null}
      </View>
      <Text numberOfLines={1} style={[styles.value, { color: colors.text }]}>{value}</Text>
      {subtitle ? <Text numberOfLines={2} style={styles.subtitle}>{subtitle}</Text> : null}
    </>
  );

  if (onPress) {
    return (
      <Pressable
        accessibilityRole="button"
        onPress={onPress}
        style={({ pressed }) => [
          styles.card,
          { borderColor: colors.border },
          pressed && styles.pressed,
        ]}>
        {content}
      </Pressable>
    );
  }

  return <View style={[styles.card, { borderColor: colors.border }]}>{content}</View>;
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: Theme.colors.card,
    borderRadius: Theme.radii.card,
    borderWidth: 1,
    gap: Spacing.two,
    minHeight: 128,
    padding: Spacing.three,
    width: 168,
  },
  pressed: {
    opacity: 0.82,
  },
  header: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  title: {
    color: Theme.colors.text,
    flex: 1,
    fontSize: 13,
    fontWeight: '900',
  },
  change: {
    fontSize: 12,
    fontWeight: '900',
  },
  value: {
    fontSize: 25,
    fontWeight: '900',
  },
  subtitle: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '700',
    lineHeight: 17,
  },
});
