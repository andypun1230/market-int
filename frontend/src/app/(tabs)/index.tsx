import type { ReactNode } from 'react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useFocusEffect, useRouter } from 'expo-router';
import { SymbolView } from 'expo-symbols';
import {
  Animated,
  Easing,
  LayoutAnimation,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  useWindowDimensions,
  View,
} from 'react-native';
import Svg, { Polyline } from 'react-native-svg';

import { AppScreen } from '@/components/ui/AppScreen';
import { ErrorState } from '@/components/ui/ErrorState';
import { SkeletonCard } from '@/components/ui/SkeletonCard';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Theme } from '@/constants/theme';
import { createCopilotContext } from '@/features/copilot/context/buildScreenContext';
import { WhatMovedMarketCard } from '@/features/context-intelligence/components/ContextIntelligenceCards';
import {
  buildHomeSummary,
  type HomeIndexSnapshot,
  type HomeLeadershipItem,
  type HomeMetric,
  type HomeSummary,
  type HomeTone,
} from '@/features/home/homeSummary';
import { useHomeDashboard } from '@/hooks/useHomeDashboard';

type HomeIcon = { android: string; ios: string; web: string };

const ICONS = {
  breadth: { android: 'donut_large', ios: 'chart.pie.fill', web: 'donut_large' },
  chevron: { android: 'chevron_right', ios: 'chevron.right', web: 'chevron_right' },
  insight: { android: 'lightbulb', ios: 'lightbulb.fill', web: 'lightbulb' },
  leadership: { android: 'leaderboard', ios: 'trophy.fill', web: 'leaderboard' },
  market: { android: 'format_list_bulleted', ios: 'list.bullet', web: 'format_list_bulleted' },
  pulse: { android: 'monitor_heart', ios: 'waveform.path.ecg', web: 'monitor_heart' },
  risk: { android: 'speed', ios: 'gauge.with.dots.needle.50percent', web: 'speed' },
  snapshot: { android: 'show_chart', ios: 'chart.xyaxis.line', web: 'show_chart' },
  stocks: { android: 'star', ios: 'star.fill', web: 'star' },
  volatility: { android: 'waves', ios: 'waveform', web: 'waves' },
} satisfies Record<string, HomeIcon>;

const HOME_LAYOUT = {
  cardGap: 12,
  cardRadius: 8,
  gridGap: 8,
};

