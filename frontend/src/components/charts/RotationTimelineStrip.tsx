import { StyleSheet, Text, View } from 'react-native';

import { StatusBadge, type Tone } from '@/components/ui/StatusBadge';
import { Spacing, Theme } from '@/constants/theme';
import { classifyQuadrant, formatQuadrant, type RotationPoint } from '@/data/sectorTabTestData';

export function RotationTimelineStrip({ history }: { history: RotationPoint[] }) {
  const checkpoints = pickCheckpoints(history);

  if (!checkpoints.length) {
    return <Text style={styles.empty}>No rotation timeline available.</Text>;
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Rotation Timeline</Text>
      <View style={styles.timeline}>
        {checkpoints.map((point, index) => {
          const quadrant = classifyQuadrant(point.relativeStrength, point.relativeMomentum);
          return (
            <View key={`${point.dateLabel}-${index}`} style={styles.checkpoint}>
              <Text style={styles.date}>{point.dateLabel}</Text>
              <StatusBadge label={formatQuadrant(quadrant)} tone={getQuadrantTone(quadrant)} />
              <Text style={styles.metric}>RS {point.relativeStrength.toFixed(1)}</Text>
              <Text style={styles.metric}>Mom {point.relativeMomentum.toFixed(1)}</Text>
            </View>
          );
        })}
      </View>
    </View>
  );
}

function pickCheckpoints(history: RotationPoint[]) {
  if (history.length <= 4) {
    return history;
  }
  return [
    history[0],
    history[Math.floor(history.length * 0.35)],
    history[Math.floor(history.length * 0.7)],
    history[history.length - 1],
  ];
}

function getQuadrantTone(quadrant: ReturnType<typeof classifyQuadrant>): Tone {
  switch (quadrant) {
    case 'leading':
      return 'success';
    case 'weakening':
      return 'warning';
    case 'improving':
      return 'info';
    case 'lagging':
      return 'danger';
  }
}

const styles = StyleSheet.create({
  checkpoint: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    flexBasis: '47%',
    flexGrow: 1,
    gap: Spacing.one,
    padding: Spacing.two,
  },
  container: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    gap: Spacing.two,
    padding: Spacing.three,
  },
  date: {
    color: Theme.colors.text,
    fontSize: 12,
    fontWeight: '900',
  },
  empty: {
    color: Theme.colors.textMuted,
    fontSize: 13,
    fontWeight: '800',
  },
  metric: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '800',
  },
  timeline: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  title: {
    color: Theme.colors.text,
    fontSize: 14,
    fontWeight: '900',
  },
});
