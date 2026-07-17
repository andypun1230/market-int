import { PropsWithChildren } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { Spacing, Theme } from '@/constants/theme';

type AISectionProps = PropsWithChildren<{
  title: string;
}>;

export function AISection({ children, title }: AISectionProps) {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>{title}</Text>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    gap: Spacing.two,
    padding: Spacing.twoAndHalf,
  },
  title: {
    color: Theme.colors.text,
    fontSize: 12,
    fontWeight: '900',
    textTransform: 'uppercase',
  },
});
