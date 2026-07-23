import { StyleSheet, Text, View } from 'react-native';

import { Spacing, Theme, Typography } from '@/constants/theme';

export function TestDataBadge({ label = 'Test Data' }: { label?: string }) {
  return (
    <View style={styles.badge}>
      <View style={styles.dot} />
      <Text style={styles.label}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    alignItems: 'center',
    alignSelf: 'flex-start',
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.warning,
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    flexDirection: 'row',
    gap: Spacing.one,
    paddingHorizontal: Spacing.two,
    paddingVertical: 5,
  },
  dot: {
    backgroundColor: Theme.colors.warning,
    borderRadius: 3,
    height: 6,
    width: 6,
  },
  label: {
    color: Theme.colors.warning,
    fontSize: Typography.caption.fontSize,
    fontWeight: Typography.weights.strong,
  },
});
