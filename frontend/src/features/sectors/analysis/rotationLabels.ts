import {
  classifyQuadrant,
  formatQuadrant,
  type RotationPoint,
  type RotationQuadrant,
} from '@/data/sectorTabTestData';

export type RotationLabelMode = 'smart' | 'all' | 'none';
export type RotationQuadrantFilter = RotationQuadrant | 'all';
export type LabelPlacement =
  | 'right'
  | 'left'
  | 'above'
  | 'below'
  | 'upper-right'
  | 'upper-left'
  | 'lower-right'
  | 'lower-left';

export type Rect = {
  height: number;
  width: number;
  x: number;
  y: number;
};

export type RotationLabelCandidate = {
  fullName: string;
  history: RotationPoint[];
  id: string;
  key: string;
  latest: RotationPoint;
  shortName: string;
  type: 'sector' | 'theme' | string;
};

export type RotationLabelContext = {
  labelMode: RotationLabelMode;
  maxLabelCount: number;
  selectedItemKey?: string | null;
  watchlistKeys?: Set<string>;
};

export type LabelLayoutInput = {
  chartHeight: number;
  chartWidth: number;
  label: string;
  pointX: number;
  pointY: number;
  selected?: boolean;
};

export type PlacedLabel = {
  bounds: Rect;
  connector: boolean;
  placement: LabelPlacement;
};

const SHORT_LABELS: Record<string, string> = {
  'AI Infrastructure': 'AI Infra',
  Biotechnology: 'Biotech',
  'Communication Services': 'Comms',
  'Consumer Discretionary': 'Cons Disc.',
  'Consumer Staples': 'Staples',
  Cybersecurity: 'Cybersec.',
  'Data Centers': 'Data Centers',
  'Defense Technology': 'Defense',
  Energy: 'Energy',
  Financials: 'Financials',
  Fintech: 'Fintech',
  Healthcare: 'Health',
  Industrials: 'Industrials',
  Materials: 'Materials',
  'Medical Devices': 'Med Devices',
  Memory: 'Memory',
  'Nuclear Energy': 'Nuclear',
  'Oil & Gas': 'Oil & Gas',
  'Optical Networking': 'Optical',
  'Quantum Computing': 'Quantum',
  'Real Estate': 'Real Estate',
  Robotics: 'Robotics',
  Semiconductors: 'Semis',
  Space: 'Space',
  Technology: 'Tech',
  Utilities: 'Utilities',
};

const LABEL_PLACEMENTS: LabelPlacement[] = [
  'right',
  'left',
  'above',
  'below',
  'upper-right',
  'upper-left',
  'lower-right',
  'lower-left',
];

export function getRotationShortLabel(item: { name?: string; fullName?: string }) {
  const fullName = item.fullName ?? item.name ?? '';
  const configured = SHORT_LABELS[fullName];
  if (configured) {
    return configured;
  }

  const abbreviated = fullName
    .replace(/\bInfrastructure\b/g, 'Infra')
    .replace(/\bTechnology\b/g, 'Tech')
    .replace(/\bTechnologies\b/g, 'Tech')
    .replace(/\bCommunication\b/g, 'Comms')
    .replace(/\bServices\b/g, 'Svc')
    .replace(/\bDiscretionary\b/g, 'Disc.')
    .replace(/\bHealthcare\b/g, 'Health')
    .replace(/\bConsumer\b/g, 'Cons.')
    .replace(/\bNetworking\b/g, 'Net');

  if (abbreviated.length <= 12) {
    return abbreviated;
  }

  const words = abbreviated.split(/\s+/).filter(Boolean);
  if (words.length > 1) {
    const compact = words.map((word) => word.slice(0, Math.min(word.length, 5))).join(' ');
    if (compact.length <= 12) {
      return compact;
    }
  }

  return `${abbreviated.slice(0, 10).trimEnd()}…`;
}

export function filterRotationItemsByQuadrant<T extends RotationLabelCandidate>(
  items: T[],
  quadrantFilter: RotationQuadrantFilter,
) {
  if (quadrantFilter === 'all') {
    return items;
  }
  return items.filter((item) => classifyQuadrant(item.latest.relativeStrength, item.latest.relativeMomentum) === quadrantFilter);
}

export function rankRotationLabels(items: RotationLabelCandidate[], context: RotationLabelContext) {
  const watchlistKeys = context.watchlistKeys ?? new Set<string>();
  return [...items].sort((a, b) => {
    const priorityDelta = getLabelPriority(b, context.selectedItemKey, watchlistKeys) - getLabelPriority(a, context.selectedItemKey, watchlistKeys);
    if (priorityDelta !== 0) {
      return priorityDelta;
    }
    return a.key.localeCompare(b.key);
  });
}

export function selectSmartLabelKeys(items: RotationLabelCandidate[], context: RotationLabelContext) {
  if (context.labelMode === 'none') {
    return new Set<string>();
  }
  if (context.labelMode === 'all') {
    return new Set(items.map((item) => item.key));
  }

  const selectedKey = context.selectedItemKey;
  const ranked = rankRotationLabels(items, context);
  const keys = new Set<string>();
  ranked.slice(0, Math.max(0, context.maxLabelCount)).forEach((item) => keys.add(item.key));
  if (selectedKey && items.some((item) => item.key === selectedKey)) {
    keys.add(selectedKey);
  }
  return keys;
}

