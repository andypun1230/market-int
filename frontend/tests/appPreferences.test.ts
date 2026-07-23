import { DEFAULT_PREFERENCES, migratePreferences } from '../src/features/preferences/appPreferencesModel';

function assert(condition: unknown, message: string) {
  if (!condition) {
    throw new Error(message);
  }
}

function run() {
  const defaults = DEFAULT_PREFERENCES;
  assert(defaults.version === 2, 'default preferences use schema version 2');
  assert(defaults.appearance.theme === 'dark', 'dark theme is the default supported theme');
  assert(defaults.appearance.reduceMotion === false, 'motion is enabled by default');

  const migrated = migratePreferences({
    appearance: { reduceMotion: true, theme: 'system' },
    profile: { displayName: 'Andy' },
  });

  assert(migrated.appearance.reduceMotion === true, 'reduce motion preference is preserved');
  assert(migrated.appearance.theme === 'dark', 'unavailable legacy system theme is normalized to the supported beta theme');
  assert(migrated.profile.displayName === 'Andy', 'profile display name is preserved');

  const invalid = migratePreferences(null);
  assert(invalid.profile.displayName === defaults.profile.displayName, 'invalid stored preferences reset to defaults');
}

run();
