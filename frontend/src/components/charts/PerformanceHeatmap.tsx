import { Pressable, StyleSheet, Text, View } from 'react-native';

import { AppIcon } from '@/components/ui/AppIcon';
import { Spacing, Theme, Typography } from '@/constants/theme';

type PerformanceHeatmapProps<T> = {
  emptyLabel?: string;
  getBadgeLabel?: (item: T) => string | null | undefined;
  getName: (item: T) => string;
  getSubtitle?: (item: T) => string | null | undefined;
  getValue: (item: T) => number | null;
  isFavourite?: (item: T) => boolean;
  items: T[];
  onPressItem?: (item: T) => void;
  onToggleFavourite?: (item: T) => void;
};

export function PerformanceHeatmap<T>({
  emptyLabel = 'No performance data available.',
  getBadgeLabel,
  getName,
  getSubtitle,
  getValue,
  isFavourite,
  items,
  onPressItem,
  onToggleFavourite,
}: PerformanceHeatmapProps<T>) {
  if (!items.length) {
    return <Text style={styles.emptyText}>{emptyLabel}</Text>;
  }

  return (
    <View style={styles.grid}>
      {items.map((item) => {
        const name = getName(item);
        const badgeLabel = getBadgeLabel?.(item);
        const subtitle = getSubtitle?.(item);
        const value = getValue(item);
        const palette = getReturnPalette(value);
        const favourite = Boolean(isFavourite?.(item));

        return (
          <Pressable
            accessibilityLabel={`${name}, ${formatPercent(value)}`}
            accessibilityRole={onPressItem ? 'button' : undefined}
            disabled={!onPressItem}
            key={name}
            onPress={() => onPressItem?.(item)}
            style={[
              styles.tile,
              {
                backgroundColor: palette.background,
                borderColor: palette.border,
              },
            ]}>
            {onToggleFavourite ? (
              <Pressable
                accessibilityLabel={`${favourite ? 'Remove' : 'Add'} ${name} watchlist`}
                accessibilityRole="button"
                hitSlop={8}
                onPress={(event) => {
                  event.stopPropagation();
                  onToggleFavourite(item);
                }}
                style={styles.favouriteButton}>
                <AppIcon color={favourite ? Theme.colors.warning : Theme.colors.textMuted} name={favourite ? 'saved' : 'savedOutline'} size={17} />
              </Pressable>
            ) : null}
            <View style={styles.labelStack}>
              <Text numberOfLines={2} style={styles.name}>
                {name}
              </Text>
              {subtitle ? (
                <Text numberOfLines={1} style={styles.subtitle}>
                  {subtitle}
                </Text>
              ) : null}
            </View>
            <Text style={[styles.value, { color: palette.text }]}>
              {formatPercent(value)}
            </Text>
            {badgeLabel ? <Text style={styles.badgeLabel}>{badgeLabel}</Text> : null}
          </Pressable>
        );
      })}
    </View>
  );
}

function getReturnPalette(value: number | null) {
  if (value === null) {
    return {
      background: Theme.colors.cardMuted,
      border: Theme.colors.border,
      text: Theme.colors.textMuted,
    };
  }
  const magnitude = Math.min(Math.abs(value), 8);
  if (value > 0) {
    return {
      background: magnitude >= 4 ? '#052E1A' : Theme.colors.successSoft,
      border: '#166534',
      text: Theme.colors.success,
    };
  }
  if (value < 0) {
    return {
      background: magnitude >= 4 ? '#3F1010' : Theme.colors.dangerSoft,
      border: '#7F1D1D',
      text: Theme.colors.danger,
    };
  }
  return {
    background: Theme.colors.backgroundMuted,
    border: Theme.colors.border,
    text: Theme.colors.textMuted,
  };
}

function formatPercent(value: number | null) {
  if (value === null) {
    return 'N/A';
  }
  const prefix = value > 0 ? '+' : '';
  return `${prefix}${value.toLocaleString('en-US', {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  })}%`;
}

const styles = StyleSheet.create({
  emptyText: {
    color: Theme.colors.textMuted,
    fontSize: Typography.body.fontSize,
    fontWeight: Typography.weights.emphasis,
  },
  badgeLabel: {
    color: Theme.colors.warning,
    fontSize: Typography.chartLabel.fontSize,
    fontWeight: Typography.weights.strong,
  },
  favouriteButton: {
    alignItems: 'center',
    backgroundColor: 'rgba(15, 23, 42, 0.42)',
    borderRadius: Theme.radii.pill,
    height: 24,
    justifyContent: 'center',
    position: 'absolute',
    right: Spacing.one,
    top: Spacing.one,
    width: 24,
    zIndex: 2,
  },
  favouriteText: {
    color: Theme.colors.textMuted,
    fontSize: Typography.bodyLarge.fontSize,
    fontWeight: Typography.weights.strong,
  },
  favouriteTextActive: {
    color: Theme.colors.warning,
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  labelStack: {
    gap: 1,
  },
  name: {
    color: Theme.colors.text,
    fontSize: Typography.control.fontSize,
    fontWeight: Typography.weights.strong,
    lineHeight: 17,
  },
  tile: {
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    flexBasis: '47%',
    justifyContent: 'space-between',
    height: 72,
    padding: Spacing.two,
  },
  subtitle: {
    color: Theme.colors.textMuted,
    fontSize: Typography.chartLabel.fontSize,
    fontWeight: Typography.weights.strong,
    lineHeight: 13,
  },
  value: {
    fontSize: Typography.cardTitle.fontSize,
    fontWeight: Typography.weights.strong,
  },
});
