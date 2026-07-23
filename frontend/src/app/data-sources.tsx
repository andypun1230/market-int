import { useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { AppScreen } from '@/components/ui/AppScreen';
import { SettingsRow } from '@/components/ui/SettingsRow';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Spacing, Theme } from '@/constants/theme';
import { formatProviderName } from '@/features/more/appInfo';
import { getProviderStatus, getTestDataStatus } from '@/services/api';
import { areTestScenariosEnabled } from '@/services/runtimeConfig';
import type { ProviderStatus, TestDataStatus } from '@/types/market';
import { useUserFacingDataState } from '@/features/trust/UserFacingDataStateProvider';

export default function DataSourcesScreen() {
  const [provider, setProvider] = useState<ProviderStatus | null>(null);
  const [testData, setTestData] = useState<TestDataStatus | null>(null);
  const testScenariosEnabled = areTestScenariosEnabled();
  const { dataState } = useUserFacingDataState();

  useEffect(() => {
    let mounted = true;
    Promise.allSettled([getProviderStatus(), getTestDataStatus()]).then(([providerResult, testDataResult]) => {
      if (!mounted) {
        return;
      }
      if (providerResult.status === 'fulfilled') {
        setProvider(providerResult.value);
      }
      if (testDataResult.status === 'fulfilled') {
        setTestData(testDataResult.value);
      }
    });
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <AppScreen showBackButton title="Data Sources" subtitle="Current data mode and calculation limits.">
      <View style={styles.stack}>
        <DashboardCard title="Current Mode" accentColor={Theme.colors.accent}>
          <View style={styles.stack}>
            <StatusBadge label={dataState.headline} tone={dataState.state === 'live' ? 'success' : dataState.state === 'failed' || dataState.state === 'unavailable' ? 'danger' : 'warning'} />
            <SettingsRow title="Availability" value={dataState.availabilitySummary} description={dataState.explanation} />
            <SettingsRow title="Market-data provider" value={formatProviderName(provider?.active_provider ?? provider?.market_data_provider)} />
            <SettingsRow title="Quote provider" value={formatProviderName(provider?.configured_quote_provider ?? provider?.active_quote_provider)} />
            <SettingsRow title="History provider" value={formatProviderName(provider?.configured_history_provider ?? provider?.active_history_provider)} />
            <SettingsRow
              title="History access"
              value={formatProviderAccess(provider?.history_capability?.daily_history_access_state)}
              description={historyAccessDescription(provider)}
            />
            {testScenariosEnabled ? <SettingsRow title="Scenario control" value={formatProviderName(testData?.scenario)} description="Development control; not the provider state." /> : null}
          </View>
        </DashboardCard>

        <InfoCard title="Market Data">
          Quotes can route through Finnhub while daily stock and ETF history routes through Polygon / Massive. Cached live data is labelled at the section level.
        </InfoCard>
        <InfoCard title="Historical Data">
          Daily stock and ETF history can route through Polygon / Massive. Quote and history providers may differ, so mixed-source labels can be normal.
        </InfoCard>
        <InfoCard title="Derived Indicators">
          Breadth, rotation, risk, ratings, and reports are derived from app calculations and may differ from broker platforms.
        </InfoCard>
        <InfoCard title="AI Commentary">
          AI and rules-based commentary can be incomplete or incorrect. Use it as educational market context, not advice.
        </InfoCard>
        <InfoCard title="Report Generation">
          Daily reports use the app’s current data state. Mock, cached, or partial data should remain visibly labelled.
        </InfoCard>
      </View>
    </AppScreen>
  );
}

function formatProviderAccess(value?: string | null): string {
  if (!value) {
    return 'Unknown';
  }
  return value
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function historyAccessDescription(provider: ProviderStatus | null): string | undefined {
  const state = provider?.history_capability?.daily_history_access_state;
  if (state === 'restricted') {
    return 'Live history unavailable under the current provider plan. History may route to mock/test data.';
  }
  if (state === 'available') {
    return 'Daily history provider is available.';
  }
  return undefined;
}

function InfoCard({ children, title }: { children: string; title: string }) {
  return (
    <DashboardCard title={title} accentColor={Theme.colors.purple}>
      <Text style={styles.body}>{children}</Text>
    </DashboardCard>
  );
}

const styles = StyleSheet.create({
  body: {
    color: Theme.colors.textMuted,
    fontSize: 14,
    lineHeight: 21,
  },
  stack: {
    gap: Spacing.two,
  },
});