export function estimateLabelBounds(label: string, fontSize: number) {
  return {
    height: Math.ceil(fontSize * 1.65),
    width: Math.min(116, Math.max(38, Math.ceil(label.length * fontSize * 0.62) + 16)),
  };
}

export function findAvailableLabelPlacement(
  input: LabelLayoutInput,
  placedLabels: Rect[],
  reservedRects: Rect[] = [],
): PlacedLabel | null {
  const size = estimateLabelBounds(input.label, input.selected ? 11 : 10);
  const orderedPlacements = input.selected ? LABEL_PLACEMENTS : LABEL_PLACEMENTS;

  for (const placement of orderedPlacements) {
    const proposed = clampLabelToBounds(
      buildLabelRect(input.pointX, input.pointY, size.width, size.height, placement),
      input.chartWidth,
      input.chartHeight,
    );
    const collides = [...placedLabels, ...reservedRects].some((rect) => doRectsOverlap(proposed, rect));
    if (!collides) {
      return {
        bounds: proposed,
        connector: placement !== 'right' && placement !== 'left',
        placement,
      };
    }
  }

  if (input.selected) {
    const fallback = clampLabelToBounds(
      buildLabelRect(input.pointX, input.pointY, size.width, size.height, 'above'),
      input.chartWidth,
      input.chartHeight,
    );
    return {
      bounds: fallback,
      connector: true,
      placement: 'above',
    };
  }

  return null;
}

export function doRectsOverlap(a: Rect, b: Rect, padding = 2) {
  return !(
    a.x + a.width + padding <= b.x ||
    b.x + b.width + padding <= a.x ||
    a.y + a.height + padding <= b.y ||
    b.y + b.height + padding <= a.y
  );
}

export function clampLabelToBounds(rect: Rect, chartWidth: number, chartHeight: number): Rect {
  return {
    ...rect,
    x: Math.max(4, Math.min(rect.x, chartWidth - rect.width - 4)),
    y: Math.max(4, Math.min(rect.y, chartHeight - rect.height - 4)),
  };
}

export function buildRotationVisibilitySummary({
  filtered,
  labels,
  mode,
  quadrantFilter,
  total,
}: {
  filtered: number;
  labels: number;
  mode: RotationLabelMode;
  quadrantFilter: RotationQuadrantFilter;
  total: number;
}) {
  const filterText = quadrantFilter === 'all' ? '' : ` · ${formatQuadrant(quadrantFilter)} filter`;
  if (mode === 'none') {
    return `${filtered} points shown · Labels hidden${filterText}`;
  }
  return `${filtered} points shown · ${labels} labels shown${filterText}${filtered < total ? ` · ${total - filtered} filtered` : ''}`;
}

function getLabelPriority(item: RotationLabelCandidate, selectedItemKey: string | null | undefined, watchlistKeys: Set<string>) {
  const history = item.history;
  const latest = item.latest;
  const previous = history[history.length - 2] ?? latest;
  const first = history[0] ?? latest;
  const recentMove = Math.hypot(latest.relativeStrength - previous.relativeStrength, latest.relativeMomentum - previous.relativeMomentum);
  const totalMove = Math.hypot(latest.relativeStrength - first.relativeStrength, latest.relativeMomentum - first.relativeMomentum);
  const quadrantChanged = classifyQuadrant(first.relativeStrength, first.relativeMomentum) !== classifyQuadrant(latest.relativeStrength, latest.relativeMomentum);
  const neutralDistance = Math.hypot(latest.relativeStrength - 100, latest.relativeMomentum - 100);

  let score = 0;
  if (selectedItemKey === item.key) {
    score += 10000;
  }
  if (watchlistKeys.has(item.key)) {
    score += 2600;
  }
  if (quadrantChanged) {
    score += 1600;
  }
  score += recentMove * 220;
  score += totalMove * 90;
  score += Math.max(0, latest.relativeMomentum - 100) * 65;
  score += Math.max(0, latest.relativeStrength - 100) * 52;
  score += Math.max(0, 2.2 - neutralDistance) * 120;

  return score;
}

function buildLabelRect(
  pointX: number,
  pointY: number,
  width: number,
  height: number,
  placement: LabelPlacement,
): Rect {
  const offset = 12;
  switch (placement) {
    case 'left':
      return { height, width, x: pointX - width - offset, y: pointY - height / 2 };
    case 'above':
      return { height, width, x: pointX - width / 2, y: pointY - height - offset };
    case 'below':
      return { height, width, x: pointX - width / 2, y: pointY + offset };
    case 'upper-right':
      return { height, width, x: pointX + offset, y: pointY - height - offset };
    case 'upper-left':
      return { height, width, x: pointX - width - offset, y: pointY - height - offset };
    case 'lower-right':
      return { height, width, x: pointX + offset, y: pointY + offset };
    case 'lower-left':
      return { height, width, x: pointX - width - offset, y: pointY + offset };
    case 'right':
    default:
      return { height, width, x: pointX + offset, y: pointY - height / 2 };
  }
}
