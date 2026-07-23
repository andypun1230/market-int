export const SHARED_COMPONENT_REGISTRY = {
  alertBadges: ['StatusBadge', 'AlertList'],
  confidenceIndicators: ['ConfidenceIndicator', 'ScoreGauge', 'StatusBadge'],
  evidencePanels: ['ExpandableSection', 'DashboardCard'],
  intelligenceCards: ['DashboardCard', 'DecisionCard', 'HeroDecisionCard'],
  summaryComponents: ['CompactSummaryCard', 'SummaryTile', 'MetricTile'],
} as const;
