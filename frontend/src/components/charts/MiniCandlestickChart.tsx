import { Fragment, useMemo, useState } from 'react';
import { LayoutChangeEvent, StyleSheet, Text, View } from 'react-native';

import { Spacing, Theme } from '@/constants/theme';
import { Candle, PatternKeyLevels, PatternMarker } from '@/types/market';

type MiniCandlestickChartProps = {
  candles: Candle[];
  markers?: PatternMarker[];
  keyLevels?: PatternKeyLevels;
  height?: number;
};

type LevelOverlay = {
  key: string;
  label: string;
  value: number;
  color: string;
};

const MAX_VISIBLE_CANDLES = 30;
const PRICE_LABEL_WIDTH = 62;
const CHART_HORIZONTAL_PADDING = 14;
const CHART_TOP_PADDING = 18;
const CHART_BOTTOM_PADDING = 16;
const VOLUME_HEIGHT = 46;
const VOLUME_GAP = 8;
const BULLISH_COLOR = '#22C55E';
const BEARISH_COLOR = '#EF4444';
const LEVEL_BLUE = '#3B82F6';
const LEVEL_AMBER = '#F59E0B';
const EMA20_COLOR = '#A855F7';
const EMA50_COLOR = '#38BDF8';

export function MiniCandlestickChart({
  candles,
  markers = [],
  keyLevels,
  height = 246,
}: MiniCandlestickChartProps) {
  const [chartWidth, setChartWidth] = useState(0);
  const visibleCandles = useMemo(() => candles.slice(-MAX_VISIBLE_CANDLES), [candles]);
  const visibleStartIndex = Math.max(candles.length - visibleCandles.length, 0);
  const ema20 = useMemo(() => calculateEmaSeries(candles, 20), [candles]);
  const ema50 = useMemo(() => calculateEmaSeries(candles, 50), [candles]);

  if (!visibleCandles.length) {
    return (
      <View style={styles.container}>
        <View style={[styles.chartArea, styles.emptyChart, { height }]}>
          <Text style={styles.emptyText}>No chart data</Text>
        </View>
      </View>
    );
  }

  const priceAreaHeight = Math.max(height - VOLUME_HEIGHT - VOLUME_GAP, 140);
  const plotHeight = Math.max(priceAreaHeight - CHART_TOP_PADDING - CHART_BOTTOM_PADDING, 1);
  const plotWidth = Math.max(
    chartWidth - CHART_HORIZONTAL_PADDING * 2 - PRICE_LABEL_WIDTH,
    1,
  );
  const candleSlotWidth = plotWidth / visibleCandles.length;
  const candleBodyWidth = Math.max(6, Math.min(13, candleSlotWidth * 0.72));
  const volumeTop = priceAreaHeight + VOLUME_GAP;
  const rawMinPrice = Math.min(...visibleCandles.map((candle) => candle.low));
  const rawMaxPrice = Math.max(...visibleCandles.map((candle) => candle.high));
  const rawRange = rawMaxPrice - rawMinPrice || 1;
  const minPrice = rawMinPrice - rawRange * 0.08;
  const maxPrice = rawMaxPrice + rawRange * 0.08;
  const midPrice = (maxPrice + minPrice) / 2;
  const priceRange = maxPrice - minPrice || 1;
  const maxVolume = Math.max(...visibleCandles.map((candle) => candle.volume), 1);
  const levelOverlays = buildLevelOverlays(keyLevels).filter(
    (level) => level.value >= rawMinPrice && level.value <= rawMaxPrice,
  );

  function handleLayout(event: LayoutChangeEvent) {
    setChartWidth(event.nativeEvent.layout.width);
  }

  function getX(index: number) {
    return CHART_HORIZONTAL_PADDING + index * candleSlotWidth + candleSlotWidth / 2;
  }

  function getPriceY(price: number) {
    const normalized = (maxPrice - price) / priceRange;
    return CHART_TOP_PADDING + normalized * plotHeight;
  }

  function getMarkerPosition(marker: PatternMarker) {
    const candleIndex = visibleCandles.findIndex((candle) => candle.date === marker.date);

    if (candleIndex === -1 || marker.price < minPrice || marker.price > maxPrice) {
      return null;
    }

    return {
      left: Math.max(2, Math.min(chartWidth - PRICE_LABEL_WIDTH - 52, getX(candleIndex) - 22)),
      top: Math.max(4, Math.min(priceAreaHeight - 24, getPriceY(marker.price) - 24)),
    };
  }

  return (
    <View style={styles.container}>
      <View onLayout={handleLayout} style={[styles.chartArea, { height }]}>
        {[0.2, 0.4, 0.6, 0.8].map((position) => (
          <View
            key={position}
            style={[
              styles.gridLine,
              {
                left: CHART_HORIZONTAL_PADDING,
                right: PRICE_LABEL_WIDTH,
                top: CHART_TOP_PADDING + plotHeight * position,
              },
            ]}
          />
        ))}

        <Text style={[styles.priceLabel, { top: CHART_TOP_PADDING - 5 }]}>
          {formatPrice(maxPrice)}
        </Text>
        <Text style={[styles.priceLabel, { top: getPriceY(midPrice) - 8 }]}>
          {formatPrice(midPrice)}
        </Text>
        <Text style={[styles.priceLabel, { top: priceAreaHeight - CHART_BOTTOM_PADDING - 10 }]}>
          {formatPrice(minPrice)}
        </Text>

        <View
          style={[
            styles.volumeDivider,
            {
              left: CHART_HORIZONTAL_PADDING,
              right: PRICE_LABEL_WIDTH,
              top: volumeTop - 5,
            },
          ]}
        />

        <Text style={[styles.legendText, { color: EMA20_COLOR, left: CHART_HORIZONTAL_PADDING }]}>
          EMA20
        </Text>
        <Text style={[styles.legendText, { color: EMA50_COLOR, left: CHART_HORIZONTAL_PADDING + 50 }]}>
          EMA50
        </Text>

        {chartWidth > 0
          ? levelOverlays.map((level) => {
              const y = getPriceY(level.value);

              return (
                <Fragment key={level.key}>
                  <View
                    style={[
                      styles.levelLine,
                      {
                        backgroundColor: level.color,
                        left: CHART_HORIZONTAL_PADDING,
                        right: PRICE_LABEL_WIDTH,
                        top: y,
                      },
                    ]}
                  />
                  <View
                    style={[
                      styles.levelTag,
                      {
                        borderColor: level.color,
                        top: Math.max(4, Math.min(priceAreaHeight - 24, y - 10)),
                      },
                    ]}
                  >
                    <Text style={[styles.levelTagText, { color: level.color }]}>
                      {level.label} {formatPrice(level.value)}
                    </Text>
                  </View>
                </Fragment>
              );
            })
          : null}

        {chartWidth > 0
          ? visibleCandles.map((candle, index) => {
              const isBullish = candle.close >= candle.open;
              const candleColor = isBullish ? BULLISH_COLOR : BEARISH_COLOR;
              const highY = getPriceY(candle.high);
              const lowY = getPriceY(candle.low);
              const openY = getPriceY(candle.open);
              const closeY = getPriceY(candle.close);
              const bodyTop = Math.min(openY, closeY);
              const bodyHeight = Math.max(Math.abs(openY - closeY), 4);
              const centerX = getX(index);
              const volumeHeight = Math.max((candle.volume / maxVolume) * (VOLUME_HEIGHT - 8), 3);

              return (
                <Fragment key={candle.date}>
                  <View
                    style={[
                      styles.wick,
                      {
                        backgroundColor: candleColor,
                        height: Math.max(lowY - highY, 1),
                        left: centerX - 1,
                        top: highY,
                      },
                    ]}
                  />
                  <View
                    style={[
                      styles.body,
                      {
                        backgroundColor: candleColor,
                        height: bodyHeight,
                        left: centerX - candleBodyWidth / 2,
                        top: bodyTop,
                        width: candleBodyWidth,
                      },
                    ]}
                  />
                  <View
                    style={[
                      styles.volumeBar,
                      {
                        backgroundColor: candleColor,
                        height: volumeHeight,
                        left: centerX - candleBodyWidth / 2,
                        top: volumeTop + VOLUME_HEIGHT - volumeHeight,
                        width: candleBodyWidth,
                      },
                    ]}
                  />
                </Fragment>
              );
            })
          : null}

        {chartWidth > 0
          ? ema20.slice(visibleStartIndex).map((value, index) => {
              if (value === null || value < minPrice || value > maxPrice) {
                return null;
              }

              return (
                <View
                  key={`ema20-${visibleCandles[index]?.date ?? index}`}
                  style={[
                    styles.emaDot,
                    {
                      backgroundColor: EMA20_COLOR,
                      left: getX(index) - 2,
                      top: getPriceY(value) - 2,
                    },
                  ]}
                />
              );
            })
          : null}

        {chartWidth > 0
          ? ema50.slice(visibleStartIndex).map((value, index) => {
              if (value === null || value < minPrice || value > maxPrice) {
                return null;
              }

              return (
                <View
                  key={`ema50-${visibleCandles[index]?.date ?? index}`}
                  style={[
                    styles.emaDot,
                    styles.ema50Dot,
                    {
                      backgroundColor: EMA50_COLOR,
                      left: getX(index) - 2,
                      top: getPriceY(value) - 2,
                    },
                  ]}
                />
              );
            })
          : null}

        {chartWidth > 0
          ? markers.map((marker) => {
              const position = getMarkerPosition(marker);

              if (!position) {
                return null;
              }

              return (
                <View key={`${marker.date}-${marker.label}-chart`} style={[styles.chartMarker, position]}>
                  <Text style={styles.chartMarkerText}>{marker.label}</Text>
                </View>
              );
            })
          : null}
      </View>

      {markers.length ? (
        <View style={styles.markerList}>
          {markers.map((marker) => (
            <View key={`${marker.date}-${marker.label}`} style={styles.markerChip}>
              <Text style={styles.markerText}>
                {marker.label} · {formatShortDate(marker.date)} · {formatPrice(marker.price)}
              </Text>
            </View>
          ))}
        </View>
      ) : null}
    </View>
  );
}

