import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';

import { Spacing, Theme } from '@/constants/theme';

type LoadingStateProps = {
  inverse?: boolean;
  label?: string;
  title?: string;
  variant?: 'screen' | 'card' | 'list';
};

export function LoadingState({
  inverse = false,
  label = 'Loading...',
  title,
  variant = 'card',
}: LoadingStateProps) {
  const rows = variant === 'list' ? 4 : 3;

  return (
    <View style={[styles.container, styles[variant], inverse && styles.inverseContainer]}>
      <View style={styles.header}>
        <ActivityIndicator color={inverse ? Theme.colors.textInverse : Theme.colors.accent} />
        <View style={styles.copy}>
          {title ? <Text style={[styles.title, inverse && styles.inverseLabel]}>{title}</Text> : null}
          <Text style={[styles.label, inverse && styles.inverseLabel]}>{label}</Text>
        </View>
      </View>
      <View style={styles.placeholderStack}>
        {Array.from({ length: rows }).map((_, index) => (
          <View
            key={index}
            style={[
              styles.placeholder,
              index === rows - 1 && styles.placeholderShort,
              inverse && styles.inversePlaceholder,
            ]}
          />
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: Theme.colors.card,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.card,
    borderWidth: 1,
    gap: Spacing.three,
    justifyContent: 'center',
    padding: Spacing.three,
  },
  screen: {
    minHeight: 180,
  },
  card: {
    minHeight: 116,
  },
  list: {
    minHeight: 156,
  },
  inverseContainer: {
    backgroundColor: 'rgba(15, 23, 42, 0.24)',
    borderColor: 'rgba(148, 163, 184, 0.22)',
  },
  header: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
  },
  copy: {
    flex: 1,
    gap: Spacing.half,
  },
  title: {
    color: Theme.colors.text,
    fontSize: 14,
    fontWeight: '900',
  },
  label: {
    color: Theme.colors.textMuted,
    fontSize: 13,
    fontWeight: '700',
  },
  inverseLabel: {
    color: Theme.colors.textInverseMuted,
  },
  placeholderStack: {
    gap: Spacing.two,
  },
  placeholder: {
    backgroundColor: Theme.colors.cardMuted,
    borderRadius: Theme.radii.small,
    height: 10,
    opacity: 0.9,
    width: '100%',
  },
  placeholderShort: {
    width: '62%',
  },
  inversePlaceholder: {
    backgroundColor: 'rgba(148, 163, 184, 0.24)',
  },
});
