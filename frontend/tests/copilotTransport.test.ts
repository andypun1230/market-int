import {
  CopilotTransportError,
  parseCopilotNDJSON,
  serializeCopilotRequest,
} from '../src/features/copilot/api/copilotStream';
import type { CopilotChatRequest } from '../src/features/copilot/types';

function assert(condition: unknown, message: string) {
  if (!condition) throw new Error(message);
}

function run() {
  const first = parseCopilotNDJSON('', [
    JSON.stringify({ eventId: 'event-1', requestId: 'request-1', type: 'start', payload: { label: 'Planning' } }),
    '{"eventId":"event-2","requestId":"request-1","type":"direct_answer","payload":{"directAnswer":"Part',
  ].join('\n'), 'request-1');
  assert(first.events.length === 1 && first.events[0]?.type === 'start', 'complete NDJSON lines emit immediately');
  assert(first.remainder.includes('"Part'), 'split NDJSON line remains buffered');

  const second = parseCopilotNDJSON(first.remainder, 'ial answer."}}\n', 'request-1', first.events.length);
  assert(second.events[0]?.type === 'direct_answer', 'a line split across chunks is reassembled');
  assert((second.events[0]?.payload as { directAnswer?: string }).directAnswer === 'Partial answer.', 'reassembled event preserves section payload');

  const complete = parseCopilotNDJSON('', `${JSON.stringify({
    eventId: 'event-complete', requestId: 'request-1', type: 'complete', payload: { response: { threadId: 'thread-1', answer: 'Done.' } },
  })}\n`, 'request-1');
  assert(complete.events[0]?.response?.answer === 'Done.', 'complete.payload.response is exposed to the transport');

  let malformed: unknown;
  try {
    parseCopilotNDJSON('', '{not-json}\n', 'request-1');
  } catch (error) {
    malformed = error;
  }
  assert(malformed instanceof CopilotTransportError && malformed.category === 'malformed_stream', 'malformed NDJSON fails with a retryable transport category');

  const request: CopilotChatRequest = {
    context: { generatedAt: '2026-07-22T00:00:00Z', routeName: '/market', screenTitle: 'Market', screenType: 'market', sourceState: 'live' },
    message: 'What is the market condition?',
    requestId: 'request-1',
    threadId: 'thread-1',
  };
  const serialized = serializeCopilotRequest(request);
  assert(serialized.screenContext === request.context, 'Stage 7 request emits screenContext');
  assert(serialized.context === request.context, 'legacy context remains available during the backend migration');
  assert(serialized.responseDepth === 'compact', 'transport applies a bounded default response depth');

  console.log('PASS Copilot NDJSON chunking, completion, malformed-stream handling, and request serialization');
}

run();
