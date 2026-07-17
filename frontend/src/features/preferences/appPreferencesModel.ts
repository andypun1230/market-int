export type AppearancePreferences = {
  accentColor: 'blue' | 'green' | 'purple' | 'orange';
  reduceMotion: boolean;
  textSize: 'small' | 'default' | 'large';
  theme: 'system' | 'dark';
};

export type LanguagePreferences = {
  currency: 'USD' | 'HKD';
  language: 'en';
  marketTimeDisplay: 'local' | 'et';
  numberFormat: 'comma';
  region: 'HK' | 'US';
};

export type DataUsagePreferences = {
  autoDownloadReports: 'off' | 'wifi' | 'always';
  autoLoadCharts: boolean;
  backgroundRefresh: boolean;
  lowDataMode: boolean;
  refreshMode: 'manual' | '15m' | '30m' | '60m';
  wifiOnly: boolean;
};

export type NotificationPreferences = {
  dailyReportReady: boolean;
  majorMacroEvents: boolean;
  marketRegimeChanges: boolean;
  notificationTime: string;
  quietHours: boolean;
  riskLevelChanges: boolean;
  sectorLeadershipChanges: boolean;
  watchlistPriceAlerts: boolean;
};

export type LocalProfilePreferences = {
  defaultMarket: 'US';
  displayName: string;
  experienceLevel: 'Beginner' | 'Intermediate' | 'Advanced';
  investorStyle: 'Conservative' | 'Balanced' | 'Aggressive';
  preferredReportFocus: 'Market Overview' | 'Watchlist' | 'Risk' | 'Sectors';
  preferredWatchlist: string;
};

export type AppPreferences = {
  appearance: AppearancePreferences;
  dataUsage: DataUsagePreferences;
  language: LanguagePreferences;
  notifications: NotificationPreferences;
  profile: LocalProfilePreferences;
  version: 1;
};

export const DEFAULT_PREFERENCES: AppPreferences = {
  appearance: {
    accentColor: 'blue',
    reduceMotion: false,
    textSize: 'default',
    theme: 'dark',
  },
  dataUsage: {
    autoDownloadReports: 'off',
    autoLoadCharts: true,
    backgroundRefresh: false,
    lowDataMode: false,
    refreshMode: 'manual',
    wifiOnly: false,
  },
  language: {
    currency: 'USD',
    language: 'en',
    marketTimeDisplay: 'local',
    numberFormat: 'comma',
    region: 'HK',
  },
  notifications: {
    dailyReportReady: true,
    majorMacroEvents: false,
    marketRegimeChanges: true,
    notificationTime: '08:30',
    quietHours: true,
    riskLevelChanges: true,
    sectorLeadershipChanges: true,
    watchlistPriceAlerts: false,
  },
  profile: {
    defaultMarket: 'US',
    displayName: 'Guest User',
    experienceLevel: 'Intermediate',
    investorStyle: 'Balanced',
    preferredReportFocus: 'Market Overview',
    preferredWatchlist: 'Default Watchlist',
  },
  version: 1,
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
    appearance: { ...base.appearance, ...(patch.appearance ?? {}) },
    dataUsage: { ...base.dataUsage, ...(patch.dataUsage ?? {}) },
    language: { ...base.language, ...(patch.language ?? {}) },
    notifications: { ...base.notifications, ...(patch.notifications ?? {}) },
    profile: { ...base.profile, ...(patch.profile ?? {}) },
    version: 1,
  };
}
