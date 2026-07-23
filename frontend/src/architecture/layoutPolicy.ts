export type LayoutWidthPolicy =
  | 'full_width_analytical'
  | 'constrained_analytical'
  | 'constrained_settings'
  | 'modal_content';

export type ViewportClass = 'mobile' | 'tablet' | 'desktop';

export const LAYOUT_POLICY = {
  bottomNavigation: {
    breathingSpace: 16,
    nativeBarHeight: 58,
    webBarHeight: 70,
  },
  gutters: {
    desktop: 32,
    mobile: 16,
    tablet: 24,
  },
  widths: {
    constrained_analytical: 1100,
    constrained_settings: 800,
    full_width_analytical: 1440,
    modal_content: 760,
  },
} as const;

const PRIMARY_ROUTES = new Set(['/', '/market', '/sectors', '/watchlist', '/more']);
const FULL_WIDTH_ROUTES = new Set(['/market', '/sectors']);
const ANALYTICAL_ROUTES = new Set(['/', '/watchlist', '/report', '/ai']);

export function isPrimaryRoute(pathname: string) {
  return PRIMARY_ROUTES.has(pathname);
}

export function widthPolicyForRoute(pathname: string): LayoutWidthPolicy {
  if (FULL_WIDTH_ROUTES.has(pathname)) return 'full_width_analytical';
  if (ANALYTICAL_ROUTES.has(pathname)) return 'constrained_analytical';
  return 'constrained_settings';
}

export function viewportClass(width: number): ViewportClass {
  if (width < 600) return 'mobile';
  if (width < 1024) return 'tablet';
  return 'desktop';
}

export function horizontalGutter(width: number) {
  return LAYOUT_POLICY.gutters[viewportClass(width)];
}

export function maximumContentWidth(policy: LayoutWidthPolicy) {
  return LAYOUT_POLICY.widths[policy];
}

export function pageBottomInset({
  isPrimary,
  platform = 'native',
  safeAreaBottom,
}: {
  isPrimary: boolean;
  platform?: string;
  safeAreaBottom: number;
}) {
  const safeArea = Math.max(0, safeAreaBottom);
  if (!isPrimary) return safeArea + LAYOUT_POLICY.bottomNavigation.breathingSpace;
  const barHeight = platform === 'web'
    ? LAYOUT_POLICY.bottomNavigation.webBarHeight
    : LAYOUT_POLICY.bottomNavigation.nativeBarHeight + safeArea;
  return barHeight + LAYOUT_POLICY.bottomNavigation.breathingSpace;
}

export function modalBottomInset(safeAreaBottom: number) {
  return Math.max(0, safeAreaBottom) + LAYOUT_POLICY.bottomNavigation.breathingSpace;
}

export function selectedItemScrollOffset({
  contentWidth,
  itemWidth,
  itemX,
  viewportWidth,
}: {
  contentWidth: number;
  itemWidth: number;
  itemX: number;
  viewportWidth: number;
}) {
  if (contentWidth <= viewportWidth || viewportWidth <= 0) return 0;
  const centered = itemX + itemWidth / 2 - viewportWidth / 2;
  return Math.max(0, Math.min(centered, contentWidth - viewportWidth));
}
