import { intelligenceStateLabel } from '@/features/context-intelligence/newsIntelligenceNormalizer';
import type {
  IntelligenceDisplayState,
  SessionConsumerPresentation,
  SessionNarrativeDto,
  SessionNarrativeModel,
} from '@/features/context-intelligence/types';

export function normalizeSessionNarrative(input: unknown): SessionNarrativeModel {
  const dto = asRecord(input) as SessionNarrativeDto;
  const narrative = asRecord(dto.narrative);
  const provenance = asRecord(dto.provenance);
  const state = resolveSessionState({
    status: lower(dto.status),
    availability: lower(dto.availability),
    dataMode: lower(dto.data_mode),
    freshness: lower(narrative.freshness),
    testDataDetected: provenance.test_data_detected === true,
  });

  return {
    state,
    headline: safeText(narrative.headline, 700) ?? defaultHeadline(state),
    claims: normalizeClaims(narrative.claims),
    caveats: dedupe([
      ...stringList(narrative.caveats, 8, 500),
      ...stringList(dto.limitations, 8, 500),
    ]),
    confidence: normalizeConfidence(narrative.confidence),
    provider: safeText(dto.provider, 120),
    asOf: asIsoDate(dto.as_of),
    latestDailySession: asDate(dto.latest_daily_session),
    causalityDisclosure: safeText(narrative.causality_disclosure, 700),
  };
}

export function buildSessionConsumerPresentation(
  model: SessionNarrativeModel,
): SessionConsumerPresentation {
  return {
    state: model.state,
    stateLabel: intelligenceStateLabel(model.state),
    headline: model.headline,
    supportingText: sessionSupportingText(model),
  };
}

function resolveSessionState({
  status,
  availability,
  dataMode,
  freshness,
  testDataDetected,
}: {
  status: string | null;
  availability: string | null;
  dataMode: string | null;
  freshness: string | null;
  testDataDetected: boolean;
}): IntelligenceDisplayState {
  if (status === 'unavailable' || availability === 'unavailable' || dataMode === 'unavailable') return 'unavailable';
  if (testDataDetected || freshness === 'test') return 'test';
  if (status === 'daily_only' || availability === 'daily_only' || dataMode === 'daily_only') return 'daily_only';
  if (freshness === 'unavailable') return 'unavailable';
  if (status === 'partial' || availability === 'partial' || freshness === 'partial' || freshness === 'mixed') return 'partial';
  if (freshness === 'stale') return 'stale';
  if (freshness === 'cached') return 'cached';
  if (freshness === 'delayed') return 'delayed';
  if (
    status === 'complete'
    && availability === 'available'
    && (dataMode === 'intraday_5m' || dataMode === 'intraday_15m')
    && freshness === 'live'
  ) return 'live';
  return 'unavailable';
}

function sessionSupportingText(model: SessionNarrativeModel): string | null {
  if (model.state === 'daily_only') {
    return model.latestDailySession
      ? `Intraday context is unavailable. Latest daily session: ${model.latestDailySession}.`
      : 'Intraday context is unavailable; only daily context is available.';
  }
  if (model.state === 'unavailable') {
    return model.caveats[0] ?? 'Session context is currently unavailable.';
  }
  if (model.state === 'test') {
    return 'Test data is isolated and is not live session intelligence.';
  }
  if (model.state === 'stale') {
    return 'Session context is stale and should not be treated as current.';
  }
  if (model.state === 'partial') {
    return model.caveats[0] ?? 'Session coverage is partial.';
  }
  return model.claims[0] ?? model.caveats[0] ?? null;
}

function defaultHeadline(state: IntelligenceDisplayState): string {
  if (state === 'daily_only') return 'Daily market context only';
  if (state === 'test') return 'Test session context';
  if (state === 'failed') return 'Session context failed';
  if (state === 'unavailable') return 'Session context unavailable';
  return 'Session context';
}

function normalizeClaims(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((claim) => {
    const text = safeText(asRecord(claim).text, 700);
    return text ? [text] : [];
  }).slice(0, 5);
}

function normalizeConfidence(value: unknown): SessionNarrativeModel['confidence'] {
  const normalized = lower(value);
  return normalized === 'high' || normalized === 'moderate' || normalized === 'limited'
    ? normalized
    : null;
}

function dedupe(values: string[]): string[] {
  return [...new Set(values)];
}

function asRecord(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {};
}

function lower(value: unknown): string | null {
  return typeof value === 'string' ? value.toLowerCase() : null;
}

function safeText(value: unknown, maxLength: number): string | null {
  if (typeof value !== 'string') return null;
  const clean = value
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

function asDate(value: unknown): string | null {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
  return value;
}
