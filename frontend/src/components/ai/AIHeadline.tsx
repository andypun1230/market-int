import { StyleSheet, Text, View } from 'react-native';

import { Spacing, Theme, Typography } from '@/constants/theme';

type AIHeadlineProps = {
  headline?: string;
  label?: string;
  summary?: string;
};

export function AIHeadline({ headline, label = 'AI Insight', summary }: AIHeadlineProps) {
  return (
    <View style={styles.container}>
      <Text style={styles.label}>{label}</Text>
      <Text style={styles.headline}>{headline ?? 'Insight unavailable'}</Text>
      {summary ? <Text style={styles.summary}>{summary}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: Spacing.one,
  },
  headline: {
    color: Theme.colors.text,
    fontSize: Typography.toolbarTitle.fontSize,
    fontWeight: Typography.weights.strong,
    lineHeight: 25,
  },
  label: {
    color: Theme.colors.purple,
    fontSize: Typography.caption.fontSize,
    fontWeight: Typography.weights.strong,
    textTransform: 'uppercase',
  },
  summary: {
    color: Theme.colors.textMuted,
    fontSize: Typography.body.fontSize,
    lineHeight: 21,
  },
});
