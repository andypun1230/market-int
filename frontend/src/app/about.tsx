import { useEffect, useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { AppScreen } from '@/components/ui/AppScreen';
import { MetricTile } from '@/components/ui/MetricTile';
import { SettingsRow } from '@/components/ui/SettingsRow';
import { Spacing, Theme } from '@/constants/theme';
import { formatDateTime, formatProviderName, getAppInfo } from '@/features/more/appInfo';
import { getProviderStatus, getTestDataStatus } from '@/services/api';
import type { ProviderStatus, TestDataStatus } from '@/types/market';

export default function AboutScreen() {
  const appInfo = getAppInfo();
  const [provider, setProvider] = useState<ProviderStatus | null>(null);
  const [testData, setTestData] = useState<TestDataStatus | null>(null);

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
    <AppScreen showBackButton title="About" subtitle="Version, build, environment, and system state.">
      <View style={styles.stack}>
        <DashboardCard title={appInfo.name} accentColor={Theme.colors.accent}>
          <View style={styles.grid}>
            <MetricTile label="Version" value={appInfo.version} />
            <MetricTile label="Build" value={appInfo.buildNumber} />
            <MetricTile label="Environment" value={appInfo.environment} />
            <MetricTile label="API URL" value={appInfo.apiUrl} />
          </View>
        </DashboardCard>

        <DashboardCard title="System Information" accentColor={Theme.colors.purple}>
          <View style={styles.stack}>
            <SettingsRow title="Data mode" value={testData?.mode ?? 'Test Data'} />
            <SettingsRow title="Scenario" value={formatProviderName(testData?.scenario)} />
            <SettingsRow title="Last successful data refresh" value={formatDateTime(testData?.generated_at)} />
            <SettingsRow title="Market-data provider" value={formatProviderName(provider?.active_provider ?? provider?.market_data_provider)} />
            <SettingsRow title="Report API status" value="Available when backend is running" />
          </View>
        </DashboardCard>
      </View>
    </AppScreen>
  );
}

const styles = StyleSheet.create({
  grid: {
    gap: Spacing.two,
  },
  stack: {
    gap: Spacing.two,
  },
});
