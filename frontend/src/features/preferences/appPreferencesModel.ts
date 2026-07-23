export type AppearancePreferences = {
  reduceMotion: boolean;
  theme: 'system' | 'dark';
};

export type LocalProfilePreferences = {
  displayName: string;
};

export type AppPreferences = {
  appearance: AppearancePreferences;
  profile: LocalProfilePreferences;
  version: 2;
};

export const DEFAULT_PREFERENCES: AppPreferences = {
  appearance: {
    reduceMotion: false,
    theme: 'dark',
  },
  profile: {
    displayName: 'Guest User',
  },
  version: 2,
};

export function migratePreferences(value: unknown): AppPreferences {
  if (!value || typeof value !== 'object') {
    return DEFAULT_PREFERENCES;
  }
  const parsed = value as Partial<AppPreferences>;
  return mergePreferences(DEFAULT_PREFERENCES, parsed);
}

export function mergePreferences(base: AppPreferences, patch: Partial<AppPreferences>): AppPreferences {
  return {
    appearance: {
      reduceMotion: typeof patch.appearance?.reduceMotion === 'boolean'
        ? patch.appearance.reduceMotion
        : base.appearance.reduceMotion,
      theme: patch.appearance?.theme === 'system' || patch.appearance?.theme === 'dark'
        ? patch.appearance.theme
        : base.appearance.theme,
    },
    profile: {
      displayName: typeof patch.profile?.displayName === 'string'
        ? patch.profile.displayName
        : base.profile.displayName,
    },
    version: 2,
  };
}
