import { DATA_STATE_SCREEN_IDS, classifyUserFacingDataState, dataStateForScreen } from '../src/features/trust/userFacingDataState';
import type { ProviderStatus, TestDataStatus } from '../src/types/market';

function assert(condition: unknown, message: string) { if (!condition) throw new Error(message); }
const base = (overrides: Partial<ProviderStatus> = {}): ProviderStatus => ({
  data_provider: 'finnhub', market_data_provider: 'finnhub', configured_provider: 'finnhub',
  configured_quote_provider: 'finnhub', configured_history_provider: 'polygon', active_provider: 'finnhub',
  live_ready: true, history_ready: true, quote_health: { provider: 'finnhub', enabled: true, configured: true, reachable: true, status: 'available', last_successful_request: null, last_error: null, fallback_active: false },
  history_capability: { provider: 'polygon', supports_quotes: false, supports_batch_quotes: false, supports_daily_history: true, supports_intraday_history: false, quote_access_state: 'unavailable', daily_history_access_state: 'available' },
  ...overrides,
});
const testData: TestDataStatus = { mode: 'TEST_DATA', scenario: 'balanced_market', seed: '7', generated_at: '2026-07-23T10:00:00Z', source: 'generated_test_data', data_status: 'test', is_mock: true, schema_version: 1 };

const live = classifyUserFacingDataState({ provider: base(), testData });
assert(live.state === 'live' && live.headline === 'Live market data', 'test controls do not override a live provider state');
DATA_STATE_SCREEN_IDS.forEach((screen) => assert(dataStateForScreen({ provider: base(), testData }, screen).headline === live.headline, `${screen} receives identical plain-language state`));
assert(classifyUserFacingDataState({ provider: base(), cached: true }).state === 'live_cached', 'cached live is qualified');
assert(classifyUserFacingDataState({ provider: base({ history_ready: false, history_capability: { ...base().history_capability!, daily_history_access_state: 'restricted' } }) }).state === 'partial', 'partial is not unavailable');
assert(classifyUserFacingDataState({ provider: base({ configured_provider: 'test', market_data_provider: 'test', data_status: 'test', live_ready: false }), testData }).state === 'test', 'test provider is explicit');
assert(classifyUserFacingDataState({ provider: base({ configured_provider: 'test', market_data_provider: 'test', data_status: 'test', live_ready: false }), testData, scenarioActive: true }).state === 'scenario', 'scenario is distinct from test provider');
assert(classifyUserFacingDataState({ provider: base(), stale: true }).state === 'stale', 'stale is explicit');
assert(classifyUserFacingDataState({ loading: true }).state === 'loading', 'loading is explicit');
assert(classifyUserFacingDataState({ error: 'offline' }).state === 'failed', 'failed is explicit');
assert(classifyUserFacingDataState({}).state === 'unavailable', 'unavailable is explicit');
assert(!live.headline.includes('TEST_DATA'), 'raw backend enums are never user-facing');
console.log('PASS Stage 10.2 user-facing data-state authority');
