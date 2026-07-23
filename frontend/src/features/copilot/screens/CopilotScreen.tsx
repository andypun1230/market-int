import { useEffect, useMemo, useReducer, useRef, useState } from 'react';
import { useRouter } from 'expo-router';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import { AppScreen } from '@/components/ui/AppScreen';
import { QuickActionChip } from '@/components/ui/QuickActionChip';
import { Spacing, Theme } from '@/constants/theme';
import { CopilotSourceBadge } from '@/features/copilot/components/CopilotSourceBadge';
import { CopilotStructuredResponse } from '@/features/copilot/components/CopilotStructuredResponse';
import { buildStarterPrompts } from '@/features/copilot/context/contextRegistry';
import { CopilotTransportError, streamCopilotChat } from '@/features/copilot/api/copilotApi';
import { resolveNavigationAction } from '@/architecture/navigationRegistry';
import {
  copilotConversationReducer,
  createInitialCopilotState,
  draftToCopilotResponse,
} from '@/features/copilot/state/copilotReducer';
import {
  buildNextSessionContext,
  clearThreadMessages,
  consumeCopilotLaunchContext,
  getDefaultCopilotContext,
  hydrateCopilotStore,
  saveThreadMessages,
} from '@/features/copilot/state/copilotStore';
import { sanitizeCopilotContext } from '@/features/copilot/utils/sanitizeCopilotContext';
import { mergeHydratedWatchlistMembership } from '@/features/copilot/utils/watchlistMembershipContext';
import { useWatchlist } from '@/features/watchlist/store';
import type {
  CopilotActionV1,
  CopilotChatRequest,
  CopilotContext,
  CopilotMessage,
} from '@/features/copilot/types';

