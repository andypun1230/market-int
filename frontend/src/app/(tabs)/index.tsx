import type { ReactNode } from 'react';
import { useCallback, useMemo, useState } from 'react';
import { useFocusEffect, useRouter } from 'expo-router';
import { Pressable, RefreshControl, StyleSheet, Text, View } from 'react-native';

import { AppScreen } from '@/components/ui/AppScreen';
import { ErrorState } from '@/components/ui/ErrorState';
import { SkeletonCard } from '@/components/ui/SkeletonCard';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Spacing, Theme } from '@/constants/theme';
import { AskCopilotButton } from '@/features/copilot/components/AskCopilotButton';
import { createCopilotContext } from '@/features/copilot/context/buildScreenContext';
import { buildHomeSummary, type HomeIndexSnapshot, type HomeLeadershipItem, type HomeMetric, type HomeSourceState, type HomeSummary } from '@/features/home/homeSummary';
import { useHomeDashboard } from '@/hooks/useHomeDashboard';

const HOME_LAYOUT = {
  cardGap: 12,
  cardPaddingHorizontal: 16,
  cardPaddingVertical: 16,
  cardRadius: 12,
  compactGap: 8,
  contentGap: 10,
  gridGap: 8,
  screenPaddingHorizontal: 12,
  sectionHeaderGap: 12,
};

export default function HomeScreen() {
  const router = useRouter();
  const [refreshing, setRefreshing] = useState(false);
  const [isFocused, setIsFocused] = useState(false);
  useFocusEffect(
    useCallback(() => {
      setIsFocused(true);
      return () => setIsFocused(false);
    }, []),
  );

  const { error, homeDashboard, loading, refetch } = useHomeDashboard(isFocused);
  const summary = useMemo(() => buildHomeSummary(homeDashboard), [homeDashboard]);
  const copilotContext = useMemo(
    () => createCopilotContext({
      payload: {
        breadth: summary.breadth,
        healthScore: summary.healthScore,
        indexes: summary.indexes,
        leaders: summary.leaders,
        playbook: homeDashboard?.core.decision_summary.playbook,
        positioningScore: summary.positioningScore,
        recommendation: summary.recommendation,
        riskScore: summary.riskScore,
        stockIdeas: summary.stockIdeas,
        summary: summary.summary,
        volatility: summary.volatility,
      },
      routeName: '/',
      screenTitle: 'Home Dashboard',
      screenType: 'home',
      sourceState: summary.sourceState,
    }),
    [homeDashboard, summary],
  );

  const handleRefresh = async () => {
    setRefreshing(true);
    await refetch();
    setRefreshing(false);
  };

  return (
    <AppScreen
      title="Market Intelligence"
      subtitle="Decision-first market dashboard"
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={handleRefresh}
          tintColor={Theme.colors.textInverse}
        />
      }>
      {error ? <ErrorState message={error} onRetry={refetch} /> : null}
      {!loading ? (
        <AskCopilotButton
          context={copilotContext}
          prompt="Explain today’s playbook and the main risk."
        />
      ) : null}

      {loading && !homeDashboard ? (
        <HomeSkeleton />
      ) : (
        <View style={styles.stack}>
          <TodaysPlaybookCard
            onPress={() => router.push('/market')}
            summary={summary}
          />
          <MarketSnapshotCard
            onPress={() => router.push('/market')}
            summary={summary}
          />
          <LeadershipSnapshotCard
            onPress={() => router.push('/sectors')}
            summary={summary}
          />
          <RiskMacroCard
            onPress={() => router.push('/market')}
            summary={summary}
          />
          <WatchlistSnapshotCard
            onPressTicker={() => router.push('/watchlist')}
            onPressView={() => router.push('/watchlist')}
            summary={summary}
          />
          <DailyInsightCard
            onPress={() => router.push('/report')}
            summary={summary}
          />
        </View>
      )}
    </AppScreen>
  );
}

