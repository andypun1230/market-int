import type { ProviderStatus, TestDataStatus } from '@/types/market';

export type UserFacingDataStateKey =
  | 'live'
  | 'live_cached'
  | 'partial'
  | 'scenario'
  | 'test'
  | 'stale'
  | 'unavailable'
  | 'failed'
  | 'loading';

export type UserFacingDataState = {
  state: UserFacingDataStateKey;
  headline: string;
  explanation: string;
  providerSummary: string;
  freshness: string;
  availabilitySummary: string;
  limitations: string[];
  recommendedAction: string | null;
  provenance: string[];
  technicalDetail: Record<string, string | boolean | null>;
  reasonCodes: string[];
};

export type UserFacingDataStateInput = {
  provider?: ProviderStatus | null;
  testData?: TestDataStatus | null;
  loading?: boolean;
  error?: string | null;
  scenarioActive?: boolean;
  cached?: boolean;
  stale?: boolean;
  now?: Date;
};

export const DATA_STATE_SCREEN_IDS = [
  'home', 'market', 'sectors', 'theme_detail', 'sector_detail', 'stock_detail',
  'watchlist', 'reports', 'copilot', 'settings', 'about', 'data_sources', 'more',
] as const;

export function classifyUserFacingDataState(input: UserFacingDataStateInput): UserFacingDataState {
  const provider = input.provider ?? null;
  const testData = input.testData ?? provider?.test_data ?? null;
  const selected = normalize(provider?.configured_provider ?? provider?.market_data_provider ?? provider?.data_provider);
  const quoteProvider = displayProvider(provider?.configured_quote_provider ?? provider?.active_quote_provider);
  const historyProvider = displayProvider(provider?.configured_history_provider ?? provider?.active_history_provider);
  const providerSummary = [quoteProvider && `Quotes: ${quoteProvider}`, historyProvider && `History: ${historyProvider}`]
    .filter(Boolean).join(' · ') || 'Provider details unavailable';
  const generatedAt = testData?.last_regenerated ?? testData?.generated_at ?? null;
  const freshness = formatFreshness(generatedAt, input.now);
  const technicalDetail = {
    configuredMode: selected || null,
    liveReady: provider?.live_ready ?? false,
    quoteProvider: provider?.configured_quote_provider ?? provider?.active_quote_provider ?? null,
    historyProvider: provider?.configured_history_provider ?? provider?.active_history_provider ?? null,
    historyAccess: provider?.history_capability?.daily_history_access_state ?? null,
    fallbackActive: provider?.fallback_active ?? false,
    testScenario: testData?.scenario ?? null,
  };

  if (input.loading && !provider) {
    return result('loading', 'Checking data source', 'Confirming provider availability and freshness.', providerSummary,
      'Update time pending', 'Availability is being checked.', [], null, [], technicalDetail, ['provider_status_loading']);
  }
  if (input.error && !provider) {
    return result('failed', 'Data status check failed', 'The app could not confirm the current provider state.', providerSummary,
      'Last update unavailable', 'Current availability could not be verified.', [input.error], 'Retry the status check.', [], technicalDetail, ['provider_status_failed']);
  }
  if (!provider) {
    return result('unavailable', 'Data source unavailable', 'No provider status is currently available.', providerSummary,
      'Last update unavailable', 'Market data availability is unknown.', ['Provider diagnostics are unavailable.'], 'Check the backend connection.', [], technicalDetail, ['provider_status_unavailable']);
  }

  const isTestProvider = ['test', 'mock', 'generated_test_data'].some((value) => selected.includes(value));
  if (input.scenarioActive && isTestProvider) {
    return result('scenario', 'Scenario data active', 'A selected scenario is driving analytical data; it is not live market data.',
      `Scenario: ${displayProvider(testData?.scenario) || 'Selected scenario'}`, freshness, 'Scenario coverage depends on generated fixtures.',
      ['Scenario results are deterministic development data.'], 'Do not treat scenario conclusions as current market conditions.',
      compact([testData?.source, testData?.seed && `Seed ${testData.seed}`]), technicalDetail, ['scenario_control_active', 'provider_is_test']);
  }
  if (isTestProvider || provider.data_status === 'test') {
    return result('test', 'Test data active', 'Generated data is driving the application; it is not live market data.',
      displayProvider(provider.active_provider ?? provider.source) || 'Generated test data', freshness, 'Only generated test coverage is available.',
      ['Prices, histories, and conclusions may be simulated.'], 'Use live providers before making time-sensitive decisions.',
      compact([testData?.source, testData?.schema_version && `Schema ${testData.schema_version}`]), technicalDetail, ['provider_is_test']);
  }
  if (input.stale) {
    return result('stale', 'Market data is stale', 'The latest successful provider data is older than the active freshness window.',
      providerSummary, freshness, 'Older observations remain visible and are clearly identified.',
      ['Current market conditions may have changed.'], 'Refresh before acting on time-sensitive signals.', compact([provider.source]), technicalDetail, ['provider_data_stale']);
  }
  if (input.cached || provider.fallback_active) {
    return result('live_cached', 'Live source unavailable; showing cached data', 'The last successful live response is retained while the provider recovers.',
      providerSummary, freshness, 'Cached coverage may be narrower than normal.', ['Cached values are not current quotes.'],
      'Refresh before acting on time-sensitive signals.', compact([provider.source]), technicalDetail, ['live_cache_retained']);
  }

  const quoteAvailable = provider.quote_capability?.quote_access_state === 'available'
    || provider.quote_health?.reachable === true;
  const historyState = provider.history_capability?.daily_history_access_state;
  const historyAvailable = historyState === 'available' || provider.history_ready === true;
  const liveConfigured = provider.live_ready || ['finnhub', 'live', 'auto'].includes(selected);
  if (liveConfigured && (quoteAvailable || provider.live_ready) && !historyAvailable) {
    return result('partial', 'Live data partially available', 'Live quotes are available, but one or more analytical history domains are limited.',
      providerSummary, 'Provider status current', 'Quotes available · history limited',
      compact([historyState === 'restricted' ? 'Daily history access is restricted by the provider plan.' : 'Daily history is unavailable.']),
      'Use available quotes and treat history-based conclusions as partial.', compact([provider.source]), technicalDetail,
      ['live_quotes_available', `history_${historyState || 'unavailable'}`]);
  }
  if (liveConfigured && (quoteAvailable || provider.live_ready) && historyAvailable) {
    return result('live', 'Live market data', 'Current provider routes are available for quotes and daily history.', providerSummary,
      'Provider status current', 'Live quotes and daily history available.', [], null, compact([provider.source]), technicalDetail, ['live_providers_available']);
  }
  return result('unavailable', 'Live market data unavailable', 'Configured providers are not currently ready.', providerSummary,
    'Last update unavailable', 'No verified live provider coverage.', ['Provider health is unavailable or unreachable.'],
    'Check provider access and retry.', compact([provider.source]), technicalDetail, ['live_provider_unavailable']);
}