export function CopilotScreen() {
  const router = useRouter();
  const { hydrated: watchlistHydrated, stockItems: savedStockItems } = useWatchlist();
  const launch = useMemo(() => consumeCopilotLaunchContext(), []);
  const [context, setContext] = useState<CopilotContext>(launch.context ?? getDefaultCopilotContext());
  const [input, setInput] = useState(launch.initialPrompt ?? '');
  const [state, dispatch] = useReducer(copilotConversationReducer, undefined, createInitialCopilotState);
  const stateRef = useRef(state);
  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<ScrollView | null>(null);
  useEffect(() => {
    stateRef.current = state;
  }, [state]);
  const busy = state.status === 'requesting' || state.status === 'streaming';
  const starterPrompts = buildStarterPrompts(context).slice(0, 6);
  const requestContext = useMemo(() => sanitizeCopilotContext(
    mergeHydratedWatchlistMembership(context, watchlistHydrated, savedStockItems),
  ), [context, savedStockItems, watchlistHydrated]);

  useEffect(() => {
    let active = true;
    void hydrateCopilotStore().then((session) => {
      if (!active) return;
      dispatch({
        type: 'hydrate',
        messages: session.messages,
        sessionContext: session.sessionContext,
        threadId: session.threadId,
      });
    });
    return () => {
      active = false;
      abortRef.current?.abort();
    };
  }, []);

  async function send(promptOverride?: string) {
    const prompt = (promptOverride ?? input).trim();
    const current = stateRef.current;
    if (!prompt || current.status === 'requesting' || current.status === 'streaming') return;
    const requestId = createRequestId();
    const now = new Date().toISOString();
    const userMessage: CopilotMessage = { content: prompt, createdAt: now, id: `user-${requestId}`, role: 'user' };
    const request: CopilotChatRequest = {
      requestId,
      context: requestContext,
      history: current.messages.slice(-8).map((item) => ({ content: item.content, role: item.role })),
      message: prompt,
      responseDepth: 'compact',
      sessionContext: current.sessionContext,
      threadId: current.threadId,
    };
    const messagesBeforeAssistant = [...current.messages, userMessage];
    dispatch({ type: 'submit', request, userMessage });
    setInput('');
    await runRequest(request, messagesBeforeAssistant);
  }

  async function runRequest(request: CopilotChatRequest, messagesBeforeAssistant: CopilotMessage[]) {
    const controller = new AbortController();
    abortRef.current?.abort();
    abortRef.current = controller;
    try {
      const result = await streamCopilotChat(request, {
        signal: controller.signal,
        onEvent: (event) => dispatch({ type: 'stream_event', event }),
      });
      const response = result.response;
      const assistantMessage: CopilotMessage = {
        content: response.answer,
        createdAt: response.grounding.generatedAt,
        id: `assistant-${response.requestId ?? createRequestId()}`,
        response,
        role: 'assistant',
      };
      const nextSessionContext = buildNextSessionContext({
        context: request.context,
        previous: stateRef.current.sessionContext,
        question: request.message,
        response,
      });
      const finalMessages = [...messagesBeforeAssistant, assistantMessage];
      dispatch({ type: 'complete', response, assistantMessage });
      dispatch({ type: 'set_session_context', sessionContext: nextSessionContext });
      saveThreadMessages(response.threadId, finalMessages, nextSessionContext);
    } catch (error) {
      const transportError = error instanceof CopilotTransportError ? error : null;
      if (transportError?.category === 'cancelled' || controller.signal.aborted) {
        dispatch({ type: 'cancel' });
      } else {
        dispatch({
          type: 'fail',
          message: transportError?.message ?? 'Institutional Copilot is temporarily unavailable.',
          partial: transportError?.partial,
          retryable: transportError?.retryable ?? true,
        });
      }
    } finally {
      if (abortRef.current === controller) abortRef.current = null;
    }
  }

  async function retry() {
    const current = stateRef.current;
    if (!current.lastRequest || busy) return;
    const request = {
      ...current.lastRequest,
      requestId: createRequestId(),
      context: requestContext,
      sessionContext: current.sessionContext,
      threadId: current.threadId,
    };
    dispatch({ type: 'retry', request });
    await runRequest(request, current.messages);
  }

  function cancel() {
    abortRef.current?.abort();
  }

  function clearConversation() {
    abortRef.current?.abort();
    if (stateRef.current.threadId) clearThreadMessages(stateRef.current.threadId);
    dispatch({ type: 'clear' });
    setInput('');
  }

  function removeContext() {
    setContext(getDefaultCopilotContext());
  }

  function openAction(action: CopilotActionV1) {
    const destination = resolveNavigationAction(action);
    if (!destination) return;
    router.push({
      pathname: destination.pathname,
      params: { ...(destination.params ?? {}), actionNonce: `${Date.now()}` },
    } as never);
  }

  const partialResponse = state.draft ? draftToCopilotResponse(state.draft, state.threadId) : null;

  return (
    <AppScreen
      contentStyle={styles.appContent}
      scroll={false}
      showBackButton
      title="Institutional Copilot"
      subtitle="Grounded market reasoning, evidence, and app-native actions.">
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 8 : 0}
        style={styles.keyboardView}>
        <ScrollView
          contentContainerStyle={styles.conversationContent}
          keyboardDismissMode="interactive"
          keyboardShouldPersistTaps="handled"
          onContentSizeChange={() => scrollRef.current?.scrollToEnd({ animated: true })}
          ref={scrollRef}
          showsVerticalScrollIndicator={false}>
          <CopilotContextBar context={context} onClearChat={clearConversation} onClearContext={removeContext} />

          {!state.messages.length && !partialResponse ? (
            <View style={styles.starterBlock}>
              <Text style={styles.starterLabel}>START WITH A RESEARCH QUESTION</Text>
              <View style={styles.promptRow}>
                {starterPrompts.map((prompt) => (
                  <QuickActionChip key={prompt} label={prompt} onPress={() => void send(prompt)} tone="purple" />
                ))}
              </View>
            </View>
          ) : null}

          <View style={styles.messageStack}>
            {state.messages.map((message) => (
              <CopilotTurn
                disabled={busy}
                key={message.id}
                message={message}
                onAction={openAction}
                onFollowUp={(prompt) => void send(prompt)}
              />
            ))}

            {partialResponse ? (
              <View style={styles.assistantTurn}>
                <View accessibilityLiveRegion="polite" style={styles.streamStatus}>
                  {busy ? <ActivityIndicator color={Theme.colors.purple} size="small" /> : null}
                  <Text style={styles.streamStatusText}>{state.draft?.stageLabel ?? 'Partial answer'}</Text>
                </View>
                <CopilotStructuredResponse onAction={openAction} partial response={partialResponse} />
              </View>
            ) : busy ? (
              <View accessibilityLiveRegion="polite" style={styles.streamStatus}>
                <ActivityIndicator color={Theme.colors.purple} size="small" />
                <Text style={styles.streamStatusText}>Classifying intent and routing validated engines…</Text>
              </View>
            ) : null}

            {state.error ? (
              <View accessibilityRole="alert" style={styles.errorPanel}>
                <Text style={styles.errorTitle}>{state.status === 'cancelled' ? 'Request cancelled' : state.status === 'partial' ? 'Partial response preserved' : 'Copilot request incomplete'}</Text>
                <Text style={styles.errorText}>{state.error}</Text>
                {state.retryable ? <SmallAction label="Retry request" onPress={() => void retry()} /> : null}
              </View>
            ) : null}
          </View>
        </ScrollView>

        <View style={styles.composerShell}>
          <TextInput
            accessibilityLabel="Ask Institutional Copilot"
            editable={!busy}
            multiline
            onChangeText={setInput}
            placeholder="Ask about a market condition, report thesis, stock setup, risk, or app destination…"
            placeholderTextColor={Theme.colors.textMuted}
            style={styles.input}
            value={input}
          />
          <View style={styles.composerActions}>
            <Text style={styles.composerHint}>Evidence first · no portfolio assumptions</Text>
            {busy ? (
              <Pressable accessibilityLabel="Cancel Copilot request" accessibilityRole="button" onPress={cancel} style={({ pressed }) => [styles.cancelButton, pressed && styles.pressed]}>
                <Text style={styles.cancelText}>Cancel</Text>
              </Pressable>
            ) : (
              <Pressable
                accessibilityLabel="Send question to Institutional Copilot"
                accessibilityRole="button"
                disabled={!input.trim()}
                onPress={() => void send()}
                style={({ pressed }) => [styles.sendButton, !input.trim() && styles.disabled, pressed && styles.pressed]}>
                <Text style={styles.sendText}>Send</Text>
              </Pressable>
            )}
          </View>
        </View>
      </KeyboardAvoidingView>
    </AppScreen>
  );
}

