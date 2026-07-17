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
    accentSoft: '#18354A',
    success: '#22C55E',
    successSoft: '#123524',
    warning: '#F59E0B',
    warningSoft: '#3B2A10',
    danger: '#EF4444',
    dangerSoft: '#3B1717',
    purple: '#A855F7',
    purpleSoft: '#2E174A',
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
