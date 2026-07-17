export type MarketBrief = {
  regime: string;
  drivers: string[];
  risks: string[];
  top_sectors: string[];
  summary: string;
};

export type MarketRegime = {
  status: string;
  trend: {
    spy: string;
    qqq: string;
    iwm: string;
    dji?: string;
  };
  breadth: {
    status: string;
    stocks_above_20ma: number;
    stocks_above_50ma: number;
    stocks_above_200ma: number;
    advance_decline_ratio: number;
  };
  volatility: {
    vix: number;
    status: string;
  };
  institutional_activity: {
    distribution_days: number;
    accumulation_days: number;
    follow_through_day: string;
  };
  explanation: string;
};

export type IndexSnapshot = {
  symbol: string;
  price: number;
  change: number;
  change_percent: number;
  volume: number | null;
  ema_20: number | null;
  ema_50: number | null;
  ema_200: number | null;
  sma_50: number | null;
  rsi_14: number | null;
  data_source?: string | null;
  is_live?: boolean | null;
  is_stale?: boolean | null;
  fallback_used?: boolean | null;
  as_of?: string | null;
  quote_is_live?: boolean | null;
  history_is_live?: boolean | null;
  analysis_is_live?: boolean | null;
  history_quality_score?: number | null;
};

export type IndexesResponse = {
  indexes: IndexSnapshot[];
};

export type MarketBreadth = SourceMetadata & {
  total_stocks: number;
  advancing_stocks: number;
  declining_stocks: number;
  unchanged_stocks: number;
  advance_decline_ratio: number | null;
  percent_above_20ema: number;
  percent_above_50ema: number;
  percent_above_200ema: number;
  new_52w_highs: number;
  new_52w_lows: number;
  breadth_score?: number | null;
  breadth_status?: string | null;
};

export type SectorBreadthItem = SourceMetadata & {
  sector: string;
  total_stocks: number;
  advancing_stocks: number;
  declining_stocks: number;
  percent_above_50ema: number;
};

export type MarketBreadthResponse = {
  market: MarketBreadth;
  sectors: SectorBreadthItem[];
};

export type SectorLeader = SourceMetadata & {
  rank: number;
  name: string;
  status: string;
  change: string;
  return_1d?: number;
  return_1w?: number;
  return_mtd?: number;
  return_ytd?: number;
  daily_change_percent?: number;
  weekly_change_percent?: number;
  monthly_change_percent?: number;
  relative_strength_score?: number;
  percent_above_50ema?: number;
  advancing_stocks?: number;
  declining_stocks?: number;
  etf_symbol?: string | null;
};

export type SectorResponse = {
  leaders: SectorLeader[];
  summary: string;
  overall_mode?: string | null;
  coverage_percent?: number | null;
  as_of?: string | null;
};

export type SectorsSummaryResponse = {
  top_sectors: SectorLeader[];
  top_sector_etfs: SectorEtfItem[];
  top_industry_groups: IndustryGroupItem[];
  rotation_summary?: string | null;
  return_interval_default: '1d' | '1w' | 'mtd' | 'ytd' | string;
  as_of?: string | null;
  overall_mode?: string | null;
  cache_status?: string | null;
  refreshing?: boolean | null;
};

export type PerformanceIntervals = {
  oneDay: number | null;
  oneWeek: number | null;
  oneMonth: number | null;
  threeMonths: number | null;
  sixMonths: number | null;
  oneYear: number | null;
};

export type RotationPoint = {
  date?: string | null;
  relativeStrength: number;
  relativeMomentum: number;
};

export type RotationQuadrant = 'leading' | 'weakening' | 'lagging' | 'improving';

export type RotationIntervalData = {
  relativeStrength: number | null;
  relativeMomentum: number | null;
  quadrant: RotationQuadrant | null;
  history?: RotationPoint[];
};

export type SectorDashboardItem = {
  id: string;
  name: string;
  symbol?: string | null;
  parentSector?: string | null;
  returns: PerformanceIntervals;
  rotation: {
    oneWeek?: RotationIntervalData | null;
    oneMonth?: RotationIntervalData | null;
    threeMonths?: RotationIntervalData | null;
  };
  source?: 'live' | 'cached' | 'mock' | 'partial' | string | null;
  metadata?: {
    status?: string | null;
    rotation_score?: number | null;
    coverage_percent?: number | null;
    successful_symbols?: number | null;
    history_quality_score?: number | null;
    fallback_used?: boolean | null;
    as_of?: string | null;
  } | null;
};

export type SectorDashboardResponse = {
  status: string;
  source?: 'live' | 'cached' | 'mock' | 'partial' | string | null;
  benchmark: string;
  sectors: SectorDashboardItem[];
  themes: SectorDashboardItem[];
  theme_legacy_source?: string | null;
  summary?: string | null;
  as_of?: string | null;
  cache_status?: string | null;
  partial?: boolean | null;
  refreshing?: boolean | null;
};

