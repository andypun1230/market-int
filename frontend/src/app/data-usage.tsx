import { useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { AppScreen } from '@/components/ui/AppScreen';
import { SettingsRow } from '@/components/ui/SettingsRow';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Spacing, Theme } from '@/constants/theme';
import { useAppPreferences, type DataUsagePreferences } from '@/features/preferences/appPreferences';
import { clearMarketDataCache, getMarketDataCacheStatus } from '@/services/api';
import type { ProviderCacheStatus } from '@/types/market';

const REFRESH_MODES: { label: string; value: DataUsagePreferences['refreshMode'] }[] = [
  { label: 'Manual', value: 'manual' },
  { label: 'Every 15 minutes', value: '15m' },
  { label: 'Every 30 minutes', value: '30m' },
  { label: 'Every hour', value: '60m' },
];

export default function DataUsageScreen() {
  const { preferences, updatePreferences } = useAppPreferences();
  const [cacheStatus, setCacheStatus] = useState<ProviderCacheStatus | null>(null);
  const [cacheMessage, setCacheMessage] = useState<string | null>(null);
  const dataUsage = preferences.dataUsage;
  const update = (patch: Partial<DataUsagePreferences>) =>
    updatePreferences({ dataUsage: { ...dataUsage, ...patch } });

  useEffect(() => {
    let mounted = true;
    getMarketDataCacheStatus()
      .then((status) => {
        if (mounted) {
          setCacheStatus(status);
        }
      })
      .catch(() => {
        if (mounted) {
          setCacheMessage('Cache status unavailable.');
        }
      });
    return () => {
      mounted = false;
    };
  }, []);

  const clearCache = async () => {
    setCacheMessage('Clearing cached market data...');
    try {
      const nextStatus = await clearMarketDataCache();
      setCacheStatus(nextStatus);
      setCacheMessage('Cached market data cleared.');
    } catch {
      setCacheMessage('Unable to clear cached market data.');
    }
  };

  return (
    <AppScreen showBackButton title="Data Usage" subtitle="Refresh, downloads, and future cache controls.">
      <View style={styles.stack}>
        <DashboardCard title="Refresh Mode" accentColor={Theme.colors.accent}>
          <View style={styles.stack}>
            {REFRESH_MODES.map((mode) => (
              <SettingsRow
                badge={dataUsage.refreshMode === mode.value ? <StatusBadge label="Selected" showDot={false} tone="info" /> : undefined}
                key={mode.value}
                onPress={() => update({ refreshMode: mode.value })}
                title={mode.label}
              />
            ))}
          </View>
        </DashboardCard>

        <DashboardCard title="Network Controls" accentColor={Theme.colors.purple}>
          <View style={styles.stack}>
            <SettingsRow title="Low Data Mode" description="Reduces automatic refreshes, chart history requests, and report downloads." switchValue={dataUsage.lowDataMode} onValueChange={(lowDataMode) => update({ lowDataMode })} />
            <SettingsRow title="Wi-Fi Only" description="Future downloads and background refreshes will respect this setting." switchValue={dataUsage.wifiOnly} onValueChange={(wifiOnly) => update({ wifiOnly })} />
            <SettingsRow title="Background Refresh" switchValue={dataUsage.backgroundRefresh} onValueChange={(backgroundRefresh) => update({ backgroundRefresh })} />
            <SettingsRow title="Download Charts Automatically" switchValue={dataUsage.autoLoadCharts} onValueChange={(autoLoadCharts) => update({ autoLoadCharts })} />
          </View>
        </DashboardCard>

        <DashboardCard title="Reports" accentColor={Theme.colors.warning}>
          <View style={styles.stack}>
            {(['off', 'wifi', 'always'] as const).map((value) => (
              <SettingsRow
                badge={dataUsage.autoDownloadReports === value ? <StatusBadge label="Selected" showDot={false} tone="info" /> : undefined}
                key={value}
                onPress={() => update({ autoDownloadReports: value })}
                title={value === 'off' ? 'Do Not Auto-Download' : value === 'wifi' ? 'Wi-Fi Only' : 'Always'}
              />
            ))}
          </View>
        </DashboardCard>

        <DashboardCard title="Market Data Cache" accentColor={Theme.colors.accent}>
          <View style={styles.stack}>
            <SettingsRow
              title="Persistent Cache"
              value={cacheStatus?.repository?.persistent?.healthy === false ? 'Unavailable' : 'Enabled'}
              badge={<StatusBadge label={cacheStatus?.repository?.persistent?.healthy === false ? 'Issue' : 'Active'} showDot tone={cacheStatus?.repository?.persistent?.healthy === false ? 'warning' : 'success'} />}
            />
            <SettingsRow
              title="Cache Size"
              value={formatCacheSize(cacheStatus)}
              description={`${cacheStatus?.repository?.persistent?.entries ?? 0} persisted entries · ${cacheStatus?.repository?.persistent?.stale_entries ?? 0} stale`}
            />
            <SettingsRow
              title="Use Stale Data When Offline"
              description="The backend may show clearly labelled stale market data when providers are unavailable."
              switchValue={dataUsage.backgroundRefresh}
              onValueChange={(backgroundRefresh) => update({ backgroundRefresh })}
            />
            <SettingsRow
              title="Clear Cached Market Data"
              description="Removes memory and persistent market-data cache entries. API keys and preferences are not stored here."
              onPress={clearCache}
              value="Clear"
            />
            {cacheMessage ? <Text style={styles.note}>{cacheMessage}</Text> : null}
          </View>
        </DashboardCard>
      </View>
    </AppScreen>
  );
}

function formatCacheSize(status: ProviderCacheStatus | null): string {
  const sizeMb = status?.repository?.persistent?.database_size_mb;
  if (typeof sizeMb === 'number' && Number.isFinite(sizeMb)) {
    return `${sizeMb.toFixed(2)} MB`;
  }
  return 'N/A';
}

const styles = StyleSheet.create({
  note: {
    color: Theme.colors.textMuted,
    fontSize: 13,
    lineHeight: 20,
  },
  stack: {
    gap: Spacing.two,
  },
});
