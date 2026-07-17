import { StyleSheet, Text, View } from 'react-native';

import { Spacing, Theme } from '@/constants/theme';

type AIBulletListProps = {
  emptyText?: string;
  items?: string[];
  tone?: 'success' | 'warning' | 'danger' | 'info' | 'purple' | 'muted';
};

export function AIBulletList({
  emptyText = 'No insight available.',
  items,
  tone = 'purple',
}: AIBulletListProps) {
  const bulletColor = getBulletColor(tone);
  const safeItems = items?.length ? items : [emptyText];

  return (
    <View style={styles.list}>
      {safeItems.map((item, index) => (
        <View key={`${item}-${index}`} style={styles.item}>
          <View style={[styles.bullet, { backgroundColor: bulletColor }]} />
          <Text style={styles.text}>{item}</Text>
        </View>
      ))}
    </View>
  );
}

function getBulletColor(tone: NonNullable<AIBulletListProps['tone']>) {
  switch (tone) {
    case 'success':
      return Theme.colors.success;
    case 'warning':
      return Theme.colors.warning;
    case 'danger':
      return Theme.colors.danger;
    case 'info':
      return Theme.colors.accent;
    case 'muted':
      return Theme.colors.textMuted;
    default:
      return Theme.colors.purple;
  }
}

const styles = StyleSheet.create({
  bullet: {
    borderRadius: 4,
    height: 8,
    marginTop: 7,
    width: 8,
  },
  item: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: Spacing.two,
  },
  list: {
    gap: Spacing.two,
  },
  text: {
    color: Theme.colors.text,
    flex: 1,
    fontSize: 13,
    lineHeight: 20,
  },
});
