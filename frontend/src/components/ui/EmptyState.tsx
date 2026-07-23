import { StyleSheet, Text, View } from 'react-native';

import { CARD_SURFACE } from '@/components/cards/DashboardCard';
import { STATE_PRESENTATION_REGISTRY, type StatePresentationType } from '@/architecture/statePresentationRegistry';
import { AppButton } from '@/components/ui/AppButton';
import { AppIcon } from '@/components/ui/AppIcon';
import { Spacing, Theme, Typography } from '@/constants/theme';

type EmptyStateProps = {
  actionLabel?: string;
  message?: string;
  onAction?: () => void;
  stateType?: StatePresentationType;
  title: string;
};

export function EmptyState({ actionLabel, message, onAction, stateType = 'empty', title }: EmptyStateProps) {
  const presentation = STATE_PRESENTATION_REGISTRY[stateType];
  const iconColor = presentation.tone === 'danger'
    ? Theme.colors.danger
    : presentation.tone === 'warning'
      ? Theme.colors.warning
      : presentation.tone === 'accent'
        ? Theme.colors.accent
        : Theme.colors.textMuted;
  return (
    <View style={styles.container}>
      <View accessibilityElementsHidden importantForAccessibility="no-hide-descendants" style={styles.iconCircle}>
        <AppIcon color={iconColor} name={presentation.icon} size={18} />
      </View>
      <Text accessibilityLabel={`${presentation.accessibilityPrefix}: ${title}`} accessibilityRole="header" style={styles.title}>{title}</Text>
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