function CopilotContextBar({
  context,
  onClearChat,
  onClearContext,
}: {
  context: CopilotContext;
  onClearChat: () => void;
  onClearContext: () => void;
}) {
  return (
    <View style={styles.contextBar}>
      <View style={styles.contextCopy}>
        <Text style={styles.contextEyebrow}>ACTIVE CONTEXT</Text>
        <Text style={styles.contextTitle}>{context.screenTitle}</Text>
        <Text style={styles.contextMeta}>{context.screenType} · {context.routeName}</Text>
      </View>
      <View style={styles.contextActions}>
        <CopilotSourceBadge sourceState={context.sourceState} />
        <SmallAction label="Clear context" onPress={onClearContext} />
        <SmallAction label="Clear chat" onPress={onClearChat} />
      </View>
    </View>
  );
}

function CopilotTurn({
  disabled,
  message,
  onAction,
  onFollowUp,
}: {
  disabled: boolean;
  message: CopilotMessage;
  onAction: (action: CopilotActionV1) => void;
  onFollowUp: (prompt: string) => void;
}) {
  if (message.role === 'user') {
    return (
      <View style={styles.userTurn}>
        <Text style={styles.turnLabel}>YOU</Text>
        <Text style={styles.userText}>{message.content}</Text>
      </View>
    );
  }
  if (!message.response) return <Text style={styles.userText}>{message.content}</Text>;
  return (
    <View style={styles.assistantTurn}>
      <Text style={styles.turnLabel}>INSTITUTIONAL COPILOT</Text>
      <CopilotStructuredResponse onAction={onAction} response={message.response} />
      {message.response.suggestedFollowUps.length ? (
        <View style={styles.followUpBlock}>
          <Text style={styles.starterLabel}>FOLLOW-UP</Text>
          <View style={styles.promptRow}>
            {message.response.suggestedFollowUps.slice(0, 4).map((item) => (
              <QuickActionChip key={item} label={item} onPress={disabled ? undefined : () => onFollowUp(item)} tone="purple" />
            ))}
          </View>
        </View>
      ) : null}
    </View>
  );
}

function SmallAction({ label, onPress }: { label: string; onPress: () => void }) {
  return (
    <Pressable accessibilityLabel={label} accessibilityRole="button" onPress={onPress} style={({ pressed }) => [styles.smallAction, pressed && styles.pressed]}>
      <Text style={styles.smallActionText}>{label}</Text>
    </Pressable>
  );
}

