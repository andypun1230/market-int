import { API_URL } from '@/services/apiConfig';
import type {
  CopilotChatRequest,
  CopilotChatResponse,
  CopilotStreamEventType,
  CopilotStreamEventV1,
} from '@/features/copilot/types';
import { normalizeCopilotChatResponse } from '@/features/copilot/utils/normalizeCopilotResponse';

const STREAM_PATH = '/copilot/chat/stream';
const JSON_PATH = '/copilot/chat';
const STREAM_TIMEOUT_MS = 30_000;
const FALLBACK_STATUSES = new Set([404, 405, 406, 415, 501]);

export type CopilotTransportMode = 'ndjson' | 'json';

export type CopilotStreamResult = {
  mode: CopilotTransportMode;
  response: CopilotChatResponse;
};

export type CopilotStreamOptions = {
  onEvent?: (event: CopilotStreamEventV1) => void;
  signal?: AbortSignal;
  timeoutMs?: number;
};

export class CopilotTransportError extends Error {
  category: 'cancelled' | 'timeout' | 'network' | 'http' | 'malformed_stream' | 'stream_interrupted';
  retryable: boolean;
  partial: boolean;

  constructor(
    category: CopilotTransportError['category'],
    message: string,
    { retryable = false, partial = false }: { retryable?: boolean; partial?: boolean } = {},
  ) {
    super(message);
    this.name = 'CopilotTransportError';
    this.category = category;
    this.retryable = retryable;
    this.partial = partial;
  }
}

export async function streamCopilotChat(
  request: CopilotChatRequest,
  options: CopilotStreamOptions = {},
): Promise<CopilotStreamResult> {
  const timeoutMs = options.timeoutMs ?? STREAM_TIMEOUT_MS;
  const linked = createLinkedAbortController(options.signal, timeoutMs);
  let deliveredEvents = 0;
  try {
    const body = serializeCopilotRequest(request);
    const response = await fetch(`${API_URL}${STREAM_PATH}`, {
      body: JSON.stringify(body),
      headers: {
        Accept: 'application/x-ndjson, application/json',
        'Content-Type': 'application/json',
        'X-Copilot-Request-ID': request.requestId ?? '',
      },
      method: 'POST',
      signal: linked.controller.signal,
    });

    if (FALLBACK_STATUSES.has(response.status)) {
      return {
        mode: 'json',
        response: await requestCopilotJson(request, linked.controller.signal),
      };
    }
    if (!response.ok) {
      throw new CopilotTransportError('http', await responseMessage(response), { retryable: response.status >= 500 });
    }

    const contentType = response.headers.get('content-type')?.toLowerCase() ?? '';
    if (contentType.includes('application/json')) {
      return {
        mode: 'json',
        response: normalizeCopilotChatResponse(await response.json(), {
          requestId: request.requestId,
          threadId: request.threadId,
        }),
      };
    }

    let completedResponse: CopilotChatResponse | null = null;
    const deliver = (event: CopilotStreamEventV1) => {
      deliveredEvents += 1;
      options.onEvent?.(event);
      const rawResponse = event.response ?? responseFromEventPayload(event);
      if (event.type === 'complete' && rawResponse) {
        completedResponse = normalizeCopilotChatResponse(rawResponse, {
          requestId: request.requestId,
          threadId: request.threadId,
        });
      }
    };

    if (response.body && typeof response.body.getReader === 'function') {
      await consumeReadableNDJSON(response.body, request.requestId ?? 'copilot-request', deliver);
    } else {
      consumeBufferedNDJSON(await response.text(), request.requestId ?? 'copilot-request').forEach(deliver);
    }

    if (!completedResponse) {
      throw new CopilotTransportError(
        'stream_interrupted',
        'The Copilot stream ended before a complete response was received.',
        { partial: deliveredEvents > 0, retryable: true },
      );
    }
    return { mode: 'ndjson', response: completedResponse };
  } catch (error) {
    if (error instanceof CopilotTransportError) throw error;
    if (linked.timedOut()) {
      throw new CopilotTransportError('timeout', 'Copilot took longer than the bounded response window.', {
        partial: deliveredEvents > 0,
        retryable: true,
      });
    }
    if (options.signal?.aborted || isAbortError(error)) {
      throw new CopilotTransportError('cancelled', 'Copilot request cancelled.', { partial: deliveredEvents > 0 });
    }
    throw new CopilotTransportError('network', 'Unable to reach Institutional Copilot.', {
      partial: deliveredEvents > 0,
      retryable: true,
    });
  } finally {
    linked.dispose();
  }
}

export function parseCopilotNDJSON(
  currentBuffer: string,
  nextChunk: string,
  requestId: string,
  startingIndex = 0,
): { events: CopilotStreamEventV1[]; remainder: string } {
  const lines = `${currentBuffer}${nextChunk}`.split(/\r?\n/);
  const remainder = lines.pop() ?? '';
  const events = lines.flatMap((line, index) => {
    const parsed = parseStreamLine(line, requestId, startingIndex + index);
    return parsed ? [parsed] : [];
  });
  return { events, remainder };
}

export function normalizeCopilotStreamEvent(
  input: unknown,
  requestId: string,
  index = 0,
): CopilotStreamEventV1 | null {
  const record = asRecord(input);
  if (!record) return null;
  const rawType = text(record.type ?? record.event ?? record.kind).toLowerCase().replaceAll('-', '_');
  const sectionType = rawType === 'section'
    ? text(record.section ?? record.name).toLowerCase().replaceAll('-', '_')
    : rawType;
  const type = normalizeEventType(sectionType);
  if (!type) return null;
  const eventRequestId = text(record.requestId ?? record.request_id) || requestId;
  const payload = record.payload ?? record.data ?? record.sectionData ?? record.section_data;
  const response = asRecord(record.response)
    ?? (type === 'complete' ? asRecord(payload)?.response as CopilotChatResponse | undefined : undefined);
  return {
    schemaVersion: text(record.schemaVersion ?? record.schema_version ?? record.version) || 'copilot-stream-event-v1',
    eventId: text(record.eventId ?? record.event_id ?? record.id) || `${eventRequestId}:${type}:${index}`,
    requestId: eventRequestId,
    type,
    payload,
    response: response as CopilotChatResponse | undefined,
    message: text(record.message) || undefined,
    retryable: typeof record.retryable === 'boolean' ? record.retryable : undefined,
  };
}

