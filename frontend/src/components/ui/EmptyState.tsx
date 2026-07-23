import { StyleSheet, Text, View } from 'react-native';

import { CARD_SURFACE } from '@/components/cards/DashboardCard';
import { AppButton } from '@/components/ui/AppButton';
import { Spacing, Theme, Typography } from '@/constants/theme';

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
        <AppButton label={actionLabel} onPress={onAction} style={styles.actionButton} variant="primary" />
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    ...CARD_SURFACE,
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
    fontSize: Typography.supportTitle.fontSize,
    fontWeight: Typography.weights.strong,
    textAlign: 'center',
  },
  message: {
    color: Theme.colors.textMuted,
    fontSize: Typography.control.fontSize,
    lineHeight: 19,
    textAlign: 'center',
  },
  actionButton: {
    marginTop: Spacing.one,
  },
});
