import * as FileSystem from 'expo-file-system/legacy';

import type {
  CopilotChatResponse,
  CopilotContext,
  CopilotEntityV1,
  CopilotMessage,
  CopilotSessionContextV1,
} from '@/features/copilot/types';
import { resolveSessionActiveIntent } from '@/features/copilot/state/sessionContext';

type CopilotLaunchState = {
  context: CopilotContext | null;
  initialPrompt?: string;
};

type PersistedThread = {
  messages: CopilotMessage[];
  sessionContext: CopilotSessionContextV1 | null;
  updatedAt: string;
};

type PersistedCopilotStoreV2 = {
  version: 2;
  activeThreadId: string | null;
  threads: Record<string, PersistedThread>;
};

export type HydratedCopilotSession = {
  messages: CopilotMessage[];
  sessionContext: CopilotSessionContextV1 | null;
  threadId: string | null;
};

let launchState: CopilotLaunchState = { context: null };
const STORAGE_KEY = 'market-intelligence-copilot-threads-v2';
const LEGACY_STORAGE_KEY = 'market-intelligence-copilot-threads-v1';
const MAX_THREADS = 6;
const MAX_MESSAGES = 12;
const MAX_MESSAGE_LENGTH = 2_000;
const threads = new Map<string, PersistedThread>();
let activeThreadId: string | null = null;
let hydrated = false;
let hydrationPromise: Promise<void> | null = null;

export function setCopilotLaunchContext(context: CopilotContext, initialPrompt?: string) {
  launchState = { context, initialPrompt };
}

export function consumeCopilotLaunchContext(): CopilotLaunchState {
  const current = launchState;
  launchState = { context: null };
  return current;
}

export function getDefaultCopilotContext(): CopilotContext {
  return {
    generatedAt: new Date().toISOString(),
    routeName: '/ai',
    screenTitle: 'Institutional Copilot',
    screenType: 'general',
    sourceState: 'unavailable',
  };
}

export async function hydrateCopilotStore(): Promise<HydratedCopilotSession> {
  if (!hydrated) {
    hydrationPromise ??= hydrate().finally(() => {
      hydrated = true;
      hydrationPromise = null;
    });
    await hydrationPromise;
  }
  return currentSession();
}

export function getThreadMessages(threadId: string) {
  return threads.get(threadId)?.messages ?? [];
}

export function getThreadSessionContext(threadId: string) {
  return threads.get(threadId)?.sessionContext ?? null;
}

export function getActiveCopilotThreadId() {
  return activeThreadId;
}

export function saveThreadMessages(
  threadId: string,
  messages: CopilotMessage[],
  sessionContext: CopilotSessionContextV1 | null = threads.get(threadId)?.sessionContext ?? null,
) {
  activeThreadId = threadId;
  threads.set(threadId, {
    messages: compactMessages(messages),
    sessionContext: sessionContext ? compactSessionContext(sessionContext) : null,
    updatedAt: new Date().toISOString(),
  });
  pruneThreads();
  void persist();
}

export function saveThreadSessionContext(threadId: string, sessionContext: CopilotSessionContextV1) {
  const existing = threads.get(threadId);
  threads.set(threadId, {
    messages: existing?.messages ?? [],
    sessionContext: compactSessionContext(sessionContext),
    updatedAt: new Date().toISOString(),
  });
  activeThreadId = threadId;
  pruneThreads();
  void persist();
}

export function clearThreadMessages(threadId: string) {
  threads.delete(threadId);
  if (activeThreadId === threadId) activeThreadId = null;
  void persist();
}

export function clearAllCopilotThreads() {
  threads.clear();
  activeThreadId = null;
  void persist();
}