export type IndustryGroupItem = SourceMetadata & {
  rank: number;
  name: string;
  parent_sector: string;
  score: number;
  status: string;
  return_1d: number;
  return_1w: number;
  return_mtd: number;
  return_ytd: number;
  relative_strength_score: number;
  breadth_above_50ema: number;
  percent_above_20ema?: number | null;
  percent_above_50ema?: number | null;
  percent_above_200ema?: number | null;
  advancing_stocks?: number | null;
  declining_stocks?: number | null;
  unchanged_stocks?: number | null;
  new_highs?: number | null;
  new_lows?: number | null;
  volume_participation?: number | null;
  trend_direction?: string | null;
};

export type IndustryGroupResponse = {
  items: IndustryGroupItem[];
  summary: string;
  overall_mode?: string | null;
  coverage_percent?: number | null;
  as_of?: string | null;
};

export type WatchlistItem = {
  ticker: string;
  trend: string;
  setup: string;
  support_zone: string;
  risk_flag: string;
  price?: number | null;
  change?: number | null;
  change_percent?: number | null;
  data_source?: string | null;
  is_live?: boolean | null;
  is_stale?: boolean | null;
  fallback_used?: boolean | null;
  as_of?: string | null;
};

export type WatchlistResponse = {
  items: WatchlistItem[];
};

export type WatchlistSummaryItem = WatchlistItem & {
  symbol?: string;
  rating?: string | null;
  overall_score?: number | null;
  rs_rank?: number | null;
  rs_status?: string | null;
  pattern_name?: string | null;
  pattern_confidence?: number | null;
};

export type WatchlistSummaryResponse = {
  items: WatchlistSummaryItem[];
  summary?: string | null;
  cache_status?: string | null;
};

export type RiskResponse = {
  risk_level: string;
  main_risks: string[];
  suggested_positioning: string;
};

export type MarketHealthComponents = {
  momentum: number;
  breadth: number;
  trend: number;
  volume: number;
  institutional: number;
  volatility: number;
  sector_strength: number;
};

export type MarketHealthResponse = {
  overall_score: number;
  status: string;
  components: MarketHealthComponents;
  component_explanations: Record<string, string>;
  summary: string;
  improving_factors: string[];
  weakening_factors: string[];
  decision_confidence?: DecisionConfidenceResponse | null;
  data_quality?: {
    live_components?: string[];
    fallback_components?: string[];
    mock_components?: string[];
    overall_mode?: 'live' | 'mixed' | 'mock' | string;
    breadth_universe?: string | null;
    breadth_coverage_percent?: number | null;
    leadership_coverage_percent?: number | null;
  } | null;
};

export type SectorEtfItem = SourceMetadata & {
  symbol: string;
  name: string;
  sector: string;
  price: number;
  change_percent: number;
  return_1d: number;
  return_1w: number;
  return_mtd: number;
  return_ytd: number;
  return_1m: number;
  relative_strength_score: number;
  volume_trend: string;
  status: string;
  quote_source?: string | null;
  history_source?: string | null;
  quote_is_live?: boolean | null;
  history_is_live?: boolean | null;
  ema_20?: number | null;
  ema_50?: number | null;
  trend_status?: string | null;
  rotation_score?: number | null;
};

export type SectorEtfResponse = {
  items: SectorEtfItem[];
  summary: string;
  overall_mode?: string | null;
  coverage_percent?: number | null;
  as_of?: string | null;
};

export type MarketCapRotationItem = {
  category: string;
  symbol: string;
  score: number;
  return_1w: number;
  return_1m: number;
  relative_strength: number;
  money_flow: string;
  status: string;
};

export type MarketCapRotationResponse = {
  items: MarketCapRotationItem[];
  leader: string;
  laggard: string;
  summary: string;
};

export type FearGreedComponent = {
  key: string;
  label: string;
  score: number;
  status: string;
  explanation: string;
};

export type FearGreedResponse = {
  score: number;
  status: string;
  components: FearGreedComponent[];
  summary: string;
};

export type ProbabilityItem = {
  strategy: string;
  probability: number;
  confidence: number;
  explanation: string;
};

export type ProbabilityResponse = {
  items: ProbabilityItem[];
  summary: string;
};

export type LeadershipStock = SourceMetadata & {
  symbol: string;
  score: number;
  reason: string;
  relative_strength: number;
  category?: string | null;
  change_in_rs?: number | null;
  trend_status?: string | null;
  sector?: string | null;
  industry_group?: string | null;
};

export type LeadershipCategory = {
  category: string;
  items: LeadershipStock[];
};

export type LeadershipResponse = {
  categories: LeadershipCategory[];
  summary: string;
  overall_mode?: string | null;
  coverage_percent?: number | null;
  as_of?: string | null;
};

