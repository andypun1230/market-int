import { useEffect, useMemo, useState } from 'react';
import type { GestureResponderEvent } from 'react-native';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { SegmentedControl } from '@/components/ui/SegmentedControl';
import { StatusBadge, type Tone } from '@/components/ui/StatusBadge';
import { Spacing, Theme, Typography } from '@/constants/theme';
import {
  loadComparisonHistories,
  type CompareCoverageMetadata,
} from '@/features/stock-detail/compare/compareHistoryLoader';
import {
  buildStockComparisonDashboard,
  resolveStockThemeContext,
  stockCompareTimeframeDays,
  stockCompareTimeframes,
  type NormalizedSeriesPoint,
  type PeerComparisonViewModel,
  type StockCompareTimeframe,
  type StockComparisonChartSeries,
  type StockComparisonDashboardViewModel,
} from '@/features/stock-detail/compare/stockCompareModel';
import type { HistoryData, VolumeAnalysis, WatchlistItem } from '@/types/market';

const CHART_HEIGHT = 178;
const CHART_TOP = 18;
const CHART_BOTTOM = 28;
const CHART_LEFT = 28;
const CHART_RIGHT = 42;

type ChartPoint = NormalizedSeriesPoint & {
  index: number;
  x: number;
  y: number;
};

type ChartSeries = StockComparisonChartSeries & {
  color: string;
  mappedPoints: ChartPoint[];
};