function buildLevelOverlays(keyLevels?: PatternKeyLevels): LevelOverlay[] {
  if (!keyLevels) {
    return [];
  }

  return [
    {
      key: 'support',
      label: 'Support',
      value: keyLevels.support,
      color: BULLISH_COLOR,
    },
    {
      key: 'neckline',
      label: 'Neckline',
      value: keyLevels.neckline,
      color: LEVEL_AMBER,
    },
    {
      key: 'breakout',
      label: 'Breakout',
      value: keyLevels.breakout,
      color: LEVEL_BLUE,
    },
    {
      key: 'stop_reference',
      label: 'Stop',
      value: keyLevels.stop_reference,
      color: BEARISH_COLOR,
    },
  ].filter((level): level is LevelOverlay => typeof level.value === 'number');
}

function calculateEmaSeries(candles: Candle[], period: number) {
  const closes = candles.map((candle) => candle.close);
  const smoothing = 2 / (period + 1);
  const series: (number | null)[] = closes.map(() => null);

  if (closes.length < period) {
    return series;
  }

  let ema = closes.slice(0, period).reduce((total, close) => total + close, 0) / period;
  series[period - 1] = ema;

  for (let index = period; index < closes.length; index += 1) {
    ema = closes[index] * smoothing + ema * (1 - smoothing);
    series[index] = ema;
  }

  return series;
}

