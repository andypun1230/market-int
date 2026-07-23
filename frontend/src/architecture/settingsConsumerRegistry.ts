import type { AppPreferences } from '@/features/preferences/appPreferencesModel';

export type PreferencePath = 'appearance.reduceMotion' | 'appearance.theme' | 'profile.displayName';

export const SETTINGS_CONSUMER_REGISTRY = {
  'appearance.reduceMotion': {
    consumers: ['useReducedMotion', 'AppScreen transitions', 'DetailModal', 'AnimatedSplashOverlay'],
    owner: 'Appearance settings',
  },
  'appearance.theme': {
    consumers: ['Root Expo Router ThemeProvider'],
    owner: 'Appearance settings',
  },
  'profile.displayName': {
    consumers: ['More profile destination summary'],
    owner: 'Profile settings',
  },
} as const satisfies Record<PreferencePath, { consumers: readonly string[]; owner: string }>;

export const ACTIVE_PREFERENCE_PATHS = [
  'appearance.reduceMotion',
  'appearance.theme',
  'profile.displayName',
] as const satisfies readonly PreferencePath[];

export function validatePreferenceShape(preferences: AppPreferences) {
  const actualPaths = [
    ...Object.keys(preferences.appearance).map((key) => `appearance.${key}`),
    ...Object.keys(preferences.profile).map((key) => `profile.${key}`),
  ].sort();
  const registeredPaths = [...ACTIVE_PREFERENCE_PATHS].sort();
  return actualPaths.join('|') === registeredPaths.join('|')
    && ACTIVE_PREFERENCE_PATHS.every((path) => SETTINGS_CONSUMER_REGISTRY[path].consumers.length > 0);
}
