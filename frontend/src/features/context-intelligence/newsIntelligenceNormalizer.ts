import type {
  IntelligenceDisplayState,
  NewsConsumerPresentation,
  NewsEventModel,
  NewsIntelligenceDto,
  NewsIntelligenceModel,
  NewsServiceStatus,
} from '@/features/context-intelligence/types';

const NEWS_STATUSES = new Set<NewsServiceStatus>([
  'complete',
  'partial',
  'stale',
  'unavailable',
  'failed',
]);

const DISPLAYABLE_EVENT_STATUSES = new Set<NewsEventModel['eventStatus']>([
  'confirmed',
  'developing',
  'corrected',
]);

const DISPLAYABLE_SOURCE_QUALITIES = new Set<NewsEventModel['sourceQuality']>([
  'primary',
  'high_confidence_secondary',
  'supporting_secondary',
]);

export function normalizeNewsIntelligence(input: unknown): NewsIntelligenceModel {
  const record = asRecord(input);
  const dto = record as NewsIntelligenceDto;
  const status = normalizeStatus(dto.status);
  const provider = asRecord(dto.provider);
  const freshness = asRecord(dto.freshness);
  const rawEvents = Array.isArray(dto.events) ? dto.events : [];
  const state = resolveNewsState({
    status,
    providerMode: asString(provider.mode),
    providerState: asString(provider.source_state),
    freshnessState: asString(freshness.state),
    hasTestEvent: rawEvents.some(isTestEvent),
  });

  return {
    state,
    status,
    provider: safeText(provider.provider, 120),
    asOf: asIsoDate(dto.as_of) ?? asIsoDate(provider.as_of),
    events: state === 'unavailable' || state === 'failed'
      ? []
      : rawEvents.flatMap((event) => {
          const normalized = normalizeEvent(event, state);
          return normalized ? [normalized] : [];
        }),
    contradictions: normalizeContradictions(record.contradictions),
    evidenceCount: Array.isArray(record.evidence) ? record.evidence.length : 0,
    limitations: stringList(dto.limitations, 8, 300),
    errors: stringList(dto.errors, 5, 300),
  };
}

export function buildNewsConsumerPresentation({
  model,
  title,
  maxItems = 5,
  emptyMessage = 'No material events are available for this context.',
}: {
  model: NewsIntelligenceModel;
  title: string;
  maxItems?: number;
  emptyMessage?: string;
}): NewsConsumerPresentation {
  const itemLimit = Math.max(0, Math.min(10, Math.floor(maxItems)));
  const message = getNewsMessage(model, emptyMessage);

  return {
    title,
    state: model.state,
    stateLabel: intelligenceStateLabel(model.state),
    items: model.events.slice(0, itemLimit),
    message,
  };
}

export function intelligenceStateLabel(state: IntelligenceDisplayState): string {
  switch (state) {
    case 'live':
      return 'Live';
    case 'delayed':
      return 'Delayed';
    case 'cached':
      return 'Cached';
    case 'partial':
      return 'Partial';
    case 'stale':
      return 'Stale';
    case 'test':
      return 'Test data';
    case 'daily_only':
      return 'Daily only';
    case 'failed':
      return 'Failed';
    default:
      return 'Unavailable';
  }
}

function getNewsMessage(model: NewsIntelligenceModel, emptyMessage: string): string | null {
  if (model.state === 'failed') {
    return 'Context intelligence failed to load. Other screen data is unaffected.';
  }
  if (model.state === 'unavailable') {
    return model.limitations[0] ?? 'Context intelligence is currently unavailable.';
  }
  if (!model.events.length) {
    return emptyMessage;
  }
  if (model.state === 'test') {
    return 'Test data is isolated from live market intelligence.';
  }
  if (model.state === 'stale') {
    return 'These events are stale and should not be treated as current.';
  }
  if (model.state === 'partial') {
    return 'Coverage is partial; material events may be missing.';
  }
  return null;
}

function normalizeEvent(input: unknown, fallbackState: IntelligenceDisplayState): NewsEventModel | null {
  const event = asRecord(input);
  const eventStatus = asString(event.event_status);
  const sourceQuality = asString(event.source_quality);
  const eventId = safeText(event.event_id, 200);
  const headline = safeText(event.canonical_headline, 500);

  if (
    !eventId
    || !headline
    || event.quarantined === true
    || !DISPLAYABLE_EVENT_STATUSES.has(eventStatus as NewsEventModel['eventStatus'])
    || !DISPLAYABLE_SOURCE_QUALITIES.has(sourceQuality as NewsEventModel['sourceQuality'])
  ) {
    return null;
  }

  const metadata = asRecord(event.provider_metadata);
  const freshness = asRecord(event.freshness);
  const state = resolveEventState(
    asString(metadata.provider_mode),
    asString(freshness.state),
    fallbackState,
  );
  if (state === 'unavailable') {
    return null;
  }

  return {
    id: eventId,
    headline,
    summary: safeText(event.source_summary, 700),
    sourceName: safeText(event.source_name, 200) ?? 'Source unavailable',
    sourceQuality: sourceQuality as NewsEventModel['sourceQuality'],
    publishedAt: asIsoDate(event.published_at),
    eventStatus: eventStatus as NewsEventModel['eventStatus'],
    eventType: safeText(event.event_type, 120),
    materiality: normalizeMateriality(event.materiality),
    affectedEntities: normalizeAffectedEntities(event.affected_entities),
    reactionSummary: safeText(asRecord(event.reaction).summary, 700),
    evidenceIds: stringList(event.evidence_ids, 20, 200),
    state,
  };
}

