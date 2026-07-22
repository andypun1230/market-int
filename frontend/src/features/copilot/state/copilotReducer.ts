import type {
  CopilotActionV1,
  CopilotChatRequest,
  CopilotChatResponse,
  CopilotEvidenceV1,
  CopilotMessage,
  CopilotReasoningV1,
  CopilotSessionContextV1,
  CopilotStreamEventV1,
} from '@/features/copilot/types';
import {
  buildPartialCopilotResponse,
  normalizeCopilotAction,
  normalizeCopilotEvidence,
} from '@/features/copilot/utils/normalizeCopilotResponse';

export type CopilotRequestStatus =
  | 'idle'
  | 'requesting'
  | 'streaming'
  | 'complete'
  | 'partial'
  | 'cancelled'
  | 'failed';

export type CopilotResponseDraft = {
  requestId: string;
  stageLabel: string;
  directAnswer: string;
  stance: string | null;
  supportingFactors: string[];
  contradictoryFactors: string[];
  contradictions: string[];
  keyRisks: string[];
  confirmationConditions: string[];
  invalidationConditions: string[];
  missingEvidence: string[];
  evidence: CopilotEvidenceV1[];
  contradictoryEvidence: CopilotEvidenceV1[];
  actions: CopilotActionV1[];
  warnings: string[];
  followUps: string[];
};

export type CopilotConversationState = {
  messages: CopilotMessage[];
  threadId: string | null;
  sessionContext: CopilotSessionContextV1 | null;
  status: CopilotRequestStatus;
  activeRequestId: string | null;
  seenEventIds: string[];
  draft: CopilotResponseDraft | null;
  error: string | null;
  retryable: boolean;
  lastRequest: CopilotChatRequest | null;
};

export type CopilotConversationAction =
  | { type: 'hydrate'; messages: CopilotMessage[]; threadId: string | null; sessionContext?: CopilotSessionContextV1 | null }
  | { type: 'submit'; request: CopilotChatRequest; userMessage: CopilotMessage }
  | { type: 'retry'; request: CopilotChatRequest }
  | { type: 'stream_event'; event: CopilotStreamEventV1 }
  | { type: 'complete'; response: CopilotChatResponse; assistantMessage: CopilotMessage }
  | { type: 'fail'; message: string; retryable: boolean; partial?: boolean }
  | { type: 'cancel' }
  | { type: 'clear' }
  | { type: 'set_session_context'; sessionContext: CopilotSessionContextV1 };

export function createInitialCopilotState(): CopilotConversationState {
  return {
    messages: [],
    threadId: null,
    sessionContext: null,
    status: 'idle',
    activeRequestId: null,
    seenEventIds: [],
    draft: null,
    error: null,
    retryable: false,
    lastRequest: null,
  };
}

export function copilotConversationReducer(
  state: CopilotConversationState,
  action: CopilotConversationAction,
): CopilotConversationState {
  switch (action.type) {
    case 'hydrate':
      if (state.messages.length || state.status !== 'idle') return state;
      return {
        ...state,
        messages: action.messages,
        threadId: action.threadId,
        sessionContext: action.sessionContext ?? null,
      };
    case 'submit':
      return {
        ...state,
        messages: [...state.messages, action.userMessage],
        status: 'requesting',
        activeRequestId: action.request.requestId ?? null,
        seenEventIds: [],
        draft: createDraft(action.request.requestId ?? 'copilot-request'),
        error: null,
        retryable: false,
        lastRequest: action.request,
      };
    case 'retry':
      return {
        ...state,
        status: 'requesting',
        activeRequestId: action.request.requestId ?? null,
        seenEventIds: [],
        draft: createDraft(action.request.requestId ?? 'copilot-request'),
        error: null,
        retryable: false,
        lastRequest: action.request,
      };
    case 'stream_event': {
      if (action.event.requestId !== state.activeRequestId || state.seenEventIds.includes(action.event.eventId)) return state;
      const draft = applyStreamEvent(state.draft ?? createDraft(action.event.requestId), action.event);
      return {
        ...state,
        status: action.event.type === 'error' ? 'partial' : 'streaming',
        seenEventIds: [...state.seenEventIds, action.event.eventId].slice(-160),
        draft,
        error: action.event.type === 'error' ? action.event.message ?? 'Copilot reported a partial result.' : null,
        retryable: action.event.type === 'error' ? Boolean(action.event.retryable) : false,
      };
    }
    case 'complete':
      if (state.activeRequestId && action.response.requestId && state.activeRequestId !== action.response.requestId) return state;
      return {
        ...state,
        messages: [...state.messages, action.assistantMessage],
        threadId: action.response.threadId,
        status: 'complete',
        activeRequestId: null,
        seenEventIds: [],
        draft: null,
        error: null,
        retryable: false,
      };
    case 'fail':
      return {
        ...state,
        status: action.partial && state.draft ? 'partial' : 'failed',
        activeRequestId: null,
        error: action.message,
        retryable: action.retryable,
      };
    case 'cancel':
      return {
        ...state,
        status: state.draft && hasDraftContent(state.draft) ? 'partial' : 'cancelled',
        activeRequestId: null,
        error: state.draft && hasDraftContent(state.draft)
          ? 'Request cancelled. The validated sections received so far are preserved.'
          : 'Request cancelled.',
        retryable: true,
      };
    case 'clear':
      return createInitialCopilotState();
    case 'set_session_context':
      return { ...state, sessionContext: action.sessionContext };
    default:
      return state;
  }
}

