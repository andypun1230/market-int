export type IntelligenceDisplayState =
  | 'live'
  | 'delayed'
  | 'cached'
  | 'partial'
  | 'stale'
  | 'test'
  | 'daily_only'
  | 'unavailable'
  | 'failed';

export type NewsServiceStatus = 'complete' | 'partial' | 'stale' | 'unavailable' | 'failed';

export type NewsIntelligenceDto = {
  status?: unknown;
  provider?: {
    provider?: unknown;
    mode?: unknown;
    source_state?: unknown;
    as_of?: unknown;
  } | null;
  as_of?: unknown;
  events?: unknown;
  limitations?: unknown;
  errors?: unknown;
  freshness?: {
    state?: unknown;
    availability?: unknown;
    warnings?: unknown;
  } | null;
};

export type NewsEventModel = {
  id: string;
  headline: string;
  summary: string | null;
  sourceName: string;
  sourceQuality: 'primary' | 'high_confidence_secondary' | 'supporting_secondary';
  publishedAt: string | null;
  eventStatus: 'confirmed' | 'developing' | 'corrected';
  eventType: string | null;
  materiality: {
    market: number | null;
    entity: number | null;
    user: number | null;
  };
  affectedEntities: string[];
  reactionSummary: string | null;
  evidenceIds: string[];
  state: Exclude<IntelligenceDisplayState, 'daily_only' | 'failed'>;
};

export type NewsIntelligenceModel = {
  state: IntelligenceDisplayState;
  status: NewsServiceStatus;
  provider: string | null;
  asOf: string | null;
  events: NewsEventModel[];
  contradictions: string[];
  evidenceCount: number;
  limitations: string[];
  errors: string[];
};

export type SessionNarrativeDto = {
  status?: unknown;
  availability?: unknown;
  provider?: unknown;
  data_mode?: unknown;
  as_of?: unknown;
  latest_daily_session?: unknown;
  narrative?: {
    headline?: unknown;
    claims?: unknown;
    confidence?: unknown;
    freshness?: unknown;
    caveats?: unknown;
    causality_disclosure?: unknown;
  } | null;
  limitations?: unknown;
  provenance?: {
    test_data_detected?: unknown;
    intraday_supported?: unknown;
  } | null;
};

export type SessionNarrativeModel = {
  state: IntelligenceDisplayState;
  headline: string;
  claims: string[];
  caveats: string[];
  confidence: 'high' | 'moderate' | 'limited' | null;
  provider: string | null;
  asOf: string | null;
  latestDailySession: string | null;
  causalityDisclosure: string | null;
};

export type NewsConsumerPresentation = {
  title: string;
  state: IntelligenceDisplayState;
  stateLabel: string;
  items: NewsEventModel[];
  message: string | null;
};

export type SessionConsumerPresentation = {
  state: IntelligenceDisplayState;
  stateLabel: string;
  headline: string;
  supportingText: string | null;
};
