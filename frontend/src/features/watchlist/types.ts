import type { WatchlistSummaryItem } from '@/types/market';

export type WatchlistGroup =
  | 'needs_attention'
  | 'high_priority'
  | 'momentum'
  | 'watching'
  | 'data_unavailable';

export type WatchlistSignalType =
  | 'breakout'
  | 'near_breakout'
  | 'strong_momentum'
  | 'relative_strength'
  | 'volume_surge'
  | 'new_high'
  | 'earnings_soon'
  | 'major_news'
  | 'rating_upgrade'
  | 'lost_support'
  | 'lost_ema'
  | 'weak_momentum'
  | 'earnings_risk'
  | 'stale_data'
  | 'watching'
  | 'unavailable';

export type WatchlistSeverity = 'positive' | 'neutral' | 'warning' | 'critical';

export type WatchlistDataStatus = 'live' | 'test' | 'cached' | 'stale' | 'mock' | 'unavailable';

export type WatchlistClassification = {
  dataStatus: WatchlistDataStatus;
  group: WatchlistGroup;
  primarySignal: WatchlistSignalType;
  reason: string;
  score: number | null;
  secondarySignals: WatchlistSignalType[];
  severity: WatchlistSeverity;
  ticker: string;
};

export type ClassifiedWatchlistItem = {
  classification: WatchlistClassification;
  item: WatchlistSummaryItem;
  originalIndex: number;
};

export type WatchlistSortMode =
  | 'smartPriority'
  | 'dailyGain'
  | 'dailyLoss'
  | 'momentum'
  | 'relativeStrength'
  | 'volume'
  | 'nearHigh'
  | 'earningsDate'
  | 'manualOrder'
  | 'alphabetical';

export type SectorThemeGroup =
  | 'leading'
  | 'improving'
  | 'watching'
  | 'weakening'
  | 'data_unavailable';

export type SectorThemeItemType = 'sector' | 'theme';

export type SectorThemePrimaryStatus =
  | 'leading'
  | 'improving'
  | 'neutral'
  | 'weakening'
  | 'lagging'
  | 'unavailable';

export type SectorThemeDataStatus = 'live' | 'test' | 'cached' | 'stale' | 'mock' | 'unavailable';

export type SectorThemeClassification = {
  dataStatus: SectorThemeDataStatus;
  group: SectorThemeGroup;
  id: string;
  name: string;
  period: string;
  primaryStatus: SectorThemePrimaryStatus;
  reason: string;
  returnPercent: number | null;
  score: number | null;
  type: SectorThemeItemType;
};

export type SectorThemeTypeFilter = 'all' | 'sector' | 'theme';

export type SectorThemeSortMode =
  | 'smartPriority'
  | 'recent'
  | 'topReturn'
  | 'weakest'
  | 'momentum'
  | 'alphabetical';