export function draftToCopilotResponse(
  draft: CopilotResponseDraft,
  threadId: string | null,
): CopilotChatResponse {
  const response = buildPartialCopilotResponse({
    actions: draft.actions,
    answer: draft.directAnswer || 'Collecting validated evidence…',
    evidence: [...draft.evidence, ...draft.contradictoryEvidence],
    requestId: draft.requestId,
    threadId,
    warnings: draft.warnings,
  });
  const reasoning: CopilotReasoningV1 = {
    schemaVersion: 'copilot-reasoning-v1',
    directAnswer: response.answer,
    stance: draft.stance,
    supportingFactors: factors(draft.supportingFactors),
    contradictoryFactors: factors(draft.contradictoryFactors),
    contradictions: draft.contradictions,
    keyRisks: factors(draft.keyRisks),
    confirmationConditions: factors(draft.confirmationConditions),
    invalidationConditions: factors(draft.invalidationConditions),
    missingEvidence: draft.missingEvidence,
  };
  return {
    ...response,
    reasoning,
    contradictoryEvidence: draft.contradictoryEvidence,
    suggestedFollowUps: draft.followUps,
  };
}

function createDraft(requestId: string): CopilotResponseDraft {
  return {
    requestId,
    stageLabel: 'Classifying the request',
    directAnswer: '',
    stance: null,
    supportingFactors: [],
    contradictoryFactors: [],
    contradictions: [],
    keyRisks: [],
    confirmationConditions: [],
    invalidationConditions: [],
    missingEvidence: [],
    evidence: [],
    contradictoryEvidence: [],
    actions: [],
    warnings: [],
    followUps: [],
  };
}

function applyStreamEvent(draft: CopilotResponseDraft, event: CopilotStreamEventV1): CopilotResponseDraft {
  const payload = asRecord(event.payload);
  switch (event.type) {
    case 'start':
      return { ...draft, stageLabel: text(payload?.label) || event.message || 'Planning the evidence route' };
    case 'intent':
      return {
        ...draft,
        stageLabel: `Intent · ${text(asRecord(payload?.intent)?.intent ?? payload?.intent) || text(event.payload) || 'classified'}`,
      };
    case 'plan':
      return { ...draft, stageLabel: text(payload?.label) || 'Collecting engine evidence' };
    case 'status':
      return { ...draft, stageLabel: text(payload?.label ?? payload?.status) || event.message || draft.stageLabel };
    case 'direct_answer':
      return {
        ...draft,
        stageLabel: 'Building the grounded answer',
        directAnswer: text(payload?.directAnswer ?? payload?.direct_answer ?? payload?.text ?? event.payload) || draft.directAnswer,
        stance: nullableText(payload?.stance) ?? draft.stance,
      };
    case 'reasoning':
      return mergeReasoning(draft, payload);
    case 'evidence': {
      const items = payloadItems(event.payload).map(normalizeCopilotEvidence).filter((item): item is CopilotEvidenceV1 => item !== null);
      return { ...draft, stageLabel: 'Validating supporting evidence', evidence: dedupeEvidence([...draft.evidence, ...items]) };
    }
    case 'contradiction': {
      const items = payloadItems(event.payload).map(normalizeCopilotEvidence).filter((item): item is CopilotEvidenceV1 => item !== null);
      return {
        ...draft,
        stageLabel: 'Testing the counter-thesis',
        contradictoryEvidence: dedupeEvidence([...draft.contradictoryEvidence, ...items]),
        contradictoryFactors: dedupeStrings([
          ...draft.contradictoryFactors,
          ...statementList(payload?.factors ?? payload?.contradictoryFactors ?? payload?.contradictory_factors),
        ]),
        contradictions: dedupeStrings([...draft.contradictions, ...stringList(payload?.contradictions)]),
      };
    }
    case 'conditions':
      return {
        ...draft,
        stageLabel: 'Defining confirmation and invalidation',
        confirmationConditions: dedupeStrings([
          ...draft.confirmationConditions,
          ...statementList(payload?.confirmation ?? payload?.confirmationConditions ?? payload?.confirmation_conditions),
        ]),
        invalidationConditions: dedupeStrings([
          ...draft.invalidationConditions,
          ...statementList(payload?.invalidation ?? payload?.invalidationConditions ?? payload?.invalidation_conditions),
        ]),
      };
    case 'actions': {
      const items = payloadItems(event.payload).map(normalizeCopilotAction).filter((item): item is CopilotActionV1 => item !== null);
      return { ...draft, actions: dedupeActions([...draft.actions, ...items]) };
    }
    case 'follow_ups':
      return {
        ...draft,
        followUps: dedupeStrings([
          ...draft.followUps,
          ...stringList(payload?.suggestedFollowUps ?? payload?.suggested_follow_ups ?? payload?.items ?? event.payload),
        ]),
      };
    case 'warning':
      return { ...draft, warnings: dedupeStrings([...draft.warnings, event.message ?? text(payload?.message ?? event.payload)].filter(Boolean)) };
    case 'error':
      return { ...draft, warnings: dedupeStrings([...draft.warnings, event.message ?? 'One evidence path did not complete.']) };
    case 'complete':
      return { ...draft, stageLabel: 'Complete' };
    default:
      return draft;
  }
}

