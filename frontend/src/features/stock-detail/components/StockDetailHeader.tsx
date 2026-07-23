import { StyleSheet, Text, View } from 'react-native';

import { StatusBadge } from '@/components/ui/StatusBadge';
import { Spacing, Theme, Typography } from '@/constants/theme';
import {
  getRiskTone,
  stockToneToBadgeTone,
} from '@/features/stock-detail/stockDetailSemanticColors';
import type { StockDetailOverviewModel } from '@/features/stock-detail/stockDetailPresenter';
import { StockMiniChart } from '@/features/stock-detail/components/StockMiniChart';
import type { HistoryData } from '@/types/market';

export function StockDetailHeader({ chartHistory, model }: { chartHistory?: HistoryData | null; model: StockDetailOverviewModel }) {
  const changeTone = getChangeTone(model.quote.changePercent);

  return (
    <View style={styles.headerCard}>
      <View style={styles.topRow}>
        <View style={styles.identityBlock}>
          <Text numberOfLines={1} style={styles.symbol}>{model.symbol}</Text>
          <Text numberOfLines={1} style={styles.status}>{model.assessmentLabel}</Text>
        </View>
        <View style={styles.priceBlock}>
          <Text style={styles.price}>{formatCurrency(model.quote.price)}</Text>
          <Text style={[styles.change, { color: changeTone }]}>
            {formatMove(model.quote.change, model.quote.changePercent)}
          </Text>
        </View>
      </View>

      <View style={styles.badgeRow}>
        <StatusBadge label={model.sourceLabel} tone={stockToneToBadgeTone(model.sourceTone)} />
        <StatusBadge label={`${model.riskLevel} risk`} tone={stockToneToBadgeTone(getRiskTone(model.riskLevel))} />
      </View>

      <StockMiniChart
        history={chartHistory}
        quote={{
          price: model.quote.price,
          source: model.quote.source,
          timestamp: model.quote.timestamp,
        }}
        symbol={model.symbol}
      />
    </View>
  );
}

function getChangeTone(value?: number | null) {
  if (typeof value !== 'number') {
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

function formatCurrency(value?: number | null): string {
  return typeof value === 'number' && Number.isFinite(value) && value > 0 ? `$${value.toFixed(2)}` : 'Price unavailable';
}

function formatMove(change?: number | null, percent?: number | null): string {
  const pieces: string[] = [];
  if (typeof change === 'number' && Number.isFinite(change)) {
    pieces.push(`${change >= 0 ? '+' : ''}${change.toFixed(2)}`);
  }
  if (typeof percent === 'number' && Number.isFinite(percent)) {
    pieces.push(`${percent >= 0 ? '+' : ''}${percent.toFixed(2)}%`);
  }
  return pieces.length ? pieces.join(' · ') : 'Move unavailable';
}

const styles = StyleSheet.create({
  headerCard: {
    backgroundColor: Theme.colors.card,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.card,
    borderWidth: 1,
    gap: Spacing.twoAndHalf,
    padding: Spacing.three,
  },
  topRow: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  identityBlock: {
    flex: 1,
    minWidth: 0,
  },
  symbol: {
    color: Theme.colors.text,
    fontSize: Typography.entityTitle.fontSize,
    fontWeight: Typography.weights.heavy,
    lineHeight: 34,
  },
  status: {
    color: Theme.colors.textMuted,
    fontSize: Typography.control.fontSize,
    fontWeight: Typography.weights.strong,
    marginTop: Spacing.half,
  },
  priceBlock: {
    alignItems: 'flex-end',
    maxWidth: '46%',
  },
  price: {
    color: Theme.colors.text,
    fontSize: Typography.detailTitle.fontSize,
    fontWeight: Typography.weights.strong,
  },
  change: {
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.strong,
    marginTop: Spacing.half,
    textAlign: 'right',
  },
  badgeRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.one,
  },
});
