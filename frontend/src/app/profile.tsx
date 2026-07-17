import { StyleSheet, Text, TextInput, View } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { AppScreen } from '@/components/ui/AppScreen';
import { SettingsRow } from '@/components/ui/SettingsRow';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Spacing, Theme } from '@/constants/theme';
import { useAppPreferences, type LocalProfilePreferences } from '@/features/preferences/appPreferences';

const INVESTOR_STYLES: LocalProfilePreferences['investorStyle'][] = ['Conservative', 'Balanced', 'Aggressive'];
const EXPERIENCE_LEVELS: LocalProfilePreferences['experienceLevel'][] = ['Beginner', 'Intermediate', 'Advanced'];
const REPORT_FOCUS: LocalProfilePreferences['preferredReportFocus'][] = ['Market Overview', 'Watchlist', 'Risk', 'Sectors'];

export default function ProfileScreen() {
  const { preferences, updatePreferences } = useAppPreferences();
  const profile = preferences.profile;
  const update = (patch: Partial<LocalProfilePreferences>) =>
    updatePreferences({ profile: { ...profile, ...patch } });

  return (
    <AppScreen showBackButton title="Profile" subtitle="Local-only profile and market preferences.">
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
            <SettingsRow title="Default Market" value={profile.defaultMarket} />
            <SettingsRow title="Preferred Watchlist" value={profile.preferredWatchlist} />
          </View>
        </DashboardCard>

        <ChoiceCard
          current={profile.investorStyle}
          options={INVESTOR_STYLES}
          onSelect={(investorStyle) => update({ investorStyle })}
          title="Investor Style"
        />
        <ChoiceCard
          current={profile.experienceLevel}
          options={EXPERIENCE_LEVELS}
          onSelect={(experienceLevel) => update({ experienceLevel })}
          title="Experience Level"
        />
        <ChoiceCard
          current={profile.preferredReportFocus}
          options={REPORT_FOCUS}
          onSelect={(preferredReportFocus) => update({ preferredReportFocus })}
          title="Preferred Report Focus"
        />

        <DashboardCard title="Account Actions" accentColor={Theme.colors.warning}>
          <View style={styles.stack}>
            <SettingsRow disabled title="Sign In" value="Planned" />
            <SettingsRow disabled title="Manage Subscription" value="Later" />
          </View>
        </DashboardCard>
      </View>
    </AppScreen>
  );
}

function ChoiceCard<T extends string>({
  current,
  onSelect,
  options,
  title,
}: {
  current: T;
  onSelect: (value: T) => void;
  options: T[];
  title: string;
}) {
  return (
    <DashboardCard title={title} accentColor={Theme.colors.accent}>
      <View style={styles.stack}>
        {options.map((option) => (
          <SettingsRow
            badge={current === option ? <StatusBadge label="Selected" showDot={false} tone="info" /> : undefined}
            key={option}
            onPress={() => onSelect(option)}
            title={option}
          />
        ))}
      </View>
    </DashboardCard>
  );
}

const styles = StyleSheet.create({
  input: {
    color: Theme.colors.text,
    fontSize: 16,
    fontWeight: '800',
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
    fontSize: 11,
    fontWeight: '900',
    textTransform: 'uppercase',
  },
  note: {
    color: Theme.colors.textMuted,
    fontSize: 13,
    lineHeight: 19,
  },
  stack: {
    gap: Spacing.two,
  },
});
