import {
  buildNavigationDestination,
  type DestinationId,
  type DestinationInput,
} from '@/architecture/navigationRegistry';

export type CommandCategory =
  | 'Stocks'
  | 'ETFs'
  | 'Indexes'
  | 'Sectors'
  | 'Themes'
  | 'Reports'
  | 'App Features'
  | 'Settings'
  | 'Copilot Suggestions';

export type CommandSourceState = 'live' | 'cached' | 'delayed' | 'test' | 'unavailable';

export type CommandItem = {
  category: CommandCategory;
  id: string;
  keywords: string[];
  metadata: string;
  params?: Record<string, string>;
  pathname: string;
  sourceState?: CommandSourceState;
  title: string;
};

export type ActiveMarketInput = {
  changePercent?: number | null;
  isLive?: boolean | null;
  isStale?: boolean | null;
  fallbackUsed?: boolean | null;
  source?: string | null;
  symbol: string;
};

const SECTORS = [
  ['communication_services', 'Communication Services'],
  ['consumer_discretionary', 'Consumer Discretionary'],
  ['consumer_staples', 'Consumer Staples'],
  ['energy', 'Energy'],
  ['financials', 'Financials'],
  ['health_care', 'Health Care'],
  ['industrials', 'Industrials'],
  ['information_technology', 'Information Technology'],
  ['materials', 'Materials'],
  ['real_estate', 'Real Estate'],
  ['utilities', 'Utilities'],
] as const;

const STOCKS = ['AAPL', 'MSFT', 'NVDA', 'AMZN', 'GOOGL', 'META', 'TSLA', 'JPM'];
const ETFS = ['SPY', 'QQQ', 'IWM', 'DIA', 'XLK', 'XLE', 'XLF'];
const INDEXES = [
  ['SPX', 'S&P 500'],
  ['NDX', 'Nasdaq-100'],
  ['IXIC', 'Nasdaq Composite'],
  ['RUT', 'Russell 2000'],
  ['DJI', 'Dow Jones Industrial Average'],
] as const;

export const COMMAND_CATEGORY_ORDER: CommandCategory[] = [
  'Stocks',
  'ETFs',
  'Indexes',
  'Sectors',
  'Themes',
  'Reports',
  'App Features',
  'Settings',
  'Copilot Suggestions',
];

export const EXPLORE_FEATURE_IDS = [
  'feature-market-overview',
  'feature-market-breadth',
  'feature-sector-rotation',
  'feature-theme-rotation',
  'report-daily',
  'feature-watchlist',
];

export function buildCommandRegistry(): CommandItem[] {
  const stockItems = STOCKS.map((symbol): CommandItem => destinationItem(
    'Stocks', `stock-${symbol}`, symbol, 'Stock Detail', 'stock_detail', { symbol }, [symbol, 'equity', 'stock detail'],
  ));
  const etfItems = ETFS.map((symbol): CommandItem => destinationItem(
    'ETFs', `etf-${symbol}`, symbol, 'ETF Detail', 'stock_detail', { symbol }, [symbol, 'fund', 'etf'],
  ));
  const indexItems = INDEXES.map(([symbol, name]): CommandItem => destinationItem(
    'Indexes', `index-${symbol}`, `${symbol} · ${name}`, 'Market › Indexes', 'market_indexes', {}, [symbol, name, 'index', 'market snapshot'],
  ));
  const sectorItems = SECTORS.map(([id, name]): CommandItem => destinationItem(
    'Sectors', `sector-${id}`, name, 'Sectors › Heatmap', 'sector_detail', { entityId: id, entityName: name }, [name, id.replaceAll('_', ' '), 'sector'],
  ));

  return [
    ...stockItems,
    ...etfItems,
    ...indexItems,
    ...sectorItems,
    destinationItem('Themes', 'theme-cybersecurity', 'Cybersecurity', 'Themes › Heatmap', 'theme_detail', { entityId: 'cybersecurity', entityName: 'Cybersecurity' }),
    destinationItem('Themes', 'theme-memory-storage', 'Memory & Storage', 'Themes › Heatmap', 'theme_detail', { entityId: 'memory_storage', entityName: 'Memory & Storage' }),
    destinationItem('Reports', 'report-daily', 'Daily Market Intelligence', 'Reports › Today', 'report'),
    destinationItem('App Features', 'feature-market-overview', 'Market Overview', 'Market › Overview', 'market_overview'),
    destinationItem('App Features', 'feature-market-health', 'Market Health', 'Market › Health', 'market_health'),
    destinationItem('App Features', 'feature-market-breadth', 'Market Breadth', 'Market › Breadth', 'market_breadth'),
    destinationItem('App Features', 'feature-market-regime', 'Market Regime', 'Market › Decision', 'market_decision'),
    destinationItem('App Features', 'feature-market-institutions', 'Institutions', 'Market › Institutions', 'market_institutions'),
    destinationItem('App Features', 'feature-market-macro', 'Economic and Macro', 'Market › Macro', 'market_macro'),
    destinationItem('App Features', 'feature-sector-heatmap', 'Sector Heatmap', 'Sectors › Heatmap', 'sector_detail'),
    destinationItem('App Features', 'feature-sector-rotation', 'Sector Rotation', 'Sectors › Rotation', 'sector_rotation'),
    destinationItem('App Features', 'feature-theme-rotation', 'Theme Rotation', 'Themes › Rotation', 'theme_rotation'),
    destinationItem('App Features', 'feature-leadership-scanner', 'Leadership Scanner', 'Sectors › Emerging', 'leadership_scanner'),
    destinationItem('App Features', 'feature-watchlist', 'Watchlist', 'Watchlist › Stocks', 'watchlist'),
    destinationItem('App Features', 'feature-saved-sectors', 'Saved Sectors', 'Watchlist › Sectors', 'watchlist_sectors'),
    destinationItem('App Features', 'feature-saved-themes', 'Saved Themes', 'Watchlist › Themes', 'watchlist_themes'),
    destinationItem('Settings', 'settings-main', 'Settings', 'Settings › Application', 'settings'),
    command('Settings', 'settings-appearance', 'Appearance', 'Settings › Appearance', '/appearance'),
    command('Settings', 'settings-notifications', 'Notifications', 'Settings › Alerts', '/notifications'),
    command('Settings', 'settings-accessibility', 'Accessibility', 'Settings › Accessibility', '/accessibility'),
    command('Settings', 'settings-data-sources', 'Data Sources', 'Settings › Providers', '/data-sources'),
    command('Settings', 'settings-language', 'Language & Region', 'Settings › Region', '/language-region'),
    command('Settings', 'settings-privacy', 'Privacy', 'Settings › Privacy', '/privacy'),
  ];
}

