import { StyleSheet, View } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { AppScreen } from '@/components/ui/AppScreen';
import { SettingsRow } from '@/components/ui/SettingsRow';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Spacing, Theme } from '@/constants/theme';
import { useAppPreferences, type AppearancePreferences } from '@/features/preferences/appPreferences';

const ACCENTS: { label: string; value: AppearancePreferences['accentColor'] }[] = [
  { label: 'Market Blue', value: 'blue' },
  { label: 'Growth Green', value: 'green' },
  { label: 'Insight Purple', value: 'purple' },
  { label: 'Alert Orange', value: 'orange' },
];

export default function AppearanceScreen() {
  const { preferences, updatePreferences } = useAppPreferences();
  const appearance = preferences.appearance;
  const update = (patch: Partial<AppearancePreferences>) =>
    updatePreferences({ appearance: { ...appearance, ...patch } });

  return (
    <AppScreen showBackButton title="Appearance" subtitle="Theme, text size, accent color, and motion.">
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

        <DashboardCard title="Text Size" accentColor={Theme.colors.accent}>
          <View style={styles.stack}>
            {(['small', 'default', 'large'] as const).map((value) => (
              <SettingsRow
                badge={appearance.textSize === value ? <StatusBadge label="Selected" showDot={false} tone="info" /> : undefined}
                key={value}
                onPress={() => update({ textSize: value })}
                title={value === 'default' ? 'Default' : value === 'small' ? 'Small' : 'Large'}
              />
            ))}
          </View>
        </DashboardCard>

        <DashboardCard title="Accent Color" accentColor={Theme.colors.accent}>
          <View style={styles.stack}>
            {ACCENTS.map((accent) => (
              <SettingsRow
                badge={appearance.accentColor === accent.value ? <StatusBadge label="Selected" showDot={false} tone="info" /> : undefined}
                description="Affects selection and branding accents, not financial green/red meaning."
                key={accent.value}
                onPress={() => update({ accentColor: accent.value })}
                title={accent.label}
              />
            ))}
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