function TodaysPlaybookCard({ onPress, summary }: { onPress: () => void; summary: HomeSummary }) {
  return (
    <Pressable
      accessibilityLabel="Open Market Overview"
      accessibilityRole="button"
      onPress={onPress}
      style={({ pressed }) => [styles.heroCard, pressed && styles.pressed]}>
      <HomeSectionHeader right={<SourceBadge source={summary.sourceState} />} title="Today’s Playbook" />
      <View style={styles.playbookStack}>
        <Text style={styles.heroHeadline}>{summary.recommendation}</Text>
        <View style={styles.heroMetricRow}>
          <CompactMetric label="Health" tone={toneForScore(summary.healthScore)} value={formatMetricValue(summary.healthScore, summary.healthLabel)} />
          <CompactMetric label="Risk" tone={riskTone(summary.riskLabel)} value={summary.riskScore === null ? summary.riskLabel : `${summary.riskLabel} ${Math.round(summary.riskScore)}`} />
          <CompactMetric label="Positioning" tone={positioningTone(summary.positioningLabel)} value={formatMetricValue(summary.positioningScore, summary.positioningLabel)} />
        </View>
        <Text numberOfLines={2} style={styles.summaryText}>{summary.summary}</Text>
      </View>
    </Pressable>
  );
}

function MarketSnapshotCard({ onPress, summary }: { onPress: () => void; summary: HomeSummary }) {
  const internals = [summary.breadth, summary.volatility, summary.yield10Y].filter((item): item is HomeMetric => item !== null);
  return (
    <HomeCard onPress={onPress} title="Market Snapshot">
      <View style={styles.cardContentStack}>
        {summary.indexes.length ? (
          <View style={styles.indexRow}>
            {summary.indexes.map((index) => <IndexChip index={index} key={index.symbol} />)}
          </View>
        ) : (
          <Text style={styles.emptyText}>Index snapshot is updating.</Text>
        )}
        {internals.length ? (
          <View style={styles.inlineMetricRow}>
            {internals.map((metric) => <InlineMetric key={metric.label} metric={metric} />)}
          </View>
        ) : null}
      </View>
    </HomeCard>
  );
}

function LeadershipSnapshotCard({ onPress, summary }: { onPress: () => void; summary: HomeSummary }) {
  return (
    <HomeCard onPress={onPress} title="Leadership">
      <View style={styles.cardContentStack}>
        <LeadershipRow items={summary.leaders} label="Leading" />
        <LeadershipRow emptyState={summary.laggardState} items={summary.laggards} label="Lagging" />
      </View>
    </HomeCard>
  );
}

function RiskMacroCard({ onPress, summary }: { onPress: () => void; summary: HomeSummary }) {
  return (
    <HomeCard onPress={onPress} title="Risk & Macro">
      <View style={[styles.splitGrid, !summary.upcomingEvents.length && styles.splitGridStacked]}>
        <View style={styles.splitPanel}>
          <Text style={styles.mutedLabel}>Risk</Text>
          <Text style={styles.panelValue}>{summary.riskScore === null ? summary.riskLabel : `${summary.riskLabel} — ${Math.round(summary.riskScore)}/100`}</Text>
          <Text numberOfLines={2} style={styles.panelSubtext}>{summary.riskDriver ?? 'No material risk driver detected.'}</Text>
        </View>
        <View style={styles.splitPanel}>
          <Text style={styles.mutedLabel}>Next Events</Text>
          {summary.upcomingEvents.length ? summary.upcomingEvents.slice(0, 3).map((event) => (
            <Text key={`${event.label}-${event.when}`} numberOfLines={1} style={styles.eventText}>{event.label} · {event.when}</Text>
          )) : <Text style={styles.panelSubtext}>No major scheduled events</Text>}
        </View>
      </View>
    </HomeCard>
  );
}

function WatchlistSnapshotCard({
  onPressTicker,
  onPressView,
  summary,
}: {
  onPressTicker: (symbol: string) => void;
  onPressView: () => void;
  summary: HomeSummary;
}) {
  return (
    <HomeCard title="Top Stock Ideas">
      <View style={styles.cardContentStack}>
        {summary.stockIdeas.length ? (
          <View style={styles.tickerRow}>
            {summary.stockIdeas.map((item) => (
              <Pressable
                accessibilityLabel={`Open ${item.symbol} in Watchlist`}
                accessibilityRole="button"
                key={item.symbol}
                onPress={() => onPressTicker(item.symbol)}
                style={({ pressed }) => [styles.tickerChip, pressed && styles.pressed]}>
                <Text style={styles.tickerText}>{item.symbol}</Text>
                {item.changePercent !== null ? <Text style={[styles.tickerChange, { color: returnColor(item.changePercent) }]}>{formatSignedPercent(item.changePercent)}</Text> : null}
              </Pressable>
            ))}
          </View>
        ) : (
          <Text style={styles.emptyText}>No stocks saved yet</Text>
        )}
        <Pressable
          accessibilityLabel="Open Watchlist"
          accessibilityRole="button"
          onPress={onPressView}
          style={({ pressed }) => pressed && styles.pressed}>
          <Text style={styles.linkText}>View Watchlist ›</Text>
        </Pressable>
      </View>
    </HomeCard>
  );
}

