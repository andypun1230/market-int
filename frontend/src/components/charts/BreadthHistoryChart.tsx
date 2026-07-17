import { useMemo, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Spacing, Theme } from '@/constants/theme';
import type { BreadthHistoryPoint } from '@/data/sectorTabTestData';
import {
  buildBreadthAccessibilitySummary,
  calculateBreadthNetChanges,
  calculateBreadthTrendLabel,
  formatBreadthPointChange,
} from '@/features/sectors/analysis/breadthTrend';

type BreadthHistoryChartProps = {
  points: BreadthHistoryPoint[];
};

type ChartPoint = {
  index: number;
  label: string;
  value: number;
  x: number;
  y: number;
};

type LineSeries = {
  color: string;
  key: 'percentAbove20Ema' | 'percentAbove50Ema';
  label: string;
  points: ChartPoint[];
};

export const BREADTH_CHART_Y_DOMAIN = { max: 100, min: 0 };
export const BREADTH_CHART_REFERENCE_LINES = [25, 50, 75] as const;

const CHART_HEIGHT = 170;
const CHART_HORIZONTAL_PADDING = 26;
const CHART_VERTICAL_PADDING = 14;
const MAX_VISIBLE_POINTS = 52;

export function BreadthHistoryChart({ points }: BreadthHistoryChartProps) {
  const [chartWidth, setChartWidth] = useState(0);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const visiblePoints = useMemo(() => sampleChartPoints(points, MAX_VISIBLE_POINTS), [points]);
  const selectedSource = selectedIndex === null ? null : visiblePoints[selectedIndex] ?? null;
  const changes = useMemo(() => calculateBreadthNetChanges(points), [points]);
  const trend = useMemo(() => calculateBreadthTrendLabel(points), [points]);
  const move20 = formatBreadthPointChange(changes.start20, changes.end20);
  const move50 = formatBreadthPointChange(changes.start50, changes.end50);
  const move200 = formatBreadthPointChange(changes.start200, changes.end200);
  const lineSeries = useMemo(
    () => buildBreadthLineSeries(visiblePoints, chartWidth, CHART_HEIGHT),
    [chartWidth, visiblePoints],
  );
  const selectedChartPoint = selectedIndex === null ? null : lineSeries[0]?.points[selectedIndex] ?? null;

  if (!visiblePoints.length) {
    return <Text style={styles.empty}>No breadth history available.</Text>;
  }

  return (
    <View
      accessibilityLabel={buildBreadthAccessibilitySummary(points)}
      accessibilityRole="summary"
      style={styles.container}
    >
      <View style={styles.header}>
        <View>
          <Text style={styles.title}>Breadth History</Text>
          <Text style={styles.subtitle}>Fixed 0–100% participation scale</Text>
        </View>
        <View accessibilityLabel={`Breadth trend ${trend}`} style={styles.trendPill}>
          <Text style={styles.trendText}>{trend}</Text>
        </View>
      </View>

      <View style={styles.legend}>
        <Legend color={Theme.colors.success} label="Above 20 EMA" />
        <Legend color={Theme.colors.accent} label="Above 50 EMA" />
      </View>

      <Pressable
        accessibilityLabel="Breadth history line chart. Tap a point for values."
        onLayout={(event) => setChartWidth(event.nativeEvent.layout.width)}
        onPress={() => setSelectedIndex(null)}
        style={styles.chart}
      >
        {[0, ...BREADTH_CHART_REFERENCE_LINES, 100].map((guide) => (
          <View
            key={guide}
            style={[
              styles.guideLine,
              guide === 50 && styles.midGuideLine,
              { top: getYForPercent(guide, CHART_HEIGHT) },
            ]}
          >
            <Text style={[styles.guideLabel, guide === 50 && styles.midGuideLabel]}>{guide}%</Text>
          </View>
        ))}

        {chartWidth > 0
          ? lineSeries.map((series) => (
              <View key={series.key} pointerEvents="box-none" style={StyleSheet.absoluteFill}>
                {series.points.slice(1).map((point, index) => (
                  <LineSegment
                    color={series.color}
                    key={`${series.key}-${point.label}-${index}`}
                    start={series.points[index]}
                    end={point}
                  />
                ))}
                {series.points.map((point, index) => {
                  const isLatest = index === series.points.length - 1;
                  const isSelected = selectedSource?.label === point.label;
                  return (
                    <Pressable
                      accessibilityLabel={`${series.label} ${point.value.toFixed(1)}% at ${point.label}`}
                      accessibilityRole="button"
                      hitSlop={8}
                      key={`${series.key}-marker-${point.label}-${index}`}
                      onPress={() => setSelectedIndex(index)}
                      style={[
                        styles.marker,
                        {
                          backgroundColor: series.color,
                          borderColor: isLatest || isSelected ? Theme.colors.text : series.color,
                          height: isLatest || isSelected ? 11 : 6,
                          left: point.x - (isLatest || isSelected ? 5.5 : 3),
                          top: point.y - (isLatest || isSelected ? 5.5 : 3),
                          width: isLatest || isSelected ? 11 : 6,
                        },
                      ]}
                    />
                  );
                })}
              </View>
            ))
          : null}

        {selectedChartPoint && selectedSource && chartWidth > 0 ? (
          <Tooltip
            point={selectedChartPoint}
            source={selectedSource}
            width={chartWidth}
          />
        ) : null}
      </Pressable>

      <View style={styles.axisRow}>
        <Text style={styles.axisText}>{visiblePoints[0]?.label}</Text>
        <Text style={styles.axisText}>Current</Text>
      </View>

      <View style={styles.currentCard}>
        <Text style={styles.currentTitle}>Current Breadth</Text>
        <View style={styles.currentMetrics}>
          <SummaryMetric label="20 EMA" value={`${changes.end20.toFixed(1)}%`} tone="success" />
          <SummaryMetric label="50 EMA" value={`${changes.end50.toFixed(1)}%`} tone="accent" />
          <SummaryMetric label="Trend" value={trend} />
        </View>
      </View>

      <View style={styles.summaryStack}>
        <ChangeRow label="Above 20 EMA" move={move20} />
        <ChangeRow label="Above 50 EMA" move={move50} />
        <ChangeRow label="Above 200 EMA" move={move200} />
      </View>
    </View>
  );
}

