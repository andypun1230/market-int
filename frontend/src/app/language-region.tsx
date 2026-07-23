import { StyleSheet, Text, View } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { AppScreen } from '@/components/ui/AppScreen';
import { SettingsRow } from '@/components/ui/SettingsRow';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Spacing, Theme, Typography } from '@/constants/theme';
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
          <Text style={styles.note}>Traditional Chinese support is planned after the main screens are localized.</Text>
        </DashboardCard>

      </View>
    </AppScreen>
  );
}

const styles = StyleSheet.create({
  note: {
    color: Theme.colors.textMuted,
    fontSize: Typography.control.fontSize,
    lineHeight: 19,
    marginTop: Spacing.two,
  },
  stack: {
    gap: Spacing.two,
  },
});