function resolveNewsState({
  status,
  providerMode,
  providerState,
  freshnessState,
  hasTestEvent,
}: {
  status: NewsServiceStatus;
  providerMode: string | null;
  providerState: string | null;
  freshnessState: string | null;
  hasTestEvent: boolean;
}): IntelligenceDisplayState {
  if (status === 'failed') return 'failed';
  if (
    status === 'unavailable'
    || providerMode === 'unavailable'
    || providerState === 'unavailable'
    || freshnessState === 'unavailable'
  ) return 'unavailable';
  if (providerMode === 'test' || providerState === 'test' || freshnessState === 'test' || hasTestEvent) return 'test';
  if (status === 'stale' || providerState === 'stale' || freshnessState === 'stale') return 'stale';
  if (
    status === 'partial'
    || providerState === 'partial'
    || providerState === 'mixed'
    || freshnessState === 'partial'
    || freshnessState === 'mixed'
  ) return 'partial';
  if (providerMode === 'cached' || providerState === 'cached' || freshnessState === 'cached') return 'cached';
  if (providerState === 'delayed' || freshnessState === 'delayed') return 'delayed';
  if (status === 'complete' && providerMode === 'live' && providerState === 'live' && freshnessState === 'live') return 'live';
  return 'unavailable';
}

function resolveEventState(
  providerMode: string | null,
  freshnessState: string | null,
  fallbackState: IntelligenceDisplayState,
): NewsEventModel['state'] {
  if (providerMode === 'unavailable' || freshnessState === 'unavailable') return 'unavailable';
  if (providerMode === 'test' || freshnessState === 'test') return 'test';
  if (freshnessState === 'stale') return 'stale';
  if (freshnessState === 'partial' || freshnessState === 'mixed') return 'partial';
  if (providerMode === 'cached' || freshnessState === 'cached') return 'cached';
  if (freshnessState === 'delayed') return 'delayed';
  if (providerMode === 'live' && freshnessState === 'live') return 'live';
  return fallbackState === 'failed' || fallbackState === 'daily_only' ? 'unavailable' : fallbackState;
}

function isTestEvent(input: unknown): boolean {
  const event = asRecord(input);
  const metadata = asRecord(event.provider_metadata);
  const freshness = asRecord(event.freshness);
  return asString(metadata.provider_mode) === 'test' || asString(freshness.state) === 'test';
}

function normalizeStatus(value: unknown): NewsServiceStatus {
  const status = asString(value);
  return NEWS_STATUSES.has(status as NewsServiceStatus) ? status as NewsServiceStatus : 'unavailable';
}

function normalizeMateriality(value: unknown): NewsEventModel['materiality'] {
  const materiality = asRecord(value);
  return {
    market: boundedScore(materiality.market_materiality),
    entity: boundedScore(materiality.entity_materiality),
    user: boundedScore(materiality.user_relevance),
  };
}

function boundedScore(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value)
    ? Math.max(0, Math.min(100, Math.round(value)))
    : null;
}

function normalizeAffectedEntities(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((item) => {
    const entity = asRecord(item);
    const label = safeText(entity.symbol, 20) ?? safeText(entity.display_name, 200);
    return label ? [label] : [];
  }).slice(0, 8);
}

function normalizeContradictions(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((item) => {
    const statement = safeText(asRecord(item).statement, 700);
    return statement ? [statement] : [];
  }).slice(0, 5);
}

function asRecord(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {};
}

function asString(value: unknown): string | null {
  return typeof value === 'string' ? value.toLowerCase() : null;
}

function safeText(value: unknown, maxLength: number): string | null {
  if (typeof value !== 'string') return null;
  const clean = value
    .replace(/\[([^\]]+)\]\([^\s)]+\)/g, '$1')
    .replace(/<[^>]*>/g, ' ')
    .replace(/[\u0000-\u001F\u007F]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  if (!clean) return null;
  return clean.length > maxLength ? `${clean.slice(0, Math.max(0, maxLength - 1)).trimEnd()}…` : clean;
}

function stringList(value: unknown, maxItems: number, maxLength: number): string[] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((item) => {
    const text = safeText(item, maxLength);
    return text ? [text] : [];
  }).slice(0, maxItems);
}

function asIsoDate(value: unknown): string | null {
  if (typeof value !== 'string' || !value.trim()) return null;
  return Number.isNaN(Date.parse(value)) ? null : value;
}