export function dataStateForScreen(input: UserFacingDataStateInput, _screenId: typeof DATA_STATE_SCREEN_IDS[number]) {
  return classifyUserFacingDataState(input);
}

export function formatFreshness(value?: string | null, now = new Date()): string {
  if (!value) return 'Last update unavailable';
  const timestamp = new Date(value);
  if (!Number.isFinite(timestamp.getTime())) return 'Last update unavailable';
  const minutes = Math.max(0, Math.floor((now.getTime() - timestamp.getTime()) / 60_000));
  if (minutes < 1) return 'Updated just now';
  if (minutes < 60) return `Updated ${minutes} minute${minutes === 1 ? '' : 's'} ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `Data is ${hours} hour${hours === 1 ? '' : 's'} old`;
  return `Last successful update ${hours < 48 ? 'yesterday' : `${Math.floor(hours / 24)} days ago`}`;
}

function result(
  state: UserFacingDataStateKey,
  headline: string,
  explanation: string,
  providerSummary: string,
  freshness: string,
  availabilitySummary: string,
  limitations: string[],
  recommendedAction: string | null,
  provenance: string[],
  technicalDetail: UserFacingDataState['technicalDetail'],
  reasonCodes: string[],
): UserFacingDataState {
  return { state, headline, explanation, providerSummary, freshness, availabilitySummary, limitations, recommendedAction, provenance, technicalDetail, reasonCodes };
}

function displayProvider(value?: string | null) {
  return normalize(value).split('_').filter(Boolean).map((part) => part[0].toUpperCase() + part.slice(1)).join(' ');
}

function normalize(value?: string | null) {
  return (value ?? '').trim().toLowerCase();
}

function compact(values: (string | number | null | undefined | false)[]) {
  return values.filter((value): value is string | number => value !== null && value !== undefined && value !== false && value !== '').map(String);
}
