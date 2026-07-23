import { StyleSheet, View } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { AppScreen } from '@/components/ui/AppScreen';
import { SettingsRow } from '@/components/ui/SettingsRow';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Spacing, Theme } from '@/constants/theme';
import { useAppPreferences, type AppearancePreferences } from '@/features/preferences/appPreferences';

export default function AppearanceScreen() {
  const { preferences, updatePreferences } = useAppPreferences();
  const appearance = preferences.appearance;
  const update = (patch: Partial<AppearancePreferences>) =>
    updatePreferences({ appearance: { ...appearance, ...patch } });

  return (
    <AppScreen showBackButton title="Appearance" subtitle="Theme and motion preferences applied across the app.">
      <View style={styles.stack}>
        <DashboardCard title="Theme" accentColor={Theme.colors.accent}>
          <View style={styles.stack}>
            <SettingsRow
              badge={appearance.theme === 'dark' ? <StatusBadge label="Selected" showDot={false} tone="info" /> : undefined}
              description="Current dark premium theme."
              onPress={() => update({ theme: 'dark' })}
              title="Dark"
            />
            <SettingsRow
              badge={appearance.theme === 'system' ? <StatusBadge label="Selected" showDot={false} tone="info" /> : undefined}
              description="Follow system theme where supported. Light mode is not enabled yet."
              onPress={() => update({ theme: 'system' })}
              title="System"
            />
          </View>
        </DashboardCard>

        <DashboardCard title="Motion" accentColor={Theme.colors.purple}>
          <SettingsRow
            description="Reduce decorative transitions where supported."
            onValueChange={(reduceMotion) => update({ reduceMotion })}
            switchValue={appearance.reduceMotion}
            title="Reduce Motion"
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
