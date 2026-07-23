import { StyleSheet, View } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { AppScreen } from '@/components/ui/AppScreen';
import { SettingsRow } from '@/components/ui/SettingsRow';
import { Spacing, Theme } from '@/constants/theme';
import { useAppPreferences } from '@/features/preferences/appPreferences';

export default function AccessibilityScreen() {
  const { preferences, updatePreferences } = useAppPreferences();
  const appearance = preferences.appearance;
  return (
    <AppScreen showBackButton title="Accessibility" subtitle="Readable display preferences.">
      <DashboardCard title="Display" accentColor={Theme.colors.accent}>
        <View style={styles.stack}>
          <SettingsRow
            description="Reduce decorative transitions where supported."
            onValueChange={(reduceMotion) => updatePreferences({ appearance: { ...appearance, reduceMotion } })}
            switchValue={appearance.reduceMotion}
            title="Reduce Motion"
          />
          <SettingsRow
            description="Badges and labels use text, not color alone, for market status."
            title="Color Meaning"
            value="Text labels"
          />
        </View>
      </DashboardCard>
    </AppScreen>
  );
}

const styles = StyleSheet.create({
  stack: {
    gap: Spacing.two,
  },
});
