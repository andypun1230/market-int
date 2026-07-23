import { Pressable, StyleSheet, Text, View } from 'react-native';

import { ScoreGauge } from '@/components/ui/ScoreGauge';
import { SignalDots } from '@/components/ui/SignalDots';
import { StatusBadge, type Tone } from '@/components/ui/StatusBadge';
import { Spacing, Theme, Typography } from '@/constants/theme';

type DecisionTag = string;

type DecisionCardProps = {
  decision: string;
  onPress?: () => void;
  risk?: string;
  score?: number | null;
  signals?: { label: string; tone: Tone }[];
  status?: string;
  subtitle?: string;
  tags?: DecisionTag[];
  title: string;
};

export function DecisionCard({
  decision,
  onPress,
  risk,
  score,
  signals,
  status,
  subtitle,
  tags,
  title,
}: DecisionCardProps) {
  const content = (
    <>
      <View style={styles.header}>
        <View style={styles.copy}>
          <Text numberOfLines={1} style={styles.title}>{title}</Text>
          {subtitle ? <Text numberOfLines={1} style={styles.subtitle}>{subtitle}</Text> : null}
        </View>
        <ScoreGauge value={score} size="small" />
      </View>

      <Text numberOfLines={2} style={styles.decision}>{decision}</Text>

      <View style={styles.metaRow}>
        {status ? <StatusBadge label={status} tone={getStatusTone(status)} /> : null}
        {risk ? <StatusBadge label={risk} tone={getRiskTone(risk)} /> : null}
      </View>

      {signals?.length ? <SignalDots signals={signals} showLabels /> : null}

      {tags?.length ? (
        <View style={styles.tags}>
          {tags.slice(0, 3).map((tag) => (
            <Text key={tag} numberOfLines={1} style={styles.tag}>{tag}</Text>
          ))}
        </View>
      ) : null}
    </>
  );

  if (onPress) {
    return (
      <Pressable
        accessibilityRole="button"
        onPress={onPress}
        style={({ pressed }) => [styles.card, pressed && styles.pressed]}>
        {content}
      </Pressable>
    );
  }

  return <View style={styles.card}>{content}</View>;
}

function getRiskTone(risk: string): Tone {
  switch (risk.toLowerCase()) {
    case 'low':
      return 'success';
    case 'moderate':
      return 'info';
    case 'elevated':
      return 'warning';
    case 'high':
      return 'danger';
    default:
      return 'muted';
  }
}

function getStatusTone(status: string): Tone {
  const normalized = status.toLowerCase();
  if (normalized.includes('leading') || normalized.includes('strong') || normalized.includes('candidate')) {
    return 'success';
  }
  if (normalized.includes('weak') || normalized.includes('avoid')) {
    return 'danger';
  }
  if (normalized.includes('risk') || normalized.includes('watch')) {
    return 'warning';
  }
  return 'info';
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: Theme.colors.card,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.card,
    borderWidth: 1,
    gap: Spacing.two,
    minHeight: 172,
    padding: Spacing.three,
    width: 220,
  },
  pressed: {
    opacity: 0.82,
  },
  header: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  copy: {
    flex: 1,
    gap: Spacing.half,
  },
  title: {
    color: Theme.colors.text,
    fontSize: Typography.sectionTitle.fontSize,
    fontWeight: Typography.weights.strong,
  },
  subtitle: {
    color: Theme.colors.textMuted,
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.strong,
  },
  decision: {
    color: Theme.colors.text,
    fontSize: Typography.body.fontSize,
    fontWeight: Typography.weights.strong,
    lineHeight: 20,
  },
  metaRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.one,
  },
  tags: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.one,
  },
  tag: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    color: Theme.colors.textMuted,
    fontSize: Typography.caption.fontSize,
    fontWeight: Typography.weights.strong,
    maxWidth: '100%',
    paddingHorizontal: Spacing.two,
    paddingVertical: Spacing.one,
  },
});
