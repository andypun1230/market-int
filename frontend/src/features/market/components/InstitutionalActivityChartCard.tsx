import { useEffect, useMemo, useState } from 'react';
import type { GestureResponderEvent } from 'react-native';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { StatusBadge, type Tone } from '@/components/ui/StatusBadge';
import { Spacing, Theme } from '@/constants/theme';
import {
  buildInstitutionalActivityChartViewModel,
  institutionalChartHistoryDays,
  institutionalChartIndexes,
  institutionalChartTimeframes,
  institutionalEventFilters,
  type InstitutionalActivityChartViewModel,
  type InstitutionalChartIndex,
  type InstitutionalChartTimeframe,
  type InstitutionalCandleViewModel,
  type InstitutionalEventFilter,
  type InstitutionalEventType,
  type InstitutionalGroupedMarker,
  formatInstitutionalChartWindow,
} from '@/features/market/institutionalActivityChart';
import { getLiveHistory } from '@/services/api';
import type { FollowThroughDay, HistoryData } from '@/types/market';

const PRICE_HEIGHT = 170;
const VOLUME_HEIGHT = 54;
const CHART_HEIGHT = PRICE_HEIGHT + VOLUME_HEIGHT + 30;
const CHART_LEFT = 28;
const CHART_RIGHT = 56;
const CHART_TOP = 18;
const VOLUME_TOP = PRICE_HEIGHT + 22;

type MappedCandle = InstitutionalCandleViewModel & {
  bodyHeight: number;
  bodyTop: number;
  candleWidth: number;
  closeY: number;
  highY: number;
  lowY: number;
  openY: number;
  volumeHeight: number;
  volumeAverageY: number | null;
  x: number;
};

type HistoryState = {
  price: HistoryData | null;
  volume: HistoryData | null;
};

export function InstitutionalActivityChartCard({ followThroughDay }: { followThroughDay?: FollowThroughDay | null }) {
  const [selectedIndex, setSelectedIndex] = useState<InstitutionalChartIndex>('SPX');
  const [timeframe, setTimeframe] = useState<InstitutionalChartTimeframe>('3M');
  const [filter, setFilter] = useState<InstitutionalEventFilter>('all');
  const [histories, setHistories] = useState<HistoryState>({ price: null, volume: null });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const volumeSymbol = selectedIndex === 'SPX' ? 'SPY' : 'QQQ';
    const priceSymbol = selectedIndex;
    Promise.resolve()
      .then(async () => {
        if (cancelled) {
          return null;
        }
        setLoading(true);
        setError(null);
        const days = institutionalChartHistoryDays[timeframe];
        const [priceResult, volumeResult] = await Promise.allSettled([
          getLiveHistory(priceSymbol, 'D', days),
          getLiveHistory(volumeSymbol, 'D', days),
        ]);
        const volume = volumeResult.status === 'fulfilled' ? volumeResult.value : null;
        return {
          price: priceResult.status === 'fulfilled' ? priceResult.value : volume,
          volume,
          failed: priceResult.status === 'rejected' && volumeResult.status === 'rejected',
        };
      })
      .then((next) => {
        if (!next || cancelled) {
          return;
        }
        setHistories({ price: next.price, volume: next.volume });
        setError(next.failed ? 'Institutional activity history unavailable.' : null);
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [selectedIndex, timeframe]);

  const model = useMemo(
    () => buildInstitutionalActivityChartViewModel({
      filter,
      followThroughDay,
      index: selectedIndex,
      priceHistory: histories.price,
      timeframe,
      volumeHistory: histories.volume,
    }),
    [filter, followThroughDay, histories.price, histories.volume, selectedIndex, timeframe],
  );

  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <View style={styles.titleBlock}>
          <Text style={styles.title}>Institutional Activity Chart</Text>
          <Text style={styles.subtitle}>{model.priceScale.label} · {model.source.volumeLabel} volume proxy</Text>
        </View>
        <StatusBadge label={model.dataQuality.sourceLabel} tone={sourceTone(model.source.sourceKind)} />
      </View>

      <SelectorRow
        items={institutionalChartIndexes}
        selected={selectedIndex}
        onChange={(value) => setSelectedIndex(value as InstitutionalChartIndex)}
      />
      <SelectorRow
        items={institutionalChartTimeframes}
        selected={timeframe}
        onChange={(value) => setTimeframe(value as InstitutionalChartTimeframe)}
      />

      <InstitutionalSummary model={model} />
      {loading ? <Text style={styles.helperText}>Updating institutional chart…</Text> : null}
      {error ? <Text style={styles.warningText}>{error}</Text> : null}
      <EventFilterRow selected={filter} onChange={setFilter} />
      <CandlestickChart model={model} />
      <MethodologyDisclosure model={model} />
    </View>
  );
}

