import { useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import { AIConfidenceBadge } from '@/components/ai/AIConfidenceBadge';
import { AIBulletList } from '@/components/ai/AIBulletList';
import { AISection } from '@/components/ai/AISection';
import { DashboardCard } from '@/components/cards/DashboardCard';
import { QuickActionChip } from '@/components/ui/QuickActionChip';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Spacing, Theme, Typography } from '@/constants/theme';
import { askAIChat } from '@/services/api';
import type { AIChatResponse } from '@/types/market';

type AIChatBoxProps = {
  initialPrompt?: string;
  placeholder?: string;
  suggestedPrompts?: string[];
  symbol?: string;
};

export function AIChatBox({
  initialPrompt = '',
  placeholder = 'Ask the AI analyst...',
  suggestedPrompts,
  symbol,
}: AIChatBoxProps) {
  const [question, setQuestion] = useState(initialPrompt);
  const [response, setResponse] = useState<AIChatResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submitChat(promptOverride?: string) {
    const prompt = (promptOverride ?? question).trim();

    if (!prompt || loading) {
      return;
    }

    setQuestion(prompt);
    setLoading(true);
    setError(null);

    try {
      const chatResponse = await askAIChat(prompt, symbol);
      setResponse(chatResponse);
    } catch (chatError) {
      setError(chatError instanceof Error ? chatError.message : 'Unable to reach AI analyst.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <View style={styles.container}>
      {suggestedPrompts?.length ? (
        <View style={styles.suggestedPrompts}>
          {suggestedPrompts.map((prompt) => (
            <QuickActionChip
              key={prompt}
              label={prompt}
              onPress={() => submitChat(prompt)}
              tone="purple"
            />
          ))}
        </View>
      ) : null}

      <DashboardCard title={symbol ? `${symbol} AI Chat` : 'Ask AI Analyst'} accentColor={Theme.colors.purple}>
        <View style={styles.inputStack}>
          <TextInput
            multiline
            onChangeText={setQuestion}
            placeholder={placeholder}
            placeholderTextColor={Theme.colors.textMuted}
            style={styles.input}
            value={question}
          />

          {error ? (
            <View style={styles.errorBox}>
              <Text style={styles.errorText}>{error}</Text>
            </View>
          ) : null}

          <Pressable
            accessibilityRole="button"
            disabled={!question.trim() || loading}
            onPress={() => submitChat()}
            style={({ pressed }) => [
              styles.sendButton,
              (!question.trim() || loading) && styles.sendButtonDisabled,
              pressed && styles.pressed,
            ]}>
            {loading ? <ActivityIndicator color={Theme.colors.background} /> : null}
            <Text style={styles.sendButtonText}>{loading ? 'Thinking...' : 'Send'}</Text>
          </Pressable>
        </View>
      </DashboardCard>

      {response ? <AIChatResponseCard response={response} /> : null}
    </View>
  );
}

function AIChatResponseCard({ response }: { response: AIChatResponse }) {
  return (
    <DashboardCard title="AI Analyst Response" accentColor={Theme.colors.purple}>
      <View style={styles.responseStack}>
        <Text style={styles.answer}>{response.answer || 'No answer returned.'}</Text>

        <AIConfidenceBadge
          confidence={response.confidence}
          generatedBy={response.generated_by}
          nextUpdate="On demand"
        />

        {response.key_points?.length ? (
          <AISection title="Key Points">
            <AIBulletList items={response.key_points} tone="info" />
          </AISection>
        ) : null}

        {response.risks?.length ? (
          <AISection title="Risks">
            <AIBulletList items={response.risks} tone="warning" />
          </AISection>
        ) : null}

        {response.what_to_watch?.length ? (
          <AISection title="What to Watch">
            <AIBulletList items={response.what_to_watch} tone="purple" />
          </AISection>
        ) : null}

        {response.related_symbols?.length ? (
          <AISection title="Related Symbols">
            <View style={styles.symbolRow}>
              {response.related_symbols.map((relatedSymbol) => (
                <StatusBadge key={relatedSymbol} label={relatedSymbol} tone="info" />
              ))}
            </View>
          </AISection>
        ) : null}

        {response.disclaimer ? <Text style={styles.disclaimer}>{response.disclaimer}</Text> : null}
      </View>
    </DashboardCard>
  );
}

const styles = StyleSheet.create({
  answer: {
    color: Theme.colors.text,
    fontSize: Typography.body.fontSize,
    fontWeight: Typography.weights.emphasis,
    lineHeight: 22,
  },
  container: {
    gap: Spacing.three,
  },
  disclaimer: {
    color: Theme.colors.textMuted,
    fontSize: Typography.caption.fontSize,
    fontWeight: Typography.weights.strong,
    lineHeight: 16,
  },
  errorBox: {
    backgroundColor: Theme.colors.dangerSoft,
    borderColor: Theme.colors.danger,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    padding: Spacing.two,
  },
  errorText: {
    color: Theme.colors.danger,
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.strong,
    lineHeight: 18,
  },
  input: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    color: Theme.colors.text,
    fontSize: Typography.body.fontSize,
    fontWeight: Typography.weights.emphasis,
    lineHeight: 20,
    minHeight: 92,
    padding: Spacing.twoAndHalf,
    textAlignVertical: 'top',
  },
  inputStack: {
    gap: Spacing.two,
  },
  pressed: {
    opacity: 0.82,
  },
  responseStack: {
    gap: Spacing.three,
  },
  sendButton: {
    alignItems: 'center',
    alignSelf: 'flex-end',
    backgroundColor: Theme.colors.purple,
    borderRadius: Theme.radii.pill,
    flexDirection: 'row',
    gap: Spacing.two,
    minHeight: 44,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.two,
  },
  sendButtonDisabled: {
    opacity: 0.48,
  },
  sendButtonText: {
    color: Theme.colors.background,
    fontSize: Typography.control.fontSize,
    fontWeight: Typography.weights.strong,
  },
  suggestedPrompts: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  symbolRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.one,
  },
});