export default function HomeScreen() {
  const router = useRouter();
  const { width: viewportWidth } = useWindowDimensions();
  const [refreshing, setRefreshing] = useState(false);
  const [isFocused, setIsFocused] = useState(false);
  useFocusEffect(
    useCallback(() => {
      setIsFocused(true);
      return () => setIsFocused(false);
    }, []),
  );

  const {
    error,
    homeDashboard,
    loading,
    refetch,
  } = useHomeDashboard(isFocused);
  const summary = useMemo(
    () => buildHomeSummary(homeDashboard),
    [homeDashboard],
  );
  const updatedLabel = formatUpdatedLabel(
    summary.updatedAt,
    homeDashboard?.cache_age_seconds ?? homeDashboard?.snapshot_age_seconds ?? homeDashboard?.core.snapshot_age_seconds,
  );
  const copilotContext = useMemo(
    () => createCopilotContext({
      payload: {
        breadth: summary.breadth,
        indexes: summary.indexes,
        leadership: summary.leadership,
        marketPulse: summary.marketPulse,
        riskDrivers: summary.riskDrivers,
        riskScore: summary.riskScore,
        stockIdeas: summary.stockIdeas,
        todaysBias: summary.todaysBias,
        volatility: summary.volatility,
      },
      routeName: '/',
      screenTitle: 'Home Dashboard',
      screenType: 'home',
      sourceState: summary.sourceState,
    }),
    [summary],
  );

  const handleRefresh = async () => {
    setRefreshing(true);
    await refetch();
    setRefreshing(false);
  };

  const openLeadership = (item: HomeLeadershipItem) => {
    router.push({
      pathname: '/sectors',
      params: {
        entityId: item.id ?? '',
        entityKind: item.kind,
        entityName: item.label,
      },
    });
  };

  return (
    <AppScreen
      copilotContext={copilotContext}
      copilotPrompt="Explain today’s market pulse and the main risk."
      contentStyle={styles.screenContent}
      title="Market Intelligence"
      subtitle="Your market, distilled"
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={handleRefresh}
          tintColor={Theme.colors.textInverse}
        />
      }>
      {error ? <ErrorState message={error} onRetry={refetch} /> : null}
      {loading && !homeDashboard ? (
        <HomeSkeleton />
      ) : (
        <View style={styles.stack}>
          <MarketPulseCard
            onPress={() => router.push('/market')}
            summary={summary}
            updatedLabel={updatedLabel}
          />
          <TodaysMarketCard summary={summary} />
          <WhatMovedMarketCard enabled={isFocused} maxItems={3} />
          <MarketSnapshotCard
            indexColumns={viewportWidth >= 700 ? 4 : 2}
            narrow={viewportWidth < 360}
            onPress={() => router.push('/market')}
            summary={summary}
          />
          <LeadershipCard onPressItem={openLeadership} summary={summary} />
          <RiskDashboardCard onPress={() => router.push('/market')} stacked={viewportWidth < 360} summary={summary} />
          <TopStockIdeasCard
            onPressTicker={(symbol) => router.push({ pathname: '/watchlist', params: { symbol } })}
            onPressView={() => router.push('/watchlist')}
            summary={summary}
          />
          <DailyInsightCard onPress={() => router.push('/report')} summary={summary} />
        </View>
      )}
    </AppScreen>
  );
}

function MarketPulseCard({
  onPress,
  summary,
  updatedLabel,
}: {
  onPress: () => void;
  summary: HomeSummary;
  updatedLabel: string;
}) {
  const pulseColor = toneColor(summary.marketPulse.tone);
  return (
    <Pressable
      accessibilityLabel={`Open market overview. Market pulse is ${summary.marketPulse.label}`}
      accessibilityRole="button"
      onPress={onPress}
      style={({ pressed }) => [styles.pulseCard, pressed && styles.pressed]}>
      <View style={[styles.accentLine, { backgroundColor: pulseColor }]} />
      <View style={styles.pulseTopRow}>
        <View style={styles.titleWithIcon}>
          <SectionIcon icon={ICONS.pulse} tone={summary.marketPulse.tone} />
          <Text style={styles.eyebrow}>MARKET PULSE</Text>
        </View>
        <Text style={styles.updatedText}>{updatedLabel}</Text>
      </View>
      <View style={styles.pulseHeadlineRow}>
        <Text style={[styles.pulseHeadline, { color: pulseColor }]}>{summary.marketPulse.label}</Text>
        <SymbolView name={ICONS.chevron as never} size={17} tintColor={Theme.colors.textMuted} weight="bold" />
      </View>
      <View style={styles.factorRow}>
        {summary.marketPulse.factors.map((factor) => (
          <View key={factor.label} style={styles.factorItem}>
            <View style={[styles.factorDot, { backgroundColor: toneColor(factor.tone) }]} />
            <View style={styles.factorText}>
              <Text style={styles.microLabel}>{factor.label}</Text>
              <Text numberOfLines={1} style={styles.factorValue}>{factor.value}</Text>
              {factor.direction ? <Text numberOfLines={1} style={styles.factorDirection}>{factor.direction}</Text> : null}
            </View>
          </View>
        ))}
      </View>
    </Pressable>
  );
}

