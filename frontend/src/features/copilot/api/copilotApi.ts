import { postCopilotChat } from '@/services/api';
import type { CopilotChatRequest, CopilotChatResponse } from '@/features/copilot/types';

export function askMarketCopilot(request: CopilotChatRequest): Promise<CopilotChatResponse> {
  return postCopilotChat(request);
}
