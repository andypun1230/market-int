import { useRouter } from 'expo-router';
import { StyleSheet, View } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { AppScreen } from '@/components/ui/AppScreen';
import { SettingsRow } from '@/components/ui/SettingsRow';
import { StatusBadge, type Tone } from '@/components/ui/StatusBadge';
import { Spacing, Theme } from '@/constants/theme';
import { useAppPreferences } from '@/features/preferences/appPreferences';

type RoutePath =
  | '/about'
  | '/ai'
  | '/appearance'
  | '/data-sources'
  | '/data-usage'
  | '/disclaimer'
  | '/language-region'
  | '/notifications'
  | '/privacy'
  | '/profile'
  | '/report'
  | '/settings';

type MoreRow = {
  badge?: { label: string; tone: Tone };
  description: string;
  href: RoutePath;
  title: string;
  value?: string;
};

const TOOLS: MoreRow[] = [
  {
    description: 'Ask about today’s market, reports, sectors, risks, watchlist, and stocks.',
    href: '/ai',
    title: 'Market Copilot',
    value: 'Open',
  },
  {
    badge: { label: 'Saved', tone: 'muted' },
    description: 'Notification delivery availability and connection status.',
    href: '/notifications',
    title: 'Notifications',
  },
  {
    description: 'Local display identity used by this device.',
    href: '/profile',
    title: 'Profile',
    value: 'Local',
  },
];

const PREFERENCES: MoreRow[] = [
  { description: 'Theme and reduced-motion settings.', href: '/appearance', title: 'Appearance', value: 'Dark' },
  { description: 'Currently supported display language.', href: '/language-region', title: 'Language', value: 'English' },
  { description: 'Operational market-data cache controls.', href: '/data-usage', title: 'Data Usage', value: 'Cache' },
  { description: 'All settings and diagnostics in one place.', href: '/settings', title: 'Settings', value: 'Manage' },
];

const ABOUT: MoreRow[] = [
  { description: 'Current data mode, provider status, and calculation limits.', href: '/data-sources', title: 'Data Sources', value: 'Providers' },
  { description: 'Important educational-use and market-data limitations.', href: '/disclaimer', title: 'Financial Disclaimer' },
  { description: 'Local preferences, watchlist storage, Market Copilot, and downloads.', href: '/privacy', title: 'Privacy' },
  { description: 'Version, build, environment, and backend status.', href: '/about', title: 'About', value: '1.0.0' },
];

const COMING_NEXT = [
  { status: 'In Development', title: 'Live market data', tone: 'info' as Tone },
  { status: 'Planned', title: 'Push alerts', tone: 'muted' as Tone },
  { status: 'Planned', title: 'User accounts', tone: 'muted' as Tone },
  { status: 'Later', title: 'Premium subscription', tone: 'purple' as Tone },
];

export default function MoreScreen() {
  const router = useRouter();
  const { preferences } = useAppPreferences();
  const tools = TOOLS.map((item) => item.href === '/profile'
    ? { ...item, value: preferences.profile.displayName.trim() || 'Guest User' }
    : item);

  return (
    <AppScreen title="More" subtitle="Secondary tools and account controls.">
      <View style={styles.stack}>
        <DashboardCard title="Reports" accentColor={Theme.colors.accent}>
          <SettingsRow
            description="View, refresh, download, and share today’s market report."
            onPress={() => router.push('/report')}
            title="Daily Market Intelligence"
            value="Open"
          />
        </DashboardCard>

        <UtilitySection items={tools} title="Tools" />
        <UtilitySection items={PREFERENCES} title="Preferences" />
        <UtilitySection items={ABOUT} title="About & Legal" />

        <DashboardCard title="Coming Next" accentColor={Theme.colors.purple}>
          <View style={styles.rowStack}>
            {COMING_NEXT.map((item) => (
              <SettingsRow
                badge={<StatusBadge label={item.status} showDot={false} tone={item.tone} />}
                description="Prepared for a future release."
                disabled
                key={item.title}
                title={item.title}
              />
            ))}
          </View>
        </DashboardCard>
      </View>
    </AppScreen>
  );
}

function UtilitySection({ items, title }: { items: MoreRow[]; title: string }) {
  const router = useRouter();
  return (
    <DashboardCard title={title} accentColor={Theme.colors.accent}>
      <View style={styles.rowStack}>
        {items.map((item) => (
          <SettingsRow
            badge={item.badge ? <StatusBadge label={item.badge.label} showDot={false} tone={item.badge.tone} /> : undefined}
            description={item.description}
            key={item.title}
            onPress={() => router.push(item.href)}
            title={item.title}
            value={item.value}
          />
        ))}
      </View>
    </DashboardCard>
  );
}

const styles = StyleSheet.create({
  rowStack: {
    gap: Spacing.two,
  },
  stack: {
    gap: Spacing.three,
  },
});
