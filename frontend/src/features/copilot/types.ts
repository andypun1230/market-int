export type CopilotScreenType =
  | 'home'
  | 'market'
  | 'sector'
  | 'theme'
  | 'watchlist'
  | 'stock'
  | 'report'
  | 'general';

export type CopilotSourceState =
  | 'live'
  | 'delayed'
  | 'cached'
  | 'stale'
  | 'test'
  | 'mock'
  | 'partial'
  | 'mixed'
  | 'unavailable';

export type CopilotResponseDepth = 'compact' | 'standard' | 'detailed';
export type CopilotDataCompleteness = 'complete' | 'partial' | 'unavailable';
export type CopilotAgentStatus = 'complete' | 'partial' | 'stale' | 'unavailable' | 'failed';
export type CopilotEvidenceStance = 'supports' | 'contradicts' | 'neutral';
export type CopilotResponseStatus = 'complete' | 'partial' | 'stale' | 'unavailable' | 'failed';

export type CopilotFocusedMetric = {
  id: string;
  title: string;
  value?: string | number | null;
  status?: string | null;
  timeframe?: string | null;
  description?: string | null;
  calculationInputs?: Record<string, unknown>;
  supportingEvidence?: string[];
  relatedRisks?: string[];
  sourceState?: CopilotSourceState;
};

export type CopilotContext = {
  screenType: CopilotScreenType;
  screenTitle: string;
  routeName: string;
  generatedAt: string;
  sourceState: CopilotSourceState;
  savedSymbols?: string[];
  market?: Record<string, unknown>;
  sector?: Record<string, unknown>;
  theme?: Record<string, unknown>;
  watchlist?: Record<string, unknown>;
  stock?: Record<string, unknown>;
  report?: Record<string, unknown>;
  focusedMetric?: CopilotFocusedMetric;
};

export type CopilotEntityV1 = {
  entityId: string;
  entityType: string;
  displayName: string;
  symbol?: string | null;
  confidence: number;
  resolutionSource: string;
};

export type CopilotSessionContextV1 = {
  schemaVersion: 'copilot-session-context-v1';
  threadId: string;
  activeEntities: CopilotEntityV1[];
  activeIntent: string | null;
  latestReferencedStock: string | null;
  latestReferencedSectorOrTheme: string | null;
  latestReportId: string | null;
  latestThesis: string | null;
  unresolvedQuestion: string | null;
  previousAnswerStance: string | null;
  relevantEvidenceIds: string[];
  currentScreen: CopilotScreenType;
  currentRoute: string;
  updatedAt: string;
};

export type CopilotIntentV1 = {
  schemaVersion: 'copilot-intent-v1' | string;
  intentId: string;
  intent: string;
  subIntent: string;
  entities: CopilotEntityV1[];
  tickerSymbols: string[];
  sectors: string[];
  themes: string[];
  timeHorizon: string;
  requestedOutputType: string;
  decisionSupportRequested: boolean;
  personalizationRelevant: boolean;
  navigationRequested: boolean;
  ambiguityLevel: 'none' | 'low' | 'moderate' | 'high' | string;
  confidence: number;
  requiredAgents: string[];
  optionalAgents: string[];
  prohibitedAssumptions: string[];
  unresolvedEntities: string[];
  clarificationQuestion?: string | null;
};

export type CopilotPlanStepV1 = {
  stepId: string;
  order: number;
  agent: string;
  dependsOn: string[];
  required: boolean;
  parallelGroup: number;
  timeoutMs: number;
  purpose: string;
};

export type CopilotPlanV1 = {
  schemaVersion: 'copilot-plan-v1' | string;
  planId: string;
  intentId: string;
  orderedSteps: CopilotPlanStepV1[];
  requiredAgents: string[];
  optionalAgents: string[];
  dependencies: Record<string, string[]>;
  requiredEntities: string[];
  evidenceRequirements: unknown[];
  freshnessRequirements?: Record<string, unknown> | null;
  responseTemplate?: string | null;
  deepLinkRequirements: string[];
  fallbackRules: string[];
  maximumLatencyMs: number | null;
  parallelExecutionAllowed: boolean;
};

export type CopilotFreshnessV1 = {
  state: CopilotSourceState;
  marketDate?: string | null;
  generatedAt?: string | null;
  observedAt?: string | null;
  expiresAt?: string | null;
  ageSeconds?: number | null;
  completeness?: number | CopilotDataCompleteness | null;
  provider?: string | null;
  warnings?: string[];
  label?: string | null;
};

export type CopilotFreshnessSummaryV1 = {
  overallState: CopilotSourceState;
  marketDates: string[];
  generatedTimestamps: string[];
  currentCount: number;
  staleCount: number;
  partialCount: number;
  unavailableCount: number;
  testCount: number;
  warnings: string[];
};

export type CopilotSourceReferenceV1 = {
  sourceId: string;
  provider: string;
  dataset: string;
  generatedAt?: string | null;
  marketDate?: string | null;
  rawEngineReference?: string | null;
};

