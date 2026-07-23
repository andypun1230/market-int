import { Pressable, StyleSheet, Text, View } from 'react-native';

import { AppIcon } from '@/components/ui/AppIcon';
import { StatusBadge, type Tone } from '@/components/ui/StatusBadge';
import { Spacing, Theme, Typography } from '@/constants/theme';
import { getSectorThemeStatusLabel } from '@/features/watchlist/sectorThemeClassifier';
import type { ClassifiedSectorThemeItem } from '@/features/watchlist/sectorThemeSort';

type SectorThemeRowProps = {
  entry: ClassifiedSectorThemeItem;
  onOpen: () => void;
  onRemove: () => void;
};

export function SectorThemeRow({ entry, onOpen, onRemove }: SectorThemeRowProps) {
  const { classification, stored } = entry;
  const typeLabel = stored.type === 'sector' ? 'Sector' : 'Theme';
  const statusLabel = getSectorThemeStatusLabel(classification.primaryStatus);
  const tone = getStatusTone(classification.primaryStatus);

  return (
    <Pressable
      accessibilityLabel={`Open ${stored.name}, ${typeLabel}, ${statusLabel}`}
      accessibilityRole="button"
      disabled={!entry.item}
      onPress={onOpen}
      style={({ pressed }) => [styles.row, !entry.item && styles.disabled, pressed && styles.pressed]}>
      <View style={styles.main}>
        <View style={styles.titleRow}>
          <Text numberOfLines={1} style={styles.name}>{stored.name}</Text>
          <StatusBadge label={typeLabel} showDot={false} tone={stored.type === 'sector' ? 'info' : 'purple'} />
        </View>
        <Text numberOfLines={1} style={styles.meta}>
          {typeLabel} · {statusLabel} · {classification.reason}
        </Text>
      </View>
      <View style={styles.side}>
        <Text style={[styles.returnText, { color: getReturnColor(classification.returnPercent) }]}>
          {formatReturn(classification.returnPercent)}
        </Text>
        <StatusBadge label={statusLabel} showDot={false} tone={tone} />
      </View>
      <Pressable
        accessibilityLabel={`Remove ${stored.name} from watchlist`}
        accessibilityRole="button"
        hitSlop={8}
        onPress={(event) => {
          event.stopPropagation();
          onRemove();
        }}
        style={({ pressed }) => [styles.bookmarkButton, pressed && styles.pressed]}>
        <AppIcon color={Theme.colors.warning} name="saved" size={17} />
      </Pressable>
      <AppIcon name="chevronRight" size={17} />
    </Pressable>
  );
}

function getStatusTone(status: ClassifiedSectorThemeItem['classification']['primaryStatus']): Tone {
  switch (status) {
    case 'leading':
      return 'success';
    case 'improving':
      return 'info';
    case 'weakening':
    case 'lagging':
      return 'warning';
    case 'unavailable':
      return 'danger';
    case 'neutral':
      return 'muted';
  }
}

function getReturnColor(value: number | null) {
  if (typeof value !== 'number') {
    return Theme.colors.textMuted;
  }
  if (value > 0) {
    return Theme.colors.success;
  }
  if (value < 0) {
    return Theme.colors.danger;
  }
  return Theme.colors.textMuted;
}

function formatReturn(value: number | null) {
  if (typeof value !== 'number') {
    return 'N/A';
  }
  const prefix = value > 0 ? '+' : '';
  return `${prefix}${value.toFixed(2)}%`;
}

const styles = StyleSheet.create({
  bookmarkButton: {
    alignItems: 'center',
    borderRadius: Theme.radii.pill,
    height: 44,
    justifyContent: 'center',
    width: 44,
  },
  bookmarkIcon: {
    color: Theme.colors.warning,
    fontSize: Typography.supportTitle.fontSize,
    fontWeight: Typography.weights.strong,
  },
  chevron: {
    color: Theme.colors.textMuted,
    fontSize: Typography.entityHero.fontSize,
    fontWeight: Typography.weights.emphasis,
  },
  disabled: {
    opacity: 0.55,
  },
  main: {
    flex: 1,
    minWidth: 0,
  },
  meta: {
    color: Theme.colors.textMuted,
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.emphasis,
    lineHeight: 17,
    marginTop: Spacing.half,
  },
  name: {
    color: Theme.colors.text,
    flex: 1,
    fontSize: Typography.bodyLarge.fontSize,
    fontWeight: Typography.weights.strong,
  },
  pressed: {
    opacity: 0.78,
  },
  returnText: {
    fontSize: Typography.bodyLarge.fontSize,
    fontWeight: Typography.weights.strong,
    textAlign: 'right',
  },
  row: {
    alignItems: 'center',
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    flexDirection: 'row',
    gap: Spacing.one,
    minHeight: 62,
    paddingHorizontal: Spacing.two,
    paddingVertical: Spacing.one,
  },
  side: {
    alignItems: 'flex-end',
    gap: Spacing.half,
    minWidth: 78,
  },
  titleRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.one,
    minWidth: 0,
  },
});