function TodaysMarketCard({ summary }: { summary: HomeSummary }) {
  const [expanded, setExpanded] = useState(false);
  const [rotation] = useState(() => new Animated.Value(0));

  useEffect(() => {
    Animated.timing(rotation, {
      duration: 180,
      easing: Easing.out(Easing.cubic),
      toValue: expanded ? 1 : 0,
      useNativeDriver: true,
    }).start();
  }, [expanded, rotation]);

  const toggle = () => {
    LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
    setExpanded((current) => !current);
  };
  const visibleEvents = expanded ? summary.marketEvents : summary.marketEvents.slice(0, 3);
  const rotate = rotation.interpolate({ inputRange: [0, 1], outputRange: ['0deg', '90deg'] });

  return (
    <HomeCard accentColor={Theme.colors.accent} icon={ICONS.market} title="Today’s Market">
      <Pressable
        accessibilityLabel={`${expanded ? 'Collapse' : 'Expand'} Today’s Market`}
        accessibilityRole="button"
        accessibilityState={{ expanded }}
        onPress={toggle}
        style={({ pressed }) => [styles.marketEventStack, pressed && styles.pressedSoft]}>
        {visibleEvents.map((event, index) => (
          <View key={`${index}-${event}`} style={styles.marketEventRow}>
            <View style={styles.eventMarker} />
            <Text numberOfLines={expanded ? undefined : 1} style={styles.marketEventText}>{event}</Text>
          </View>
        ))}
        {summary.marketEvents.length > 3 ? (
          <View style={styles.expandRow}>
            <Text style={styles.expandText}>{expanded ? 'Show less' : `${summary.marketEvents.length - 3} more observations`}</Text>
            <Animated.View style={{ transform: [{ rotate }] }}>
              <SymbolView name={ICONS.chevron as never} size={15} tintColor={Theme.colors.accent} weight="bold" />
            </Animated.View>
          </View>
        ) : null}
      </Pressable>
      <View style={styles.biasRow}>
        <Text style={styles.biasLabel}>Today’s Bias</Text>
        <Text numberOfLines={2} style={styles.biasText}>{summary.todaysBias}</Text>
      </View>
    </HomeCard>
  );
}

function MarketSnapshotCard({
  indexColumns,
  narrow,
  onPress,
  summary,
}: {
  indexColumns: 2 | 4;
  narrow: boolean;
  onPress: () => void;
  summary: HomeSummary;
}) {
  return (
    <HomeCard accentColor={Theme.colors.success} icon={ICONS.snapshot} onPress={onPress} title="Market Snapshot">
      {summary.indexes.length ? (
        <View style={styles.indexGrid}>
          {summary.indexes.map((index) => (
            <IndexChip columns={indexColumns} index={index} key={index.symbol} narrow={narrow} />
          ))}
        </View>
      ) : (
        <Text style={styles.emptyText}>Index snapshot is updating.</Text>
      )}
      <View style={styles.visualMetricRow}>
        {summary.breadth ? <VisualIndicator icon={ICONS.breadth} metric={summary.breadth} /> : null}
        {summary.volatility ? <VisualIndicator icon={ICONS.volatility} metric={summary.volatility} /> : null}
      </View>
    </HomeCard>
  );
}

function LeadershipCard({
  onPressItem,
  summary,
}: {
  onPressItem: (item: HomeLeadershipItem) => void;
  summary: HomeSummary;
}) {
  return (
    <HomeCard accentColor={Theme.colors.purple} icon={ICONS.leadership} title="Leadership">
      <View style={styles.leadershipList}>
        {summary.leadership.length ? summary.leadership.map((item) => (
          <Pressable
            accessibilityLabel={`Open ${item.role}: ${item.label}`}
            accessibilityRole="button"
            key={item.role}
            onPress={() => onPressItem(item)}
            style={({ pressed }) => [styles.leadershipRow, pressed && styles.pressedRow]}>
            <View style={[styles.leadershipAccent, { backgroundColor: toneColor(item.tone) }]} />
            <View style={styles.leadershipTextWrap}>
              <Text style={styles.microLabel}>{item.role}</Text>
              <Text numberOfLines={1} style={styles.leadershipValue}>{item.label}</Text>
            </View>
            <SymbolView name={ICONS.chevron as never} size={15} tintColor={Theme.colors.textMuted} weight="bold" />
          </Pressable>
        )) : <Text style={styles.emptyText}>Leadership snapshot is updating.</Text>}
      </View>
    </HomeCard>
  );
}

