import { useMemo, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { DetailModal } from '@/components/ui/DetailModal';
import { TabbedDetailPanel } from '@/components/ui/TabbedDetailPanel';
import {
  SectionSummary,
} from '@/components/watchlist/WatchlistPrimitives';
import { RiskPlanSection } from '@/components/watchlist/RiskPlanSection';
import { Spacing, Theme } from '@/constants/theme';
import { AskCopilotButton } from '@/features/copilot/components/AskCopilotButton';
import { createCopilotContext } from '@/features/copilot/context/buildScreenContext';
import { StockCompareSections } from '@/features/stock-detail/compare/components/StockCompareSections';
import { StockDetailHeader } from '@/features/stock-detail/components/StockDetailHeader';
import { StockOverviewSections } from '@/features/stock-detail/components/StockOverviewSections';
import { buildStockDetailOverview } from '@/features/stock-detail/stockDetailPresenter';
import { StockSignalsSections } from '@/features/stock-detail/signals/components/StockSignalsSections';
import { StockTechnicalSections } from '@/features/stock-detail/technical/components/StockTechnicalSections';
import { buildStockTechnicalViewModel } from '@/features/stock-detail/technical/technicalViewModel';
import { DataStatusDot, WatchlistSignalBadge } from '@/features/watchlist/components/WatchlistSignalBadge';
import type { WatchlistClassification } from '@/features/watchlist/types';
import { useStockAnalysisDetails } from '@/hooks/useStockAnalysisDetails';
import type {
  DetectedPattern,
  RelativeStrengthItem,
  RiskPlan,
  StockRatingItem,
  SupportResistanceResponse,
  TrendlineResponse,
  VolumeAnalysis,
  WatchlistItem,
} from '@/types/market';
import { formatNullablePercent } from '@/utils/formatters';

export function StockCard({
  patterns = [],
  relativeStrength,
  riskPlan,
  stock,
  classification,
  stockRating,
  supportResistance,
  trendline,
  volumeAnalysis,
  onRemove,
}: {
  patterns?: DetectedPattern[];
  relativeStrength?: RelativeStrengthItem;
  riskPlan?: RiskPlan;
  stock: WatchlistItem;
  classification?: WatchlistClassification;
  stockRating?: StockRatingItem;
  supportResistance?: SupportResistanceResponse;
  trendline?: TrendlineResponse;
  volumeAnalysis?: VolumeAnalysis;
  onRemove?: (symbol: string) => void;
}) {
  const [detailsVisible, setDetailsVisible] = useState(false);
  const detailState = useStockAnalysisDetails(stock.ticker, detailsVisible);
  const activeMultiTimeframeSignals = detailState.data?.multiTimeframeSignals;
  const activeLeadershipSignal = detailState.data?.leadershipSignal;
  const activePatterns = detailState.data?.patterns ?? patterns;
  const activeRelativeStrength = relativeStrength ?? detailState.data?.relativeStrength;
  const activeRiskPlan = riskPlan ?? detailState.data?.riskPlan;
  const activeStockRating = stockRating ?? detailState.data?.stockRating;
  const activeSupportResistance = supportResistance ?? detailState.data?.supportResistance;
  const activeTrendline = trendline ?? detailState.data?.trendline;
  const activeVolumeAnalysis = volumeAnalysis ?? detailState.data?.volumeAnalysis;
  const mainPattern = activePatterns[0];
  const overviewModel = useMemo(
    () => buildStockDetailOverview({
      relativeStrength: activeRelativeStrength,
      riskPlan: activeRiskPlan,
      stock,
      stockRating: activeStockRating,
      supportResistance: activeSupportResistance,
      volumeAnalysis: activeVolumeAnalysis,
    }),
    [
      activeRelativeStrength,
      activeRiskPlan,
      activeStockRating,
      activeSupportResistance,
      activeVolumeAnalysis,
      stock,
    ],
  );
  const technicalModel = useMemo(
    () => buildStockTechnicalViewModel({
      pattern: mainPattern,
      stock,
      supportResistance: activeSupportResistance,
      trendline: activeTrendline,
      volumeAnalysis: activeVolumeAnalysis,
    }),
    [activeSupportResistance, activeTrendline, activeVolumeAnalysis, mainPattern, stock],
  );
  const copilotContext = useMemo(
    () => createCopilotContext({
      payload: {
        classification,
        leadershipSignal: activeLeadershipSignal,
        multiTimeframeSignals: activeMultiTimeframeSignals,
        overview: overviewModel,
        patterns: activePatterns,
        relativeStrength: activeRelativeStrength,
        riskPlan: activeRiskPlan,
        stock,
        stockRating: activeStockRating,
        supportResistance: activeSupportResistance,
        technical: technicalModel,
        trendline: activeTrendline,
        volumeAnalysis: activeVolumeAnalysis,
      },
      routeName: '/watchlist',
      screenTitle: `${stock.ticker} Stock Detail`,
      screenType: 'stock',
      sourceState: overviewModel.sourceLabel?.toLowerCase().includes('live') ? 'live' : overviewModel.sourceLabel?.toLowerCase().includes('mixed') ? 'mixed' : 'mock',
    }),
    [
      activeLeadershipSignal,
      activeMultiTimeframeSignals,
      activePatterns,
      activeRelativeStrength,
      activeRiskPlan,
      activeStockRating,
      activeSupportResistance,
      activeTrendline,
      activeVolumeAnalysis,
      classification,
      overviewModel,
      stock,
      technicalModel,
    ],
  );
  const changeTone = getChangeTone(stock.change_percent);

  return (
    <>
      <Pressable
        accessibilityLabel={`Open ${stock.ticker} full analysis${classification ? `, ${classification.reason}` : ''}`}
        accessibilityRole="button"
        onPress={() => setDetailsVisible(true)}
        style={styles.tickerRow}>
        <View style={styles.tickerMain}>
          <Text numberOfLines={1} style={styles.tickerSymbol}>{stock.ticker}</Text>
        </View>
        <Text style={[styles.changeValue, { color: changeTone }]}>
          {formatNullablePercent(stock.change_percent)}
        </Text>
        {classification ? (
          <View style={styles.signalBlock}>
            <WatchlistSignalBadge classification={classification} />
            <DataStatusDot status={classification.dataStatus} />
          </View>
        ) : null}
        {onRemove ? (
          <Pressable
            accessibilityLabel={`Remove ${stock.ticker} from watchlist`}
            accessibilityRole="button"
            hitSlop={8}
            onPress={(event) => {
              event.stopPropagation();
              onRemove(stock.ticker);
            }}
            style={styles.removeButton}>
            <Text style={styles.removeText}>★</Text>
          </Pressable>
        ) : null}
        <Text style={styles.chevron}>›</Text>
      </Pressable>

      <DetailModal
        onClose={() => setDetailsVisible(false)}
        subtitle="Stock intelligence"
        title={stock.ticker}
        visible={detailsVisible}>
        {detailState.loading ? <SectionSummary>Loading detailed analysis...</SectionSummary> : null}
        {detailState.error ? <SectionSummary>{detailState.error}</SectionSummary> : null}
        <AskCopilotButton
          context={copilotContext}
          prompt={`Explain ${stock.ticker}'s current setup and main risk.`}
        />
        <StockDetailHeader model={overviewModel} />
        <TabbedDetailPanel
          initialKey="overview"
          tabs={[
            {
              key: 'overview',
              label: 'Overview',
              content: (
                <StockOverviewSections model={overviewModel} />
              ),
            },
            {
              key: 'technical',
              label: 'Technical',
              content: (
                <StockTechnicalSections
                  model={technicalModel}
                  pattern={mainPattern}
                  supportResistance={activeSupportResistance}
                  trendline={activeTrendline}
                  volumeAnalysis={activeVolumeAnalysis}
                />
              ),
            },
            {
              key: 'signals',
              label: 'Signals',
              content: (
                <StockSignalsSections
                  leadershipSignal={activeLeadershipSignal}
                  multiTimeframeSignals={activeMultiTimeframeSignals}
                  relativeStrength={activeRelativeStrength}
                  volumeAnalysis={activeVolumeAnalysis}
                />
              ),
            },
            {
              key: 'risk',
              label: 'Risk',
              content: (
                <RiskPlanSection
                  riskPlan={activeRiskPlan}
                  showTitle
                  supportResistance={activeSupportResistance}
                />
              ),
            },
            {
              key: 'compare',
              label: 'Compare',
              content: (
                <StockCompareSections
                  stock={stock}
                  volumeAnalysis={activeVolumeAnalysis}
                />
              ),
            },
          ]}
        />
      </DetailModal>
    </>
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

const styles = StyleSheet.create({
  tickerRow: {
    alignItems: 'center',
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    flexDirection: 'row',
    gap: Spacing.two,
    minHeight: 56,
    paddingHorizontal: Spacing.twoAndHalf,
    paddingVertical: Spacing.one,
  },
  tickerMain: {
    flex: 1,
    minWidth: 0,
  },
  tickerSymbol: {
    color: Theme.colors.text,
    fontSize: 18,
    fontWeight: '900',
  },
  changeValue: {
    fontSize: 15,
    fontWeight: '900',
    minWidth: 74,
    textAlign: 'right',
  },
  removeButton: {
    alignItems: 'center',
    borderRadius: Theme.radii.pill,
    height: 44,
    justifyContent: 'center',
    width: 30,
  },
  removeText: {
    color: Theme.colors.warning,
    fontSize: 16,
    fontWeight: '900',
  },
  chevron: {
    color: Theme.colors.textMuted,
    fontSize: 28,
    fontWeight: '700',
  },
  signalBlock: {
    alignItems: 'flex-end',
    gap: Spacing.half,
    minWidth: 104,
  },
});
