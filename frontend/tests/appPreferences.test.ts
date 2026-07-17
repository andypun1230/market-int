import { DEFAULT_PREFERENCES, migratePreferences } from '../src/features/preferences/appPreferencesModel';

function assert(condition: unknown, message: string) {
  if (!condition) {
    throw new Error(message);
  }
}

function run() {
  const defaults = DEFAULT_PREFERENCES;
  assert(defaults.version === 1, 'default preferences use schema version 1');
  assert(defaults.appearance.theme === 'dark', 'dark theme is the default supported theme');
  assert(defaults.dataUsage.refreshMode === 'manual', 'manual refresh is the default data mode');
  assert(defaults.notifications.dailyReportReady === true, 'daily report notification preference defaults on');

  const migrated = migratePreferences({
    appearance: { accentColor: 'purple', textSize: 'large' },
    dataUsage: { lowDataMode: true, refreshMode: '30m' },
    notifications: { watchlistPriceAlerts: true },
    profile: { displayName: 'Andy', investorStyle: 'Aggressive' },
  });

  assert(migrated.appearance.accentColor === 'purple', 'accent color preference is preserved');
  assert(migrated.appearance.textSize === 'large', 'text size preference is preserved');
  assert(migrated.appearance.theme === 'dark', 'missing appearance fields fall back safely');
  assert(migrated.dataUsage.lowDataMode === true, 'low data mode preference is preserved');
  assert(migrated.dataUsage.refreshMode === '30m', 'refresh mode preference is preserved');
  assert(migrated.notifications.watchlistPriceAlerts === true, 'notification preference is preserved');
  assert(migrated.profile.displayName === 'Andy', 'profile display name is preserved');
  assert(migrated.profile.investorStyle === 'Aggressive', 'profile investor style is preserved');

  const invalid = migratePreferences(null);
  assert(invalid.profile.displayName === defaults.profile.displayName, 'invalid stored preferences reset to defaults');
}

run();
