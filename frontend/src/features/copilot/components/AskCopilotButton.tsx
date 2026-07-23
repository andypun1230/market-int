import { useRouter } from 'expo-router';
import { StyleSheet } from 'react-native';

import { AppButton } from '@/components/ui/AppButton';
import { AppIcon } from '@/components/ui/AppIcon';
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
    <AppButton
      accessibilityLabel={`${label} using ${context.screenTitle} context`}
      label={label}
      leadingIcon={<AppIcon color={Theme.colors.purple} name="sparkles" size={14} />}
      onPress={() => {
        setCopilotLaunchContext(sanitizeCopilotContext(context), prompt);
        router.push('/ai');
      }}
      style={styles.button}
      tone="copilot"
      variant="compact"
    />
  );
}

export function ExplainThisButton({ context, prompt }: AskCopilotButtonProps) {
  return <AskCopilotButton context={context} label="Explain This" prompt={prompt ?? 'Explain this value and what would cause it to rise or fall.'} />;
}

const styles = StyleSheet.create({
  button: {
    borderRadius: Theme.radii.pill,
    paddingHorizontal: Spacing.twoAndHalf,
  },
});
