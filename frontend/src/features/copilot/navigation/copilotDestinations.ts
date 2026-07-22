import type { CopilotActionV1 } from '@/features/copilot/types';

export type CopilotDestinationId =
  | 'home'
  | 'market_overview'
  | 'market_indexes'
  | 'market_health'
  | 'market_breadth'
  | 'market_decision'
  | 'market_institutions'
  | 'market_macro'
  | 'sector_rotation'
  | 'theme_rotation'
  | 'sector_detail'
  | 'theme_detail'
  | 'leadership_scanner'
  | 'stock_detail'
  | 'stock_technical'
  | 'stock_signals'
  | 'stock_risk'
  | 'watchlist'
  | 'watchlist_sectors'
  | 'watchlist_themes'
  | 'report'
  | 'report_research_focus'
  | 'report_scenarios'
  | 'report_watchlist'
  | 'settings';

export type CopilotDestinationInput = {
  symbol?: string | null;
  entityId?: string | null;
  entityName?: string | null;
  reportId?: string | null;
  sectionId?: string | null;
};

export type CopilotResolvedDestination = {
  pathname: string;
  params?: Record<string, string>;
};

type DestinationDefinition = {
  label: string;
  pathname: string;
  params?: (input: CopilotDestinationInput) => Record<string, string>;
};

const MARKET_SECTION = (section: string) => () => ({ commandTarget: section, section });
const SECTOR_SECTION = (section: string) => () => ({ commandTarget: section, section });
const WATCHLIST_SECTION = (section: string) => () => ({ commandTarget: section, section });

export const COPILOT_DESTINATIONS: Record<CopilotDestinationId, DestinationDefinition> = {
  home: { label: 'Home / Market Pulse', pathname: '/' },
  market_overview: { label: 'Market Overview', pathname: '/market', params: MARKET_SECTION('overview') },
  market_indexes: { label: 'Indexes', pathname: '/market', params: MARKET_SECTION('indexes') },
  market_health: { label: 'Market Health', pathname: '/market', params: MARKET_SECTION('health') },
  market_breadth: { label: 'Breadth', pathname: '/market', params: MARKET_SECTION('breadth') },
  market_decision: { label: 'Decision / Fear & Greed', pathname: '/market', params: MARKET_SECTION('decision') },
  market_institutions: { label: 'Institutions', pathname: '/market', params: MARKET_SECTION('institutions') },
  market_macro: { label: 'Economic and Macro', pathname: '/market', params: MARKET_SECTION('macro') },
  sector_rotation: { label: 'Sector Rotation', pathname: '/sectors', params: SECTOR_SECTION('sectorRotation') },
  theme_rotation: { label: 'Theme Rotation', pathname: '/sectors', params: SECTOR_SECTION('themesRotation') },
  sector_detail: {
    label: 'Sector Detail',
    pathname: '/sectors',
    params: (input) => compactParams({
      commandTarget: 'sectorDetail',
      section: 'sectorHeatmap',
      entityKind: 'sector',
      entityId: input.entityId,
      entityName: input.entityName,
    }),
  },
  theme_detail: {
    label: 'Theme Detail',
    pathname: '/sectors',
    params: (input) => compactParams({
      commandTarget: 'themeDetail',
      section: 'themesHeatmap',
      entityKind: 'theme',
      entityId: input.entityId,
      entityName: input.entityName,
    }),
  },
  leadership_scanner: { label: 'Leadership Scanner', pathname: '/sectors', params: SECTOR_SECTION('emergingLeadership') },
  stock_detail: {
    label: 'Stock Detail',
    pathname: '/watchlist',
    params: (input) => compactParams({ commandTarget: 'stockDetail', section: 'stocks', symbol: input.symbol, detailTab: 'overview' }),
  },
  stock_technical: {
    label: 'Stock Technical',
    pathname: '/watchlist',
    params: (input) => compactParams({ commandTarget: 'stockTechnical', section: 'stocks', symbol: input.symbol, detailTab: 'technical' }),
  },
  stock_signals: {
    label: 'Stock Signals',
    pathname: '/watchlist',
    params: (input) => compactParams({ commandTarget: 'stockSignals', section: 'stocks', symbol: input.symbol, detailTab: 'signals' }),
  },
  stock_risk: {
    label: 'Stock Risk',
    pathname: '/watchlist',
    params: (input) => compactParams({ commandTarget: 'stockRisk', section: 'stocks', symbol: input.symbol, detailTab: 'risk' }),
  },
  watchlist: { label: 'Watchlist', pathname: '/watchlist', params: WATCHLIST_SECTION('stocks') },
  watchlist_sectors: { label: 'Saved Sectors', pathname: '/watchlist', params: WATCHLIST_SECTION('sectors') },
  watchlist_themes: { label: 'Saved Themes', pathname: '/watchlist', params: WATCHLIST_SECTION('themes') },
  report: {
    label: 'Daily Report',
    pathname: '/report',
    params: (input) => compactParams({ commandTarget: 'report', reportId: input.reportId }),
  },
  report_research_focus: {
    label: 'Report Research Focus',
    pathname: '/report',
    params: (input) => compactParams({ commandTarget: 'research-focus', reportId: input.reportId, sectionId: input.sectionId ?? 'research-focus' }),
  },
  report_scenarios: {
    label: 'Report Scenarios',
    pathname: '/report',
    params: (input) => compactParams({ commandTarget: 'scenarios', reportId: input.reportId, sectionId: input.sectionId ?? 'scenarios' }),
  },
  report_watchlist: {
    label: 'Report Watchlist Intelligence',
    pathname: '/report',
    params: (input) => compactParams({ commandTarget: 'watchlist', reportId: input.reportId, sectionId: input.sectionId ?? 'watchlist' }),
  },
  settings: { label: 'Settings', pathname: '/settings' },
};