export type DecisionConfidenceContributor = {
  label: string;
  score: number;
  signal: string;
};

export type DecisionConfidenceResponse = {
  score: number;
  status: string;
  contributors: DecisionConfidenceContributor[];
  disagreements: string[];
  summary: string;
};

export type DashboardComparisonItem = {
  metric: string;
  today: number | string;
  yesterday: number | string;
  change: number | string;
};

export type DashboardComparisonResponse = {
  items: DashboardComparisonItem[];
  summary: string;
};

export type IndustryRotationSector = {
  sector: string;
  strongest_industry_groups: string[];
  weakest_industry_groups: string[];
  improving: string[];
  deteriorating: string[];
};

export type IndustryRotationResponse = {
  sectors: IndustryRotationSector[];
  summary: string;
  overall_mode?: string | null;
  coverage_percent?: number | null;
  as_of?: string | null;
};

export type RiskDashboardContributor = {
  label: string;
  impact: string;
  explanation: string;
};

export type RiskDashboardV2Response = {
  score: number;
  contributors: RiskDashboardContributor[];
  warnings: string[];
  upcoming_events: string[];
  summary: string;
};

export type MarketSentimentSignal = {
  key?: string | null;
  label: string;
  score: number;
  status: string;
  explanation: string;
  value?: number | string | null;
  previous_value?: number | string | null;
  trend?: string | null;
  metadata?: Record<string, unknown> | null;
};

export type MarketSentimentResponse = {
  score: number;
  status: string;
  signals: MarketSentimentSignal[];
  opportunities: string[];
  risks: string[];
  summary: string;
  confidence?: number | null;
  methodology?: string | null;
  official_index?: boolean | null;
  metadata?: Record<string, unknown> | null;
  overall_mode?: string | null;
  limitations?: string[];
};

export type MoneyFlowItem = {
  area: string;
  score: number;
  status: string;
  flow: string;
  change_1d: number;
  change_1w: number;
  summary: string;
  metadata?: Record<string, unknown> | null;
};

export type MoneyFlowResponse = {
  score: number;
  status: string;
  items: MoneyFlowItem[];
  summary: string;
  methodology?: string | null;
  inflow_leaders?: MoneyFlowItem[];
  outflow_leaders?: MoneyFlowItem[];
  metadata?: Record<string, unknown> | null;
};

export type BlockTradeCandidate = {
  symbol: string;
  date?: string | null;
  price?: number | null;
  volume?: number | null;
  notional?: number | null;
  side?: string | null;
  reason?: string | null;
  confidence?: number | null;
  source?: string | null;
  is_live?: boolean | null;
  fallback_used?: boolean | null;
};

export type InstitutionalDashboardResponse = {
  score: number;
  status: string;
  accumulation_distribution: string;
  block_trade_bias: string;
  dark_pool_bias: string;
  program_trading: string;
  signals: string[];
  risks: string[];
  summary: string;
  block_trade_candidates?: BlockTradeCandidate[];
  block_notional_by_symbol?: Record<string, number>;
  block_notional_by_sector?: Record<string, number>;
  repeated_large_print_symbols?: string[];
  confidence?: number | null;
  limitations?: string[];
  metadata?: Record<string, unknown> | null;
};

export type OptionsIntelligenceResponse = {
  score: number;
  status: string;
  put_call_ratio: number;
  implied_volatility_rank: number;
  skew: string;
  options_flow_bias: string;
  unusual_activity: string[];
  summary: string;
  market_summary?: string | number | {
    average_expected_move?: string | number | null;
    estimated_gamma_regime?: string | number | null;
    items_analyzed?: string | number | null;
  } | null;
  items?: SymbolOptionsIntelligence[];
  expected_move?: number | null;
  estimated_gamma_regime?: string | null;
  call_wall?: number | null;
  put_wall?: number | null;
  confidence?: number | null;
  metadata?: Record<string, unknown> | null;
};

export type SymbolOptionsIntelligence = {
  symbol: string;
  score: number;
  status: string;
  put_call_ratio: number | null;
  implied_volatility_rank: number | null;
  expected_move?: number | null;
  estimated_gamma_regime?: string | null;
  call_wall?: number | null;
  put_wall?: number | null;
  options_flow_bias?: string | null;
  summary: string;
  metadata?: Record<string, unknown> | null;
};

export type LiquidityDashboardResponse = {
  score: number;
  status: string;
  spread_condition: string;
  depth_condition: string;
  funding_condition: string;
  volume_condition: string;
  warnings: string[];
  summary: string;
  items?: SymbolLiquidityResponse[];
  metadata?: Record<string, unknown> | null;
};

