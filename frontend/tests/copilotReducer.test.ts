import {
  copilotConversationReducer,
  createInitialCopilotState,
  draftToCopilotResponse,
} from '../src/features/copilot/state/copilotReducer';
import { resolveSessionActiveIntent } from '../src/features/copilot/state/sessionContext';
import type {
  CopilotChatRequest,
  CopilotMessage,
  CopilotSessionContextV1,
  CopilotStreamEventV1,
} from '../src/features/copilot/types';

function assert(condition: unknown, message: string) {
  if (!condition) throw new Error(message);
}

const request: CopilotChatRequest = {
  context: { generatedAt: '2026-07-22T00:00:00Z', routeName: '/market', screenTitle: 'Breadth', screenType: 'market', sourceState: 'live' },
  history: [],
  message: 'Why is breadth weak?',
  requestId: 'request-1',
  responseDepth: 'compact',
  threadId: 'thread-1',
};
const userMessage: CopilotMessage = { id: 'user-1', role: 'user', content: request.message, createdAt: '2026-07-22T00:00:00Z' };

function event(type: CopilotStreamEventV1['type'], eventId: string, payload: unknown): CopilotStreamEventV1 {
  return { eventId, requestId: 'request-1', type, payload };
}

function run() {
  let state = copilotConversationReducer(createInitialCopilotState(), { type: 'submit', request, userMessage });
  assert(state.messages.length === 1 && state.status === 'requesting', 'submit adds one user message and begins a bounded request');

  state = copilotConversationReducer(state, { type: 'stream_event', event: event('direct_answer', 'event-1', { directAnswer: 'Breadth is weak.' }) });
  state = copilotConversationReducer(state, { type: 'stream_event', event: event('intent', 'event-intent', { intent: { intent: 'BREADTH_QUERY' } }) });
  assert(state.draft?.stageLabel === 'Intent · BREADTH_QUERY', 'nested intent stream payload updates the stage label');
  state = copilotConversationReducer(state, { type: 'stream_event', event: event('reasoning', 'event-2', {
    supportingFactors: [{ statement: 'The index trend remains intact.', evidenceIds: ['evidence-1'] }],
    contradictoryFactors: [{ statement: 'Participation is narrow.', evidenceIds: ['evidence-2'] }],
    keyRisks: [{ statement: 'Leadership can reverse.', evidenceIds: [] }],
    confirmationConditions: [{ statement: 'Participation broadens.', evidenceIds: [] }],
    invalidationConditions: [{ statement: 'The index loses support.', evidenceIds: [] }],
  }) });
  const beforeDuplicate = state;
  state = copilotConversationReducer(state, { type: 'stream_event', event: event('reasoning', 'event-2', { supportingFactors: ['Duplicate'] }) });
  assert(state === beforeDuplicate, 'duplicate stream event IDs are ignored by identity');
  assert(state.draft?.supportingFactors[0] === 'The index trend remains intact.', 'factor objects are reduced into display-safe statements');
  state = copilotConversationReducer(state, { type: 'stream_event', event: event('contradiction', 'event-contradiction', {
    factors: [{ statement: 'Participation is below the threshold.', evidenceIds: ['evidence-2'] }],
  }) });
  state = copilotConversationReducer(state, { type: 'stream_event', event: event('follow_ups', 'event-follow-ups', {
    suggestedFollowUps: ['Show me breadth.'],
  }) });
  assert(state.draft?.contradictoryFactors.includes('Participation is below the threshold.'), 'contradiction factor stream payload is retained');
  assert(state.draft?.followUps[0] === 'Show me breadth.', 'suggestedFollowUps stream payload is retained');

  state = copilotConversationReducer(state, { type: 'cancel' });
  assert(state.status === 'partial' && state.activeRequestId === null, 'cancellation preserves a meaningful partial response and clears loading');
  assert(state.retryable, 'cancelled requests can be retried');
  const partial = state.draft ? draftToCopilotResponse(state.draft, state.threadId) : null;
  assert(partial?.reasoning?.confirmationConditions[0]?.statement === 'Participation broadens.', 'partial response retains structured conditions');

  const retryRequest = { ...request, requestId: 'request-2' };
  state = copilotConversationReducer(state, { type: 'retry', request: retryRequest });
  assert(state.messages.length === 1, 'retry does not duplicate the original user message');
  assert(state.activeRequestId === 'request-2' && state.status === 'requesting', 'retry starts a new request identity');

  const wrongRequest = { eventId: 'wrong-1', requestId: 'request-old', type: 'direct_answer' as const, payload: { directAnswer: 'Wrong' } };
  const beforeWrongRequest = state;
  state = copilotConversationReducer(state, { type: 'stream_event', event: wrongRequest });
  assert(state === beforeWrongRequest, 'late events from a previous request are ignored');

  let activeIntent = resolveSessionActiveIntent('STOCK_DECISION_SUPPORT', null);
  assert(activeIntent === 'STOCK_DECISION_SUPPORT', 'ARM establishes a substantive stock decision intent');
  activeIntent = resolveSessionActiveIntent('FOLLOW_UP', activeIntent);
  assert(activeIntent === 'STOCK_DECISION_SUPPORT', 'Why preserves the prior substantive ARM intent');
  activeIntent = resolveSessionActiveIntent('FOLLOW_UP', activeIntent);
  assert(activeIntent === 'STOCK_DECISION_SUPPORT', 'a completed Why retry still preserves the substantive intent');
  activeIntent = resolveSessionActiveIntent('FOLLOW_UP', activeIntent);
  assert(activeIntent === 'STOCK_DECISION_SUPPORT', 'What confirms it resolves against the substantive stock intent');
  assert(resolveSessionActiveIntent('FOLLOW_UP', 'FOLLOW_UP') === null, 'follow-up-only history safely falls back to no active intent');

  const armSession: CopilotSessionContextV1 = {
    activeEntities: [{ confidence: 1, displayName: 'ARM', entityId: 'ARM', entityType: 'stock', resolutionSource: 'registry', symbol: 'ARM' }],
    activeIntent,
    currentRoute: '/watchlist',
    currentScreen: 'stock',
    latestReferencedSectorOrTheme: null,
    latestReferencedStock: 'ARM',
    latestReportId: null,
    latestThesis: 'ARM is nearly actionable if confirmation improves.',
    previousAnswerStance: 'nearly_actionable',
    relevantEvidenceIds: ['evidence-arm-1'],
    schemaVersion: 'copilot-session-context-v1',
    threadId: 'thread-arm',
    unresolvedQuestion: null,
    updatedAt: '2026-07-22T00:00:00Z',
  };
  let retryState = copilotConversationReducer(createInitialCopilotState(), {
    messages: [], sessionContext: armSession, threadId: 'thread-arm', type: 'hydrate',
  });
  retryState = copilotConversationReducer(retryState, { type: 'retry', request: retryRequest });
  assert(retryState.sessionContext === armSession, 'retry keeps the persisted ARM session context intact');

  console.log('PASS Copilot reducer streaming, cancellation, retry identity, and substantive follow-up session continuity');
}

run();
