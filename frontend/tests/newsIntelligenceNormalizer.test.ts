import { normalizeNewsIntelligence } from '../src/features/context-intelligence/newsIntelligenceNormalizer';

function assert(condition: unknown, message: string) {
  if (!condition) throw new Error(message);
}

function event(overrides: Record<string, unknown> = {}) {
  return {
    event_id: 'event-1',
    canonical_headline: '<b>Fed</b> [decision](https://unsafe.example)',
    source_name: 'Primary wire',
    source_quality: 'primary',
    source_summary: 'Observed update only.',
    published_at: '2026-07-22T09:30:00Z',
    event_status: 'confirmed',
    materiality: {
      market_materiality: 91,
      entity_materiality: 72,
      user_relevance: 44,
    },
    affected_entities: [
      { symbol: 'AAPL', display_name: 'Apple' },
      { display_name: 'Technology' },
    ],
    reaction: { summary: 'SPY moved 0.4% in the observed window.' },
    evidence_ids: ['evidence-1'],
    freshness: { state: 'live' },
    provider_metadata: { provider_mode: 'live' },
    quarantined: false,
    ...overrides,
  };
}

function response(overrides: Record<string, unknown> = {}) {
  return {
    status: 'complete',
    provider: {
      provider: 'licensed-provider',
      mode: 'live',
      source_state: 'live',
      as_of: '2026-07-22T10:00:00Z',
    },
    freshness: { state: 'live' },
    as_of: '2026-07-22T10:00:00Z',
    events: [
      event(),
      event({ event_id: 'quarantined', quarantined: true, event_status: 'unverified' }),
      event({ event_id: 'unverified', source_quality: 'unverified', event_status: 'developing' }),
      event({ event_id: 'retracted', event_status: 'retracted' }),
    ],
    evidence: [{ evidence_id: 'evidence-1' }],
    contradictions: [{ statement: 'A secondary source disputes the timing.' }],
    limitations: [],
    errors: [],
    ...overrides,
  };
}

const live = normalizeNewsIntelligence(response());
assert(live.state === 'live', 'fully live provenance is presented as live');
assert(live.events.length === 1, 'quarantined, unverified, and retracted events are excluded');
assert(live.events[0]?.headline === 'Fed decision', 'headlines are rendered as inert sanitized text');
assert(live.events[0]?.sourceQuality === 'primary', 'source quality is preserved for disclosure');
assert(live.events[0]?.materiality.market === 91, 'market materiality is preserved');
assert(live.events[0]?.materiality.entity === 72, 'entity materiality is preserved');
assert(live.events[0]?.materiality.user === 44, 'watchlist relevance is preserved independently');
assert(live.events[0]?.affectedEntities.join(',') === 'AAPL,Technology', 'affected mappings are preserved');
assert(live.events[0]?.reactionSummary?.includes('observed window'), 'observed reaction summary is preserved');
assert(live.events[0]?.evidenceIds[0] === 'evidence-1', 'event evidence identifiers are preserved');
assert(live.evidenceCount === 1, 'top-level evidence coverage is retained');
assert(live.contradictions[0]?.includes('disputes'), 'contradictions are retained for disclosure');

const partial = normalizeNewsIntelligence(response({
  status: 'partial',
  freshness: { state: 'partial' },
  provider: { provider: 'licensed-provider', mode: 'live', source_state: 'partial' },
}));
assert(partial.state === 'partial', 'partial coverage is never promoted to live');
assert(partial.events.length === 1, 'verified events remain visible with partial coverage');

const stale = normalizeNewsIntelligence(response({ status: 'stale', freshness: { state: 'stale' } }));
assert(stale.state === 'stale', 'stale coverage remains explicitly stale');

const testData = normalizeNewsIntelligence(response({
  provider: { provider: 'fixture', mode: 'test', source_state: 'test' },
  freshness: { state: 'test' },
  events: [event({ freshness: { state: 'test' }, provider_metadata: { provider_mode: 'test' } })],
}));
assert(testData.state === 'test', 'test data is never presented as live');

const unavailable = normalizeNewsIntelligence(response({
  status: 'unavailable',
  provider: { provider: 'unavailable', mode: 'unavailable', source_state: 'unavailable' },
  freshness: { state: 'unavailable' },
  events: [event()],
  limitations: ['Licensed provider is not configured.'],
}));
assert(unavailable.state === 'unavailable', 'unavailable status remains explicit');
assert(unavailable.events.length === 0, 'unavailable responses cannot leak event cards');

const failClosed = normalizeNewsIntelligence({ status: 'complete', events: [event()] });
assert(failClosed.state === 'unavailable', 'missing provenance fails closed instead of claiming live');
