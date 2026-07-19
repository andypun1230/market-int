import { useMemo, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { SegmentedControl } from '@/components/ui/SegmentedControl';
import { StatusBadge, type Tone } from '@/components/ui/StatusBadge';
import { TestDataBadge } from '@/components/ui/TestDataBadge';
import { Spacing, Theme } from '@/constants/theme';
import {
  buildRotationTrailSummary,
  calculateRotationDomain,
  classifyQuadrant,
  formatQuadrant,
  type RotationDomain,
  type RotationPoint,
  type RotationQuadrant,
} from '@/data/sectorTabTestData';
import {
  buildRotationVisibilitySummary,
  filterRotationItemsByQuadrant,
  findAvailableLabelPlacement,
  getRotationShortLabel,
  selectSmartLabelKeys,
  type PlacedLabel,
  type Rect,
  type RotationLabelCandidate,
  type RotationLabelMode,
  type RotationQuadrantFilter,
} from '@/features/sectors/analysis/rotationLabels';

type ChartRotationPoint = RotationPoint & {
  date?: string | null;
};

type ChartItem<T> = RotationLabelCandidate & {
  color: string;
  item: T;
  momentum: number;
  strength: number;
};

type SelectedPoint<T> = {
  chartItem: ChartItem<T>;
  point: ChartRotationPoint;
  pointIndex: number;
  totalPoints: number;
};

type RotationQuadrantChartProps<T> = {
  benchmark: string;
  chartSize?: number;
  emptyLabel?: string;
  getHistory?: (item: T) => ChartRotationPoint[];
  getItemKey?: (item: T) => string;
  getItemType?: (item: T) => 'sector' | 'theme' | string;
  getLabel?: (item: T) => string;
  getLabelPriority?: (item: T) => number;
  getName: (item: T) => string;
  getRelativeMomentum: (item: T) => number | null;
  getRelativeStrength: (item: T) => number | null;
  interval: string;
  items: T[];
  labelMode?: RotationLabelMode;
  maxItems?: number;
  maxSmartLabels?: number;
  onExpand?: () => void;
  onLabelModeChange?: (mode: RotationLabelMode) => void;
  onPressItem?: (item: T) => void;
  onQuadrantFilterChange?: (filter: RotationQuadrantFilter) => void;
  onSelectItem?: (itemKey: string | null) => void;
  onToggleWatchlist?: (item: T) => void;
  presentation?: 'card' | 'fullscreen';
  quadrantFilter?: RotationQuadrantFilter;
  selectedItemKey?: string | null;
  showExpandButton?: boolean;
  showTestDataBadge?: boolean;
  trailLength?: number;
  watchlistKeys?: Set<string>;
};

const DEFAULT_CHART_SIZE = 300;
const PADDING = 34;
const LABEL_MODE_OPTIONS = [
  { key: 'smart', label: 'Smart' },
  { key: 'all', label: 'All' },
  { key: 'none', label: 'None' },
];
const QUADRANT_OPTIONS = [
  { key: 'all', label: 'All' },
  { key: 'leading', label: 'Leading' },
  { key: 'improving', label: 'Improving' },
  { key: 'weakening', label: 'Weakening' },
  { key: 'lagging', label: 'Lagging' },
];

export function RotationQuadrantChart<T>({
  benchmark,
  chartSize = DEFAULT_CHART_SIZE,
  emptyLabel = 'No rotation data available.',
  getHistory,
  getItemKey,
  getItemType,
  getLabel,
  getLabelPriority,
  getName,
  getRelativeMomentum,
  getRelativeStrength,
  interval,
  items,
  labelMode: controlledLabelMode,
  maxItems,
  maxSmartLabels,
  onExpand,
  onLabelModeChange,
  onPressItem,
  onQuadrantFilterChange,
  onSelectItem,
  onToggleWatchlist,
  presentation = 'card',
  quadrantFilter: controlledQuadrantFilter,
  selectedItemKey: controlledSelectedItemKey,
  showExpandButton = false,
  showTestDataBadge = false,
  trailLength,
  watchlistKeys,
}: RotationQuadrantChartProps<T>) {
  const [localLabelMode, setLocalLabelMode] = useState<RotationLabelMode>('smart');
  const [localQuadrantFilter, setLocalQuadrantFilter] = useState<RotationQuadrantFilter>('all');
  const [localSelectedItemKey, setLocalSelectedItemKey] = useState<string | null>(null);

  const labelMode = controlledLabelMode ?? localLabelMode;
  const quadrantFilter = controlledQuadrantFilter ?? localQuadrantFilter;
  const selectedItemKey = controlledSelectedItemKey ?? localSelectedItemKey;
  const smartLabelLimit = maxSmartLabels ?? getSmartLabelLimit(chartSize, presentation, maxItems);
  const plotSize = chartSize - PADDING * 2;

  const chartItems = useMemo<ChartItem<T>[]>(() => {
    const mappedItems: ChartItem<T>[] = [];
    items.forEach((item) => {
        const strength = getRelativeStrength(item);
        const momentum = getRelativeMomentum(item);
        if (strength === null || momentum === null) {
          return;
        }

        const normalizedHistory = normalizeHistory(getHistory?.(item), strength, momentum);
        const history = trailLength ? normalizedHistory.slice(-trailLength) : normalizedHistory;
        const latest = history[history.length - 1];
        const fullName = getName(item);
        const type = getItemType?.(item) ?? 'item';
        const id = getItemKey?.(item) ?? `${type}:${fullName.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`;
        const key = id.includes(':') ? id : `${type}:${id}`;

        mappedItems.push({
          color: getBubbleColor(strength, momentum),
          fullName,
          history,
          id,
          item,
          key,
          latest,
          momentum,
          priority: getLabelPriority?.(item) ?? 0,
          shortName: getLabel?.(item) ?? getRotationShortLabel({ name: fullName }),
          strength,
          type,
        });
      });
    return mappedItems;
  }, [getHistory, getItemKey, getItemType, getLabel, getLabelPriority, getName, getRelativeMomentum, getRelativeStrength, items, trailLength]);

  const visibleItems = useMemo<ChartItem<T>[]>(
    () => filterRotationItemsByQuadrant(chartItems, quadrantFilter),
    [chartItems, quadrantFilter],
  );
  const selectedItem = useMemo(
    () => chartItems.find((item) => item.key === selectedItemKey) ?? null,
    [chartItems, selectedItemKey],
  );
  const selectedPoint = selectedItem
    ? {
        chartItem: selectedItem,
        point: selectedItem.latest,
        pointIndex: selectedItem.history.length - 1,
        totalPoints: selectedItem.history.length,
      }
    : null;
  const allPoints = visibleItems.flatMap((item) => item.history);
  const domain = calculateRotationDomain(allPoints);
  const labelKeys = useMemo(
    () =>
      selectSmartLabelKeys(visibleItems, {
        labelMode,
        maxLabelCount: smartLabelLimit,
        selectedItemKey,
        watchlistKeys,
      }),
    [labelMode, selectedItemKey, smartLabelLimit, visibleItems, watchlistKeys],
  );
  const placedLabels = useMemo(
    () => buildPlacedLabels(visibleItems, labelKeys, labelMode, selectedItemKey, domain, plotSize, chartSize),
    [chartSize, domain, labelKeys, labelMode, plotSize, selectedItemKey, visibleItems],
  );
  const summary = selectedItem ? buildRotationTrailSummary(selectedItem.history) : visibleItems.length === 1 ? buildRotationTrailSummary(visibleItems[0].history) : null;

  if (!chartItems.length) {
    return <Text style={styles.emptyText}>{emptyLabel}</Text>;
  }

  const updateLabelMode = (mode: RotationLabelMode) => {
    setLocalLabelMode(mode);
    onLabelModeChange?.(mode);
  };
  const updateQuadrantFilter = (filter: RotationQuadrantFilter) => {
    setLocalQuadrantFilter(filter);
    onQuadrantFilterChange?.(filter);
    if (selectedItemKey && filter !== 'all' && selectedItem && classifyQuadrant(selectedItem.latest.relativeStrength, selectedItem.latest.relativeMomentum) !== filter) {
      updateSelectedItem(null);
    }
  };
  const updateSelectedItem = (itemKey: string | null) => {
    setLocalSelectedItemKey(itemKey);
    onSelectItem?.(itemKey);
  };

  return (
    <View style={styles.wrapper}>
      <View style={styles.chartHeader}>
        <Text style={styles.description}>
          Rotation based on relative strength and momentum vs {benchmark} · {interval}
        </Text>
        {showExpandButton && onExpand ? (
          <Pressable
            accessibilityLabel="Open full-screen rotation chart"
            accessibilityRole="button"
            onPress={onExpand}
            style={({ pressed }) => [styles.expandButton, pressed && styles.pressed]}>
            <Text style={styles.expandText}>Expand</Text>
          </Pressable>
        ) : null}
      </View>

      <View style={styles.controlStack}>
        <SegmentedControl
          label="Labels"
          options={LABEL_MODE_OPTIONS}
          selectedKey={labelMode}
          variant="switch"
          onChange={(value) => updateLabelMode(value as RotationLabelMode)}
        />
        <SegmentedControl
          compact
          label="Quadrant"
          options={QUADRANT_OPTIONS}
          selectedKey={quadrantFilter}
          variant="switch"
          onChange={(value) => updateQuadrantFilter(value as RotationQuadrantFilter)}
        />
      </View>

      {!visibleItems.length ? (
        <Text style={styles.emptyText}>No points match the selected quadrant.</Text>
      ) : (
        <View style={[styles.chart, { height: chartSize, width: chartSize }]}>
          <QuadrantLabels />
          <View style={[styles.verticalAxis, { height: plotSize, left: scaleX(100, domain, plotSize), top: PADDING }]} />
          <View style={[styles.horizontalAxis, { left: PADDING, top: scaleY(100, domain, plotSize), width: plotSize }]} />
          <Text style={[styles.neutralLabel, { left: scaleX(100, domain, plotSize) + 4, top: PADDING + 3 }]}>100 RS</Text>
          <Text style={[styles.neutralLabel, { left: PADDING + 4, top: scaleY(100, domain, plotSize) + 3 }]}>100 Mom</Text>

          {visibleItems.map((item) => (
            <ChartTrail
              domain={domain}
              item={item}
              key={item.key}
              plotSize={plotSize}
              selected={item.key === selectedItemKey}
              selectedItemKey={selectedItemKey}
              onSelect={() => updateSelectedItem(item.key)}
            />
          ))}

          {placedLabels.map(({ item, label, layout, pointX, pointY }) => (
            <RotationLabel
              item={item}
              key={`${item.key}-label`}
              label={label}
              layout={layout}
              onSelect={() => updateSelectedItem(item.key)}
              pointX={pointX}
              pointY={pointY}
              plotSize={plotSize}
              selected={item.key === selectedItemKey}
            />
          ))}

          <Text style={styles.xAxisLabel}>Relative Strength</Text>
          <Text style={styles.yAxisLabel}>Relative Momentum</Text>
        </View>
      )}

      <Text style={styles.helperText}>
        {buildRotationVisibilitySummary({
          filtered: visibleItems.length,
          labels: placedLabels.length,
          mode: labelMode,
          quadrantFilter,
          total: chartItems.length,
        })}
      </Text>
      <Text style={styles.helperText}>Values above 100 outperform the benchmark; momentum above 100 is improving.</Text>

      {labelMode === 'all' ? (
        <Text style={styles.helperText}>All labels are attempted; tap any point when labels compete for space.</Text>
      ) : null}

      {summary ? (
        <View style={styles.summaryCard}>
          <Text style={styles.summaryTitle}>Rotation Summary</Text>
          <Text style={styles.summaryText}>
            {formatQuadrant(summary.startQuadrant)} to {formatQuadrant(summary.currentQuadrant)} · RS {formatSigned(summary.netRelativeStrength)} · Mom{' '}
            {formatSigned(summary.netRelativeMomentum)} · {summary.speed}
          </Text>
        </View>
      ) : null}

      {selectedPoint ? (
        <PointInspector
          benchmark={benchmark}
          interval={interval}
          selectedPoint={selectedPoint}
          showTestDataBadge={showTestDataBadge}
          watchlisted={Boolean(watchlistKeys?.has(selectedPoint.chartItem.key))}
          onOpenDetails={() => onPressItem?.(selectedPoint.chartItem.item)}
          onToggleWatchlist={onToggleWatchlist ? () => onToggleWatchlist(selectedPoint.chartItem.item) : undefined}
        />
      ) : null}
    </View>
  );
}

function ChartTrail<T>({
  domain,
  item,
  onSelect,
  plotSize,
  selected,
  selectedItemKey,
}: {
  domain: RotationDomain;
  item: ChartItem<T>;
  onSelect: () => void;
  plotSize: number;
  selected: boolean;
  selectedItemKey: string | null;
}) {
  const dimmed = selectedItemKey !== null && !selected;
  return (
    <View>
      {item.history.map((point, pointIndex) => {
        const nextPoint = item.history[pointIndex + 1];
        const x = scaleX(point.relativeStrength, domain, plotSize);
        const y = scaleY(point.relativeMomentum, domain, plotSize);
        const isLatest = pointIndex === item.history.length - 1;
        const opacity = selected
          ? isLatest ? 1 : 0.45 + pointIndex / Math.max(item.history.length - 1, 1) * 0.35
          : dimmed
            ? 0.42
            : isLatest
              ? 0.9
              : 0.18 + pointIndex / Math.max(item.history.length - 1, 1) * 0.36;
        const size = isLatest ? (selected ? 20 : 13) : selected ? 7 : 5;
        const touchSize = Math.max(size + 18, 34);

        return (
          <View key={`${item.key}-${point.dateLabel}-${pointIndex}`}>
            {nextPoint ? (
              <View
                style={[
                  styles.trailSegment,
                  getSegmentStyle(
                    x,
                    y,
                    scaleX(nextPoint.relativeStrength, domain, plotSize),
                    scaleY(nextPoint.relativeMomentum, domain, plotSize),
                    item.color,
                    pointIndex,
                    item.history.length,
                    selected,
                    dimmed,
                  ),
                ]}
              />
            ) : null}
            {isLatest && item.history.length > 1 ? (
              <Text
                style={[
                  styles.arrow,
                  getArrowStyle(
                    scaleX(item.history[item.history.length - 2].relativeStrength, domain, plotSize),
                    scaleY(item.history[item.history.length - 2].relativeMomentum, domain, plotSize),
                    x,
                    y,
                    item.color,
                    dimmed,
                  ),
                ]}>
                ›
              </Text>
            ) : null}
            <Pressable
              accessibilityLabel={`${item.fullName} ${item.type}. ${formatQuadrant(classifyQuadrant(point.relativeStrength, point.relativeMomentum))} quadrant. Relative strength ${point.relativeStrength.toFixed(1)}. Relative momentum ${point.relativeMomentum.toFixed(1)}. Tap for details.`}
              accessibilityRole="button"
              onPress={(event) => {
                event.stopPropagation();
                onSelect();
              }}
              style={[
                styles.trailDotButton,
                {
                  height: touchSize,
                  left: x - touchSize / 2,
                  top: y - touchSize / 2,
                  width: touchSize,
                },
              ]}>
              <View
                style={[
                  styles.trailDot,
                  isLatest && styles.latestDot,
                  selected && isLatest && styles.selectedDot,
                  {
                    backgroundColor: item.color,
                    borderColor: selected && isLatest ? Theme.colors.text : isLatest ? Theme.colors.border : item.color,
                    height: size,
                    opacity,
                    width: size,
                  },
                ]}
              />
            </Pressable>
          </View>
        );
      })}
    </View>
  );
}

function RotationLabel<T>({
  item,
  label,
  layout,
  onSelect,
  pointX,
  pointY,
  selected,
}: {
  item: ChartItem<T>;
  label: string;
  layout: PlacedLabel;
  onSelect: () => void;
  pointX: number;
  pointY: number;
  plotSize: number;
  selected: boolean;
}) {
  const labelX = layout.bounds.x + layout.bounds.width / 2;
  const labelY = layout.bounds.y + layout.bounds.height / 2;

  return (
    <>
      {layout.connector ? (
        <View
          style={[
            styles.labelConnector,
            getSegmentStyle(
              pointX,
              pointY,
              labelX,
              labelY,
              selected ? Theme.colors.text : item.color,
              0,
              1,
              selected,
              false,
            ),
            { pointerEvents: 'none' },
          ]}
        />
      ) : null}
      <Pressable
        accessibilityLabel={`Select ${item.fullName}`}
        accessibilityRole="button"
        onPress={onSelect}
        style={[
          styles.pointLabel,
          selected && styles.selectedLabel,
          {
            borderColor: selected ? Theme.colors.text : item.color,
            left: layout.bounds.x,
            top: layout.bounds.y,
            width: layout.bounds.width,
          },
        ]}>
        <Text numberOfLines={1} style={[styles.pointLabelText, selected && styles.selectedLabelText]}>{label}</Text>
      </Pressable>
    </>
  );
}

function PointInspector<T>({
  benchmark,
  interval,
  onOpenDetails,
  onToggleWatchlist,
  selectedPoint,
  showTestDataBadge,
  watchlisted,
}: {
  benchmark: string;
  interval: string;
  onOpenDetails?: () => void;
  onToggleWatchlist?: () => void;
  selectedPoint: SelectedPoint<T>;
  showTestDataBadge: boolean;
  watchlisted: boolean;
}) {
  const quadrant = classifyQuadrant(selectedPoint.point.relativeStrength, selectedPoint.point.relativeMomentum);
  const summary = buildRotationTrailSummary(selectedPoint.chartItem.history);
  const typeLabel = selectedPoint.chartItem.type === 'theme' ? 'Theme' : selectedPoint.chartItem.type === 'sector' ? 'Sector' : 'Item';

  return (
    <View style={styles.inspector}>
      <View style={[styles.inspectorDot, { backgroundColor: selectedPoint.chartItem.color }]} />
      <View style={styles.inspectorContent}>
        <View style={styles.inspectorHeader}>
          <Text style={styles.inspectorTitle}>{selectedPoint.chartItem.fullName} · {selectedPoint.chartItem.shortName}</Text>
          {watchlisted ? <StatusBadge label="Watchlist" tone="info" /> : null}
        </View>
        <View style={styles.inspectorBadgeRow}>
          <StatusBadge label={typeLabel} tone={selectedPoint.chartItem.type === 'theme' ? 'purple' : 'info'} />
          <StatusBadge label={formatQuadrant(quadrant)} tone={getQuadrantTone(quadrant)} />
          {showTestDataBadge ? <TestDataBadge /> : null}
        </View>
        <Text style={styles.inspectorText}>
          Relative Strength {selectedPoint.point.relativeStrength.toFixed(2)} · Relative Momentum {selectedPoint.point.relativeMomentum.toFixed(2)}
        </Text>
        <Text style={styles.inspectorText}>
          {interval} direction {summary ? `${formatSigned(summary.netRelativeStrength)} RS, ${formatSigned(summary.netRelativeMomentum)} Mom` : 'Insufficient snapshot history'} · Benchmark {benchmark}
        </Text>
        {onOpenDetails ? (
          <View style={styles.inspectorActions}>
            {onToggleWatchlist ? (
              <Pressable
                accessibilityLabel={watchlisted ? `Remove ${selectedPoint.chartItem.fullName} from Watchlist` : `Save ${selectedPoint.chartItem.fullName} to Watchlist`}
                accessibilityRole="button"
                onPress={onToggleWatchlist}
                style={({ pressed }) => [styles.watchlistButton, pressed && styles.pressed]}>
                <Text style={styles.watchlistButtonText}>{watchlisted ? 'Remove' : 'Save'}</Text>
              </Pressable>
            ) : null}
            <Pressable
              accessibilityRole="button"
              onPress={onOpenDetails}
              style={({ pressed }) => [styles.openDetailsButton, pressed && styles.pressed]}>
              <Text style={styles.openDetailsText}>Open Details</Text>
            </Pressable>
          </View>
        ) : null}
      </View>
    </View>
  );
}

function buildPlacedLabels<T>(
  items: ChartItem<T>[],
  labelKeys: Set<string>,
  labelMode: RotationLabelMode,
  selectedItemKey: string | null,
  domain: RotationDomain,
  plotSize: number,
  chartSize: number,
) {
  const candidates = [...items]
    .filter((item) => labelKeys.has(item.key))
    .sort((a, b) => {
      if (a.key === selectedItemKey) return -1;
      if (b.key === selectedItemKey) return 1;
      return a.key.localeCompare(b.key);
    });
  const labels: { item: ChartItem<T>; label: string; layout: PlacedLabel; pointX: number; pointY: number }[] = [];
  const placedRects: Rect[] = [];
  const reservedRects: Rect[] = [
    { height: 26, width: 90, x: 0, y: 0 },
    { height: 26, width: 90, x: chartSize - 92, y: 0 },
    { height: 26, width: 90, x: 0, y: chartSize - 28 },
    { height: 26, width: 100, x: chartSize - 104, y: chartSize - 28 },
  ];

  candidates.forEach((item, index) => {
    const selected = item.key === selectedItemKey;
    const pointX = scaleX(item.latest.relativeStrength, domain, plotSize);
    const pointY = scaleY(item.latest.relativeMomentum, domain, plotSize);
    const layout = findAvailableLabelPlacement(
      {
        chartHeight: chartSize,
        chartWidth: chartSize,
        label: selected ? item.fullName : item.shortName,
        pointX,
        pointY,
        selected,
      },
      placedRects,
      reservedRects,
    );
    const fallback = labelMode === 'all' ? fallbackAllLabelLayout(pointX, pointY, index, chartSize) : null;
    if (!layout && !fallback) {
      return;
    }
    labels.push({
      item,
      label: selected ? item.fullName : item.shortName,
      layout: layout ?? fallback!,
      pointX,
      pointY,
    });
    placedRects.push((layout ?? fallback!).bounds);
  });

  return labels;
}

function fallbackAllLabelLayout(pointX: number, pointY: number, index: number, chartSize: number): PlacedLabel {
  const width = 52;
  const height = 17;
  const column = index % 2 === 0 ? 12 : -width - 12;
  const row = (Math.floor(index / 2) % 3 - 1) * 19;
  return {
    bounds: {
      height,
      width,
      x: Math.max(4, Math.min(pointX + column, chartSize - width - 4)),
      y: Math.max(30, Math.min(pointY + row, chartSize - height - 30)),
    },
    connector: true,
    placement: index % 2 === 0 ? 'right' : 'left',
  };
}

function normalizeHistory(history: ChartRotationPoint[] | undefined, strength: number, momentum: number): ChartRotationPoint[] {
  const validHistory = (history ?? [])
    .filter((point) => Number.isFinite(point.relativeStrength) && Number.isFinite(point.relativeMomentum))
    .map((point, index) => ({
      ...point,
      dateLabel: point.dateLabel ?? point.date ?? (index === (history?.length ?? 0) - 1 ? 'Current' : `Point ${index + 1}`),
    }));
  if (validHistory.length) {
    return validHistory;
  }
  return [{ dateLabel: 'Current', relativeMomentum: momentum, relativeStrength: strength }];
}

function QuadrantLabels() {
  return (
    <>
      <Text style={[styles.quadrantLabel, styles.improving]}>Improving</Text>
      <Text style={[styles.quadrantLabel, styles.leading]}>Leading</Text>
      <Text style={[styles.quadrantLabel, styles.lagging]}>Lagging</Text>
      <Text style={[styles.quadrantLabel, styles.weakening]}>Weakening</Text>
    </>
  );
}

function scaleX(value: number, domain: RotationDomain, plotSize: number) {
  const percent = (clamp(value, domain.xMin, domain.xMax) - domain.xMin) / Math.max(domain.xMax - domain.xMin, 1);
  return PADDING + percent * plotSize;
}

function scaleY(value: number, domain: RotationDomain, plotSize: number) {
  const percent = (clamp(value, domain.yMin, domain.yMax) - domain.yMin) / Math.max(domain.yMax - domain.yMin, 1);
  return PADDING + (1 - percent) * plotSize;
}

function getBubbleColor(strength: number, momentum: number) {
  if (strength >= 100 && momentum >= 100) {
    return Theme.colors.success;
  }
  if (strength >= 100) {
    return Theme.colors.warning;
  }
  if (momentum >= 100) {
    return Theme.colors.accent;
  }
  return Theme.colors.danger;
}

function getSegmentStyle(x1: number, y1: number, x2: number, y2: number, color: string, index: number, total: number, selected = false, dimmed = false) {
  const length = Math.hypot(x2 - x1, y2 - y1);
  const angle = `${Math.atan2(y2 - y1, x2 - x1)}rad`;
  const ageOpacity = selected ? 0.62 : dimmed ? 0.14 : 0.16 + (index / Math.max(total - 1, 1)) * 0.42;

  return {
    backgroundColor: color,
    left: x1,
    opacity: ageOpacity,
    top: y1,
    transform: [{ rotate: angle }],
    width: length,
  };
}

function getArrowStyle(x1: number, y1: number, x2: number, y2: number, color: string, dimmed: boolean) {
  const angle = `${Math.atan2(y2 - y1, x2 - x1)}rad`;
  return {
    color,
    left: x2 - 2,
    opacity: dimmed ? 0.35 : 0.9,
    top: y2 - 12,
    transform: [{ rotate: angle }],
  };
}

function getSmartLabelLimit(chartSize: number, presentation: 'card' | 'fullscreen', legacyMax?: number) {
  if (presentation === 'fullscreen') {
    return chartSize >= 420 ? 15 : 12;
  }
  if (legacyMax && legacyMax < 12) {
    return Math.max(6, legacyMax);
  }
  return chartSize < 310 ? 6 : 8;
}

function getQuadrantTone(quadrant: RotationQuadrant): Tone {
  switch (quadrant) {
    case 'leading':
      return 'success';
    case 'weakening':
      return 'warning';
    case 'improving':
      return 'info';
    case 'lagging':
      return 'danger';
  }
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

function formatSigned(value: number) {
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}`;
}

const styles = StyleSheet.create({
  arrow: {
    fontSize: 22,
    fontWeight: '900',
    position: 'absolute',
    zIndex: 4,
  },
  chart: {
    alignSelf: 'center',
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    overflow: 'hidden',
  },
  chartHeader: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  controlStack: {
    gap: Spacing.two,
  },
  description: {
    color: Theme.colors.textMuted,
    flex: 1,
    fontSize: 12,
    fontWeight: '700',
    lineHeight: 17,
  },
  emptyText: {
    color: Theme.colors.textMuted,
    fontSize: 14,
    fontWeight: '700',
  },
  expandButton: {
    alignItems: 'center',
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    minHeight: 34,
    paddingHorizontal: Spacing.twoAndHalf,
    paddingVertical: Spacing.one,
  },
  expandText: {
    color: Theme.colors.accent,
    fontSize: 11,
    fontWeight: '900',
  },
  helperText: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '700',
  },
  horizontalAxis: {
    backgroundColor: Theme.colors.border,
    height: 1,
    position: 'absolute',
  },
  improving: {
    left: Spacing.two,
    top: Spacing.two,
  },
  inspector: {
    alignItems: 'flex-start',
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    flexDirection: 'row',
    gap: Spacing.two,
    padding: Spacing.twoAndHalf,
  },
  inspectorBadgeRow: {
    alignItems: 'center',
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.one,
  },
  inspectorContent: {
    flex: 1,
    gap: Spacing.one,
  },
  inspectorDot: {
    borderRadius: 5,
    height: 10,
    marginTop: 4,
    width: 10,
  },
  inspectorHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  inspectorActions: {
    alignItems: 'center',
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
    marginTop: Spacing.one,
  },
  inspectorText: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '700',
    lineHeight: 16,
  },
  inspectorTitle: {
    color: Theme.colors.text,
    flex: 1,
    fontSize: 13,
    fontWeight: '900',
  },
  labelConnector: {
    height: 1,
    position: 'absolute',
    transformOrigin: 'left center',
    zIndex: 5,
  },
  lagging: {
    bottom: Spacing.two,
    left: Spacing.two,
  },
  latestDot: {
    borderRadius: 99,
    borderWidth: 2,
  },
  leading: {
    right: Spacing.two,
    top: Spacing.two,
  },
  neutralLabel: {
    color: Theme.colors.textMuted,
    fontSize: 9,
    fontWeight: '900',
    opacity: 0.75,
    position: 'absolute',
  },
  openDetailsButton: {
    alignItems: 'center',
    alignSelf: 'flex-start',
    backgroundColor: Theme.colors.accentSoft,
    borderColor: Theme.colors.accent,
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    minHeight: 34,
    paddingHorizontal: Spacing.twoAndHalf,
    paddingVertical: Spacing.one,
  },
  openDetailsText: {
    color: Theme.colors.accent,
    fontSize: 11,
    fontWeight: '900',
  },
  pointLabel: {
    backgroundColor: Theme.colors.card,
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    paddingHorizontal: Spacing.two,
    paddingVertical: Spacing.one,
    position: 'absolute',
    textAlign: 'center',
    zIndex: 7,
  },
  pointLabelText: {
    color: Theme.colors.textMuted,
    fontSize: 10,
    fontWeight: '900',
    textAlign: 'center',
  },
  pressed: {
    opacity: 0.78,
  },
  quadrantLabel: {
    color: Theme.colors.textMuted,
    fontSize: 10,
    fontWeight: '900',
    letterSpacing: 0,
    position: 'absolute',
    textTransform: 'uppercase',
    zIndex: 1,
  },
  selectedDot: {
    shadowColor: Theme.colors.text,
    shadowOpacity: 0.4,
    shadowRadius: 7,
  },
  selectedLabel: {
    backgroundColor: Theme.colors.cardElevated,
  },
  selectedLabelText: {
    color: Theme.colors.text,
    fontSize: 11,
  },
  summaryCard: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    gap: Spacing.one,
    padding: Spacing.twoAndHalf,
  },
  summaryText: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '800',
    lineHeight: 17,
  },
  summaryTitle: {
    color: Theme.colors.text,
    fontSize: 13,
    fontWeight: '900',
  },
  trailDot: {
    borderRadius: 99,
  },
  trailDotButton: {
    alignItems: 'center',
    justifyContent: 'center',
    position: 'absolute',
    zIndex: 6,
  },
  trailSegment: {
    height: 2,
    position: 'absolute',
    transformOrigin: 'left center',
    zIndex: 2,
  },
  verticalAxis: {
    backgroundColor: Theme.colors.border,
    position: 'absolute',
    width: 1,
  },
  watchlistButton: {
    alignItems: 'center',
    backgroundColor: Theme.colors.card,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    minHeight: 34,
    paddingHorizontal: Spacing.twoAndHalf,
    paddingVertical: Spacing.one,
  },
  watchlistButtonText: {
    color: Theme.colors.text,
    fontSize: 11,
    fontWeight: '900',
  },
  weakening: {
    bottom: Spacing.two,
    right: Spacing.two,
  },
  wrapper: {
    gap: Spacing.two,
  },
  xAxisLabel: {
    bottom: Spacing.one,
    color: Theme.colors.textMuted,
    fontSize: 10,
    fontWeight: '900',
    left: 0,
    position: 'absolute',
    right: 0,
    textAlign: 'center',
  },
  yAxisLabel: {
    color: Theme.colors.textMuted,
    fontSize: 10,
    fontWeight: '900',
    left: -28,
    position: 'absolute',
    top: '46%',
    transform: [{ rotate: '-90deg' }],
  },
});