function RiskDashboardCard({ onPress, stacked, summary }: { onPress: () => void; stacked: boolean; summary: HomeSummary }) {
  const tone = riskTone(summary.riskLabel, summary.riskScore);
  return (
    <HomeCard accentColor={Theme.colors.warning} icon={ICONS.risk} onPress={onPress} title="Risk Dashboard">
      <View style={[styles.riskLayout, stacked && styles.riskLayoutStacked]}>
        <View style={[styles.riskScoreBlock, stacked && styles.riskScoreBlockStacked]}>
          <Text style={styles.riskScore}>{summary.riskScore === null ? '—' : Math.round(summary.riskScore)}</Text>
          <Text style={styles.riskScale}>/ 100</Text>
          <StatusBadge label={summary.riskLabel} showDot tone={badgeTone(tone)} />
        </View>
        <View style={styles.driverList}>
          {summary.riskDrivers.length ? summary.riskDrivers.map((driver) => (
            <View key={driver} style={styles.driverRow}>
              <View style={[styles.driverMarker, { backgroundColor: Theme.colors.warning }]} />
              <Text numberOfLines={1} style={styles.driverText}>{driver}</Text>
            </View>
          )) : <Text style={styles.emptyText}>No material risk driver detected.</Text>}
        </View>
      </View>
    </HomeCard>
  );
}

function TopStockIdeasCard({
  onPressTicker,
  onPressView,
  summary,
}: {
  onPressTicker: (symbol: string) => void;
  onPressView: () => void;
  summary: HomeSummary;
}) {
  return (
    <HomeCard
      accentColor={Theme.colors.warning}
      headerAction={<HeaderLink label="View Watchlist" onPress={onPressView} />}
      icon={ICONS.stocks}
      title="Top Stock Ideas">
      {summary.stockIdeas.length ? (
        <View style={styles.tickerRow}>
          {summary.stockIdeas.map((item) => (
            <Pressable
              accessibilityLabel={`Open ${item.symbol} Stock Detail`}
              accessibilityRole="button"
              key={item.symbol}
              onPress={() => onPressTicker(item.symbol)}
              style={({ pressed }) => [styles.tickerChip, pressed && styles.tickerChipPressed]}>
              <Text style={styles.tickerText}>{item.symbol}</Text>
              <Text style={[styles.tickerChange, { color: returnColor(item.changePercent) }]}>
                {item.changePercent === null ? 'N/A' : formatSignedPercent(item.changePercent)}
              </Text>
            </Pressable>
          ))}
        </View>
      ) : <Text style={styles.emptyText}>No stocks saved yet.</Text>}
    </HomeCard>
  );
}

function DailyInsightCard({ onPress, summary }: { onPress: () => void; summary: HomeSummary }) {
  if (!summary.dailyInsight) {
    return null;
  }
  return (
    <HomeCard accentColor={Theme.colors.accent} icon={ICONS.insight} onPress={onPress} title="Daily Insight">
      <View style={styles.insightBody}>
        <Text style={styles.insightCategory}>{summary.dailyInsight.category}</Text>
        <Text style={styles.insightHeadline}>{summary.dailyInsight.headline}</Text>
        <Text numberOfLines={2} style={styles.insightText}>{summary.dailyInsight.summary}</Text>
      </View>
    </HomeCard>
  );
}

