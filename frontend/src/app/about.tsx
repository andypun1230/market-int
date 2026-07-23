import { useEffect, useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { AppScreen } from '@/components/ui/AppScreen';
import { MetricTile } from '@/components/ui/MetricTile';
import { SettingsRow } from '@/components/ui/SettingsRow';
import { Spacing, Theme } from '@/constants/theme';
import { formatDateTime, formatProviderName, getAppInfo } from '@/features/more/appInfo';
import { getProviderStatus, getTestDataStatus } from '@/services/api';
import { areTestScenariosEnabled } from '@/services/runtimeConfig';
import type { ProviderStatus, TestDataStatus } from '@/types/market';
import { useUserFacingDataState } from '@/features/trust/UserFacingDataStateProvider';

export default function AboutScreen() {
  const appInfo = getAppInfo();
  const { dataState } = useUserFacingDataState();
  const testScenariosEnabled = areTestScenariosEnabled();
  const [provider, setProvider] = useState<ProviderStatus | null>(null);
  const [testData, setTestData] = useState<TestDataStatus | null>(null);

  useEffect(() => {
    let mounted = true;
    const requests = testScenariosEnabled
      ? Promise.allSettled([getProviderStatus(), getTestDataStatus()])
      : Promise.allSettled([getProviderStatus()]);
    requests.then(([providerResult, testDataResult]) => {
      if (!mounted) {
        return;
      }
      if (providerResult.status === 'fulfilled') {
        setProvider(providerResult.value);
      }
      if (testDataResult?.status === 'fulfilled') {
        setTestData(testDataResult.value);
      }
    });
    return () => {
      mounted = false;
    };
  }, [testScenariosEnabled]);

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
            <SettingsRow title="Current data state" value={dataState.headline} description={dataState.explanation} />
            <SettingsRow title="Provider coverage" value={dataState.availabilitySummary} />
            {testScenariosEnabled ? <SettingsRow title="Scenario control (Development only)" value={formatProviderName(testData?.scenario)} description="Test fixtures; separate from the current provider state." /> : null}
            {testScenariosEnabled ? <SettingsRow title="Scenario generated" value={formatDateTime(testData?.generated_at)} /> : null}
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