function DailyInsightCard({ onPress, summary }: { onPress: () => void; summary: HomeSummary }) {
  if (!summary.dailyInsight) {
    return null;
  }
  return (
    <HomeCard onPress={onPress} title="Daily Insight">
      <View style={styles.insightHeaderRow}>
        <Text style={styles.insightHeadline}>{summary.dailyInsight.headline}</Text>
        <StatusBadge label={summary.dailyInsight.sourceLabel} tone="muted" />
      </View>
      <Text numberOfLines={3} style={styles.summaryText}>{summary.dailyInsight.summary}</Text>
    </HomeCard>
  );
}

function HomeCard({ children, onPress, title }: { children: ReactNode; onPress?: () => void; title: string }) {
  const content = (
    <View style={styles.homeCard}>
      <HomeSectionHeader showChevron={Boolean(onPress)} title={title} />
      {children}
    </View>
  );
  if (!onPress) {
    return content;
  }
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

function HomeSectionHeader({
  right,
  showChevron = false,
  subtitle,
  title,
}: {
  right?: ReactNode;
  showChevron?: boolean;
  subtitle?: string;
  title: string;
}) {
  return (
    <View style={styles.sectionHeader}>
      <View style={styles.sectionHeaderText}>
        <Text style={styles.sectionTitle}>{title}</Text>
        {subtitle ? <Text numberOfLines={1} style={styles.sectionSubtitle}>{subtitle}</Text> : null}
      </View>
      {right ?? (showChevron ? <Text style={styles.chevron}>›</Text> : null)}
    </View>
  );
}

function CompactMetric({ label, tone, value }: { label: string; tone: HomeMetric['tone']; value: string }) {
  return (
    <View style={styles.compactMetric}>
      <Text style={styles.mutedLabel}>{label}</Text>
      <Text numberOfLines={1} style={[styles.compactMetricValue, { color: toneColor(tone) }]}>{value}</Text>
    </View>
  );
}

function IndexChip({ index }: { index: HomeIndexSnapshot }) {
  return (
    <View
      accessibilityLabel={buildIndexAccessibilityLabel(index)}
      accessible
      style={styles.indexChip}>
      <Text style={styles.indexSymbol}>{index.symbol}</Text>
      <Text style={[styles.indexChange, { color: returnColor(index.changePercent) }]}>
        {index.changePercent === null ? 'Updating' : formatSignedPercent(index.changePercent)}
      </Text>
      {index.trendLabel ? <Text style={styles.indexTrend}>50D Trend: {index.trendLabel}</Text> : null}
    </View>
  );
}

function InlineMetric({ metric }: { metric: HomeMetric }) {
  return (
    <View style={styles.inlineMetric}>
      <Text style={styles.mutedLabel}>{metric.label}</Text>
      <Text style={[styles.inlineMetricValue, { color: toneColor(metric.tone) }]}>{metric.value}</Text>
    </View>
  );
}

function LeadershipRow({
  emptyState = 'unavailable',
  items,
  label,
}: {
  emptyState?: HomeSummary['laggardState'];
  items: HomeLeadershipItem[];
  label: string;
}) {
  return (
    <View style={styles.leadershipRow}>
      <Text style={styles.mutedLabel}>{label}</Text>
      {items.length ? (
        <View style={styles.leadershipList}>
          {items.map((item) => (
            <View key={`${item.kind}-${item.label}`} style={styles.leadershipItemRow}>
              <Text style={styles.leadershipKind}>{item.kind === 'theme' ? 'Theme' : 'Sector'}</Text>
              <Text numberOfLines={2} style={styles.leadershipText}>{item.label}</Text>
            </View>
          ))}
        </View>
      ) : <Text style={styles.emptyText}>{getLeadershipEmptyText(label, emptyState)}</Text>}
    </View>
  );
}

function SourceBadge({ source }: { source: HomeSourceState }) {
  if (source === 'live') {
    return <StatusBadge label="Live" tone="success" />;
  }
  if (source === 'mock') {
    return <StatusBadge label="Mock data" tone="warning" />;
  }
  if (source === 'cached') {
    return <StatusBadge label="Cached" tone="muted" />;
  }
  return null;
}

function HomeSkeleton() {
  return (
    <View style={styles.stack}>
      <SkeletonCard rows={4} />
      <SkeletonCard compact rows={3} />
      <SkeletonCard compact rows={3} />
    </View>
  );
}

function formatMetricValue(score: number | null, label: string) {
  return score === null ? label : `${Math.round(score)}`;
}

function formatSignedPercent(value: number) {
  const sign = value > 0 ? '+' : value < 0 ? '' : '';
  return `${sign}${value.toFixed(1)}%`;
}

function buildIndexAccessibilityLabel(index: HomeIndexSnapshot) {
  const dailyMove = index.changePercent === null
    ? 'has no current daily move available'
    : `${index.changePercent >= 0 ? 'is up' : 'is down'} ${Math.abs(index.changePercent).toFixed(1)} percent today`;
  const trend = index.trendLabel ? ` Its 50-day trend is ${index.trendLabel.toLowerCase()}.` : '';
  return `${index.symbol} ${dailyMove}.${trend}`;
}

function getLeadershipEmptyText(label: string, emptyState: HomeSummary['laggardState']) {
  if (label !== 'Lagging') {
    return 'Leadership signals are updating.';
  }
  return emptyState === 'evaluated_empty' ? 'No major laggards detected' : 'Laggard data unavailable';
}

function returnColor(value: number | null) {
  if (value === null || Math.abs(value) < 0.05) {
    return Theme.colors.textMuted;
  }
  return value > 0 ? Theme.colors.success : Theme.colors.danger;
}

function toneForScore(score: number | null): HomeMetric['tone'] {
  if (score === null) {
    return 'neutral';
  }
  if (score >= 70) {
    return 'positive';
  }
  if (score >= 50) {
    return 'warning';
  }
  return 'negative';
}

function riskTone(label: string): HomeMetric['tone'] {
  const value = label.toLowerCase();
  if (value.includes('low')) {
    return 'positive';
  }
  if (value.includes('high') || value.includes('elevated')) {
    return 'negative';
  }
  if (value.includes('moderate')) {
    return 'warning';
  }
  return 'neutral';
}

function positioningTone(label: string): HomeMetric['tone'] {
  const value = label.toLowerCase();
  if (value.includes('defensive') || value.includes('risk-off')) {
    return 'negative';
  }
  if (value.includes('selective') || value.includes('moderate')) {
    return 'warning';
  }
  if (value.includes('aggressive') || value.includes('strong')) {
    return 'positive';
  }
  return 'neutral';
}

function toneColor(tone: HomeMetric['tone']) {
  switch (tone) {
    case 'positive':
      return Theme.colors.success;
    case 'warning':
      return Theme.colors.warning;
    case 'negative':
      return Theme.colors.danger;
    default:
      return Theme.colors.textMuted;
  }
}

const styles = StyleSheet.create({
  stack: {
    gap: HOME_LAYOUT.cardGap,
  },
  heroCard: {
    backgroundColor: Theme.colors.card,
    borderColor: Theme.colors.border,
    borderRadius: HOME_LAYOUT.cardRadius,
    borderWidth: 1,
    paddingHorizontal: HOME_LAYOUT.cardPaddingHorizontal,
    paddingVertical: HOME_LAYOUT.cardPaddingVertical,
  },
  homeCard: {
    backgroundColor: Theme.colors.card,
    borderColor: Theme.colors.border,
    borderRadius: HOME_LAYOUT.cardRadius,
    borderWidth: 1,
    paddingHorizontal: HOME_LAYOUT.cardPaddingHorizontal,
    paddingVertical: HOME_LAYOUT.cardPaddingVertical,
  },
  pressed: {
    opacity: 0.78,
  },
  sectionHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: HOME_LAYOUT.compactGap,
    justifyContent: 'space-between',
    marginBottom: HOME_LAYOUT.sectionHeaderGap,
    minHeight: 24,
  },
  sectionHeaderText: {
    flex: 1,
    gap: 2,
  },
  sectionTitle: {
    color: Theme.colors.text,
    fontSize: 16,
    fontWeight: '900',
  },
  sectionSubtitle: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '700',
  },
  chevron: {
    color: Theme.colors.textMuted,
    fontSize: 24,
    fontWeight: '900',
    lineHeight: 24,
  },
  playbookStack: {
    gap: HOME_LAYOUT.contentGap,
  },
  heroHeadline: {
    color: Theme.colors.text,
    fontSize: 24,
    fontWeight: '900',
    lineHeight: 29,
  },
  heroMetricRow: {
    flexDirection: 'row',
    gap: HOME_LAYOUT.compactGap,
  },
  compactMetric: {
    backgroundColor: Theme.colors.cardMuted,
    borderRadius: Theme.radii.small,
    flex: 1,
    justifyContent: 'center',
    minHeight: 54,
    paddingHorizontal: HOME_LAYOUT.compactGap,
    paddingVertical: HOME_LAYOUT.compactGap,
  },
  compactMetricValue: {
    fontSize: 15,
    fontWeight: '900',
    marginTop: Spacing.half,
  },
  mutedLabel: {
    color: Theme.colors.textMuted,
    fontSize: 10,
    fontWeight: '900',
    textTransform: 'uppercase',
  },
  summaryText: {
    color: Theme.colors.textMuted,
    fontSize: 13,
    fontWeight: '700',
    lineHeight: 18,
  },
  cardContentStack: {
    gap: HOME_LAYOUT.contentGap,
  },
  indexRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: HOME_LAYOUT.gridGap,
  },
  indexChip: {
    backgroundColor: Theme.colors.cardMuted,
    borderRadius: Theme.radii.small,
    flexBasis: '47%',
    flexGrow: 1,
    justifyContent: 'center',
    minHeight: 66,
    paddingHorizontal: HOME_LAYOUT.compactGap,
    paddingVertical: HOME_LAYOUT.compactGap,
  },
  indexSymbol: {
    color: Theme.colors.text,
    fontSize: 13,
    fontWeight: '900',
  },
  indexChange: {
    fontSize: 13,
    fontWeight: '900',
    marginTop: Spacing.half,
  },
  indexTrend: {
    color: Theme.colors.textMuted,
    fontSize: 10,
    fontWeight: '800',
    marginTop: Spacing.half,
  },
  inlineMetricRow: {
    flexDirection: 'row',
    gap: HOME_LAYOUT.compactGap,
  },
  inlineMetric: {
    backgroundColor: Theme.colors.cardMuted,
    borderRadius: Theme.radii.small,
    flex: 1,
    minHeight: 52,
    justifyContent: 'center',
    paddingHorizontal: HOME_LAYOUT.compactGap,
    paddingVertical: HOME_LAYOUT.compactGap,
  },
  inlineMetricValue: {
    fontSize: 13,
    fontWeight: '900',
    marginTop: Spacing.half,
  },
  leadershipRow: {
    gap: HOME_LAYOUT.compactGap,
  },
  leadershipList: {
    gap: HOME_LAYOUT.compactGap,
  },
  leadershipItemRow: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: HOME_LAYOUT.compactGap,
  },
  leadershipKind: {
    color: Theme.colors.textMuted,
    fontSize: 10,
    fontWeight: '900',
    minWidth: 42,
    textTransform: 'uppercase',
  },
  leadershipText: {
    color: Theme.colors.text,
    flexShrink: 1,
    fontSize: 12,
    fontWeight: '900',
  },
  splitGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: HOME_LAYOUT.compactGap,
  },
  splitGridStacked: {
    flexDirection: 'column',
  },
  splitPanel: {
    backgroundColor: Theme.colors.cardMuted,
    borderRadius: Theme.radii.small,
    flex: 1,
    minWidth: 145,
    paddingHorizontal: HOME_LAYOUT.contentGap,
    paddingVertical: HOME_LAYOUT.contentGap,
  },
  panelValue: {
    color: Theme.colors.text,
    fontSize: 15,
    fontWeight: '900',
    marginTop: Spacing.one,
  },
  panelSubtext: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '700',
    lineHeight: 17,
    marginTop: Spacing.one,
  },
  eventText: {
    color: Theme.colors.text,
    fontSize: 12,
    fontWeight: '800',
    marginTop: Spacing.one,
  },
  tickerRow: {
    flexDirection: 'row',
    gap: HOME_LAYOUT.compactGap,
  },
  tickerChip: {
    alignItems: 'center',
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    flex: 1,
    justifyContent: 'center',
    minHeight: 52,
    paddingHorizontal: HOME_LAYOUT.compactGap,
  },
  tickerText: {
    color: Theme.colors.text,
    fontSize: 16,
    fontWeight: '900',
  },
  tickerChange: {
    fontSize: 11,
    fontWeight: '900',
    marginTop: Spacing.half,
  },
  linkText: {
    color: Theme.colors.accent,
    fontSize: 12,
    fontWeight: '900',
  },
  insightHeadline: {
    color: Theme.colors.text,
    flex: 1,
    fontSize: 14,
    fontWeight: '900',
  },
  insightHeaderRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: HOME_LAYOUT.compactGap,
    marginBottom: HOME_LAYOUT.contentGap,
  },
  emptyText: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '700',
    lineHeight: 17,
  },
});
