import type { ThemeStatusResponse } from '@/types/market';

export type ThemeGovernancePresentation = {
  body: string;
  footer: string;
  pilotThemes: { displayName: string; reviewStatus: string }[];
  title: string;
};

export function themeGovernancePresentation(status: ThemeStatusResponse | null): ThemeGovernancePresentation {
  return {
    title: status?.status === 'live' ? 'Theme Intelligence' : 'Theme Intelligence is awaiting review',
    body: 'Reviewed theme definitions and constituent memberships are required before live Theme Heatmap, Rotation, and Alerts can be published.',
    footer: 'Generated and proposed Theme data remains hidden until review and live validation are complete.',
    pilotThemes: (status?.pilot_themes ?? []).map((theme) => ({ displayName: theme.display_name ?? theme.theme_id ?? 'Theme', reviewStatus: theme.review_status ?? 'awaiting_review' })),
  };
}
