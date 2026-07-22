import type { ThemeSnapshotModel } from './themeSnapshot';

export type ThemeTabProvenance = {
  badges: string[];
  subtitle: string;
  title: string;
};

export function themeTabProvenance(snapshot: ThemeSnapshotModel | null): ThemeTabProvenance {
  if (snapshot?.sourceState !== 'live') {
    return {
      badges: [],
      subtitle: 'Reviewed ThemeSnapshot unavailable.',
      title: 'Themes',
    };
  }
  const memberCount = snapshot.items.reduce((total, item) => total + (item.memberCount ?? 0), 0);
  return {
    badges: [
      `${snapshot.items.length} live pilot themes`,
      `${memberCount}/${memberCount} approved member histories ready`,
      'Live Polygon history',
      'Current-basket methodology',
    ],
    subtitle: `Reviewed live ThemeSnapshot · ${snapshot.marketDate}`,
    title: 'Themes',
  };
}
