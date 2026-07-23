export {
  COPILOT_DESTINATIONS as NAVIGATION_REGISTRY,
  buildCopilotDestination as buildNavigationDestination,
  createCopilotAction,
  normalizeDestinationId,
  resolveCopilotAction as resolveNavigationAction,
  type CopilotDestinationId as DestinationId,
  type CopilotDestinationInput as DestinationInput,
  type CopilotResolvedDestination as ResolvedDestination,
} from '@/features/copilot/navigation/copilotDestinations';

export const STATIC_ROUTE_REGISTRY = [
  '/', '/market', '/sectors', '/watchlist', '/more', '/report', '/ai', '/settings',
  '/profile', '/notifications', '/appearance', '/accessibility', '/language-region',
  '/data-usage', '/data-sources', '/about', '/disclaimer', '/privacy',
] as const;