export type SymbolLiquidityResponse = {
  symbol: string;
  score: number;
  status: string;
  spread_condition?: string | null;
  depth_condition?: string | null;
  funding_condition?: string | null;
  volume_condition?: string | null;
  warnings?: string[];
  summary: string;
  metadata?: Record<string, unknown> | null;
};

export type InstitutionalIntelligenceResponse = {
  sentiment: MarketSentimentResponse;
  money_flow: MoneyFlowResponse;
  institutional: InstitutionalDashboardResponse;
  options: OptionsIntelligenceResponse;
  liquidity: LiquidityDashboardResponse;
  summary: string;
};

export type SuggestedExposure = {
  stocks: number;
  cash: number;
  margin: string;
  options: string;
};

export type AggressivenessResponse = {
  score: number;
  status: string;
  suggested_exposure: SuggestedExposure;
  summary: string;
  reasons: string[];
  cautions: string[];
};

export type TradingStyleItem = {
  style: string;
  score: number;
  rating: number;
  status: string;
  reason: string;
};

export type TradingStyleResponse = {
  items: TradingStyleItem[];
  preferred_style: string;
  summary: string;
};

export type MarketChecklistItem = {
  label: string;
  passed: boolean;
  value: string;
};

export type MarketChecklistResponse = {
  score: number;
  max_score: number;
  grade: string;
  items: MarketChecklistItem[];
  summary: string;
};

export type MarketPlaybookResponse = {
  headline: string;
  summary: string;
  preferred_strategy: string;
  suggested_aggressiveness: string;
  top_sector: string;
  top_industry_group: string;
  cap_rotation_leader: string;
  main_risk: string;
  action_guidelines: string[];
  avoid: string[];
  disclaimer: string;
};

export type DecisionDashboardResponse = {
  aggressiveness: AggressivenessResponse;
  trading_styles: TradingStyleResponse;
  checklist: MarketChecklistResponse;
  playbook: MarketPlaybookResponse;
  probabilities: ProbabilityResponse;
  leadership: LeadershipResponse;
  decision_confidence: DecisionConfidenceResponse;
  comparison: DashboardComparisonResponse;
  industry_rotation: IndustryRotationResponse;
  risk_dashboard: RiskDashboardV2Response;
  institutional_intelligence: InstitutionalIntelligenceResponse;
};

export type CacheMetadata = {
  bootstrap?: boolean;
  refreshing?: boolean;
  cache_status?: 'fresh' | 'stale' | 'miss' | string | null;
  cache_age_seconds?: number | null;
  is_stale?: boolean | null;
  generated_at?: string | null;
  next_refresh_at?: string | null;
};

export type MarketCoreSnapshot = {
  indexes: IndexSnapshot[];
  market_health?: MarketHealthResponse | null;
  decision_summary: {
    playbook?: MarketPlaybookResponse | null;
    aggressiveness?: AggressivenessResponse | null;
    preferred_style?: string | null;
    main_risk?: string | null;
  };
  breadth_summary?: {
    breadth_score?: number | null;
    breadth_status?: string | null;
    percent_above_50ema?: number | null;
    coverage_percent?: number | null;
    overall_mode?: string | null;
    universe?: string | null;
  };
  top_sector?: SectorLeader | null;
  top_industry_group?: IndustryGroupItem | null;
  as_of?: string | null;
  overall_mode?: string | null;
} & CacheMetadata;

export type HomeDashboardResponse = {
  core: MarketCoreSnapshot;
  risk_summary: {
    score?: number | null;
    status?: string | null;
    top_contributors: RiskDashboardContributor[];
    summary?: string | null;
  };
  watchlist_summary: {
    items: {
      symbol: string;
      price?: number | null;
      change_percent?: number | null;
      rating?: string | null;
      score?: number | null;
      main_setup?: string | null;
      source?: string | null;
      is_live?: boolean | null;
      fallback_used?: boolean | null;
    }[];
  };
} & CacheMetadata;

