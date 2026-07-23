import { StyleSheet, Text, View } from 'react-native';

import { CARD_SURFACE } from '@/components/cards/DashboardCard';
import { STATE_PRESENTATION_REGISTRY } from '@/architecture/statePresentationRegistry';
import { AppButton } from '@/components/ui/AppButton';
import { Spacing, Theme, Typography } from '@/constants/theme';

type ErrorStateProps = {
  message: string;
  onRetry?: () => void;
  retryLabel?: string;
  title?: string;
};

export function ErrorState({
  message,
  onRetry,
  retryLabel = 'Retry',
  title = 'Something went wrong',
}: ErrorStateProps) {
  const presentation = STATE_PRESENTATION_REGISTRY.failed;
  return (
    <View style={styles.container}>
      <View style={styles.accentRow}>
        <View style={styles.accentDot} />
        <Text accessibilityLabel={`${presentation.accessibilityPrefix}: ${title}`} accessibilityRole="header" style={styles.title}>{title}</Text>
      </View>
      <Text style={styles.message}>{message}</Text>
      {onRetry ? (
        <AppButton label={retryLabel} onPress={onRetry} style={styles.retryButton} variant="danger" />
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    ...CARD_SURFACE,
    borderColor: 'rgba(239, 68, 68, 0.58)',
    gap: Spacing.two,
    padding: Spacing.three,
  },
  accentRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
  },
  accentDot: {
    backgroundColor: Theme.colors.danger,
    borderRadius: 5,
    height: 10,
    width: 10,
  },
  title: {
    color: Theme.colors.danger,
    fontSize: Typography.supportTitle.fontSize,
    fontWeight: Typography.weights.strong,
  },
  message: {
    color: Theme.colors.textMuted,
    fontSize: Typography.body.fontSize,
    lineHeight: 20,
  },
  retryButton: {
    marginTop: Spacing.two,
  },
});
