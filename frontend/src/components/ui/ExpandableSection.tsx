import { useState } from 'react';
import type { ReactNode } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Spacing, Theme } from '@/constants/theme';

type ExpandableSectionProps = {
  children: ReactNode;
  defaultExpanded?: boolean;
  summary?: string | number | null;
  title: string;
};

export function ExpandableSection({
  children,
  defaultExpanded = false,
  summary,
  title,
}: ExpandableSectionProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const safeSummary =
    typeof summary === 'string' || typeof summary === 'number' ? summary : null;

  return (
    <View style={styles.container}>
      <Pressable
        accessibilityRole="button"
        accessibilityState={{ expanded }}
        onPress={() => setExpanded((current) => !current)}
        style={styles.header}>
        <View style={styles.titleBlock}>
          <Text style={styles.title}>{title}</Text>
          {safeSummary ? <Text style={styles.summary}>{safeSummary}</Text> : null}
        </View>
        <Text style={styles.chevron}>{expanded ? '▾' : '▸'}</Text>
      </Pressable>

      {expanded ? <View style={styles.content}>{children}</View> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    overflow: 'hidden',
  },
  header: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
    minHeight: 48,
    paddingHorizontal: Spacing.twoAndHalf,
    paddingVertical: Spacing.two,
  },
  titleBlock: {
    flex: 1,
    gap: Spacing.half,
  },
  title: {
    color: Theme.colors.text,
    fontSize: 14,
    fontWeight: '900',
  },
  summary: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '700',
    lineHeight: 17,
  },
  chevron: {
    color: Theme.colors.textMuted,
    fontSize: 18,
    fontWeight: '900',
  },
  content: {
    borderColor: Theme.colors.border,
    borderTopWidth: 1,
    padding: Spacing.twoAndHalf,
  },
});
