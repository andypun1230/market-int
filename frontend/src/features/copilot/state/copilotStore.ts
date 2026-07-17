import type { CopilotContext, CopilotMessage } from '@/features/copilot/types';

type CopilotLaunchState = {
  context: CopilotContext | null;
  initialPrompt?: string;
};

let launchState: CopilotLaunchState = {
  context: null,
};

const STORAGE_KEY = 'market-intelligence-copilot-threads-v1';
const messagesByThread = new Map<string, CopilotMessage[]>();
hydrateThreads();

export function setCopilotLaunchContext(context: CopilotContext, initialPrompt?: string) {
  launchState = { context, initialPrompt };
}

export function consumeCopilotLaunchContext(): CopilotLaunchState {
  const current = launchState;
  launchState = { context: current.context };
  return current;
}

export function getDefaultCopilotContext(): CopilotContext {
  return {
    generatedAt: new Date().toISOString(),
    routeName: '/ai',
    screenTitle: 'Market Copilot',
    screenType: 'general',
    sourceState: 'unavailable',
  };
}

export function getThreadMessages(threadId: string) {
  return messagesByThread.get(threadId) ?? [];
}

export function saveThreadMessages(threadId: string, messages: CopilotMessage[]) {
  messagesByThread.set(threadId, messages.slice(-16));
  persistThreads();
}

export function clearThreadMessages(threadId: string) {
  messagesByThread.delete(threadId);
  persistThreads();
}

function hydrateThreads() {
  try {
    const raw = getStorage()?.getItem(STORAGE_KEY);
    if (!raw) {
      return;
    }
    const parsed = JSON.parse(raw) as Record<string, CopilotMessage[]>;
    Object.entries(parsed).forEach(([threadId, messages]) => {
      if (Array.isArray(messages)) {
        messagesByThread.set(threadId, messages.slice(-16));
      }
    });
  } catch {
    // Conversation persistence is best-effort.
  }
}

function persistThreads() {
  try {
    const payload = Object.fromEntries(messagesByThread.entries());
    getStorage()?.setItem(STORAGE_KEY, JSON.stringify(payload));
  } catch {
    // Conversation persistence is best-effort.
  }
}

function getStorage(): Storage | null {
  if (typeof globalThis === 'undefined' || !('localStorage' in globalThis)) {
    return null;
  }
  return globalThis.localStorage;
}
