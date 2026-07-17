import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Spacing, Theme } from '@/constants/theme';

type EmptyStateProps = {
  actionLabel?: string;
  message?: string;
  onAction?: () => void;
  title: string;
};

export function EmptyState({ actionLabel, message, onAction, title }: EmptyStateProps) {
  return (
    <View style={styles.container}>
      <View style={styles.iconCircle}>
        <View style={styles.iconDot} />
      </View>
      <Text style={styles.title}>{title}</Text>
      {message ? <Text style={styles.message}>{message}</Text> : null}
      {actionLabel && onAction ? (
        <Pressable accessibilityRole="button" onPress={onAction} style={styles.actionButton}>
          <Text style={styles.actionText}>{actionLabel}</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    backgroundColor: Theme.colors.card,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.card,
    borderWidth: 1,
    gap: Spacing.two,
    padding: Spacing.four,
  },
  iconCircle: {
    alignItems: 'center',
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: 22,
    borderWidth: 1,
    height: 44,
    justifyContent: 'center',
    width: 44,
  },
  iconDot: {
    backgroundColor: Theme.colors.textMuted,
    borderRadius: 6,
    height: 12,
    opacity: 0.7,
    width: 12,
  },
  title: {
    color: Theme.colors.text,
    fontSize: 16,
    fontWeight: '900',
    textAlign: 'center',
  },
  message: {
    color: Theme.colors.textMuted,
    fontSize: 13,
    lineHeight: 19,
    textAlign: 'center',
  },
  actionButton: {
    backgroundColor: Theme.colors.accent,
    borderRadius: Theme.radii.small,
    marginTop: Spacing.one,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.two,
  },
  actionText: {
    color: Theme.colors.background,
    fontSize: 13,
    fontWeight: '900',
  },
});