async function requestCopilotJson(request: CopilotChatRequest, signal: AbortSignal): Promise<CopilotChatResponse> {
  const response = await fetch(`${API_URL}${JSON_PATH}`, {
    body: JSON.stringify(serializeCopilotRequest(request)),
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    method: 'POST',
    signal,
  });
  if (!response.ok) {
    throw new CopilotTransportError('http', await responseMessage(response), { retryable: response.status >= 500 });
  }
  return normalizeCopilotChatResponse(await response.json(), {
    requestId: request.requestId,
    threadId: request.threadId,
  });
}

export function serializeCopilotRequest(request: CopilotChatRequest) {
  return {
    requestId: request.requestId,
    threadId: request.threadId,
    message: request.message,
    // Keep `context` during the Stage 6-to-7 migration; Pydantic ignores it once
    // `screenContext` becomes canonical and older servers still require it.
    context: request.context,
    screenContext: request.context,
    sessionContext: request.sessionContext,
    history: request.history ?? [],
    responseDepth: request.responseDepth ?? 'compact',
  };
}

async function consumeReadableNDJSON(
  stream: ReadableStream<Uint8Array>,
  requestId: string,
  onEvent: (event: CopilotStreamEventV1) => void,
) {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let eventIndex = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const parsed = parseCopilotNDJSON(buffer, decoder.decode(value, { stream: true }), requestId, eventIndex);
      buffer = parsed.remainder;
      eventIndex += parsed.events.length;
      parsed.events.forEach(onEvent);
    }
    const finalText = `${buffer}${decoder.decode()}`.trim();
    if (finalText) {
      const finalEvent = parseStreamLine(finalText, requestId, eventIndex);
      if (finalEvent) onEvent(finalEvent);
    }
  } finally {
    reader.releaseLock();
  }
}

function consumeBufferedNDJSON(input: string, requestId: string): CopilotStreamEventV1[] {
  return input.split(/\r?\n/).flatMap((line, index) => {
    const parsed = parseStreamLine(line, requestId, index);
    return parsed ? [parsed] : [];
  });
}

function parseStreamLine(line: string, requestId: string, index: number): CopilotStreamEventV1 | null {
  const trimmed = line.trim().replace(/^data:\s*/, '');
  if (!trimmed || trimmed === '[DONE]') return null;
  try {
    return normalizeCopilotStreamEvent(JSON.parse(trimmed), requestId, index);
  } catch {
    throw new CopilotTransportError('malformed_stream', 'Copilot returned a malformed structured stream.', {
      partial: index > 0,
      retryable: true,
    });
  }
}

function responseFromEventPayload(event: CopilotStreamEventV1): CopilotChatResponse | null {
  const payload = asRecord(event.payload);
  if (!payload) return null;
  return (asRecord(payload.response) ?? (event.type === 'complete' ? payload : null)) as CopilotChatResponse | null;
}

function normalizeEventType(input: string): CopilotStreamEventType | null {
  const aliases: Record<string, CopilotStreamEventType> = {
    started: 'start',
    answer: 'direct_answer',
    directanswer: 'direct_answer',
    direct_answer: 'direct_answer',
    supporting_evidence: 'evidence',
    opposing_evidence: 'contradiction',
    contradictory_evidence: 'contradiction',
    condition: 'conditions',
    action: 'actions',
    deep_links: 'actions',
    followups: 'follow_ups',
    suggested_follow_ups: 'follow_ups',
    done: 'complete',
  };
  const normalized = aliases[input] ?? input;
  return [
    'start', 'intent', 'plan', 'status', 'direct_answer', 'reasoning', 'evidence',
    'contradiction', 'conditions', 'actions', 'follow_ups', 'warning', 'complete', 'error',
  ].includes(normalized) ? normalized as CopilotStreamEventType : null;
}

function createLinkedAbortController(externalSignal: AbortSignal | undefined, timeoutMs: number) {
  const controller = new AbortController();
  let didTimeout = false;
  const abortFromExternal = () => controller.abort();
  externalSignal?.addEventListener('abort', abortFromExternal, { once: true });
  if (externalSignal?.aborted) controller.abort();
  const timeout = setTimeout(() => {
    didTimeout = true;
    controller.abort();
  }, timeoutMs);
  return {
    controller,
    timedOut: () => didTimeout,
    dispose: () => {
      clearTimeout(timeout);
      externalSignal?.removeEventListener('abort', abortFromExternal);
    },
  };
}

async function responseMessage(response: Response) {
  try {
    const body = await response.json() as { detail?: string; message?: string };
    return body.detail || body.message || `Copilot request failed (${response.status}).`;
  } catch {
    return `Copilot request failed (${response.status}).`;
  }
}

function asRecord(input: unknown): Record<string, unknown> | null {
  return input !== null && typeof input === 'object' && !Array.isArray(input)
    ? input as Record<string, unknown>
    : null;
}

function text(input: unknown) {
  return typeof input === 'string' ? input.trim() : '';
}

function isAbortError(error: unknown) {
  return error instanceof Error && (error.name === 'AbortError' || error.message.toLowerCase().includes('abort'));
}
