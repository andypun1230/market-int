import { useMemo, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { AppScreen } from '@/components/ui/AppScreen';
import { QuickActionChip } from '@/components/ui/QuickActionChip';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Spacing, Theme } from '@/constants/theme';
import { askMarketCopilot } from '@/features/copilot/api/copilotApi';
import { buildStarterPrompts } from '@/features/copilot/context/contextRegistry';
import { CopilotSourceBadge } from '@/features/copilot/components/CopilotSourceBadge';
import type { CopilotContext, CopilotMessage } from '@/features/copilot/types';
import {
  clearThreadMessages,
  consumeCopilotLaunchContext,
  getDefaultCopilotContext,
  getThreadMessages,
  saveThreadMessages,
} from '@/features/copilot/state/copilotStore';

export function CopilotScreen() {
  const launch = useMemo(() => consumeCopilotLaunchContext(), []);
  const [context, setContext] = useState<CopilotContext>(launch.context ?? getDefaultCopilotContext());
  const [threadId, setThreadId] = useState<string | null>(null);
  const [messages, setMessages] = useState<CopilotMessage[]>(threadId ? getThreadMessages(threadId) : []);
  const [input, setInput] = useState(launch.initialPrompt ?? '');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const starterPrompts = buildStarterPrompts(context).slice(0, 6);

  async function send(promptOverride?: string) {
    const prompt = (promptOverride ?? input).trim();
    if (!prompt || loading) {
      return;
    }
    const now = new Date().toISOString();
    const userMessage: CopilotMessage = {
      content: prompt,
      createdAt: now,
      id: `user-${now}`,
      role: 'user',
    };
    const nextMessages = [...messages, userMessage];
    setMessages(nextMessages);
    setInput('');
    setLoading(true);
    setError(null);

    try {
      const response = await askMarketCopilot({
        context,
        history: nextMessages.slice(-8).map((item) => ({ content: item.content, role: item.role })),
        message: prompt,
        responseDepth: 'compact',
        threadId,
      });
      const assistantMessage: CopilotMessage = {
        content: response.answer,
        createdAt: response.grounding.generatedAt,
        id: `assistant-${response.grounding.generatedAt}`,
        response,
        role: 'assistant',
      };
      const finalMessages = [...nextMessages, assistantMessage];
      setThreadId(response.threadId);
      setMessages(finalMessages);
      saveThreadMessages(response.threadId, finalMessages);
    } catch {
      setError('Market Copilot is temporarily unavailable.');
      setMessages(messages);
    } finally {
      setLoading(false);
    }
  }

  function clearConversation() {
    if (threadId) {
      clearThreadMessages(threadId);
    }
    setThreadId(null);
    setMessages([]);
    setError(null);
  }

  function removeContext() {
    setContext(getDefaultCopilotContext());
  }

  return (
    <AppScreen
      showBackButton
      title="Market Copilot"
      subtitle="Ask questions about today’s market, reports, sectors, risks, watchlist, and stocks.">
      <DashboardCard title="Context" accentColor={Theme.colors.purple}>
        <View style={styles.contextStack}>
          <View style={styles.contextHeader}>
            <View style={styles.contextTitleBlock}>
              <Text style={styles.contextTitle}>{context.screenTitle}</Text>
              <Text style={styles.contextMeta}>{context.screenType} · {context.routeName}</Text>
            </View>
            <CopilotSourceBadge sourceState={context.sourceState} />
          </View>
          {context.focusedMetric ? (
            <Text style={styles.contextText}>Focused on {context.focusedMetric.title}: {context.focusedMetric.value ?? 'N/A'}</Text>
          ) : (
            <Text style={styles.contextText}>Copilot will use the current screen context first, then app engines and report data where available.</Text>
          )}
          <View style={styles.inlineActions}>
            <SmallAction label="Clear Context" onPress={removeContext} />
            <SmallAction label="Clear Chat" onPress={clearConversation} />
          </View>
        </View>
      </DashboardCard>

      {!messages.length ? (
        <View style={styles.promptStack}>
          {starterPrompts.map((prompt) => (
            <QuickActionChip key={prompt} label={prompt} onPress={() => send(prompt)} tone="purple" />
          ))}
        </View>
      ) : null}

      <View style={styles.messageStack}>
        {messages.map((message) => (
          <CopilotMessageBubble key={message.id} disabled={loading} message={message} onFollowUpPress={send} />
        ))}
        {loading ? (
          <View style={styles.loadingRow}>
            <ActivityIndicator color={Theme.colors.purple} />
            <Text style={styles.loadingText}>{loadingTextForContext(context)}</Text>
          </View>
        ) : null}
        {error ? <Text style={styles.errorText}>{error}</Text> : null}
      </View>

      <DashboardCard title="Ask Market Copilot" accentColor={Theme.colors.purple}>
        <TextInput
          multiline
          onChangeText={setInput}
          placeholder="Ask about this screen, a score, report, stock, sector, or watchlist..."
          placeholderTextColor={Theme.colors.textMuted}
          style={styles.input}
          value={input}
        />
        <Pressable
          accessibilityLabel="Send question to Market Copilot"
          accessibilityRole="button"
          disabled={!input.trim() || loading}
          onPress={() => send()}
          style={({ pressed }) => [
            styles.sendButton,
            (!input.trim() || loading) && styles.disabled,
            pressed && styles.pressed,
          ]}>
          <Text style={styles.sendText}>{loading ? 'Reviewing…' : 'Send'}</Text>
        </Pressable>
      </DashboardCard>
      <Text style={styles.footerDisclaimer}>Educational market decision support only, not financial advice.</Text>
    </AppScreen>
  );
}

