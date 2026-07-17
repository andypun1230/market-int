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
  | 'mock'
  | 'mixed'
  | 'unavailable';

export type CopilotResponseDepth = 'compact' | 'standard' | 'detailed';

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
  market?: Record<string, unknown>;
  sector?: Record<string, unknown>;
  theme?: Record<string, unknown>;
  watchlist?: Record<string, unknown>;
  stock?: Record<string, unknown>;
  report?: Record<string, unknown>;
  focusedMetric?: CopilotFocusedMetric;
};

export type CopilotMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  createdAt: string;
  response?: CopilotChatResponse;
};

export type CopilotChatRequest = {
  threadId?: string | null;
  message: string;
  context: CopilotContext;
  history?: { role: 'user' | 'assistant'; content: string }[];
  responseDepth?: CopilotResponseDepth;
};

export type CopilotAnswerSections = {
  directAnswer: string;
  why: string[];
  mainCaution?: string | null;
  whatWouldChange: string[];
};

export type CopilotAnswerConfidence = {
  level: 'high' | 'moderate' | 'limited';
  reasons: string[];
};

export type CopilotChatResponse = {
  threadId: string;
  answer: string;
  answerSections?: CopilotAnswerSections | null;
  grounding: {
    contextUsed: string[];
    sourceState: CopilotSourceState;
    generatedAt: string;
  };
  suggestedFollowUps: string[];
  confidence: number;
  answerConfidence?: CopilotAnswerConfidence | null;
  generatedBy: string;
  disclaimer: string;
};
