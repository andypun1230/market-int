import { BETA_SETTINGS_REGISTRY, validateBetaSettingsRegistry } from '../src/architecture/settingsBetaRegistry';
import { DEFAULT_PREFERENCES, migratePreferences } from '../src/features/preferences/appPreferencesModel';

function assert(condition: unknown, message: string) {
  if (!condition) throw new Error(message);
}

const result = validateBetaSettingsRegistry();
assert(result.valid, 'beta settings registry has no enabled no-ops, enabled planned settings, visible obsolete settings, or unfinished trust controls');
assert(BETA_SETTINGS_REGISTRY.every((entry) => entry.consumer.trim().length > 0), 'every registry entry names its downstream consumer or explicit unavailable boundary');

const migratedLegacySystem = migratePreferences({
  appearance: { reduceMotion: true, theme: 'system' },
  profile: { displayName: 'Restart User' },
});
assert(migratedLegacySystem.appearance.theme === 'dark', 'legacy unavailable system-theme selections normalize to the beta theme');
assert(migratedLegacySystem.appearance.reduceMotion === true, 'reduce-motion survives preference migration and restart loading');
assert(migratedLegacySystem.profile.displayName === 'Restart User', 'local display name survives preference migration and restart loading');
assert(DEFAULT_PREFERENCES.appearance.theme === 'dark', 'beta starts in the supported theme');

console.log('PASS Stage 11.3 beta settings readiness contracts');