export type DailyReport = {
  date: string;
  title: string;
  executive_summary: string;
  market_regime: string;
  key_drivers: string[];
  main_risks: string[];
  sector_leaders: string[];
  tomorrow_watch: string[];
  strategy_note: string;
  volume_analysis?: DailyVolumeAnalysis;
  risk_plans?: DailyRiskPlans;
  multi_timeframe?: DailyMultiTimeframe;
  market_health?: MarketHealthResponse;
  sector_etfs?: SectorEtfResponse;
  industry_groups?: IndustryGroupResponse;
  cap_rotation?: MarketCapRotationResponse;
  fear_greed?: FearGreedResponse;
  decision_dashboard?: DecisionDashboardResponse;
  probabilities?: ProbabilityResponse;
  leadership?: LeadershipResponse;
  decision_confidence?: DecisionConfidenceResponse;
  comparison?: DashboardComparisonResponse;
  industry_rotation?: IndustryRotationResponse;
  risk_dashboard?: RiskDashboardV2Response;
  institutional_intelligence?: InstitutionalIntelligenceResponse;
  ai_summary?: MarketAISummary | null;
  report_id?: string | null;
  market_date?: string | null;
  generated_time?: string | null;
  report_snapshot?: Record<string, unknown>;
  report_narrative?: Record<string, unknown>;
  report_changes?: Record<string, unknown>;
  signal_convergence?: Record<string, unknown>;
  hidden_warnings?: string[];
  hidden_confirmations?: string[];
  market_conviction?: Record<string, unknown>;
  decision_checklist?: Record<string, unknown>;
  recommendation_confidence?: Record<string, unknown>;
  scenario_plan?: Record<string, unknown>[];
  previous_playbook_review?: Record<string, unknown>;
  market_evolution?: Record<string, unknown>;
  signal_relationships?: string[];
  trade_off_analysis?: Record<string, unknown>;
  report_commentary?: Record<string, unknown>;
  indexes?: IndexSnapshot[];
  index_histories?: Record<string, number[]>;
  watchlist_summary?: Record<string, unknown> | null;
  sector_dashboard?: Record<string, unknown> | null;
  stock_charts?: Record<string, unknown>[];
  economic_calendar?: Record<string, unknown>[];
};

export type MarketAISummary = {
  type: string;
  headline: string;
  summary: string;
  confidence: number;
  generated_by: string;
  next_update: string;
  key_points: string[];
  opportunities: string[];
  risks: string[];
  what_to_watch: string[];
  disclaimer: string;
};

export type AIChatRequest = {
  message: string;
  symbol?: string | null;
};

export type AIChatResponse = {
  type: string;
  answer: string;
  key_points: string[];
  risks: string[];
  what_to_watch: string[];
  related_symbols: string[];
  confidence: number;
  generated_by: string;
  disclaimer: string;
};

export type StockAnalysisAggregate = {
  symbol: string;
  supportResistance?: SupportResistanceResponse | null;
  trendline?: TrendlineResponse | null;
  volumeAnalysis?: VolumeAnalysis | null;
  riskPlan?: RiskPlan | null;
  multiTimeframe?: MultiTimeframeItem | null;
  multiTimeframeSignals?: MultiTimeframeTechnicalSignals | null;
  patterns?: PatternResponse | null;
  relativeStrength?: RelativeStrengthItem | null;
  leadershipSignal?: StockLeadershipSignal | null;
  stockRating?: StockRatingItem | null;
  options?: SymbolOptionsIntelligence | null;
  liquidity?: SymbolLiquidityResponse | null;
  partial?: boolean;
  errors?: Record<string, string>;
};

export type TimeframeSignalName =
  | 'strong_bearish'
  | 'bearish'
  | 'neutral'
  | 'bullish'
  | 'strong_bullish'
  | 'unavailable';

export type TimeframeSignalStrength = 'weak' | 'moderate' | 'strong' | 'unavailable';

export type TimeframeSignalDataStatus =
  | 'live'
  | 'test'
  | 'cached'
  | 'stale'
  | 'fallback'
  | 'mixed'
  | 'partial'
  | 'mock'
  | 'unavailable';

export type TimeframeSignalEvidence = {
  key: string;
  label: string;
  value?: string | number | boolean | null;
  sourceStatus?: TimeframeSignalDataStatus | string | null;
};

export type TimeframeSignalInput = {
  key: string;
  label: string;
  timeframe: 'short' | 'medium' | 'long' | string;
  contribution?: number | null;
  weight: number;
  value?: string | number | boolean | null;
  sourceStatus: TimeframeSignalDataStatus | string;
  available: boolean;
};

export type TimeframeTechnicalSignal = {
  timeframe: 'short' | 'medium' | 'long';
  horizonLabel: string;
  signal: TimeframeSignalName;
  score: number | null;
  strength: TimeframeSignalStrength;
  headline: string;
  explanation: string;
  positiveEvidence: TimeframeSignalEvidence[];
  negativeEvidence: TimeframeSignalEvidence[];
  availableInputs: number;
  requiredInputs: number;
  dataStatus: TimeframeSignalDataStatus;
  asOf: string | null;
  inputs?: TimeframeSignalInput[];
};

export type MultiTimeframeTechnicalSignals = {
  short: TimeframeTechnicalSignal;
  medium: TimeframeTechnicalSignal;
  long: TimeframeTechnicalSignal;
  overallDataStatus: TimeframeSignalDataStatus | string;
  generatedAt: string | null;
  methodologyVersion: string;
};

export type LeadershipSignalName =
  | 'leader'
  | 'emerging_leader'
  | 'follower'
  | 'lagging'
  | 'unavailable';

