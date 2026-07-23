import type { AppIconName } from '@/components/ui/AppIcon';

export type StatePresentationType =
  | 'empty'
  | 'no_search_results'
  | 'unavailable'
  | 'partial'
  | 'failed'
  | 'maintenance'
  | 'permission_restricted'
  | 'not_generated'
  | 'no_saved_entities'
  | 'no_qualifying_results';

export const STATE_PRESENTATION_REGISTRY: Record<StatePresentationType, {
  accessibilityPrefix: string;
  icon: AppIconName;
  tone: 'neutral' | 'accent' | 'warning' | 'danger';
}> = {
  empty: { accessibilityPrefix: 'Empty', icon: 'neutralDot', tone: 'neutral' },
  no_search_results: { accessibilityPrefix: 'No search results', icon: 'search', tone: 'neutral' },
  unavailable: { accessibilityPrefix: 'Unavailable', icon: 'info', tone: 'neutral' },
  partial: { accessibilityPrefix: 'Partial data', icon: 'warning', tone: 'warning' },
  failed: { accessibilityPrefix: 'Failed', icon: 'warning', tone: 'danger' },
  maintenance: { accessibilityPrefix: 'Maintenance', icon: 'info', tone: 'neutral' },
  permission_restricted: { accessibilityPrefix: 'Access restricted', icon: 'info', tone: 'neutral' },
  not_generated: { accessibilityPrefix: 'Report not generated', icon: 'pending', tone: 'accent' },
  no_saved_entities: { accessibilityPrefix: 'No saved entities', icon: 'savedOutline', tone: 'neutral' },
  no_qualifying_results: { accessibilityPrefix: 'No qualifying results', icon: 'filter', tone: 'neutral' },
};
