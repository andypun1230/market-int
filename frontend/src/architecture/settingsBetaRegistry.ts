export type BetaSettingsClassification =
  | 'complete'
  | 'partially_implemented_but_useful'
  | 'planned_for_later'
  | 'obsolete';

export type BetaSettingsEntry = {
  classification: BetaSettingsClassification;
  consumer: string;
  enabledInBeta: boolean;
  id: string;
  persistence: 'local' | 'action' | 'none';
  surface: string;
  trustSensitive?: boolean;
  visibleInBeta: boolean;
  wording?: string;
};

export const BETA_SETTINGS_REGISTRY: readonly BetaSettingsEntry[] = [
  { id: 'appearance.dark', surface: 'Appearance', classification: 'complete', enabledInBeta: false, visibleInBeta: true, persistence: 'none', consumer: 'Application dark visual system', wording: 'Selected' },
  { id: 'appearance.system', surface: 'Appearance', classification: 'planned_for_later', enabledInBeta: false, visibleInBeta: true, persistence: 'none', consumer: 'None until complete light-mode support ships', wording: 'Not available in beta' },
  { id: 'accessibility.reduceMotion', surface: 'Appearance, Accessibility', classification: 'complete', enabledInBeta: true, visibleInBeta: true, persistence: 'local', consumer: 'useReducedMotion animation policy', trustSensitive: true },
  { id: 'accessibility.colorMeaning', surface: 'Accessibility', classification: 'complete', enabledInBeta: false, visibleInBeta: true, persistence: 'none', consumer: 'Shared badge and state-presentation contracts' },
  { id: 'language.english', surface: 'Language & Region', classification: 'complete', enabledInBeta: false, visibleInBeta: true, persistence: 'none', consumer: 'Application copy' },
  { id: 'language.traditionalChinese', surface: 'Language & Region', classification: 'planned_for_later', enabledInBeta: false, visibleInBeta: true, persistence: 'none', consumer: 'None until translations ship', wording: 'Not available in beta' },
  { id: 'notifications.push', surface: 'Notifications, More', classification: 'planned_for_later', enabledInBeta: false, visibleInBeta: true, persistence: 'none', consumer: 'None until delivery service ships', wording: 'Not available in beta', trustSensitive: true },
  { id: 'profile.displayName', surface: 'Profile, More', classification: 'partially_implemented_but_useful', enabledInBeta: true, visibleInBeta: true, persistence: 'local', consumer: 'More profile destination summary', wording: 'Local display identity; no account sync' },
  { id: 'dataUsage.clearMarketDataCache', surface: 'Data Usage', classification: 'complete', enabledInBeta: true, visibleInBeta: true, persistence: 'action', consumer: 'Frontend request cache and backend market-data cache invalidation', trustSensitive: true },
  { id: 'dataSources.status', surface: 'Settings, About, Data Sources, More', classification: 'complete', enabledInBeta: true, visibleInBeta: true, persistence: 'none', consumer: 'Canonical Data Sources route using UserFacingDataStateProvider', trustSensitive: true },
  { id: 'privacy.disclosure', surface: 'Privacy', classification: 'complete', enabledInBeta: true, visibleInBeta: true, persistence: 'none', consumer: 'Canonical Privacy route', trustSensitive: true },
  { id: 'about.systemInformation', surface: 'About', classification: 'complete', enabledInBeta: true, visibleInBeta: true, persistence: 'none', consumer: 'Canonical About route using UserFacingDataStateProvider' },
  { id: 'scenario.testControls', surface: 'Settings, About, Data Sources', classification: 'partially_implemented_but_useful', enabledInBeta: false, visibleInBeta: false, persistence: 'action', consumer: 'Development-only deterministic fixture endpoints', wording: 'Development only', trustSensitive: true },
  { id: 'future.userAccounts', surface: 'More', classification: 'planned_for_later', enabledInBeta: false, visibleInBeta: true, persistence: 'none', consumer: 'None until accounts ship', wording: 'Not available in beta', trustSensitive: true },
  { id: 'future.subscription', surface: 'More', classification: 'planned_for_later', enabledInBeta: false, visibleInBeta: true, persistence: 'none', consumer: 'None until subscriptions ship', wording: 'Not available in beta', trustSensitive: true },
] as const;

export function validateBetaSettingsRegistry(entries: readonly BetaSettingsEntry[] = BETA_SETTINGS_REGISTRY) {
  const duplicateIds = entries.filter((entry, index) => entries.findIndex((candidate) => candidate.id === entry.id) !== index);
  const enabledNoOps = entries.filter((entry) => entry.visibleInBeta && entry.enabledInBeta && !entry.consumer.trim());
  const enabledPlanned = entries.filter((entry) => entry.visibleInBeta && entry.enabledInBeta && entry.classification === 'planned_for_later');
  const dishonestPlanned = entries.filter((entry) => entry.visibleInBeta && entry.classification === 'planned_for_later' && entry.wording !== 'Not available in beta');
  const visibleObsolete = entries.filter((entry) => entry.visibleInBeta && entry.classification === 'obsolete');
  const unfinishedTrustControls = entries.filter((entry) => entry.visibleInBeta && entry.enabledInBeta && entry.trustSensitive && entry.classification !== 'complete');
  return {
    duplicateIds,
    enabledNoOps,
    enabledPlanned,
    dishonestPlanned,
    visibleObsolete,
    unfinishedTrustControls,
    valid: [duplicateIds, enabledNoOps, enabledPlanned, dishonestPlanned, visibleObsolete, unfinishedTrustControls].every((items) => items.length === 0),
  };
}
