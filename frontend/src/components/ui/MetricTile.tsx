import { StyleSheet, Text, View } from 'react-native';

import { Spacing, Theme } from '@/constants/theme';
import { getToneColors, type Tone } from '@/components/ui/StatusBadge';

type MetricTileProps = {
  label: string;
  subvalue?: string | number;
  tone?: Tone;
  value: string | number;
};

export function MetricTile({ label, subvalue, tone = 'muted', value }: MetricTileProps) {
  const colors = getToneColors(tone);

  return (
    <View style={[styles.container, tone !== 'muted' && { borderColor: colors.border }]}>
      <Text style={styles.label}>{label}</Text>
      <Text style={[styles.value, tone !== 'muted' && { color: colors.text }]}>{value}</Text>
      {subvalue !== undefined ? <Text style={styles.subvalue}>{subvalue}</Text> : null}
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
  label: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '900',
    marginBottom: Spacing.one,
    textTransform: 'uppercase',
  },
  value: {
    color: Theme.colors.text,
    fontSize: 16,
    fontWeight: '900',
    lineHeight: 22,
  },
  subvalue: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '700',
    marginTop: Spacing.one,
  },
});