export function buildBreadthLineSeries(points: BreadthHistoryPoint[], width: number, height: number): LineSeries[] {
  return [
    {
      color: Theme.colors.success,
      key: 'percentAbove20Ema',
      label: 'Above 20 EMA',
      points: mapPointsToChart(points, 'percentAbove20Ema', width, height),
    },
    {
      color: Theme.colors.accent,
      key: 'percentAbove50Ema',
      label: 'Above 50 EMA',
      points: mapPointsToChart(points, 'percentAbove50Ema', width, height),
    },
  ];
}

export function sampleChartPoints(points: BreadthHistoryPoint[], maxPoints: number) {
  if (points.length <= maxPoints) {
    return points;
  }

  const step = (points.length - 1) / (maxPoints - 1);
  return Array.from({ length: maxPoints }, (_, index) => points[Math.round(index * step)]);
}

function mapPointsToChart(
  points: BreadthHistoryPoint[],
  key: 'percentAbove20Ema' | 'percentAbove50Ema',
  width: number,
  height: number,
): ChartPoint[] {
  if (width <= 0) {
    return [];
  }
  const plotWidth = Math.max(1, width - CHART_HORIZONTAL_PADDING * 2);
  return points.map((point, index) => ({
    index,
    label: point.label,
    value: point[key],
    x: CHART_HORIZONTAL_PADDING + (points.length <= 1 ? 0 : (index / (points.length - 1)) * plotWidth),
    y: getYForPercent(point[key], height),
  }));
}

function getYForPercent(value: number, height: number) {
  const plotHeight = height - CHART_VERTICAL_PADDING * 2;
  return CHART_VERTICAL_PADDING + ((BREADTH_CHART_Y_DOMAIN.max - value) / 100) * plotHeight;
}

function LineSegment({ color, start, end }: { color: string; start: ChartPoint; end: ChartPoint }) {
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
          top: midY - 1,
          transform: [{ rotateZ: `${angle}rad` }],
          width: length,
        },
      ]}
    />
  );
}

function Tooltip({ point, source, width }: { point: ChartPoint; source: BreadthHistoryPoint; width: number }) {
  const tooltipWidth = 164;
  const left = Math.min(Math.max(8, point.x - tooltipWidth / 2), Math.max(8, width - tooltipWidth - 8));
  return (
    <View style={[styles.tooltip, { left, top: Math.max(8, point.y - 74), width: tooltipWidth }]}>
      <Text style={styles.tooltipTitle}>{source.label}</Text>
      <Text style={styles.tooltipText}>Above 20 EMA: {source.percentAbove20Ema.toFixed(1)}%</Text>
      <Text style={styles.tooltipText}>Above 50 EMA: {source.percentAbove50Ema.toFixed(1)}%</Text>
      <Text style={styles.tooltipText}>Above 200 EMA: {source.percentAbove200Ema.toFixed(1)}%</Text>
    </View>
  );
}

