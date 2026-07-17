import { useEffect, useState } from 'react';
import { useRouter } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { AppScreen } from '@/components/ui/AppScreen';
import { MetricTile } from '@/components/ui/MetricTile';
import { SettingsRow } from '@/components/ui/SettingsRow';
import { Spacing, Theme } from '@/constants/theme';
import {
  API_URL,
  getIntelligenceStatus,
  getProviderCacheStatus,
  getProviderStatus,
  getTestDataScenarios,
  getTestDataStatus,
  getUniverseStatus,
  regenerateTestData,
} from '@/services/api';
import { clearRequestCache } from '@/services/requestCache';
import {
  IntelligenceStatus,
  ProviderCacheStatus,
  ProviderStatus,
  TestDataScenario,
  TestDataStatus,
  UniverseStatus,
} from '@/types/market';

const settings = [
  { label: 'App name', value: 'Market Intelligence' },
  { label: 'API URL', value: API_URL },
  { label: 'Version', value: '1.0.0' },
];

export default function SettingsScreen() {
  const router = useRouter();
  const [providerStatus, setProviderStatus] = useState<ProviderStatus | null>(null);
  const [cacheStatus, setCacheStatus] = useState<ProviderCacheStatus | null>(null);
  const [universeStatus, setUniverseStatus] = useState<UniverseStatus | null>(null);
  const [intelligenceStatus, setIntelligenceStatus] = useState<IntelligenceStatus | null>(null);
  const [testDataStatus, setTestDataStatus] = useState<TestDataStatus | null>(null);
  const [testDataScenarios, setTestDataScenarios] = useState<TestDataScenario[]>([]);
  const [selectedScenario, setSelectedScenario] = useState('balanced_market');
  const [providerError, setProviderError] = useState<string | null>(null);
  const [refreshingProvider, setRefreshingProvider] = useState(false);

  useEffect(() => {
    let isMounted = true;

    refreshProviderDiagnostics()
      .then(({ cache, intelligence, scenarios, status, testData, universe }) => {
        if (isMounted) {
          setProviderStatus(status);
          setCacheStatus(cache);
          setUniverseStatus(universe);
          setIntelligenceStatus(intelligence);
          setTestDataStatus(testData);
          setTestDataScenarios(scenarios);
          setSelectedScenario(testData.scenario);
          setProviderError(null);
        }
      })
      .catch((error) => {
        if (isMounted) {
          setProviderStatus(null);
          setCacheStatus(null);
          setUniverseStatus(null);
          setIntelligenceStatus(null);
          setTestDataStatus(null);
          setTestDataScenarios([]);
          setProviderError(getErrorMessage(error));
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const currentProvider = formatProviderName(providerStatus?.active_provider ?? providerStatus?.market_data_provider);
  const visibleCacheStatus = cacheStatus ?? providerStatus?.cache_status ?? null;

  const handleRefreshProvider = async () => {
    setRefreshingProvider(true);
    try {
      const diagnostics = await refreshProviderDiagnostics();
      setProviderStatus(diagnostics.status);
      setCacheStatus(diagnostics.cache);
      setUniverseStatus(diagnostics.universe);
      setIntelligenceStatus(diagnostics.intelligence);
      setTestDataStatus(diagnostics.testData);
      setTestDataScenarios(diagnostics.scenarios);
      setSelectedScenario(diagnostics.testData.scenario);
      setProviderError(null);
    } catch (error) {
      setProviderError(getErrorMessage(error));
    } finally {
      setRefreshingProvider(false);
    }
  };

  const handleRegenerateTestData = async () => {
    setRefreshingProvider(true);
    try {
      const result = await regenerateTestData({ scenario: selectedScenario });
      clearRequestCache();
      const diagnostics = await refreshProviderDiagnostics();
      setTestDataStatus(result.test_data ?? diagnostics.testData);
      setProviderStatus(diagnostics.status);
      setCacheStatus(diagnostics.cache);
      setUniverseStatus(diagnostics.universe);
      setIntelligenceStatus(diagnostics.intelligence);
      setTestDataScenarios(diagnostics.scenarios);
      setProviderError(null);
    } catch (error) {
      setProviderError(getErrorMessage(error));
    } finally {
      setRefreshingProvider(false);
    }
  };

  return (
    <AppScreen showBackButton title="Settings" subtitle="Application details and local backend configuration.">
      <DashboardCard title="Appearance" accentColor={Theme.colors.accent}>
        <View style={styles.rowStack}>
          <SettingsRow title="Appearance" description="Theme, text size, accent color, and motion." value="Dark" onPress={() => router.push('/appearance')} />
          <SettingsRow title="Accessibility" description="Readable display preferences." value="Manage" onPress={() => router.push('/accessibility')} />
        </View>
      </DashboardCard>

      <DashboardCard title="Language & Region" accentColor={Theme.colors.purple}>
        <View style={styles.rowStack}>
          <SettingsRow title="Language & Region" description="Language, region, time display, and number format." value="English" onPress={() => router.push('/language-region')} />
        </View>
      </DashboardCard>

      <DashboardCard title="Data Usage" accentColor={Theme.colors.warning}>
        <View style={styles.rowStack}>
          <SettingsRow title="Data Usage" description="Refresh cadence, Wi-Fi only mode, and report downloads." value="Manual" onPress={() => router.push('/data-usage')} />
        </View>
      </DashboardCard>

      <DashboardCard title="About" accentColor={Theme.colors.accent}>
        <View style={styles.rowStack}>
          <SettingsRow title="About" description="Version, build, environment, and backend status." onPress={() => router.push('/about')} />
          <SettingsRow title="Data Sources" description="Current data mode, providers, and calculation limits." onPress={() => router.push('/data-sources')} />
          <SettingsRow title="Financial Disclaimer" description="Important educational-use limitations." onPress={() => router.push('/disclaimer')} />
          <SettingsRow title="Privacy" description="Local storage, AI chat, report downloads, and future accounts." onPress={() => router.push('/privacy')} />
        </View>
      </DashboardCard>

      <DashboardCard title="Application" accentColor={Theme.colors.accent}>
        <View style={styles.settingGrid}>
          {settings.map((setting) => (
            <MetricTile key={setting.label} label={setting.label} value={setting.value} />
          ))}
        </View>
      </DashboardCard>

      <DashboardCard
        title="Universe Diagnostics"
        subtitle="Generated breadth coverage"
        accentColor={Theme.colors.accent}
      >
        <View style={styles.settingGrid}>
          <MetricTile label="Breadth universe" value={formatProviderName(universeStatus?.breadth_universe)} />
          <MetricTile label="Universe size" value={universeStatus?.configured_symbols ?? 'N/A'} />
          <MetricTile label="Coverage" value={formatPercent(universeStatus?.coverage_percent)} />
          <MetricTile label="Successful symbols" value={universeStatus?.last_successful_symbols ?? 'N/A'} />
          <MetricTile label="Test-data symbols" value={universeStatus?.last_successful_symbols ?? 'N/A'} />
          <MetricTile label="Fallback symbols" value="0" />
          <MetricTile label="Failed symbols" value={universeStatus?.failed_symbols_count ?? 'N/A'} />
          <MetricTile label="Breadth mode" value="Test Data" />
          <MetricTile label="Last update" value={formatDateTime(universeStatus?.as_of)} />
        </View>
        <Text style={styles.helperText}>
          Breadth is generated from the local test-data universe and is not current exchange-wide breadth.
        </Text>
      </DashboardCard>

      <DashboardCard
        title="Generated Test Data"
        subtitle="Local market-data mode"
        accentColor={Theme.colors.accent}
      >
        <View style={styles.settingGrid}>
          <MetricTile label="Data mode" value="Test Data" />
          <MetricTile label="Source" value={currentProvider} />
          <MetricTile label="Scenario" value={formatProviderName(testDataStatus?.scenario)} />
          <MetricTile label="Seed" value={testDataStatus?.seed ?? 'N/A'} />
          <MetricTile label="Last regenerated" value={formatDateTime(testDataStatus?.last_regenerated ?? testDataStatus?.generated_at)} />
          <MetricTile label="Cache items" value={visibleCacheStatus?.items ?? 'N/A'} />
        </View>
        <View style={styles.scenarioRow}>
          {testDataScenarios.map((scenario) => {
            const selected = selectedScenario === scenario.id;
            return (
              <Pressable
                accessibilityRole="button"
                key={scenario.id}
                onPress={() => setSelectedScenario(scenario.id)}
                style={({ pressed }) => [
                  styles.scenarioChip,
                  selected && styles.scenarioChipSelected,
                  pressed && styles.actionButtonPressed,
                ]}>
                <Text style={[styles.scenarioChipText, selected && styles.scenarioChipTextSelected]}>
                  {scenario.label}
                </Text>
              </Pressable>
            );
          })}
        </View>
        <View style={styles.actionRow}>
          <Pressable
            accessibilityRole="button"
            disabled={refreshingProvider}
            onPress={handleRefreshProvider}
            style={({ pressed }) => [
              styles.actionButton,
              pressed && styles.actionButtonPressed,
              refreshingProvider && styles.actionButtonDisabled,
            ]}>
            <Text style={styles.actionButtonText}>
              {refreshingProvider ? 'Working...' : 'Refresh Status'}
            </Text>
          </Pressable>
          <Pressable
            accessibilityRole="button"
            disabled={refreshingProvider}
            onPress={handleRegenerateTestData}
            style={({ pressed }) => [
              styles.actionButton,
              pressed && styles.actionButtonPressed,
              refreshingProvider && styles.actionButtonDisabled,
            ]}>
            <Text style={styles.actionButtonText}>Regenerate Test Data</Text>
          </Pressable>
        </View>
        <Text style={styles.helperText}>
          Market quotes, histories, sectors, themes, signals, and intelligence are generated locally for interface development.
        </Text>
        {providerError ? <Text style={styles.errorText}>{truncateText(providerError, 120)}</Text> : null}
      </DashboardCard>

      <DashboardCard
        title="Intelligence Data Diagnostics"
        subtitle="Generated sentiment, options, trade-flow, and liquidity"
        accentColor={Theme.colors.accent}
      >
        <View style={styles.settingGrid}>
          <MetricTile label="Sentiment provider" value={formatProviderName(intelligenceStatus?.sentiment_provider ?? undefined)} />
          <MetricTile label="Options provider" value={formatProviderName(intelligenceStatus?.options_provider ?? undefined)} />
          <MetricTile label="Trade-flow provider" value={formatProviderName(intelligenceStatus?.trade_flow_provider ?? undefined)} />
          <MetricTile label="Liquidity provider" value={formatProviderName(intelligenceStatus?.liquidity_provider ?? undefined)} />
          <MetricTile label="Data mode" value="Test Data" />
          <MetricTile label="Sentiment available" value={formatBoolean(intelligenceStatus?.sentiment_health?.reachable)} />
          <MetricTile label="Options available" value={formatBoolean(intelligenceStatus?.options_health?.reachable)} />
          <MetricTile label="Trade-flow available" value={formatBoolean(intelligenceStatus?.trade_flow_health?.reachable)} />
          <MetricTile label="Liquidity available" value={formatBoolean(intelligenceStatus?.liquidity_health?.reachable)} />
          <MetricTile
            label="Last intelligence error"
            value={truncateText(
              intelligenceStatus?.options_health?.last_error ??
                intelligenceStatus?.trade_flow_health?.last_error ??
                intelligenceStatus?.sentiment_health?.last_error ??
                intelligenceStatus?.liquidity_health?.last_error ??
                'None',
              72,
            )}
          />
        </View>
        <Text style={styles.helperText}>
          These are deterministic test scenarios. They are not live options, liquidity, news, or institutional feeds.
        </Text>
      </DashboardCard>

      <DashboardCard title="Disclaimer" accentColor={Theme.colors.warning}>
        <View style={styles.disclaimerBox}>
          <Text style={styles.disclaimer}>
            This app provides market information and educational analysis only. It is not
            financial advice.
          </Text>
        </View>
      </DashboardCard>
    </AppScreen>
  );
}

function formatProviderName(provider?: string) {
  if (!provider) {
    return 'Test Data';
  }

  return provider
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

async function refreshProviderDiagnostics() {
  const [status, cache, universe, intelligence, testData, scenariosResponse] = await Promise.all([
    getProviderStatus(),
    getProviderCacheStatus(),
    getUniverseStatus(),
    getIntelligenceStatus(),
    getTestDataStatus(),
    getTestDataScenarios(),
  ]);
  return { cache, intelligence, scenarios: scenariosResponse.items, status, testData, universe };
}

function formatBoolean(value?: boolean | null) {
  if (value === undefined || value === null) {
    return 'N/A';
  }

  return value ? 'Yes' : 'No';
}

function formatDateTime(value?: string | null) {
  if (!value) {
    return 'N/A';
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return 'N/A';
  }

  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function truncateText(value: string, maxLength: number) {
  if (value.length <= maxLength) {
    return value;
  }

  return `${value.slice(0, maxLength - 1)}…`;
}

function formatPercent(value?: number | null) {
  if (typeof value !== 'number') {
    return 'N/A';
  }

  return `${value.toFixed(1)}%`;
}

function getErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : 'Unable to load provider diagnostics.';
}

const styles = StyleSheet.create({
  rowStack: {
    gap: Spacing.two,
  },
  settingGrid: {
    gap: Spacing.two,
  },
  helperText: {
    color: Theme.colors.textMuted,
    fontSize: 13,
    lineHeight: 19,
    marginTop: Spacing.three,
  },
  actionRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
    marginTop: Spacing.three,
  },
  scenarioRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
    marginTop: Spacing.three,
  },
  scenarioChip: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.two,
  },
  scenarioChipSelected: {
    backgroundColor: Theme.colors.accentSoft,
    borderColor: Theme.colors.accent,
  },
  scenarioChipText: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '800',
  },
  scenarioChipTextSelected: {
    color: Theme.colors.accent,
  },
  actionButton: {
    backgroundColor: Theme.colors.accentSoft,
    borderColor: Theme.colors.accent,
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.two,
  },
  secondaryButton: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
  },
  actionButtonPressed: {
    opacity: 0.78,
  },
  actionButtonDisabled: {
    opacity: 0.55,
  },
  actionButtonText: {
    color: Theme.colors.text,
    fontSize: 13,
    fontWeight: '900',
  },
  errorText: {
    color: Theme.colors.danger,
    fontSize: 12,
    lineHeight: 18,
    marginTop: Spacing.two,
  },
  disclaimerBox: {
    backgroundColor: Theme.colors.warningSoft,
    borderRadius: Theme.radii.small,
    padding: Spacing.three,
  },
  disclaimer: {
    color: Theme.colors.text,
    fontSize: 15,
    lineHeight: 23,
  },
});
