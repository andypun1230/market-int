import { StyleSheet, Text, View } from 'react-native';

import { ProgressBar } from '@/components/ui/ProgressBar';
import { Spacing, Theme } from '@/constants/theme';
import type { SectorLeader } from '@/types/market';

type SectorRotationBarsProps = {
  sectors: SectorLeader[];
  returnLabel?: string;
  getReturnValue?: (sector: SectorLeader) => number | undefined;
};

export function SectorRotationBars({
  getReturnValue = (sector) => sector.weekly_change_percent,
  returnLabel = '1W Return',
  sectors,
}: SectorRotationBarsProps) {
  if (!sectors.length) {
    return <Text style={styles.emptyText}>No sector data available.</Text>;
  }

  return (
    <View style={styles.list}>
      {sectors.map((sector) => (
        <View key={sector.name} style={styles.card}>
          <View style={styles.header}>
            <Text style={styles.rank}>#{sector.rank}</Text>
            <Text numberOfLines={1} style={styles.name}>
              {sector.name}
            </Text>
            <Text style={[styles.change, getChangeStyle(getReturnValue(sector))]}>
              {formatPercent(getReturnValue(sector))}
            </Text>
          </View>

          <Bar
            label="RS Score"
            tone="success"
            value={formatNumber(sector.relative_strength_score)}
            width={normalizePercent(sector.relative_strength_score, 0, 100)}
          />
          <Bar
            label={returnLabel}
            tone="info"
            value={formatPercent(getReturnValue(sector))}
            width={normalizePercent(getReturnValue(sector), -10, 50)}
          />
          <Bar
            label="Above 50EMA"
            tone="warning"
            value={formatPercent(sector.percent_above_50ema, false)}
            width={normalizePercent(sector.percent_above_50ema, 0, 100)}
          />
        </View>
      ))}
    </View>
  );
}

function Bar({
  label,
  tone,
  value,
  width,
}: {
  label: string;
  tone: 'success' | 'warning' | 'danger' | 'info' | 'muted';
  value: string;
  width: number;
}) {
  return (
    <View style={styles.barRow}>
      <View style={styles.barMeta}>
        <Text style={styles.barLabel}>{label}</Text>
        <Text style={styles.barValue}>{value}</Text>
      </View>
      <ProgressBar showValue={false} tone={tone} value={width} />
    </View>
  );
}

function normalizePercent(value: number | undefined, min: number, max: number) {
  if (value === undefined || value === null || max === min) {
    return 0;
  }

  const clamped = Math.max(min, Math.min(max, value));
  return Math.round(((clamped - min) / (max - min)) * 100);
}

function formatNumber(value?: number) {
  if (value === undefined || value === null) {
    return 'N/A';
  }

  return value.toLocaleString('en-US', {
    maximumFractionDigits: 0,
  });
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

function getChangeStyle(value?: number) {
  if (value === undefined || value === null) {
    return { color: Theme.colors.textMuted };
  }

  return { color: value >= 0 ? Theme.colors.success : Theme.colors.danger };
}

const styles = StyleSheet.create({
  list: {
    gap: Spacing.two,
  },
  card: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    gap: Spacing.twoAndHalf,
    padding: Spacing.two,
  },
  header: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
  },
  rank: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '900',
  },
  name: {
    color: Theme.colors.text,
    flex: 1,
    fontSize: 14,
    fontWeight: '900',
  },
  change: {
    fontSize: 12,
    fontWeight: '900',
  },
  barRow: {
    gap: Spacing.one,
  },
  barMeta: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  barLabel: {
    color: Theme.colors.textMuted,
    fontSize: 10,
    fontWeight: '800',
    textTransform: 'uppercase',
  },
  barValue: {
    color: Theme.colors.text,
    fontSize: 12,
    fontWeight: '900',
  },
  emptyText: {
    color: Theme.colors.textMuted,
    fontSize: 14,
    fontWeight: '700',
  },
});
