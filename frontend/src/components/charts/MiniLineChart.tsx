import { StyleSheet, Text, View } from 'react-native';

import { Spacing, Theme, Typography } from '@/constants/theme';
import { Candle, PatternMarker } from '@/types/market';

type MiniLineChartProps = {
  chartData: Candle[];
  markers?: PatternMarker[];
};

export function MiniLineChart({ chartData, markers = [] }: MiniLineChartProps) {
  if (!chartData.length) {
    return (
      <View style={styles.container}>
        <View style={[styles.chartArea, styles.emptyChart]}>
          <Text style={styles.emptyText}>No chart data available</Text>
        </View>
      </View>
    );
  }

  const closes = chartData.map((candle) => candle.close);
  const minClose = Math.min(...closes);
  const maxClose = Math.max(...closes);
  const range = maxClose - minClose || 1;
  const visibleCandles = chartData.slice(-36);

  return (
    <View style={styles.container}>
      <View style={styles.chartArea}>
        {visibleCandles.map((candle) => {
          const normalizedHeight = ((candle.close - minClose) / range) * 46 + 8;
          const isUp = candle.close >= candle.open;

          return (
            <View key={candle.date} style={styles.barSlot}>
              <View
                style={[
                  styles.bar,
                  {
                    height: normalizedHeight,
                    backgroundColor: isUp ? Theme.colors.success : Theme.colors.danger,
                  },
                ]}
              />
            </View>
          );
        })}
      </View>

      {markers.length ? (
        <View style={styles.markerList}>
          {markers.map((marker) => (
            <Text key={`${marker.date}-${marker.label}`} style={styles.markerText}>
              {marker.label}: {formatPrice(marker.price)}
            </Text>
          ))}
        </View>
      ) : null}
    </View>
  );
}

function formatPrice(value: number) {
  return value.toLocaleString('en-US', {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  });
}

const styles = StyleSheet.create({
  container: {
    gap: Spacing.two,
  },
  chartArea: {
    alignItems: 'flex-end',
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    flexDirection: 'row',
    gap: 2,
    height: 76,
    padding: Spacing.two,
  },
  barSlot: {
    alignItems: 'center',
    flex: 1,
    justifyContent: 'flex-end',
  },
  bar: {
    borderRadius: 3,
    minHeight: 4,
    width: '100%',
  },
  markerList: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  markerText: {
    color: Theme.colors.textMuted,
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.emphasis,
  },
  emptyChart: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  emptyText: {
    color: Theme.colors.textMuted,
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.emphasis,
  },
});
