import type { ReactNode } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { Spacing, Theme } from '@/constants/theme';

type SectionHeaderProps = {
  rightElement?: ReactNode;
  subtitle?: string;
  title: string;
};

export function SectionHeader({ rightElement, subtitle, title }: SectionHeaderProps) {
  return (
    <View style={styles.container}>
      <View style={styles.row}>
        <View style={styles.copy}>
          <Text style={styles.title}>{title}</Text>
          {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
        </View>
        {rightElement ? <View style={styles.rightElement}>{rightElement}</View> : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: Spacing.one,
  },
  row: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  copy: {
    flex: 1,
    gap: Spacing.one,
  },
  title: {
    color: Theme.colors.text,
    fontSize: 18,
    fontWeight: '900',
  },
  subtitle: {
    color: Theme.colors.textMuted,
    fontSize: 13,
    lineHeight: 19,
  },
  rightElement: {
    flexShrink: 0,
  },
});
