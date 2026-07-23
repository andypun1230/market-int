export const SHARED_COMPONENT_REGISTRY = {
  alertBadges: ['StatusBadge', 'AlertList'],
  buttons: ['AppButton', 'QuickActionChip', 'SegmentedControl'],
  confidenceIndicators: ['ConfidenceIndicator', 'ScoreGauge', 'StatusBadge'],
  confidenceFreshnessPresentation: ['ConfidenceFreshness', 'FreshnessText'],
  evidencePanels: ['ExpandableSection', 'DashboardCard'],
  icons: ['AppIcon'],
  intelligenceCards: ['DashboardCard', 'DecisionCard', 'HeroDecisionCard', 'DecisionSummaryCard'],
  summaryComponents: ['CompactSummaryCard', 'SummaryTile', 'MetricTile', 'DataStateSummary'],
} as const;