function SelectorRow<T extends string>({ items, onChange, selected }: { items: readonly T[]; onChange: (value: T) => void; selected: T }) {
  return (
    <View style={styles.selectorRow}>
      {items.map((item) => {
        const active = item === selected;
        return (
          <Pressable
            accessibilityRole="button"
            accessibilityState={{ selected: active }}
            key={item}
            onPress={() => onChange(item)}
            style={({ pressed }) => [
              styles.selectorButton,
              active && styles.selectorButtonActive,
              pressed && styles.pressed,
            ]}>
            <Text style={[styles.selectorText, active && styles.selectorTextActive]}>{item}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

function InstitutionalSummary({ model }: { model: InstitutionalActivityChartViewModel }) {
  const { summary } = model;
  const windowLabel = formatInstitutionalChartWindow(model.chartWindow.startDate, model.chartWindow.endDate);
  return (
    <View style={styles.summaryBox}>
      <View style={styles.summaryHeader}>
        <View>
          <Text style={styles.summaryTitle}>{model.selectedIndex} Institutional Activity</Text>
          <Text style={styles.helperText}>
            {model.timeframe} · {filterSummaryText(model)}
          </Text>
          {windowLabel ? <Text style={styles.helperText}>Window: {windowLabel}</Text> : null}
        </View>
        <StatusBadge label={summary.bias} tone={summaryTone(summary.bias)} />
      </View>
      <View style={styles.summaryMetricRow}>
        <Metric label="Accumulation" value={`${summary.accumulationCount}`} />
        <Metric label="Distribution" value={`${summary.distributionCount}`} />
        <Metric label="FTD" value={`${summary.followThroughCount}`} />
        <Metric label="Net Activity" value={summary.netActivity === null ? 'N/A' : `${summary.netActivity >= 0 ? '+' : ''}${summary.netActivity.toFixed(1)}`} />
      </View>
      {summary.stallCount || summary.churningCount ? (
        <Text style={styles.helperText}>Stall {summary.stallCount} · Churning {summary.churningCount}</Text>
      ) : null}
      <NetActivityGauge value={summary.netActivity} />
      <Text style={styles.bodyText}>{summary.interpretation}</Text>
    </View>
  );
}

function NetActivityGauge({ value }: { value: number | null }) {
  const markerPercent = value === null ? 50 : clamp(50 + value * 8, 4, 96);
  return (
    <View style={styles.netGaugeBlock}>
      <View style={styles.netGaugeLabels}>
        <Text style={styles.helperText}>Distribution</Text>
        <Text style={styles.helperText}>Neutral</Text>
        <Text style={styles.helperText}>Accumulation</Text>
      </View>
      <View style={styles.netGaugeTrack}>
        <View style={styles.netGaugeCenter} />
        <View style={[styles.netGaugeMarker, { left: `${markerPercent}%` }]} />
      </View>
    </View>
  );
}

function EventFilterRow({ onChange, selected }: { onChange: (filter: InstitutionalEventFilter) => void; selected: InstitutionalEventFilter }) {
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.filterRow}>
      {institutionalEventFilters.map((filter) => {
        const active = selected === filter;
        return (
          <Pressable
            accessibilityRole="button"
            accessibilityState={{ selected: active }}
            key={filter}
            onPress={() => onChange(filter)}
            style={({ pressed }) => [
              styles.filterButton,
              active && styles.filterButtonActive,
              pressed && styles.pressed,
            ]}>
            <Text style={[styles.filterText, active && styles.filterTextActive]}>{eventFilterLabel(filter)}</Text>
          </Pressable>
        );
      })}
    </ScrollView>
  );
}

function CandlestickChart({ model }: { model: InstitutionalActivityChartViewModel }) {
  const [width, setWidth] = useState(0);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const mapped = useMemo(() => mapCandles(model.candles, width), [model.candles, width]);
  const selected = selectedIndex === null ? null : mapped[selectedIndex] ?? null;

  function handlePress(event: GestureResponderEvent) {
    if (!mapped.length) {
      return;
    }
    const x = event.nativeEvent.locationX;
    const nearest = mapped.reduce((best, candle) => Math.abs(candle.x - x) < Math.abs(best.x - x) ? candle : best, mapped[0]);
    setSelectedIndex(mapped.findIndex((candle) => candle.dateKey === nearest.dateKey));
  }

  if (!model.candles.length) {
    return (
      <View style={styles.emptyChart}>
        <Text style={styles.emptyTitle}>Institutional chart unavailable</Text>
        <Text style={styles.helperText}>{model.dataQuality.message}</Text>
      </View>
    );
  }

  return (
    <Pressable
      accessibilityLabel={`${model.selectedIndex} institutional price-volume candlestick chart`}
      accessibilityRole="summary"
      onLayout={(event) => setWidth(event.nativeEvent.layout.width)}
      onPressIn={handlePress}
      onPressOut={() => setSelectedIndex(null)}
      style={styles.chartBox}>
      {width > 0 ? (
        <>
          <PriceAxis model={model} />
          {mapped.map((candle) => <Candle key={candle.dateKey} candle={candle} selected={selected?.dateKey === candle.dateKey} />)}
          <EmaLine candles={mapped} field="ema20" color={Theme.colors.accent} />
          <EmaLine candles={mapped} field="ema50" color={Theme.colors.purple} />
          {mapped.map((candle) => <VolumeBar key={`${candle.dateKey}-volume`} candle={candle} selected={selected?.dateKey === candle.dateKey} />)}
          <VolumeAverageLine candles={mapped} />
          {model.groupedMarkers.map((marker, index) => {
            const candle = mapped.find((item) => item.dateKey === marker.dateKey);
            return candle ? <EventMarker candle={candle} key={`${marker.dateKey}-${marker.type}`} marker={marker} offset={index} /> : null;
          })}
          {selected ? (
            <>
              <View style={[styles.crosshair, { left: selected.x }]} />
              <ChartTooltip candle={selected} events={model.allEvents.filter((event) => event.date === selected.dateKey)} priceLabel={model.priceScale.symbol} source={model.source.volumeLabel} width={width} />
            </>
          ) : null}
          <Text style={[styles.axisDateLabel, { left: CHART_LEFT }]}>{formatShortDate(mapped[0]?.timestamp)}</Text>
          <Text style={[styles.axisDateLabel, { right: CHART_RIGHT }]}>{formatShortDate(mapped.at(-1)?.timestamp)}</Text>
        </>
      ) : null}
      <View style={styles.legendRow}>
        <LegendDot color={Theme.colors.success} label="Up candle" />
        <LegendDot color={Theme.colors.danger} label="Down candle" />
        <LegendDot color={Theme.colors.accent} label="EMA20" />
        <LegendDot color={Theme.colors.purple} label="EMA50" />
      </View>
      <EventLegend model={model} />
    </Pressable>
  );
}

function Candle({ candle, selected }: { candle: MappedCandle; selected: boolean }) {
  const up = candle.close >= candle.open;
  const color = up ? Theme.colors.success : Theme.colors.danger;
  return (
    <>
      <View style={[styles.wick, { backgroundColor: color, height: Math.max(1, candle.lowY - candle.highY), left: candle.x, top: candle.highY }]} />
      <View
        style={[
          styles.candleBody,
          selected && styles.selectedCandle,
          {
            backgroundColor: up ? 'rgba(34, 197, 94, 0.36)' : 'rgba(248, 113, 113, 0.34)',
            borderColor: color,
            height: candle.bodyHeight,
            left: candle.x - candle.candleWidth / 2,
            top: candle.bodyTop,
            width: candle.candleWidth,
          },
        ]}
      />
    </>
  );
}

function VolumeBar({ candle, selected }: { candle: MappedCandle; selected: boolean }) {
  const up = candle.close > candle.open;
  const down = candle.close < candle.open;
  return (
    <View
      style={[
        styles.volumeBar,
        up && styles.volumeBarUp,
        down && styles.volumeBarDown,
        candle.volumeChangePct !== null && Math.abs(candle.volumeChangePct) > 20 && styles.volumeBarEvent,
        selected && styles.selectedVolumeBar,
        {
          height: candle.volumeHeight,
          left: candle.x - candle.candleWidth / 2,
          top: VOLUME_TOP + VOLUME_HEIGHT - candle.volumeHeight,
          width: candle.candleWidth,
        },
      ]}
    />
  );
}

function VolumeAverageLine({ candles }: { candles: MappedCandle[] }) {
  const points = candles.filter((candle) => candle.volumeAverageY !== null);
  return (
    <>
      {points.map((point, index) => {
        const prior = points[index - 1];
        if (!prior || point.volumeAverageY === null || prior.volumeAverageY === null) {
          return null;
        }
        return (
          <LineSegment
            color="rgba(148, 163, 184, 0.66)"
            end={{ x: point.x, y: point.volumeAverageY }}
            key={`volume-average-${point.dateKey}`}
            start={{ x: prior.x, y: prior.volumeAverageY }}
          />
        );
      })}
    </>
  );
}

function EmaLine({ candles, color, field }: { candles: MappedCandle[]; color: string; field: 'ema20' | 'ema50' }) {
  const points = candles.filter((candle) => candle[field] !== null);
  return (
    <>
      {points.map((point, index) => {
        const prior = points[index - 1];
        if (!prior || point[field] === null || prior[field] === null) {
          return null;
        }
        return (
          <LineSegment
            color={color}
            end={{ x: point.x, y: priceToY(point[field] ?? 0, candles) }}
            key={`${field}-${point.dateKey}`}
            start={{ x: prior.x, y: priceToY(prior[field] ?? 0, candles) }}
          />
        );
      })}
    </>
  );
}

function EventMarker({ candle, marker, offset }: { candle: MappedCandle; marker: InstitutionalGroupedMarker; offset: number }) {
  const above = marker.position === 'above';
  const label = marker.count > 1 && marker.type !== 'follow_through'
    ? `${eventLabel(marker.type)}×${marker.count}`
    : eventLabel(marker.type);
  const lane = offset % 3;
  const top = above
    ? clamp(candle.highY - 24 - lane * 13, 3, PRICE_HEIGHT - 26)
    : clamp(candle.lowY + 8 + lane * 13, 3, PRICE_HEIGHT - 20);
  return (
    <View style={[styles.eventMarker, marker.type === 'follow_through' && styles.eventMarkerFtd, eventMarkerStyle(marker.type), { left: clamp(candle.x - (marker.type === 'follow_through' ? 16 : 10), CHART_LEFT, Number.MAX_SAFE_INTEGER), top }]}>
      <Text style={styles.eventMarkerText}>{label}</Text>
    </View>
  );
}

function ChartTooltip({ candle, events, priceLabel, source, width }: { candle: MappedCandle; events: InstitutionalActivityChartViewModel['events']; priceLabel: string; source: string; width: number }) {
  const tooltipWidth = 196;
  const left = clamp(candle.x - tooltipWidth / 2, 8, Math.max(8, width - tooltipWidth - 8));
  const primary = [...events].sort((a, b) => eventPriorityForTooltip(a.type) - eventPriorityForTooltip(b.type))[0] ?? null;
  return (
    <View style={[styles.tooltip, { left, top: clamp(candle.closeY - 112, 8, PRICE_HEIGHT - 116), width: tooltipWidth }]}>
      <Text style={styles.tooltipTitle}>{formatDate(candle.timestamp)}</Text>
      <Text style={styles.tooltipLine}>{priceLabel}</Text>
      <Text style={styles.tooltipLine}>O {formatPrice(candle.open)} · H {formatPrice(candle.high)}</Text>
      <Text style={styles.tooltipLine}>L {formatPrice(candle.low)} · C {formatPrice(candle.close)}</Text>
      {candle.priceChangePct !== null ? <Text style={styles.tooltipLine}>Return {formatSignedPercent(candle.priceChangePct)}</Text> : null}
      {candle.proxyVolume !== null ? <Text style={styles.tooltipLine}>{source} volume {formatCompactVolume(candle.proxyVolume)}</Text> : null}
      {candle.volumeChangePct !== null ? <Text style={styles.tooltipLine}>Volume {formatSignedPercent(candle.volumeChangePct)} vs prior</Text> : null}
      {candle.volumeRatio20 !== null ? <Text style={styles.tooltipLine}>Volume {candle.volumeRatio20.toFixed(2)}× 20-day avg</Text> : null}
      {candle.ema20 !== null ? <Text style={styles.tooltipLine}>EMA20 {formatPrice(candle.ema20)}</Text> : null}
      {candle.ema50 !== null ? <Text style={styles.tooltipLine}>EMA50 {formatPrice(candle.ema50)}</Text> : null}
      {primary ? <Text style={styles.tooltipPrimary}>{eventName(primary.type)}</Text> : null}
      {events.map((event) => (
        <Text key={`${event.date}-${event.type}`} style={styles.tooltipEvent}>{eventName(event.type)}: {event.reason}</Text>
      ))}
    </View>
  );
}

function MethodologyDisclosure({ model }: { model: InstitutionalActivityChartViewModel }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <View style={styles.disclosure}>
      <Pressable
        accessibilityRole="button"
        accessibilityState={{ expanded }}
        onPress={() => setExpanded((value) => !value)}
        style={({ pressed }) => [styles.disclosureHeader, pressed && styles.pressed]}>
        <View>
          <Text style={styles.disclosureTitle}>How institutional days are classified</Text>
          <Text style={styles.helperText}>{model.dataQuality.message}</Text>
        </View>
        <Text style={styles.chevron}>{expanded ? '−' : '+'}</Text>
      </Pressable>
      {expanded ? (
        <View style={styles.disclosureBody}>
          <Text style={styles.helperText}>Price instrument: {model.source.priceLabel}</Text>
          <Text style={styles.helperText}>Volume proxy: {model.source.volumeLabel} ETF volume</Text>
          <Text style={styles.helperText}>Accumulation proxy: price up at least 0.3%, stronger proxy volume, constructive close location, and minimum event-quality score.</Text>
          <Text style={styles.helperText}>Distribution proxy: price down at least 0.2% on higher proxy volume.</Text>
          <Text style={styles.helperText}>FTD uses the shared follow-through date when available, plus a conservative price-volume proxy.</Text>
          <Text style={styles.helperText}>Stall and churning are deterministic price-volume proxies, not verified institutional identity.</Text>
        </View>
      ) : null}
    </View>
  );
}

function PriceAxis({ model }: { model: InstitutionalActivityChartViewModel }) {
  return (
    <>
      {model.priceTicks.map((value) => (
        <View key={value} style={[styles.gridLine, { top: priceToY(value, model.candles) }]}>
          <Text style={styles.yAxisLabel}>{formatPrice(value)}</Text>
        </View>
      ))}
    </>
  );
}

function LineSegment({ color, end, start }: { color: string; end: { x: number; y: number }; start: { x: number; y: number } }) {
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  const length = Math.sqrt(dx * dx + dy * dy);
  const angle = Math.atan2(dy, dx);
  return (
    <View
      style={[
        styles.emaSegment,
        {
          backgroundColor: color,
          left: (start.x + end.x) / 2 - length / 2,
          top: (start.y + end.y) / 2,
          transform: [{ rotateZ: `${angle}rad` }],
          width: length,
        },
      ]}
    />
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.metric}>
      <Text style={styles.metricLabel}>{label}</Text>
      <Text style={styles.metricValue}>{value}</Text>
    </View>
  );
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <View style={styles.legendItem}>
      <View style={[styles.legendDot, { backgroundColor: color }]} />
      <Text style={styles.legendText}>{label}</Text>
    </View>
  );
}

function EventLegend({ model }: { model: InstitutionalActivityChartViewModel }) {
  const present = new Set(model.displayedEvents.map((event) => event.type));
  const allTypes: InstitutionalEventType[] = ['accumulation', 'distribution', 'follow_through', 'stall', 'churning'];
  const legendTypes = allTypes
    .filter((type) => present.has(type) || type === 'accumulation' || type === 'distribution' || type === 'follow_through');
  return (
    <View style={styles.eventLegendRow}>
      {legendTypes.map((type) => (
        <View key={type} style={styles.legendItem}>
          <View style={[styles.eventLegendMarker, eventMarkerStyle(type)]}>
            <Text style={styles.eventLegendMarkerText}>{eventLabel(type)}</Text>
          </View>
          <Text style={styles.legendText}>{eventName(type).replace(' Day', '')}</Text>
        </View>
      ))}
    </View>
  );
}

function mapCandles(candles: InstitutionalCandleViewModel[], width: number): MappedCandle[] {
  if (width <= 0 || !candles.length) {
    return [];
  }
  const prices = candles.flatMap((candle) => [candle.high, candle.low, candle.ema20, candle.ema50]).filter(isNumber);
  const maxPrice = Math.max(...prices);
  const minPrice = Math.min(...prices);
  const maxVolume = Math.max(...candles.map((candle) => candle.proxyVolume ?? 0), 1);
  const plotWidth = Math.max(1, width - CHART_LEFT - CHART_RIGHT);
  const candleWidth = clamp(plotWidth / Math.max(candles.length, 1) * 0.58, 3, 9);
  return candles.map((candle, index) => {
    const x = CHART_LEFT + (index / Math.max(candles.length - 1, 1)) * plotWidth;
    const openY = scalePrice(candle.open, minPrice, maxPrice);
    const closeY = scalePrice(candle.close, minPrice, maxPrice);
    const highY = scalePrice(candle.high, minPrice, maxPrice);
    const lowY = scalePrice(candle.low, minPrice, maxPrice);
    return {
      ...candle,
      bodyHeight: Math.max(2, Math.abs(closeY - openY)),
      bodyTop: Math.min(openY, closeY),
      candleWidth,
      closeY,
      highY,
      lowY,
      openY,
      volumeHeight: candle.proxyVolume ? Math.max(2, (candle.proxyVolume / maxVolume) * VOLUME_HEIGHT) : 0,
      volumeAverageY: candle.volumeAverage20 ? VOLUME_TOP + VOLUME_HEIGHT - (candle.volumeAverage20 / maxVolume) * VOLUME_HEIGHT : null,
      x,
    };
  });
}

function priceToY(value: number, candles: InstitutionalCandleViewModel[]) {
  const prices = candles.flatMap((candle) => [candle.high, candle.low, candle.ema20, candle.ema50]).filter(isNumber);
  return scalePrice(value, Math.min(...prices), Math.max(...prices));
}

function scalePrice(value: number, min: number, max: number) {
  const padding = Math.max(0.01, (max - min) * 0.08);
  const domainMin = min - padding;
  const domainMax = max + padding;
  return CHART_TOP + ((domainMax - value) / Math.max(0.01, domainMax - domainMin)) * (PRICE_HEIGHT - CHART_TOP - 10);
}

function summaryTone(bias: InstitutionalActivityChartViewModel['summary']['bias']): Tone {
  if (bias === 'Accumulation') {
    return 'success';
  }
  if (bias === 'Distribution') {
    return 'danger';
  }
  if (bias === 'Mixed') {
    return 'warning';
  }
  return 'muted';
}

function sourceTone(source: string): Tone {
  if (source === 'live') {
    return 'success';
  }
  if (source === 'fallback' || source === 'mock' || source === 'test') {
    return 'warning';
  }
  if (source === 'unavailable') {
    return 'muted';
  }
  return 'info';
}

function eventMarkerStyle(type: InstitutionalEventType) {
  switch (type) {
    case 'accumulation':
      return styles.markerAccumulation;
    case 'distribution':
      return styles.markerDistribution;
    case 'follow_through':
      return styles.markerFollowThrough;
    case 'stall':
      return styles.markerStall;
    case 'churning':
      return styles.markerChurning;
  }
}

function eventLabel(type: InstitutionalEventType) {
  switch (type) {
    case 'accumulation':
      return 'A';
    case 'distribution':
      return 'D';
    case 'follow_through':
      return 'FTD';
    case 'stall':
      return 'S';
    case 'churning':
      return 'C';
  }
}

function eventName(type: InstitutionalEventType) {
  switch (type) {
    case 'accumulation':
      return 'Accumulation Day';
    case 'distribution':
      return 'Distribution Day';
    case 'follow_through':
      return 'Follow-Through Day';
    case 'stall':
      return 'Stall Day';
    case 'churning':
      return 'Churning Day';
  }
}

function eventFilterLabel(filter: InstitutionalEventFilter) {
  switch (filter) {
    case 'all':
      return 'All';
    case 'accumulation':
      return 'A';
    case 'distribution':
      return 'D';
    case 'follow_through':
      return 'FTD';
    case 'stall':
      return 'S';
    case 'churning':
      return 'C';
  }
}

function filterSummaryText(model: InstitutionalActivityChartViewModel) {
  const total = model.summary.totalClassifiedSignals;
  const displayed = model.summary.totalDisplayedMarkers;
  if (model.hiddenEventCount > 0) {
    return `${total} signals · ${displayed} displayed`;
  }
  if (model.visibleEvents.length !== model.allEvents.length) {
    return `${model.visibleEvents.length} ${eventFilterLabel(model.visibleEvents[0]?.type ?? 'all')} signals · ${displayed} displayed`;
  }
  return `${total} institutional signal${total === 1 ? '' : 's'}`;
}

function eventPriorityForTooltip(type: InstitutionalEventType) {
  switch (type) {
    case 'follow_through':
      return 1;
    case 'distribution':
      return 2;
    case 'accumulation':
      return 3;
    case 'stall':
      return 4;
    case 'churning':
      return 5;
  }
}

function formatShortDate(timestamp?: string) {
  if (!timestamp) {
    return '';
  }
  const date = new Date(timestamp);
  return Number.isNaN(date.getTime()) ? timestamp.slice(5, 10) : date.toLocaleDateString('en-US', { day: 'numeric', month: 'short' });
}

function formatDate(timestamp: string) {
  const date = new Date(timestamp);
  return Number.isNaN(date.getTime()) ? timestamp : date.toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' });
}

function formatPrice(value: number) {
  return value >= 1000 ? value.toFixed(0) : value.toFixed(2);
}

function formatSignedPercent(value: number) {
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
}

function formatCompactVolume(value: number) {
  if (value >= 1_000_000_000) {
    return `${(value / 1_000_000_000).toFixed(1)}B`;
  }
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)}M`;
  }
  return value.toFixed(0);
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

function isNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

const styles = StyleSheet.create({
  axisDateLabel: {
    bottom: 2,
    color: Theme.colors.textMuted,
    fontSize: 10,
    fontWeight: '800',
    position: 'absolute',
  },
  bodyText: {
    color: Theme.colors.text,
    fontSize: 12,
    fontWeight: '700',
    lineHeight: 18,
  },
  candleBody: {
    borderRadius: 2,
    borderWidth: 1,
    position: 'absolute',
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
  chevron: {
    color: Theme.colors.textMuted,
    fontSize: 18,
    fontWeight: '900',
  },
  crosshair: {
    backgroundColor: 'rgba(148, 163, 184, 0.28)',
    bottom: 20,
    position: 'absolute',
    top: CHART_TOP,
    width: 1,
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
  disclosureTitle: {
    color: Theme.colors.text,
    fontSize: 12,
    fontWeight: '900',
  },
  emaSegment: {
    borderRadius: Theme.radii.pill,
    height: 2,
    position: 'absolute',
  },
  emptyChart: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    gap: Spacing.one,
    padding: Spacing.twoAndHalf,
  },
  emptyTitle: {
    color: Theme.colors.text,
    fontSize: 13,
    fontWeight: '900',
  },
  eventMarker: {
    alignItems: 'center',
    borderRadius: 10,
    borderWidth: 1,
    height: 20,
    justifyContent: 'center',
    minWidth: 20,
    paddingHorizontal: 3,
    position: 'absolute',
  },
  eventMarkerFtd: {
    borderRadius: 6,
    minWidth: 32,
    transform: [{ rotateZ: '-6deg' }],
  },
  eventMarkerText: {
    color: Theme.colors.text,
    fontSize: 9,
    fontWeight: '900',
  },
  eventLegendMarker: {
    alignItems: 'center',
    borderRadius: 8,
    borderWidth: 1,
    height: 16,
    justifyContent: 'center',
    minWidth: 18,
    paddingHorizontal: 2,
  },
  eventLegendMarkerText: {
    color: Theme.colors.text,
    fontSize: 8,
    fontWeight: '900',
  },
  eventLegendRow: {
    bottom: 1,
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
    left: CHART_LEFT,
    position: 'absolute',
    right: CHART_RIGHT,
  },
  filterButton: {
    backgroundColor: Theme.colors.card,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    minHeight: 34,
    paddingHorizontal: Spacing.two,
    paddingVertical: Spacing.one,
  },
  filterButtonActive: {
    backgroundColor: Theme.colors.accentSoft,
    borderColor: Theme.colors.accent,
  },
  filterRow: {
    gap: Spacing.one,
    paddingRight: Spacing.two,
  },
  filterText: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '900',
  },
  filterTextActive: {
    color: Theme.colors.accent,
  },
  gridLine: {
    backgroundColor: 'rgba(148, 163, 184, 0.14)',
    height: 1,
    left: 0,
    position: 'absolute',
    right: CHART_RIGHT,
  },
  header: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  helperText: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '800',
    lineHeight: 16,
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
  legendRow: {
    bottom: 17,
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
    left: CHART_LEFT,
    position: 'absolute',
    right: CHART_RIGHT,
  },
  legendText: {
    color: Theme.colors.textMuted,
    fontSize: 10,
    fontWeight: '800',
  },
  markerAccumulation: {
    backgroundColor: 'rgba(34, 197, 94, 0.24)',
    borderColor: Theme.colors.success,
  },
  markerChurning: {
    backgroundColor: 'rgba(245, 158, 11, 0.18)',
    borderColor: Theme.colors.warning,
  },
  markerDistribution: {
    backgroundColor: 'rgba(248, 113, 113, 0.22)',
    borderColor: Theme.colors.danger,
  },
  markerFollowThrough: {
    backgroundColor: 'rgba(14, 165, 233, 0.28)',
    borderColor: Theme.colors.accent,
    minWidth: 28,
  },
  markerStall: {
    backgroundColor: 'rgba(245, 158, 11, 0.2)',
    borderColor: Theme.colors.warning,
  },
  metric: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: StyleSheet.hairlineWidth,
    flexGrow: 1,
    minWidth: '46%',
    padding: Spacing.two,
  },
  metricLabel: {
    color: Theme.colors.textMuted,
    fontSize: 10,
    fontWeight: '900',
    textTransform: 'uppercase',
  },
  metricValue: {
    color: Theme.colors.text,
    fontSize: 14,
    fontWeight: '900',
  },
  netGaugeBlock: {
    gap: Spacing.one,
  },
  netGaugeCenter: {
    backgroundColor: 'rgba(148, 163, 184, 0.42)',
    height: '100%',
    left: '50%',
    position: 'absolute',
    width: 1,
  },
  netGaugeLabels: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  netGaugeMarker: {
    backgroundColor: Theme.colors.accent,
    borderRadius: 6,
    height: 12,
    marginLeft: -6,
    position: 'absolute',
    top: -4,
    width: 12,
  },
  netGaugeTrack: {
    backgroundColor: Theme.colors.card,
    borderRadius: Theme.radii.pill,
    height: 4,
    position: 'relative',
  },
  pressed: {
    opacity: 0.78,
  },
  selectedCandle: {
    borderWidth: 2,
  },
  selectedVolumeBar: {
    backgroundColor: 'rgba(14, 165, 233, 0.48)',
  },
  selectorButton: {
    alignItems: 'center',
    backgroundColor: Theme.colors.card,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    flex: 1,
    justifyContent: 'center',
    minHeight: 34,
    paddingHorizontal: Spacing.two,
  },
  selectorButtonActive: {
    backgroundColor: Theme.colors.accentSoft,
    borderColor: Theme.colors.accent,
  },
  selectorRow: {
    flexDirection: 'row',
    gap: Spacing.one,
  },
  selectorText: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '900',
  },
  selectorTextActive: {
    color: Theme.colors.accent,
  },
  subtitle: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '800',
  },
  summaryBox: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: StyleSheet.hairlineWidth,
    gap: Spacing.two,
    padding: Spacing.two,
  },
  summaryHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  summaryMetricRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.one,
  },
  summaryTitle: {
    color: Theme.colors.text,
    fontSize: 13,
    fontWeight: '900',
  },
  title: {
    color: Theme.colors.text,
    fontSize: 15,
    fontWeight: '900',
  },
  titleBlock: {
    flex: 1,
    gap: Spacing.half,
  },
  tooltip: {
    backgroundColor: Theme.colors.cardElevated,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    gap: 2,
    padding: Spacing.two,
    position: 'absolute',
    zIndex: 10,
  },
  tooltipEvent: {
    color: Theme.colors.warning,
    fontSize: 10,
    fontWeight: '800',
    lineHeight: 14,
  },
  tooltipPrimary: {
    color: Theme.colors.text,
    fontSize: 10,
    fontWeight: '900',
    paddingTop: 2,
  },
  tooltipLine: {
    color: Theme.colors.textMuted,
    fontSize: 10,
    fontWeight: '800',
  },
  tooltipTitle: {
    color: Theme.colors.text,
    fontSize: 11,
    fontWeight: '900',
  },
  volumeBar: {
    backgroundColor: 'rgba(148, 163, 184, 0.34)',
    borderRadius: 2,
    position: 'absolute',
  },
  volumeBarDown: {
    backgroundColor: 'rgba(248, 113, 113, 0.36)',
  },
  volumeBarEvent: {
    borderColor: 'rgba(245, 158, 11, 0.76)',
    borderWidth: 1,
  },
  volumeBarUp: {
    backgroundColor: 'rgba(34, 197, 94, 0.34)',
  },
  warningText: {
    color: Theme.colors.warning,
    fontSize: 11,
    fontWeight: '800',
  },
  wick: {
    position: 'absolute',
    width: 1,
  },
  yAxisLabel: {
    color: Theme.colors.textMuted,
    fontSize: 9,
    fontWeight: '800',
    position: 'absolute',
    right: -CHART_RIGHT + 4,
    top: -7,
  },
});
