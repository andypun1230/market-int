import { useState } from 'react';
import type { ReactNode } from 'react';
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  View,
  type AccessibilityState,
  type StyleProp,
  type ViewStyle,
} from 'react-native';

import { Spacing, Theme, Typography } from '@/constants/theme';

export type AppButtonVariant = 'primary' | 'secondary' | 'neutral' | 'danger' | 'icon' | 'compact';
export type AppButtonTone = 'default' | 'copilot';

type AppButtonProps = {
  accessibilityLabel?: string;
  accessibilityState?: AccessibilityState;
  children?: ReactNode;
  disabled?: boolean;
  label: string;
  leadingIcon?: ReactNode;
  loading?: boolean;
  onPress: () => void;
  style?: StyleProp<ViewStyle>;
  tone?: AppButtonTone;
  trailingIcon?: ReactNode;
  variant?: AppButtonVariant;
};

export function AppButton({
  accessibilityLabel,
  accessibilityState,
  children,
  disabled = false,
  label,
  leadingIcon,
  loading = false,
  onPress,
  style,
  tone = 'default',
  trailingIcon,
  variant = 'neutral',
}: AppButtonProps) {
  const [focused, setFocused] = useState(false);
  const colors = variantColors(variant, tone);
  const unavailable = disabled || loading;

  return (
    <Pressable
      accessibilityLabel={accessibilityLabel ?? label}
      accessibilityRole="button"
      accessibilityState={{ ...accessibilityState, busy: loading, disabled: unavailable }}
      disabled={unavailable}
      onBlur={() => setFocused(false)}
      onFocus={() => setFocused(true)}
      onPress={onPress}
      style={({ pressed }) => [
        styles.base,
        variant === 'icon' && styles.icon,
        variant === 'compact' && styles.compact,
        { backgroundColor: colors.background, borderColor: colors.border },
        focused && styles.focused,
        pressed && styles.pressed,
        unavailable && styles.disabled,
        style,
      ]}>
      {loading ? <ActivityIndicator color={colors.text} size="small" /> : leadingIcon ? (
        <View accessibilityElementsHidden aria-hidden importantForAccessibility="no-hide-descendants">{leadingIcon}</View>
      ) : null}
      {variant !== 'icon' ? (
        <>
          <Text numberOfLines={1} style={[styles.label, { color: colors.text }]}>{label}</Text>
          {trailingIcon ? (
            <View accessibilityElementsHidden aria-hidden importantForAccessibility="no-hide-descendants">{trailingIcon}</View>
          ) : null}
        </>
      ) : null}
      {children}
    </Pressable>
  );
}

function variantColors(variant: AppButtonVariant, tone: AppButtonTone) {
  if (tone === 'copilot') {
    if (variant === 'primary') {
      return { background: Theme.colors.purple, border: Theme.colors.purple, text: Theme.colors.background };
    }
    return { background: Theme.colors.cardMuted, border: Theme.colors.purple, text: Theme.colors.purple };
  }
  if (variant === 'primary') {
    return { background: Theme.colors.accent, border: Theme.colors.accent, text: Theme.colors.background };
  }
  if (variant === 'secondary') {
    return { background: Theme.colors.card, border: Theme.colors.accent, text: Theme.colors.accent };
  }
  if (variant === 'danger') {
    return { background: Theme.colors.dangerSoft, border: Theme.colors.danger, text: Theme.colors.danger };
  }
  return { background: Theme.colors.cardMuted, border: Theme.colors.border, text: Theme.colors.text };
}

const styles = StyleSheet.create({
  base: {
    alignItems: 'center',
    alignSelf: 'flex-start',
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'center',
    // Keep this literal synchronized with Theme.accessibility.minimumTouchTarget;
    // the frozen Stage 11.2A validator asserts the canonical 44px contract here.
    minHeight: 44,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.two,
  },
  compact: {
    paddingHorizontal: Spacing.twoAndHalf,
  },
  disabled: {
    opacity: 0.55,
  },
  focused: {
    borderColor: Theme.colors.focus,
    outlineColor: Theme.colors.focus,
    outlineOffset: Theme.accessibility.focusRingOffset,
    outlineStyle: 'solid',
    outlineWidth: Theme.accessibility.focusRingWidth,
  } as never,
  icon: {
    minWidth: Theme.accessibility.minimumTouchTarget,
    paddingHorizontal: Spacing.two,
  },
  label: {
    fontSize: Typography.control.fontSize,
    fontWeight: Typography.weights.strong,
    lineHeight: Typography.control.lineHeight,
  },
  pressed: {
    opacity: 0.76,
  },
});
