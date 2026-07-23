export type ConfidenceQualifier = 'confidence' | 'evidence confidence' | 'evidence quality';
export type EvidenceFreshnessState = 'live' | 'cached' | 'stale' | 'test' | 'mock' | 'partial' | 'mixed' | 'delayed' | 'unavailable';

export function confidenceLabel({
  confidence,
  fallback,
  qualifier,
}: {
  confidence?: number | null;
  fallback?: string | null;
  qualifier?: ConfidenceQualifier;
}) {
  if (typeof confidence === 'number' && Number.isFinite(confidence)) {
    const inferredQualifier = qualifier
      ?? (fallback?.toLowerCase().includes('evidence quality') ? 'evidence quality'
        : fallback?.toLowerCase().includes('evidence confidence') ? 'evidence confidence'
          : 'confidence');
    return `${Math.round(confidence)}/100 ${inferredQualifier}`;
  }
  return fallback?.trim() || 'Confidence unavailable';
}

export function freshnessLabel(value?: string | null) {
  const trimmed = value?.trim();
  if (!trimmed) return 'Last update unavailable';
  if (/^(updated|generated|evidence through|as of|freshness|displayed analysis|\d+ items? require)/i.test(trimmed)) {
    return formatEmbeddedTimestamp(trimmed);
  }
  const parsed = new Date(trimmed);
  if (!Number.isNaN(parsed.getTime())) return `Updated ${formatDateTime(parsed)}`;
  return trimmed;
}

export function availabilityLabel(value?: string | null) {
  if (!value) return 'Unavailable';
  return titleCaseDelimited(value);
}

export function providerLabel(value?: string | null) {
  const normalized = value?.trim().toLowerCase();
  if (!normalized) return 'Provider unavailable';
  if (normalized === 'finnhub') return 'Finnhub';
  if (normalized === 'polygon') return 'Polygon';
  if (normalized === 'openai') return 'OpenAI';
  return titleCaseDelimited(normalized);
}

export function evidenceFreshnessLabel(state: EvidenceFreshnessState) {
  if (state === 'live') return 'Live evidence';
  if (state === 'cached') return 'Cached evidence';
  if (state === 'stale') return 'Stale evidence';
  if (state === 'test' || state === 'mock') return 'Test evidence';
  if (state === 'partial' || state === 'mixed') return 'Partial evidence';
  if (state === 'delayed') return 'Delayed evidence';
  return 'Evidence unavailable';
}

function formatEmbeddedTimestamp(value: string) {
  const match = value.match(/^(Updated|Generated)\s+(.+)$/i);
  if (!match) return value;
  const parsed = new Date(match[2]);
  return Number.isNaN(parsed.getTime()) ? value : `${match[1]} ${formatDateTime(parsed)}`;
}

function formatDateTime(value: Date) {
  const includesTime = value.getUTCHours() !== 0 || value.getUTCMinutes() !== 0 || value.getUTCSeconds() !== 0;
  return new Intl.DateTimeFormat(undefined, includesTime
    ? { dateStyle: 'medium', timeStyle: 'short' }
    : { dateStyle: 'medium' }).format(value);
}

function titleCaseDelimited(value: string) {
  return value.split(/[_-]/).map((part) => part ? part[0].toUpperCase() + part.slice(1) : part).join(' ');
}
