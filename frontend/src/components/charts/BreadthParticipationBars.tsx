import { StyleSheet, Text, View } from 'react-native';

import { ProgressBar } from '@/components/ui/ProgressBar';
import { Spacing, Theme } from '@/constants/theme';
import type { SectorBreadthSnapshot } from '@/data/sectorTabTestData';

export function BreadthParticipationBars({ breadth }: { breadth: SectorBreadthSnapshot }) {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Breadth Participation</Text>
      <ProgressBar label="Above 20 EMA" tone={getTone(breadth.percentAbove20Ema)} value={breadth.percentAbove20Ema} />
      <ProgressBar label="Above 50 EMA" tone={getTone(breadth.percentAbove50Ema)} value={breadth.percentAbove50Ema} />
      <ProgressBar label="Above 200 EMA" tone={getTone(breadth.percentAbove200Ema)} value={breadth.percentAbove200Ema} />
    </View>
  );
}

function getTone(value: number) {
  if (value >= 70) {
    return 'success';
  }
  if (value >= 50) {
    return 'info';
  }
  if (value >= 35) {
    return 'warning';
  }
  return 'danger';
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    gap: Spacing.two,
    padding: Spacing.three,
  },
  title: {
    color: Theme.colors.text,
    fontSize: 14,
    fontWeight: '900',
  },
});