function createRequestId() {
  return `copilot-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

const styles = StyleSheet.create({
  appContent: { padding: 0 },
  assistantTurn: { gap: Spacing.two },
  cancelButton: { alignItems: 'center', borderColor: Theme.colors.warning, borderRadius: Theme.radii.pill, borderWidth: 1, minHeight: 40, justifyContent: 'center', paddingHorizontal: Spacing.three },
  cancelText: { color: Theme.colors.warning, fontSize: 13, fontWeight: '900' },
  composerActions: { alignItems: 'center', flexDirection: 'row', gap: Spacing.two, justifyContent: 'space-between' },
  composerHint: { color: Theme.colors.textMuted, flex: 1, fontSize: 10, fontWeight: '700' },
  composerShell: { backgroundColor: Theme.colors.background, borderTopColor: Theme.colors.border, borderTopWidth: 1, gap: Spacing.two, padding: Spacing.three },
  contextActions: { alignItems: 'center', flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.one, justifyContent: 'flex-end' },
  contextBar: { alignItems: 'flex-start', backgroundColor: Theme.colors.card, borderColor: Theme.colors.border, borderRadius: Theme.radii.small, borderWidth: 1, flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.two, justifyContent: 'space-between', padding: Spacing.twoAndHalf },
  contextCopy: { flex: 1, gap: 2, minWidth: 190 },
  contextEyebrow: { color: Theme.colors.purple, fontSize: 10, fontWeight: '900', letterSpacing: 0.6 },
  contextMeta: { color: Theme.colors.textMuted, fontSize: 11, fontWeight: '700', textTransform: 'capitalize' },
  contextTitle: { color: Theme.colors.text, fontSize: 14, fontWeight: '900' },
  conversationContent: { gap: Spacing.three, padding: Spacing.three, paddingBottom: Spacing.four },
  disabled: { opacity: 0.45 },
  errorPanel: { alignItems: 'flex-start', backgroundColor: Theme.colors.dangerSoft, borderColor: Theme.colors.danger, borderRadius: Theme.radii.small, borderWidth: 1, gap: Spacing.one, padding: Spacing.twoAndHalf },
  errorText: { color: Theme.colors.text, fontSize: 12, fontWeight: '700', lineHeight: 18 },
  errorTitle: { color: Theme.colors.danger, fontSize: 12, fontWeight: '900' },
  followUpBlock: { gap: Spacing.one },
  input: { backgroundColor: Theme.colors.backgroundMuted, borderColor: Theme.colors.border, borderRadius: Theme.radii.small, borderWidth: 1, color: Theme.colors.text, fontSize: 14, fontWeight: '700', lineHeight: 20, maxHeight: 130, minHeight: 56, padding: Spacing.twoAndHalf, textAlignVertical: 'top' },
  keyboardView: { flex: 1 },
  messageStack: { gap: Spacing.four },
  pressed: { opacity: 0.74 },
  promptRow: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.two },
  sendButton: { alignItems: 'center', backgroundColor: Theme.colors.purple, borderRadius: Theme.radii.pill, justifyContent: 'center', minHeight: 40, paddingHorizontal: Spacing.four },
  sendText: { color: Theme.colors.background, fontSize: 13, fontWeight: '900' },
  smallAction: { backgroundColor: Theme.colors.cardMuted, borderColor: Theme.colors.border, borderRadius: Theme.radii.pill, borderWidth: 1, paddingHorizontal: Spacing.two, paddingVertical: Spacing.one },
  smallActionText: { color: Theme.colors.text, fontSize: 10, fontWeight: '900' },
  starterBlock: { gap: Spacing.two },
  starterLabel: { color: Theme.colors.textMuted, fontSize: 10, fontWeight: '900', letterSpacing: 0.6 },
  streamStatus: { alignItems: 'center', flexDirection: 'row', gap: Spacing.two, paddingHorizontal: Spacing.one },
  streamStatusText: { color: Theme.colors.textMuted, fontSize: 12, fontWeight: '800' },
  turnLabel: { color: Theme.colors.textMuted, fontSize: 10, fontWeight: '900', letterSpacing: 0.6 },
  userText: { color: Theme.colors.text, fontSize: 14, fontWeight: '700', lineHeight: 21 },
  userTurn: { alignSelf: 'flex-end', backgroundColor: Theme.colors.purpleSoft, borderColor: Theme.colors.purple, borderRadius: Theme.radii.small, borderWidth: 1, gap: Spacing.one, maxWidth: '88%', padding: Spacing.twoAndHalf },
});
