import { useRouter } from 'expo-router';
import { SymbolView } from 'expo-symbols';
import { Pressable, StyleSheet, Text } from 'react-native';

import { Spacing, Theme } from '@/constants/theme';
import type { CopilotContext } from '@/features/copilot/types';
import { setCopilotLaunchContext } from '@/features/copilot/state/copilotStore';
import { sanitizeCopilotContext } from '@/features/copilot/utils/sanitizeCopilotContext';

type AskCopilotButtonProps = {
  context: CopilotContext;
  label?: string;
  prompt?: string;
};

export function AskCopilotButton({ context, label = 'Ask Copilot', prompt }: AskCopilotButtonProps) {
  const router = useRouter();
  return (
    <Pressable
      accessibilityLabel={`${label} using ${context.screenTitle} context`}
      accessibilityRole="button"
      onPress={() => {
        setCopilotLaunchContext(sanitizeCopilotContext(context), prompt);
        router.push('/ai');
      }}
      style={({ pressed }) => [styles.button, pressed && styles.pressed]}>
      <SymbolView name="sparkles" size={14} tintColor={Theme.colors.purple} weight="bold" />
      <Text style={styles.label}>{label}</Text>
    </Pressable>
  );
}

export function ExplainThisButton({ context, prompt }: AskCopilotButtonProps) {
  return <AskCopilotButton context={context} label="Explain This" prompt={prompt ?? 'Explain this value and what would cause it to rise or fall.'} />;
}

const styles = StyleSheet.create({
  button: {
    alignItems: 'center',
    alignSelf: 'flex-start',
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.purple,
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    flexDirection: 'row',
    gap: Spacing.one,
    minHeight: 34,
    paddingHorizontal: Spacing.twoAndHalf,
    paddingVertical: Spacing.two,
  },
  label: {
    color: Theme.colors.purple,
    fontSize: 12,
    fontWeight: '900',
  },
  pressed: {
    opacity: 0.76,
  },
});
