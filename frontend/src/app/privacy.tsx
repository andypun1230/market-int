import { StyleSheet, Text, View } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { AppScreen } from '@/components/ui/AppScreen';
import { Spacing, Theme, Typography } from '@/constants/theme';

const PRIVACY_ITEMS = [
  {
    body: 'Reduced-motion and local profile preferences are stored on this device. Unavailable notification, language, and system-theme options do not save preferences.',
    title: 'Local Preferences',
  },
  {
    body: 'Saved stocks, sectors, and themes are stored locally by the app. Removing items from the watchlist removes them from local watchlist state.',
    title: 'Watchlist Storage',
  },
  {
    body: 'Market Copilot questions and compact app context are sent to the configured backend AI service when you use Copilot. Do not enter sensitive personal information.',
    title: 'Market Copilot Content',
  },
  {
    body: 'Downloaded reports are saved to app cache or shared through the native share sheet. Files shared outside the app are controlled by the destination app.',
    title: 'Report Downloads',
  },
  {
    body: 'A full privacy policy will be published before account and subscription features are released.',
    title: 'Future Accounts',
  },
];

export default function PrivacyScreen() {
  return (
    <AppScreen showBackButton title="Privacy" subtitle="Current local data and future account notes.">
      <View style={styles.stack}>
        {PRIVACY_ITEMS.map((item) => (
          <DashboardCard key={item.title} title={item.title} accentColor={Theme.colors.accent}>
            <Text style={styles.body}>{item.body}</Text>
          </DashboardCard>
        ))}
      </View>
    </AppScreen>
  );
}

const styles = StyleSheet.create({
  body: {
    color: Theme.colors.textMuted,
    fontSize: Typography.body.fontSize,
    lineHeight: 22,
  },
  stack: {
    gap: Spacing.two,
  },
});
