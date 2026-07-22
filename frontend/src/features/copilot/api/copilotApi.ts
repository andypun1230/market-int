import type { CopilotChatRequest, CopilotChatResponse } from '@/features/copilot/types';
import { streamCopilotChat as requestCopilot } from '@/features/copilot/api/copilotStream';
export {
  CopilotTransportError,
  parseCopilotNDJSON,
  serializeCopilotRequest,
  streamCopilotChat,
  type CopilotStreamOptions,
  type CopilotStreamResult,
} from '@/features/copilot/api/copilotStream';

export function askMarketCopilot(request: CopilotChatRequest): Promise<CopilotChatResponse> {
  return requestCopilot(request).then((result) => result.response);
}