export function buildNextSessionContext({
  context,
  previous,
  question,
  response,
}: {
  context: CopilotContext;
  previous?: CopilotSessionContextV1 | null;
  question: string;
  response: CopilotChatResponse;
}): CopilotSessionContextV1 {
  const evidenceIds = response.evidence?.map((item) => item.evidenceId) ?? response.grounding.evidenceIds ?? [];
  const symbols = response.intent?.tickerSymbols ?? findSymbols(question);
  const groups = [...(response.intent?.sectors ?? []), ...(response.intent?.themes ?? [])];
  const reportId = stringAt(context.report, 'reportId', 'report_id');
  const inferredEntities: CopilotEntityV1[] = [
    ...symbols.map((symbol) => ({
      confidence: 1,
      displayName: symbol,
      entityId: symbol,
      entityType: 'stock',
      resolutionSource: 'session',
      symbol,
    })),
    ...groups.map((group) => ({
      confidence: 1,
      displayName: group,
      entityId: group,
      entityType: response.intent?.sectors.includes(group) ? 'sector' : 'theme',
      resolutionSource: 'session',
      symbol: null,
    })),
  ];
  return {
    schemaVersion: 'copilot-session-context-v1',
    threadId: response.threadId,
    activeEntities: uniqueEntities([
      ...(response.intent?.entities ?? []),
      ...inferredEntities,
      ...(previous?.activeEntities ?? []),
    ]).slice(0, 10),
    activeIntent: resolveSessionActiveIntent(response.intent?.intent, previous?.activeIntent),
    latestReferencedStock: symbols.at(-1) ?? previous?.latestReferencedStock ?? null,
    latestReferencedSectorOrTheme: groups.at(-1) ?? previous?.latestReferencedSectorOrTheme ?? null,
    latestReportId: reportId ?? previous?.latestReportId ?? null,
    latestThesis: response.reasoning?.thesis ?? previous?.latestThesis ?? null,
    unresolvedQuestion: response.missingEvidence?.length ? question : null,
    previousAnswerStance: response.reasoning?.stance ?? previous?.previousAnswerStance ?? null,
    relevantEvidenceIds: unique([...evidenceIds, ...(previous?.relevantEvidenceIds ?? [])]).slice(0, 20),
    currentScreen: context.screenType,
    currentRoute: context.routeName,
    updatedAt: new Date().toISOString(),
  };
}

async function hydrate() {
  try {
    const raw = getWebStorage()?.getItem(STORAGE_KEY)
      ?? await readFileStorage()
      ?? getWebStorage()?.getItem(LEGACY_STORAGE_KEY);
    if (!raw) return;
    const parsed = JSON.parse(raw) as unknown;
    const normalized = normalizePersistedStore(parsed);
    activeThreadId = normalized.activeThreadId;
    Object.entries(normalized.threads).forEach(([threadId, thread]) => {
      threads.set(threadId, {
        messages: compactMessages(thread.messages),
        sessionContext: thread.sessionContext ? compactSessionContext(thread.sessionContext) : null,
        updatedAt: thread.updatedAt,
      });
    });
    pruneThreads();
  } catch {
    // Conversation persistence is best-effort and must never block Copilot.
  }
}

function currentSession(): HydratedCopilotSession {
  const active = activeThreadId ? threads.get(activeThreadId) : null;
  return {
    messages: active?.messages ?? [],
    sessionContext: active?.sessionContext ?? null,
    threadId: active ? activeThreadId : null,
  };
}

function normalizePersistedStore(input: unknown): PersistedCopilotStoreV2 {
  if (input && typeof input === 'object' && !Array.isArray(input)) {
    const record = input as Record<string, unknown>;
    if (record.version === 2 && record.threads && typeof record.threads === 'object') {
      return input as PersistedCopilotStoreV2;
    }
    const legacyThreads = Object.fromEntries(Object.entries(record).flatMap(([threadId, messages]) => (
      Array.isArray(messages)
        ? [[threadId, { messages, sessionContext: null, updatedAt: new Date(0).toISOString() }]]
        : []
    )));
    const latestLegacyId = Object.keys(legacyThreads).at(-1) ?? null;
    return { version: 2, activeThreadId: latestLegacyId, threads: legacyThreads as Record<string, PersistedThread> };
  }
  return { version: 2, activeThreadId: null, threads: {} };
}

function compactMessages(messages: CopilotMessage[]) {
  return messages.slice(-MAX_MESSAGES).map((message) => ({
    ...message,
    content: message.content.slice(0, MAX_MESSAGE_LENGTH),
    response: message.response ? compactResponse(message.response) : undefined,
  }));
}

function compactResponse(response: CopilotChatResponse): CopilotChatResponse {
  return {
    ...response,
    answer: response.answer.slice(0, MAX_MESSAGE_LENGTH),
    evidence: response.evidence?.slice(0, 20),
    contradictoryEvidence: response.contradictoryEvidence?.slice(0, 12),
    actions: response.actions?.slice(0, 8),
    warnings: response.warnings?.slice(0, 8),
    missingEvidence: response.missingEvidence?.slice(0, 8),
    suggestedFollowUps: response.suggestedFollowUps.slice(0, 4),
  };
}