export type StockLeadershipSignal = {
  signal: LeadershipSignalName;
  score: number | null;
  strength: TimeframeSignalStrength;
  explanation: string;
  positiveEvidence: string[];
  limitingEvidence: string[];
  availableInputs: number;
  requiredInputs: number;
  dataStatus: TimeframeSignalDataStatus | string;
  asOf?: string | null;
  methodologyVersion: string;
};

export type ProviderStatus = {
  mode?: string;
  data_status?: string;
  source?: string;
  data_provider: string;
  market_data_provider: string;
  configured_provider?: string;
  configured_quote_provider?: string;
  configured_history_provider?: string;
  active_provider?: string;
  active_quote_provider?: string;
  active_history_provider?: string;
  live_ready: boolean;
  history_ready?: boolean;
  fallback_enabled?: boolean;
  fallback_active?: boolean;
  cache_status?: ProviderCacheStatus;
  provider_routing?: ProviderRoutingStatus;
  provider_capabilities?: Record<string, ProviderCapabilityStatus>;
  quote_capability?: ProviderCapabilityStatus | null;
  history_capability?: ProviderCapabilityStatus | null;
  health?: ProviderHealth;
  quote_health?: ProviderHealth;
  history_health?: ProviderHealth;
  test_data?: TestDataStatus;
};

export type ProviderCapabilityStatus = {
  provider: string;
  supports_quotes: boolean;
  supports_batch_quotes: boolean;
  supports_daily_history: boolean;
  supports_intraday_history: boolean;
  supports_macro?: boolean;
  supports_economic_calendar?: boolean;
  quote_access_state: 'available' | 'restricted' | 'unavailable' | 'unknown' | string;
  daily_history_access_state: 'available' | 'restricted' | 'unavailable' | 'unknown' | string;
  notes?: string[];
  last_restricted_at?: string | null;
  restriction_reason?: string | null;
};

export type ProviderRoutingStatus = {
  configured_quote_provider?: string;
  configured_history_provider?: string;
  capabilities?: Record<string, ProviderCapabilityStatus>;
};

export type IntelligenceStatus = {
  overall_mode?: string | null;
  data_status?: string | null;
  source?: string | null;
  sentiment_provider?: string | null;
  options_provider?: string | null;
  trade_flow_provider?: string | null;
  liquidity_provider?: string | null;
  fallback_enabled?: boolean | null;
  sentiment_health?: ProviderHealth | null;
  options_health?: ProviderHealth | null;
  trade_flow_health?: ProviderHealth | null;
  liquidity_health?: ProviderHealth | null;
};

export type TestDataScenario = {
  id: string;
  label: string;
  description: string;
};

export type TestDataStatus = {
  mode: string;
  scenario: string;
  seed: string;
  generated_at: string;
  last_regenerated?: string;
  source: string;
  data_status: string;
  is_mock: boolean;
  schema_version: number;
  label?: string;
  scenarios?: TestDataScenario[];
};

export type TestDataScenariosResponse = {
  items: TestDataScenario[];
};

export type RegenerateTestDataRequest = {
  scenario?: string | null;
  seed?: string | null;
};

export type RegenerateTestDataResponse = {
  status: string;
  message: string;
  test_data: TestDataStatus;
  seed: string;
  scenario: string;
  generated_at: string;
};

export type ProviderHealth = {
  provider: string;
  enabled: boolean;
  configured: boolean;
  reachable: boolean;
  last_successful_request: string | null;
  last_error: string | null;
  fallback_active: boolean;
  status?: string | null;
  checked_at?: string | null;
  response_time_ms?: number | null;
  last_success_at?: string | null;
  last_failure_at?: string | null;
  recent_error_count?: number | null;
  rate_limit_state?: string | null;
  message?: string | null;
  capabilities?: {
    quotes: boolean;
    daily_history: boolean;
    intraday_history: boolean;
    adjusted_history: boolean;
    volume: boolean;
  } | null;
};

export type ProviderCacheStatus = {
  items?: number;
  keys?: string[];
  repository?: {
    items?: number;
    keys?: string[];
    hit_count?: number;
    miss_count?: number;
    persistent_hit_count?: number;
    stale_hit_count?: number;
    write_count?: number;
    oldest_item_age_seconds?: number;
    newest_item_age_seconds?: number;
    persistent?: MarketDataPersistentCacheStatus;
    provider_routing?: ProviderRoutingStatus;
    repository_metrics?: Record<string, unknown>;
  };
  provider_cache?: {
    items?: number;
    keys?: string[];
    persistent?: Record<string, unknown>;
  };
  persistent?: Record<string, unknown>;
};

