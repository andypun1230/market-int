import { Pressable, StyleSheet, Text, View } from 'react-native';

import { QuickActionChip } from '@/components/ui/QuickActionChip';
import { ScoreGauge } from '@/components/ui/ScoreGauge';
import { StatusBadge, getToneColors, type Tone } from '@/components/ui/StatusBadge';
import { Spacing, Theme } from '@/constants/theme';

type HeroDecisionCardProps = {
  actionLabel?: string;
  badges?: string[];
  headline: string;
  label?: string;
  onPress?: () => void;
  score?: number | null;
  status?: string;
  subheadline?: string;
  title: string;
  tone?: Tone;
};

export function HeroDecisionCard({
  actionLabel,
  badges,
  headline,
  label,
  onPress,
  score,
  status,
  subheadline,
  title,
  tone = 'info',
}: HeroDecisionCardProps) {
  const colors = getToneColors(tone);
  const content = (
    <>
      <View style={styles.topRow}>
        <View style={styles.titleBlock}>
          {label ? <Text style={styles.label}>{label}</Text> : null}
          <Text style={styles.title}>{title}</Text>
        </View>
        {status ? <StatusBadge label={status} tone={tone} /> : null}
      </View>

      <View style={styles.mainRow}>
        <View style={styles.copy}>
          <Text style={[styles.headline, { color: colors.text }]}>{headline}</Text>
          {subheadline ? <Text numberOfLines={3} style={styles.subheadline}>{subheadline}</Text> : null}
        </View>
        {typeof score === 'number' ? <ScoreGauge value={score} size="medium" tone={tone} /> : null}
      </View>

      {badges?.length ? (
        <View style={styles.badges}>
          {badges.slice(0, 4).map((badge) => (
            <Text key={badge} numberOfLines={1} style={styles.badge}>{badge}</Text>
          ))}
        </View>
      ) : null}

      {actionLabel ? <QuickActionChip label={actionLabel} tone={tone} /> : null}
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
    gap: Spacing.three,
    padding: Spacing.three,
  },
  pressed: {
    opacity: 0.84,
  },
  topRow: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  titleBlock: {
    flex: 1,
    gap: Spacing.half,
  },
  label: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '900',
    textTransform: 'uppercase',
  },
  title: {
    color: Theme.colors.text,
    fontSize: 15,
    fontWeight: '900',
  },
  mainRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.three,
  },
  copy: {
    flex: 1,
    gap: Spacing.two,
  },
  headline: {
    fontSize: 28,
    fontWeight: '900',
    lineHeight: 33,
  },
  subheadline: {
    color: Theme.colors.textMuted,
    fontSize: 14,
    fontWeight: '700',
    lineHeight: 21,
  },
  badges: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.one,
  },
  badge: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '800',
    maxWidth: '100%',
    paddingHorizontal: Spacing.two,
    paddingVertical: Spacing.one,
  },
});
