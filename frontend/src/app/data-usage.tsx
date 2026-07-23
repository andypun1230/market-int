import { useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { AppScreen } from '@/components/ui/AppScreen';
import { SettingsRow } from '@/components/ui/SettingsRow';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Spacing, Theme, Typography } from '@/constants/theme';
import { clearMarketDataCache, getMarketDataCacheStatus } from '@/services/api';
import { clearRequestCache } from '@/services/requestCache';
import type { ProviderCacheStatus } from '@/types/market';

export default function DataUsageScreen() {
  const [cacheStatus, setCacheStatus] = useState<ProviderCacheStatus | null>(null);
  const [cacheMessage, setCacheMessage] = useState<string | null>(null);
  const [clearingCache, setClearingCache] = useState(false);

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
    setClearingCache(true);
    setCacheMessage('Clearing cached market data...');
    try {
      const nextStatus = await clearMarketDataCache();
      clearRequestCache();
      setCacheStatus(nextStatus);
      setCacheMessage('Cached market data cleared. The next market-data request may take longer while fresh data is fetched.');
    } catch {
      setCacheMessage('Unable to clear cached market data.');
    } finally {
      setClearingCache(false);
    }
  };

  return (
    <AppScreen showBackButton title="Data Usage" subtitle="Operational market-data cache controls.">
      <View style={styles.stack}>
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
              title="Clear Cached Market Data"
              description="Removes frontend request data plus backend memory and persistent market-data entries. Preferences are kept; the next request may take longer."
              disabled={clearingCache}
              onPress={clearCache}
              value={clearingCache ? 'Clearing…' : 'Clear'}
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
    fontSize: Typography.control.fontSize,
    lineHeight: 20,
  },
  stack: {
    gap: Spacing.two,
  },
});