export function StockCompareSections({
  stock,
  volumeAnalysis,
}: {
  stock: WatchlistItem;
  volumeAnalysis?: VolumeAnalysis | null;
}) {
  const [timeframe, setTimeframe] = useState<StockCompareTimeframe>('1M');
  const [histories, setHistories] = useState<Record<string, HistoryData | null>>({});
  const [coverage, setCoverage] = useState<CompareCoverageMetadata | null>(null);
  const [loading, setLoading] = useState(false);
  const symbol = stock.ticker.toUpperCase();
  const themeContext = useMemo(() => resolveStockThemeContext(symbol), [symbol]);
  const requestedSymbols = useMemo(
    () => Array.from(new Set([symbol, 'SPY', ...themeContext.peerSymbols.slice(0, 6)])),
    [symbol, themeContext.peerSymbols],
  );

  useEffect(() => {
    let cancelled = false;
    Promise.resolve()
      .then(() => {
        if (cancelled) {
          return null;
        }
        setLoading(true);
        setCoverage(null);
        return loadComparisonHistories(requestedSymbols, {
          days: stockCompareTimeframeDays[timeframe],
          onUpdate: (state) => {
            if (cancelled) {
              return;
            }
            setHistories(state.histories);
            setCoverage(state.coverage);
          },
          resolution: 'D',
        });
      })
      .then((state) => {
        if (!state || cancelled) {
          return null;
        }
        setHistories(state.histories);
        setCoverage(state.coverage);
        if (state.coverage.partial && state.coverage.peers_available.length) {
          return delay(8_000).then(() => {
            if (cancelled) {
              return null;
            }
            return loadComparisonHistories(requestedSymbols, {
              days: stockCompareTimeframeDays[timeframe],
              onUpdate: (retryState) => {
                if (cancelled) {
                  return;
                }
                setHistories(retryState.histories);
                setCoverage(retryState.coverage);
              },
              resolution: 'D',
            });
          });
        }
        return state;
      })
      .then((state) => {
        if (!state || cancelled) {
          return;
        }
        setHistories(state.histories);
        setCoverage(state.coverage);
      })
      .catch(() => {
        if (!cancelled) {
          setCoverage({
            coverage_ratio: 0,
            partial: true,
            peers_available: [],
            peers_requested: requestedSymbols,
            peers_unavailable: requestedSymbols,
            refreshing: false,
            unavailable_reasons: Object.fromEntries(requestedSymbols.map((requestedSymbol) => [requestedSymbol, 'history unavailable'])),
          });
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [requestedSymbols, timeframe]);

  const model = useMemo(
    () => buildStockComparisonDashboard({
      histories,
      stock,
      symbol,
      timeframe,
      volumeAnalysis,
    }),
    [histories, stock, symbol, timeframe, volumeAnalysis],
  );

  return (
    <View style={styles.stack}>
      <CompareTimeframeSelector timeframe={timeframe} onChange={setTimeframe} />
      <CompareLoadState coverage={coverage} loading={loading} />
      <BenchmarkComparisonCard model={model} />
      <PerformanceSummaryCard model={model} />
      <RelativeStrengthCard model={model} />
      <PeerComparisonDashboard model={model} />
    </View>
  );
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function CompareLoadState({
  coverage,
  loading,
}: {
  coverage: CompareCoverageMetadata | null;
  loading: boolean;
}) {
  if (loading && !coverage?.peers_available.length) {
    return (
      <View style={styles.loadingStack}>
        <View style={styles.loadingBar} />
        <View style={[styles.loadingBar, styles.loadingBarShort]} />
      </View>
    );
  }
  if (coverage?.refreshing && coverage.peers_available.length) {
    return <Text style={styles.helperText}>Some comparisons are still loading.</Text>;
  }
  if (coverage?.partial && coverage.peers_available.length) {
    return (
      <Text style={styles.warningText}>
        {coverage.peers_available.length} of {coverage.peers_requested.length} comparison histories loaded.
      </Text>
    );
  }
  if (coverage && !coverage.peers_available.length) {
    return <Text style={styles.warningText}>Comparison history unavailable.</Text>;
  }
  return null;
}

function CompareTimeframeSelector({
  onChange,
  timeframe,
}: {
  onChange: (timeframe: StockCompareTimeframe) => void;
  timeframe: StockCompareTimeframe;
}) {
  return (
    <SegmentedControl
      options={stockCompareTimeframes.map((item) => ({ key: item, label: item }))}
      selectedKey={timeframe}
      onChange={(key) => onChange(key as StockCompareTimeframe)}
    />
  );
}

function BenchmarkComparisonCard({ model }: { model: StockComparisonDashboardViewModel }) {
  const hasChart = model.chart.series.some((series) => series.points.length >= 2);
  return (
    <View style={styles.card}>
      <View style={styles.sectionHeader}>
        <View style={styles.titleBlock}>
          <Text style={styles.title}>Stock vs Market & Theme</Text>
          {hasChart ? <Text style={styles.subtitle}>{model.timeframe} normalized return</Text> : null}
        </View>
        <StatusBadge label={model.dataQuality.dataSourceLabel} tone={sourceTone(model.dataQuality.dataSource)} />
      </View>
      {hasChart ? (
        <>
          <ComparisonChart model={model} />
          <View style={styles.legendRow}>
            {model.chart.series.map((series) => (
              <View key={series.label} style={styles.legendItem}>
                <View style={[styles.legendDot, { backgroundColor: seriesColor(series.colorKey) }]} />
                <Text style={styles.legendLabel}>{series.label}</Text>
              </View>
            ))}
          </View>
          {model.dataQuality.partialNotice ? <Text style={styles.warningText}>{model.dataQuality.partialNotice}</Text> : null}
        </>
      ) : (
        <ComparisonUnavailableState reason={model.dataQuality.unavailableReason} />
      )}
      <ComparisonDisclosure model={model} />
    </View>
  );
}

function ComparisonUnavailableState({ reason }: { reason: StockComparisonDashboardViewModel['dataQuality']['unavailableReason'] }) {
  return (
    <View style={styles.compactEmptyState}>
      <Text style={styles.emptyTitle}>Comparison history unavailable</Text>
      <Text style={styles.emptyText}>{unavailableReasonText(reason)}</Text>
    </View>
  );
}

function ComparisonChart({ model }: { model: StockComparisonDashboardViewModel }) {
  const [width, setWidth] = useState(0);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const domain = getDomain(model.chart.series.flatMap((series) => series.points.map((point) => point.value)));
  const series = useMemo(
    () => model.chart.series.map((item) => ({
      ...item,
      color: seriesColor(item.colorKey),
      mappedPoints: mapChartPoints(item.points, width, domain.min, domain.max),
    })),
    [domain.max, domain.min, model.chart.series, width],
  );
  const anchorSeries = series.find((item) => item.mappedPoints.length) ?? null;
  const selectedPoint = selectedIndex === null ? null : anchorSeries?.mappedPoints[selectedIndex] ?? null;

  function handlePress(event: GestureResponderEvent) {
    if (!anchorSeries?.mappedPoints.length) {
      return;
    }
    const x = event.nativeEvent.locationX;
    const nearest = anchorSeries.mappedPoints.reduce((best, point) => (
      Math.abs(point.x - x) < Math.abs(best.x - x) ? point : best
    ), anchorSeries.mappedPoints[0]);
    setSelectedIndex(nearest.index);
  }

  const hasSourceSeries = model.chart.series.some((item) => item.points.length >= 2);
  if (!hasSourceSeries) {
    return (
      <View style={[styles.chartBox, styles.emptyChart]}>
        <Text style={styles.emptyText}>Comparison history unavailable.</Text>
      </View>
    );
  }
  const hasMeasuredSeries = width > 0 && series.some((item) => item.mappedPoints.length >= 2);

  return (
    <Pressable
      accessibilityLabel={`${model.symbol} comparison chart for ${model.timeframe}`}
      accessibilityRole="summary"
      onLayout={(event) => setWidth(event.nativeEvent.layout.width)}
      onPressIn={handlePress}
      onPressOut={() => setSelectedIndex(null)}
      onResponderMove={handlePress}
      onMoveShouldSetResponder={() => true}
      style={styles.chartBox}>
      {hasMeasuredSeries ? [domain.max, 0, domain.min].map((value) => (
          <View key={`grid-${value}`} style={[styles.gridLine, { top: getY(value, domain.min, domain.max) }]}>
            <Text style={styles.yAxisLabel}>{formatPercent(value)}</Text>
          </View>
        )) : null}
      {hasMeasuredSeries ? series.map((item) => (
          <View key={item.label}>
            {item.mappedPoints.map((point, index) => {
              if (index === 0) {
                return null;
              }
              return (
                <LineSegment
                  color={item.color}
                  end={point}
                  key={`${item.label}-${point.timestamp}`}
                  start={item.mappedPoints[index - 1]}
                />
              );
            })}
            {item.mappedPoints.length ? <PointMarker color={item.color} point={item.mappedPoints[item.mappedPoints.length - 1]} /> : null}
          </View>
        )) : null}
      {hasMeasuredSeries && selectedPoint ? (
        <>
          <View style={[styles.crosshair, { left: selectedPoint.x }]} />
          {series.map((item) => {
            const active = nearestPointByDate(item.mappedPoints, selectedPoint.timestamp);
            return active ? <PointMarker key={`${item.label}-active`} color={item.color} point={active} active /> : null;
          })}
          <CompareTooltip model={model} point={selectedPoint} series={series} width={width} />
        </>
      ) : null}
      {hasMeasuredSeries ? buildXAxisLabels(anchorSeries?.mappedPoints ?? []).map((item) => (
        <Text key={`${item.timestamp}-${item.label}`} style={[styles.xAxisLabel, { left: clamp(item.x - 18, 2, Math.max(2, width - 42)) }]}>
          {item.label}
        </Text>
      )) : null}
    </Pressable>
  );
}

function CompareTooltip({
  model,
  point,
  series,
  width,
}: {
  model: StockComparisonDashboardViewModel;
  point: ChartPoint;
  series: ChartSeries[];
  width: number;
}) {
  const tooltipWidth = 176;
  const left = clamp(point.x - tooltipWidth / 2, 8, Math.max(8, width - tooltipWidth - 8));
  const rows = series
    .map((item) => {
      const active = nearestPointByDate(item.mappedPoints, point.timestamp);
      return active ? { color: item.color, label: item.label, value: active.value } : null;
    })
    .filter((item): item is { color: string; label: string; value: number } => Boolean(item));
  const stock = rows.find((row) => row.label === model.symbol)?.value ?? null;
  const spy = rows.find((row) => row.label === 'SPY')?.value ?? null;
  const theme = rows.find((row) => row.label !== model.symbol && row.label !== 'SPY')?.value ?? null;
  return (
    <View style={[styles.tooltip, { left, top: clamp(point.y - 92, 8, CHART_HEIGHT - 112), width: tooltipWidth }]}>
      <Text style={styles.tooltipTitle}>{formatDate(point.timestamp)}</Text>
      {rows.map((row) => (
        <View key={row.label} style={styles.tooltipRow}>
          <View style={[styles.tooltipDot, { backgroundColor: row.color }]} />
          <Text style={styles.tooltipLabel}>{row.label}</Text>
          <Text style={styles.tooltipValue}>{formatSignedPercent(row.value)}</Text>
        </View>
      ))}
      {stock !== null && spy !== null ? <Text style={styles.tooltipEdge}>vs SPY {formatSignedPoints(stock - spy)}</Text> : null}
      {stock !== null && theme !== null ? <Text style={styles.tooltipEdge}>vs Theme {formatSignedPoints(stock - theme)}</Text> : null}
    </View>
  );
}

function PerformanceSummaryCard({ model }: { model: StockComparisonDashboardViewModel }) {
  const { performance } = model;
  return (
    <View style={styles.card}>
      <SectionTitle subtitle={`${performance.timeframe} return and relative edge`} title="Performance Summary" />
      <View style={styles.metricGrid}>
        <Metric label={model.symbol} value={formatSignedPercent(performance.stockReturn)} />
        <Metric label={model.themeContext.primaryThemeName ?? 'Theme'} value={formatSignedPercent(performance.themeReturn)} />
        <Metric label="SPY" value={formatSignedPercent(performance.spyReturn)} />
        <Metric label="Relative Edge vs SPY" value={formatSignedPoints(performance.edgeVsSpy)} />
        <Metric label="Relative Edge vs Theme" value={formatSignedPoints(performance.edgeVsTheme)} />
      </View>
    </View>
  );
}

function RelativeStrengthCard({ model }: { model: StockComparisonDashboardViewModel }) {
  return (
    <View style={styles.card}>
      <View style={styles.sectionHeader}>
        <SectionTitle title="Relative Strength" />
        <StatusBadge label={model.relativeStrength.label} tone={relativeStrengthTone(model.relativeStrength.state)} />
      </View>
      <Text style={styles.bodyText}>{model.relativeStrength.interpretation}</Text>
      <Text style={styles.helperText}>Confidence: {capitalize(model.relativeStrength.confidence)}</Text>
    </View>
  );
}

function PeerComparisonDashboard({ model }: { model: StockComparisonDashboardViewModel }) {
  return (
    <View style={styles.card}>
      <SectionTitle subtitle={`${model.peerRanking.rankedCount} comparable symbols`} title="Peer Comparison" />
      <PeerRankingCard model={model} />
      <View style={styles.dashboardDivider} />
      <PeerComparisonCard model={model} />
      <View style={styles.dashboardDivider} />
      <LeadershipReadCard model={model} />
    </View>
  );
}

function PeerRankingCard({ model }: { model: StockComparisonDashboardViewModel }) {
  const maxMagnitude = Math.max(...model.peerRanking.items.map((item) => Math.abs(item.periodReturn ?? 0)), 1);
  return (
    <View style={styles.dashboardSection}>
      <SectionTitle title="Ranking" />
      {model.peerRanking.items.length >= 2 ? (
        <View style={styles.rankStack}>
          {model.peerRanking.items.slice(0, 7).map((item) => (
            <View key={item.symbol} style={styles.rankRow}>
              <Text style={[styles.rankSymbol, item.isSelectedStock && styles.selectedText]}>{item.symbol}</Text>
              <View style={styles.rankTrack}>
                <View
                  style={[
                    styles.rankFill,
                    item.isSelectedStock && styles.rankFillSelected,
                    (item.periodReturn ?? 0) < 0 && styles.rankFillNegative,
                    { width: `${Math.max(4, Math.abs(item.periodReturn ?? 0) / maxMagnitude * 100)}%` },
                  ]}
                />
              </View>
              <Text style={[styles.rankValue, item.isSelectedStock && styles.selectedText]}>{formatSignedPercent(item.periodReturn)}</Text>
            </View>
          ))}
          {model.peerRanking.themeMedian !== null ? (
            <View style={styles.medianRow}>
              <Text style={styles.helperText}>Theme Median {formatSignedPercent(model.peerRanking.themeMedian)}</Text>
            </View>
          ) : null}
        </View>
      ) : (
        <Text style={styles.emptyText}>Too few valid peers for ranking.</Text>
      )}
      <View style={styles.metricGrid}>
        <Metric label="Peer Rank" value={model.peerRanking.rank ? `${model.peerRanking.rank} of ${model.peerRanking.rankedCount}` : 'N/A'} />
        <Metric label="Percentile" value={model.peerRanking.percentile === null ? 'N/A' : `${Math.round(model.peerRanking.percentile)}th`} />
        <Metric label="Above Theme Median" value={formatSignedPoints(model.peerRanking.aboveMedian)} />
      </View>
    </View>
  );
}

function PeerComparisonCard({ model }: { model: StockComparisonDashboardViewModel }) {
  return (
    <View style={styles.dashboardSection}>
      <SectionTitle subtitle="Compact leadership checks" title="Peers" />
      <View style={styles.peerList}>
        {model.peers.slice(0, 7).map((peer) => (
          <PeerRow key={peer.symbol} peer={peer} />
        ))}
      </View>
    </View>
  );
}

function PeerRow({ peer }: { peer: PeerComparisonViewModel }) {
  const unavailable = peer.periodReturn === null;
  return (
    <View style={[styles.peerRow, peer.isSelectedStock && styles.peerRowSelected]}>
      <View style={styles.peerHeader}>
        <Text style={[styles.peerSymbol, peer.isSelectedStock && styles.selectedText]}>{peer.symbol}</Text>
        <Text style={[styles.peerReturn, { color: returnColor(peer.periodReturn) }]}>{formatSignedPercent(peer.periodReturn)}</Text>
        <StatusBadge label={peerStateLabel(peer.relativeStrength)} tone={peerTone(peer.relativeStrength)} />
      </View>
      {unavailable ? (
        <Text style={styles.emptyText}>History unavailable for this peer.</Text>
      ) : (
        <View style={styles.peerMetaGrid}>
          <Info label="Trend" value={peer.trend} />
          <Info label="Momentum" value={peer.momentum} />
          {peer.volume !== 'N/A' ? <Info label="Volume" value={peer.volume} /> : null}
          <Info label="Setup" value={peer.setup} />
          <Info label="From High" value={formatSignedPercent(peer.distanceFromHigh)} />
        </View>
      )}
    </View>
  );
}

function LeadershipReadCard({ model }: { model: StockComparisonDashboardViewModel }) {
  return (
    <View style={styles.dashboardSection}>
      <View style={styles.sectionHeader}>
        <SectionTitle title="Conclusion" />
        <StatusBadge label={model.leadership.classification} tone={relativeStrengthTone(model.relativeStrength.state)} />
      </View>
      <Text style={styles.bodyText}>{model.leadership.summary}</Text>
      <View style={styles.metricGrid}>
        <Metric label="Main Strength" value={model.leadership.mainStrength} />
        <Metric label="Main Risk" value={model.leadership.mainRisk} warning />
      </View>
    </View>
  );
}

function ComparisonDisclosure({ model }: { model: StockComparisonDashboardViewModel }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <View style={styles.disclosure}>
      <Pressable
        accessibilityRole="button"
        accessibilityState={{ expanded }}
        onPress={() => setExpanded((value) => !value)}
        style={styles.disclosureHeader}>
        <Text style={styles.disclosureTitle}>How comparison is calculated</Text>
        <Text style={styles.disclosureIcon}>{expanded ? '−' : '+'}</Text>
      </Pressable>
      {expanded ? (
        <View style={styles.disclosureBody}>
          <Text style={styles.helperText}>Theme benchmark: {model.dataQuality.benchmarkLabel}</Text>
          <Text style={styles.helperText}>Method: {model.dataQuality.benchmarkMethod}</Text>
          <Text style={styles.helperText}>Peer universe: {model.dataQuality.peerUniverseLabel}</Text>
          <Text style={styles.helperText}>Alignment: {model.dataQuality.alignment.alignedPointCount} shared comparison points</Text>
          {model.dataQuality.alignment.asOfDate ? (
            <Text style={styles.helperText}>As of: {formatShortDate(model.dataQuality.alignment.asOfDate)}</Text>
          ) : null}
          {model.dataQuality.warnings.map((warning) => (
            <Text key={warning} style={styles.warningText}>{warning}</Text>
          ))}
        </View>
      ) : (
        <View style={styles.disclosureBody}>
          <Text style={styles.helperText}>Theme benchmark: {model.dataQuality.benchmarkLabel}</Text>
          <Text style={styles.helperText}>{model.dataQuality.peerUniverseLabel}</Text>
        </View>
      )}
    </View>
  );
}

function SectionTitle({ subtitle, title }: { subtitle?: string; title: string }) {
  return (
    <View style={styles.titleBlock}>
      <Text style={styles.title}>{title}</Text>
      {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
    </View>
  );
}

function Metric({ label, value, warning = false }: { label: string; value: string; warning?: boolean }) {
  return (
    <View style={styles.metric}>
      <Text style={styles.metricLabel}>{label}</Text>
      <Text style={[styles.metricValue, warning && styles.warningText]}>{value}</Text>
    </View>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <Text style={styles.infoText}>{label}: <Text style={styles.infoValue}>{value}</Text></Text>
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
          top: midY - 1,
          transform: [{ rotateZ: `${angle}rad` }],
          width: length,
        },
      ]}
    />
  );
}

function PointMarker({ active = false, color, point }: { active?: boolean; color: string; point: ChartPoint }) {
  const size = active ? 10 : 8;
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

function mapChartPoints(points: NormalizedSeriesPoint[], width: number, min: number, max: number): ChartPoint[] {
  if (width <= 0 || points.length < 2) {
    return [];
  }
  const plotWidth = Math.max(1, width - CHART_LEFT - CHART_RIGHT);
  return points.map((point, index) => ({
    ...point,
    index,
    x: CHART_LEFT + (index / Math.max(points.length - 1, 1)) * plotWidth,
    y: getY(point.value, min, max),
  }));
}

function getY(value: number, min: number, max: number) {
  const plotHeight = CHART_HEIGHT - CHART_TOP - CHART_BOTTOM;
  const range = Math.max(max - min, 0.01);
  return CHART_TOP + ((max - value) / range) * plotHeight;
}

function getDomain(values: number[]) {
  const valid = values.filter((value) => Number.isFinite(value));
  const min = Math.min(0, ...valid);
  const max = Math.max(0, ...valid);
  const padding = Math.max(2, (max - min) * 0.12);
  return { max: max + padding, min: min - padding };
}

function buildXAxisLabels(points: ChartPoint[]) {
  if (!points.length) {
    return [];
  }
  const count = Math.min(5, points.length);
  return Array.from({ length: count }, (_, index) => {
    const sourceIndex = Math.round((index / Math.max(1, count - 1)) * (points.length - 1));
    const point = points[sourceIndex];
    return {
      label: formatShortDate(point.timestamp),
      timestamp: point.timestamp,
      x: point.x,
    };
  });
}

function nearestPointByDate(points: ChartPoint[], timestamp: string) {
  const key = timestamp.slice(0, 10);
  return points.find((point) => point.timestamp.slice(0, 10) === key) ?? null;
}

function seriesColor(key: StockComparisonChartSeries['colorKey']) {
  switch (key) {
    case 'stock':
      return Theme.colors.success;
    case 'spy':
      return Theme.colors.accent;
    case 'theme':
      return Theme.colors.purple;
  }
}

function sourceTone(source: string): Tone {
  const normalized = source.toLowerCase();
  if (normalized.includes('live')) {
    return 'success';
  }
  if (normalized.includes('mock') || normalized.includes('fallback') || normalized.includes('generated_test_data') || normalized === 'test') {
    return 'warning';
  }
  if (normalized.includes('unavailable')) {
    return 'muted';
  }
  return 'info';
}

function unavailableReasonText(reason: StockComparisonDashboardViewModel['dataQuality']['unavailableReason']) {
  switch (reason) {
    case 'stock_history_missing':
      return 'Stock history is unavailable for this timeframe.';
    case 'spy_history_missing':
      return 'SPY benchmark history is unavailable for this timeframe.';
    case 'theme_history_missing':
      return 'Theme benchmark history is unavailable for this timeframe.';
    case 'no_overlapping_dates':
      return 'Historical comparison will appear when stock and benchmark histories overlap.';
    case 'insufficient_points':
      return 'At least two valid history points are needed to draw the comparison.';
    case 'invalid_values':
      return 'History contains invalid price values.';
    default:
      return 'Historical comparison will appear when valid histories overlap.';
  }
}

function relativeStrengthTone(state: StockComparisonDashboardViewModel['relativeStrength']['state']): Tone {
  if (state === 'leading_market_and_theme' || state === 'leading_theme') {
    return 'success';
  }
  if (state === 'following_theme' || state === 'mixed' || state === 'leader_weakening') {
    return 'warning';
  }
  if (state.includes('lagging')) {
    return 'danger';
  }
  return 'muted';
}

function peerTone(state: PeerComparisonViewModel['relativeStrength']): Tone {
  switch (state) {
    case 'leader':
    case 'strong':
      return 'success';
    case 'lagging':
      return 'warning';
    case 'weak':
      return 'danger';
    case 'neutral':
      return 'muted';
    default:
      return 'muted';
  }
}

function peerStateLabel(state: PeerComparisonViewModel['relativeStrength']) {
  switch (state) {
    case 'leader':
      return 'Leader';
    case 'strong':
      return 'Strong';
    case 'lagging':
      return 'Lagging';
    case 'weak':
      return 'Weak';
    case 'neutral':
      return 'Neutral';
    default:
      return 'N/A';
  }
}

function returnColor(value: number | null) {
  if (value === null) {
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

function formatSignedPercent(value: number | null) {
  if (value === null || !Number.isFinite(value)) {
    return 'N/A';
  }
  return `${value >= 0 ? '+' : '-'}${Math.abs(value).toFixed(1)}%`;
}

function formatPercent(value: number) {
  return `${value.toFixed(1)}%`;
}

function formatSignedPoints(value: number | null) {
  if (value === null || !Number.isFinite(value)) {
    return 'N/A';
  }
  return `${value >= 0 ? '+' : '-'}${Math.abs(value).toFixed(1)} pts`;
}

function formatShortDate(timestamp: string) {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return timestamp.slice(5, 10);
  }
  return date.toLocaleDateString('en-US', { day: 'numeric', month: 'short' });
}

function formatDate(timestamp: string) {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return timestamp;
  }
  return date.toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' });
}

function capitalize(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

const styles = StyleSheet.create({
  bodyText: {
    color: Theme.colors.text,
    fontSize: Typography.control.fontSize,
    fontWeight: Typography.weights.emphasis,
    lineHeight: 19,
  },
  card: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    gap: Spacing.twoAndHalf,
    padding: Spacing.twoAndHalf,
  },
  chartBox: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    height: CHART_HEIGHT,
    overflow: 'hidden',
  },
  compactEmptyState: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    gap: Spacing.one,
    padding: Spacing.twoAndHalf,
  },
  crosshair: {
    backgroundColor: 'rgba(148, 163, 184, 0.28)',
    bottom: CHART_BOTTOM,
    position: 'absolute',
    top: CHART_TOP,
    width: 1,
  },
  dashboardDivider: {
    backgroundColor: Theme.colors.border,
    height: 1,
  },
  dashboardSection: {
    gap: Spacing.two,
  },
  disclosure: {
    gap: Spacing.one,
  },
  disclosureBody: {
    gap: Spacing.one,
  },
  disclosureHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
    minHeight: 44,
  },
  disclosureIcon: {
    color: Theme.colors.textMuted,
    fontSize: Typography.sectionTitle.fontSize,
    fontWeight: Typography.weights.strong,
  },
  disclosureTitle: {
    color: Theme.colors.text,
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.strong,
  },
  emptyChart: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  emptyText: {
    color: Theme.colors.textMuted,
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.strong,
  },
  emptyTitle: {
    color: Theme.colors.text,
    fontSize: Typography.control.fontSize,
    fontWeight: Typography.weights.strong,
  },
  gridLine: {
    backgroundColor: 'rgba(148, 163, 184, 0.16)',
    height: 1,
    left: 0,
    position: 'absolute',
    right: CHART_RIGHT,
  },
  helperText: {
    color: Theme.colors.textMuted,
    fontSize: Typography.caption.fontSize,
    fontWeight: Typography.weights.strong,
    lineHeight: 16,
  },
  infoText: {
    color: Theme.colors.textMuted,
    fontSize: Typography.caption.fontSize,
    fontWeight: Typography.weights.strong,
    lineHeight: 16,
  },
  infoValue: {
    color: Theme.colors.text,
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
  legendLabel: {
    color: Theme.colors.textMuted,
    fontSize: Typography.caption.fontSize,
    fontWeight: Typography.weights.strong,
  },
  legendRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  lineSegment: {
    borderRadius: Theme.radii.pill,
    height: 2,
    position: 'absolute',
  },
  loadingBar: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderRadius: Theme.radii.pill,
    height: 10,
    width: '100%',
  },
  loadingBarShort: {
    width: '62%',
  },
  loadingStack: {
    gap: Spacing.one,
  },
  medianRow: {
    paddingTop: Spacing.one,
  },
  metric: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: StyleSheet.hairlineWidth,
    flexBasis: '47%',
    flexGrow: 1,
    gap: Spacing.half,
    minWidth: 126,
    padding: Spacing.two,
  },
  metricGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  metricLabel: {
    color: Theme.colors.textMuted,
    fontSize: Typography.chartLabel.fontSize,
    fontWeight: Typography.weights.strong,
    textTransform: 'uppercase',
  },
  metricValue: {
    color: Theme.colors.text,
    fontSize: Typography.control.fontSize,
    fontWeight: Typography.weights.strong,
    lineHeight: 18,
  },
  peerHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
  },
  peerList: {
    gap: Spacing.two,
  },
  peerMetaGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  peerReturn: {
    fontSize: Typography.control.fontSize,
    fontWeight: Typography.weights.strong,
  },
  peerRow: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: StyleSheet.hairlineWidth,
    gap: Spacing.one,
    padding: Spacing.two,
  },
  peerRowSelected: {
    borderColor: Theme.colors.accent,
  },
  peerSymbol: {
    color: Theme.colors.text,
    flex: 1,
    fontSize: Typography.bodyLarge.fontSize,
    fontWeight: Typography.weights.strong,
  },
  pointMarker: {
    backgroundColor: Theme.colors.background,
    borderRadius: 6,
    borderWidth: 2,
    position: 'absolute',
  },
  rankFill: {
    backgroundColor: Theme.colors.success,
    borderRadius: Theme.radii.pill,
    height: '100%',
  },
  rankFillNegative: {
    backgroundColor: Theme.colors.danger,
  },
  rankFillSelected: {
    backgroundColor: Theme.colors.accent,
  },
  rankRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
  },
  rankStack: {
    gap: Spacing.two,
  },
  rankSymbol: {
    color: Theme.colors.textMuted,
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.strong,
    width: 52,
  },
  rankTrack: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderRadius: Theme.radii.pill,
    flex: 1,
    height: 10,
    overflow: 'hidden',
  },
  rankValue: {
    color: Theme.colors.text,
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.strong,
    textAlign: 'right',
    width: 58,
  },
  sectionHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  selectedText: {
    color: Theme.colors.accent,
  },
  stack: {
    gap: Spacing.three,
  },
  subtitle: {
    color: Theme.colors.textMuted,
    fontSize: Typography.caption.fontSize,
    fontWeight: Typography.weights.strong,
  },
  title: {
    color: Theme.colors.text,
    fontSize: Typography.bodyLarge.fontSize,
    fontWeight: Typography.weights.strong,
  },
  titleBlock: {
    flex: 1,
    gap: Spacing.half,
    minWidth: 0,
  },
  tooltip: {
    backgroundColor: 'rgba(15, 23, 42, 0.96)',
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    gap: Spacing.half,
    padding: Spacing.two,
    position: 'absolute',
  },
  tooltipDot: {
    borderRadius: 4,
    height: 8,
    width: 8,
  },
  tooltipEdge: {
    color: Theme.colors.textMuted,
    fontSize: Typography.chartLabel.fontSize,
    fontWeight: Typography.weights.strong,
  },
  tooltipLabel: {
    color: Theme.colors.textMuted,
    flex: 1,
    fontSize: Typography.chartLabel.fontSize,
    fontWeight: Typography.weights.strong,
  },
  tooltipRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.one,
  },
  tooltipTitle: {
    color: Theme.colors.text,
    fontSize: Typography.caption.fontSize,
    fontWeight: Typography.weights.strong,
  },
  tooltipValue: {
    color: Theme.colors.text,
    fontSize: Typography.chartLabel.fontSize,
    fontWeight: Typography.weights.strong,
  },
  warningText: {
    color: Theme.colors.warning,
    fontSize: Typography.caption.fontSize,
    fontWeight: Typography.weights.strong,
    lineHeight: 16,
  },
  xAxisLabel: {
    bottom: 5,
    color: Theme.colors.textMuted,
    fontSize: Typography.chartAxis.fontSize,
    fontWeight: Typography.weights.strong,
    position: 'absolute',
    width: 40,
  },
  yAxisLabel: {
    backgroundColor: 'rgba(15, 23, 42, 0.78)',
    color: Theme.colors.textMuted,
    fontSize: Typography.chartAxis.fontSize,
    fontWeight: Typography.weights.strong,
    paddingHorizontal: Spacing.half,
    position: 'absolute',
    right: 2,
    top: -7,
  },
});