function CopilotMessageBubble({
  disabled,
  message,
  onFollowUpPress,
}: {
  disabled: boolean;
  message: CopilotMessage;
  onFollowUpPress: (prompt: string) => void;
}) {
  const isUser = message.role === 'user';
  const sections = message.response?.answerSections;
  const confidence = message.response?.answerConfidence;
  return (
    <View style={[styles.messageBubble, isUser ? styles.userBubble : styles.assistantBubble]}>
      <Text style={styles.messageRole}>{isUser ? 'You' : 'Market Copilot'}</Text>
      {sections && !isUser ? (
        <View style={styles.answerStack}>
          <Text style={styles.messageText}>{sections.directAnswer}</Text>
          {sections.why.length ? <CompactList title="Why" items={sections.why.slice(0, 3)} /> : null}
          {sections.mainCaution ? (
            <View style={styles.cautionBox}>
              <Text style={styles.sectionLabel}>Main caution</Text>
              <Text style={styles.cautionText}>{sections.mainCaution}</Text>
            </View>
          ) : null}
          {sections.whatWouldChange.length ? <CompactList title="What would change this" items={sections.whatWouldChange.slice(0, 2)} /> : null}
        </View>
      ) : (
        <Text style={styles.messageText}>{message.content}</Text>
      )}
      {message.response ? (
        <View style={styles.responseMeta}>
          <View style={styles.badgeRow}>
            <StatusBadge label={`${confidenceLabel(confidence?.level)} confidence`} showDot={false} tone={confidenceTone(confidence?.level)} />
            <CopilotSourceBadge sourceState={message.response.grounding.sourceState} />
          </View>
          {confidence?.reasons.length ? (
            <Text style={styles.confidenceText}>{confidence.reasons.slice(0, 2).join(' · ')}</Text>
          ) : null}
          {message.response.grounding.contextUsed.length ? (
            <Text style={styles.groundingText}>Based on: {message.response.grounding.contextUsed.join(', ')}</Text>
          ) : null}
          {message.response.suggestedFollowUps.length ? (
            <View style={styles.followUpRow}>
              {message.response.suggestedFollowUps.slice(0, 3).map((item) => (
                <QuickActionChip
                  key={item}
                  label={item}
                  onPress={disabled ? undefined : () => onFollowUpPress(item)}
                  tone="purple"
                />
              ))}
            </View>
          ) : null}
          <View style={styles.feedbackRow}>
            <SmallAction label="Helpful" onPress={() => undefined} />
            <SmallAction label="Not Helpful" onPress={() => undefined} />
          </View>
        </View>
      ) : null}
    </View>
  );
}

function CompactList({ items, title }: { items: string[]; title: string }) {
  return (
    <View style={styles.compactSection}>
      <Text style={styles.sectionLabel}>{title}</Text>
      {items.map((item, index) => (
        <View key={`${title}-${item}-${index}`} style={styles.evidenceRow}>
          <View style={styles.evidenceDot} />
          <Text style={styles.evidenceText}>{item}</Text>
        </View>
      ))}
    </View>
  );
}

function confidenceLabel(level?: 'high' | 'moderate' | 'limited') {
  if (level === 'high') {
    return 'High';
  }
  if (level === 'limited') {
    return 'Limited';
  }
  return 'Moderate';
}

function confidenceTone(level?: 'high' | 'moderate' | 'limited') {
  if (level === 'high') {
    return 'success' as const;
  }
  if (level === 'limited') {
    return 'warning' as const;
  }
  return 'purple' as const;
}