export type CopilotEvidenceV1 = {
  schemaVersion: 'copilot-evidence-v1' | string;
  evidenceId: string;
  category: string;
  entity: string;
  metric: string;
  value?: unknown;
  unit?: string | null;
  currentState?: string | null;
  priorValue?: unknown;
  change?: unknown;
  timeframe: string;
  interpretationClass: string;
  source: CopilotSourceReferenceV1;
  freshness: CopilotFreshnessV1;
  confidence: string | number;
  deepLink?: string | null;
  reportReference?: string | null;
  supportsClaimIds: string[];
  contradictsClaimIds: string[];
  /** Derived by the client from claim references or a stream section. */
  stance: CopilotEvidenceStance;
  /** Optional legacy prose retained for older JSON responses. */
  interpretation?: string | null;
};

export type CopilotReasoningFactorV1 = {
  statement: string;
  evidenceIds: string[];
};

export type CopilotReasoningV1 = {
  schemaVersion: 'copilot-reasoning-v1' | string;
  directAnswer: string;
  stance?: string | null;
  confidenceLabel?: string | null;
  thesis?: string | null;
  supportingFactors: CopilotReasoningFactorV1[];
  contradictoryFactors: CopilotReasoningFactorV1[];
  keyRisks: CopilotReasoningFactorV1[];
  confirmationConditions: CopilotReasoningFactorV1[];
  invalidationConditions: CopilotReasoningFactorV1[];
  missingEvidence: string[];
  personalizationNote?: string | null;
  relatedResearch?: string[];
  recommendedAppDestinations?: string[];
  disclaimerClass?: string | null;
  /** Legacy contradiction prose accepted by the compatibility normalizer. */
  contradictions?: string[];
};

export type CopilotActionType =
  | 'navigate'
  | 'open_entity'
  | 'open_report_section'
  | 'open_report'
  | 'highlight';

export type CopilotActionV1 = {
  schemaVersion?: 'copilot-action-v1' | string;
  actionId?: string;
  label: string;
  actionType: CopilotActionType;
  /** Canonical backend field. */
  destinationId?: string | null;
  /** Accepted compatibility alias used by early Stage 7 fixtures. */
  destination?: string | null;
  route?: string | null;
  tab?: string | null;
  subTab?: string | null;
  sectionId?: string | null;
  entity?: string | null;
  highlightTarget?: string | null;
  parameters?: Record<string, string>;
};

export type CopilotGroundingV1 = {
  contextUsed: string[];
  sourceState: CopilotSourceState;
  generatedAt: string;
  marketDate?: string | null;
  providers?: string[];
  evidenceIds?: string[];
  completeness?: number | null;
};

export type CopilotAnswerSections = {
  directAnswer: string;
  why: string[];
  evidenceFor: string[];
  evidenceAgainst: string[];
  mainCaution?: string | null;
  whatWouldConfirm: string[];
  whatWouldInvalidate: string[];
  whatWouldChange: string[];
  keyRisks?: string[];
  missingEvidence?: string[];
};

export type CopilotAnswerConfidence = {
  level: 'high' | 'moderate' | 'limited';
  reasons: string[];
};

export type CopilotValidationResultV1 = {
  status: 'passed' | 'failed' | 'fallback' | string;
  checksRun: string[];
  issues: { check: string; severity: string; message: string }[];
  fallbackUsed: boolean;
};

export type CopilotChatResponse = {
  schemaVersion: 'institutional-copilot-response-v1' | 'copilot-chat-response-v1' | string;
  requestId?: string | null;
  planId?: string | null;
  threadId: string;
  answer: string;
  status?: CopilotResponseStatus;
  intent?: CopilotIntentV1 | null;
  plan?: CopilotPlanV1 | null;
  reasoning?: CopilotReasoningV1 | null;
  answerSections?: CopilotAnswerSections | null;
  evidence?: CopilotEvidenceV1[];
  contradictoryEvidence?: CopilotEvidenceV1[];
  actions?: CopilotActionV1[];
  warnings?: string[];
  missingEvidence?: string[];
  freshnessSummary?: CopilotFreshnessSummaryV1 | null;
  grounding: CopilotGroundingV1;
  suggestedFollowUps: string[];
  confidence: number;
  answerConfidence?: CopilotAnswerConfidence | null;
  generatedBy: string;
  disclaimer: string;
  validation?: CopilotValidationResultV1 | null;
  agentTimingsMs?: Record<string, number>;
};

export type CopilotMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  createdAt: string;
  response?: CopilotChatResponse;
};

export type CopilotChatRequest = {
  requestId?: string;
  threadId?: string | null;
  message: string;
  /** Local canonical name; transport serialization also emits screenContext. */
  context: CopilotContext;
  sessionContext?: CopilotSessionContextV1 | null;
  history?: { role: 'user' | 'assistant'; content: string }[];
  responseDepth?: CopilotResponseDepth;
};

export type CopilotStreamEventType =
  | 'start'
  | 'intent'
  | 'plan'
  | 'status'
  | 'direct_answer'
  | 'reasoning'
  | 'evidence'
  | 'contradiction'
  | 'conditions'
  | 'actions'
  | 'follow_ups'
  | 'warning'
  | 'complete'
  | 'error';

export type CopilotStreamEventV1 = {
  schemaVersion?: 'copilot-stream-event-v1' | string;
  eventId: string;
  requestId: string;
  type: CopilotStreamEventType;
  payload?: unknown;
  response?: CopilotChatResponse;
  message?: string;
  retryable?: boolean;
};
