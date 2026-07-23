import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Spacing, Theme, Typography } from '@/constants/theme';

export type PresentedAlert = {
  id: string;
  message: string;
  metadata?: string | null;
  onPress?: () => void;
  title: string;
};

export function AlertList({ alerts, emptyMessage }: { alerts: PresentedAlert[]; emptyMessage: string }) {
  if (!alerts.length) {
    return <Text style={styles.empty}>{emptyMessage}</Text>;
  }
  return (
    <View>
      {alerts.map((alert) => (
        <Pressable
          accessibilityRole={alert.onPress ? 'button' : undefined}
          disabled={!alert.onPress}
          key={alert.id}
          onPress={alert.onPress}
          style={({ pressed }) => [styles.alert, pressed && styles.pressed]}>
          <Text style={styles.title}>{alert.title}</Text>
          <Text style={styles.message}>{alert.message}</Text>
          {alert.metadata ? <Text style={styles.metadata}>{alert.metadata}</Text> : null}
        </Pressable>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  alert: {
    borderTopColor: Theme.colors.border,
    borderTopWidth: 1,
    gap: Spacing.half,
    paddingVertical: Spacing.two,
  },
  empty: { color: Theme.colors.textMuted, fontSize: Typography.control.fontSize, fontWeight: Typography.weights.emphasis },
  message: { color: Theme.colors.textMuted, fontSize: Typography.control.fontSize, fontWeight: Typography.weights.emphasis },
  metadata: { color: Theme.colors.textMuted, fontSize: Typography.caption.fontSize, fontWeight: Typography.weights.emphasis },
  pressed: { opacity: 0.76 },
  title: { color: Theme.colors.text, fontSize: Typography.body.fontSize, fontWeight: Typography.weights.strong },
});