function HomeCard({
  accentColor,
  children,
  headerAction,
  icon,
  onPress,
  title,
}: {
  accentColor: string;
  children: ReactNode;
  headerAction?: ReactNode;
  icon: HomeIcon;
  onPress?: () => void;
  title: string;
}) {
  const content = (
    <View style={styles.homeCard}>
      <View style={[styles.accentLine, { backgroundColor: accentColor }]} />
      <View style={styles.sectionHeader}>
        <View style={styles.titleWithIcon}>
          <SectionIcon color={accentColor} icon={icon} />
          <Text style={styles.sectionTitle}>{title}</Text>
        </View>
        {headerAction ?? (onPress ? <SymbolView name={ICONS.chevron as never} size={16} tintColor={Theme.colors.textMuted} weight="bold" /> : null)}
      </View>
      {children}
    </View>
  );
  if (!onPress) return content;
  return (
    <Pressable
      accessibilityLabel={`Open ${title}`}
      accessibilityRole="button"
      onPress={onPress}
      style={({ pressed }) => pressed && styles.pressed}>
      {content}
    </Pressable>
  );
}

function SectionIcon({ color, icon, tone }: { color?: string; icon: HomeIcon; tone?: HomeTone }) {
  const tint = color ?? toneColor(tone ?? 'neutral');
  return (
    <View style={[styles.sectionIcon, { backgroundColor: softColor(tone ?? 'neutral') }]}>
      <SymbolView name={icon as never} size={15} tintColor={tint} weight="bold" />
    </View>
  );
}

function IndexChip({ columns, index, narrow }: { columns: 2 | 4; index: HomeIndexSnapshot; narrow: boolean }) {
  return (
    <View
      accessibilityLabel={buildIndexAccessibilityLabel(index)}
      accessible
      style={[styles.indexChip, { flexBasis: columns === 4 ? '23%' : '47%' }]}>
      <View style={styles.indexTopRow}>
        <Text style={styles.indexSymbol}>{index.symbol}</Text>
        <Text style={styles.indexTrend}>{index.trendLabel ?? 'Updating'}</Text>
      </View>
      <View style={[styles.indexMoveRow, narrow && styles.indexMoveRowNarrow]}>
        <Text style={[styles.indexChange, { color: returnColor(index.changePercent) }]}>
          {index.changePercent === null ? 'N/A' : formatSignedPercent(index.changePercent)}
        </Text>
        <Sparkline narrow={narrow} points={index.sparkline} tone={index.direction === 'up' ? 'positive' : index.direction === 'down' ? 'negative' : 'neutral'} />
      </View>
    </View>
  );
}

