import { StyleSheet, Text, View } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { AppScreen } from '@/components/ui/AppScreen';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Spacing, Theme } from '@/constants/theme';
export default function NotificationsScreen() {
  return (
    <AppScreen showBackButton title="Notifications" subtitle="Notification delivery status.">
      <View style={styles.stack}>
        <DashboardCard title="Notification Status" accentColor={Theme.colors.warning}>
          <View style={styles.statusStack}>
            <StatusBadge label="Not Available" tone="warning" />
            <Text style={styles.note}>Push delivery is not connected. Notification controls will appear only when a delivery service can consume them.</Text>
          </View>
        </DashboardCard>
      </View>
    </AppScreen>
  );
}

const styles = StyleSheet.create({
  note: {
    color: Theme.colors.textMuted,
    fontSize: 13,
    lineHeight: 20,
  },
  stack: {
    gap: Spacing.two,
  },
  statusStack: {
    gap: Spacing.two,
  },
});
