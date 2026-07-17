import { StyleSheet, Text, View } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { AppScreen } from '@/components/ui/AppScreen';
import { SettingsRow } from '@/components/ui/SettingsRow';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Spacing, Theme } from '@/constants/theme';
import { useAppPreferences, type LanguagePreferences } from '@/features/preferences/appPreferences';

export default function LanguageRegionScreen() {
  const { preferences, updatePreferences } = useAppPreferences();
  const language = preferences.language;
  const update = (patch: Partial<LanguagePreferences>) =>
    updatePreferences({ language: { ...language, ...patch } });

  return (
    <AppScreen showBackButton title="Language & Region" subtitle="Display language, region, time, and formatting.">
      <View style={styles.stack}>
        <DashboardCard title="Language" accentColor={Theme.colors.accent}>
          <SettingsRow
            badge={<StatusBadge label="Active" showDot={false} tone="info" />}
            description="English is currently supported across the app."
            title="English"
          />
          <Text style={styles.note}>Traditional Chinese support is planned after the main screens are localized.</Text>
        </DashboardCard>

        <DashboardCard title="Region" accentColor={Theme.colors.accent}>
          <View style={styles.stack}>
            <SettingsRow
              badge={language.region === 'HK' ? <StatusBadge label="Selected" showDot={false} tone="info" /> : undefined}
              onPress={() => update({ region: 'HK' })}
              title="Hong Kong"
            />
            <SettingsRow
              badge={language.region === 'US' ? <StatusBadge label="Selected" showDot={false} tone="info" /> : undefined}
              onPress={() => update({ region: 'US' })}
              title="United States"
            />
          </View>
        </DashboardCard>

        <DashboardCard title="Market Time Display" accentColor={Theme.colors.purple}>
          <View style={styles.stack}>
            <SettingsRow
              badge={language.marketTimeDisplay === 'local' ? <StatusBadge label="Selected" showDot={false} tone="info" /> : undefined}
              onPress={() => update({ marketTimeDisplay: 'local' })}
              title="Local Time"
            />
            <SettingsRow
              badge={language.marketTimeDisplay === 'et' ? <StatusBadge label="Selected" showDot={false} tone="info" /> : undefined}
              onPress={() => update({ marketTimeDisplay: 'et' })}
              title="US Eastern Time"
            />
          </View>
        </DashboardCard>

        <DashboardCard title="Number & Currency" accentColor={Theme.colors.warning}>
          <View style={styles.stack}>
            <SettingsRow title="Number Format" value="1,234.56" />
            <SettingsRow
              description="Market prices remain in source currency unless conversion data is available."
              title="Currency"
              value={language.currency}
            />
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
    lineHeight: 19,
    marginTop: Spacing.two,
  },
  stack: {
    gap: Spacing.two,
  },
});
