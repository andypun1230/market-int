import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Spacing, Theme, Typography } from '@/constants/theme';
import type { SectorLeader } from '@/types/market';

type SectorHeatmapProps = {
  sectors: SectorLeader[];
  returnLabel?: string;
  getReturnValue?: (sector: SectorLeader) => number | undefined;
  onSectorPress?: (sector: SectorLeader) => void;
};

export function SectorHeatmap({
  getReturnValue = (sector) => sector.weekly_change_percent,
  onSectorPress,
  returnLabel = '1W',
  sectors,
}: SectorHeatmapProps) {
  if (!sectors.length) {
    return <Text style={styles.emptyText}>No sector data available.</Text>;
  }

  return (
    <View style={styles.grid}>
      {sectors.map((sector) => {
        const palette = getTilePalette(sector);

        return (
          <Pressable
            accessibilityLabel={onSectorPress ? `Open ${sector.name} sector details, ${returnLabel} ${formatPercent(getReturnValue(sector))}` : `${sector.name}, ${returnLabel} ${formatPercent(getReturnValue(sector))}`}
            accessibilityRole={onSectorPress ? 'button' : undefined}
            disabled={!onSectorPress}
            key={sector.name}
            onPress={() => onSectorPress?.(sector)}
            style={[
              styles.tile,
              {
                backgroundColor: palette.background,
                borderColor: palette.border,
              },
            ]}>
            <Text numberOfLines={2} style={styles.sectorName}>
              {sector.name}
            </Text>

            <View style={styles.tileFooter}>
              <Text style={[styles.returnValue, { color: palette.text }]}>
                {formatPercent(getReturnValue(sector))}
              </Text>
              <Text numberOfLines={1} style={[styles.statusText, { color: palette.text }]}>
                {sector.status || `#${sector.rank}`}
              </Text>
            </View>
          </Pressable>
        );
      })}
    </View>
  );
}

function getTilePalette(sector: SectorLeader) {
  const status = sector.status.toLowerCase();
  const weekly = sector.weekly_change_percent ?? 0;

  if (status === 'leading' || status === 'strong' || weekly >= 2) {
    return {
      background: Theme.colors.successSoft,
      badge: Theme.colors.success,
      border: '#166534',
      text: Theme.colors.success,
    };
  }

  if (status === 'weak' || weekly < 0) {
    return {
      background: weekly < -1 ? Theme.colors.dangerSoft : Theme.colors.warningSoft,
      badge: weekly < -1 ? Theme.colors.danger : Theme.colors.warning,
      border: weekly < -1 ? '#7F1D1D' : '#92400E',
      text: weekly < -1 ? Theme.colors.danger : Theme.colors.warning,
    };
  }

  return {
    background: Theme.colors.cardMuted,
    badge: Theme.colors.accent,
    border: Theme.colors.border,
    text: Theme.colors.accent,
  };
}

function formatPercent(value?: number, signed = true) {
  if (value === undefined || value === null) {
    return 'N/A';
  }

  const prefix = signed && value > 0 ? '+' : '';
  return `${prefix}${value.toLocaleString('en-US', {
    maximumFractionDigits: 1,
    minimumFractionDigits: 1,
  })}%`;
}

const styles = StyleSheet.create({
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  tile: {
    flexBasis: '47%',
    flexGrow: 1,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    height: 104,
    justifyContent: 'space-between',
    padding: Spacing.two,
  },
  statusText: {
    flexShrink: 1,
    fontSize: Typography.chartLabel.fontSize,
    fontWeight: Typography.weights.strong,
    textTransform: 'uppercase',
    maxWidth: '58%',
  },
  sectorName: {
    color: Theme.colors.text,
    fontSize: Typography.bodyLarge.fontSize,
    fontWeight: Typography.weights.strong,
    lineHeight: 19,
  },
  tileFooter: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.one,
    justifyContent: 'space-between',
  },
  returnValue: {
    fontSize: Typography.supportTitle.fontSize,
    fontWeight: Typography.weights.strong,
  },
  emptyText: {
    color: Theme.colors.textMuted,
    fontSize: Typography.body.fontSize,
    fontWeight: Typography.weights.emphasis,
  },
});
