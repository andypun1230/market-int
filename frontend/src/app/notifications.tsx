import { StyleSheet, Text, View } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { AppScreen } from '@/components/ui/AppScreen';
import { SettingsRow } from '@/components/ui/SettingsRow';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Spacing, Theme } from '@/constants/theme';
import { useAppPreferences, type NotificationPreferences } from '@/features/preferences/appPreferences';

const NOTIFICATION_ROWS: { description: string; key: keyof Omit<NotificationPreferences, 'notificationTime'>; title: string }[] = [
  { description: 'Save a preference for when the daily report is ready.', key: 'dailyReportReady', title: 'Daily Report Ready' },
  { description: 'Alert preference for regime shifts.', key: 'marketRegimeChanges', title: 'Market Regime Changes' },
  { description: 'Alert preference for risk dashboard changes.', key: 'riskLevelChanges', title: 'Risk Level Changes' },
  { description: 'Alert preference for saved ticker price alerts.', key: 'watchlistPriceAlerts', title: 'Watchlist Price Alerts' },
  { description: 'Alert preference when sector or theme leadership changes.', key: 'sectorLeadershipChanges', title: 'Sector Leadership Changes' },
  { description: 'Alert preference for major scheduled macro events.', key: 'majorMacroEvents', title: 'Major Macro Events' },
  { description: 'Suppress future notification delivery during quiet hours.', key: 'quietHours', title: 'Quiet Hours' },
];

export default function NotificationsScreen() {
  const { preferences, updatePreferences } = useAppPreferences();
  const notifications = preferences.notifications;
  const update = (patch: Partial<NotificationPreferences>) =>
    updatePreferences({ notifications: { ...notifications, ...patch } });

  return (
    <AppScreen showBackButton title="Notifications" subtitle="Saved alert preferences for future push delivery.">
      <View style={styles.stack}>
        <DashboardCard title="Notification Status" accentColor={Theme.colors.warning}>
          <View style={styles.statusStack}>
            <StatusBadge label="Preferences Saved" tone="warning" />
            <Text style={styles.note}>Push delivery will be enabled in a future update. Your preferences will be saved locally.</Text>
          </View>
        </DashboardCard>

        <DashboardCard title="Alert Preferences" accentColor={Theme.colors.accent}>
          <View style={styles.stack}>
            {NOTIFICATION_ROWS.map((row) => (
              <SettingsRow
                description={row.description}
                key={row.key}
                onValueChange={(value) => update({ [row.key]: value })}
                switchValue={Boolean(notifications[row.key])}
                title={row.title}
              />
            ))}
          </View>
        </DashboardCard>

        <DashboardCard title="Timing" accentColor={Theme.colors.purple}>
          <SettingsRow
            description="Preferred future notification time."
            title="Notification Time"
            value={notifications.notificationTime}
          />
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
