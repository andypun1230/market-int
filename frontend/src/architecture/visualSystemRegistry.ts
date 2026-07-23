export const SEMANTIC_TYPOGRAPHY_ROLES = [
  'chartMicro',
  'chartAxis',
  'chartLabel',
  'caption',
  'small',
  'control',
  'body',
  'bodyLarge',
  'supportTitle',
  'cardTitle',
  'sectionTitle',
  'toolbarTitle',
  'detailTitle',
  'scoreTitle',
  'sectionHero',
  'decisionState',
  'decisionHero',
  'reportTitle',
  'entityHero',
  'screenTitleSmall',
  'entityTitle',
  'screenTitle',
  'screenTitleLarge',
  'hero',
  'heroValue',
  'display',
  'displayLarge',
  'displayHero',
] as const;

export const TYPOGRAPHY_EXCEPTIONS = [
  {
    minimumSize: 8,
    owner: 'RotationQuadrantChart and other analytical charts',
    reason: 'Non-interactive axes and point annotations have equivalent accessible chart summaries.',
    roles: ['chartMicro', 'chartAxis'] as const,
  },
] as const;

export const BUTTON_VARIANTS = ['primary', 'secondary', 'neutral', 'danger', 'icon', 'compact'] as const;

export const BUTTON_CONTRACT = {
  canonicalOwner: 'AppButton',
  minimumTouchTarget: 44,
  states: ['default', 'pressed', 'focused', 'disabled', 'loading'] as const,
} as const;

export const CONFIDENCE_FRESHNESS_CONTRACT = {
  availabilityOwner: 'availabilityLabel',
  confidenceOwner: 'confidenceLabel',
  freshnessOwner: 'freshnessLabel',
  providerOwner: 'providerLabel',
  presentationOwner: 'FreshnessText',
} as const;

export const SHARED_CARD_SURFACES = [
  'DashboardCard',
  'EmptyState',
  'ErrorState',
  'LoadingState',
  'SkeletonCard',
] as const;

export const ICON_EXCEPTIONS = [
  {
    owner: 'RotationQuadrantChart',
    glyph: '›',
    reason: 'Rotated trajectory arrow is a plotted data mark, not an interactive UI icon.',
  },
] as const;