function formatPrice(value: number) {
  if (!Number.isFinite(value)) {
    return 'N/A';
  }

  return value.toLocaleString('en-US', {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  });
}

function formatShortDate(value: string) {
  const [, month, day] = value.split('-');
  return month && day ? `${month}/${day}` : value;
}

const styles = StyleSheet.create({
  container: {
    gap: Spacing.two,
  },
  chartArea: {
    backgroundColor: '#0B1220',
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    overflow: 'hidden',
    position: 'relative',
  },
  gridLine: {
    backgroundColor: Theme.colors.border,
    height: 1,
    opacity: 0.28,
    position: 'absolute',
  },
  priceLabel: {
    color: Theme.colors.textMuted,
    fontSize: 10,
    fontWeight: '800',
    position: 'absolute',
    right: Spacing.two,
  },
  volumeDivider: {
    backgroundColor: Theme.colors.border,
    height: 1,
    opacity: 0.45,
    position: 'absolute',
  },
  legendText: {
    fontSize: 10,
    fontWeight: '900',
    position: 'absolute',
    top: Spacing.two,
  },
  levelLine: {
    height: 1,
    opacity: 0.9,
    position: 'absolute',
  },
  levelTag: {
    backgroundColor: '#0F172A',
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    paddingHorizontal: Spacing.one,
    paddingVertical: 2,
    position: 'absolute',
    right: Spacing.one,
  },
  levelTagText: {
    fontSize: 9,
    fontWeight: '900',
  },
  wick: {
    borderRadius: 1,
    opacity: 0.95,
    position: 'absolute',
    width: 2,
  },
  body: {
    borderRadius: 2,
    position: 'absolute',
  },
  volumeBar: {
    borderRadius: 2,
    opacity: 0.45,
    position: 'absolute',
  },
  emaDot: {
    borderRadius: 999,
    height: 4,
    opacity: 0.95,
    position: 'absolute',
    width: 4,
  },
  ema50Dot: {
    opacity: 0.85,
  },
  chartMarker: {
    backgroundColor: '#172033',
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    paddingHorizontal: Spacing.one,
    paddingVertical: 2,
    position: 'absolute',
  },
  chartMarkerText: {
    color: Theme.colors.text,
    fontSize: 9,
    fontWeight: '900',
  },
  markerList: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.one,
  },
  markerChip: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    paddingHorizontal: Spacing.two,
    paddingVertical: Spacing.one,
  },
  markerText: {
    color: Theme.colors.text,
    fontSize: 11,
    fontWeight: '800',
  },
  emptyChart: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  emptyText: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '700',
  },
});