function SmallAction({ label, onPress }: { label: string; onPress: () => void }) {
  return (
    <Pressable accessibilityLabel={label} accessibilityRole="button" onPress={onPress} style={({ pressed }) => [styles.smallAction, pressed && styles.pressed]}>
      <Text style={styles.smallActionText}>{label}</Text>
    </Pressable>
  );
}

function loadingTextForContext(context: CopilotContext) {
  if (context.screenType === 'report') {
    return 'Reading the selected report…';
  }
  if (context.screenType === 'watchlist') {
    return 'Comparing watchlist signals…';
  }
  if (context.focusedMetric) {
    return 'Evaluating score contributors…';
  }
  return 'Reviewing today’s market context…';
}

const styles = StyleSheet.create({
  assistantBubble: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
  },
  answerStack: {
    gap: Spacing.two,
  },
  badgeRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.one,
  },
  cautionBox: {
    backgroundColor: Theme.colors.warningSoft,
    borderColor: Theme.colors.warning,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    gap: 4,
    padding: Spacing.two,
  },
  cautionText: {
    color: Theme.colors.text,
    fontSize: 13,
    fontWeight: '800',
    lineHeight: 19,
  },
  compactSection: {
    gap: Spacing.one,
  },
  confidenceText: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '800',
    lineHeight: 16,
  },
  contextHeader: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  contextMeta: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '800',
    textTransform: 'capitalize',
  },
  contextStack: {
    gap: Spacing.two,
  },
  contextText: {
    color: Theme.colors.textMuted,
    fontSize: 13,
    fontWeight: '700',
    lineHeight: 19,
  },
  contextTitle: {
    color: Theme.colors.text,
    fontSize: 15,
    fontWeight: '900',
  },
  contextTitleBlock: {
    flex: 1,
    gap: 2,
    minWidth: 0,
  },
  disabled: {
    opacity: 0.5,
  },
  evidenceDot: {
    backgroundColor: Theme.colors.purple,
    borderRadius: 3,
    height: 6,
    marginTop: 7,
    width: 6,
  },
  evidenceRow: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: Spacing.one,
  },
  evidenceText: {
    color: Theme.colors.text,
    flex: 1,
    fontSize: 13,
    fontWeight: '700',
    lineHeight: 19,
  },
  errorText: {
    color: Theme.colors.danger,
    fontSize: 13,
    fontWeight: '800',
  },
  feedbackRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.one,
  },
  followUpRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.one,
  },
  footerDisclaimer: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '700',
    lineHeight: 16,
    paddingHorizontal: Spacing.one,
    textAlign: 'center',
  },
  groundingText: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '800',
    lineHeight: 17,
  },
  inlineActions: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  input: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    color: Theme.colors.text,
    fontSize: 14,
    fontWeight: '700',
    lineHeight: 20,
    minHeight: 90,
    padding: Spacing.twoAndHalf,
    textAlignVertical: 'top',
  },
  loadingRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
    padding: Spacing.two,
  },
  loadingText: {
    color: Theme.colors.textMuted,
    fontSize: 13,
    fontWeight: '800',
  },
  messageBubble: {
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    gap: Spacing.one,
    padding: Spacing.twoAndHalf,
  },
  messageRole: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '900',
    textTransform: 'uppercase',
  },
  messageStack: {
    gap: Spacing.two,
  },
  messageText: {
    color: Theme.colors.text,
    fontSize: 14,
    fontWeight: '700',
    lineHeight: 22,
  },
  pressed: {
    opacity: 0.76,
  },
  promptStack: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  responseMeta: {
    gap: Spacing.two,
    marginTop: Spacing.two,
  },
  sectionLabel: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '900',
    textTransform: 'uppercase',
  },
  sendButton: {
    alignItems: 'center',
    alignSelf: 'flex-end',
    backgroundColor: Theme.colors.purple,
    borderRadius: Theme.radii.pill,
    marginTop: Spacing.two,
    minHeight: 42,
    paddingHorizontal: Spacing.four,
    paddingVertical: Spacing.two,
  },
  sendText: {
    color: Theme.colors.background,
    fontSize: 13,
    fontWeight: '900',
  },
  smallAction: {
    backgroundColor: Theme.colors.card,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    paddingHorizontal: Spacing.two,
    paddingVertical: Spacing.one,
  },
  smallActionText: {
    color: Theme.colors.text,
    fontSize: 11,
    fontWeight: '900',
  },
  userBubble: {
    alignSelf: 'flex-end',
    backgroundColor: Theme.colors.purpleSoft,
    borderColor: Theme.colors.purple,
    maxWidth: '92%',
  },
});