const DESTINATION_ALIASES: Record<string, CopilotDestinationId> = {
  market: 'market_overview',
  market_pulse: 'home',
  indexes: 'market_indexes',
  breadth: 'market_breadth',
  health: 'market_health',
  decision: 'market_decision',
  fear_greed: 'market_decision',
  fear_and_greed: 'market_decision',
  institutions: 'market_institutions',
  macro: 'market_macro',
  sector: 'sector_detail',
  theme: 'theme_detail',
  stock: 'stock_detail',
  stock_setup: 'stock_technical',
  leadership: 'leadership_scanner',
  risk: 'stock_risk',
  research_focus: 'report_research_focus',
  report_scenario: 'report_scenarios',
  report_watchlist_intelligence: 'report_watchlist',
};

const ALLOWED_ROUTES = new Set([
  '/', '/market', '/sectors', '/watchlist', '/report', '/settings', '/ai', '/more',
  '/about', '/accessibility', '/appearance', '/data-sources', '/data-usage', '/disclaimer',
  '/language-region', '/notifications', '/privacy', '/profile',
]);

export function buildCopilotDestination(
  destinationId: CopilotDestinationId,
  input: CopilotDestinationInput = {},
): CopilotResolvedDestination {
  const definition = COPILOT_DESTINATIONS[destinationId];
  const params = definition.params?.(input);
  return { pathname: definition.pathname, ...(params && Object.keys(params).length ? { params } : {}) };
}

export function createCopilotAction(
  destinationId: CopilotDestinationId,
  input: CopilotDestinationInput = {},
  label?: string,
): CopilotActionV1 {
  const destination = buildCopilotDestination(destinationId, input);
  return {
    schemaVersion: 'copilot-action-v1',
    actionId: `${destinationId}:${input.symbol ?? input.entityId ?? input.reportId ?? 'root'}`,
    actionType: 'navigate',
    destinationId,
    label: label ?? COPILOT_DESTINATIONS[destinationId].label,
    route: destination.pathname,
    sectionId: destination.params?.sectionId ?? null,
    entity: input.symbol ?? input.entityId ?? null,
    highlightTarget: destination.params?.commandTarget ?? null,
    parameters: destination.params,
  };
}

export function resolveCopilotAction(action: CopilotActionV1): CopilotResolvedDestination | null {
  const requestedId = normalizeDestinationId(action.destinationId ?? action.destination);
  const entity = action.entity?.trim() || null;
  const parameters = compactParams(action.parameters ?? {});
  const input: CopilotDestinationInput = {
    symbol: parameters.symbol ?? (requestedId?.startsWith('stock_') ? entity : null),
    entityId: parameters.entityId ?? (!requestedId?.startsWith('stock_') ? entity : null),
    entityName: parameters.entityName,
    reportId: parameters.reportId,
    sectionId: action.sectionId ?? parameters.sectionId,
  };
  if (requestedId) {
    const resolved = buildCopilotDestination(requestedId, input);
    const isStockDestination = requestedId.startsWith('stock_');
    const isMarketDestination = resolved.pathname === '/market';
    const isSectorDestination = resolved.pathname === '/sectors';
    const detailTab = parameters.stockTab
      ?? parameters.detailTab
      ?? (isStockDestination ? action.subTab : undefined)
      ?? resolved.params?.detailTab;
    const section = isStockDestination
      ? 'stocks'
      : isMarketDestination
        ? action.tab ?? parameters.tab ?? parameters.section ?? resolved.params?.section
        : isSectorDestination
          ? action.sectionId ?? parameters.sectionId ?? parameters.section ?? resolved.params?.section
          : parameters.section ?? resolved.params?.section;
    return {
      pathname: resolved.pathname,
      params: compactParams({
        ...(resolved.params ?? {}),
        ...parameters,
        section,
        detailTab,
        subTab: action.subTab ?? parameters.subTab,
        sectionId: action.sectionId ?? parameters.sectionId ?? resolved.params?.sectionId,
        commandTarget: action.highlightTarget ?? parameters.commandTarget ?? resolved.params?.commandTarget,
      }),
    };
  }
  const route = action.route?.trim() ?? '';
  if (!ALLOWED_ROUTES.has(route)) return null;
  return {
    pathname: route,
    params: compactParams({
      ...parameters,
      section: route === '/watchlist' && (action.subTab || parameters.stockTab) ? 'stocks' : action.tab ?? parameters.section,
      detailTab: route === '/watchlist' ? parameters.stockTab ?? action.subTab ?? parameters.detailTab : parameters.detailTab,
      subTab: action.subTab ?? parameters.subTab,
      sectionId: action.sectionId ?? parameters.sectionId,
      commandTarget: action.highlightTarget ?? parameters.commandTarget,
    }),
  };
}

export function normalizeDestinationId(input?: string | null): CopilotDestinationId | null {
  const normalized = input?.trim().toLowerCase().replaceAll('-', '_').replaceAll(' ', '_') ?? '';
  if (normalized in COPILOT_DESTINATIONS) return normalized as CopilotDestinationId;
  return DESTINATION_ALIASES[normalized] ?? null;
}

function compactParams(input: Record<string, string | null | undefined>): Record<string, string> {
  return Object.fromEntries(Object.entries(input).flatMap(([key, value]) => {
    const normalized = value?.trim();
    return normalized ? [[key, normalized]] : [];
  }));
}
