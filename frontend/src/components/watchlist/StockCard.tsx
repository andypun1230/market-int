import { useMemo, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { AppIcon } from '@/components/ui/AppIcon';
import { DetailModal } from '@/components/ui/DetailModal';
import { SegmentedControl } from '@/components/ui/SegmentedControl';
import {
  SectionSummary,
} from '@/components/watchlist/WatchlistPrimitives';
import { RiskPlanSection } from '@/components/watchlist/RiskPlanSection';
import { Spacing, Theme, Typography } from '@/constants/theme';
import { AskCopilotButton } from '@/features/copilot/components/AskCopilotButton';
import { createCopilotContext } from '@/features/copilot/context/buildScreenContext';
import { MaterialEventsCard } from '@/features/context-intelligence/components/ContextIntelligenceCards';
import { shouldRequestStockMaterialEvents } from '@/features/context-intelligence/consumerPolicy';
import { StockCompareSections } from '@/features/stock-detail/compare/components/StockCompareSections';
import { StockDetailHeader } from '@/features/stock-detail/components/StockDetailHeader';
import { applyCurrentPrice } from '@/features/stock-detail/currentPrice';
import { StockOverviewSections } from '@/features/stock-detail/components/StockOverviewSections';
import { StockThemeContext } from '@/features/stock-detail/components/StockThemeContext';
import { buildStockDetailOverview } from '@/features/stock-detail/stockDetailPresenter';
import { StockSignalsSections } from '@/features/stock-detail/signals/components/StockSignalsSections';
import { StockTechnicalSections } from '@/features/stock-detail/technical/components/StockTechnicalSections';
import { buildStockTechnicalViewModel } from '@/features/stock-detail/technical/technicalViewModel';
import { DataStatusDot, WatchlistSignalBadge } from '@/features/watchlist/components/WatchlistSignalBadge';
import { getWatchlistDecisionLabel, getWatchlistDecisionStatus } from '@/features/watchlist/watchlistDecision';
import type { WatchlistViewMode } from '@/features/watchlist/watchlistListControls';
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
  openDetails = false,
  openDetailTab,
  deepLinkNonce,
  viewMode = 'detailed',
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
  openDetails?: boolean;
  openDetailTab?: string;
  deepLinkNonce?: string;
  viewMode?: WatchlistViewMode;
}) {
  const [detailsVisible, setDetailsVisible] = useState(false);
  const deepLinkKey = openDetails ? `${stock.ticker}:${openDetailTab ?? 'overview'}:${deepLinkNonce ?? 'initial'}` : null;
  const [dismissedDeepLinkKey, setDismissedDeepLinkKey] = useState<string | null>(null);
  const [detailTabSelection, setDetailTabSelection] = useState({ deepLinkKey: null as string | null, tab: 'overview' });
  const requestedDetailTab = openDetailTab && ['overview', 'technical', 'signals', 'risk', 'compare'].includes(openDetailTab)
    ? openDetailTab
    : 'overview';
  const selectedDetailTab = detailTabSelection.deepLinkKey === deepLinkKey ? detailTabSelection.tab : requestedDetailTab;
  const showDetails = detailsVisible || Boolean(openDetails && deepLinkKey !== dismissedDeepLinkKey);
  const detailState = useStockAnalysisDetails(stock.ticker, showDetails);
  const activeMultiTimeframeSignals = detailState.data?.multiTimeframeSignals;
  const activeLeadershipSignal = detailState.data?.leadershipSignal;
  const activePatterns = detailState.data?.patterns ?? patterns;
  const activeRelativeStrength = relativeStrength ?? detailState.data?.relativeStrength;
  const activeRiskPlan = riskPlan ?? detailState.data?.riskPlan;
  const activeStockRating = stockRating ?? detailState.data?.stockRating;
  const activeSupportResistance = supportResistance ?? detailState.data?.supportResistance;
  const activeTrendline = trendline ?? detailState.data?.trendline;
  const activeVolumeAnalysis = volumeAnalysis ?? detailState.data?.volumeAnalysis;
  const currentPrice = detailState.data?.currentPrice;
  const detailStock = useMemo(
    () => applyCurrentPrice(stock, currentPrice ?? {
      change: null,
      changePercent: null,
      isLive: false,
      price: null,
      source: 'unavailable',
      sourceLabel: 'Price unavailable',
      timestamp: null,
    }),
    [currentPrice, stock],
  );
  const mainPattern = activePatterns[0];
  const overviewModel = useMemo(
    () => buildStockDetailOverview({
      currentPrice,
      relativeStrength: activeRelativeStrength,
      riskPlan: activeRiskPlan,
      stock: detailStock,
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
      detailStock,
      currentPrice,
    ],
  );
  const technicalModel = useMemo(
    () => buildStockTechnicalViewModel({
      currentPrice,
      pattern: mainPattern,
      stock: detailStock,
      supportResistance: activeSupportResistance,
      trendline: activeTrendline,
      volumeAnalysis: activeVolumeAnalysis,
    }),
    [activeSupportResistance, activeTrendline, activeVolumeAnalysis, currentPrice, detailStock, mainPattern],
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
        selectedDetailTab,
        stock: detailStock,
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
      detailStock,
      selectedDetailTab,
      stock.ticker,
      technicalModel,
    ],
  );
  const changeTone = getChangeTone(stock.change_percent);
  const decisionStatus = classification
    ? getWatchlistDecisionStatus(classification)
    : stock.setup ?? 'Waiting for a clearer setup.';
  const compactDecisionLabel = classification ? getWatchlistDecisionLabel(classification) : 'Waiting';
  const compact = viewMode === 'compact';
  const urgencyColor = getUrgencyColor(classification);
  const detailTabs = [
    {
      key: 'overview',
      label: 'Overview',
      content: (
        <>
          <StockOverviewSections model={overviewModel} />
          <StockThemeContext mappings={detailState.data?.themeMappings} />
          <MaterialEventsCard
            enabled={shouldRequestStockMaterialEvents(showDetails, selectedDetailTab)}
            symbol={stock.ticker}
          />
        </>
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
          currentPrice={currentPrice}
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
          stock={detailStock}
          volumeAnalysis={activeVolumeAnalysis}
        />
      ),
    },
  ];
  const activeDetailTab = detailTabs.find((tab) => tab.key === selectedDetailTab) ?? detailTabs[0];

  return (
    <>
      <View style={[styles.tickerRow, compact && styles.tickerRowCompact, classification ? { borderLeftColor: urgencyColor, borderLeftWidth: 3 } : null]}>
        <Pressable
          accessibilityLabel={`Open ${stock.ticker} full analysis${classification ? `, ${classification.reason}` : ''}`}
          accessibilityRole="button"
          onPress={() => {
            setDetailsVisible(true);
          }}
          style={[styles.tickerRowContent, compact && styles.tickerRowContentCompact]}>
          {compact ? (
            <View style={styles.compactHeadline}>
              <Text numberOfLines={1} style={styles.tickerSymbol}>{stock.ticker}</Text>
              <Text style={[styles.changeValue, styles.compactChangeValue, { color: changeTone }]}>
                {formatNullablePercent(stock.change_percent)}
              </Text>
              <Text numberOfLines={1} style={styles.compactDecision}>{compactDecisionLabel}</Text>
              {classification ? <DataStatusDot primarySignal={classification.primarySignal} status={classification.dataStatus} /> : null}
              <AppIcon name="chevronRight" size={14} />
            </View>
          ) : (
            <>
              <View style={styles.tickerHeadline}>
                <Text numberOfLines={1} style={styles.tickerSymbol}>{stock.ticker}</Text>
                <Text style={[styles.changeValue, { color: changeTone }]}>
                  {formatNullablePercent(stock.change_percent)}
                </Text>
                <AppIcon name="chevronRight" size={16} />
              </View>
              <View style={styles.decisionRow}>
                <Text numberOfLines={1} style={styles.decisionStatus}>{decisionStatus}</Text>
                {classification ? (
                  <View style={styles.signalBlock}>
                    <WatchlistSignalBadge classification={classification} />
                    <DataStatusDot primarySignal={classification.primarySignal} status={classification.dataStatus} />
                  </View>
                ) : null}
              </View>
            </>
          )}
        </Pressable>
        {onRemove ? (
          <Pressable
            accessibilityLabel={`Remove ${stock.ticker} from watchlist`}
            accessibilityRole="button"
            hitSlop={8}
            onPress={() => onRemove(stock.ticker)}
            style={styles.removeButton}>
            <AppIcon color={Theme.colors.warning} name="saved" size={17} />
          </Pressable>
        ) : null}
      </View>

      <DetailModal
        onClose={() => {
          setDismissedDeepLinkKey(deepLinkKey);
          setDetailsVisible(false);
        }}
        scrollHeader={(
          <>
            {detailState.loading ? <SectionSummary>Loading detailed analysis...</SectionSummary> : null}
            {detailState.data?.snapshotStatus === 'initializing' ? <SectionSummary>Preparing live history...</SectionSummary> : null}
            {detailState.error ? <SectionSummary>{detailState.error}</SectionSummary> : null}
            <AskCopilotButton
              context={copilotContext}
              prompt={`Explain ${stock.ticker}'s current setup and main risk.`}
            />
            <StockDetailHeader chartHistory={detailState.data?.chartHistory} model={overviewModel} />
          </>
        )}
        stickyHeader={(
          <SegmentedControl
            compact
            dense
            fullWidth
            options={detailTabs.map((tab) => ({ key: tab.key, label: tab.label }))}
            selectedKey={activeDetailTab.key}
            onChange={(tab) => setDetailTabSelection({ deepLinkKey, tab })}
          />
        )}
        subtitle="Stock intelligence"
        title={stock.ticker}
        visible={showDetails}>
        <View style={styles.detailTabContent}>{activeDetailTab.content}</View>
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

function getUrgencyColor(classification?: WatchlistClassification) {
  if (!classification) return Theme.colors.border;
  if (classification.severity === 'critical') return Theme.colors.danger;
  if (classification.severity === 'warning') return Theme.colors.warning;
  if (classification.severity === 'positive') return Theme.colors.success;
  return Theme.colors.border;
}

const styles = StyleSheet.create({
  detailTabContent: {
    gap: Spacing.three,
  },
  tickerRow: {
    alignItems: 'center',
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    flexDirection: 'row',
    gap: Spacing.two,
    minHeight: 64,
    paddingHorizontal: Spacing.twoAndHalf,
    paddingVertical: Spacing.one,
  },
  tickerRowCompact: {
    minHeight: 52,
    paddingVertical: Spacing.half,
  },
  tickerRowContent: {
    flex: 1,
    gap: Spacing.half,
    minWidth: 0,
  },
  tickerRowContentCompact: {
    justifyContent: 'center',
  },
  tickerSymbol: {
    color: Theme.colors.text,
    flex: 1,
    fontSize: Typography.sectionTitle.fontSize,
    fontWeight: Typography.weights.strong,
  },
  changeValue: {
    fontSize: Typography.bodyLarge.fontSize,
    fontWeight: Typography.weights.strong,
    minWidth: 66,
    textAlign: 'right',
  },
  compactChangeValue: {
    minWidth: 60,
  },
  compactChevron: {
    color: Theme.colors.textMuted,
    fontSize: Typography.sectionHero.fontSize,
    fontWeight: Typography.weights.emphasis,
  },
  compactDecision: {
    color: Theme.colors.textMuted,
    fontSize: Typography.caption.fontSize,
    fontWeight: Typography.weights.strong,
    minWidth: 54,
    textAlign: 'right',
  },
  compactHeadline: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.one,
  },
  decisionRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.one,
    minWidth: 0,
  },
  decisionStatus: {
    color: Theme.colors.textMuted,
    flex: 1,
    fontSize: Typography.caption.fontSize,
    fontWeight: Typography.weights.strong,
    minWidth: 0,
  },
  removeButton: {
    alignItems: 'center',
    borderRadius: Theme.radii.pill,
    height: 44,
    justifyContent: 'center',
    width: 44,
  },
  removeText: {
    color: Theme.colors.warning,
    fontSize: Typography.supportTitle.fontSize,
    fontWeight: Typography.weights.strong,
  },
  chevron: {
    color: Theme.colors.textMuted,
    fontSize: Typography.entityTitle.fontSize,
    fontWeight: Typography.weights.emphasis,
  },
  signalBlock: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.half,
    maxWidth: '48%',
  },
  tickerHeadline: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
  },
});
