import type { ThemeSnapshotModel } from './themeSnapshot';

export type ThemeTabProvenance = {
  badges: string[];
  subtitle: string;
  title: string;
};

export function themeTabProvenance(snapshot: ThemeSnapshotModel | null): ThemeTabProvenance {
  if (!snapshot?.items.length) {
    return {
      badges: [],
      subtitle: 'Canonical Theme Intelligence directory unavailable.',
      title: 'Themes',
    };
  }
  const available = snapshot.items.filter((item) => item.status === 'available');
  const partial = snapshot.items.filter((item) => item.status === 'partial');
  const memberCount = snapshot.items.reduce((total, item) => total + (item.memberCount ?? 0), 0);
  return {
    badges: [
      `${snapshot.items.length} launch themes`,
      `${available.length} available · ${partial.length} partial`,
      `${memberCount} mapped constituents`,
      snapshot.sourceState === 'live' ? 'Governed live snapshots where available' : 'Market analytics unavailable',
    ],
    subtitle: snapshot.sourceState === 'live'
      ? `Canonical Theme Intelligence · market data ${snapshot.marketDate}`
      : 'Canonical taxonomy available; market analytics remain explicitly unavailable.',
    title: 'Themes',
  };
}
