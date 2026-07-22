import type {
  BreadthHistoryInterval,
  SectorThemeTestItem,
  TestHeatmapInterval,
  TestRotationInterval,
  TestSectorItem,
  TestThemeItem,
} from '@/data/sectorTabTestData';
import type { RotationLabelMode, RotationQuadrantFilter } from '@/features/sectors/analysis/rotationLabels';
import type {
  ThemeRotationMovementFilter,
  ThemeRotationTailLength,
  ThemeRotationUniverse,
} from '@/features/themes/themeRotationView';

export type SectorActiveSection =
  | 'sectorHeatmap'
  | 'sectorRotation'
  | 'sectorAlerts'
  | 'themesHeatmap'
  | 'themesRotation'
  | 'themeAlerts'
  | 'emergingLeadership'
  | 'leadershipRisk';

export type SectorActiveCategory = 'sectors' | 'themes' | 'signals';

export type SectorDetailSelection =
  | {
      item: TestSectorItem;
      kind: 'Sector';
    }
  | {
      item: TestThemeItem;
      kind: 'Theme';
    }
  | null;

export type SectorUiPreferences = {
  activeSection: SectorActiveSection;
  detailBreadthInterval: BreadthHistoryInterval;
  detailRotationInterval: TestRotationInterval;
  sectorHeatmapInterval: TestHeatmapInterval;
  sectorRotationInterval: TestRotationInterval;
  sectorRotationLabelMode: RotationLabelMode;
  sectorRotationQuadrant: RotationQuadrantFilter;
  themeHeatmapInterval: TestHeatmapInterval;
  themeRotationInterval: TestRotationInterval;
  themeRotationLabelMode: RotationLabelMode;
  themeRotationMovement: ThemeRotationMovementFilter;
  themeRotationQuadrant: RotationQuadrantFilter;
  themeRotationTailLength: ThemeRotationTailLength;
  themeRotationUniverse: ThemeRotationUniverse;
};

export type SectorThemeRepository = {
  getAllItems: () => SectorThemeTestItem[];
  getBenchmark: () => 'SPY';
  getSectorById: (id: string) => TestSectorItem | null;
  getSectors: () => TestSectorItem[];
  getThemeById: (id: string) => TestThemeItem | null;
  getThemes: () => TestThemeItem[];
};
