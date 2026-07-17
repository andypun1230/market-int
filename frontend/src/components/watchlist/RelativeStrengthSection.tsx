import { StyleSheet, Text, View } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { EmptyState } from '@/components/ui/EmptyState';
import { SkeletonCard } from '@/components/ui/SkeletonCard';
import {
  DetailGrid,
  InfoTile,
  WarningCard,
  WatchlistSectionHeader,
} from '@/components/watchlist/WatchlistPrimitives';
import { Spacing, Theme } from '@/constants/theme';
import type { RelativeStrengthItem } from '@/types/market';
import { getRelativeStrengthColor, getRelativeStrengthSoftColor } from '@/utils/colors';
import { formatNullableNumber, formatNullablePercent } from '@/utils/formatters';

export function RelativeStrengthSection({
  error,
  items,
  loading,
}: {
  error: string | null;
  items: RelativeStrengthItem[];
  loading: boolean;
}) {
  return (
    <>
      <WatchlistSectionHeader
        title="Relative Strength Ranking"
        subtitle="Watchlist leadership versus SPY, QQQ, and sector benchmarks."
      />

      {loading ? <SkeletonCard compact rows={4} /> : null}

      {error ? (
        <WarningCard title="Relative strength unavailable" message={error} />
      ) : null}

      {!loading && !error && items.length ? (
        <View style={styles.list}>
          {items.map((item) => (
            <RelativeStrengthCard key={item.symbol} item={item} />
          ))}
        </View>
      ) : null}

      {!loading && !error && items.length === 0 ? (
        <EmptyState
          title="No relative strength data"
          message="Relative strength rankings will appear here when available."
        />
      ) : null}
    </>
  );
}

function RelativeStrengthCard({ item }: { item: RelativeStrengthItem }) {
  return (
    <DashboardCard accentColor={getRelativeStrengthColor(item.status)}>
      <View style={styles.header}>
        <View style={styles.rankBadge}>
          <Text style={styles.rankLabel}>Rank</Text>
          <Text style={styles.rankValue}>{formatNullableNumber(item.rank)}</Text>
        </View>
        <View style={styles.titleBlock}>
          <Text style={styles.symbol}>{item.symbol}</Text>
          <Text style={styles.sector}>{item.sector}</Text>
        </View>
        <View style={[styles.statusBadge, { backgroundColor: getRelativeStrengthSoftColor(item.status) }]}>
          <Text style={[styles.statusText, { color: getRelativeStrengthColor(item.status) }]}>
            {item.status}
          </Text>
        </View>
      </View>

      <View style={styles.scoreRow}>
        <Text style={styles.scoreValue}>{formatNullableNumber(item.overall_rs_score)}</Text>
        <Text style={styles.scoreLabel}>Overall RS Score</Text>
      </View>

      <DetailGrid>
        <InfoTile label="RS vs SPY" value={formatNullableNumber(item.rs_vs_spy)} />
        <InfoTile label="RS vs QQQ" value={formatNullableNumber(item.rs_vs_qqq)} />
        <InfoTile label="RS vs Sector" value={formatNullableNumber(item.rs_vs_sector)} />
        <InfoTile label="20D Return" value={formatNullablePercent(item.return_20d)} />
        <InfoTile label="60D Return" value={formatNullablePercent(item.return_60d)} />
      </DetailGrid>
    </DashboardCard>
  );
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
  statusBadge: {
    borderRadius: Theme.radii.pill,
    paddingHorizontal: Spacing.twoAndHalf,
    paddingVertical: Spacing.one,
  },
  statusText: {
    fontSize: 12,
    fontWeight: '900',
  },
  scoreRow: {
    alignItems: 'baseline',
    flexDirection: 'row',
    gap: Spacing.two,
    marginBottom: Spacing.twoAndHalf,
  },
  scoreValue: {
    color: Theme.colors.text,
    fontSize: 30,
    fontWeight: '900',
  },
  scoreLabel: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '900',
    textTransform: 'uppercase',
  },
});
