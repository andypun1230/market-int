import { useCallback, useEffect, useRef, useState } from 'react';
import { Platform, ScrollView, Pressable, StyleSheet, Text, View } from 'react-native';

import { selectedItemScrollOffset } from '@/architecture/layoutPolicy';
import { webRovingTabProps } from '@/architecture/keyboardNavigation';
import { Spacing, Theme, Typography } from '@/constants/theme';

type SegmentedOption = {
  key: string;
  label: string;
};

type SegmentedControlProps = {
  compact?: boolean;
  dense?: boolean;
  fullWidth?: boolean;
  label?: string;
  onChange: (key: string) => void;
  options: SegmentedOption[];
  selectedKey: string;
  variant?: 'chips' | 'switch';
  wrap?: boolean;
};

export function SegmentedControl({
  compact = false,
  dense = false,
  fullWidth = false,
  label,
  onChange,
  options,
  selectedKey,
  variant = 'chips',
  wrap = false,
}: SegmentedControlProps) {
  const isSwitch = variant === 'switch';
  const scrollRef = useRef<ScrollView | null>(null);
  const itemLayouts = useRef(new Map<string, { width: number; x: number }>());
  const [contentWidth, setContentWidth] = useState(0);
  const [viewportWidth, setViewportWidth] = useState(0);
  const revealSelected = useCallback((animated: boolean) => {
    const item = itemLayouts.current.get(selectedKey);
    if (!item || !contentWidth || !viewportWidth || fullWidth || wrap) return;
    scrollRef.current?.scrollTo({
      animated,
      x: selectedItemScrollOffset({ contentWidth, itemWidth: item.width, itemX: item.x, viewportWidth }),
    });
  }, [contentWidth, fullWidth, selectedKey, viewportWidth, wrap]);

  useEffect(() => {
    const frame = requestAnimationFrame(() => revealSelected(false));
    return () => cancelAnimationFrame(frame);
  }, [revealSelected]);

  const content = options.map((option, index) => {
    const selected = option.key === selectedKey;

    return (
      <Pressable
        accessibilityHint={`${index + 1} of ${options.length}`}
        accessibilityLabel={option.label}
        accessibilityRole="tab"
        accessibilityState={{ selected }}
        aria-selected={selected}
        key={option.key}
        {...webRovingTabProps({
          count: options.length,
          enabled: Platform.OS === 'web',
          index,
          onSelect: (nextIndex) => onChange(options[nextIndex].key),
          selected,
        })}
        onLayout={(event) => {
          const { width, x } = event.nativeEvent.layout;
          itemLayouts.current.set(option.key, { width, x });
          if (selected) requestAnimationFrame(() => revealSelected(false));
        }}
        onPress={() => onChange(option.key)}
        style={({ pressed }) => [
          styles.chip,
          isSwitch && styles.switchChip,
          compact && styles.compactChip,
          dense && styles.denseChip,
          fullWidth && styles.fullWidthChip,
          selected && styles.selectedChip,
          isSwitch && selected && styles.selectedSwitchChip,
          pressed && styles.pressedChip,
        ]}>
        <Text numberOfLines={1} style={[styles.label, compact && styles.compactLabel, dense && styles.denseLabel, fullWidth && styles.fullWidthLabel, selected && styles.selectedLabel]}>{option.label}</Text>
      </Pressable>
    );
  });

  return (
    <View style={[styles.wrapper, isSwitch && styles.switchWrapper]}>
      {label ? <Text style={styles.controlLabel}>{label}</Text> : null}
      {fullWidth || wrap ? (
        <View style={[
          styles.content,
          isSwitch && styles.switchContent,
          (fullWidth || wrap) && styles.fullWidthContent,
          wrap && styles.wrapContent,
        ]}>
          {content}
        </View>
      ) : (
        <ScrollView
          accessibilityLabel={label ?? 'Options'}
          accessibilityRole="tablist"
          horizontal
          contentContainerStyle={[
            styles.content,
            isSwitch && styles.switchContent,
          ]}
          onContentSizeChange={(width) => setContentWidth(width)}
          onLayout={(event) => setViewportWidth(event.nativeEvent.layout.width)}
          ref={scrollRef}
          showsHorizontalScrollIndicator={false}>
          {content}
        </ScrollView>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  content: {
    flexDirection: 'row',
    gap: Spacing.two,
    paddingRight: Spacing.three,
  },
  chip: {
    backgroundColor: Theme.colors.card,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    minHeight: 44,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.two,
  },
  compactChip: {
    paddingHorizontal: Spacing.one,
  },
  compactLabel: {
    fontSize: Typography.small.fontSize,
  },
  denseChip: {
    paddingHorizontal: Spacing.half,
  },
  denseLabel: {
    fontSize: Typography.caption.fontSize,
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
    fontSize: Typography.control.fontSize,
    fontWeight: Typography.weights.strong,
  },
  controlLabel: {
    color: Theme.colors.textMuted,
    fontSize: Typography.caption.fontSize,
    fontWeight: Typography.weights.strong,
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
    minHeight: 44,
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
  wrapContent: {
    flexWrap: 'wrap',
  },
  wrapper: {
    gap: Spacing.one,
  },
});
