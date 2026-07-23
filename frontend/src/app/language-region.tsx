import { StyleSheet, View } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { AppScreen } from '@/components/ui/AppScreen';
import { SettingsRow } from '@/components/ui/SettingsRow';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Spacing, Theme } from '@/constants/theme';
export default function LanguageRegionScreen() {
  return (
    <AppScreen showBackButton title="Language & Region" subtitle="Supported display locale.">
      <View style={styles.stack}>
        <DashboardCard title="Language" accentColor={Theme.colors.accent}>
          <SettingsRow
            badge={<StatusBadge label="Active" showDot={false} tone="info" />}
            description="English is currently supported across the app."
            title="English"
          />
          <SettingsRow
            badge={<StatusBadge label="Not available in beta" showDot={false} tone="muted" />}
            description="This language will remain unavailable until the application is fully translated."
            disabled
            title="Traditional Chinese"
          />
        </DashboardCard>

      </View>
    </AppScreen>
  );
}

const styles = StyleSheet.create({
  stack: {
    gap: Spacing.two,
  },
});
