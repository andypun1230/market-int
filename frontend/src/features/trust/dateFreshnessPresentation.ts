export type DatePresentationKind =
  | 'updated'
  | 'cached'
  | 'last-successful-update'
  | 'evidence-through'
  | 'generated';

export type DatePresentationOptions = {
  kind?: DatePresentationKind;
  locale?: string;
  now?: Date;
  timeZone?: string;
};

export function dateFreshnessLabel(value?: string | null, options: DatePresentationOptions = {}) {
  const parsed = parseDate(value);
  const kind = options.kind ?? 'updated';
  if (!parsed) return unavailableLabel(kind);
  if (kind === 'evidence-through') return `Evidence through ${formatLocalizedDate(parsed, options)}`;
  if (kind === 'generated') return `Generated ${formatLocalizedDateTime(parsed, options)}`;
  if (kind === 'cached') return `Cached from ${formatLocalizedTime(parsed, options)}`;
  if (kind === 'last-successful-update') return `Last successful update ${relativeUpdate(parsed, options)}`;
  return `Updated ${relativeUpdate(parsed, options)}`;
}

export function formatLocalizedDate(value?: string | Date | null, options: Omit<DatePresentationOptions, 'kind'> = {}) {
  const parsed = parseDate(value);
  if (!parsed) return 'date unavailable';
  return new Intl.DateTimeFormat(options.locale, {
    dateStyle: 'medium',
    timeZone: options.timeZone,
  }).format(parsed);
}

export function formatLocalizedDateTime(value?: string | Date | null, options: Omit<DatePresentationOptions, 'kind'> = {}) {
  const parsed = parseDate(value);
  if (!parsed) return 'time unavailable';
  return new Intl.DateTimeFormat(options.locale, {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: options.timeZone,
  }).format(parsed);
}

function formatLocalizedTime(value: Date, options: Omit<DatePresentationOptions, 'kind'>) {
  return new Intl.DateTimeFormat(options.locale, {
    timeStyle: 'short',
    timeZone: options.timeZone,
  }).format(value);
}

function relativeUpdate(value: Date, options: Omit<DatePresentationOptions, 'kind'>) {
  const now = options.now ?? new Date();
  const elapsedMinutes = Math.max(0, Math.floor((now.getTime() - value.getTime()) / 60_000));
  if (elapsedMinutes < 1) return 'just now';
  if (elapsedMinutes < 60) return `${elapsedMinutes} minute${elapsedMinutes === 1 ? '' : 's'} ago`;
  const elapsedHours = Math.floor(elapsedMinutes / 60);
  if (elapsedHours < 24) return `${elapsedHours} hour${elapsedHours === 1 ? '' : 's'} ago`;
  if (elapsedHours < 48) return 'yesterday';
  return `on ${formatLocalizedDate(value, options)}`;
}

function parseDate(value?: string | Date | null) {
  if (value instanceof Date) return Number.isNaN(value.getTime()) ? null : value;
  if (!value?.trim()) return null;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function unavailableLabel(kind: DatePresentationKind) {
  if (kind === 'evidence-through') return 'Evidence date unavailable';
  if (kind === 'generated') return 'Generation time unavailable';
  if (kind === 'cached') return 'Cache time unavailable';
  if (kind === 'last-successful-update') return 'Last successful update unavailable';
  return 'Last update unavailable';
}
