import type { CopilotContext } from '@/features/copilot/types';

const SENSITIVE_KEY_PARTS = ['api', 'token', 'secret', 'password', 'authorization', 'cookie'];
const MAX_LIST_ITEMS = 12;
const MAX_STRING_LENGTH = 900;
const MAX_DEPTH = 5;

export function sanitizeCopilotContext(context: CopilotContext): CopilotContext {
  return compactValue(context, 0) as CopilotContext;
}

function compactValue(value: unknown, depth: number): unknown {
  if (depth > MAX_DEPTH) {
    return null;
  }
  if (typeof value === 'string') {
    return value.slice(0, MAX_STRING_LENGTH);
  }
  if (typeof value === 'number' || typeof value === 'boolean' || value == null) {
    return value;
  }
  if (Array.isArray(value)) {
    return value.slice(0, MAX_LIST_ITEMS).map((item) => compactValue(item, depth + 1));
  }
  if (typeof value === 'object') {
    const output: Record<string, unknown> = {};
    Object.entries(value as Record<string, unknown>).slice(0, 80).forEach(([key, item]) => {
      const normalizedKey = key.toLowerCase();
      if (SENSITIVE_KEY_PARTS.some((part) => normalizedKey.includes(part))) {
        return;
      }
      const compacted = compactValue(item, depth + 1);
      if (compacted !== null) {
        output[key] = compacted;
      }
    });
    return output;
  }
  return String(value).slice(0, MAX_STRING_LENGTH);
}
