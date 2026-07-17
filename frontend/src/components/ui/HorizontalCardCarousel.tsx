import type { ReactNode } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import { Spacing, Theme } from '@/constants/theme';

type HorizontalCardCarouselProps = {
  children: ReactNode;
  subtitle?: string;
  title?: string;
};

export function HorizontalCardCarousel({
  children,
  subtitle,
  title,
}: HorizontalCardCarouselProps) {
  return (
    <View style={styles.container}>
      {title || subtitle ? (
        <View style={styles.header}>
          {title ? <Text style={styles.title}>{title}</Text> : null}
          {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
        </View>
      ) : null}
      <ScrollView
        horizontal
        contentContainerStyle={styles.content}
        showsHorizontalScrollIndicator={false}>
        {children}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: Spacing.two,
  },
  header: {
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
  content: {
    gap: Spacing.two,
    paddingRight: Spacing.three,
  },
});
