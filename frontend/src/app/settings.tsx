import { useEffect, useState } from 'react';
import { useRouter } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { AppScreen } from '@/components/ui/AppScreen';
import { MetricTile } from '@/components/ui/MetricTile';
import { SettingsRow } from '@/components/ui/SettingsRow';
import { Spacing, Theme, Typography } from '@/constants/theme';
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
import { useUserFacingDataState } from '@/features/trust/UserFacingDataStateProvider';
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
  const { dataState, refresh: refreshSharedDataState } = useUserFacingDataState();
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
      await refreshSharedDataState();
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
      await refreshSharedDataState();
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
          <SettingsRow title="Appearance" description="Theme and reduced-motion behavior." value="Dark" onPress={() => router.push('/appearance')} />
          <SettingsRow title="Accessibility" description="Readable display preferences." value="Manage" onPress={() => router.push('/accessibility')} />
        </View>
      </DashboardCard>

      <DashboardCard title="Language & Region" accentColor={Theme.colors.purple}>
        <View style={styles.rowStack}>
          <SettingsRow title="Language & Region" description="Currently supported display locale." value="English" onPress={() => router.push('/language-region')} />
        </View>
      </DashboardCard>

      <DashboardCard title="Data Usage" accentColor={Theme.colors.warning}>
        <View style={styles.rowStack}>
          <SettingsRow title="Data Usage" description="Operational market-data cache controls." value="Cache" onPress={() => router.push('/data-usage')} />
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
        title="Breadth Coverage Diagnostics"
        subtitle="Coverage for the breadth evidence class"
        accentColor={Theme.colors.accent}
      >
        <View style={styles.settingGrid}>
          <MetricTile label="Breadth universe" value={formatProviderName(universeStatus?.breadth_universe)} />
          <MetricTile label="Universe size" value={universeStatus?.configured_symbols ?? 'N/A'} />
          <MetricTile label="Coverage" value={formatPercent(universeStatus?.coverage_percent)} />
          <MetricTile label="Successful symbols" value={universeStatus?.last_successful_symbols ?? 'N/A'} />
          <MetricTile label="Analyzed symbols" value={universeStatus?.last_successful_symbols ?? 'N/A'} />
          <MetricTile label="Fallback symbols" value="0" />
          <MetricTile label="Failed symbols" value={universeStatus?.failed_symbols_count ?? 'N/A'} />
          <MetricTile label="Breadth evidence" value={formatProviderName(universeStatus?.breadth_universe)} />
          <MetricTile label="Last update" value={formatDateTime(universeStatus?.as_of)} />
        </View>
        <Text style={styles.helperText}>
          Breadth coverage is a separate evidence domain. Its source can differ from the live quote and history providers shown in Data status.
        </Text>
      </DashboardCard>

      <DashboardCard
        title="Scenario Controls"
        subtitle="Development scenarios are separate from the current provider state"
        accentColor={Theme.colors.accent}
      >
        <View style={styles.settingGrid}>
          <MetricTile label="Current provider state" value={dataState.headline} />
          <MetricTile label="Scenario source" value={formatProviderName(testDataStatus?.source)} />
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
                accessibilityState={{ selected }}
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
              {refreshingProvider ? 'Working…' : 'Refresh status'}
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
            <Text style={styles.actionButtonText}>Regenerate test data</Text>
          </Pressable>
        </View>
        <Text style={styles.helperText}>
          Regenerating a scenario updates deterministic development fixtures. It does not change a configured live provider unless the provider mode itself is set to test.
        </Text>
        {providerError ? <Text style={styles.errorText}>{truncateText(providerError, 120)}</Text> : null}
      </DashboardCard>

      <DashboardCard
        title="Intelligence Data Diagnostics"
        subtitle="Evidence-class provider coverage"
        accentColor={Theme.colors.accent}
      >
        <View style={styles.settingGrid}>
          <MetricTile label="Sentiment provider" value={formatProviderName(intelligenceStatus?.sentiment_provider ?? undefined)} />
          <MetricTile label="Options provider" value={formatProviderName(intelligenceStatus?.options_provider ?? undefined)} />
          <MetricTile label="Trade-flow provider" value={formatProviderName(intelligenceStatus?.trade_flow_provider ?? undefined)} />
          <MetricTile label="Liquidity provider" value={formatProviderName(intelligenceStatus?.liquidity_provider ?? undefined)} />
          <MetricTile label="Evidence mode" value={formatProviderName(intelligenceStatus?.overall_mode ?? intelligenceStatus?.data_status ?? undefined)} />
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
          Each evidence class reports its own availability. Generated or proxy evidence never upgrades the live market-data state above.
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
    return 'N/A';
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
    fontSize: Typography.control.fontSize,
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
    minHeight: 44,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.two,
  },
  scenarioChipSelected: {
    backgroundColor: Theme.colors.accentSoft,
    borderColor: Theme.colors.accent,
  },
  scenarioChipText: {
    color: Theme.colors.textMuted,
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.strong,
  },
  scenarioChipTextSelected: {
    color: Theme.colors.accent,
  },
  actionButton: {
    backgroundColor: Theme.colors.accentSoft,
    borderColor: Theme.colors.accent,
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    minHeight: 44,
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
    fontSize: Typography.control.fontSize,
    fontWeight: Typography.weights.strong,
  },
  errorText: {
    color: Theme.colors.danger,
    fontSize: Typography.small.fontSize,
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
    fontSize: Typography.bodyLarge.fontSize,
    lineHeight: 23,
  },
});