function Sparkline({ narrow, points, tone }: { narrow: boolean; points: number[]; tone: HomeTone }) {
  if (points.length < 2) {
    return <View style={[styles.sparklinePlaceholder, narrow && styles.sparklineNarrow]}><Text numberOfLines={1} style={styles.sparklineUnavailable}>No intraday</Text></View>;
  }
  const width = 112;
  const height = 26;
  const start = points[0] || 1;
  const scalePercent = 2;
  const coordinates = points.map((point, index) => {
    const x = (index / (points.length - 1)) * width;
    const percentMove = Math.max(-scalePercent, Math.min(scalePercent, ((point - start) / start) * 100));
    const y = (height / 2) - (percentMove / scalePercent) * ((height - 6) / 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
  return (
    <View style={[styles.sparklineWrap, narrow && styles.sparklineNarrow]}>
      <Svg height={height} preserveAspectRatio="none" viewBox={`0 0 ${width} ${height}`} width="100%">
        <Polyline fill="none" points={coordinates} stroke={toneColor(tone)} strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" />
      </Svg>
    </View>
  );
}

function VisualIndicator({ icon, metric }: { icon: HomeIcon; metric: HomeMetric }) {
  return (
    <View style={styles.visualMetric}>
      <View style={styles.visualMetricHeader}>
        <SymbolView name={icon as never} size={14} tintColor={toneColor(metric.tone)} weight="bold" />
        <Text style={styles.microLabel}>{metric.label}</Text>
      </View>
      <Text numberOfLines={1} style={[styles.visualMetricValue, { color: toneColor(metric.tone) }]}>{metric.value}{metric.direction ? ` · ${metric.direction}` : ''}</Text>
    </View>
  );
}

function HeaderLink({ label, onPress }: { label: string; onPress: () => void }) {
  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      style={({ pressed }) => [styles.headerLink, pressed && styles.pressedSoft]}>
      <Text style={styles.headerLinkText}>{label}</Text>
      <SymbolView name={ICONS.chevron as never} size={13} tintColor={Theme.colors.accent} weight="bold" />
    </Pressable>
  );
}

function HomeSkeleton() {
  return (
    <View style={styles.stack}>
      <SkeletonCard rows={3} />
      <SkeletonCard compact rows={3} />
      <View style={styles.skeletonGrid}>
        <SkeletonCard compact rows={2} />
        <SkeletonCard compact rows={2} />
      </View>
      <SkeletonCard compact rows={3} />
    </View>
  );
}

function formatSignedPercent(value: number) {
  return `${value > 0 ? '+' : ''}${value.toFixed(1)}%`;
}

function formatUpdatedLabel(timestamp: string | null, ageSeconds?: number | null) {
  const ageMinutes = typeof ageSeconds === 'number' && Number.isFinite(ageSeconds)
    ? Math.max(0, Math.floor(ageSeconds / 60))
    : timestamp
      ? Math.max(0, Math.floor((Date.now() - new Date(timestamp).getTime()) / 60_000))
      : 0;
  if (ageMinutes < 1) return 'Updated just now';
  if (ageMinutes === 1) return 'Updated 1 min ago';
  if (ageMinutes < 60) return `Updated ${ageMinutes} min ago`;
  const hours = Math.floor(ageMinutes / 60);
  return `Updated ${hours}h ago`;
}

function buildIndexAccessibilityLabel(index: HomeIndexSnapshot) {
  const dailyMove = index.changePercent === null
    ? 'has no current daily move available'
    : `${index.changePercent >= 0 ? 'is up' : 'is down'} ${Math.abs(index.changePercent).toFixed(1)} percent today`;
  return `${index.symbol} ${dailyMove}. ${index.trendLabel ?? 'Trend unavailable'}.`;
}

function returnColor(value: number | null) {
  if (value === null || Math.abs(value) < 0.05) return Theme.colors.textMuted;
  return value > 0 ? Theme.colors.success : Theme.colors.danger;
}

function riskTone(label: string, score: number | null): HomeTone {
  const normalized = label.toLowerCase();
  if (normalized.includes('low')) return 'positive';
  if (normalized.includes('high') || normalized.includes('elevated')) return 'negative';
  if (normalized.includes('moderate')) return 'warning';
  if ((score ?? 0) >= 65) return 'negative';
  if ((score ?? 0) >= 35) return 'warning';
  return 'neutral';
}

function toneColor(tone: HomeTone) {
  if (tone === 'positive') return Theme.colors.success;
  if (tone === 'warning') return Theme.colors.warning;
  if (tone === 'negative') return Theme.colors.danger;
  return Theme.colors.textMuted;
}

function softColor(tone: HomeTone) {
  if (tone === 'positive') return Theme.colors.successSoft;
  if (tone === 'warning') return Theme.colors.warningSoft;
  if (tone === 'negative') return Theme.colors.dangerSoft;
  return Theme.colors.cardMuted;
}

function badgeTone(tone: HomeTone): 'success' | 'warning' | 'danger' | 'muted' {
  if (tone === 'positive') return 'success';
  if (tone === 'warning') return 'warning';
  if (tone === 'negative') return 'danger';
  return 'muted';
}

const styles = StyleSheet.create({
  accentLine: { height: 3, left: 0, position: 'absolute', right: 0, top: 0 },
  biasLabel: { color: Theme.colors.accent, fontSize: 11, fontWeight: '900', textTransform: 'uppercase' },
  biasRow: { borderTopColor: Theme.colors.border, borderTopWidth: 1, gap: 2, paddingTop: 8 },
  biasText: { color: Theme.colors.text, fontSize: 12, lineHeight: 16 },
  driverList: { flex: 1, gap: 6, minWidth: 0 },
  driverMarker: { borderRadius: 3, height: 5, marginTop: 5, width: 5 },
  driverRow: { alignItems: 'flex-start', flexDirection: 'row', gap: 7 },
  driverText: { color: Theme.colors.text, flex: 1, fontSize: 12, lineHeight: 16 },
  emptyText: { color: Theme.colors.textMuted, fontSize: 13, lineHeight: 18 },
  eventMarker: { backgroundColor: Theme.colors.accent, borderRadius: 2, height: 4, marginTop: 6, width: 4 },
  expandRow: { alignItems: 'center', flexDirection: 'row', gap: 4, justifyContent: 'flex-end', marginTop: 2 },
  expandText: { color: Theme.colors.accent, fontSize: 11, fontWeight: '800' },
  eyebrow: { color: Theme.colors.textMuted, fontSize: 11, fontWeight: '900' },
  factorDot: { borderRadius: 3, height: 6, width: 6 },
  factorItem: { alignItems: 'center', flexBasis: 88, flexDirection: 'row', flexGrow: 1, gap: 6, minWidth: 0 },
  factorRow: { borderTopColor: Theme.colors.border, borderTopWidth: 1, flexDirection: 'row', gap: 8, paddingTop: 8 },
  factorText: { flex: 1, minWidth: 0 },
  factorDirection: { color: Theme.colors.textMuted, fontSize: 9, fontWeight: '700' },
  factorValue: { color: Theme.colors.text, fontSize: 11, fontWeight: '800' },
  headerLink: { alignItems: 'center', flexDirection: 'row', gap: 2, minHeight: 28, paddingLeft: 8 },
  headerLinkText: { color: Theme.colors.accent, fontSize: 12, fontWeight: '800' },
  homeCard: { backgroundColor: Theme.colors.card, borderColor: Theme.colors.border, borderRadius: HOME_LAYOUT.cardRadius, borderWidth: 1, gap: 8, overflow: 'hidden', padding: 12 },
  indexChange: { fontSize: 18, fontWeight: '900' },
  indexChip: { backgroundColor: Theme.colors.backgroundMuted, borderColor: Theme.colors.border, borderRadius: Theme.radii.small, borderWidth: 1, flexBasis: 155, flexGrow: 1, gap: 5, minWidth: 0, padding: 8 },
  indexGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: HOME_LAYOUT.gridGap },
  indexMoveRow: { alignItems: 'center', flexDirection: 'row', gap: 6, justifyContent: 'space-between' },
  indexMoveRowNarrow: { alignItems: 'stretch', flexDirection: 'column', gap: 2 },
  indexSymbol: { color: Theme.colors.text, fontSize: 14, fontWeight: '900' },
  indexTopRow: { alignItems: 'center', flexDirection: 'row', gap: 8, justifyContent: 'space-between' },
  indexTrend: { color: Theme.colors.textMuted, fontSize: 10, fontWeight: '700' },
  insightBody: { gap: 2 },
  insightCategory: { color: Theme.colors.accent, fontSize: 10, fontWeight: '900', textTransform: 'uppercase' },
  insightHeadline: { color: Theme.colors.text, fontSize: 14, fontWeight: '900' },
  insightText: { color: Theme.colors.textMuted, fontSize: 12, lineHeight: 17 },
  leadershipAccent: { borderRadius: 2, height: 28, width: 3 },
  leadershipList: { gap: 4 },
  leadershipRow: { alignItems: 'center', borderRadius: Theme.radii.small, flexDirection: 'row', gap: 8, height: 44, paddingHorizontal: 5 },
  leadershipTextWrap: { flex: 1, minWidth: 0 },
  leadershipValue: { color: Theme.colors.text, fontSize: 14, fontWeight: '800' },
  marketEventRow: { alignItems: 'flex-start', flexDirection: 'row', gap: 8 },
  marketEventStack: { gap: 6 },
  marketEventText: { color: Theme.colors.text, flex: 1, fontSize: 12, lineHeight: 16 },
  microLabel: { color: Theme.colors.textMuted, fontSize: 10, fontWeight: '800', textTransform: 'uppercase' },
  pressed: { opacity: 0.78, transform: [{ scale: 0.995 }] },
  pressedRow: { backgroundColor: Theme.colors.cardMuted },
  pressedSoft: { opacity: 0.7 },
  pulseCard: { backgroundColor: Theme.colors.card, borderColor: Theme.colors.border, borderRadius: HOME_LAYOUT.cardRadius, borderWidth: 1, gap: 8, overflow: 'hidden', padding: 12 },
  pulseHeadline: { fontSize: 27, fontWeight: '900', lineHeight: 31 },
  pulseHeadlineRow: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between' },
  pulseTopRow: { alignItems: 'center', flexDirection: 'row', gap: 10, justifyContent: 'space-between' },
  riskLayout: { alignItems: 'center', flexDirection: 'row', gap: 12 },
  riskLayoutStacked: { alignItems: 'stretch', flexDirection: 'column', gap: 8 },
  riskScale: { color: Theme.colors.textMuted, fontSize: 10, marginBottom: 5 },
  riskScore: { color: Theme.colors.text, fontSize: 28, fontWeight: '900', lineHeight: 30 },
  riskScoreBlock: { alignItems: 'flex-start', borderRightColor: Theme.colors.border, borderRightWidth: 1, minWidth: 82, paddingRight: 10 },
  riskScoreBlockStacked: { alignItems: 'center', borderBottomColor: Theme.colors.border, borderBottomWidth: 1, borderRightWidth: 0, flexDirection: 'row', gap: 6, paddingBottom: 8, paddingRight: 0 },
  sectionHeader: { alignItems: 'center', flexDirection: 'row', gap: 10, justifyContent: 'space-between' },
  sectionIcon: { alignItems: 'center', borderRadius: 6, height: 26, justifyContent: 'center', width: 26 },
  sectionTitle: { color: Theme.colors.text, fontSize: 15, fontWeight: '900' },
  screenContent: { alignSelf: 'center', gap: 10, maxWidth: 1100, width: '100%' },
  skeletonGrid: { flexDirection: 'row', gap: HOME_LAYOUT.gridGap },
  sparklinePlaceholder: { alignItems: 'center', borderBottomColor: Theme.colors.border, borderBottomWidth: 1, height: 26, justifyContent: 'center', minWidth: 72, width: '58%' },
  sparklineNarrow: { minWidth: 0, width: '100%' },
  sparklineUnavailable: { color: Theme.colors.textMuted, fontSize: 9, fontWeight: '700' },
  sparklineWrap: { height: 26, minWidth: 72, width: '58%' },
  stack: { gap: HOME_LAYOUT.cardGap },
  tickerChange: { fontSize: 12, fontWeight: '900' },
  tickerChip: { alignItems: 'center', backgroundColor: Theme.colors.backgroundMuted, borderColor: Theme.colors.border, borderRadius: Theme.radii.small, borderWidth: 1, flexDirection: 'row', gap: 8, height: 36, paddingHorizontal: 10 },
  tickerChipPressed: { backgroundColor: Theme.colors.cardElevated, borderColor: Theme.colors.accent, transform: [{ scale: 0.98 }] },
  tickerRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  tickerText: { color: Theme.colors.text, fontSize: 13, fontWeight: '900' },
  titleWithIcon: { alignItems: 'center', flexDirection: 'row', gap: 8, minWidth: 0 },
  updatedText: { color: Theme.colors.textMuted, flexShrink: 1, fontSize: 10, textAlign: 'right' },
  visualMetric: { backgroundColor: Theme.colors.backgroundMuted, borderRadius: Theme.radii.small, flex: 1, gap: 2, minWidth: 135, paddingHorizontal: 8, paddingVertical: 6 },
  visualMetricHeader: { alignItems: 'center', flexDirection: 'row', gap: 6 },
  visualMetricRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  visualMetricValue: { fontSize: 11, fontWeight: '900' },
});
