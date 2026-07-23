import { useState } from 'react';
import type { ReactNode } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { AppIcon } from '@/components/ui/AppIcon';
import { Spacing, Theme, Typography } from '@/constants/theme';

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
        <AppIcon name={expanded ? 'chevronDown' : 'chevronRight'} size={18} />
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
    fontSize: Typography.body.fontSize,
    fontWeight: Typography.weights.strong,
  },
  summary: {
    color: Theme.colors.textMuted,
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.emphasis,
    lineHeight: 17,
  },
  content: {
    borderColor: Theme.colors.border,
    borderTopWidth: 1,
    padding: Spacing.twoAndHalf,
  },
});
