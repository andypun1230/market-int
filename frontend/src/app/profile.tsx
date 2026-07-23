import { StyleSheet, Text, TextInput, View } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { AppScreen } from '@/components/ui/AppScreen';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Spacing, Theme, Typography } from '@/constants/theme';
import { useAppPreferences, type LocalProfilePreferences } from '@/features/preferences/appPreferences';

export default function ProfileScreen() {
  const { preferences, updatePreferences } = useAppPreferences();
  const profile = preferences.profile;
  const update = (patch: Partial<LocalProfilePreferences>) =>
    updatePreferences({ profile: { ...profile, ...patch } });

  return (
    <AppScreen showBackButton title="Profile" subtitle="Local display identity.">
      <View style={styles.stack}>
        <DashboardCard title="Local Profile" accentColor={Theme.colors.purple}>
          <View style={styles.stack}>
            <StatusBadge label="Guest Mode" tone="purple" />
            <Text style={styles.note}>These preferences are stored locally. Account sync will be added later.</Text>
            <View style={styles.inputBox}>
              <Text style={styles.inputLabel}>Display Name</Text>
              <TextInput
                accessibilityLabel="Display name"
                onChangeText={(displayName) => update({ displayName })}
                placeholder="Display name"
                placeholderTextColor={Theme.colors.textMuted}
                style={styles.input}
                value={profile.displayName}
              />
            </View>
          </View>
        </DashboardCard>
      </View>
    </AppScreen>
  );
}

const styles = StyleSheet.create({
  input: {
    color: Theme.colors.text,
    fontSize: Typography.supportTitle.fontSize,
    fontWeight: Typography.weights.strong,
    minHeight: 44,
  },
  inputBox: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    paddingHorizontal: Spacing.twoAndHalf,
    paddingVertical: Spacing.two,
  },
  inputLabel: {
    color: Theme.colors.textMuted,
    fontSize: Typography.caption.fontSize,
    fontWeight: Typography.weights.strong,
    textTransform: 'uppercase',
  },
  note: {
    color: Theme.colors.textMuted,
    fontSize: Typography.control.fontSize,
    lineHeight: 19,
  },
  stack: {
    gap: Spacing.two,
  },
});
