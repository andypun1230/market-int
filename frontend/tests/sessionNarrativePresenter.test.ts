import {
  buildSessionConsumerPresentation,
  normalizeSessionNarrative,
} from '../src/features/context-intelligence/sessionNarrativePresenter';

function assert(condition: unknown, message: string) {
  if (!condition) throw new Error(message);
}

function session(overrides: Record<string, unknown> = {}) {
  return {
    status: 'daily_only',
    availability: 'daily_only',
    provider: 'polygon',
    data_mode: 'daily_only',
    as_of: '2026-07-22T10:00:00Z',
    latest_daily_session: '2026-07-21',
    narrative: {
      headline: 'Daily context is available',
      claims: [],
      confidence: 'limited',
      freshness: 'unavailable',
      caveats: ['No licensed intraday bars are configured.'],
      causality_disclosure: 'Observed timing does not establish causality.',
    },
    limitations: ['Daily bars are never relabeled as intraday bars.'],
    provenance: {
      intraday_supported: false,
      test_data_detected: false,
    },
    ...overrides,
  };
}

const dailyOnly = normalizeSessionNarrative(session());
assert(dailyOnly.state === 'daily_only', 'top-level daily_only wins over unavailable nested intraday freshness');
const dailyPresentation = buildSessionConsumerPresentation(dailyOnly);
assert(dailyPresentation.stateLabel === 'Daily only', 'daily-only status is disclosed explicitly');
assert(dailyPresentation.supportingText?.includes('2026-07-21'), 'latest daily session is disclosed');
assert(!dailyPresentation.supportingText?.toLowerCase().includes('live'), 'daily-only data is never labeled live');

const live = normalizeSessionNarrative(session({
  status: 'complete',
  availability: 'available',
  data_mode: 'intraday_5m',
  narrative: {
    headline: 'Breadth improved after the open',
    claims: [{ text: 'Breadth improved during the observed window.' }],
    confidence: 'moderate',
    freshness: 'live',
    caveats: [],
  },
  provenance: { intraday_supported: true, test_data_detected: false },
}));
assert(live.state === 'live', 'complete licensed intraday evidence can be live');
assert(live.claims[0]?.includes('observed window'), 'server-rendered observed claim is retained');

const partial = normalizeSessionNarrative(session({
  status: 'partial',
  availability: 'partial',
  data_mode: 'intraday_15m',
  narrative: { headline: 'Partial session', freshness: 'partial', caveats: ['Coverage gap.'] },
}));
assert(partial.state === 'partial', 'partial session coverage remains partial');

const testData = normalizeSessionNarrative(session({
  status: 'complete',
  availability: 'available',
  data_mode: 'intraday_5m',
  narrative: { headline: 'Fixture session', freshness: 'live', caveats: [] },
  provenance: { intraday_supported: true, test_data_detected: true },
}));
assert(testData.state === 'test', 'detected test data overrides apparent live freshness');
assert(buildSessionConsumerPresentation(testData).supportingText?.includes('not live'), 'test disclosure is explicit');

const unavailable = normalizeSessionNarrative(session({
  status: 'unavailable',
  availability: 'unavailable',
  data_mode: 'unavailable',
}));
assert(unavailable.state === 'unavailable', 'unavailable session context remains explicit');

const failClosed = normalizeSessionNarrative({ status: 'complete' });
assert(failClosed.state === 'unavailable', 'malformed session payload fails closed');