function mergeReasoning(draft: CopilotResponseDraft, payload: Record<string, unknown> | null): CopilotResponseDraft {
  return {
    ...draft,
    directAnswer: text(payload?.directAnswer ?? payload?.direct_answer) || draft.directAnswer,
    stance: nullableText(payload?.stance) ?? draft.stance,
    supportingFactors: dedupeStrings([...draft.supportingFactors, ...statementList(payload?.supportingFactors ?? payload?.supporting_factors)]),
    contradictoryFactors: dedupeStrings([...draft.contradictoryFactors, ...statementList(payload?.contradictoryFactors ?? payload?.contradictory_factors)]),
    contradictions: dedupeStrings([...draft.contradictions, ...stringList(payload?.contradictions)]),
    keyRisks: dedupeStrings([...draft.keyRisks, ...statementList(payload?.keyRisks ?? payload?.key_risks)]),
    confirmationConditions: dedupeStrings([...draft.confirmationConditions, ...statementList(payload?.confirmationConditions ?? payload?.confirmation_conditions)]),
    invalidationConditions: dedupeStrings([...draft.invalidationConditions, ...statementList(payload?.invalidationConditions ?? payload?.invalidation_conditions)]),
    missingEvidence: dedupeStrings([...draft.missingEvidence, ...stringList(payload?.missingEvidence ?? payload?.missing_evidence)]),
  };
}

function hasDraftContent(draft: CopilotResponseDraft) {
  return Boolean(draft.directAnswer || draft.evidence.length || draft.contradictoryEvidence.length || draft.actions.length);
}

function payloadItems(input: unknown): unknown[] {
  if (Array.isArray(input)) return input;
  const record = asRecord(input);
  const nested = record?.items ?? record?.evidence ?? record?.actions;
  return Array.isArray(nested) ? nested : record ? [record] : [];
}

function dedupeEvidence(items: CopilotEvidenceV1[]) {
  return [...new Map(items.map((item) => [item.evidenceId, item])).values()];
}

function dedupeActions(items: CopilotActionV1[]) {
  return [...new Map(items.map((item) => [item.actionId ?? `${item.label}:${item.route}`, item])).values()];
}

function dedupeStrings(items: string[]) {
  return [...new Set(items.map((item) => item.trim()).filter(Boolean))];
}

function asRecord(input: unknown): Record<string, unknown> | null {
  return input !== null && typeof input === 'object' && !Array.isArray(input)
    ? input as Record<string, unknown>
    : null;
}

function stringList(input: unknown): string[] {
  return Array.isArray(input) ? input.map(text).filter(Boolean) : typeof input === 'string' && input.trim() ? [input.trim()] : [];
}

function statementList(input: unknown): string[] {
  if (typeof input === 'string') return input.trim() ? [input.trim()] : [];
  if (!Array.isArray(input)) return [];
  return input.flatMap((item) => {
    if (typeof item === 'string') return item.trim() ? [item.trim()] : [];
    const record = asRecord(item);
    const statement = text(record?.statement ?? record?.text ?? record?.label);
    return statement ? [statement] : [];
  });
}

function factors(items: string[]) {
  return items.map((statement) => ({ statement, evidenceIds: [] }));
}

function text(input: unknown): string {
  return typeof input === 'string' ? input.trim() : '';
}

function nullableText(input: unknown): string | null {
  return text(input) || null;
}
