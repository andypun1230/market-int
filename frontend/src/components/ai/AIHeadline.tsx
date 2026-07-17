import { StyleSheet, Text, View } from 'react-native';

import { Spacing, Theme } from '@/constants/theme';

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
    fontSize: 19,
    fontWeight: '900',
    lineHeight: 25,
  },
  label: {
    color: Theme.colors.purple,
    fontSize: 11,
    fontWeight: '900',
    textTransform: 'uppercase',
  },
  summary: {
    color: Theme.colors.textMuted,
    fontSize: 14,
    lineHeight: 21,
  },
});
