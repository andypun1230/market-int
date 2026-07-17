import type { DimensionValue } from 'react-native';
import { StyleSheet, Text, View } from 'react-native';

import { Spacing, Theme } from '@/constants/theme';
import { getToneColors, type Tone } from '@/components/ui/StatusBadge';

type ProgressBarProps = {
  label?: string;
  showValue?: boolean;
  tone?: Tone;
  value: number;
};

export function ProgressBar({ label, showValue = true, tone = 'info', value }: ProgressBarProps) {
  const clamped = Math.max(0, Math.min(100, Number.isFinite(value) ? value : 0));
  const colors = getToneColors(tone);
  const width = `${Math.round(clamped)}%` as DimensionValue;

  return (
    <View style={styles.container}>
      {label || showValue ? (
        <View style={styles.header}>
          {label ? <Text numberOfLines={1} style={styles.label}>{label}</Text> : <View />}
          {showValue ? <Text style={styles.value}>{Math.round(clamped)}%</Text> : null}
        </View>
      ) : null}
      <View style={styles.track}>
        <View style={[styles.fill, { backgroundColor: colors.text, width }]} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: Spacing.one,
    width: '100%',
  },
  header: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  label: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '900',
    flex: 1,
    textTransform: 'uppercase',
  },
  value: {
    color: Theme.colors.text,
    fontSize: 12,
    fontWeight: '900',
  },
  track: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderRadius: Theme.radii.pill,
    height: 8,
    overflow: 'hidden',
  },
  fill: {
    borderRadius: Theme.radii.pill,
    height: 8,
  },
});
