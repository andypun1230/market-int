import '@/global.css';

import { Platform } from 'react-native';

export const Theme = {
  colors: {
    background: '#0F172A',
    backgroundMuted: '#111827',
    card: '#111827',
    cardAlt: '#172033',
    cardMuted: '#172033',
    cardElevated: '#1E293B',
    border: '#334155',
    borderDark: '#334155',
    primary: '#F8FAFC',
    accent: '#38BDF8',
    focus: '#38BDF8',
    accentSoft: '#18354A',
    success: '#22C55E',
    successSoft: '#123524',
    warning: '#F59E0B',
    warningSoft: '#3B2A10',
    danger: '#EF4444',
    dangerSoft: '#111827',
    purple: '#A855F7',
    purpleSoft: '#0F172A',
    text: '#F8FAFC',
    textMuted: '#94A3B8',
    textInverse: '#F8FAFC',
    textInverseMuted: '#94A3B8',
    tabBar: '#111827',
    tabInactive: '#94A3B8',
  },
  radii: {
    card: 10,
    small: 8,
    pill: 999,
  },
  fontSizes: {
    caption: 11,
    small: 12,
    body: 14,
    bodyLarge: 15,
    sectionTitle: 18,
    screenTitle: 29,
    hero: 31,
  },
  accessibility: {
    focusRingOffset: 2,
    focusRingWidth: 3,
    minimumTouchTarget: 44,
  },
} as const;

/**
 * Semantic typography roles used across product UI.
 *
 * `chartMicro` and `chartAxis` are the only approved sub-caption exceptions;
 * they are reserved for non-interactive chart annotations that have an
 * equivalent accessibility summary. Product copy and controls start at
 * `caption` and `small`, respectively.
 */
export const Typography = {
  chartMicro: { fontSize: 8, lineHeight: 11 },
  chartAxis: { fontSize: 9, lineHeight: 12 },
  chartLabel: { fontSize: Theme.fontSizes.caption, lineHeight: 14 },
  caption: { fontSize: Theme.fontSizes.caption, lineHeight: 16 },
  small: { fontSize: Theme.fontSizes.small, lineHeight: 18 },
  control: { fontSize: 13, lineHeight: 18 },
  body: { fontSize: Theme.fontSizes.body, lineHeight: 20 },
  bodyLarge: { fontSize: Theme.fontSizes.bodyLarge, lineHeight: 22 },
  supportTitle: { fontSize: 16, lineHeight: 21 },
  cardTitle: { fontSize: 17, lineHeight: 22 },
  sectionTitle: { fontSize: Theme.fontSizes.sectionTitle, lineHeight: 24 },
  toolbarTitle: { fontSize: 19, lineHeight: 24 },
  detailTitle: { fontSize: 20, lineHeight: 26 },
  scoreTitle: { fontSize: 21, lineHeight: 27 },
  sectionHero: { fontSize: 22, lineHeight: 28 },
  decisionState: { fontSize: 23, lineHeight: 29 },
  decisionHero: { fontSize: 24, lineHeight: 30 },
  reportTitle: { fontSize: 25, lineHeight: 31 },
  entityHero: { fontSize: 26, lineHeight: 32 },
  screenTitleSmall: { fontSize: 27, lineHeight: 33 },
  entityTitle: { fontSize: 28, lineHeight: 34 },
  screenTitle: { fontSize: Theme.fontSizes.screenTitle, lineHeight: 35 },
  screenTitleLarge: { fontSize: 30, lineHeight: 36 },
  hero: { fontSize: Theme.fontSizes.hero, lineHeight: 38 },
  heroValue: { fontSize: 32, lineHeight: 39 },
  display: { fontSize: 34, lineHeight: 41 },
  displayLarge: { fontSize: 40, lineHeight: 48 },
  displayHero: { fontSize: 48, lineHeight: 56 },
  weights: {
    medium: '600',
    emphasis: '700',
    strong: '800',
    heavy: '900',
  },
} as const;

export const Colors = {
  light: {
    text: Theme.colors.text,
    background: Theme.colors.background,
    backgroundElement: Theme.colors.card,
    backgroundSelected: Theme.colors.accentSoft,
    textSecondary: Theme.colors.textMuted,
  },
  dark: {
    text: Theme.colors.textInverse,
    background: Theme.colors.background,
    backgroundElement: Theme.colors.primary,
    backgroundSelected: Theme.colors.cardElevated,
    textSecondary: Theme.colors.textInverseMuted,
  },
} as const;

export type ThemeColor = keyof typeof Colors.light & keyof typeof Colors.dark;

export const Fonts = Platform.select({
  ios: {
    /** iOS `UIFontDescriptorSystemDesignDefault` */
    sans: 'system-ui',
    /** iOS `UIFontDescriptorSystemDesignSerif` */
    serif: 'ui-serif',
    /** iOS `UIFontDescriptorSystemDesignRounded` */
    rounded: 'ui-rounded',
    /** iOS `UIFontDescriptorSystemDesignMonospaced` */
    mono: 'ui-monospace',
  },
  default: {
    sans: 'normal',
    serif: 'serif',
    rounded: 'normal',
    mono: 'monospace',
  },
  web: {
    sans: 'var(--font-display)',
    serif: 'var(--font-serif)',
    rounded: 'var(--font-rounded)',
    mono: 'var(--font-mono)',
  },
});

export const Spacing = {
  half: 2,
  one: 4,
  two: 8,
  twoAndHalf: 12,
  three: 16,
  four: 24,
  five: 32,
  six: 64,
} as const;

export const BottomTabInset = Platform.select({ ios: 50, android: 80 }) ?? 0;
export const MaxContentWidth = 800;
