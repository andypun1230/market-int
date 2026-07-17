import type { CopilotContext, CopilotFocusedMetric, CopilotSourceState } from '@/features/copilot/types';

export function createCopilotContext({
  focusedMetric,
  payload,
  routeName,
  screenTitle,
  screenType,
  sourceState,
}: {
  focusedMetric?: CopilotFocusedMetric;
  payload?: Record<string, unknown>;
  routeName: string;
  screenTitle: string;
  screenType: CopilotContext['screenType'];
  sourceState?: string | null;
}): CopilotContext {
  const context: CopilotContext = {
    focusedMetric,
    generatedAt: new Date().toISOString(),
    routeName,
    screenTitle,
    screenType,
    sourceState: normalizeSourceState(sourceState),
  };
  if (payload) {
    if (screenType === 'home' || screenType === 'market') {
      context.market = payload;
    } else if (screenType === 'sector') {
      context.sector = payload;
    } else if (screenType === 'theme') {
      context.theme = payload;
    } else if (screenType === 'watchlist') {
      context.watchlist = payload;
    } else if (screenType === 'stock') {
      context.stock = payload;
    } else if (screenType === 'report') {
      context.report = payload;
    }
  }
  return context;
}

export function normalizeSourceState(value?: string | null): CopilotSourceState {
  if (value === 'live' || value === 'delayed' || value === 'cached' || value === 'stale' || value === 'mock' || value === 'mixed') {
    return value;
  }
  return 'unavailable';
}

export function sourceStateLabel(value: CopilotSourceState) {
  switch (value) {
    case 'live':
      return 'Live data';
    case 'delayed':
      return 'Delayed data';
    case 'cached':
      return 'Cached data';
    case 'stale':
      return 'Stale data';
    case 'mock':
      return 'Mock data';
    case 'mixed':
      return 'Mixed sources';
    default:
      return 'Source unavailable';
  }
}