function compactSessionContext(context: CopilotSessionContextV1): CopilotSessionContextV1 {
  return {
    ...context,
    schemaVersion: 'copilot-session-context-v1',
    threadId: context.threadId || activeThreadId || 'copilot-local',
    activeEntities: uniqueEntities((context.activeEntities as unknown[])
      .map(normalizeStoredEntity)
      .filter((item): item is CopilotEntityV1 => item !== null)).slice(0, 10),
    relevantEvidenceIds: unique(context.relevantEvidenceIds).slice(0, 20),
    latestThesis: context.latestThesis?.slice(0, 500) ?? null,
    unresolvedQuestion: context.unresolvedQuestion?.slice(0, 500) ?? null,
  };
}

function pruneThreads() {
  const retained = [...threads.entries()]
    .sort((left, right) => right[1].updatedAt.localeCompare(left[1].updatedAt))
    .slice(0, MAX_THREADS);
  threads.clear();
  retained.forEach(([threadId, thread]) => threads.set(threadId, thread));
  if (activeThreadId && !threads.has(activeThreadId)) activeThreadId = retained[0]?.[0] ?? null;
}

async function persist() {
  const payload: PersistedCopilotStoreV2 = {
    version: 2,
    activeThreadId,
    threads: Object.fromEntries(threads.entries()),
  };
  const raw = JSON.stringify(payload);
  try {
    getWebStorage()?.setItem(STORAGE_KEY, raw);
  } catch {
    // Native file persistence remains available when web storage is unavailable.
  }
  try {
    const path = getFilePath();
    if (!path || !FileSystem.documentDirectory) return;
    await FileSystem.makeDirectoryAsync(FileSystem.documentDirectory, { intermediates: true });
    await FileSystem.writeAsStringAsync(path, raw);
  } catch {
    // Local transcript persistence is deliberately best-effort.
  }
}

async function readFileStorage() {
  const path = getFilePath();
  if (!path) return null;
  const info = await FileSystem.getInfoAsync(path);
  return info.exists ? FileSystem.readAsStringAsync(path) : null;
}

function getFilePath() {
  return FileSystem.documentDirectory ? `${FileSystem.documentDirectory}${STORAGE_KEY}.json` : null;
}

function getWebStorage(): Storage | null {
  if (typeof globalThis === 'undefined' || !('localStorage' in globalThis)) return null;
  return globalThis.localStorage;
}

function stringAt(record: Record<string, unknown> | undefined, ...keys: string[]) {
  for (const key of keys) {
    const value = record?.[key];
    if (typeof value === 'string' && value.trim()) return value.trim();
  }
  return null;
}

function findSymbols(input: string) {
  return unique(input.match(/\b[A-Z][A-Z0-9.-]{0,9}\b/g) ?? []).filter((item) => !['I', 'A', 'THE', 'WHAT', 'WHY', 'SHOW'].includes(item));
}

function unique(items: string[]) {
  return [...new Set(items.map((item) => item.trim()).filter(Boolean))];
}

function uniqueEntities(items: CopilotEntityV1[]) {
  return [...new Map(items.map((item) => [item.entityId.trim().toLowerCase(), item])).values()]
    .filter((item) => item.entityId.trim() && item.displayName.trim());
}

function normalizeStoredEntity(input: unknown): CopilotEntityV1 | null {
  if (typeof input === 'string') {
    const name = input.trim();
    if (!name) return null;
    const isSymbol = /^[A-Z][A-Z0-9.-]{0,9}$/.test(name);
    return {
      confidence: 1,
      displayName: name,
      entityId: name,
      entityType: isSymbol ? 'stock' : 'app_feature',
      resolutionSource: 'legacy-session',
      symbol: isSymbol ? name : null,
    };
  }
  if (!input || typeof input !== 'object' || Array.isArray(input)) return null;
  const record = input as Partial<CopilotEntityV1>;
  const entityId = typeof record.entityId === 'string' ? record.entityId.trim() : '';
  const displayName = typeof record.displayName === 'string' ? record.displayName.trim() : entityId;
  if (!entityId || !displayName) return null;
  return {
    confidence: typeof record.confidence === 'number' ? record.confidence : 1,
    displayName,
    entityId,
    entityType: typeof record.entityType === 'string' ? record.entityType : 'app_feature',
    resolutionSource: typeof record.resolutionSource === 'string' ? record.resolutionSource : 'session',
    symbol: typeof record.symbol === 'string' ? record.symbol : null,
  };
}