export type MarketDataPersistentCacheStatus = {
  enabled?: boolean;
  healthy?: boolean;
  entries?: number;
  fresh_entries?: number;
  stale_entries?: number;
  expired_entries?: number;
  domain_counts?: Record<string, number>;
  provider_counts?: Record<string, number>;
  database_size_bytes?: number;
  database_size_mb?: number;
  oldest_entry_age_seconds?: number | null;
  newest_entry_age_seconds?: number | null;
  last_cleanup_at?: string | null;
  read_errors?: number;
  write_errors?: number;
  corrupt_entries?: number;
};

export type ServiceCacheStatus = {
  items: number;
  keys: string[];
  hit_count: number;
  miss_count: number;
  compute_count: number;
  avoided_duplicate_computations: number;
  oldest_item_age: number | null;
  newest_item_age: number | null;
  removed?: number;
};

export type UniverseStatus = {
  breadth_universe: string;
  configured_symbols: number;
  last_successful_symbols: number;
  coverage_percent: number;
  live_symbols?: number | null;
  fallback_symbols?: number | null;
  failed_symbols_count?: number | null;
  overall_mode?: string | null;
  as_of?: string | null;
};

export type QuoteData = {
  symbol: string;
  price: number;
  change: number;
  change_percent: number;
  open: number | null;
  high: number | null;
  low: number | null;
  previous_close: number | null;
  volume: number | null;
  timestamp: string;
  source: string;
  is_live: boolean;
  is_stale: boolean;
  fallback_used: boolean;
  provider?: string | null;
  requested_provider?: string | null;
  original_provider?: string | null;
  source_state?: string | null;
  fetched_at?: string | null;
  cache_hit?: boolean;
  cache_age_seconds?: number | null;
  memory_cache_hit?: boolean;
  persistent_cache_hit?: boolean;
  expires_at?: string | null;
  stale_until?: string | null;
  background_refresh_started?: boolean;
  capability_state?: string | null;
  fallback_reason?: string | null;
};