export function searchCommands(items: CommandItem[], query: string): CommandItem[] {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return [];
  return items
    .map((item) => ({ item, score: commandScore(item, normalized) }))
    .filter(({ score }) => score > 0)
    .sort((left, right) => right.score - left.score || left.item.title.localeCompare(right.item.title))
    .map(({ item }) => item);
}

export function buildTickerCommand(query: string): CommandItem | null {
  const symbol = query.trim().toUpperCase();
  if (!/^[A-Z][A-Z0-9.-]{0,9}$/.test(symbol)) return null;
  return destinationItem('Stocks', `ticker-${symbol}`, symbol, 'Open Stock Detail', 'stock_detail', { symbol }, [symbol]);
}

export function buildMostActiveCommands(items: ActiveMarketInput[]): CommandItem[] {
  return items
    .filter((item) => Boolean(item.symbol))
    .sort((left, right) => Math.abs(right.changePercent ?? 0) - Math.abs(left.changePercent ?? 0))
    .slice(0, 6)
    .map((item) => ({
      ...destinationItem('Stocks', `active-${item.symbol}`, item.symbol, formatChange(item.changePercent), 'stock_detail', { symbol: item.symbol }, [item.symbol]),
      sourceState: sourceStateForActiveItem(item),
    }));
}

export function groupCommands(items: CommandItem[]) {
  return COMMAND_CATEGORY_ORDER.flatMap((category) => {
    const categoryItems = items.filter((item) => item.category === category);
    return categoryItems.length ? [{ category, items: categoryItems }] : [];
  });
}

function command(category: CommandCategory, id: string, title: string, metadata: string, pathname: string, params?: Record<string, string>): CommandItem {
  return { category, id, keywords: [title, metadata], metadata, params, pathname, title };
}

function destinationItem(
  category: CommandCategory,
  id: string,
  title: string,
  metadata: string,
  destinationId: DestinationId,
  input: DestinationInput = {},
  keywords: string[] = [title, metadata],
): CommandItem {
  const destination = buildNavigationDestination(destinationId, input);
  return {
    category,
    id,
    keywords,
    metadata,
    params: destination.params,
    pathname: destination.pathname,
    title,
  };
}

function commandScore(item: CommandItem, query: string) {
  const title = item.title.toLowerCase();
  if (title === query) return 100;
  if (title.startsWith(query)) return 80;
  if (item.keywords.some((keyword) => keyword.toLowerCase() === query)) return 70;
  if (title.includes(query)) return 60;
  if (`${item.metadata} ${item.keywords.join(' ')}`.toLowerCase().includes(query)) return 40;
  return 0;
}

function sourceStateForActiveItem(item: ActiveMarketInput): CommandSourceState {
  const source = item.source?.toLowerCase() ?? '';
  if (item.isStale || source.includes('stale') || source.includes('delay')) return 'delayed';
  if (item.isLive) return 'live';
  if (source.includes('test') || source.includes('mock')) return 'test';
  if (item.fallbackUsed || source.includes('cache')) return 'cached';
  return 'unavailable';
}

function formatChange(value?: number | null) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return 'Change unavailable';
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}% today`;
}