function SummaryMetric({ label, value, tone }: { label: string; value: string; tone?: 'success' | 'accent' }) {
  const color = tone === 'success' ? Theme.colors.success : tone === 'accent' ? Theme.colors.accent : Theme.colors.text;
  return (
    <View style={styles.summaryMetric}>
      <Text style={styles.metricLabel}>{label}</Text>
      <Text style={[styles.metricValue, { color }]}>{value}</Text>
    </View>
  );
}

function ChangeRow({ label, move }: { label: string; move: ReturnType<typeof formatBreadthPointChange> }) {
  const tone = move.change > 0 ? Theme.colors.success : move.change < 0 ? Theme.colors.danger : Theme.colors.textMuted;
  return (
    <View style={styles.changeRow}>
      <Text style={styles.changeLabel}>{label}</Text>
      <View style={styles.changeValueGroup}>
        <Text style={styles.changeRange}>{move.rangeLabel}</Text>
        <Text style={[styles.changeDelta, { color: tone }]}>Change: {move.changeLabel}</Text>
      </View>
    </View>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <View style={styles.legendItem}>
      <View style={[styles.legendDot, { backgroundColor: color }]} />
      <Text style={styles.legendText}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  axisRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  axisText: {
    color: Theme.colors.textMuted,
    fontSize: 10,
    fontWeight: '800',
  },
  changeDelta: {
    fontSize: 11,
    fontWeight: '900',
  },
  changeLabel: {
    color: Theme.colors.textMuted,
    flex: 1,
    fontSize: 11,
    fontWeight: '800',
  },
  changeRange: {
    color: Theme.colors.text,
    fontSize: 12,
    fontWeight: '900',
  },
  changeRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  changeValueGroup: {
    alignItems: 'flex-end',
    gap: Spacing.half,
  },
  chart: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    height: CHART_HEIGHT,
    overflow: 'hidden',
  },
  container: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    gap: Spacing.two,
    padding: Spacing.three,
  },
  currentCard: {
    backgroundColor: Theme.colors.card,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    gap: Spacing.two,
    padding: Spacing.two,
  },
  currentMetrics: {
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  currentTitle: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '900',
    textTransform: 'uppercase',
  },
  empty: {
    color: Theme.colors.textMuted,
    fontSize: 13,
    fontWeight: '800',
  },
  guideLabel: {
    color: Theme.colors.textMuted,
    fontSize: 9,
    fontWeight: '800',
    left: 4,
    position: 'absolute',
    top: -7,
  },
  guideLine: {
    backgroundColor: Theme.colors.border,
    height: 1,
    left: 0,
    opacity: 0.45,
    position: 'absolute',
    right: 0,
  },
  header: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  legend: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  legendDot: {
    borderRadius: 4,
    height: 8,
    width: 8,
  },
  legendItem: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.one,
  },
  legendText: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '800',
  },
  lineSegment: {
    borderRadius: 2,
    height: 2,
    position: 'absolute',
  },
  marker: {
    borderRadius: 999,
    borderWidth: 2,
    position: 'absolute',
  },
  metricLabel: {
    color: Theme.colors.textMuted,
    fontSize: 10,
    fontWeight: '800',
  },
  metricValue: {
    fontSize: 13,
    fontWeight: '900',
  },
  midGuideLabel: {
    color: Theme.colors.text,
  },
  midGuideLine: {
    opacity: 0.85,
  },
  subtitle: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '700',
  },
  summaryMetric: {
    flex: 1,
    gap: Spacing.half,
  },
  summaryStack: {
    gap: Spacing.one,
  },
  title: {
    color: Theme.colors.text,
    fontSize: 14,
    fontWeight: '900',
  },
  tooltip: {
    backgroundColor: Theme.colors.cardElevated,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    gap: Spacing.half,
    padding: Spacing.two,
    position: 'absolute',
  },
  tooltipText: {
    color: Theme.colors.text,
    fontSize: 11,
    fontWeight: '800',
  },
  tooltipTitle: {
    color: Theme.colors.textMuted,
    fontSize: 10,
    fontWeight: '900',
    textTransform: 'uppercase',
  },
  trendPill: {
    backgroundColor: Theme.colors.accentSoft,
    borderColor: Theme.colors.accent,
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    paddingHorizontal: Spacing.two,
    paddingVertical: Spacing.one,
  },
  trendText: {
    color: Theme.colors.text,
    fontSize: 11,
    fontWeight: '900',
  },
});
