import { StyleSheet, Text, View } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { EmptyState } from '@/components/ui/EmptyState';
import { ScoreGauge } from '@/components/ui/ScoreGauge';
import { SkeletonCard } from '@/components/ui/SkeletonCard';
import { StatusBadge, type Tone } from '@/components/ui/StatusBadge';
import {
  DetailGrid,
  InfoTile,
  NarrativeList,
  WarningCard,
  WatchlistSectionHeader,
} from '@/components/watchlist/WatchlistPrimitives';
import { Spacing, Theme } from '@/constants/theme';
import type { StockRatingItem } from '@/types/market';
import { getRatingColor } from '@/utils/colors';
import { formatNullableNumber } from '@/utils/formatters';

export function StockRatingSection({
  error,
  items,
  loading,
}: {
  error: string | null;
  items: StockRatingItem[];
  loading: boolean;
}) {
  return (
    <>
      <WatchlistSectionHeader
        title="Stock Intelligence Ratings"
        subtitle="Transparent 0-100 ratings from relative strength, setup quality, market alignment, and risk."
      />

      {loading ? <SkeletonCard compact rows={4} /> : null}

      {error ? <WarningCard title="Stock ratings unavailable" message={error} /> : null}

      {!loading && !error && items.length ? (
        <View style={styles.list}>
          {items.map((item, index) => (
            <StockRatingCard key={item.symbol} item={item} rank={index + 1} />
          ))}
        </View>
      ) : null}

      {!loading && !error && items.length === 0 ? (
        <EmptyState
          title="No stock ratings"
          message="Stock intelligence ratings will appear here when available."
        />
      ) : null}
    </>
  );
}

function StockRatingCard({ item, rank }: { item: StockRatingItem; rank: number }) {
  return (
    <DashboardCard accentColor={getRatingColor(item.rating)}>
      <View style={styles.header}>
        <View style={styles.rankBadge}>
          <Text style={styles.rankLabel}>Rank</Text>
          <Text style={styles.rankValue}>{rank}</Text>
        </View>
        <View style={styles.titleBlock}>
          <Text style={styles.symbol}>{item.symbol}</Text>
          <Text style={styles.sector}>{item.status}</Text>
        </View>
        <StatusBadge label={item.rating} tone={getRatingTone(item.rating)} />
      </View>

      <View style={styles.scoreRow}>
        <ScoreGauge label="Overall Score" size="medium" value={item.overall_score} />
        <View style={styles.scoreMeta}>
          <StatusBadge label={`Risk ${item.risk_level}`} tone={getRiskTone(item.risk_level)} />
          <Text style={styles.riskText}>
            Component scores below explain the rating.
          </Text>
        </View>
      </View>

      <DetailGrid>
        <InfoTile label="Relative Strength" value={formatNullableNumber(item.components.relative_strength)} />
        <InfoTile label="Pattern Quality" value={formatNullableNumber(item.components.pattern_quality)} />
        <InfoTile label="Sector Strength" value={formatNullableNumber(item.components.sector_strength)} />
        <InfoTile label="Market Alignment" value={formatNullableNumber(item.components.market_alignment)} />
        <InfoTile label="Institutional Support" value={formatNullableNumber(item.components.institutional_support)} />
        <InfoTile label="Risk Control" value={formatNullableNumber(item.components.risk_control)} />
      </DetailGrid>

      <View style={styles.narrativeGrid}>
        <NarrativeList title="Strengths" items={item.strengths} tone="success" />
        <NarrativeList title="Warnings" items={item.warnings} tone="warning" />
      </View>

      <Text style={styles.explanation}>{item.explanation || 'N/A'}</Text>
    </DashboardCard>
  );
}

function getRatingTone(rating?: string): Tone {
  if (rating === 'A' || rating === 'A+') {
    return 'success';
  }
  if (rating === 'B') {
    return 'info';
  }
  if (rating === 'C') {
    return 'warning';
  }
  if (rating === 'D' || rating === 'F') {
    return 'danger';
  }
  return 'muted';
}

function getRiskTone(riskLevel?: string): Tone {
  switch (riskLevel?.toLowerCase()) {
    case 'low':
      return 'success';
    case 'moderate':
      return 'info';
    case 'elevated':
      return 'warning';
    case 'high':
      return 'danger';
    default:
      return 'muted';
  }
}

const styles = StyleSheet.create({
  list: {
    gap: Spacing.two,
  },
  header: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
    marginBottom: Spacing.twoAndHalf,
  },
  rankBadge: {
    alignItems: 'center',
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    height: 50,
    justifyContent: 'center',
    width: 54,
  },
  rankLabel: {
    color: Theme.colors.textMuted,
    fontSize: 10,
    fontWeight: '900',
    textTransform: 'uppercase',
  },
  rankValue: {
    color: Theme.colors.text,
    fontSize: 18,
    fontWeight: '900',
  },
  titleBlock: {
    flex: 1,
  },
  symbol: {
    color: Theme.colors.text,
    fontSize: 22,
    fontWeight: '900',
  },
  sector: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '800',
    marginTop: Spacing.one,
  },
  scoreRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
    marginBottom: Spacing.twoAndHalf,
  },
  scoreMeta: {
    flex: 1,
    gap: Spacing.one,
  },
  riskText: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '700',
    lineHeight: 17,
  },
  narrativeGrid: {
    gap: Spacing.two,
    marginTop: Spacing.twoAndHalf,
  },
  explanation: {
    color: Theme.colors.textMuted,
    fontSize: 13,
    fontWeight: '700',
    lineHeight: 20,
    marginTop: Spacing.twoAndHalf,
  },
});