export type CandleData = {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

export type HistoryData = {
  symbol: string;
  candles: CandleData[];
  timeframe: string;
  source: string;
  is_live: boolean;
  is_stale: boolean;
  fallback_used: boolean;
  as_of: string;
  adjusted?: boolean;
  requested_days?: number | null;
  returned_candles?: number | null;
  error_message?: string | null;
  provider?: string | null;
  requested_provider?: string | null;
  original_provider?: string | null;
  source_state?: string | null;
  fetched_at?: string | null;
  cache_hit?: boolean;
  cache_age_seconds?: number | null;
  memory_cache_hit?: boolean;
  persistent_cache_hit?: boolean;
  expires_at?: string | null;
  stale_until?: string | null;
  background_refresh_started?: boolean;
  capability_state?: string | null;
  fallback_reason?: string | null;
};

export type LiveQuotesResponse = {
  items: QuoteData[];
};

export type Candle = {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

export type PatternKeyLevels = {
  support?: number | null;
  resistance?: number | null;
  neckline?: number | null;
  breakout?: number | null;
  stop_reference?: number | null;
};

export type PatternMarker = {
  date: string;
  label: string;
  price: number;
};

export type VolumeConfirmation = {
  volume_quality: string;
  relative_volume: number | null;
  signals: string[];
  summary: string;
};

export type SourceMetadata = {
  data_source?: string | null;
  overall_mode?: string | null;
  coverage_percent?: number | null;
  successful_symbols?: number | null;
  universe?: string | null;
  universe_size?: number | null;
  analysis_is_live?: boolean | null;
  history_is_live?: boolean | null;
  is_live?: boolean | null;
  fallback_used?: boolean | null;
  as_of?: string | null;
  history_quality_score?: number | null;
};

export type AnalysisDataQuality = {
  history_source?: string | null;
  overall_mode?: 'live' | 'mixed' | 'mock' | string;
  live_dependencies?: string[];
  fallback_dependencies?: string[];
  mock_dependencies?: string[];
  live_components?: string[];
  fallback_components?: string[];
  mock_components?: string[];
  history_quality_score?: number | null;
};

export type DetectedPattern = {
  id: string;
  symbol: string;
  name: string;
  type: string;
  direction: string;
  status: string;
  confidence: number;
  timeframe: string;
  description: string;
  key_levels: PatternKeyLevels;
  chart_data: Candle[];
  markers: PatternMarker[];
  volume_confirmation?: VolumeConfirmation | null;
  data_source?: string | null;
  is_live?: boolean | null;
};

export type PatternResponse = {
  symbol: string;
  patterns: DetectedPattern[];
};

export type PriceZone = {
  low: number;
  high: number;
  strength: number;
  reason: string;
};

export type MovingAverageSupport = {
  ema_20: number | null;
  ema_50: number | null;
};

export type SupportResistanceResponse = SourceMetadata & {
  symbol: string;
  current_price: number;
  support_zones: PriceZone[];
  resistance_zones: PriceZone[];
  breakout_level: number | null;
  stop_reference: number | null;
  moving_average_support: MovingAverageSupport;
};

export type TrendlineDetail = {
  detected: boolean;
  slope: number | null;
  touch_count: number;
  start_date: string | null;
  end_date: string | null;
  start_price: number | null;
  end_price: number | null;
  current_line_value: number | null;
  distance_percent: number | null;
  status: string;
};

export type TrendlineBreak = {
  broken: boolean;
  direction: string;
  description: string;
};

export type TrendlineResponse = SourceMetadata & {
  symbol: string;
  current_price: number;
  rising_support: TrendlineDetail;
  falling_resistance: TrendlineDetail;
  trendline_break: TrendlineBreak;
  summary: string;
};

export type VolumeAnalysis = SourceMetadata & {
  symbol: string;
  average_volume_20: number | null;
  relative_volume: number | null;
  status: string;
  signals: string[];
  volume_quality: string;
  volume_quality_score: number;
  distribution_volume: boolean;
  accumulation_volume: boolean;
  dry_up: boolean;
  climax_run: boolean;
  breakout_volume: boolean;
  summary: string;
};

export type VolumeAnalysisResponse = {
  items: VolumeAnalysis[];
  summary: string;
};

export type RiskPlan = {
  symbol: string;
  current_price: number;
  entry: number;
  stop_loss: number;
  target_1: number;
  target_2: number;
  atr_14: number | null;
  risk_percent: number;
  reward_percent_target_1: number;
  reward_percent_target_2: number;
  risk_reward_target_1: number;
  risk_reward_target_2: number;
  volatility_level: string;
  risk_level: string;
  position_size_note: string;
  summary: string;
  data_quality?: AnalysisDataQuality | null;
};

export type RiskPlanResponse = {
  items: RiskPlan[];
  summary: string;
};

export type TimeframeAnalysis = {
  timeframe: string;
  trend: string;
  price_vs_ema20: string;
  price_vs_ema50: string;
  momentum: string;
  structure: string;
  score: number;
};

export type MultiTimeframeItem = {
  symbol: string;
  alignment: string;
  alignment_score: number;
  timeframes: TimeframeAnalysis[];
  summary: string;
  data_source?: string | null;
  is_live?: boolean | null;
};

export type MultiTimeframeResponse = {
  items: MultiTimeframeItem[];
  summary: string;
};

export type RelativeStrengthItem = {
  symbol: string;
  sector: string;
  rs_vs_spy: number;
  rs_vs_qqq: number;
  rs_vs_sector: number;
  return_5d: number;
  return_20d: number;
  return_60d: number;
  benchmark_return_20d: number;
  sector_return_20d: number;
  overall_rs_score: number;
  rank: number;
  status: string;
  explanation: string;
  data_source?: string | null;
  analysis_is_live?: boolean | null;
  fallback_used?: boolean | null;
  as_of?: string | null;
  history_quality_score?: number | null;
};

export type RelativeStrengthResponse = {
  items: RelativeStrengthItem[];
  summary: string;
};

export type StockRatingComponents = {
  relative_strength: number;
  pattern_quality: number;
  sector_strength: number;
  market_alignment: number;
  institutional_support: number;
  risk_control: number;
};

export type StockRatingItem = {
  symbol: string;
  overall_score: number;
  rating: string;
  status: string;
  components: StockRatingComponents;
  risk_level: string;
  strengths: string[];
  warnings: string[];
  explanation: string;
  data_quality?: AnalysisDataQuality | null;
};

export type StockRatingResponse = {
  items: StockRatingItem[];
  summary: string;
};

export type InstitutionalDay = {
  date: string;
  close: number;
  volume: number;
  change_percent: number;
  reason: string;
};

export type FollowThroughDay = {
  triggered: boolean;
  date: string | null;
  index: string | null;
  gain_percent: number | null;
};

export type IndexInstitutionalActivity = {
  symbol: string;
  distribution_days: InstitutionalDay[];
  accumulation_days: InstitutionalDay[];
  stall_days: InstitutionalDay[];
  churning_days: InstitutionalDay[];
  follow_through_day: FollowThroughDay;
};

export type InstitutionalActivityBias = {
  bias: string;
  summary: string;
  distribution_count: number;
  accumulation_count: number;
  stall_count: number;
  churning_count: number;
  follow_through_day: FollowThroughDay;
};

export type InstitutionalActivityResponse = {
  bias: InstitutionalActivityBias;
  indexes: IndexInstitutionalActivity[];
};

export type DailyVolumeAnalysis = {
  highest_relative_volume: string;
  best_volume_setup: string;
  distribution_volume_alerts: string[];
};

export type DailyRiskPlans = {
  best_risk_reward_setup: string;
  highest_risk_stock: string;
  risk_summary: string;
};

export type DailyMultiTimeframe = {
  strongest_alignment_stock: string;
  weakest_alignment_stock: string;
  summary: string;
};
