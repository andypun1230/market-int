import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Spacing, Theme } from '@/constants/theme';

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
  return (
    <View style={styles.container}>
      <View style={styles.accentRow}>
        <View style={styles.accentDot} />
        <Text style={styles.title}>{title}</Text>
      </View>
      <Text style={styles.message}>{message}</Text>
      {onRetry ? (
        <Pressable accessibilityRole="button" onPress={onRetry} style={styles.retryButton}>
          <Text style={styles.retryText}>{retryLabel}</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: Theme.colors.card,
    borderColor: 'rgba(239, 68, 68, 0.58)',
    borderRadius: Theme.radii.card,
    borderWidth: 1,
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
    fontSize: 16,
    fontWeight: '900',
  },
  message: {
    color: Theme.colors.textMuted,
    fontSize: 14,
    lineHeight: 20,
  },
  retryButton: {
    alignSelf: 'flex-start',
    backgroundColor: Theme.colors.dangerSoft,
    borderColor: Theme.colors.danger,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    marginTop: Spacing.two,
    paddingHorizontal: Spacing.twoAndHalf,
    paddingVertical: Spacing.two,
  },
  retryText: {
    color: Theme.colors.danger,
    fontSize: 13,
    fontWeight: '900',
  },
});
