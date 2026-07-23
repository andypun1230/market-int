import { StyleSheet, Text, View } from 'react-native';

import { ProgressBar } from '@/components/ui/ProgressBar';
import { type Tone } from '@/components/ui/StatusBadge';
import { Spacing, Theme, Typography } from '@/constants/theme';

type ScoreGaugeProps = {
  label?: string;
  size?: 'small' | 'medium' | 'large';
  tone?: Tone;
  value?: number | null;
};

export function ScoreGauge({
  label = 'Score',
  size = 'medium',
  tone,
  value,
}: ScoreGaugeProps) {
  const hasValue = typeof value === 'number' && Number.isFinite(value);
  const clamped = hasValue ? Math.max(0, Math.min(100, value)) : null;
  const resolvedTone = tone ?? getScoreTone(clamped);
  const sizeStyle = getSizeStyle(size);

  return (
    <View style={[styles.container, sizeStyle.container]}>
      <Text style={styles.label}>{label}</Text>
      <Text style={[styles.value, sizeStyle.value, { color: getScoreColor(resolvedTone) }]}>
        {clamped === null ? 'N/A' : Math.round(clamped)}
      </Text>
      <ProgressBar showValue={false} tone={resolvedTone} value={clamped ?? 0} />
    </View>
  );
}

function getScoreTone(value: number | null): Tone {
  if (value === null) {
    return 'muted';
  }

  if (value >= 85) {
    return 'success';
  }

  if (value >= 70) {
    return 'info';
  }

  if (value >= 55) {
    return 'warning';
  }

  return 'danger';
}

function getScoreColor(tone: Tone) {
  switch (tone) {
    case 'success':
      return Theme.colors.success;
    case 'info':
      return Theme.colors.accent;
    case 'warning':
      return Theme.colors.warning;
    case 'danger':
      return Theme.colors.danger;
    case 'purple':
      return Theme.colors.purple;
    default:
      return Theme.colors.textMuted;
  }
}

function getSizeStyle(size: NonNullable<ScoreGaugeProps['size']>) {
  switch (size) {
    case 'small':
      return {
        container: styles.smallContainer,
        value: styles.smallValue,
      };
    case 'large':
      return {
        container: styles.largeContainer,
        value: styles.largeValue,
      };
    default:
      return {
        container: styles.mediumContainer,
        value: styles.mediumValue,
      };
  }
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    gap: Spacing.one,
    padding: Spacing.two,
  },
  smallContainer: {
    minWidth: 78,
  },
  mediumContainer: {
    minWidth: 112,
  },
  largeContainer: {
    minWidth: '47%',
    padding: Spacing.twoAndHalf,
  },
  label: {
    color: Theme.colors.textMuted,
    fontSize: Typography.chartLabel.fontSize,
    fontWeight: Typography.weights.strong,
    textTransform: 'uppercase',
  },
  value: {
    fontWeight: Typography.weights.strong,
  },
  smallValue: {
    fontSize: Typography.detailTitle.fontSize,
  },
  mediumValue: {
    fontSize: Typography.entityTitle.fontSize,
  },
  largeValue: {
    fontSize: Typography.display.fontSize,
  },
});
