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
              badge={<StatusBadge label="Selected" showDot={false} tone="info" />}
              description="Current beta theme."
              title="Dark"
            />
            <SettingsRow
              badge={<StatusBadge label="Not available in beta" showDot={false} tone="muted" />}
              description="System theme requires complete light-mode support."
              disabled
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
