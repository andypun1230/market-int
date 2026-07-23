import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Spacing, Theme } from '@/constants/theme';

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
  empty: { color: Theme.colors.textMuted, fontSize: 13, fontWeight: '700' },
  message: { color: Theme.colors.textMuted, fontSize: 13, fontWeight: '700' },
  metadata: { color: Theme.colors.textMuted, fontSize: 11, fontWeight: '700' },
  pressed: { opacity: 0.76 },
  title: { color: Theme.colors.text, fontSize: 14, fontWeight: '900' },
});
