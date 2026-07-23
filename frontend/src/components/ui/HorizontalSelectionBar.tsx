import { useCallback, useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { Platform, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import type { LayoutChangeEvent } from 'react-native';

import { selectedItemScrollOffset } from '@/architecture/layoutPolicy';
import { webRovingTabProps } from '@/architecture/keyboardNavigation';
import { Spacing, Theme, Typography } from '@/constants/theme';

export type HorizontalSelectionItem<Key extends string> = {
  icon?: ReactNode;
  key: Key;
  label: string;
};

type ItemLayout = { width: number; x: number };

export function HorizontalSelectionBar<Key extends string>({
  accessibilityLabel,
  items,
  onChange,
  selectedKey,
}: {
  accessibilityLabel: string;
  items: HorizontalSelectionItem<Key>[];
  onChange: (key: Key) => void;
  selectedKey: Key;
}) {
  const scrollRef = useRef<ScrollView | null>(null);
  const itemLayouts = useRef(new Map<Key, ItemLayout>());
  const [contentWidth, setContentWidth] = useState(0);
  const [viewportWidth, setViewportWidth] = useState(0);

  const revealSelected = useCallback((animated: boolean) => {
    const item = itemLayouts.current.get(selectedKey);
    if (!item || !contentWidth || !viewportWidth) return;
    scrollRef.current?.scrollTo({
      animated,
      x: selectedItemScrollOffset({ contentWidth, itemWidth: item.width, itemX: item.x, viewportWidth }),
    });
  }, [contentWidth, selectedKey, viewportWidth]);

  useEffect(() => {
    const frame = requestAnimationFrame(() => revealSelected(false));
    return () => cancelAnimationFrame(frame);
  }, [revealSelected]);

  const captureViewport = (event: LayoutChangeEvent) => {
    setViewportWidth(event.nativeEvent.layout.width);
  };

  return (
    <ScrollView
      accessibilityLabel={accessibilityLabel}
      accessibilityRole="tablist"
      horizontal
      onContentSizeChange={(width) => setContentWidth(width)}
      onLayout={captureViewport}
      ref={scrollRef}
      showsHorizontalScrollIndicator={false}>
      <View style={styles.content}>
        {items.map((item, index) => {
          const selected = selectedKey === item.key;
          return (
            <Pressable
              accessibilityHint={`${index + 1} of ${items.length}`}
              accessibilityLabel={item.label}
              accessibilityRole="tab"
              accessibilityState={{ selected }}
              aria-selected={selected}
              key={item.key}
              {...webRovingTabProps({
                count: items.length,
                enabled: Platform.OS === 'web',
                index,
                onSelect: (nextIndex) => onChange(items[nextIndex].key),
                selected,
              })}
              onLayout={(event) => {
                const { width, x } = event.nativeEvent.layout;
                itemLayouts.current.set(item.key, { width, x });
                if (item.key === selectedKey) requestAnimationFrame(() => revealSelected(false));
              }}
              onPress={() => onChange(item.key)}
              style={({ pressed }) => [
                styles.item,
                selected && styles.selectedItem,
                pressed && styles.pressedItem,
              ]}>
              {item.icon ? (
                <View accessibilityElementsHidden aria-hidden importantForAccessibility="no-hide-descendants">
                  {item.icon}
                </View>
              ) : null}
              <Text style={[styles.label, selected && styles.selectedLabel]}>{item.label}</Text>
            </Pressable>
          );
        })}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: {
    flexDirection: 'row',
    gap: Spacing.two,
    paddingRight: Spacing.three,
  },
  item: {
    alignItems: 'center',
    backgroundColor: Theme.colors.card,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    flexDirection: 'row',
    gap: Spacing.two,
    minHeight: 44,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.two,
  },
  label: {
    color: Theme.colors.textMuted,
    fontSize: Typography.control.fontSize,
    fontWeight: Typography.weights.strong,
  },
  pressedItem: {
    opacity: 0.78,
  },
  selectedItem: {
    backgroundColor: Theme.colors.accentSoft,
    borderColor: Theme.colors.accent,
  },
  selectedLabel: {
    color: Theme.colors.accent,
  },
});
