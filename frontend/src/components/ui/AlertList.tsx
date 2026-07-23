import { StyleSheet, Text, View } from 'react-native';

import { Spacing, Theme } from '@/constants/theme';

export type PresentedAlert = {
  id: string;
  message: string;
  metadata?: string | null;
  title: string;
};

export function AlertList({ alerts, emptyMessage }: { alerts: PresentedAlert[]; emptyMessage: string }) {
  if (!alerts.length) {
    return <Text style={styles.empty}>{emptyMessage}</Text>;
  }
  return (
    <View>
      {alerts.map((alert) => (
        <View key={alert.id} style={styles.alert}>
          <Text style={styles.title}>{alert.title}</Text>
          <Text style={styles.message}>{alert.message}</Text>
          {alert.metadata ? <Text style={styles.metadata}>{alert.metadata}</Text> : null}
        </View>
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
  title: { color: Theme.colors.text, fontSize: 14, fontWeight: '900' },
});
