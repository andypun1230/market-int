import { useEffect, useMemo, useState } from 'react';
import type { GestureResponderEvent } from 'react-native';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Spacing, Theme, Typography } from '@/constants/theme';
import {
  buildStockMiniChartModel,
  formatCurrency,
  formatPercent,
  formatVolume,
  getChartDirection,
  getPaddedPriceDomain,
  getProvenanceLabel,
  getXAxisLabels,
  getYAxisLabels,
  stockMiniChartRangeDays,
  stockMiniChartRanges,
  type StockMiniChartModel,
  type StockMiniChartPoint,
  type StockMiniChartQuoteInput,
  type StockMiniChartRange,
} from '@/features/stock-detail/stockMiniChartModel';
import { getLiveHistory } from '@/services/api';
import type { HistoryData } from '@/types/market';

const CHART_HEIGHT = 158;
const PRICE_AREA_HEIGHT = 122;
const VOLUME_AREA_HEIGHT = 28;
const CHART_HORIZONTAL_PADDING = 28;
const CHART_TOP_PADDING = 14;
const CHART_BOTTOM_PADDING = 18;
const PRICE_LABEL_WIDTH = 58;

type ChartPoint = StockMiniChartPoint & {
  index: number;
  x: number;
  y: number;
};

export function StockMiniChart({
  allowNetworkFallback = false,
  history,
  quote,
  symbol,
}: {
  allowNetworkFallback?: boolean;
  history?: HistoryData | null;
  quote?: StockMiniChartQuoteInput | null;
  symbol: string;
}) {
  const [selectedRange, setSelectedRange] = useState<StockMiniChartRange>('1M');
  const [visibleRange, setVisibleRange] = useState<StockMiniChartRange>('1M');
  const [historyByRange, setHistoryByRange] = useState<Partial<Record<StockMiniChartRange, HistoryData>>>({});
  const [loadingRange, setLoadingRange] = useState<StockMiniChartRange | null>('1M');
  const [errorByRange, setErrorByRange] = useState<Partial<Record<StockMiniChartRange, string>>>({});
  const snapshotHistoryByRange = useMemo(() => history ? buildHistoryByRange(history) : {}, [history]);
  const effectiveHistoryByRange = history ? snapshotHistoryByRange : historyByRange;

  useEffect(() => {
    let cancelled = false;
    if (history) {
      return undefined;
    }
    if (!allowNetworkFallback || historyByRange[selectedRange]) {
      return undefined;
    }

    getLiveHistory(symbol, 'D', stockMiniChartRangeDays[selectedRange])
      .then((history) => {
        if (!cancelled) {
          setHistoryByRange((current) => ({ ...current, [selectedRange]: history }));
          setVisibleRange(selectedRange);
          setErrorByRange((current) => ({ ...current, [selectedRange]: undefined }));
        }
      })
      .catch((requestError: unknown) => {
        if (!cancelled) {
          const message = requestError instanceof Error ? requestError.message : 'Chart history unavailable.';
          setErrorByRange((current) => ({ ...current, [selectedRange]: message }));
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoadingRange(null);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [allowNetworkFallback, history, historyByRange, selectedRange, symbol]);

  const displayRange = history ? selectedRange : effectiveHistoryByRange[selectedRange] ? selectedRange : visibleRange;
  const model = useMemo(
    () => buildStockMiniChartModel({
      history: effectiveHistoryByRange[displayRange],
      quote,
      range: displayRange,
      symbol,
    }),
    [displayRange, effectiveHistoryByRange, quote, symbol],
  );
  const requestedLabel = !history && allowNetworkFallback && loadingRange === selectedRange && selectedRange !== displayRange
    ? `Loading ${selectedRange}...`
    : null;
  const isBackgroundLoading = Boolean(requestedLabel);
  const selectedError = errorByRange[selectedRange];

  return (
    <View style={styles.container}>
      <ChartSummary model={model} requestedLabel={requestedLabel} />
      <PriceChart
        error={selectedError ?? null}
        loading={!history && allowNetworkFallback && !effectiveHistoryByRange[displayRange] && loadingRange === selectedRange}
        model={model}
        muted={isBackgroundLoading}
      />
      <View accessibilityLabel={`Chart range selector for ${symbol}`} style={styles.rangeRow}>
        {stockMiniChartRanges.map((range) => (
          <Pressable
            accessibilityLabel={`Show ${symbol} ${range} history`}
            accessibilityRole="button"
            key={range}
            onPress={() => {
              setSelectedRange(range);
              if (effectiveHistoryByRange[range]) {
                setVisibleRange(range);
                setLoadingRange(null);
                return;
              }
              setLoadingRange(allowNetworkFallback ? range : null);
            }}
            style={[styles.rangeButton, selectedRange === range && styles.rangeButtonSelected]}>
            <Text style={[styles.rangeText, selectedRange === range && styles.rangeTextSelected]}>{range}</Text>
          </Pressable>
        ))}
      </View>
    </View>
  );
}

function buildHistoryByRange(history: HistoryData): Partial<Record<StockMiniChartRange, HistoryData>> {
  return stockMiniChartRanges.reduce<Partial<Record<StockMiniChartRange, HistoryData>>>((accumulator, range) => {
    const candles = history.candles.slice(-stockMiniChartRangeDays[range]);
    accumulator[range] = {
      ...history,
      candles,
      requested_days: stockMiniChartRangeDays[range],
      returned_candles: candles.length,
    };
    return accumulator;
  }, {});
}

function ChartSummary({
  model,
  requestedLabel,
}: {
  model: StockMiniChartModel;
  requestedLabel: string | null;
}) {
  const direction = getChartDirection(model.stats.changePercent);
  const tone = getDirectionColor(direction);
  return (
    <View style={styles.summaryBlock}>
      <View style={styles.summaryTopRow}>
        <View style={styles.summaryTitleBlock}>
          <Text style={styles.chartTitle}>Price History</Text>
          <Text style={styles.chartSubtitle}>
            {requestedLabel ?? `${model.range} · ${getProvenanceLabel(model.provenance.dataStatus, model.provenance.provider)}`}
          </Text>
        </View>
        <View accessibilityLabel={`Period performance ${formatPercent(model.stats.changePercent)}`} style={styles.performanceBlock}>
          <Text style={[styles.periodChange, { color: tone }]}>{formatPercent(model.stats.changePercent)}</Text>
          <Text style={styles.directionText}>{directionLabel(direction)}</Text>
        </View>
      </View>
      <View style={styles.statsRow}>
        <Stat label="Range" value={`${formatCurrency(model.stats.startPrice)} → ${formatCurrency(model.stats.endPrice)}`} />
        <Stat label="High" value={formatCurrency(model.stats.high)} />
        <Stat label="Low" value={formatCurrency(model.stats.low)} />
      </View>
      {model.provenance.warning ? (
        <Text accessibilityRole="text" style={styles.warningText}>{model.provenance.warning}</Text>
      ) : null}
    </View>
  );
}

function PriceChart({
  error,
  loading,
  model,
  muted,
}: {
  error: string | null;
  loading: boolean;
  model: StockMiniChartModel;
  muted: boolean;
}) {
  const [chartWidth, setChartWidth] = useState(0);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const direction = getChartDirection(model.stats.changePercent);
  const tone = getDirectionColor(direction);
  const domain = getPaddedPriceDomain(model.stats.low, model.stats.high);
  const yAxisLabels = getYAxisLabels(model.stats.low, model.stats.high);
  const xAxisLabels = getXAxisLabels(model.points, model.range);
  const chartPoints = useMemo(
    () => mapPoints(model.points, chartWidth, domain.min, domain.max),
    [chartWidth, domain.max, domain.min, model.points],
  );
  const startBaseline = model.stats.startPrice == null ? null : getPriceY(model.stats.startPrice, domain.min, domain.max);
  const selectedPoint = selectedIndex == null ? null : chartPoints[selectedIndex] ?? null;
  const hasVolume = model.points.some((point) => typeof point.volume === 'number' && point.volume > 0);

  if (loading) {
    return (
      <View style={[styles.chartBox, styles.emptyChart, { height: CHART_HEIGHT }]}>
        <Text style={styles.emptyText}>Loading chart...</Text>
      </View>
    );
  }

  if (error && model.points.length < 2) {
    return (
      <View style={[styles.chartBox, styles.emptyChart, { height: CHART_HEIGHT }]}>
        <Text numberOfLines={2} style={styles.emptyText}>Chart unavailable.</Text>
        <Text numberOfLines={2} style={styles.emptySubtext}>{error}</Text>
      </View>
    );
  }

  if (model.points.length < 2) {
    return (
      <View style={[styles.chartBox, styles.emptyChart, { height: CHART_HEIGHT }]}>
        <Text style={styles.emptyText}>Not enough history for this range.</Text>
      </View>
    );
  }

  function handlePress(event: GestureResponderEvent) {
    if (!chartPoints.length) {
      return;
    }
    const x = event.nativeEvent.locationX;
    const nearest = chartPoints.reduce((best, point) => (
      Math.abs(point.x - x) < Math.abs(best.x - x) ? point : best
    ), chartPoints[0]);
    setSelectedIndex(nearest.index);
  }

  return (
    <Pressable
      accessibilityLabel={buildAccessibleSummary(model)}
      accessibilityRole="summary"
      onMoveShouldSetResponder={() => true}
      onLayout={(event) => setChartWidth(event.nativeEvent.layout.width)}
      onPressIn={handlePress}
      onPressOut={() => setSelectedIndex(null)}
      onResponderMove={handlePress}
      style={[styles.chartBox, muted && styles.chartBoxMuted, { height: CHART_HEIGHT }]}>
      {yAxisLabels.map((value) => (
        <View key={value} style={[styles.gridLine, { top: getPriceY(value, domain.min, domain.max) }]}>
          <Text style={styles.yAxisLabel}>{formatCurrency(value)}</Text>
        </View>
      ))}

      {startBaseline != null ? (
        <View style={[styles.baseline, { top: startBaseline }]}>
          <View style={styles.baselineDashRow}>
            {Array.from({ length: 18 }).map((_, index) => (
              <View key={index} style={styles.baselineDash} />
            ))}
          </View>
          <Text style={styles.baselineLabel}>Start {formatCurrency(model.stats.startPrice)}</Text>
        </View>
      ) : null}

      {chartPoints.map((point, index) => {
        if (index === 0) {
          return null;
        }
        return (
          <LineSegment
            color={tone}
            end={point}
            key={`${point.timestamp}-${index}`}
            start={chartPoints[index - 1]}
          />
        );
      })}

      {chartPoints.map((point, index) => {
        if (index % Math.max(1, Math.floor(chartPoints.length / 26)) !== 0 && index !== chartPoints.length - 1) {
          return null;
        }
        return (
          <View
            key={`area-${point.timestamp}`}
            style={[
              styles.areaStem,
              {
                backgroundColor: tone,
                height: Math.max(0, PRICE_AREA_HEIGHT - point.y),
                left: point.x,
                opacity: 0.08,
                top: point.y,
              },
            ]}
          />
        );
      })}

      {chartPoints[0] ? <PointMarker color={tone} point={chartPoints[0]} small /> : null}
      {chartPoints.at(-1) ? <PointMarker color={tone} point={chartPoints.at(-1) as ChartPoint} /> : null}
      {selectedPoint ? (
        <>
          <View style={[styles.crosshair, { left: selectedPoint.x }]} />
          <PointMarker color={Theme.colors.text} point={selectedPoint} />
          <ChartTooltip model={model} point={selectedPoint} width={chartWidth} />
        </>
      ) : null}

      {hasVolume ? <VolumeStrip points={model.points} width={chartWidth} /> : null}

      {xAxisLabels.map(({ index, label }) => {
        const point = chartPoints[index];
        if (!point) {
          return null;
        }
        return (
          <Text key={`${index}-${label}`} style={[styles.xAxisLabel, { left: clamp(point.x - 18, 2, Math.max(2, chartWidth - 42)) }]}>
            {label}
          </Text>
        );
      })}
    </Pressable>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.statItem}>
      <Text style={styles.statLabel}>{label}</Text>
      <Text numberOfLines={1} style={styles.statValue}>{value}</Text>
    </View>
  );
}

function LineSegment({ color, end, start }: { color: string; end: ChartPoint; start: ChartPoint }) {
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  const length = Math.sqrt(dx * dx + dy * dy);
  const angle = Math.atan2(dy, dx);
  const midX = (start.x + end.x) / 2;
  const midY = (start.y + end.y) / 2;
  return (
    <View
      style={[
        styles.lineSegment,
        {
          backgroundColor: color,
          left: midX - length / 2,
          top: midY - 1.5,
          transform: [{ rotateZ: `${angle}rad` }],
          width: length,
        },
      ]}
    />
  );
}

function PointMarker({ color, point, small = false }: { color: string; point: ChartPoint; small?: boolean }) {
  const size = small ? 7 : 11;
  return (
    <View
      style={[
        styles.pointMarker,
        {
          borderColor: color,
          height: size,
          left: point.x - size / 2,
          top: point.y - size / 2,
          width: size,
        },
      ]}
    />
  );
}

function VolumeStrip({ points, width }: { points: StockMiniChartPoint[]; width: number }) {
  if (!width) {
    return null;
  }
  const maxVolume = Math.max(...points.map((point) => point.volume ?? 0), 1);
  const plotWidth = Math.max(1, width - CHART_HORIZONTAL_PADDING * 2 - PRICE_LABEL_WIDTH);
  const slotWidth = plotWidth / points.length;
  return (
    <View accessibilityLabel="Volume bars from selected history" style={styles.volumeStrip}>
      {points.map((point, index) => {
        const volume = point.volume ?? 0;
        if (volume <= 0) {
          return null;
        }
        return (
          <View
            key={`volume-${point.timestamp}`}
            style={[
              styles.volumeBar,
              {
                height: Math.max(2, (volume / maxVolume) * VOLUME_AREA_HEIGHT),
                left: CHART_HORIZONTAL_PADDING + index * slotWidth,
                width: Math.max(1, slotWidth * 0.62),
              },
            ]}
          />
        );
      })}
    </View>
  );
}

function ChartTooltip({ model, point, width }: { model: StockMiniChartModel; point: ChartPoint; width: number }) {
  const tooltipWidth = 174;
  const left = clamp(point.x - tooltipWidth / 2, 8, Math.max(8, width - tooltipWidth - 8));
  const change = model.stats.startPrice == null ? null : point.close - model.stats.startPrice;
  const changePercent = model.stats.startPrice && model.stats.startPrice > 0 ? (change ?? 0) / model.stats.startPrice * 100 : null;
  return (
    <View style={[styles.tooltip, { left, top: clamp(point.y - 84, 8, PRICE_AREA_HEIGHT - 72), width: tooltipWidth }]}>
      <Text style={styles.tooltipTitle}>{formatTooltipDate(point.timestamp)}</Text>
      <Text style={styles.tooltipText}>Close {formatCurrency(point.close)}</Text>
      <Text style={styles.tooltipText}>{formatCurrency(change)} · {formatPercent(changePercent)} from start</Text>
      {point.volume != null ? <Text style={styles.tooltipText}>Volume {formatVolume(point.volume)}</Text> : null}
    </View>
  );
}

function mapPoints(points: StockMiniChartPoint[], width: number, min: number, max: number): ChartPoint[] {
  if (width <= 0 || points.length < 2) {
    return [];
  }
  const plotWidth = Math.max(1, width - CHART_HORIZONTAL_PADDING * 2 - PRICE_LABEL_WIDTH);
  return points.map((point, index) => ({
    ...point,
    index,
    x: CHART_HORIZONTAL_PADDING + (index / Math.max(points.length - 1, 1)) * plotWidth,
    y: getPriceY(point.close, min, max),
  }));
}

function getPriceY(price: number, min: number, max: number) {
  const plotHeight = PRICE_AREA_HEIGHT - CHART_TOP_PADDING - CHART_BOTTOM_PADDING;
  const range = Math.max(max - min, 0.01);
  return CHART_TOP_PADDING + ((max - price) / range) * plotHeight;
}

function getDirectionColor(direction: ReturnType<typeof getChartDirection>) {
  if (direction === 'positive') {
    return Theme.colors.success;
  }
  if (direction === 'negative') {
    return Theme.colors.danger;
  }
  return Theme.colors.accent;
}

function directionLabel(direction: ReturnType<typeof getChartDirection>) {
  if (direction === 'positive') {
    return 'Period gain';
  }
  if (direction === 'negative') {
    return 'Period loss';
  }
  return 'Flat period';
}

function buildAccessibleSummary(model: StockMiniChartModel) {
  return `${model.symbol} ${model.range} price history. Period change ${formatPercent(model.stats.changePercent)} from ${formatCurrency(model.stats.startPrice)} to ${formatCurrency(model.stats.endPrice)}. High ${formatCurrency(model.stats.high)}. Low ${formatCurrency(model.stats.low)}. ${getProvenanceLabel(model.provenance.dataStatus, model.provenance.provider)}.`;
}

function formatTooltipDate(timestamp: string) {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return timestamp;
  }
  return date.toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' });
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

const styles = StyleSheet.create({
  areaStem: {
    borderRadius: 2,
    position: 'absolute',
    width: 2,
  },
  baseline: {
    left: CHART_HORIZONTAL_PADDING,
    position: 'absolute',
    right: PRICE_LABEL_WIDTH,
  },
  baselineDash: {
    backgroundColor: 'rgba(248, 250, 252, 0.32)',
    height: 1,
    width: 8,
  },
  baselineDashRow: {
    flexDirection: 'row',
    gap: 5,
    overflow: 'hidden',
  },
  baselineLabel: {
    backgroundColor: 'rgba(15, 23, 42, 0.78)',
    borderRadius: Theme.radii.small,
    color: Theme.colors.textMuted,
    fontSize: Typography.chartAxis.fontSize,
    fontWeight: Typography.weights.strong,
    paddingHorizontal: Spacing.one,
    paddingVertical: Spacing.half,
    position: 'absolute',
    right: 0,
    top: -12,
  },
  chartBox: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    overflow: 'hidden',
  },
  chartBoxMuted: {
    opacity: 0.62,
  },
  chartSubtitle: {
    color: Theme.colors.textMuted,
    fontSize: Typography.caption.fontSize,
    fontWeight: Typography.weights.strong,
  },
  chartTitle: {
    color: Theme.colors.text,
    fontSize: Typography.control.fontSize,
    fontWeight: Typography.weights.strong,
  },
  container: {
    gap: Spacing.two,
  },
  crosshair: {
    backgroundColor: 'rgba(248, 250, 252, 0.22)',
    bottom: VOLUME_AREA_HEIGHT,
    position: 'absolute',
    top: 0,
    width: 1,
  },
  directionText: {
    color: Theme.colors.textMuted,
    fontSize: Typography.chartLabel.fontSize,
    fontWeight: Typography.weights.strong,
  },
  emptyChart: {
    alignItems: 'center',
    gap: Spacing.one,
    justifyContent: 'center',
    paddingHorizontal: Spacing.two,
  },
  emptySubtext: {
    color: Theme.colors.textMuted,
    fontSize: Typography.chartLabel.fontSize,
    fontWeight: Typography.weights.emphasis,
    textAlign: 'center',
  },
  emptyText: {
    color: Theme.colors.textMuted,
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.strong,
    textAlign: 'center',
  },
  gridLine: {
    backgroundColor: 'rgba(148, 163, 184, 0.12)',
    height: 1,
    left: 0,
    position: 'absolute',
    right: 0,
  },
  lineSegment: {
    borderRadius: Theme.radii.pill,
    height: 3,
    position: 'absolute',
  },
  performanceBlock: {
    alignItems: 'flex-end',
  },
  periodChange: {
    fontSize: Typography.cardTitle.fontSize,
    fontWeight: Typography.weights.strong,
  },
  pointMarker: {
    backgroundColor: Theme.colors.background,
    borderRadius: Theme.radii.pill,
    borderWidth: 3,
    position: 'absolute',
  },
  rangeButton: {
    alignItems: 'center',
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    flex: 1,
    justifyContent: 'center',
    minHeight: 30,
  },
  rangeButtonSelected: {
    backgroundColor: Theme.colors.accentSoft,
    borderColor: Theme.colors.accent,
  },
  rangeRow: {
    flexDirection: 'row',
    gap: Spacing.one,
  },
  rangeText: {
    color: Theme.colors.textMuted,
    fontSize: Typography.chartLabel.fontSize,
    fontWeight: Typography.weights.strong,
  },
  rangeTextSelected: {
    color: Theme.colors.accent,
  },
  statItem: {
    flexGrow: 1,
    minWidth: '30%',
  },
  statLabel: {
    color: Theme.colors.textMuted,
    fontSize: Typography.chartLabel.fontSize,
    fontWeight: Typography.weights.strong,
    textTransform: 'uppercase',
  },
  statValue: {
    color: Theme.colors.text,
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.strong,
    marginTop: Spacing.half,
  },
  statsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  summaryBlock: {
    gap: Spacing.one,
  },
  summaryTitleBlock: {
    flex: 1,
    minWidth: 0,
  },
  summaryTopRow: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  tooltip: {
    backgroundColor: 'rgba(15, 23, 42, 0.94)',
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    gap: Spacing.half,
    padding: Spacing.two,
    position: 'absolute',
  },
  tooltipText: {
    color: Theme.colors.textMuted,
    fontSize: Typography.chartLabel.fontSize,
    fontWeight: Typography.weights.strong,
  },
  tooltipTitle: {
    color: Theme.colors.text,
    fontSize: Typography.caption.fontSize,
    fontWeight: Typography.weights.strong,
  },
  volumeBar: {
    backgroundColor: 'rgba(148, 163, 184, 0.36)',
    borderTopLeftRadius: 2,
    borderTopRightRadius: 2,
    bottom: 4,
    position: 'absolute',
  },
  volumeStrip: {
    bottom: 0,
    height: VOLUME_AREA_HEIGHT,
    left: 0,
    position: 'absolute',
    right: PRICE_LABEL_WIDTH,
  },
  warningText: {
    color: Theme.colors.warning,
    fontSize: Typography.caption.fontSize,
    fontWeight: Typography.weights.strong,
    lineHeight: 16,
  },
  xAxisLabel: {
    bottom: VOLUME_AREA_HEIGHT + 1,
    color: Theme.colors.textMuted,
    fontSize: Typography.chartAxis.fontSize,
    fontWeight: Typography.weights.strong,
    position: 'absolute',
  },
  yAxisLabel: {
    backgroundColor: 'rgba(15, 23, 42, 0.72)',
    color: Theme.colors.textMuted,
    fontSize: Typography.chartAxis.fontSize,
    fontWeight: Typography.weights.strong,
    paddingLeft: Spacing.one,
    position: 'absolute',
    right: 3,
    top: -7,
    width: PRICE_LABEL_WIDTH - 4,
  },
});
