import type { PresentedAlert } from '@/components/ui/AlertList';

export function presentSnapshotAlerts(
  alerts: Record<string, unknown>[],
  fallbackEntity: string,
): PresentedAlert[] {
  return alerts.map((alert, index) => {
    const entity = firstText(alert, 'display_name', 'sector_name', 'theme_name', 'sector_id', 'theme_id', 'entity_id') ?? fallbackEntity;
    const previous = firstText(alert, 'previous_classification', 'previous_quadrant', 'previous_state');
    const current = firstText(alert, 'current_classification', 'current_quadrant', 'current_state');
    const reason = firstText(alert, 'message', 'reason', 'explanation', 'type') ?? 'Snapshot state changed.';
    const transition = previous && current ? `${humanize(previous)} → ${humanize(current)}` : reason;
    const asOf = firstText(alert, 'as_of', 'market_date', 'created_at');
    return {
      id: firstText(alert, 'id', 'alert_id') ?? `${fallbackEntity}-${index}`,
      message: transition,
      metadata: [asOf, previous && current && reason !== transition ? reason : null].filter(Boolean).join(' · ') || null,
      title: humanize(entity),
    };
  });
}

function firstText(record: Record<string, unknown>, ...keys: string[]) {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === 'string' && value.trim()) return value.trim();
    if (typeof value === 'number' && Number.isFinite(value)) return String(value);
  }
  return null;
}

function humanize(value: string) {
  return value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
}
