export type CanonicalEntityKind = 'stock' | 'sector' | 'theme' | 'report';

export type EntityDestinationInput = {
  entityId?: string | null;
  entityName?: string | null;
  reportId?: string | null;
  sectionId?: string | null;
  stockTab?: 'overview' | 'technical' | 'signals' | 'risk';
  symbol?: string | null;
};

export type CanonicalEntityDestination = {
  params: Record<string, string>;
  pathname: '/report' | '/sectors' | '/watchlist';
};

export const ENTITY_ROUTING_REGISTRY = {
  stock: { owner: 'Watchlist Stock Detail', pathname: '/watchlist' },
  sector: { owner: 'Sectors Sector Detail', pathname: '/sectors' },
  theme: { owner: 'Sectors Theme Detail', pathname: '/sectors' },
  report: { owner: 'Report Document', pathname: '/report' },
} as const satisfies Record<CanonicalEntityKind, { owner: string; pathname: CanonicalEntityDestination['pathname'] }>;

export function buildEntityDestination(
  kind: CanonicalEntityKind,
  input: EntityDestinationInput = {},
): CanonicalEntityDestination {
  if (kind === 'stock') {
    return {
      pathname: '/watchlist',
      params: compactParams({
        commandTarget: input.stockTab && input.stockTab !== 'overview' ? `stock${capitalize(input.stockTab)}` : 'stockDetail',
        detailTab: input.stockTab ?? 'overview',
        section: 'stocks',
        symbol: input.symbol?.toUpperCase(),
      }),
    };
  }
  if (kind === 'sector' || kind === 'theme') {
    return {
      pathname: '/sectors',
      params: compactParams({
        commandTarget: `${kind}Detail`,
        entityId: input.entityId,
        entityKind: kind,
        entityName: input.entityName,
        section: kind === 'sector' ? 'sectorHeatmap' : 'themesHeatmap',
      }),
    };
  }
  return {
    pathname: '/report',
    params: compactParams({
      commandTarget: input.sectionId ?? 'report',
      reportId: input.reportId,
      sectionId: input.sectionId,
    }),
  };
}

function capitalize(value: string) {
  return `${value.charAt(0).toUpperCase()}${value.slice(1)}`;
}

function compactParams(input: Record<string, string | null | undefined>): Record<string, string> {
  return Object.fromEntries(Object.entries(input).flatMap(([key, value]) => {
    const normalized = value?.trim();
    return normalized ? [[key, normalized]] : [];
  }));
}
