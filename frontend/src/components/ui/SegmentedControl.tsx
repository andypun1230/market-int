import { ScrollView, Pressable, StyleSheet, Text, View } from 'react-native';

import { Spacing, Theme } from '@/constants/theme';

type SegmentedOption = {
  key: string;
  label: string;
};

type SegmentedControlProps = {
  fullWidth?: boolean;
  label?: string;
  onChange: (key: string) => void;
  options: SegmentedOption[];
  selectedKey: string;
  variant?: 'chips' | 'switch';
};

export function SegmentedControl({
  fullWidth = false,
  label,
  onChange,
  options,
  selectedKey,
  variant = 'chips',
}: SegmentedControlProps) {
  const isSwitch = variant === 'switch';
  const content = options.map((option) => {
    const selected = option.key === selectedKey;

    return (
      <Pressable
        accessibilityRole="button"
        accessibilityState={{ selected }}
        key={option.key}
        onPress={() => onChange(option.key)}
        style={({ pressed }) => [
          styles.chip,
          isSwitch && styles.switchChip,
          fullWidth && styles.fullWidthChip,
          selected && styles.selectedChip,
          isSwitch && selected && styles.selectedSwitchChip,
          pressed && styles.pressedChip,
        ]}>
        <Text numberOfLines={1} style={[styles.label, fullWidth && styles.fullWidthLabel, selected && styles.selectedLabel]}>{option.label}</Text>
      </Pressable>
    );
  });

  return (
    <View style={[styles.wrapper, isSwitch && styles.switchWrapper]}>
      {label ? <Text style={styles.controlLabel}>{label}</Text> : null}
      {fullWidth ? (
        <View style={[
          styles.content,
          isSwitch && styles.switchContent,
          styles.fullWidthContent,
        ]}>
          {content}
        </View>
      ) : (
        <ScrollView
          horizontal
          contentContainerStyle={[
            styles.content,
            isSwitch && styles.switchContent,
          ]}
          showsHorizontalScrollIndicator={false}>
          {content}
        </ScrollView>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  content: {
    gap: Spacing.two,
    paddingRight: Spacing.three,
  },
  chip: {
    backgroundColor: Theme.colors.card,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    minHeight: 38,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.two,
  },
  selectedChip: {
    backgroundColor: Theme.colors.accentSoft,
    borderColor: Theme.colors.accent,
  },
  fullWidthChip: {
    alignItems: 'center',
    flexBasis: 0,
    flex: 1,
    justifyContent: 'center',
    minWidth: 0,
  },
  fullWidthContent: {
    paddingRight: 0,
    width: '100%',
  },
  fullWidthLabel: {
    textAlign: 'center',
  },
  pressedChip: {
    opacity: 0.78,
  },
  label: {
    color: Theme.colors.textMuted,
    fontSize: 13,
    fontWeight: '900',
  },
  controlLabel: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '900',
    textTransform: 'uppercase',
  },
  selectedLabel: {
    color: Theme.colors.accent,
  },
  selectedSwitchChip: {
    backgroundColor: Theme.colors.background,
  },
  switchChip: {
    backgroundColor: 'transparent',
    borderColor: 'transparent',
    minHeight: 34,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.one,
  },
  switchContent: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    gap: 0,
    padding: 3,
  },
  switchWrapper: {
    gap: Spacing.one,
  },
  wrapper: {
    gap: Spacing.one,
  },
});
