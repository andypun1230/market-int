import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { useFocusEffect } from 'expo-router';
import { SymbolView } from 'expo-symbols';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { AppScreen } from '@/components/ui/AppScreen';
import { ErrorState } from '@/components/ui/ErrorState';
import { ExpandableSection } from '@/components/ui/ExpandableSection';
import { ProgressBar } from '@/components/ui/ProgressBar';
import { SkeletonCard } from '@/components/ui/SkeletonCard';
import { StatusBadge, type Tone } from '@/components/ui/StatusBadge';
import { Spacing, Theme } from '@/constants/theme';
import { AskCopilotButton } from '@/features/copilot/components/AskCopilotButton';
import { createCopilotContext } from '@/features/copilot/context/buildScreenContext';
import {
  buildBreadthDashboard,
  formatBreadthRatio,
  type AdvanceDeclineViewModel,
  type BreadthDashboardViewModel,
  type BreadthProfileMetric,
  type BreadthSignalTone,
  type HighLowViewModel,
  type MovingAverageBreadthViewModel,
  formatBreadthPercent,
} from '@/features/market/breadthAnalysis';
import {
  applyBreadthMockScenarioDashboard,
  BREADTH_MOCK_SCENARIOS,
  buildBreadthMockScenario,
  type BreadthMockScenarioKey,
} from '@/features/market/breadthMockScenarios';
import {
  buildDecisionDashboardViewModel,
  gaugeMarkerPercent,
  type DecisionChangeViewModel,
  type DecisionDashboardViewModel as DecisionViewModel,
  type DecisionTone,
  type FearGreedViewModel,
  type MarketCapRotationViewModel,
} from '@/features/market/decisionAnalysis';
import {
  buildDecisionLayerSummary,
  buildHealthComponents,
  buildHealthContributions,
  buildHealthOverviewSummary,
  buildHealthRadarData,
  calculateRadarGridPoints,
  calculateRadarPoints,
  classifyHealthDirection,
  deriveHealthDrivers,
  formatHealthDirection,
  formatHealthScore,
  getHealthHistoryBadgeLabel,
  getHealthSourceBadgeLabel,
  getSupportedHealthTrendRanges,
  type HealthComponentViewModel,
  type HealthContributionViewModel,
  type HealthDriver,
  type HealthRadarDatum,
  type HealthSnapshot,
  type HealthScoreTone,
  type HealthTrendPoint,
  type HealthDirection,
  classifyHealthScore,
} from '@/features/market/healthAnalysis';
import {
  analyzeIndexes,
  deriveMarketLeadershipTrend,
  getIndexSourceLabel,
  indexSymbols,
  indexTimeframes,
  type IndexAnalysis,
  type IndexChartPoint,
  type IndexSymbol,
  type IndexTimeframe,
  type SignalTone as IndexSignalTone,
} from '@/features/market/indexAnalysis';
import {
  buildInstitutionalDashboardViewModel,
  type InstitutionalDashboardViewModel,
  type InstitutionalTone,
} from '@/features/market/institutionalAnalysis';
import { InstitutionalActivityChartCard } from '@/features/market/components/InstitutionalActivityChartCard';
import {
  buildMacroMockScenario,
  MACRO_MOCK_SCENARIO_OPTIONS,
  type MacroMockScenarioId,
} from '@/features/market/mock/macroScenarios';
import {
  buildMacroDashboardViewModel,
  formatRiskState,
  macroAssetDefinitions,
  macroTimeframeDays,
  macroTimeframes,
  type MacroAssetPerformance,
  type MacroDashboardViewModel,
  type MacroSourceKind,
  type MacroTimeframe,
} from '@/features/market/macroAnalysis';
import {
  buildMarketOverviewDashboard,
  type MarketOverviewDashboardViewModel,
  type MarketOverviewSignal,
  type MarketOverviewTone,
} from '@/features/market/marketOverviewAnalysis';
import {
  buildConcentrationBreadthSignal,
  buildWeightComparisonPair,
  getAvailableWeightPairs,
  type WeightComparisonPairId,
  type WeightComparisonViewModel,
} from '@/features/market/weightComparison';
import { useMarketDashboard } from '@/hooks/useMarketDashboard';
import { getLiveHistory } from '@/services/api';
import type {
  HistoryData,
  DecisionDashboardResponse,
  FearGreedResponse,
  IndexSnapshot,
  InstitutionalActivityResponse,
  InstitutionalIntelligenceResponse,
  MarketHealthResponse,
  MarketBreadthResponse,
  MarketCapRotationResponse,
  MarketCoreSnapshot,
  MarketRegime,
} from '@/types/market';
import { getSourceTone } from '@/utils/colors';

type MarketSection =
  | 'overview'
  | 'indexes'
  | 'health'
  | 'breadth'
  | 'decision'
  | 'institutions'
  | 'macro';

const MARKET_SECTIONS: {
  icon: { android: string; ios: string; web: string };
  key: MarketSection;
  label: string;
}[] = [
  { key: 'overview', label: 'Overview', icon: { ios: 'gauge.with.dots.needle.67percent', android: 'dashboard', web: 'gauge' } },
  { key: 'indexes', label: 'Indexes', icon: { ios: 'chart.line.uptrend.xyaxis', android: 'trending_up', web: 'chart.line.uptrend.xyaxis' } },
  { key: 'health', label: 'Health', icon: { ios: 'heart.text.square', android: 'monitor_heart', web: 'heart.text.square' } },
  { key: 'breadth', label: 'Breadth', icon: { ios: 'chart.bar.xaxis', android: 'bar_chart', web: 'chart.bar.xaxis' } },
  { key: 'decision', label: 'Decision', icon: { ios: 'brain.head.profile', android: 'psychology', web: 'brain.head.profile' } },
  { key: 'institutions', label: 'Institutions', icon: { ios: 'building.columns', android: 'account_balance', web: 'building.columns' } },
  { key: 'macro', label: 'Macro', icon: { ios: 'globe.americas', android: 'public', web: 'globe.americas' } },
];

export default function MarketScreen() {
  const [isFocused, setIsFocused] = useState(false);
  const [selectedSection, setSelectedSection] = useState<MarketSection>('overview');
  const [weightConcentration, setWeightConcentration] = useState<ReturnType<typeof buildConcentrationBreadthSignal>>(null);
  useFocusEffect(
    useCallback(() => {
      setIsFocused(true);
      return () => setIsFocused(false);
    }, []),
  );
  const {
    aiSummary,
    breadth,
    capRotation,
    core,
    decisionDashboard,
    detailsError,
    detailsLoading,
    error,
    fearGreed,
    indexes,
    institutionalActivity,
    institutionalIntelligence,
    loadDetails,
    loading,
    marketHealth,
    refetch,
    regime,
  } =
    useMarketDashboard(isFocused);
  const copilotContext = useMemo(
    () => createCopilotContext({
      payload: {
        breadth,
        capRotation,
        currentSection: selectedSection,
        decisionDashboard,
        fearGreed,
        indexes,
        institutionalActivity,
        institutionalIntelligence,
        marketHealth,
        regime,
      },
      routeName: '/market',
      screenTitle: `Market · ${selectedSection}`,
      screenType: 'market',
      sourceState: core?.overall_mode ?? marketHealth?.data_quality?.overall_mode ?? 'mixed',
    }),
    [breadth, capRotation, core, decisionDashboard, fearGreed, indexes, institutionalActivity, institutionalIntelligence, marketHealth, regime, selectedSection],
  );

  return (
    <AppScreen title="Market Regime" subtitle="Trend, breadth, volatility, and institutional activity.">
        {loading ? <MarketSkeleton /> : null}

        {error ? <ErrorState message={error} onRetry={refetch} /> : null}

        {!loading ? (
          <>
            <AskCopilotButton
              context={copilotContext}
              prompt={`Explain the ${selectedSection} section and the weakest signal.`}
            />
            <MarketSectionTabs
              onChange={setSelectedSection}
              selected={selectedSection}
            />

            {detailsError ? <ErrorState message={detailsError} /> : null}
            <MarketSectionContent
              aiSummary={aiSummary}
              breadth={breadth}
              capRotation={capRotation}
              core={core}
              decisionDashboard={decisionDashboard}
              detailsLoading={detailsLoading}
              fearGreed={fearGreed}
              indexes={indexes}
              institutionalActivity={institutionalActivity}
              institutionalIntelligence={institutionalIntelligence ?? decisionDashboard?.institutional_intelligence ?? null}
              loadDetails={loadDetails}
              marketHealth={marketHealth}
              regime={regime}
              section={selectedSection}
              weightConcentration={weightConcentration}
              onWeightConcentrationChange={setWeightConcentration}
            />
          </>
        ) : null}
    </AppScreen>
  );
}

function MarketSkeleton() {
  return (
    <View style={styles.skeletonStack}>
      <SkeletonCard rows={5} />
      <SkeletonCard rows={4} />
    </View>
  );
}

function MarketSectionTabs({
  onChange,
  selected,
}: {
  onChange: (section: MarketSection) => void;
  selected: MarketSection;
}) {
  const tabsRef = useRef<ScrollView | null>(null);
  useEffect(() => {
    if (selected === 'macro') {
      tabsRef.current?.scrollToEnd({ animated: true });
    } else if (selected === 'overview') {
      tabsRef.current?.scrollTo({ animated: true, x: 0 });
    }
  }, [selected]);
  return (
    <ScrollView
      horizontal
      ref={tabsRef}
      contentContainerStyle={styles.marketTabs}
      showsHorizontalScrollIndicator={false}>
      {MARKET_SECTIONS.map((section) => {
        const active = selected === section.key;
        return (
          <Pressable
            accessibilityRole="button"
            accessibilityState={{ selected: active }}
            key={section.key}
            onPress={() => onChange(section.key)}
            style={({ pressed }) => [
              styles.marketTab,
              active && styles.marketTabActive,
              pressed && styles.marketTabPressed,
            ]}>
            <SymbolView
              name={section.icon as never}
              size={15}
              tintColor={active ? Theme.colors.accent : Theme.colors.textMuted}
              weight="bold"
            />
            <Text style={[styles.marketTabText, active && styles.marketTabTextActive]}>
              {section.label}
            </Text>
          </Pressable>
        );
      })}
    </ScrollView>
  );
}

function MarketSectionContent({
  aiSummary,
  breadth,
  capRotation,
  core,
  decisionDashboard,
  detailsLoading,
  fearGreed,
  indexes,
  institutionalActivity,
  institutionalIntelligence,
  loadDetails,
  marketHealth,
  regime,
  section,
  weightConcentration,
  onWeightConcentrationChange,
}: {
  aiSummary: ReturnType<typeof useMarketDashboard>['aiSummary'];
  breadth: MarketBreadthResponse | null;
  capRotation: MarketCapRotationResponse | null;
  core: MarketCoreSnapshot | null;
  decisionDashboard: DecisionDashboardResponse | null;
  detailsLoading: boolean;
  fearGreed: FearGreedResponse | null;
  indexes: IndexSnapshot[];
  institutionalActivity: InstitutionalActivityResponse | null;
  institutionalIntelligence: DecisionDashboardResponse['institutional_intelligence'] | null;
  loadDetails: (group: 'structure' | 'decision' | 'institutional') => void;
  marketHealth: MarketHealthResponse | null;
  regime: MarketRegime | null;
  section: MarketSection;
  weightConcentration: ReturnType<typeof buildConcentrationBreadthSignal>;
  onWeightConcentrationChange: (signal: ReturnType<typeof buildConcentrationBreadthSignal>) => void;
}) {
  switch (section) {
    case 'indexes':
      return <IndexesTab indexes={indexes} onWeightConcentrationChange={onWeightConcentrationChange} />;
    case 'health':
      return <MarketHealthDetails marketHealth={marketHealth} />;
    case 'breadth':
      return (
        <LazyMarketDetails group="structure" loadDetails={loadDetails} loading={detailsLoading}>
          <BreadthDetails breadth={breadth} indexes={indexes} weightConcentration={weightConcentration} />
        </LazyMarketDetails>
      );
    case 'decision':
      return (
        <LazyMarketDetails group="decision" loadDetails={loadDetails} loading={detailsLoading}>
          <DecisionDashboardDetails
            capRotation={capRotation}
            decisionDashboard={decisionDashboard}
            fearGreed={fearGreed}
          />
        </LazyMarketDetails>
      );
    case 'institutions':
      return (
        <LazyMarketDetails group="institutional" loadDetails={loadDetails} loading={detailsLoading}>
          <InstitutionsDashboardDetails
            institutionalActivity={institutionalActivity}
            institutionalIntelligence={institutionalIntelligence ?? decisionDashboard?.institutional_intelligence ?? null}
          />
        </LazyMarketDetails>
      );
    case 'macro':
      return <MacroTab />;
    case 'overview':
    default:
      return (
        <OverviewTab
          aiSummary={aiSummary}
          breadth={breadth}
          capRotation={capRotation}
          core={core}
          decisionDashboard={decisionDashboard}
          fearGreed={fearGreed}
          indexes={indexes}
          institutionalActivity={institutionalActivity}
          institutionalIntelligence={institutionalIntelligence ?? decisionDashboard?.institutional_intelligence ?? null}
          marketHealth={marketHealth}
          regime={regime}
        />
      );
  }
}

function OverviewTab({
  aiSummary,
  breadth,
  capRotation,
  core,
  decisionDashboard,
  fearGreed,
  indexes,
  institutionalActivity,
  institutionalIntelligence,
  marketHealth,
  regime,
}: {
  aiSummary: ReturnType<typeof useMarketDashboard>['aiSummary'];
  breadth: MarketBreadthResponse | null;
  capRotation: MarketCapRotationResponse | null;
  core: MarketCoreSnapshot | null;
  decisionDashboard: DecisionDashboardResponse | null;
  fearGreed: FearGreedResponse | null;
  indexes: IndexSnapshot[];
  institutionalActivity: InstitutionalActivityResponse | null;
  institutionalIntelligence: DecisionDashboardResponse['institutional_intelligence'] | null;
  marketHealth: MarketHealthResponse | null;
  regime: MarketRegime | null;
}) {
  const [histories, setHistories] = useState<Partial<Record<string, HistoryData>>>({});
  useEffect(() => {
    let cancelled = false;
    const symbols = Array.from(new Set([...indexSymbols, 'RSP', 'QQEW', ...macroAssetDefinitions.map((asset) => asset.symbol)]));
    Promise.allSettled(symbols.map((symbol) => getLiveHistory(symbol, 'D', 370)))
      .then((results) => {
        if (cancelled) {
          return;
        }
        const nextHistories: Partial<Record<string, HistoryData>> = {};
        results.forEach((result, index) => {
          if (result.status === 'fulfilled') {
            nextHistories[symbols[index]] = result.value;
          }
        });
        setHistories(nextHistories);
      })
      .catch(() => {
        if (!cancelled) {
          setHistories({});
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);
  const indexHistories = useMemo<Partial<Record<IndexSymbol, HistoryData>>>(() => ({
    DJI: histories.DJI,
    QQQ: histories.QQQ,
    SPY: histories.SPY,
  }), [histories.DJI, histories.QQQ, histories.SPY]);
  const indexAnalyses = useMemo(() => analyzeIndexes(indexes, indexHistories, '1M'), [indexHistories, indexes]);
  const weightConcentration = useMemo(
    () => buildConcentrationBreadthSignal(buildWeightComparisonPair('sp500', histories, '1M')),
    [histories],
  );
  const macroHistories = useMemo(() => Object.fromEntries(
    macroAssetDefinitions.map((asset) => [asset.symbol, histories[asset.symbol]]).filter((entry): entry is [string, HistoryData] => Boolean(entry[1])),
  ), [histories]);
  const macro = useMemo(
    () => buildMacroDashboardViewModel(macroHistories, '3M', Intl.DateTimeFormat().resolvedOptions().timeZone, null),
    [macroHistories],
  );
  const breadthDashboard = useMemo(() => buildBreadthDashboard(breadth, indexes), [breadth, indexes]);
  const institutional = useMemo(
    () => buildInstitutionalDashboardViewModel(institutionalIntelligence, institutionalActivity),
    [institutionalActivity, institutionalIntelligence],
  );
  const decision = useMemo(
    () => buildDecisionDashboardViewModel(decisionDashboard, capRotation, fearGreed),
    [capRotation, decisionDashboard, fearGreed],
  );
  const overview = useMemo(() => buildMarketOverviewDashboard({
    breadth: breadthDashboard,
    core,
    decision,
    health: marketHealth,
    indexes: indexAnalyses,
    institutional,
    macro,
    weightConcentration,
  }), [breadthDashboard, core, decision, indexAnalyses, institutional, macro, marketHealth, weightConcentration]);

  return (
    <View style={styles.sectionStack}>
      <MarketRegimeHero core={core} marketHealth={marketHealth} overview={overview} regime={regime} />
      <MarketSnapshotGrid overview={overview} />
      <SignalAlignmentCard overview={overview} />
      <MarketInsightPanel aiSummary={aiSummary} overview={overview} />
      <MarketDecisionPostureCard overview={overview} />
      <KeySignals overview={overview} />
      {overview.dataQuality.label ? <MarketOverviewDataQuality overview={overview} /> : null}
    </View>
  );
}

function IndexesTab({
  indexes,
  onWeightConcentrationChange,
}: {
  indexes: IndexSnapshot[];
  onWeightConcentrationChange: (signal: ReturnType<typeof buildConcentrationBreadthSignal>) => void;
}) {
  const [timeframe, setTimeframe] = useState<IndexTimeframe>('1M');
  const [weightTimeframe, setWeightTimeframe] = useState<IndexTimeframe>('1M');
  const [histories, setHistories] = useState<Partial<Record<string, HistoryData>>>({});
  const [selectedWeightPair, setSelectedWeightPair] = useState<WeightComparisonPairId>('sp500');
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const analyses = useMemo(() => analyzeIndexes(indexes, histories, timeframe), [histories, indexes, timeframe]);
  const availableWeightPairs = useMemo(() => getAvailableWeightPairs(histories), [histories]);
  const weightModel = useMemo(() => {
    const pair = availableWeightPairs.includes(selectedWeightPair) ? selectedWeightPair : availableWeightPairs[0] ?? 'sp500';
    return buildWeightComparisonPair(pair, histories, weightTimeframe);
  }, [availableWeightPairs, histories, selectedWeightPair, weightTimeframe]);
  const sourceLabel = getIndexSourceLabel(indexes, histories);

  useEffect(() => {
    const sp500 = buildWeightComparisonPair('sp500', histories, weightTimeframe);
    onWeightConcentrationChange(buildConcentrationBreadthSignal(sp500));
  }, [histories, onWeightConcentrationChange, weightTimeframe]);

  useEffect(() => {
    let cancelled = false;

    const historySymbols = [...indexSymbols, 'RSP', 'QQEW'];
    Promise.allSettled(historySymbols.map((symbol) => getLiveHistory(symbol, 'D', 370)))
      .then((results) => {
        if (cancelled) {
          return;
        }
        const nextHistories: Partial<Record<string, HistoryData>> = {};
        results.forEach((result, index) => {
          if (result.status === 'fulfilled') {
            nextHistories[historySymbols[index]] = result.value;
          }
        });
        setHistories(nextHistories);
        if (results.some((result) => result.status === 'rejected')) {
          setHistoryError('Some index history is unavailable.');
        }
      })
      .catch(() => {
        if (!cancelled) {
          setHistoryError('Index history is unavailable.');
        }
      })
      .finally(() => {
        if (!cancelled) {
          setHistoryLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <View style={styles.sectionStack}>
      <CompactTimeframeSelector
        onChange={(key) => setTimeframe(key as IndexTimeframe)}
        selected={timeframe}
      />
      <View style={styles.indexDisclosureRow}>
        <StatusBadge label={sourceLabel} tone={sourceLabel.includes('Live') ? 'success' : sourceLabel.includes('Mock') || sourceLabel.includes('Mixed') ? 'warning' : 'muted'} />
        {historyLoading ? <Text style={styles.helperInline}>Updating history…</Text> : null}
        {historyError ? <Text style={styles.warningInline}>{historyError}</Text> : null}
      </View>

      <IndexComparisonChart analyses={analyses} timeframe={timeframe} />
      <IndexComparisonSummary analyses={analyses} timeframe={timeframe} />
      <WeightedEqualWeightCard
        availablePairs={availableWeightPairs}
        model={weightModel}
        onSelectPair={setSelectedWeightPair}
        onTimeframeChange={setWeightTimeframe}
        selectedPair={weightModel.pairId}
        timeframe={weightTimeframe}
      />
      <MarketLeadershipTrendCard analyses={analyses} />
      <IndexVolumeParticipationCard analyses={analyses} />
      <View style={styles.sectionStack}>
        <Text style={styles.detailSectionTitle}>Index Setups</Text>
        {analyses.length ? analyses.map((analysis) => (
          <IndexSetupCard analysis={analysis} key={analysis.symbol} timeframe={timeframe} />
        )) : <Text style={styles.bodyText}>SPY, QQQ, and DJI snapshots are unavailable.</Text>}
      </View>
    </View>
  );
}

function CompactTimeframeSelector({
  onChange,
  selected,
}: {
  onChange: (timeframe: IndexTimeframe) => void;
  selected: IndexTimeframe;
}) {
  return (
    <View style={styles.compactTimeframeRow}>
      {indexTimeframes.map((timeframe) => {
        const active = selected === timeframe;
        return (
          <Pressable
            accessibilityRole="button"
            accessibilityState={{ selected: active }}
            key={timeframe}
            onPress={() => onChange(timeframe)}
            style={({ pressed }) => [
              styles.compactTimeframeButton,
              active && styles.compactTimeframeButtonActive,
              pressed && styles.marketTabPressed,
            ]}>
            <Text style={[styles.compactTimeframeText, active && styles.compactTimeframeTextActive]}>
              {timeframe}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

function MacroTab() {
  const [timeframe, setTimeframe] = useState<MacroTimeframe>('3M');
  const [selectedScenario, setSelectedScenario] = useState<MacroMockScenarioId>('soft_landing');
  const [histories, setHistories] = useState<Partial<Record<string, HistoryData>>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const macroScenario = useMemo(() => (
    typeof __DEV__ !== 'undefined' && __DEV__
      ? buildMacroMockScenario(selectedScenario)
      : null
  ), [selectedScenario]);
  const model = useMemo(
    () => buildMacroDashboardViewModel(histories, timeframe, Intl.DateTimeFormat().resolvedOptions().timeZone, macroScenario),
    [histories, macroScenario, timeframe],
  );

  useEffect(() => {
    let cancelled = false;
    Promise.resolve()
      .then(() => {
        if (cancelled) {
          return [];
        }
        setLoading(true);
        setError(null);
        return Promise.allSettled(
          macroAssetDefinitions.map((asset) => getLiveHistory(asset.symbol, 'D', macroTimeframeDays[timeframe])),
        );
      })
      .then((results) => {
        if (cancelled) {
          return;
        }
        const nextHistories: Partial<Record<string, HistoryData>> = {};
        results.forEach((result, index) => {
          if (result.status === 'fulfilled') {
            nextHistories[macroAssetDefinitions[index].symbol] = result.value;
          }
        });
        setHistories(nextHistories);
        setError(results.every((result) => result.status === 'rejected') ? 'Macro proxy history unavailable.' : null);
      })
      .catch(() => {
        if (!cancelled) {
          setError('Macro proxy history unavailable.');
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
  }, [timeframe]);

  return (
    <View style={styles.sectionStack}>
      <MacroTimeframeSelector selected={timeframe} onChange={setTimeframe} />
      {macroScenario ? (
        <MacroScenarioSwitcher
          selected={selectedScenario}
          onChange={setSelectedScenario}
        />
      ) : null}
      <View style={styles.indexDisclosureRow}>
        <StatusBadge label={model.dataQuality.sourceLabel} tone={macroSourceTone(model.dataQuality.sourceKind)} />
        {loading ? <Text style={styles.helperInline}>Updating macro proxies…</Text> : null}
        {error ? <Text style={styles.warningInline}>{error}</Text> : null}
      </View>
      <MacroOverviewCard model={model} />
      <MacroCrossAssetCard model={model} />
      <MacroRiskAppetiteCard model={model} />
      <MacroTreasuryEquityCard model={model} />
      <MacroCommodityCard model={model} />
      <MacroEconomicDashboardCard model={model} />
      <MacroEventTimelineCard model={model} />
      <MacroInterpretationCard model={model} />
      <MacroMethodologyDisclosure model={model} />
    </View>
  );
}

function MacroScenarioSwitcher({
  onChange,
  selected,
}: {
  onChange: (scenario: MacroMockScenarioId) => void;
  selected: MacroMockScenarioId;
}) {
  const scenario = buildMacroMockScenario(selected);
  return (
    <View style={styles.breadthMockPanel}>
      <View style={styles.sectionHeaderRow}>
        <View style={styles.summaryTitleBlock}>
          <Text style={styles.detailSectionTitle}>Macro Test Scenario</Text>
          <Text style={styles.helperInline}>{scenario.description}</Text>
        </View>
        <StatusBadge label="Test data" tone="warning" />
      </View>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.breadthMockOptions}>
        {MACRO_MOCK_SCENARIO_OPTIONS.map((option) => {
          const active = selected === option.id;
          return (
            <Pressable
              accessibilityRole="button"
              accessibilityState={{ selected: active }}
              key={option.id}
              onPress={() => onChange(option.id)}
              style={[styles.breadthMockChip, active && styles.breadthMockChipActive]}
            >
              <Text style={[styles.breadthMockChipText, active && styles.breadthMockChipTextActive]}>
                {option.label}
              </Text>
            </Pressable>
          );
        })}
      </ScrollView>
    </View>
  );
}

function MacroTimeframeSelector({
  onChange,
  selected,
}: {
  onChange: (timeframe: MacroTimeframe) => void;
  selected: MacroTimeframe;
}) {
  return (
    <View style={styles.compactTimeframeRow}>
      {macroTimeframes.map((timeframe) => {
        const active = selected === timeframe;
        return (
          <Pressable
            accessibilityRole="button"
            accessibilityState={{ selected: active }}
            key={timeframe}
            onPress={() => onChange(timeframe)}
            style={({ pressed }) => [
              styles.compactTimeframeButton,
              active && styles.compactTimeframeButtonActive,
              pressed && styles.marketTabPressed,
            ]}>
            <Text style={[styles.compactTimeframeText, active && styles.compactTimeframeTextActive]}>
              {timeframe}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

function MacroOverviewCard({ model }: { model: MacroDashboardViewModel }) {
  return (
    <View style={styles.regimeHero}>
      <View style={styles.regimeHeader}>
        <View style={styles.regimeTitleBlock}>
          <Text style={styles.heroKicker}>Macro Overview</Text>
          <Text style={styles.regimeTitle}>{formatRiskState(model.overview.regime)}</Text>
          <Text style={styles.regimeScore}>Confidence · {capitalize(model.overview.confidence)}</Text>
        </View>
        <StatusBadge label={model.dataQuality.sourceLabel} tone={macroSourceTone(model.dataQuality.sourceKind)} />
      </View>
      <Text style={styles.regimeExplanation}>{model.overview.summary}</Text>
      <View style={styles.macroLeadLagGrid}>
        <MetricTile label="Leading" value={model.overview.leading.join(' · ') || 'N/A'} />
        <MetricTile label="Lagging" value={model.overview.lagging.join(' · ') || 'N/A'} />
      </View>
      <Text style={styles.warningInline}>Key risk: {model.overview.keyRisk}</Text>
    </View>
  );
}

function MacroCrossAssetCard({ model }: { model: MacroDashboardViewModel }) {
  return (
    <View style={styles.indexPanel}>
      <View style={styles.sectionHeaderRow}>
        <View style={styles.summaryTitleBlock}>
          <Text style={styles.detailSectionTitle}>Cross-Asset Performance</Text>
          <Text style={styles.helperInline}>{model.timeframe} normalized return · benchmark {model.crossAsset.benchmark}</Text>
        </View>
        <StatusBadge label={model.crossAsset.sourceLabel} tone={macroSourceTone(model.dataQuality.sourceKind)} />
      </View>
      <MacroNormalizedChart
        accessibilityLabel={`Cross-asset normalized ${model.timeframe} performance chart.`}
        series={model.crossAsset.series}
        timeframe={model.timeframe}
      />
      <MacroAssetRotation model={model} />
    </View>
  );
}

function MacroAssetRotation({ model }: { model: MacroDashboardViewModel }) {
  const values = model.assetRotation.items.map((item) => item.periodReturn ?? 0);
  const maxAbs = Math.max(1, ...values.map((value) => Math.abs(value)));
  return (
    <View style={styles.macroSubsection}>
      <Text style={styles.detailSectionTitle}>Asset Rotation</Text>
      <View style={styles.macroRotationRows}>
        {model.assetRotation.items.map((item) => {
          const value = item.periodReturn ?? 0;
          const width = `${Math.max(3, Math.abs(value) / maxAbs * 48)}%` as `${number}%`;
          return (
            <View key={item.symbol} style={styles.macroRotationRow}>
              <Text numberOfLines={1} style={styles.macroRotationLabel}>{item.label}</Text>
              <View style={styles.macroRotationTrack}>
                <View style={styles.macroRotationZero} />
                <View
                  style={[
                    styles.macroRotationBar,
                    value >= 0 ? styles.macroRotationBarPositive : styles.macroRotationBarNegative,
                    value >= 0 ? { left: '50%', width } : { right: '50%', width },
                  ]}
                />
              </View>
              <Text style={[styles.macroRotationValue, { color: returnColor(value) }]}>{formatNullableSignedPercent(value)}</Text>
            </View>
          );
        })}
      </View>
      <Text style={styles.bodyText}>{model.assetRotation.interpretation}</Text>
    </View>
  );
}

function MacroRiskAppetiteCard({ model }: { model: MacroDashboardViewModel }) {
  const score = model.riskAppetite.score;
  const marker = score === null ? 50 : Math.max(0, Math.min(100, score));
  return (
    <View style={styles.indexPanel}>
      <View style={styles.sectionHeaderRow}>
        <View>
          <Text style={styles.detailSectionTitle}>Risk-On vs Risk-Off</Text>
          <Text style={styles.helperInline}>Confidence · {capitalize(model.riskAppetite.confidence)}</Text>
        </View>
        <StatusBadge label={formatRiskState(model.riskAppetite.state)} tone={riskAppetiteTone(model.riskAppetite.state)} />
      </View>
      <View style={styles.macroGaugeLabels}>
        <Text style={styles.helperInline}>Risk-Off</Text>
        <Text style={styles.helperInline}>Balanced</Text>
        <Text style={styles.helperInline}>Risk-On</Text>
      </View>
      <View style={styles.macroGaugeTrack}>
        <View style={styles.macroGaugeCenter} />
        <View style={[styles.macroGaugeMarker, { left: `${marker}%` }]} />
      </View>
      <Text style={styles.decisionGaugeScore}>{score === null ? 'N/A' : score}</Text>
      <Text style={styles.bodyText}>{model.riskAppetite.explanation}</Text>
      <View style={styles.macroFactorGrid}>
        <MacroFactorColumn title="Supports" items={model.riskAppetite.supportingFactors} />
        <MacroFactorColumn title="Risks" items={model.riskAppetite.defensiveFactors} />
      </View>
    </View>
  );
}

function MacroFactorColumn({ items, title }: { items: string[]; title: string }) {
  return (
    <View style={styles.macroFactorColumn}>
      <Text style={styles.metricLabel}>{title}</Text>
      {items.length ? items.slice(0, 3).map((item) => (
        <Text key={item} style={styles.metricSubvalue}>• {item}</Text>
      )) : <Text style={styles.metricSubvalue}>No dominant factor</Text>}
    </View>
  );
}

function MacroTreasuryEquityCard({ model }: { model: MacroDashboardViewModel }) {
  return (
    <View style={styles.indexPanel}>
      <Text style={styles.detailSectionTitle}>Treasury & Equity Relationship</Text>
      <MacroNormalizedChart
        accessibilityLabel={`SPY, IEF, and TLT normalized ${model.timeframe} comparison chart.`}
        compact
        series={model.treasuryEquity.series}
        timeframe={model.timeframe}
      />
      <View style={styles.macroLeadLagGrid}>
        <MetricTile label="SPY vs 10Y Bonds" value={formatSignedPoints(model.treasuryEquity.spyVs10Y)} />
        <MetricTile label="SPY vs 30Y Bonds" value={formatSignedPoints(model.treasuryEquity.spyVs30Y)} />
      </View>
      <Text style={styles.bodyText}>{model.treasuryEquity.interpretation}</Text>
      <Text style={styles.helperInline}>{model.treasuryEquity.yieldSummary}</Text>
    </View>
  );
}

function MacroCommodityCard({ model }: { model: MacroDashboardViewModel }) {
  const commodities = [model.commodities.gold, model.commodities.oil].filter((item): item is NonNullable<typeof item> => Boolean(item));
  return (
    <View style={styles.indexPanel}>
      <Text style={styles.detailSectionTitle}>Commodity Dashboard</Text>
      <View style={styles.macroLeadLagGrid}>
        {commodities.length ? commodities.map((commodity) => (
          <View key={commodity.label} style={styles.metricTile}>
            <Text style={styles.metricLabel}>{commodity.label}</Text>
            <Text style={[styles.metricValue, { color: returnColor(commodity.returnValue) }]}>
              {formatNullableSignedPercent(commodity.returnValue)}
            </Text>
            <Text style={styles.metricSubvalue}>{commodity.trend} · vs SPY {formatSignedPoints(commodity.relativeToSpy)}</Text>
            <Text style={styles.metricSubvalue}>{commodity.interpretation}</Text>
          </View>
        )) : <Text style={styles.healthUnavailableText}>Commodity proxy data unavailable.</Text>}
      </View>
      <Text style={styles.bodyText}>{model.commodities.interpretation}</Text>
    </View>
  );
}

function MacroEconomicDashboardCard({ model }: { model: MacroDashboardViewModel }) {
  return (
    <View style={styles.indexPanel}>
      <View style={styles.sectionHeaderRow}>
        <Text style={styles.detailSectionTitle}>Economic Dashboard</Text>
        <StatusBadge label={model.economicDashboard.sourceLabel} tone={model.economicDashboard.sourceLabel === 'Test data' ? 'warning' : 'muted'} />
      </View>
      {model.economicDashboard.metrics.length ? (
        <View style={styles.metricGrid}>
          {model.economicDashboard.metrics.map((metric) => (
            <View key={`${metric.key}-${metric.periodLabel}`} style={styles.economicMetricTile}>
              <View style={styles.economicMetricHeader}>
                <Text style={styles.metricLabel}>{metric.label}{metric.periodLabel !== 'Level' ? ` · ${metric.periodLabel}` : ''}</Text>
              </View>
              <View style={styles.economicBadgeRow}>
                <StatusBadge label={metric.surpriseLabel} tone={economicToneToStatus(metric.tone)} />
              </View>
              <Text style={styles.economicActualLabel}>{metric.mode === 'market_level' ? 'Current' : 'Actual'}</Text>
              <Text style={styles.economicActualValue}>{metric.actual.formattedValue}</Text>
              <View style={styles.economicFieldRow}>
                {metric.expected ? (
                  <View style={styles.economicField}>
                    <Text style={styles.economicFieldLabel}>Expected</Text>
                    <Text numberOfLines={1} style={styles.economicFieldValue}>{metric.expected.formattedValue}</Text>
                  </View>
                ) : null}
                {metric.previous ? (
                  <View style={styles.economicField}>
                    <Text style={styles.economicFieldLabel}>Previous</Text>
                    <Text numberOfLines={1} style={styles.economicFieldValue}>{metric.previous.formattedValue}</Text>
                    {metric.revisedPrevious ? (
                      <Text numberOfLines={1} style={styles.economicRevisionText}>
                        Revised from {metric.revisedPrevious.formattedValue}
                      </Text>
                    ) : null}
                  </View>
                ) : null}
              </View>
              {metric.mode === 'market_level' ? (
                metric.change ? (
                  <View style={styles.economicSurpriseRow}>
                    <Text style={styles.economicFieldLabel}>Change</Text>
                    <Text style={styles.economicSurpriseValue}>{metric.change}</Text>
                  </View>
                ) : null
              ) : metric.surprise.formattedValue ? (
                <View style={styles.economicSurpriseRow}>
                  <Text style={styles.economicFieldLabel}>Surprise</Text>
                  <Text style={styles.economicSurpriseValue}>{metric.surprise.formattedValue}</Text>
                </View>
              ) : (
                <Text style={styles.economicConsensusText}>Consensus unavailable</Text>
              )}
              <Text numberOfLines={1} style={[styles.economicComment, { color: economicToneColor(metric.tone) }]}>
                {metric.comment}
              </Text>
              {metric.latestDate ? <Text style={styles.economicReleaseDate}>Released {metric.latestDate}</Text> : null}
            </View>
          ))}
        </View>
      ) : (
        <Text style={styles.healthUnavailableText}>{model.economicDashboard.message}</Text>
      )}
    </View>
  );
}

function MacroEventTimelineCard({ model }: { model: MacroDashboardViewModel }) {
  return (
    <View style={styles.indexPanel}>
      <View style={styles.sectionHeaderRow}>
        <Text style={styles.detailSectionTitle}>Macro Event Timeline</Text>
        <View style={styles.institutionalBadgeColumn}>
          <Text style={styles.helperInline}>{model.eventTimeline.timezone}</Text>
          {model.eventTimeline.events.some((event) => event.source === 'test') ? <StatusBadge label="Test data" tone="warning" /> : null}
        </View>
      </View>
      {model.eventTimeline.events.length ? (
        <View style={styles.decisionList}>
          {model.eventTimeline.events.map((event) => (
            <View key={`${event.date}-${event.event}`} style={styles.decisionSetupRow}>
              <View style={styles.decisionSetupBody}>
                <Text style={styles.decisionChecklistLabel}>{event.event}</Text>
                <Text style={styles.metricSubvalue}>{[event.date, event.time, event.importance].filter(Boolean).join(' · ')}</Text>
                <Text style={styles.metricSubvalue}>
                  {[event.status, event.category, event.sourceTimezone ? `Source ${event.sourceTimezone}` : null].filter(Boolean).join(' · ')}
                </Text>
                <View style={styles.macroEventValueRow}>
                  <Text style={styles.metricSubvalue}>Prev {event.previous ?? 'N/A'}</Text>
                  {event.consensus ? <Text style={styles.metricSubvalue}>Cons {event.consensus}</Text> : null}
                  {event.actual ? <Text style={styles.metricSubvalue}>Actual {event.actual}</Text> : null}
                </View>
                {event.surprise ? <Text style={styles.warningInline}>{event.surprise}</Text> : null}
              </View>
            </View>
          ))}
        </View>
      ) : (
        <Text style={styles.healthUnavailableText}>{model.eventTimeline.message}</Text>
      )}
    </View>
  );
}

function MacroInterpretationCard({ model }: { model: MacroDashboardViewModel }) {
  return (
    <View style={styles.decisionHeroCard}>
      <View style={styles.sectionHeaderRow}>
        <View style={styles.summaryTitleBlock}>
          <Text style={styles.detailSectionTitle}>Macro Interpretation</Text>
          <Text style={styles.helperInline}>Confidence · {capitalize(model.interpretation.confidence)}</Text>
        </View>
        <StatusBadge label={model.interpretation.stance} tone={riskAppetiteTone(model.riskAppetite.state)} />
      </View>
      <View style={styles.macroLeadLagGrid}>
        <MetricTile label="Supports" value={model.interpretation.supportiveFactor} />
        <MetricTile label="Main Risk" value={model.interpretation.mainRisk} />
      </View>
      <Text style={styles.bodyText}>{model.interpretation.implication}</Text>
    </View>
  );
}

function MacroMethodologyDisclosure({ model }: { model: MacroDashboardViewModel }) {
  return (
    <ExpandableSection
      summary={`${model.dataQuality.sourceLabel} · ${capitalize(model.dataQuality.confidence)} confidence`}
      title="Data Quality & Methodology">
      <View style={styles.compactDisclosureBody}>
        <Text style={styles.helperText}>Proxy symbols: {macroAssetDefinitions.map((asset) => `${asset.label}=${asset.symbol}`).join(', ')}.</Text>
        <Text style={styles.helperText}>Relative performance is normalized percentage return and is not verified capital-flow data.</Text>
        <Text style={styles.helperText}>Treasury bond ETF prices are distinct from Treasury yield levels; yield history is unavailable in the configured data source.</Text>
        <Text style={styles.helperText}>Economic releases and macro event dates are shown only when reliable project data exists. Development scenarios are labelled Test data.</Text>
        {model.dataQuality.missingAssets.length ? (
          <Text style={styles.helperText}>Missing proxies: {model.dataQuality.missingAssets.join(', ')}.</Text>
        ) : null}
      </View>
    </ExpandableSection>
  );
}

function MacroNormalizedChart({
  accessibilityLabel,
  compact = false,
  series,
  timeframe,
}: {
  accessibilityLabel: string;
  compact?: boolean;
  series: MacroAssetPerformance[];
  timeframe: MacroTimeframe;
}) {
  const [width, setWidth] = useState(0);
  const [selectedTime, setSelectedTime] = useState<number | null>(null);
  const chartWidth = Math.max(width, 1);
  const chartHeight = compact ? 132 : 178;
  const plotTop = 18;
  const plotBottom = 30;
  const plotHeight = chartHeight - plotTop - plotBottom;
  const validSeries = series.filter((asset) => asset.chartPoints.length >= 2);
  const allValues = validSeries.flatMap((asset) => asset.chartPoints.map((point) => point.value));
  const allTimes = validSeries
    .flatMap((asset) => asset.chartPoints.map((point) => Date.parse(point.timestamp)))
    .filter((time) => Number.isFinite(time));
  const minTime = allTimes.length ? Math.min(...allTimes) : 0;
  const maxTime = allTimes.length ? Math.max(...allTimes) : minTime;
  const bounds = calculateChartBounds(Math.min(0, ...allValues), Math.max(0, ...allValues));
  const yForValue = (value: number) => plotTop + ((bounds.max - value) / (bounds.max - bounds.min || 1)) * plotHeight;
  const xForTimestamp = (timestamp: string) => {
    const time = Date.parse(timestamp);
    if (!Number.isFinite(time) || maxTime <= minTime) {
      return 12;
    }
    return 12 + ((time - minTime) / (maxTime - minTime)) * Math.max(1, chartWidth - 24);
  };
  const xLabels = buildMacroXLabels(validSeries, timeframe);
  const tooltip = selectedTime === null ? null : buildMacroTooltip(validSeries, selectedTime);
  const tooltipX = selectedTime === null || maxTime <= minTime
    ? 6
    : 12 + ((selectedTime - minTime) / (maxTime - minTime)) * Math.max(1, chartWidth - 24);

  return (
    <View>
      <Pressable
        accessibilityLabel={accessibilityLabel}
        onLayout={(event) => setWidth(event.nativeEvent.layout.width)}
        onPressIn={(event) => {
          if (!allTimes.length || maxTime <= minTime) {
            return;
          }
          const ratio = Math.max(0, Math.min(1, (event.nativeEvent.locationX - 12) / Math.max(1, chartWidth - 24)));
          const targetTime = minTime + ratio * (maxTime - minTime);
          const nearest = allTimes.reduce((best, time) => (
            Math.abs(time - targetTime) < Math.abs(best - targetTime) ? time : best
          ), allTimes[0]);
          setSelectedTime(nearest);
        }}
        onPressOut={() => setSelectedTime(null)}
        style={[styles.indexChartBox, { height: chartHeight }]}>
        {bounds.ticks.map((tick) => (
          <View
            key={tick}
            style={[
              styles.indexChartGridLine,
              tick === 0 && styles.indexChartBaseline,
              { top: yForValue(tick) },
            ]}>
            <Text style={styles.indexChartYAxisLabel}>{formatAxisPercent(tick)}</Text>
          </View>
        ))}
        {validSeries.length ? validSeries.map((asset) => (
          <MacroSeriesLine
            asset={asset}
            key={asset.symbol}
            xForTimestamp={xForTimestamp}
            yForValue={yForValue}
          />
        )) : (
          <View style={styles.indexChartEmpty}>
            <Text style={styles.emptyText}>Cross-asset history unavailable.</Text>
          </View>
        )}
        {validSeries.map((asset, index) => {
          const latest = asset.chartPoints.at(-1);
          if (!latest) {
            return null;
          }
          const x = xForTimestamp(latest.timestamp);
          const y = yForValue(latest.value);
          return (
            <View
              key={`${asset.symbol}-latest`}
              style={[styles.indexLatestPoint, { borderColor: macroAssetColor(asset.symbol), left: x - 5, top: y - 5 }]}
            >
              <Text
                numberOfLines={1}
                style={[
                  styles.endpointLabel,
                  {
                    color: macroAssetColor(asset.symbol),
                    left: 7,
                    top: -8 + getEndpointLabelOffset(index, validSeries.length),
                  },
                ]}>
                {asset.symbol}
              </Text>
            </View>
          );
        })}
        {tooltip ? (
          <>
            <View style={[styles.indexCrosshair, { left: tooltipX }]} />
            <View style={[styles.indexTooltip, styles.macroTooltip, { left: getTooltipLeft(tooltipX, chartWidth) }]}>
              <Text style={styles.tooltipTitle}>{tooltip.title}</Text>
              {tooltip.rows.map((row) => (
                <View key={row.symbol} style={styles.tooltipRow}>
                  <View style={[styles.tooltipDot, { backgroundColor: macroAssetColor(row.symbol) }]} />
                  <Text style={styles.tooltipText}>{row.symbol}</Text>
                  <Text style={styles.tooltipValue}>{formatSignedPercent(row.value)}</Text>
                </View>
              ))}
              <Text style={styles.tooltipValue}>Leader: {tooltip.leader}</Text>
              <Text style={styles.tooltipValue}>Laggard: {tooltip.laggard}</Text>
              {tooltip.riskSpread !== null ? <Text style={styles.tooltipValue}>SPY vs defensive: {formatSignedPoints(tooltip.riskSpread)}</Text> : null}
            </View>
          </>
        ) : null}
        {xLabels.map((label) => (
          <Text
            key={label.key}
            numberOfLines={1}
            style={[styles.indexXAxisLabel, { left: Math.max(2, Math.min(chartWidth - 42, xForTimestamp(label.timestamp) - 14)) }]}>
            {label.label}
          </Text>
        ))}
      </Pressable>
      <View style={styles.indexLegend}>
        {validSeries.map((asset) => (
          <View key={asset.symbol} style={styles.legendItem}>
            <View style={[styles.legendDot, { backgroundColor: macroAssetColor(asset.symbol) }]} />
            <Text style={styles.legendText}>{asset.symbol}</Text>
          </View>
        ))}
      </View>
    </View>
  );
}

function MacroSeriesLine({
  asset,
  xForTimestamp,
  yForValue,
}: {
  asset: MacroAssetPerformance;
  xForTimestamp: (timestamp: string) => number;
  yForValue: (value: number) => number;
}) {
  return (
    <>
      {asset.chartPoints.slice(1).map((point, index) => {
        const previous = asset.chartPoints[index];
        return (
          <ChartLineSegment
            color={macroAssetColor(asset.symbol)}
            end={{ x: xForTimestamp(point.timestamp), y: yForValue(point.value) }}
            key={`${asset.symbol}-${point.timestamp}`}
            start={{ x: xForTimestamp(previous.timestamp), y: yForValue(previous.value) }}
          />
        );
      })}
    </>
  );
}

function IndexComparisonChart({
  analyses,
  timeframe,
}: {
  analyses: IndexAnalysis[];
  timeframe: IndexTimeframe;
}) {
  const [width, setWidth] = useState(0);
  const [selectedTime, setSelectedTime] = useState<number | null>(null);
  const chartWidth = Math.max(width, 1);
  const chartHeight = 164;
  const plotTop = 18;
  const plotBottom = 28;
  const plotHeight = chartHeight - plotTop - plotBottom;
  const series = analyses.filter((analysis) => analysis.chartPoints.length);
  const allValues = series.flatMap((analysis) => analysis.chartPoints.map((point) => point.value));
  const allTimes = series
    .flatMap((analysis) => analysis.chartPoints.map((point) => Date.parse(point.timestamp)))
    .filter((time) => Number.isFinite(time));
  const minTime = allTimes.length ? Math.min(...allTimes) : 0;
  const maxTime = allTimes.length ? Math.max(...allTimes) : minTime;
  const rawMinValue = Math.min(0, ...allValues);
  const rawMaxValue = Math.max(0, ...allValues);
  const chartBounds = calculateChartBounds(rawMinValue, rawMaxValue);
  const paddedMin = chartBounds.min;
  const paddedMax = chartBounds.max;
  const yTicks = chartBounds.ticks;
  const xLabels = buildChartXLabels(series, timeframe);
  const leader = getPeriodLeader(analyses);
  const yForValue = (value: number) => plotTop + ((paddedMax - value) / (paddedMax - paddedMin || 1)) * plotHeight;
  const xForTimestamp = (timestamp: string) => {
    const time = Date.parse(timestamp);
    if (!Number.isFinite(time) || maxTime <= minTime) {
      return 12;
    }
    return 12 + ((time - minTime) / (maxTime - minTime)) * Math.max(1, chartWidth - 24);
  };
  const selectedTooltip = selectedTime === null
    ? null
    : buildIndexTooltip(series, selectedTime);
  const selectedTooltipX = selectedTime === null || maxTime <= minTime
    ? 6
    : 12 + ((selectedTime - minTime) / (maxTime - minTime)) * Math.max(1, chartWidth - 24);

  return (
    <View style={styles.indexPanel}>
      <View style={styles.sectionHeaderRow}>
        <View style={styles.summaryTitleBlock}>
          <Text style={styles.detailSectionTitle}>Index Comparison</Text>
          {leader ? (
            <Text style={styles.helperInline}>
              Leader: {leader.symbol} {formatNullableSignedPercent(leader.periodReturn)}
            </Text>
          ) : null}
        </View>
        <Text style={styles.helperInline}>{timeframe} normalized return</Text>
      </View>
      <Pressable
        accessibilityLabel={`SPY, QQQ, and DJI normalized ${timeframe} performance comparison chart.`}
        onLayout={(event) => setWidth(event.nativeEvent.layout.width)}
        onPressIn={(event) => {
          if (!allTimes.length || maxTime <= minTime) {
            return;
          }
          const relativeX = event.nativeEvent.locationX;
          const ratio = Math.max(0, Math.min(1, (relativeX - 12) / Math.max(1, chartWidth - 24)));
          const targetTime = minTime + ratio * (maxTime - minTime);
          const nearest = allTimes.reduce((best, time) => (
            Math.abs(time - targetTime) < Math.abs(best - targetTime) ? time : best
          ), allTimes[0]);
          setSelectedTime(nearest);
        }}
        style={[styles.indexChartBox, { height: chartHeight }]}>
        {yTicks.map((tick) => (
          <View
            key={tick}
            style={[
              styles.indexChartGridLine,
              tick === 0 && styles.indexChartBaseline,
              { top: yForValue(tick) },
            ]}>
            <Text style={styles.indexChartYAxisLabel}>{formatAxisPercent(tick)}</Text>
          </View>
        ))}
        {series.length ? series.map((analysis) => (
          <IndexSeriesLine
            key={analysis.symbol}
            color={indexColor(analysis.symbol)}
            points={analysis.chartPoints}
            xForTimestamp={xForTimestamp}
            yForValue={yForValue}
          />
        )) : (
          <View style={styles.indexChartEmpty}>
            <Text style={styles.emptyText}>Comparison history unavailable.</Text>
          </View>
        )}
        {series.map((analysis) => {
          const latest = analysis.chartPoints.at(-1);
          if (!latest) {
            return null;
          }
          const x = xForTimestamp(latest.timestamp);
          const y = yForValue(latest.value);
          return (
            <View
              key={`${analysis.symbol}-latest`}
              style={[
                styles.indexLatestPoint,
                {
                  borderColor: indexColor(analysis.symbol),
                  left: x - 5,
                  top: y - 5,
                },
              ]}
            />
          );
        })}
        {series.map((analysis, index) => {
          const latest = analysis.chartPoints.at(-1);
          if (!latest) {
            return null;
          }
          const x = Math.min(xForTimestamp(latest.timestamp) + 7, Math.max(8, chartWidth - 54));
          const y = yForValue(latest.value) - 7 + getEndpointLabelOffset(index, series.length);
          return (
            <Text
              key={`${analysis.symbol}-endpoint`}
              numberOfLines={1}
              style={[
                styles.endpointLabel,
                {
                  color: indexColor(analysis.symbol),
                  left: x,
                  top: Math.max(2, Math.min(chartHeight - 18, y)),
                },
              ]}>
              {analysis.symbol} {formatNullableSignedPercent(analysis.periodReturn)}
            </Text>
          );
        })}
        {selectedTooltip ? (
          <>
            <View style={[styles.indexCrosshair, { left: selectedTooltipX }]} />
            {selectedTooltip.rows.map((row) => {
              const point = getNearestChartPoint(series, row.symbol, selectedTime ?? 0);
              if (!point) {
                return null;
              }
              return (
                <View
                  key={`${row.symbol}-active`}
                  style={[
                    styles.indexActivePoint,
                    {
                      borderColor: indexColor(row.symbol),
                      left: xForTimestamp(point.timestamp) - 6,
                      top: yForValue(point.value) - 6,
                    },
                  ]}
                />
              );
            })}
          <View style={[styles.indexTooltip, { left: getTooltipLeft(selectedTooltipX, chartWidth) }]}>
            <Text style={styles.tooltipTitle}>{selectedTooltip.title}</Text>
            {selectedTooltip.rows.map((row) => (
              <View key={row.symbol} style={styles.tooltipRow}>
                <View style={[styles.tooltipDot, { backgroundColor: indexColor(row.symbol) }]} />
                <Text style={styles.tooltipText}>{row.symbol}</Text>
                <Text style={styles.tooltipValue}>{formatSignedPercent(row.value)}</Text>
              </View>
            ))}
          </View>
          </>
        ) : null}
        {xLabels.map((label) => (
          <Text
            key={label.key}
            numberOfLines={1}
            style={[styles.indexXAxisLabel, { left: Math.max(2, Math.min(chartWidth - 42, xForTimestamp(label.timestamp) - 14)) }]}>
            {label.label}
          </Text>
        ))}
      </Pressable>
    </View>
  );
}

function IndexSeriesLine({
  color,
  points,
  xForTimestamp,
  yForValue,
}: {
  color: string;
  points: IndexChartPoint[];
  xForTimestamp: (timestamp: string) => number;
  yForValue: (value: number) => number;
}) {
  return (
    <>
      {points.slice(1).map((point, index) => {
        const previous = points[index];
        return (
          <ChartLineSegment
            color={color}
            end={{
              x: xForTimestamp(point.timestamp),
              y: yForValue(point.value),
            }}
            key={`${point.timestamp}-${index}`}
            start={{
              x: xForTimestamp(previous.timestamp),
              y: yForValue(previous.value),
            }}
          />
        );
      })}
    </>
  );
}

function ChartLineSegment({
  color,
  end,
  start,
}: {
  color: string;
  end: { x: number; y: number };
  start: { x: number; y: number };
}) {
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  const length = Math.sqrt(dx * dx + dy * dy);
  const angle = Math.atan2(dy, dx);
  const midX = (start.x + end.x) / 2;
  const midY = (start.y + end.y) / 2;
  return (
    <View
      style={[
        styles.indexLineSegment,
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

function buildIndexTooltip(series: IndexAnalysis[], selectedTime: number) {
  const rows = series
    .map((analysis) => {
      const point = analysis.chartPoints.reduce<IndexChartPoint | null>((best, candidate) => {
        if (!best) {
          return candidate;
        }
        return Math.abs(Date.parse(candidate.timestamp) - selectedTime) < Math.abs(Date.parse(best.timestamp) - selectedTime)
          ? candidate
          : best;
      }, null);
      return point
        ? { symbol: analysis.symbol, value: point.value, title: point.dateLabel }
        : null;
    })
    .filter((row): row is { symbol: IndexSymbol; value: number; title: string } => Boolean(row));
  const first = rows[0];
  return {
    rows: indexSymbols
      .map((symbol) => rows.find((row) => row.symbol === symbol))
      .filter((row): row is { symbol: IndexSymbol; value: number; title: string } => Boolean(row)),
    title: first?.title ?? 'Selected point',
  };
}

function calculateChartBounds(min: number, max: number) {
  const rawRange = Math.max(0.05, max - min);
  const padding = Math.max(rawRange * 0.16, rawRange < 0.5 ? 0.03 : 0.15);
  const paddedMin = min - padding;
  const paddedMax = max + padding;
  const ticks = buildAxisTicks(paddedMin, paddedMax);
  return {
    max: Math.max(paddedMax, ticks.at(-1) ?? paddedMax),
    min: Math.min(paddedMin, ticks[0] ?? paddedMin),
    ticks,
  };
}

function buildAxisTicks(min: number, max: number) {
  const range = Math.max(0.05, max - min);
  const step = getAxisStep(range);
  const start = Math.floor(min / step) * step;
  const end = Math.ceil(max / step) * step;
  const ticks: number[] = [];
  for (let value = start; value <= end + step / 2; value += step) {
    ticks.push(roundAxisValue(value));
  }
  const withZero = ticks.some((tick) => Math.abs(tick) < step / 10)
    ? ticks
    : [...ticks, 0];
  return Array.from(new Set(withZero.map(roundAxisValue))).sort((a, b) => a - b);
}

function getAxisStep(range: number) {
  if (range <= 0.3) {
    return 0.05;
  }
  if (range <= 0.8) {
    return 0.1;
  }
  if (range <= 1.5) {
    return 0.25;
  }
  if (range <= 3) {
    return 0.5;
  }
  if (range <= 7) {
    return 1;
  }
  if (range <= 15) {
    return 2;
  }
  return 5;
}

function roundAxisValue(value: number) {
  return Math.round(value * 100) / 100;
}

function buildChartXLabels(series: IndexAnalysis[], timeframe: IndexTimeframe) {
  const longest = series.reduce<IndexChartPoint[]>((best, analysis) => (
    analysis.chartPoints.length > best.length ? analysis.chartPoints : best
  ), []);
  if (!longest.length) {
    return [];
  }
  const targetCount = timeframe === '1D' || timeframe === '1W' ? 3 : 4;
  const lastIndex = longest.length - 1;
  const usedIndexes = new Set<number>();
  return Array.from({ length: targetCount }, (_, index) => {
    const pointIndex = Math.round((index / Math.max(1, targetCount - 1)) * lastIndex);
    if (usedIndexes.has(pointIndex)) {
      return null;
    }
    usedIndexes.add(pointIndex);
    const point = longest[pointIndex];
    return point ? { key: `${point.timestamp}-${pointIndex}`, label: point.dateLabel, timestamp: point.timestamp } : null;
  }).filter((value): value is { key: string; label: string; timestamp: string } => Boolean(value));
}

function getPeriodLeader(analyses: IndexAnalysis[]) {
  const valid = analyses.filter((analysis) => analysis.periodReturn !== null);
  if (!valid.length) {
    return null;
  }
  return [...valid].sort((a, b) => (b.periodReturn ?? 0) - (a.periodReturn ?? 0))[0];
}

function getNearestChartPoint(series: IndexAnalysis[], symbol: IndexSymbol, selectedTime: number) {
  const analysis = series.find((item) => item.symbol === symbol);
  if (!analysis?.chartPoints.length) {
    return null;
  }
  return analysis.chartPoints.reduce((best, candidate) => (
    Math.abs(Date.parse(candidate.timestamp) - selectedTime) < Math.abs(Date.parse(best.timestamp) - selectedTime)
      ? candidate
      : best
  ), analysis.chartPoints[0]);
}

function getTooltipLeft(x: number, width: number) {
  const tooltipWidth = 124;
  const preferLeft = x > width * 0.58;
  const candidate = preferLeft ? x - tooltipWidth - 10 : x + 10;
  return Math.min(Math.max(candidate, 6), Math.max(6, width - tooltipWidth - 6));
}

function getEndpointLabelOffset(index: number, total: number) {
  if (total < 2) {
    return 0;
  }
  return (index - (total - 1) / 2) * 12;
}

function formatAxisPercent(value: number) {
  if (Math.abs(value) < 0.01) {
    return '0%';
  }
  const decimals = Math.abs(value) < 1 ? 1 : 0;
  return `${value > 0 ? '+' : ''}${value.toFixed(decimals)}%`;
}

function IndexComparisonSummary({ analyses, timeframe }: { analyses: IndexAnalysis[]; timeframe: IndexTimeframe }) {
  return (
    <View style={styles.indexPanel}>
      <Text style={styles.detailSectionTitle}>Comparison Summary</Text>
      <View style={styles.indexSummaryRow}>
        {analyses.map((analysis) => (
          <View key={analysis.symbol} style={styles.indexSummaryBlock}>
            <Text style={styles.indexSummarySymbol}>{analysis.symbol}</Text>
            <Text style={[styles.indexSummaryReturn, { color: returnColor(analysis.periodReturn) }]}>
              {formatNullableSignedPercent(analysis.periodReturn)}
            </Text>
            <Text numberOfLines={1} style={styles.indexSummaryMeta}>{timeframe} return</Text>
            <Text numberOfLines={1} style={styles.indexSummaryMeta}>{analysis.trend.label}</Text>
            <Text numberOfLines={1} style={styles.indexSummaryMeta}>{analysis.relativeStrengthLabel}</Text>
            <IndexSummarySparkline analysis={analysis} />
          </View>
        ))}
      </View>
    </View>
  );
}

function WeightedEqualWeightCard({
  availablePairs,
  model,
  onSelectPair,
  onTimeframeChange,
  selectedPair,
  timeframe,
}: {
  availablePairs: WeightComparisonPairId[];
  model: WeightComparisonViewModel;
  onSelectPair: (pair: WeightComparisonPairId) => void;
  onTimeframeChange: (timeframe: IndexTimeframe) => void;
  selectedPair: WeightComparisonPairId;
  timeframe: IndexTimeframe;
}) {
  const [width, setWidth] = useState(0);
  const [selectedPoint, setSelectedPoint] = useState<number | null>(null);
  const chartWidth = Math.max(width, 1);
  const chartHeight = 118;
  const plotTop = 14;
  const plotBottom = 22;
  const plotHeight = chartHeight - plotTop - plotBottom;
  const values = model.points.flatMap((point) => [point.weightedReturn, point.equalWeightReturn]);
  const bounds = calculateChartBounds(Math.min(0, ...values), Math.max(0, ...values));
  const minTime = model.points.length ? Math.min(...model.points.map((point) => Date.parse(point.timestamp))) : 0;
  const maxTime = model.points.length ? Math.max(...model.points.map((point) => Date.parse(point.timestamp))) : minTime;
  const yForValue = (value: number) => plotTop + ((bounds.max - value) / (bounds.max - bounds.min || 1)) * plotHeight;
  const xForTimestamp = (timestamp: string) => {
    const time = Date.parse(timestamp);
    if (!Number.isFinite(time) || maxTime <= minTime) {
      return 12;
    }
    return 12 + ((time - minTime) / (maxTime - minTime)) * Math.max(1, chartWidth - 24);
  };
  const tooltip = selectedPoint === null ? null : model.points[selectedPoint] ?? null;

  return (
    <View style={styles.indexPanel}>
      <View style={styles.sectionHeaderRow}>
        <View>
          <Text style={styles.detailSectionTitle}>Weighted vs Equal Weight</Text>
          <Text style={styles.helperInline}>{timeframe} concentration read</Text>
        </View>
        <StatusBadge label={model.stateLabel} tone={getConcentrationTone(model.state)} />
      </View>
      <CompactTimeframeSelector
        onChange={onTimeframeChange}
        selected={timeframe}
      />
      {availablePairs.length > 1 ? (
        <View style={styles.weightPairSelector}>
          {availablePairs.map((pair) => (
            <Pressable
              accessibilityRole="button"
              key={pair}
              onPress={() => onSelectPair(pair)}
              style={[styles.weightPairButton, selectedPair === pair && styles.weightPairButtonActive]}
            >
              <Text style={[styles.weightPairText, selectedPair === pair && styles.weightPairTextActive]}>
                {pair === 'sp500' ? 'SPY vs RSP' : 'QQQ vs QQEW'}
              </Text>
            </Pressable>
          ))}
        </View>
      ) : null}
      {model.points.length >= 2 ? (
        <Pressable
          accessibilityLabel={`${model.weightedSymbol} versus ${model.equalWeightSymbol} ${timeframe} normalized comparison.`}
          onLayout={(event) => setWidth(event.nativeEvent.layout.width)}
          onPressIn={(event) => {
            const ratio = Math.max(0, Math.min(1, (event.nativeEvent.locationX - 12) / Math.max(1, chartWidth - 24)));
            const targetIndex = Math.round(ratio * (model.points.length - 1));
            setSelectedPoint(targetIndex);
          }}
          style={[styles.weightChartBox, { height: chartHeight }]}
        >
          {bounds.ticks.map((tick) => (
            <View key={tick} style={[styles.indexChartGridLine, tick === 0 && styles.indexChartBaseline, { top: yForValue(tick) }]}>
              <Text style={styles.indexChartYAxisLabel}>{formatAxisPercent(tick)}</Text>
            </View>
          ))}
          <IndexSeriesLine color={Theme.colors.accent} points={model.weightedSeries} xForTimestamp={xForTimestamp} yForValue={yForValue} />
          <IndexSeriesLine color={Theme.colors.purple} points={model.equalWeightSeries} xForTimestamp={xForTimestamp} yForValue={yForValue} />
          {model.points.at(-1) ? (
            <>
              <View style={[styles.indexLatestPoint, { borderColor: Theme.colors.accent, left: xForTimestamp(model.points.at(-1)!.timestamp) - 5, top: yForValue(model.points.at(-1)!.weightedReturn) - 5 }]} />
              <View style={[styles.indexLatestPoint, { borderColor: Theme.colors.purple, left: xForTimestamp(model.points.at(-1)!.timestamp) - 5, top: yForValue(model.points.at(-1)!.equalWeightReturn) - 5 }]} />
            </>
          ) : null}
          {tooltip ? (
            <View style={[styles.indexTooltip, { left: getTooltipLeft(xForTimestamp(tooltip.timestamp), chartWidth) }]}>
              <Text style={styles.tooltipTitle}>{tooltip.dateLabel}</Text>
              <Text style={styles.tooltipValue}>{model.weightedSymbol}: {formatSignedPercent(tooltip.weightedReturn)}</Text>
              <Text style={styles.tooltipValue}>{model.equalWeightSymbol}: {formatSignedPercent(tooltip.equalWeightReturn)}</Text>
              <Text style={styles.tooltipValue}>Spread: {formatSignedPoints(tooltip.spreadPoints)}</Text>
            </View>
          ) : null}
        </Pressable>
      ) : (
        <Text style={styles.healthUnavailableText}>Equal-weight comparison history unavailable.</Text>
      )}
      <View style={styles.weightSummaryGrid}>
        <WeightSummaryMetric
          label={`${model.weightedSymbol} ${timeframe}`}
          value={formatNullableSignedPercent(model.weightedPeriodReturn)}
        />
        <WeightSummaryMetric
          label={`${model.equalWeightSymbol} ${timeframe}`}
          value={formatNullableSignedPercent(model.equalWeightPeriodReturn)}
        />
        <WeightSummaryMetric
          label="Spread"
          value={formatSignedPoints(model.spreadPoints)}
        />
      </View>
      <Text style={styles.bodyText}>{model.summary}</Text>
    </View>
  );
}

function WeightSummaryMetric({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.weightSummaryTile}>
      <Text numberOfLines={1} style={styles.metricLabel}>{label}</Text>
      <Text numberOfLines={1} style={styles.weightSummaryValue}>{value}</Text>
    </View>
  );
}

function IndexSummarySparkline({ analysis }: { analysis: IndexAnalysis }) {
  const points = analysis.chartPoints;
  if (points.length < 2) {
    return <View style={styles.sparklineEmpty} />;
  }
  const width = 86;
  const height = 32;
  const values = points.map((point) => point.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const xForIndex = (index: number) => (index / Math.max(1, points.length - 1)) * width;
  const yForValue = (value: number) => height - ((value - min) / range) * height;
  const tone = (analysis.periodReturn ?? 0) >= 0 ? Theme.colors.success : Theme.colors.danger;
  return (
    <View style={styles.sparklineBox}>
      {points.slice(1).map((point, index) => (
        <ChartLineSegment
          color={tone}
          end={{ x: xForIndex(index + 1), y: yForValue(point.value) }}
          key={`${analysis.symbol}-${point.timestamp}`}
          start={{ x: xForIndex(index), y: yForValue(points[index].value) }}
        />
      ))}
      <View
        style={[
          styles.sparklinePoint,
          {
            borderColor: tone,
            left: xForIndex(points.length - 1) - 4,
            top: yForValue(points[points.length - 1].value) - 4,
          },
        ]}
      />
    </View>
  );
}

function MarketLeadershipTrendCard({ analyses }: { analyses: IndexAnalysis[] }) {
  const read = deriveMarketLeadershipTrend(analyses);
  return (
    <View style={styles.indexPanel}>
      <View style={styles.leadershipHeader}>
        <Text style={styles.detailSectionTitle}>Market Leadership & Trend</Text>
        <View style={styles.leadershipBadgeWrap}>
          <StatusBadge label={read.title} tone={signalStatusTone(read.tone)} />
        </View>
      </View>
      <Text style={styles.bodyText}>{read.explanation}</Text>
    </View>
  );
}

function IndexVolumeParticipationCard({ analyses }: { analyses: IndexAnalysis[] }) {
  const orderedAnalyses = ['SPY', 'QQQ', 'DJI']
    .map((symbol) => analyses.find((analysis) => analysis.symbol === symbol))
    .filter((analysis): analysis is IndexAnalysis => Boolean(analysis));

  return (
    <View style={styles.indexPanel}>
      <Text style={styles.detailSectionTitle}>Volume & Participation</Text>
      <View style={styles.volumeGrid}>
        {orderedAnalyses.map((analysis, index) => (
          <View key={analysis.symbol} style={[styles.volumeTile, index === 0 && styles.volumeTilePrimary]}>
            <View style={styles.volumeTileHeader}>
              <Text style={styles.volumeSymbol}>{analysis.symbol}</Text>
              <View style={[styles.signalPill, { backgroundColor: signalSoftColor(analysis.volume.tone) }]}>
                <Text style={[styles.signalPillText, { color: signalColor(analysis.volume.tone) }]}>
                  {analysis.volume.ratio == null ? 'N/A' : `${analysis.volume.ratio.toFixed(2)}×`}
                </Text>
              </View>
            </View>
            <Text style={styles.volumeLabel}>{analysis.volume.label}</Text>
            <VolumeRatioBar analysis={analysis} />
            <Text style={styles.indexSummaryMeta}>
              {analysis.volume.sourceLabel} · Latest {formatCompactVolume(analysis.volume.latestVolume)}
            </Text>
          </View>
        ))}
      </View>
    </View>
  );
}

function VolumeRatioBar({ analysis }: { analysis: IndexAnalysis }) {
  const ratio = analysis.volume.ratio;
  if (ratio == null) {
    return <View style={styles.volumeUnavailableBar}><Text style={styles.indexSummaryMeta}>Volume unavailable</Text></View>;
  }
  const clampedRatio = Math.min(ratio, 2);
  const fillWidth = `${Math.max(3, (clampedRatio / 2) * 100)}%` as `${number}%`;
  return (
    <View style={styles.volumeRatioTrack}>
      <View style={[styles.volumeRatioFill, { backgroundColor: signalColor(analysis.volume.tone), width: fillWidth }]} />
      <View style={styles.volumeAverageMarker} />
      <Text style={styles.volumeAverageLabel}>1.0×</Text>
    </View>
  );
}

function IndexSetupCard({ analysis, timeframe }: { analysis: IndexAnalysis; timeframe: IndexTimeframe }) {
  const isPositive = analysis.snapshot.change_percent >= 0;
  return (
    <View style={styles.indexSetupCard}>
      <View style={styles.indexSetupHeader}>
        <View>
          <Text style={styles.indexSetupSymbol}>{analysis.symbol}</Text>
          <Text style={styles.indexSetupPrice}>{formatPrice(analysis.snapshot.price)}</Text>
          <Text style={styles.indexSetupLabel}>{analysis.setup.label}</Text>
        </View>
        <View style={styles.priceBlock}>
          <Text style={styles.returnLabel}>Today</Text>
          <Text style={[styles.indexChange, !isPositive && styles.indexChangeNegative]}>
            {formatNullableSignedPercent(analysis.snapshot.change_percent)}
          </Text>
          <Text style={styles.returnLabel}>{timeframe}</Text>
          <Text style={[styles.indexChange, { color: returnColor(analysis.periodReturn) }]}>
            {formatNullableSignedPercent(analysis.periodReturn)}
          </Text>
        </View>
      </View>
      <View style={styles.compactSetupRows}>
        {analysis.setup.rows.map((row) => (
          <IndexSetupLine
            key={`${analysis.symbol}-${row.label}`}
            label={row.label}
            tone={row.tone}
            value={row.value}
          />
        ))}
      </View>
      <ExpandableSection summary="Rules-based rationale" title="Why this setup?">
        <Text style={styles.bodyText}>{analysis.setup.explanation}</Text>
        <View style={styles.technicalStrip}>
          {analysis.setup.technicalRows.map((row) => (
            <TechnicalMiniValue key={`${analysis.symbol}-${row.label}`} label={row.label} value={row.value} />
          ))}
        </View>
      </ExpandableSection>
    </View>
  );
}

function IndexSetupLine({
  label,
  tone,
  value,
}: {
  label: string;
  tone?: IndexSignalTone;
  value: string;
}) {
  return (
    <View style={styles.setupLine}>
      <Text style={styles.setupLineLabel}>{label}</Text>
      <Text style={[styles.setupLineValue, tone && { color: signalColor(tone) }]}>{value}</Text>
    </View>
  );
}

function TechnicalMiniValue({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.technicalMiniValue}>
      <Text style={styles.statLabel}>{label}</Text>
      <Text numberOfLines={1} style={styles.statValue}>{value}</Text>
    </View>
  );
}

function indexColor(symbol: IndexSymbol) {
  switch (symbol) {
    case 'SPY':
      return Theme.colors.accent;
    case 'QQQ':
      return Theme.colors.purple;
    case 'DJI':
      return Theme.colors.success;
    default:
      return Theme.colors.textMuted;
  }
}

function buildMacroXLabels(series: MacroAssetPerformance[], timeframe: MacroTimeframe) {
  const longest = series.reduce<MacroAssetPerformance['chartPoints']>((best, asset) => (
    asset.chartPoints.length > best.length ? asset.chartPoints : best
  ), []);
  if (!longest.length) {
    return [];
  }
  const targetCount = timeframe === '1M' ? 3 : 4;
  const lastIndex = longest.length - 1;
  const usedIndexes = new Set<number>();
  return Array.from({ length: targetCount }, (_, index) => {
    const pointIndex = Math.round((index / Math.max(1, targetCount - 1)) * lastIndex);
    if (usedIndexes.has(pointIndex)) {
      return null;
    }
    usedIndexes.add(pointIndex);
    const point = longest[pointIndex];
    return point ? { key: `${point.timestamp}-${pointIndex}`, label: point.dateLabel, timestamp: point.timestamp } : null;
  }).filter((value): value is { key: string; label: string; timestamp: string } => Boolean(value));
}

function buildMacroTooltip(series: MacroAssetPerformance[], selectedTime: number) {
  const rows = series
    .map((asset) => {
      const point = asset.chartPoints.reduce<MacroAssetPerformance['chartPoints'][number] | null>((best, candidate) => {
        if (!best) {
          return candidate;
        }
        return Math.abs(Date.parse(candidate.timestamp) - selectedTime) < Math.abs(Date.parse(best.timestamp) - selectedTime)
          ? candidate
          : best;
      }, null);
      return point
        ? { label: asset.label, symbol: asset.symbol, title: point.dateLabel, value: point.value }
        : null;
    })
    .filter((row): row is { label: string; symbol: string; title: string; value: number } => Boolean(row))
    .sort((a, b) => b.value - a.value);
  const spy = rows.find((row) => row.symbol === 'SPY')?.value ?? null;
  const defensiveValues = rows
    .filter((row) => row.symbol === 'IEF' || row.symbol === 'TLT' || row.symbol === 'GLD')
    .map((row) => row.value);
  const defensiveAverage = defensiveValues.length
    ? defensiveValues.reduce((sum, value) => sum + value, 0) / defensiveValues.length
    : null;
  return {
    laggard: rows.at(-1)?.symbol ?? 'N/A',
    leader: rows[0]?.symbol ?? 'N/A',
    riskSpread: spy !== null && defensiveAverage !== null ? spy - defensiveAverage : null,
    rows,
    title: rows[0]?.title ?? 'Selected point',
  };
}

function macroAssetColor(symbol: string) {
  switch (symbol) {
    case 'SPY':
      return Theme.colors.accent;
    case 'IEF':
      return '#60A5FA';
    case 'TLT':
      return '#818CF8';
    case 'GLD':
      return Theme.colors.warning;
    case 'USO':
      return Theme.colors.success;
    case 'UUP':
      return '#F472B6';
    case 'HYG':
      return '#2DD4BF';
    default:
      return Theme.colors.textMuted;
  }
}

function macroSourceTone(source: MacroSourceKind): Tone {
  switch (source) {
    case 'live':
      return 'success';
    case 'cached':
    case 'mixed':
    case 'mock':
    case 'fallback':
      return 'warning';
    default:
      return 'muted';
  }
}

function riskAppetiteTone(state: MacroDashboardViewModel['riskAppetite']['state']): Tone {
  switch (state) {
    case 'strong_risk_on':
    case 'risk_on':
      return 'success';
    case 'balanced':
      return 'info';
    case 'defensive_rotation':
      return 'warning';
    case 'risk_off':
      return 'danger';
    default:
      return 'muted';
  }
}

function economicToneToStatus(tone: 'positive' | 'warning' | 'negative' | 'neutral'): Tone {
  switch (tone) {
    case 'positive':
      return 'success';
    case 'warning':
      return 'warning';
    case 'negative':
      return 'danger';
    default:
      return 'muted';
  }
}

function economicToneColor(tone: 'positive' | 'warning' | 'negative' | 'neutral') {
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

function signalStatusTone(tone: IndexSignalTone): Tone {
  switch (tone) {
    case 'positive':
      return 'success';
    case 'warning':
      return 'warning';
    case 'negative':
      return 'danger';
    default:
      return 'muted';
  }
}

function signalColor(tone: IndexSignalTone) {
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

function signalSoftColor(tone: IndexSignalTone) {
  switch (tone) {
    case 'positive':
      return Theme.colors.successSoft;
    case 'warning':
      return Theme.colors.warningSoft;
    case 'negative':
      return Theme.colors.dangerSoft;
    default:
      return Theme.colors.cardMuted;
  }
}

function returnColor(value: number | null) {
  if (value === null || Math.abs(value) < 0.05) {
    return Theme.colors.textMuted;
  }
  return value > 0 ? Theme.colors.success : Theme.colors.danger;
}

function MarketRegimeHero({
  core,
  marketHealth,
  overview,
  regime,
}: {
  core: MarketCoreSnapshot | null;
  marketHealth: MarketHealthResponse | null;
  overview: MarketOverviewDashboardViewModel;
  regime: MarketRegime | null;
}) {
  const score = overview.regime.healthScore ?? marketHealth?.overall_score ?? regime?.breadth.stocks_above_50ma ?? null;
  const status = overview.regime.label ?? marketHealth?.status ?? regime?.status ?? 'Unavailable';
  const freshness = core?.refreshing
    ? 'Cached · updating'
    : core?.cache_status
      ? capitalize(String(core.cache_status))
      : overview.regime.sourceLabel;

  return (
    <View style={styles.regimeHero}>
      <View style={styles.regimeHeader}>
        <View style={styles.regimeTitleBlock}>
          <Text style={styles.heroKicker}>Market Regime</Text>
          <Text style={styles.regimeTitle}>{status}</Text>
          <Text style={styles.regimeScore}>
            Health Score · {typeof score === 'number' ? `${Math.round(score)} / 100` : 'N/A'}
          </Text>
          <Text style={styles.regimeScore}>Conviction · {overview.regime.confidence}</Text>
        </View>
        {freshness ? <StatusBadge label={freshness} tone={core?.refreshing ? 'warning' : 'muted'} /> : null}
      </View>
      {typeof score === 'number' ? (
        <ProgressBar showValue={false} tone={getScoreTone(score)} value={score} />
      ) : null}
      <Text style={styles.regimeExplanation}>
        {overview.regime.summary}
      </Text>
    </View>
  );
}

function MarketSnapshotGrid({ overview }: { overview: MarketOverviewDashboardViewModel }) {
  return (
    <View style={styles.indexPanel}>
      <Text style={styles.detailSectionTitle}>Market Snapshot</Text>
      <View style={styles.overviewSnapshotGrid}>
        {overview.snapshot.map((tile) => (
          <View key={tile.key} style={styles.overviewSnapshotTile}>
            <View style={styles.overviewSnapshotHeader}>
              <Text style={styles.metricLabel}>{tile.label}</Text>
              <View style={[styles.keySignalDot, { backgroundColor: overviewToneColor(tile.tone) }]} />
            </View>
            <Text style={styles.metricValue}>{tile.primary}</Text>
            {tile.secondary ? <Text style={styles.metricSubvalue}>{tile.secondary}</Text> : null}
          </View>
        ))}
      </View>
    </View>
  );
}

function SignalAlignmentCard({ overview }: { overview: MarketOverviewDashboardViewModel }) {
  return (
    <View style={styles.indexPanel}>
      <Text style={styles.detailSectionTitle}>Signal Alignment</Text>
      <OverviewAlignmentRow label="Supportive" items={overview.alignment.supportive} tone="positive" />
      <OverviewAlignmentRow label="Mixed" items={overview.alignment.mixed} tone="warning" />
      <OverviewAlignmentRow label="Caution" items={overview.alignment.caution} tone="negative" />
      <Text style={styles.bodyText}>{overview.alignment.summary}</Text>
    </View>
  );
}

function OverviewAlignmentRow({
  items,
  label,
  tone,
}: {
  items: MarketOverviewDashboardViewModel['alignment']['supportive'];
  label: string;
  tone: MarketOverviewTone;
}) {
  if (!items.length) {
    return null;
  }
  return (
    <View style={styles.overviewAlignmentRow}>
      <Text style={styles.metricLabel}>{label}</Text>
      <View style={styles.overviewChipRow}>
        {items.map((item) => (
          <View key={`${label}-${item.key}`} style={[styles.overviewChip, { borderColor: overviewToneColor(tone) }]}>
            <Text style={[styles.overviewChipText, { color: overviewToneColor(tone) }]}>{item.label}</Text>
          </View>
        ))}
      </View>
    </View>
  );
}

function MarketInsightPanel({
  aiSummary,
  overview,
}: {
  aiSummary: ReturnType<typeof useMarketDashboard>['aiSummary'];
  overview: MarketOverviewDashboardViewModel;
}) {
  void aiSummary;
  return (
    <View style={styles.insightCard}>
      <View style={styles.insightHeader}>
        <Text style={styles.sectionTitle}>Market Insight</Text>
        <Text style={styles.insightMeta}>Rules-based</Text>
      </View>
      <Text style={styles.insightSummary}>{overview.insight}</Text>
    </View>
  );
}

function MarketDecisionPostureCard({ overview }: { overview: MarketOverviewDashboardViewModel }) {
  const posture = overview.decisionPosture;
  return (
    <View style={styles.indexPanel}>
      <View style={styles.sectionHeaderRow}>
        <View style={styles.summaryTitleBlock}>
          <Text style={styles.detailSectionTitle}>Decision Posture</Text>
          <Text style={styles.helperInline}>Confidence · {posture.confidence === null ? 'N/A' : `${Math.round(posture.confidence)}%`}</Text>
        </View>
        <StatusBadge label={posture.posture} tone={overviewStatusTone(posture.tone)} />
      </View>
      <Text style={styles.bodyText}>{posture.implication}</Text>
      <View style={styles.macroLeadLagGrid}>
        <MetricTile label="Prefer" value={posture.prefer ?? 'N/A'} />
        <MetricTile label="Avoid" value={posture.avoid ?? 'N/A'} />
        <MetricTile label="Monitor" value={posture.monitor ?? 'N/A'} />
      </View>
    </View>
  );
}

function KeySignals({ overview }: { overview: MarketOverviewDashboardViewModel }) {
  return (
    <View style={styles.signalCard}>
      <Text style={styles.sectionTitle}>Key Signals</Text>
      <View style={styles.keySignalList}>
        {overview.keySignals.length ? overview.keySignals.map((signal) => (
          <OverviewSignalRow key={signal.key} signal={signal} />
        )) : <Text style={styles.helperText}>Key signals unavailable until more market data loads.</Text>}
      </View>
    </View>
  );
}

function OverviewSignalRow({ signal }: { signal: MarketOverviewSignal }) {
  return (
    <View style={styles.keySignalRow}>
      <View style={[styles.keySignalDot, { backgroundColor: overviewToneColor(signal.tone) }]} />
      <Text style={styles.keySignalText}>{signal.label}</Text>
    </View>
  );
}

function MarketOverviewDataQuality({ overview }: { overview: MarketOverviewDashboardViewModel }) {
  return (
    <ExpandableSection summary={overview.dataQuality.label} title="Data Quality">
      <Text style={styles.helperText}>Overview combines Market Health, Indexes, Breadth, Institutions, Macro, Decision, and leadership signals when available. Missing dimensions are omitted rather than treated as neutral.</Text>
    </ExpandableSection>
  );
}

function overviewToneColor(tone: MarketOverviewTone) {
  switch (tone) {
    case 'positive':
      return Theme.colors.success;
    case 'warning':
      return Theme.colors.warning;
    case 'negative':
      return Theme.colors.danger;
    case 'neutral':
      return Theme.colors.accent;
    default:
      return Theme.colors.textMuted;
  }
}

function overviewStatusTone(tone: MarketOverviewTone): Tone {
  switch (tone) {
    case 'positive':
      return 'success';
    case 'warning':
      return 'warning';
    case 'negative':
      return 'danger';
    case 'neutral':
      return 'info';
    default:
      return 'muted';
  }
}

function LazyMarketDetails({
  children,
  group,
  loadDetails,
  loading,
}: {
  children: ReactNode;
  group: 'structure' | 'decision' | 'institutional';
  loadDetails: (group: 'structure' | 'decision' | 'institutional') => void;
  loading: boolean;
}) {
  useEffect(() => {
    loadDetails(group);
  }, [group, loadDetails]);

  return (
    <View style={styles.sectionStack}>
      {loading ? <SkeletonCard compact rows={3} /> : null}
      {children}
    </View>
  );
}

function BreadthDetails({
  breadth,
  indexes,
  weightConcentration,
}: {
  breadth: MarketBreadthResponse | null;
  indexes: IndexSnapshot[];
  weightConcentration: ReturnType<typeof buildConcentrationBreadthSignal>;
}) {
  const [selectedMockScenario, setSelectedMockScenario] = useState<BreadthMockScenarioKey>('healthyBull');
  const mockScenario = typeof __DEV__ !== 'undefined' && __DEV__
    ? buildBreadthMockScenario(selectedMockScenario)
    : null;
  const activeBreadth = mockScenario?.breadth ?? breadth;
  const activeIndexes = mockScenario?.indexes ?? indexes;
  const baseDashboard = buildBreadthDashboard(activeBreadth, activeIndexes);
  const dashboard = mockScenario ? applyBreadthMockScenarioDashboard(baseDashboard, mockScenario) : baseDashboard;
  return (
    <View style={styles.sectionStack}>
      {mockScenario ? (
        <BreadthMockScenarioSwitcher
          selected={selectedMockScenario}
          onChange={setSelectedMockScenario}
        />
      ) : null}
      <BreadthOverviewCard dashboard={dashboard} />
      <BreadthProfileCard metrics={dashboard.profile} />
      {weightConcentration ? <BreadthConcentrationSignalCard signal={weightConcentration} /> : null}
      <BreadthConfirmationCard dashboard={dashboard} />
      <AdvanceDeclineCard data={dashboard.advanceDecline} />
      <HighLowCard data={dashboard.highLow} />
      <MovingAverageBreadthCard data={dashboard.movingAverageProfile} />
      <BreadthQualityCard data={dashboard.quality} strengthScore={dashboard.composite.score} />
      <BreadthTrendCard />
      <BreadthTakeawayCard dashboard={dashboard} />
    </View>
  );
}

function BreadthConcentrationSignalCard({ signal }: { signal: NonNullable<ReturnType<typeof buildConcentrationBreadthSignal>> }) {
  return (
    <View style={styles.breadthPanel}>
      <View style={styles.sectionHeaderRow}>
        <View>
          <Text style={styles.detailSectionTitle}>{signal.label}</Text>
          <Text style={styles.helperInline}>Weighted vs equal-weight signal</Text>
        </View>
        <StatusBadge label={signal.status} tone={getConcentrationTone(signal.state)} />
      </View>
      <View style={styles.breadthInlineMetrics}>
        <MiniDecisionMetric label="Spread" value={formatSignedPoints(signal.value)} />
      </View>
      <Text style={styles.bodyText}>{signal.summary}</Text>
    </View>
  );
}

function BreadthMockScenarioSwitcher({
  onChange,
  selected,
}: {
  onChange: (value: BreadthMockScenarioKey) => void;
  selected: BreadthMockScenarioKey;
}) {
  return (
    <View style={styles.breadthMockPanel}>
      <View style={styles.sectionHeaderRow}>
        <View>
          <Text style={styles.detailSectionTitle}>Mock Scenario</Text>
          <Text style={styles.helperInline}>Development-only breadth test data</Text>
        </View>
        <StatusBadge label="Test Data" tone="warning" />
      </View>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.breadthMockOptions}
      >
        {BREADTH_MOCK_SCENARIOS.map((scenario) => {
          const active = scenario.key === selected;
          return (
            <Pressable
              accessibilityLabel={`Use ${scenario.label} breadth scenario`}
              accessibilityRole="button"
              key={scenario.key}
              onPress={() => onChange(scenario.key)}
              style={[styles.breadthMockChip, active && styles.breadthMockChipActive]}
            >
              <Text style={[styles.breadthMockChipText, active && styles.breadthMockChipTextActive]}>
                {scenario.label}
              </Text>
            </Pressable>
          );
        })}
      </ScrollView>
    </View>
  );
}

function BreadthOverviewCard({ dashboard }: { dashboard: BreadthDashboardViewModel }) {
  const { overview, advanceDecline, quality } = dashboard;
  return (
    <View style={styles.breadthHeroCard}>
      <View style={styles.biasHeader}>
        <View>
          <Text style={styles.biasLabel}>Breadth Overview</Text>
          <Text style={styles.breadthHeroStatus}>{overview.status}</Text>
        </View>
        <StatusBadge label={quality.confidenceLabel} tone={getBreadthConfidenceTone(quality.confidence)} />
      </View>
      <View style={styles.breadthHeroMetrics}>
        <MiniDecisionMetric label="Composite" value={formatNullableNumber(overview.score)} />
        <MiniDecisionMetric label="A/D Ratio" value={formatBreadthRatio(advanceDecline.ratio)} />
        <MiniDecisionMetric
          label="Participation"
          value={`${formatNullableNumber(advanceDecline.advancing)} advancing · ${formatNullableNumber(advanceDecline.declining)} declining`}
        />
      </View>
      <Text style={styles.biasSummary}>{overview.interpretation}</Text>
    </View>
  );
}

function BreadthProfileCard({ metrics }: { metrics: BreadthProfileMetric[] }) {
  return (
    <View style={styles.breadthPanelEmphasis}>
      <View style={styles.sectionHeaderRow}>
        <View>
          <Text style={styles.detailSectionTitle}>Breadth Profile</Text>
          <Text style={styles.helperInline}>Current participation dimensions</Text>
        </View>
      </View>
      <View style={styles.breadthProfileStack}>
        {metrics.map((metric) => (
          <View key={metric.key} style={styles.breadthProfileMetricRow}>
            <View style={styles.breadthProfileLabelBlock}>
              <Text numberOfLines={1} style={styles.breadthProfileMetricLabel}>{metric.label}</Text>
              <Text numberOfLines={1} style={styles.breadthProfileMetricStatus}>{metric.status}</Text>
            </View>
            <View style={styles.breadthProfileMetricTrack}>
              <View style={styles.breadthProfileMidpoint} />
              {metric.value !== null ? (
                <View
                  style={[
                    styles.breadthProfileMetricFill,
                    breadthFillStyle(metric.tone),
                    { width: `${Math.max(0, Math.min(100, metric.value))}%` },
                  ]}
                />
              ) : null}
            </View>
            <Text numberOfLines={1} style={styles.breadthProfileMetricValue}>
              {formatBreadthPercent(metric.value)}
            </Text>
          </View>
        ))}
      </View>
    </View>
  );
}

function BreadthConfirmationCard({ dashboard }: { dashboard: BreadthDashboardViewModel }) {
  const { divergence } = dashboard;
  return (
    <View style={styles.breadthPanel}>
      <View style={styles.sectionHeaderRow}>
        <View>
          <Text style={styles.detailSectionTitle}>Breadth Confirmation</Text>
          <Text style={styles.helperInline}>SPY vs Breadth Composite</Text>
        </View>
        <StatusBadge label={divergence.confirmationLabel} tone={getBreadthTone(divergence.tone)} />
      </View>
      <View style={styles.breadthConfirmationSummary}>
        <MiniDecisionMetric label="Confirmation Score" value={formatNullableNumber(divergence.confirmationScore)} />
        <MiniDecisionMetric label="Risk" value={divergence.riskDirection} />
      </View>
      <Text style={styles.healthUnavailableText}>
        History unavailable. SPY-versus-breadth comparison will appear when real breadth snapshots are available.
      </Text>
      {divergence.state !== 'unavailable' ? <Text style={styles.bodyText}>{divergence.explanation}</Text> : null}
    </View>
  );
}

function AdvanceDeclineCard({ data }: { data: AdvanceDeclineViewModel }) {
  return (
    <View style={styles.breadthPanel}>
      <View style={styles.sectionHeaderRow}>
        <Text style={styles.detailSectionTitle}>Advance vs Decline</Text>
        <StatusBadge label={data.state} tone={getBreadthTone(data.tone)} />
      </View>
      <View style={styles.splitBarLabels}>
        <Text style={styles.splitBarLabel}>Advancing {formatBreadthPercent(data.advancingPercent)}</Text>
        <Text style={styles.splitBarLabel}>Declining {formatBreadthPercent(data.decliningPercent)}</Text>
      </View>
      <SplitBar
        leftLabel="Advancing"
        leftPercent={data.advancingPercent}
        leftTone="positive"
        leftValue={formatNullableNumber(data.advancing)}
        middlePercent={data.unchanged && data.unchanged > 0 ? data.unchangedPercent : null}
        middleValue={data.unchanged && data.unchanged > 0 ? formatNullableNumber(data.unchanged) : undefined}
        rightLabel="Declining"
        rightPercent={data.decliningPercent}
        rightTone="negative"
        rightValue={formatNullableNumber(data.declining)}
      />
      <View style={styles.breadthInlineMetrics}>
        <MiniDecisionMetric label="A/D Ratio" value={formatBreadthRatio(data.ratio)} />
        <MiniDecisionMetric
          label="Counts"
          value={`${formatNullableNumber(data.advancing)} advancing · ${formatNullableNumber(data.declining)} declining${data.unchanged ? ` · ${formatNullableNumber(data.unchanged)} unchanged` : ''}`}
        />
      </View>
      <Text style={styles.bodyText}>{data.interpretation}</Text>
    </View>
  );
}

function HighLowCard({ data }: { data: HighLowViewModel }) {
  return (
    <View style={styles.breadthPanel}>
      <View style={styles.sectionHeaderRow}>
        <Text style={styles.detailSectionTitle}>New Highs vs New Lows</Text>
        <StatusBadge label={data.state} tone={getBreadthTone(data.tone)} />
      </View>
      {data.showDetails ? (
        <>
          <SplitBar
            leftLabel="52W Highs"
            leftPercent={data.highPercent}
            leftTone="positive"
            leftValue={formatNullableNumber(data.highs)}
            rightLabel="52W Lows"
            rightPercent={data.lowPercent}
            rightTone="negative"
            rightValue={formatNullableNumber(data.lows)}
          />
          <View style={styles.breadthInlineMetrics}>
            <MiniDecisionMetric label="Differential" value={formatSignedInteger(data.differential)} />
            <MiniDecisionMetric label="High/Low Ratio" value={data.ratioLabel} />
          </View>
        </>
      ) : (
        <View style={styles.breadthCompactEmpty}>
          <Text style={styles.healthUnavailableText}>No leadership signal</Text>
        </View>
      )}
      <Text style={styles.bodyText}>{data.interpretation}</Text>
    </View>
  );
}

function MovingAverageBreadthCard({ data }: { data: MovingAverageBreadthViewModel }) {
  return (
    <View style={styles.breadthPanel}>
      <View style={styles.sectionHeaderRow}>
        <Text style={styles.detailSectionTitle}>Moving-Average Breadth</Text>
        <StatusBadge label={data.state} tone={getBreadthTone(data.tone)} />
      </View>
      <Text style={styles.breadthProfileSummary}>{data.summary}</Text>
      <View style={styles.breadthProfileStack}>
        {data.items.map((item) => (
          <View key={item.key} style={styles.healthProfileRow}>
            <Text style={styles.healthProfileLabel}>{item.label}</Text>
            <View style={styles.healthProfileTrack}>
              {item.value !== null ? (
                <View
                  style={[
                    styles.healthProfileFill,
                    breadthFillStyle(item.tone),
                    { width: `${Math.max(0, Math.min(100, item.value))}%` },
                  ]}
                />
              ) : null}
            </View>
            <Text numberOfLines={1} style={styles.healthProfileScore}>{formatBreadthPercent(item.value)}</Text>
          </View>
        ))}
      </View>
      <Text style={styles.bodyText}>{data.interpretation}</Text>
    </View>
  );
}

function BreadthQualityCard({
  data,
  strengthScore,
}: {
  data: BreadthDashboardViewModel['quality'];
  strengthScore: number | null;
}) {
  return (
    <View style={styles.breadthPanel}>
      <View style={styles.sectionHeaderRow}>
        <Text style={styles.detailSectionTitle}>Breadth Quality</Text>
        <StatusBadge label={data.sourceLabel} tone={getSourceTone({ overall_mode: data.sourceLabel })} />
      </View>
      <View style={styles.breadthInlineMetrics}>
        <MiniDecisionMetric label="Breadth Strength" value={data.strengthLabel} />
        <MiniDecisionMetric label="Data Confidence" value={data.confidenceLabel} />
      </View>
      <View style={styles.breadthQualityBars}>
        <QualityBar label="Breadth Strength" tone={strengthScore !== null ? toneForNumericScore(strengthScore) : 'neutral'} value={strengthScore} />
        <QualityBar label="Data Confidence" tone={data.confidence === 'high' ? 'positive' : 'warning'} value={data.coveragePercent} />
      </View>
      <View style={styles.coverageScaleLabels}>
        <Text style={styles.helperInline}>0%</Text>
        <Text style={styles.helperInline}>50%</Text>
        <Text style={styles.helperInline}>100%</Text>
      </View>
      <View style={styles.coverageGaugeTrack}>
        <View
          style={[
            styles.coverageGaugeFill,
            breadthFillStyle(data.confidence === 'high' ? 'positive' : data.confidence === 'moderate' ? 'warning' : 'negative'),
            { width: `${Math.max(0, Math.min(100, data.coveragePercent ?? 0))}%` },
          ]}
        />
      </View>
      <Text style={styles.helperText}>
        {formatCoverageCounts(data.trackedStocks, data.expectedUniverse)} · {formatBreadthPercent(data.coveragePercent)} universe coverage
      </Text>
      <Text style={styles.bodyText}>{data.limitation}</Text>
    </View>
  );
}

function QualityBar({
  label,
  tone,
  value,
}: {
  label: string;
  tone: BreadthSignalTone;
  value: number | null;
}) {
  return (
    <View style={styles.qualityBarRow}>
      <Text style={styles.qualityBarLabel}>{label}</Text>
      <View style={styles.qualityBarTrack}>
        {value !== null ? (
          <View
            style={[
              styles.qualityBarFill,
              breadthFillStyle(tone),
              { width: `${Math.max(0, Math.min(100, value))}%` },
            ]}
          />
        ) : null}
      </View>
      <Text numberOfLines={1} style={styles.qualityBarValue}>{formatBreadthPercent(value)}</Text>
    </View>
  );
}

function BreadthTrendCard() {
  return (
    <View style={styles.breadthPanel}>
      <View style={styles.sectionHeaderRow}>
        <Text style={styles.detailSectionTitle}>Breadth Trend</Text>
        <StatusBadge label="History Unavailable" tone="muted" />
      </View>
      <Text style={styles.healthUnavailableText}>
        Historical breadth will appear when real snapshots are available.
      </Text>
    </View>
  );
}

function BreadthTakeawayCard({ dashboard }: { dashboard: BreadthDashboardViewModel }) {
  const { takeaway } = dashboard;
  return (
    <View style={styles.breadthHeroCard}>
      <View style={styles.sectionHeaderRow}>
        <Text style={styles.detailSectionTitle}>Key Takeaway</Text>
        <StatusBadge label={`Risk: ${takeaway.risk}`} tone={getBreadthTone(getRiskLabelTone(takeaway.risk))} />
      </View>
      <Text style={styles.biasSummary}>{takeaway.conclusion}</Text>
    </View>
  );
}

function SplitBar({
  leftLabel,
  leftPercent,
  leftTone,
  leftValue,
  middlePercent,
  middleValue,
  rightLabel,
  rightPercent,
  rightTone,
  rightValue,
}: {
  leftLabel: string;
  leftPercent: number | null;
  leftTone: BreadthSignalTone;
  leftValue: string;
  middlePercent?: number | null;
  middleValue?: string;
  rightLabel: string;
  rightPercent: number | null;
  rightTone: BreadthSignalTone;
  rightValue: string;
}) {
  const leftWidth = leftPercent ?? 0;
  const rightWidth = rightPercent ?? 0;
  const middleWidth = middlePercent ?? 0;
  return (
    <View style={styles.splitBarStack}>
      <View style={styles.splitBarLabels}>
        <Text style={styles.splitBarLabel}>{leftLabel} {leftValue}</Text>
        {middlePercent != null ? <Text style={styles.splitBarLabel}>Unchanged {middleValue}</Text> : null}
        <Text style={styles.splitBarLabel}>{rightLabel} {rightValue}</Text>
      </View>
      <View style={styles.splitBarTrack}>
        <View style={styles.splitBarMidpoint} />
        <View style={[styles.splitBarSegment, breadthFillStyle(leftTone), { flex: leftWidth || 0.0001 }]} />
        {middlePercent != null ? <View style={[styles.splitBarSegment, styles.splitBarNeutral, { flex: middleWidth || 0.0001 }]} /> : null}
        <View style={[styles.splitBarSegment, breadthFillStyle(rightTone), { flex: rightWidth || 0.0001 }]} />
      </View>
    </View>
  );
}

function DecisionDashboardDetails({
  capRotation,
  decisionDashboard,
  fearGreed,
}: {
  capRotation: MarketCapRotationResponse | null;
  decisionDashboard: DecisionDashboardResponse | null;
  fearGreed: FearGreedResponse | null;
}) {
  const dashboard = buildDecisionDashboardViewModel(decisionDashboard, capRotation, fearGreed);
  if (!dashboard) {
    return (
      <View style={styles.breadthPanel}>
        <Text style={styles.detailSectionTitle}>Decision Overview</Text>
        <Text style={styles.bodyText}>Decision intelligence unavailable.</Text>
      </View>
    );
  }

  return (
    <View style={styles.sectionStack}>
      <DecisionOverviewCard dashboard={dashboard} />
      <PreferredSetupsCard dashboard={dashboard} />
      <DecisionChecklistCard dashboard={dashboard} />
      <MarketScenariosCard dashboard={dashboard} />
      <DecisionCapRotationCard data={dashboard.capRotation} />
      <DecisionFearGreedCard data={dashboard.sentiment} />
      <WhatChangedCard data={dashboard.changes} />
    </View>
  );
}

function DecisionOverviewCard({ dashboard }: { dashboard: DecisionViewModel }) {
  const { posture } = dashboard;
  return (
    <View style={styles.decisionHeroCard}>
      <View style={styles.decisionHeroHeader}>
        <View style={styles.decisionHeroTitleBlock}>
          <Text style={styles.biasLabel}>Decision Overview</Text>
          <Text style={styles.decisionHeroTitle}>{posture.postureLabel}</Text>
        </View>
        {posture.riskBadgeLabel ? <StatusBadge label={posture.riskBadgeLabel} tone={getDecisionTone(posture.tone)} /> : null}
      </View>
      <Text style={styles.biasSummary}>{posture.actionFramework}</Text>
      <View style={styles.decisionMetricRow}>
        <MiniDecisionMetric label="Confidence" value={formatNullablePercent(posture.confidence)} />
        <MiniDecisionMetric label="Exposure Stance" value={formatNullableNumber(posture.aggressivenessScore)} />
        <MiniDecisionMetric label="Risk" value={`${formatNullableNumber(posture.riskScore)} / 100`} />
      </View>
      <View style={styles.decisionFieldGrid}>
        {posture.focus && !dashboard.leadershipFocus.length ? <DecisionField label="Focus" value={posture.focus} /> : null}
        {posture.prefer ? <DecisionField label="Prefer" value={posture.prefer} /> : null}
        {posture.mainRisk ? <DecisionField label="Avoid" value={posture.mainRisk} tone="warning" /> : null}
        {posture.monitor ? <DecisionField label="Monitor" value={posture.monitor} tone="warning" /> : null}
      </View>
      {dashboard.leadershipFocus.length ? (
        <View style={styles.decisionChipsRow}>
          {dashboard.leadershipFocus.map((item) => (
            <View key={item} style={styles.decisionChip}>
              <Text style={styles.decisionChipText}>{item}</Text>
            </View>
          ))}
        </View>
      ) : null}
      <CompactDisclosure title="Why this playbook?" items={posture.why} />
    </View>
  );
}

function DecisionField({ label, tone = 'default', value }: { label: string; tone?: 'default' | 'warning'; value: string }) {
  return (
    <View style={styles.decisionField}>
      <Text style={styles.metricLabel}>{label}</Text>
      <Text style={[styles.decisionFieldValue, tone === 'warning' && { color: Theme.colors.warning }]}>{value}</Text>
    </View>
  );
}

function PreferredSetupsCard({ dashboard }: { dashboard: DecisionViewModel }) {
  return (
    <View style={styles.decisionPanel}>
      <SectionTitle title="Preferred Setups" />
      <View style={styles.decisionList}>
        {dashboard.preferredSetups.length ? dashboard.preferredSetups.map((setup, index) => (
          <View key={setup.label} style={styles.decisionSetupRow}>
            <Text style={styles.decisionRank}>{index + 1}</Text>
            <View style={styles.decisionSetupBody}>
              <Text style={styles.sectorBreadthName}>{setup.label}</Text>
            </View>
            <StatusBadge label={setup.suitabilityLabel} tone={getDecisionTone(setup.tone)} />
          </View>
        )) : (
          <Text style={styles.healthUnavailableText}>Preferred setups unavailable.</Text>
        )}
      </View>
    </View>
  );
}

function DecisionChecklistCard({ dashboard }: { dashboard: DecisionViewModel }) {
  const { checklist } = dashboard;
  return (
    <View style={styles.decisionPanel}>
      <View style={styles.sectionHeaderRow}>
        <View>
          <Text style={styles.detailSectionTitle}>Market Checklist</Text>
          <Text style={styles.helperInline}>{checklist.confirmed} / {checklist.total} Confirmed</Text>
        </View>
        <StatusBadge label={checklist.grade} tone={getChecklistTone(checklist.grade)} />
      </View>
      <View style={styles.checklistSummaryRow}>
        <StatusBadge label={`${checklist.pass} Pass`} tone="success" />
        <StatusBadge label={`${checklist.monitor} Monitor`} tone="warning" />
        <StatusBadge label={`${checklist.fail} Fail`} tone={checklist.fail ? 'danger' : 'muted'} />
      </View>
      <View style={styles.decisionChecklistGrid}>
        {checklist.items.map((item) => (
          <View key={item.label} style={styles.decisionChecklistItem}>
            <Text style={styles.decisionChecklistLabel}>{item.label}</Text>
            <StatusBadge label={item.statusLabel} tone={getDecisionTone(item.tone)} />
            <Text numberOfLines={1} style={styles.helperInline}>{item.value}</Text>
          </View>
        ))}
      </View>
    </View>
  );
}

function MarketScenariosCard({ dashboard }: { dashboard: DecisionViewModel }) {
  const { scenarios } = dashboard;
  return (
    <View style={styles.decisionPanel}>
      <View style={styles.sectionHeaderRow}>
        <View>
          <Text style={styles.detailSectionTitle}>Market Scenarios</Text>
          <Text style={styles.helperInline}>{scenarios.label}</Text>
        </View>
      </View>
      <Text style={styles.bodyText}>{scenarios.summary}</Text>
      <View style={styles.healthComponentList}>
        {scenarios.scenarios.length ? scenarios.scenarios.map((scenario) => (
          <View key={scenario.label} style={styles.healthComponentRow}>
            <ProgressBar label={`${scenario.label} · ${scenario.value}%`} tone={getDecisionTone(scenario.tone)} value={scenario.value} />
          </View>
        )) : (
          <Text style={styles.healthUnavailableText}>Market scenarios unavailable.</Text>
        )}
      </View>
      <View style={styles.decisionInvalidationBox}>
        <Text style={styles.metricLabel}>Main Invalidation</Text>
        <Text style={styles.bodyText}>{scenarios.invalidation}</Text>
      </View>
    </View>
  );
}

function DecisionCapRotationCard({ data }: { data: MarketCapRotationViewModel }) {
  return (
    <View style={styles.decisionPanel}>
      <View style={styles.sectionHeaderRow}>
        <View>
          <Text style={styles.detailSectionTitle}>Market Cap Rotation</Text>
          <Text style={styles.helperInline}>{data.stateLabel}</Text>
        </View>
        {data.leader ? <StatusBadge label={`${data.leader} Leading`} tone="info" /> : null}
      </View>
      <View style={styles.healthComponentList}>
        {data.items.length ? data.items.map((item) => (
          <View key={item.category} style={styles.healthComponentRow}>
            <ProgressBar label={`${item.category} · ${item.score}`} tone={getScoreTone(item.score)} value={item.score} />
            <Text style={styles.healthExplanation}>
              {item.status} · {item.symbol} proxy · {formatSigned(item.return_1w)}% over 1W
            </Text>
          </View>
        )) : (
          <Text style={styles.healthUnavailableText}>Market-cap rotation unavailable.</Text>
        )}
      </View>
      <Text style={styles.bodyText}>{data.read}</Text>
      <CompactDisclosure
        title="How groups are measured"
        items={['Market-cap groups are compared using configured ETF or index proxies. The score reflects relative performance and technical strength; it is not fund-flow data unless a live flow source is explicitly connected.']}
      />
    </View>
  );
}

function DecisionFearGreedCard({ data }: { data: FearGreedViewModel }) {
  const marker = gaugeMarkerPercent(data.score);
  return (
    <View style={styles.decisionPanel}>
      <View style={styles.sectionHeaderRow}>
        <View>
          <Text style={styles.detailSectionTitle}>Fear & Greed Index</Text>
          <Text style={styles.helperInline}>Sentiment gauge</Text>
        </View>
        <StatusBadge label={data.status} tone={getDecisionTone(data.tone)} />
      </View>
      {data.score !== null ? (
        <>
          <Text style={styles.decisionGaugeScore}>{formatNullableNumber(data.score)}</Text>
          <View style={styles.fearGreedGaugeTrack}>
            <View style={[styles.fearGreedGaugeZone, { backgroundColor: Theme.colors.dangerSoft, flex: 24 }]} />
            <View style={[styles.fearGreedGaugeZone, { backgroundColor: Theme.colors.warningSoft, flex: 20 }]} />
            <View style={[styles.fearGreedGaugeZone, { backgroundColor: Theme.colors.cardElevated, flex: 11 }]} />
            <View style={[styles.fearGreedGaugeZone, { backgroundColor: Theme.colors.successSoft, flex: 20 }]} />
            <View style={[styles.fearGreedGaugeZone, { backgroundColor: Theme.colors.warningSoft, flex: 25 }]} />
            <View style={[styles.fearGreedGaugeMarker, { left: `${marker}%` }]} />
          </View>
          <View style={styles.fearGreedLabels}>
            <Text style={styles.helperInline}>Extreme Fear</Text>
            <Text style={styles.helperInline}>Fear</Text>
            <Text style={styles.helperInline}>Neutral</Text>
            <Text style={styles.helperInline}>Greed</Text>
            <Text style={styles.helperInline}>Extreme Greed</Text>
          </View>
        </>
      ) : (
        <Text style={styles.healthUnavailableText}>Fear & Greed score unavailable.</Text>
      )}
      <Text style={styles.bodyText}>{data.interpretation}</Text>
      <CompactDisclosure
        title="How this is calculated"
        items={['This is an APInvest proxy built from internal sentiment components such as market momentum, breadth, options tone, volatility, and risk appetite. It is not the official CNN Fear & Greed Index and does not use external CNN data.']}
      />
    </View>
  );
}

function WhatChangedCard({ data }: { data: DecisionChangeViewModel }) {
  return (
    <View style={styles.decisionPanel}>
      <SectionTitle title="What Changed" />
      {data.unavailable ? (
        <Text style={styles.healthUnavailableText}>Recent changes unavailable.</Text>
      ) : (
        <View style={styles.decisionChangeGrid}>
          {data.groups.map((group) => (
            <View key={group.direction} style={styles.decisionChangeGroup}>
              <StatusBadge label={group.label} tone={getDecisionTone(group.tone)} />
              {group.items.map((item) => (
                <Text key={`${group.direction}-${item}`} style={styles.bodyText}>• {item}</Text>
              ))}
            </View>
          ))}
        </View>
      )}
      <Text style={styles.helperText}>{data.implication}</Text>
    </View>
  );
}

function CompactDisclosure({ items, title }: { items: string[]; title: string }) {
  const [expanded, setExpanded] = useState(false);
  if (!items.length) {
    return null;
  }
  return (
    <View style={styles.compactDisclosure}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={`${expanded ? 'Hide' : 'Show'} ${title}`}
        onPress={() => setExpanded((value) => !value)}
        style={styles.compactDisclosureButton}
      >
        <Text style={styles.compactDisclosureTitle}>{title}</Text>
        <Text style={styles.compactDisclosureChevron}>{expanded ? '−' : '+'}</Text>
      </Pressable>
      {expanded ? (
        <View style={styles.compactDisclosureBody}>
          {items.map((item, index) => (
            <Text key={`${item}-${index}`} style={styles.helperText}>{item}</Text>
          ))}
        </View>
      ) : null}
    </View>
  );
}

function InstitutionsDashboardDetails({
  institutionalActivity,
  institutionalIntelligence,
}: {
  institutionalActivity: InstitutionalActivityResponse | null;
  institutionalIntelligence: InstitutionalIntelligenceResponse | null;
}) {
  const dashboard = buildInstitutionalDashboardViewModel(institutionalIntelligence, institutionalActivity);

  if (!dashboard) {
    return (
      <View style={styles.decisionPanel}>
        <Text style={styles.detailSectionTitle}>Institutional Overview</Text>
        <Text style={styles.bodyText}>Institutional activity is unavailable.</Text>
      </View>
    );
  }

  return (
    <View style={styles.sectionStack}>
      <InstitutionalOverviewCard dashboard={dashboard} />
      <InstitutionalBiasCard data={dashboard.bias} />
      <InstitutionalActivityChartCard followThroughDay={institutionalActivity?.bias?.follow_through_day ?? null} />
      <InstitutionalMoneyFlowCard data={dashboard.moneyFlow} />
      <InstitutionalLargePrintsCard data={dashboard.largePrints} />
      <OptionsPositioningCard data={dashboard.options} />
      <InstitutionalLiquidityCard data={dashboard.liquidity} />
      <AccumulationDistributionCard data={dashboard.accumulationDistribution} />
      <FollowThroughDayCard data={dashboard.followThroughDay} />
      <SmartMoneyTrendCard data={dashboard.trend} />
      <InstitutionalDataQualityCard data={dashboard.dataQuality} />
    </View>
  );
}

function InstitutionalOverviewCard({ dashboard }: { dashboard: InstitutionalDashboardViewModel }) {
  const { overview } = dashboard;
  return (
    <View style={styles.decisionHeroCard}>
      <View style={styles.decisionHeroHeader}>
        <View style={styles.decisionHeroTitleBlock}>
          <Text style={styles.biasLabel}>Institutional Overview</Text>
          <Text style={styles.decisionHeroTitle}>{overview.bias}</Text>
          <Text style={styles.helperInline}>{overview.subtitle}</Text>
        </View>
        <View style={styles.institutionalBadgeColumn}>
          <StatusBadge label={formatInstitutionalConfidence(overview.confidence)} tone={getInstitutionalConfidenceTone(overview.confidence)} />
          <StatusBadge label={formatInstitutionalSource(overview.source)} tone={getInstitutionalSourceTone(overview.source)} />
        </View>
      </View>
      <Text style={styles.biasSummary}>{overview.summary}</Text>
      <View style={styles.decisionMetricRow}>
        <MiniDecisionMetric label="Directional Bias" value={formatNullableNumber(overview.directionalBiasScore)} />
        <MiniDecisionMetric label="Signal Quality" value={formatInstitutionalConfidence(overview.confidence)} />
      </View>
      <View style={styles.healthComponentList}>
        {overview.supportMetrics.map((metric) => (
          <InstitutionalProgressMetric
            key={metric.label}
            label={metric.label}
            tone={metric.tone}
            value={metric.value}
          />
        ))}
      </View>
    </View>
  );
}

function InstitutionalBiasCard({ data }: { data: InstitutionalDashboardViewModel['bias'] }) {
  return (
    <View style={styles.decisionPanel}>
      <View style={styles.sectionHeaderRow}>
        <View>
          <Text style={styles.detailSectionTitle}>Institutional Bias</Text>
          <Text style={styles.helperInline}>{data.followThrough}</Text>
        </View>
        <StatusBadge label={data.bias} tone={getInstitutionalTone(data.tone)} />
      </View>
      <Text style={styles.bodyText}>{data.interpretation}</Text>
    </View>
  );
}

function InstitutionalMoneyFlowCard({ data }: { data: InstitutionalDashboardViewModel['moneyFlow'] }) {
  return (
    <View style={styles.decisionPanel}>
      <InstitutionalCardHeader
        source={data.sourceLabel}
        state={data.state}
        title="Money Flow"
        tone={data.tone}
      />
      <View style={styles.institutionalBarStack}>
        <InstitutionalBar label="Buying Pressure" tone="positive" value={data.buyingPressure} />
        <InstitutionalBar label="Selling Pressure" tone="negative" value={data.sellingPressure} />
      </View>
      <View style={styles.metricGrid}>
        <MetricTile label="Net Flow Proxy" value={formatSignedPoints(data.netFlow)} />
      </View>
      <Text style={styles.bodyText}>{data.interpretation}</Text>
    </View>
  );
}

function InstitutionalLargePrintsCard({ data }: { data: InstitutionalDashboardViewModel['largePrints'] }) {
  return (
    <View style={styles.decisionPanel}>
      <InstitutionalCardHeader
        source={data.sourceLabel}
        state={data.state}
        title="Large Prints"
        tone={data.tone}
      />
      {data.hasSignal ? (
        <View style={styles.institutionalBarStack}>
          <InstitutionalCountBar label="Bullish Candidates" tone="positive" value={data.bullish} max={Math.max(data.bullish ?? 0, data.bearish ?? 0, data.neutral ?? 0, 1)} />
          <InstitutionalCountBar label="Bearish Candidates" tone="negative" value={data.bearish} max={Math.max(data.bullish ?? 0, data.bearish ?? 0, data.neutral ?? 0, 1)} />
          <InstitutionalCountBar label="Neutral Candidates" tone="neutral" value={data.neutral} max={Math.max(data.bullish ?? 0, data.bearish ?? 0, data.neutral ?? 0, 1)} />
        </View>
      ) : null}
      <View style={styles.metricGrid}>
        <MetricTile label="Net Bias" value={formatSignedInteger(data.netBias)} />
      </View>
      <Text style={styles.bodyText}>{data.interpretation}</Text>
    </View>
  );
}

function OptionsPositioningCard({ data }: { data: InstitutionalDashboardViewModel['options'] }) {
  return (
    <View style={styles.decisionPanel}>
      <InstitutionalCardHeader
        source={data.sourceLabel}
        state={data.state}
        title="Options Positioning"
        tone={data.tone}
      />
      <View style={styles.institutionalBarStack}>
        <InstitutionalBar label="Call Activity" tone="positive" value={data.callActivity} />
        <InstitutionalBar label="Put Activity" tone="negative" value={data.putActivity} />
      </View>
      <View style={styles.metricGrid}>
        <MetricTile label="Put / Call" value={formatNullableNumber(data.putCallRatio)} />
        <MetricTile label="Tone" value={data.state} />
        <MetricTile label="Confidence" value={formatInstitutionalConfidence(data.confidence)} />
      </View>
      <Text style={styles.bodyText}>{data.interpretation}</Text>
    </View>
  );
}

function InstitutionalLiquidityCard({ data }: { data: InstitutionalDashboardViewModel['liquidity'] }) {
  return (
    <View style={styles.decisionPanel}>
      <InstitutionalCardHeader
        source={data.sourceLabel}
        state={data.state}
        title="Liquidity"
        tone={data.tone}
      />
      <InstitutionalProgressMetric label="Liquidity Score" tone={data.tone} value={data.score} />
      <View style={styles.decisionFieldGrid}>
        {data.rows.map((row) => (
          <DecisionField key={row.label} label={row.label} value={row.value} />
        ))}
      </View>
      <Text style={styles.bodyText}>{data.interpretation}</Text>
    </View>
  );
}

function AccumulationDistributionCard({ data }: { data: InstitutionalDashboardViewModel['accumulationDistribution'] }) {
  return (
    <View style={styles.decisionPanel}>
      <InstitutionalCardHeader
        source="Index activity"
        state={data.state}
        title="Accumulation vs Distribution"
        tone={data.tone}
      />
      <View style={styles.institutionalBarStack}>
        <InstitutionalCountBar label="Accumulation" tone="positive" value={data.accumulation} max={data.maxCount} />
        <InstitutionalCountBar label="Distribution" tone="negative" value={data.distribution} max={data.maxCount} />
        <InstitutionalCountBar label="Stall" tone="warning" value={data.stall} max={data.maxCount} secondary />
        <InstitutionalCountBar label="Churning" tone="warning" value={data.churning} max={data.maxCount} secondary />
      </View>
      <View style={styles.metricGrid}>
        <MetricTile label="Net Balance" value={formatSignedInteger(data.netBalance)} />
        <MetricTile label="State" value={data.state} />
      </View>
      <Text style={styles.bodyText}>{data.interpretation}</Text>
    </View>
  );
}

function FollowThroughDayCard({ data }: { data: InstitutionalDashboardViewModel['followThroughDay'] }) {
  return (
    <View style={styles.decisionPanel}>
      <InstitutionalCardHeader
        source="Index confirmation"
        state={data.state}
        title="Follow-Through Day"
        tone={data.tone}
      />
      <Text style={styles.institutionalEventLine}>{formatFollowThroughEvent(data.event)}</Text>
      <Text style={styles.bodyText}>{data.interpretation}</Text>
    </View>
  );
}

function SmartMoneyTrendCard({ data }: { data: InstitutionalDashboardViewModel['trend'] }) {
  return (
    <View style={styles.decisionPanel}>
      <View style={styles.sectionHeaderRow}>
        <View>
          <Text style={styles.detailSectionTitle}>Smart Money Trend</Text>
          <Text style={styles.helperInline}>Historical snapshot trend</Text>
        </View>
        <StatusBadge label={data.historyAvailable ? 'Available' : 'History unavailable'} tone={data.historyAvailable ? 'info' : 'muted'} />
      </View>
      <Text style={styles.bodyText}>{data.summary}</Text>
    </View>
  );
}

function InstitutionalDataQualityCard({ data }: { data: InstitutionalDashboardViewModel['dataQuality'] }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <View style={styles.decisionPanel}>
      <Pressable
        accessibilityLabel={`${expanded ? 'Hide' : 'Show'} data quality and limitations`}
        accessibilityRole="button"
        accessibilityState={{ expanded }}
        onPress={() => setExpanded((value) => !value)}
        style={({ pressed }) => [
          styles.institutionalDisclosureHeader,
          pressed && styles.marketTabPressed,
        ]}>
        <View style={styles.summaryTitleBlock}>
          <Text style={styles.detailSectionTitle}>Data Quality & Limitations</Text>
          <Text style={styles.helperInline}>
            {formatInstitutionalConfidence(data.confidence)} · {data.sourceLabel}
          </Text>
        </View>
        <Text style={styles.compactDisclosureChevron}>{expanded ? '−' : '+'}</Text>
      </Pressable>
      {expanded ? (
        <View style={styles.healthDriverList}>
          {data.limitations.map((limitation, index) => (
            <View key={`${limitation}-${index}`} style={styles.healthDriverRow}>
              <View style={[styles.healthDriverDot, styles.healthDriverDotWarning]} />
              <Text style={styles.healthDriverText}>{limitation}</Text>
            </View>
          ))}
        </View>
      ) : null}
    </View>
  );
}

function InstitutionalCardHeader({
  source,
  state,
  title,
  tone,
}: {
  source: string;
  state: string;
  title: string;
  tone: InstitutionalTone;
}) {
  return (
    <View style={styles.sectionHeaderRow}>
      <View style={styles.summaryTitleBlock}>
        <Text style={styles.detailSectionTitle}>{title}</Text>
        <Text style={styles.helperInline}>{source}</Text>
      </View>
      <StatusBadge label={state} tone={getInstitutionalTone(tone)} />
    </View>
  );
}

function InstitutionalProgressMetric({
  label,
  tone,
  value,
}: {
  label: string;
  tone: InstitutionalTone;
  value: number | null;
}) {
  if (value === null) {
    return (
      <View style={styles.healthComponentRow}>
        <Text style={styles.healthUnavailableText}>{label}: unavailable</Text>
      </View>
    );
  }
  return (
    <View style={styles.healthComponentRow}>
      <ProgressBar label={label} tone={getInstitutionalTone(tone)} value={value} />
    </View>
  );
}

function InstitutionalBar({
  label,
  tone,
  value,
}: {
  label: string;
  tone: InstitutionalTone;
  value: number | null;
}) {
  return (
    <View style={styles.institutionalBarRow}>
      <Text style={styles.institutionalBarLabel}>{label}</Text>
      <View style={styles.institutionalBarTrack}>
        {value !== null ? (
          <View
            style={[
              styles.institutionalBarFill,
              institutionalFillStyle(tone),
              { width: `${Math.max(3, Math.min(100, value))}%` },
            ]}
          />
        ) : null}
      </View>
      <Text style={styles.institutionalBarValue}>{formatNullablePercent(value)}</Text>
    </View>
  );
}

function InstitutionalCountBar({
  label,
  max,
  secondary = false,
  tone,
  value,
}: {
  label: string;
  max: number;
  secondary?: boolean;
  tone: InstitutionalTone;
  value: number | null;
}) {
  const width = value === null || max <= 0 ? 0 : Math.max(3, Math.min(100, (value / max) * 100));
  return (
    <View style={[styles.institutionalBarRow, secondary && styles.institutionalBarSecondary]}>
      <Text style={styles.institutionalBarLabel}>{label}</Text>
      <View style={styles.institutionalBarTrack}>
        {value !== null ? (
          <View
            style={[
              styles.institutionalBarFill,
              institutionalFillStyle(tone),
              secondary && styles.institutionalBarFillSecondary,
              { width: `${width}%` },
            ]}
          />
        ) : null}
      </View>
      <Text style={styles.institutionalBarValue}>{formatNullableNumber(value)}</Text>
    </View>
  );
}

function MarketHealthDetails({
  marketHealth,
}: {
  marketHealth: MarketHealthResponse | null;
}) {
  const components = buildHealthComponents(marketHealth);
  const radarData = buildHealthRadarData(marketHealth);
  const contributions = buildHealthContributions(components, marketHealth?.overall_score);
  const drivers = deriveHealthDrivers(components, marketHealth);
  const healthHistory: HealthSnapshot[] = [];
  const trendHistory: HealthTrendPoint[] = healthHistory.map((snapshot) => ({
    label: snapshot.timestamp,
    score: snapshot.score,
  }));
  const direction = classifyHealthDirection(trendHistory);

  if (!marketHealth) {
    return (
      <View style={styles.sectionStack}>
        <SectionTitle title="Health Overview" />
        <Text style={styles.bodyText}>Market health unavailable.</Text>
      </View>
    );
  }

  return (
    <View style={styles.sectionStack}>
      <HealthOverviewCard
        components={components}
        direction={direction}
        marketHealth={marketHealth}
      />
      <HealthBreakdownChart components={components} radarData={radarData} />
      <HealthComponentGrid components={components} />
      <HealthTrendCard
        direction={direction}
        history={healthHistory}
        score={marketHealth.overall_score}
      />
      <HealthDriversCard drivers={drivers} />
      <ScoreContributionCard contributions={contributions} total={Math.round(marketHealth.overall_score)} />
      <DecisionLayerCard components={components} marketHealth={marketHealth} />
    </View>
  );
}

function SectionTitle({ subtitle, title }: { subtitle?: string; title: string }) {
  return (
    <View style={styles.healthSectionHeader}>
      <Text style={styles.detailSectionTitle}>{title}</Text>
      {subtitle ? <Text style={styles.healthSectionSubtitle}>{subtitle}</Text> : null}
    </View>
  );
}

function HealthOverviewCard({
  components,
  direction,
  marketHealth,
}: {
  components: HealthComponentViewModel[];
  direction: HealthDirection;
  marketHealth: MarketHealthResponse;
}) {
  const confidence = marketHealth.decision_confidence;
  const dataMode = marketHealth.data_quality?.overall_mode;
  const sourceLabel = getHealthSourceBadgeLabel(dataMode);
  return (
    <View style={styles.healthDashboardSection}>
      <SectionTitle title="Health Overview" />
      <View style={styles.healthOverviewCard}>
        <View style={styles.healthOverviewTop}>
          <View style={styles.healthScoreBlock}>
            <Text style={styles.healthScoreValue}>{formatHealthScore(marketHealth.overall_score)}</Text>
            <Text style={styles.healthScoreCaption}>Market Health</Text>
          </View>
          <View style={styles.healthStatusStack}>
            <StatusBadge label={marketHealth.status} tone={getHealthTone(marketHealth.status)} />
            {direction === 'unavailable' ? (
              <StatusBadge label={getHealthHistoryBadgeLabel('unavailable')} tone="muted" />
            ) : (
              <StatusBadge label={formatHealthDirection(direction)} tone={getDirectionTone(direction)} />
            )}
            {sourceLabel ? <StatusBadge label={sourceLabel} tone={getSourceTone({ overall_mode: dataMode })} /> : null}
          </View>
        </View>
        <Text style={styles.healthOverviewSummary}>
          {buildHealthOverviewSummary(components, marketHealth)}
        </Text>
        <View style={styles.healthOverviewMeta}>
          <MiniDecisionMetric
            label="Decision confidence"
            value={confidence ? `${confidence.score} · ${confidence.status}` : 'Unavailable'}
          />
          <MiniDecisionMetric
            label="Component profile"
            value={summarizeComponentProfile(components)}
          />
        </View>
      </View>
    </View>
  );
}

function HealthBreakdownChart({
  components,
  radarData,
}: {
  components: HealthComponentViewModel[];
  radarData: HealthRadarDatum[];
}) {
  const validCount = radarData.filter((item) => item.score !== null).length;
  return (
    <View style={styles.healthDashboardSection}>
      <SectionTitle
        subtitle="0–100 component profile"
        title="Health Breakdown"
      />
      <View style={styles.healthRadarCard}>
        {validCount >= 3 ? (
          <HealthRadarChart data={radarData} />
        ) : (
          <View style={styles.healthRadarUnavailable}>
            <Text style={styles.healthUnavailableText}>Health breakdown unavailable.</Text>
          </View>
        )}
        <HealthScoreLegend components={components} radarData={radarData} />
      </View>
    </View>
  );
}

function HealthRadarChart({ data }: { data: HealthRadarDatum[] }) {
  const [width, setWidth] = useState(0);
  const validData = data.filter((item) => item.score !== null);
  const chartSize = width > 0 ? Math.min(width, 318) : 0;
  const center = chartSize / 2;
  const radius = chartSize * 0.27;
  const labelRadius = chartSize * 0.42;
  const radarPoints = chartSize > 0 ? calculateRadarPoints(data, center, center, radius) : [];
  const outerPoints = chartSize > 0
    ? calculateRadarGridPoints(validData.length, center, center, radius, 100)
    : [];
  const labelPoints = chartSize > 0
    ? calculateRadarGridPoints(validData.length, center, center, labelRadius, 100)
    : [];

  return (
    <View
      accessibilityLabel="Market health radar chart comparing momentum, breadth, trend, volume, institutions, volatility, and sectors."
      onLayout={(event) => setWidth(event.nativeEvent.layout.width)}
      style={styles.healthRadarFrame}>
      {chartSize > 0 ? (
        <View style={[styles.healthRadarCanvas, { height: chartSize, width: chartSize }]}>
          {[25, 50, 75, 100].map((ring) => {
            const ringPoints = calculateRadarGridPoints(validData.length, center, center, radius, ring);
            return (
              <RadarPolygon
                color={ring === 50 ? Theme.colors.border : Theme.colors.borderDark}
                key={ring}
                points={ringPoints}
                thickness={ring === 50 ? 1.5 : 1}
              />
            );
          })}
          {outerPoints.map((point, index) => (
            <RadarLineSegment
              color={Theme.colors.borderDark}
              key={`spoke-${index}`}
              opacity={0.72}
              start={{ x: center, y: center }}
              end={point}
            />
          ))}
          <RadarPolygon
            color={Theme.colors.accent}
            opacity={0.16}
            points={radarPoints}
            thickness={8}
          />
          <RadarPolygon
            color={Theme.colors.accent}
            points={radarPoints}
            thickness={2}
          />
          {radarPoints.map((point) => (
            <View
              key={`${point.key}-point`}
              style={[
                styles.healthRadarPoint,
                {
                  left: point.x - 4,
                  top: point.y - 4,
                },
              ]}
            />
          ))}
          {validData.map((item, index) => {
            const labelPoint = labelPoints[index];
            if (!labelPoint) {
              return null;
            }
            return (
              <Text
                key={`${item.key}-label`}
                numberOfLines={1}
                style={[
                  styles.healthRadarLabel,
                  {
                    left: Math.max(0, Math.min(chartSize - 92, labelPoint.x - 46)),
                    top: Math.max(0, Math.min(chartSize - 18, labelPoint.y - 9)),
                  },
                ]}>
                {item.label}
              </Text>
            );
          })}
          <Text style={[styles.healthRadarRingLabel, { left: center + 6, top: center - radius * 0.5 - 10 }]}>50</Text>
          <Text style={[styles.healthRadarRingLabel, { left: center + 6, top: center - radius * 0.75 - 10 }]}>75</Text>
          <Text style={[styles.healthRadarRingLabel, { left: center + 6, top: center - radius - 10 }]}>100</Text>
        </View>
      ) : null}
    </View>
  );
}

function RadarPolygon({
  color,
  opacity = 1,
  points,
  thickness = 1,
}: {
  color: string;
  opacity?: number;
  points: { x: number; y: number }[];
  thickness?: number;
}) {
  if (points.length < 2) {
    return null;
  }
  return (
    <>
      {points.map((point, index) => (
        <RadarLineSegment
          color={color}
          end={points[(index + 1) % points.length]}
          key={`${point.x}-${point.y}-${index}`}
          opacity={opacity}
          start={point}
          thickness={thickness}
        />
      ))}
    </>
  );
}

function RadarLineSegment({
  color,
  end,
  opacity = 1,
  start,
  thickness = 1,
}: {
  color: string;
  end: { x: number; y: number };
  opacity?: number;
  start: { x: number; y: number };
  thickness?: number;
}) {
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  const length = Math.sqrt(dx * dx + dy * dy);
  const angle = Math.atan2(dy, dx);
  const midX = (start.x + end.x) / 2;
  const midY = (start.y + end.y) / 2;
  if (!Number.isFinite(length) || length <= 0) {
    return null;
  }
  return (
    <View
      style={[
        styles.healthRadarLine,
        {
          backgroundColor: color,
          height: thickness,
          left: midX - length / 2,
          opacity,
          top: midY - thickness / 2,
          transform: [{ rotateZ: `${angle}rad` }],
          width: length,
        },
      ]}
    />
  );
}

function HealthScoreLegend({
  components,
  radarData,
}: {
  components: HealthComponentViewModel[];
  radarData: HealthRadarDatum[];
}) {
  const byKey = new Map(components.map((component) => [component.key, component]));
  return (
    <View style={styles.healthRadarLegend}>
      {radarData.map((item) => {
        const component = byKey.get(item.key);
        const tone = component?.tone ?? 'unavailable';
        return (
          <View key={item.key} style={styles.healthRadarLegendItem}>
            <View style={[styles.healthRadarLegendDot, healthToneFillStyle(tone)]} />
            <Text style={styles.healthRadarLegendLabel}>{item.label}</Text>
            <Text style={styles.healthRadarLegendScore}>{formatHealthScore(item.score)}</Text>
          </View>
        );
      })}
    </View>
  );
}

function HealthComponentGrid({ components }: { components: HealthComponentViewModel[] }) {
  return (
    <View style={styles.healthDashboardSection}>
      <SectionTitle
        subtitle="What each score means"
        title="Component Scores"
      />
      <View style={styles.healthComponentGrid}>
        {components.map((component) => (
          <HealthComponentScoreCard component={component} key={component.key} />
        ))}
      </View>
    </View>
  );
}

function HealthComponentScoreCard({ component }: { component: HealthComponentViewModel }) {
  const [expanded, setExpanded] = useState(false);
  const details = buildComponentRationaleDetails(component);
  return (
    <View style={styles.healthComponentCard}>
      <View style={styles.healthComponentCardHeader}>
        <Text style={styles.healthComponentName}>{component.label}</Text>
        <HealthScorePill score={component.score} tone={component.tone} />
      </View>
      <Text style={styles.healthComponentStatus}>{component.status}</Text>
      <Text style={styles.healthComponentMeaning}>{component.explanation}</Text>
      {details.length ? (
        <View style={styles.healthDisclosure}>
          <Pressable
            accessibilityRole="button"
            accessibilityState={{ expanded }}
            onPress={() => setExpanded((value) => !value)}
            style={({ pressed }) => [
              styles.healthDisclosureButton,
              pressed && styles.marketTabPressed,
            ]}>
            <Text style={styles.healthDisclosureText}>Why this score?</Text>
            <Text style={styles.healthDisclosureIcon}>{expanded ? '−' : '+'}</Text>
          </Pressable>
          {expanded ? (
            <View style={styles.healthDisclosureBody}>
              {details.map((detail) => (
                <Text key={detail} style={styles.healthComponentRationale}>{detail}</Text>
              ))}
            </View>
          ) : null}
        </View>
      ) : null}
    </View>
  );
}

function HealthTrendCard({
  direction,
  history,
  score,
}: {
  direction: HealthDirection;
  history: HealthSnapshot[];
  score: number;
}) {
  const supportedRanges = getSupportedHealthTrendRanges(history);
  return (
    <View style={styles.healthDashboardSection}>
      <SectionTitle
        subtitle="Composite score over time"
        title="Health Trend"
      />
      <View style={styles.healthTrendCard}>
        {supportedRanges.length ? (
          <>
            <View style={styles.healthTrendCompactRow}>
              <MiniDecisionMetric label="Current score" value={formatHealthScore(score)} />
              <StatusBadge label={formatHealthDirection(direction)} tone={getDirectionTone(direction)} />
            </View>
            <Text style={styles.healthOverviewSummary}>
              Comparable market health snapshots are available for {supportedRanges.join(', ')}.
            </Text>
          </>
        ) : (
          <>
            <View style={styles.healthTrendCompactRow}>
              <MiniDecisionMetric label="Current score" value={formatHealthScore(score)} />
              <StatusBadge label={getHealthHistoryBadgeLabel('unavailable')} tone="muted" />
            </View>
            <Text style={styles.healthUnavailableText}>
              Historical trend will appear when comparable market-health snapshots are available.
            </Text>
          </>
        )}
      </View>
    </View>
  );
}

function HealthDriversCard({
  drivers,
}: {
  drivers: ReturnType<typeof deriveHealthDrivers>;
}) {
  return (
    <View style={styles.healthDashboardSection}>
      <SectionTitle title="Key Drivers" />
      <View style={styles.healthDriverColumns}>
        <View style={styles.healthDriverPanel}>
          <Text style={styles.healthDriverTitle}>Supporting Factors</Text>
          <HealthDriverList drivers={drivers.supporting} fallback="No dominant supporting factor detected." />
        </View>
        <View style={styles.healthDriverPanel}>
          <Text style={styles.healthDriverTitle}>Risks to Monitor</Text>
          <HealthDriverList drivers={drivers.monitor} fallback="No material risk signal detected." />
        </View>
      </View>
    </View>
  );
}

function HealthDriverList({
  drivers,
  fallback,
}: {
  drivers: HealthDriver[];
  fallback: string;
}) {
  if (!drivers.length) {
    return <Text style={styles.healthUnavailableText}>{fallback}</Text>;
  }
  return (
    <View style={styles.healthDriverList}>
      {drivers.map((driver, index) => (
        <View key={`${driver.label}-${index}`} style={styles.healthDriverRow}>
          <View style={[styles.healthDriverDot, healthDriverDotStyle(driver.tone)]} />
          <Text style={styles.healthDriverText}>{driver.label}</Text>
        </View>
      ))}
    </View>
  );
}

function ScoreContributionCard({
  contributions,
  total,
}: {
  contributions: HealthContributionViewModel[];
  total: number;
}) {
  const [expanded, setExpanded] = useState(false);
  return (
    <View style={styles.healthDashboardSection}>
      <SectionTitle
        subtitle="Weighted v1 composite"
        title="Score Contribution"
      />
      <View style={styles.healthContributionCard}>
        <View style={styles.healthContributionTotalRow}>
          <Text style={styles.healthContributionTotalLabel}>Composite estimate</Text>
          <Text style={styles.healthContributionTotalValue}>{total}</Text>
        </View>
        {contributions.map((component) => (
          <View key={component.component} style={styles.healthContributionRow}>
            <View style={styles.healthContributionHeader}>
              <Text style={styles.healthContributionName}>{component.label}</Text>
              <Text style={styles.healthContributionValue}>
                +{component.displayedPoints} pts
              </Text>
            </View>
            <View style={styles.healthContributionTrack}>
              <View
                style={[
                  styles.healthContributionFill,
                  healthToneFillStyle(classifyHealthScore(component.score).tone),
                  { width: `${Math.max(4, Math.min(100, (component.rawContribution / 20) * 100))}%` },
                ]}
              />
            </View>
          </View>
        ))}
        <View style={styles.healthDisclosure}>
          <Pressable
            accessibilityRole="button"
            accessibilityState={{ expanded }}
            onPress={() => setExpanded((value) => !value)}
            style={({ pressed }) => [
              styles.healthDisclosureButton,
              pressed && styles.marketTabPressed,
            ]}>
            <Text style={styles.healthDisclosureText}>How this score works</Text>
            <Text style={styles.healthDisclosureIcon}>{expanded ? '−' : '+'}</Text>
          </Pressable>
          {expanded ? (
            <View style={styles.healthDisclosureBody}>
              {contributions.map((component) => (
                <Text key={`${component.component}-math`} style={styles.healthComponentRationale}>
                  {component.label}: score {Math.round(component.score)} × weight {Math.round(component.weight * 100)}% = {component.rawContribution.toFixed(1)} pts
                </Text>
              ))}
              <Text style={styles.healthComponentRationale}>
                Displayed points are rounded with largest remainders first so they sum to the composite estimate.
              </Text>
            </View>
          ) : null}
        </View>
      </View>
    </View>
  );
}

function DecisionLayerCard({
  components,
  marketHealth,
}: {
  components: HealthComponentViewModel[];
  marketHealth: MarketHealthResponse;
}) {
  const summary = buildDecisionLayerSummary(marketHealth.decision_confidence, components, marketHealth);
  return (
    <View style={styles.healthDashboardSection}>
      <SectionTitle title="Decision Layer" />
      <View style={styles.healthDecisionCard}>
        <View style={styles.healthDecisionHeader}>
          <View>
            <Text style={styles.healthDecisionLabel}>Market posture</Text>
            <Text style={styles.healthDecisionStance}>{summary.stance}</Text>
          </View>
          {marketHealth.decision_confidence ? (
            <HealthScorePill
              score={marketHealth.decision_confidence.score}
              tone={classifyHealthScore(marketHealth.decision_confidence.score).tone}
            />
          ) : null}
        </View>
        <Text style={styles.healthOverviewSummary}>{summary.implication}</Text>
        <View style={styles.healthOverviewMeta}>
          <MiniDecisionMetric label="Supports" value={summary.supports} />
          <MiniDecisionMetric label="Monitor" value={summary.monitor} />
        </View>
      </View>
    </View>
  );
}

function HealthScorePill({
  score,
  tone,
}: {
  score: number | null;
  tone: HealthScoreTone;
}) {
  return (
    <View style={[styles.healthScorePill, healthTonePillStyle(tone)]}>
      <Text style={[styles.healthScorePillText, healthToneTextStyle(tone)]}>
        {formatHealthScore(score)}
      </Text>
    </View>
  );
}

function MiniDecisionMetric({ label, value }: { label: string; value: string | number }) {
  return (
    <View style={styles.healthMiniMetric}>
      <Text style={styles.healthMiniMetricLabel}>{label}</Text>
      <Text style={styles.healthMiniMetricValue}>{value}</Text>
    </View>
  );
}

function summarizeComponentProfile(components: HealthComponentViewModel[]) {
  const strongCount = components.filter((component) => (component.score ?? 0) >= 75).length;
  const weakCount = components.filter((component) => (component.score ?? 100) < 60).length;
  if (strongCount && weakCount) {
    return `${strongCount} strong · ${weakCount} watch`;
  }
  if (strongCount) {
    return `${strongCount} strong components`;
  }
  return 'Mixed component profile';
}

function buildComponentRationaleDetails(component: HealthComponentViewModel) {
  const details = new Set<string>();
  const rawFacts = (component.rawExplanation ?? '')
    .replace(/50EMA/g, '50 EMA')
    .replace(/20EMA/g, '20 EMA')
    .replace(/200EMA/g, '200 EMA')
    .split(/\.\s+|;\s+|\sand\s/i)
    .map((part) => part.trim().replace(/[.]+$/, ''))
    .filter((part) => part.length > 3 && part.toLowerCase() !== component.explanation.toLowerCase());

  rawFacts.slice(0, 3).forEach((fact) => details.add(fact));
  if (component.contribution !== null && Number.isFinite(component.contribution)) {
    details.add(`Contribution: ${component.contribution.toFixed(1)} pts`);
  }
  details.add(`Weight: ${Math.round(component.weight * 100)}%`);
  return Array.from(details).filter((detail) => !/undefined|null|nan/i.test(detail));
}

function getDirectionTone(direction: HealthDirection): Tone {
  switch (direction) {
    case 'improving':
      return 'success';
    case 'stable':
      return 'info';
    case 'weakening':
      return 'warning';
    default:
      return 'muted';
  }
}

function healthToneFillStyle(tone: HealthScoreTone) {
  switch (tone) {
    case 'excellent':
    case 'strong':
      return styles.healthFillStrong;
    case 'constructive':
      return styles.healthFillConstructive;
    case 'mixed':
      return styles.healthFillMixed;
    case 'weak':
      return styles.healthFillWeak;
    default:
      return styles.healthFillUnavailable;
  }
}

function healthTonePillStyle(tone: HealthScoreTone) {
  switch (tone) {
    case 'excellent':
    case 'strong':
      return styles.healthPillStrong;
    case 'constructive':
      return styles.healthPillConstructive;
    case 'mixed':
      return styles.healthPillMixed;
    case 'weak':
      return styles.healthPillWeak;
    default:
      return styles.healthPillUnavailable;
  }
}

function healthToneTextStyle(tone: HealthScoreTone) {
  switch (tone) {
    case 'excellent':
    case 'strong':
      return styles.healthTextStrong;
    case 'constructive':
      return styles.healthTextConstructive;
    case 'mixed':
      return styles.healthTextMixed;
    case 'weak':
      return styles.healthTextWeak;
    default:
      return styles.healthTextUnavailable;
  }
}

function healthDriverDotStyle(tone: HealthDriver['tone']) {
  switch (tone) {
    case 'supportive':
      return styles.healthDriverDotSupportive;
    case 'negative':
      return styles.healthDriverDotNegative;
    case 'warning':
      return styles.healthDriverDotWarning;
    default:
      return styles.healthDriverDotNeutral;
  }
}

function getHealthTone(status?: string): Tone {
  switch (status) {
    case 'Very Healthy':
    case 'Healthy':
      return 'success';
    case 'Mixed':
      return 'warning';
    case 'Weak':
    case 'Risk-Off':
      return 'danger';
    default:
      return 'muted';
  }
}

function getScoreTone(score: number): Tone {
  if (score >= 85) {
    return 'success';
  }
  if (score >= 70) {
    return 'info';
  }
  if (score >= 55) {
    return 'warning';
  }
  return 'danger';
}

function getBreadthTone(tone: BreadthSignalTone): Tone {
  switch (tone) {
    case 'positive':
      return 'success';
    case 'warning':
      return 'warning';
    case 'negative':
      return 'danger';
    default:
      return 'muted';
  }
}

function getDecisionTone(tone: DecisionTone): Tone {
  switch (tone) {
    case 'positive':
      return 'success';
    case 'warning':
      return 'warning';
    case 'negative':
      return 'danger';
    default:
      return 'muted';
  }
}

function getInstitutionalTone(tone: InstitutionalTone): Tone {
  switch (tone) {
    case 'positive':
      return 'success';
    case 'warning':
      return 'warning';
    case 'negative':
      return 'danger';
    default:
      return 'muted';
  }
}

function getInstitutionalConfidenceTone(confidence: InstitutionalDashboardViewModel['overview']['confidence']): Tone {
  switch (confidence) {
    case 'high':
      return 'success';
    case 'moderate':
      return 'warning';
    case 'low':
      return 'danger';
    default:
      return 'muted';
  }
}

function getInstitutionalSourceTone(source: InstitutionalDashboardViewModel['overview']['source']): Tone {
  switch (source) {
    case 'live':
      return 'success';
    case 'cached':
    case 'mixed':
      return 'info';
    case 'mock':
    case 'proxy':
    case 'fallback':
      return 'warning';
    default:
      return 'muted';
  }
}

function institutionalFillStyle(tone: InstitutionalTone) {
  switch (tone) {
    case 'positive':
      return styles.healthFillStrong;
    case 'warning':
      return styles.healthFillMixed;
    case 'negative':
      return styles.healthFillWeak;
    default:
      return styles.healthFillUnavailable;
  }
}

function formatInstitutionalConfidence(confidence: InstitutionalDashboardViewModel['overview']['confidence']) {
  switch (confidence) {
    case 'high':
      return 'High Confidence';
    case 'moderate':
      return 'Moderate Confidence';
    case 'low':
      return 'Low Confidence';
    default:
      return 'Unavailable';
  }
}

function formatInstitutionalSource(source: InstitutionalDashboardViewModel['overview']['source']) {
  switch (source) {
    case 'live':
      return 'Live';
    case 'cached':
      return 'Cached';
    case 'mock':
      return 'Mock Data';
    case 'proxy':
      return 'Proxy';
    case 'fallback':
      return 'Fallback';
    case 'mixed':
      return 'Mixed Sources';
    default:
      return 'Unavailable';
  }
}

function getConcentrationTone(state: string): Tone {
  switch (state) {
    case 'broad_participation':
    case 'equal_weight_leadership':
      return 'success';
    case 'mild_concentration':
    case 'mixed':
      return 'warning';
    case 'mega_cap_concentration':
      return 'purple';
    default:
      return 'muted';
  }
}

function getBreadthConfidenceTone(confidence: 'high' | 'moderate' | 'low' | 'unavailable'): Tone {
  switch (confidence) {
    case 'high':
      return 'success';
    case 'moderate':
      return 'warning';
    case 'low':
      return 'danger';
    default:
      return 'muted';
  }
}

function toneForNumericScore(score: number): BreadthSignalTone {
  if (score >= 75) {
    return 'positive';
  }
  if (score >= 60) {
    return 'warning';
  }
  if (score >= 45) {
    return 'neutral';
  }
  return 'negative';
}

function getRiskLabelTone(label: string): BreadthSignalTone {
  const normalized = label.toLowerCase();
  if (normalized.includes('elevated') || normalized.includes('high')) {
    return 'warning';
  }
  if (normalized.includes('low') || normalized.includes('stable')) {
    return 'positive';
  }
  return 'neutral';
}

function breadthFillStyle(tone: BreadthSignalTone) {
  switch (tone) {
    case 'positive':
      return styles.healthFillStrong;
    case 'warning':
      return styles.healthFillMixed;
    case 'negative':
      return styles.healthFillWeak;
    default:
      return styles.healthFillUnavailable;
  }
}

function getChecklistTone(grade?: string): Tone {
  switch (grade) {
    case 'Healthy':
      return 'success';
    case 'Mixed':
      return 'warning';
    case 'Weak':
    case 'Risk-Off':
      return 'danger';
    default:
      return 'muted';
  }
}

function MetricTile({ label, subvalue, value }: { label: string; subvalue?: string; value: string | number }) {
  return (
    <View style={styles.metricTile}>
      <Text style={styles.metricLabel}>{label}</Text>
      <Text style={styles.metricValue}>{value}</Text>
      {subvalue ? <Text style={styles.metricSubvalue}>{subvalue}</Text> : null}
    </View>
  );
}

function formatPrice(value: number) {
  return value.toLocaleString('en-US', {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  });
}

function formatSignedInteger(value: number | null | undefined) {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return 'N/A';
  }
  if (value > 0) {
    return `+${Math.round(value)}`;
  }
  return String(Math.round(value));
}

function formatCoverageCounts(tracked: number | null, expected: number | null) {
  const trackedLabel = formatNullableNumber(tracked);
  if (expected !== null && expected !== undefined && Number.isFinite(expected) && expected > 0) {
    return `${trackedLabel} of approximately ${formatNullableNumber(expected)} expected stocks`;
  }
  return `${trackedLabel} stocks tracked`;
}

function formatNullableNumber(value: number | null | undefined) {
  if (value === Number.POSITIVE_INFINITY) {
    return '∞';
  }
  return value === null || value === undefined
    ? 'N/A'
    : value.toLocaleString('en-US', {
        maximumFractionDigits: 2,
        minimumFractionDigits: 1,
      });
}

function formatNullablePercent(value: number | null | undefined) {
  return value === null || value === undefined ? 'N/A' : `${formatNullableNumber(value)}%`;
}

function formatNullableSignedPercent(value: number | null | undefined) {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return 'N/A';
  }
  return formatSignedPercent(value);
}

function formatFollowThroughEvent(event: InstitutionalDashboardViewModel['followThroughDay']['event']) {
  if (!event) {
    return 'Follow-through data unavailable';
  }
  if (!event.triggered) {
    return 'No recent follow-through day';
  }
  return [
    event.index ?? 'Index',
    event.date ?? null,
    event.gain_percent !== null && event.gain_percent !== undefined ? formatSignedPercent(event.gain_percent) : null,
  ].filter(Boolean).join(' · ');
}

function formatSignedPoints(value: number | null | undefined) {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return 'N/A';
  }
  const formatted = Math.abs(value).toLocaleString('en-US', {
    maximumFractionDigits: 1,
    minimumFractionDigits: 1,
  });
  return `${value >= 0 ? '+' : '-'}${formatted} pts`;
}

function formatSignedPercent(value: number) {
  const formatted = Math.abs(value).toLocaleString('en-US', {
    maximumFractionDigits: 2,
    minimumFractionDigits: 1,
  });
  return `${value >= 0 ? '+' : '-'}${formatted}%`;
}

function formatSigned(value: number) {
  const formatted = Math.abs(value).toLocaleString('en-US', {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  });
  return `${value >= 0 ? '+' : '-'}${formatted}`;
}

function formatCompactVolume(value?: number | null) {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return 'N/A';
  }

  if (value >= 1_000_000_000) {
    return `${(value / 1_000_000_000).toFixed(1)}B`;
  }

  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)}M`;
  }

  if (value >= 1_000) {
    return `${(value / 1_000).toFixed(1)}K`;
  }

  return value.toLocaleString('en-US');
}

function capitalize(value: string) {
  if (!value) {
    return 'N/A';
  }

  return `${value.charAt(0).toUpperCase()}${value.slice(1)}`;
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: Theme.colors.background,
    flex: 1,
  },
  content: {
    gap: Spacing.three,
    padding: Spacing.three,
    paddingBottom: Spacing.six,
  },
  header: {
    gap: Spacing.one,
    paddingTop: Spacing.two,
  },
  title: {
    color: Theme.colors.textInverse,
    fontSize: 29,
    fontWeight: '900',
  },
  subtitle: {
    color: Theme.colors.textInverseMuted,
    fontSize: 15,
    lineHeight: 22,
  },
  helperText: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    lineHeight: 18,
    marginTop: Spacing.two,
  },
  helperInline: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '800',
  },
  warningInline: {
    color: Theme.colors.warning,
    fontSize: 11,
    fontWeight: '800',
  },
  marketTabs: {
    gap: Spacing.one,
    paddingLeft: Spacing.one,
    paddingRight: Spacing.six,
  },
  marketTab: {
    alignItems: 'center',
    backgroundColor: 'transparent',
    borderColor: 'transparent',
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    flexDirection: 'row',
    gap: Spacing.one,
    minHeight: 40,
    paddingHorizontal: Spacing.two,
    paddingVertical: Spacing.two,
  },
  marketTabActive: {
    backgroundColor: Theme.colors.accentSoft,
    borderColor: Theme.colors.accent,
  },
  marketTabPressed: {
    opacity: 0.78,
  },
  marketTabText: {
    color: Theme.colors.textMuted,
    fontSize: 13,
    fontWeight: '900',
  },
  marketTabTextActive: {
    color: Theme.colors.accent,
  },
  compactTimeframeRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.one,
  },
  compactTimeframeButton: {
    alignItems: 'center',
    backgroundColor: Theme.colors.card,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    flex: 1,
    justifyContent: 'center',
    minHeight: 34,
    paddingHorizontal: Spacing.two,
    paddingVertical: Spacing.one,
  },
  compactTimeframeButtonActive: {
    backgroundColor: Theme.colors.accentSoft,
    borderColor: Theme.colors.accent,
  },
  compactTimeframeText: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '900',
  },
  compactTimeframeTextActive: {
    color: Theme.colors.accent,
  },
  regimeHero: {
    backgroundColor: Theme.colors.card,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.card,
    borderWidth: 1,
    gap: Spacing.twoAndHalf,
    padding: Spacing.three,
  },
  regimeHeader: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  regimeTitleBlock: {
    flex: 1,
    gap: Spacing.half,
  },
  heroKicker: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '900',
    textTransform: 'uppercase',
  },
  regimeTitle: {
    color: Theme.colors.text,
    fontSize: 30,
    fontWeight: '900',
    lineHeight: 34,
  },
  regimeScore: {
    color: Theme.colors.textMuted,
    fontSize: 13,
    fontWeight: '900',
  },
  regimeExplanation: {
    color: Theme.colors.textMuted,
    fontSize: 14,
    fontWeight: '700',
    lineHeight: 21,
  },
  insightCard: {
    backgroundColor: Theme.colors.card,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.card,
    borderWidth: 1,
    gap: Spacing.two,
    padding: Spacing.three,
  },
  insightHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  sectionTitle: {
    color: Theme.colors.text,
    fontSize: 15,
    fontWeight: '900',
  },
  insightHeadline: {
    color: Theme.colors.text,
    fontSize: 17,
    fontWeight: '900',
    lineHeight: 22,
  },
  insightSummary: {
    color: Theme.colors.textMuted,
    fontSize: 14,
    fontWeight: '700',
    lineHeight: 21,
  },
  insightFooter: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  insightMeta: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '800',
  },
  signalCard: {
    backgroundColor: Theme.colors.card,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.card,
    borderWidth: 1,
    gap: Spacing.one,
    padding: Spacing.three,
  },
  keySignalList: {
    gap: Spacing.one,
  },
  keySignalRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.one,
  },
  keySignalDot: {
    borderRadius: 5,
    height: 10,
    width: 10,
  },
  keySignalText: {
    color: Theme.colors.text,
    flex: 1,
    fontSize: 13,
    fontWeight: '800',
    lineHeight: 18,
  },
  overviewSnapshotGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  overviewSnapshotTile: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    flexBasis: '47%',
    flexGrow: 1,
    gap: Spacing.one,
    minWidth: 145,
    padding: Spacing.twoAndHalf,
  },
  overviewSnapshotHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.one,
    justifyContent: 'space-between',
  },
  overviewAlignmentRow: {
    gap: Spacing.one,
  },
  overviewChipRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.one,
  },
  overviewChip: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    paddingHorizontal: Spacing.two,
    paddingVertical: Spacing.one,
  },
  overviewChipText: {
    fontSize: 11,
    fontWeight: '900',
  },
  statusCard: {
    backgroundColor: Theme.colors.cardElevated,
    borderColor: Theme.colors.borderDark,
  },
  statusHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  eyebrow: {
    color: Theme.colors.textInverseMuted,
    fontSize: 12,
    fontWeight: '800',
    letterSpacing: 0,
    textTransform: 'uppercase',
  },
  statusDot: {
    backgroundColor: Theme.colors.success,
    borderRadius: 6,
    height: 12,
    width: 12,
  },
  statusText: {
    color: Theme.colors.textInverse,
    fontSize: 30,
    fontWeight: '900',
    marginTop: Spacing.three,
  },
  errorTextInverse: {
    color: '#FECACA',
    fontSize: 14,
    lineHeight: 20,
    marginTop: Spacing.two,
  },
  metricGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  summaryGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  summaryProgress: {
    marginTop: Spacing.three,
  },
  skeletonStack: {
    gap: Spacing.three,
  },
  metricTile: {
    backgroundColor: Theme.colors.cardMuted,
    borderRadius: Theme.radii.small,
    flexGrow: 1,
    minWidth: '47%',
    padding: Spacing.twoAndHalf,
  },
  economicMetricTile: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: StyleSheet.hairlineWidth,
    flexBasis: '47%',
    flexGrow: 1,
    gap: Spacing.one,
    minWidth: 155,
    padding: Spacing.twoAndHalf,
  },
  economicMetricHeader: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: Spacing.one,
    justifyContent: 'space-between',
  },
  economicBadgeRow: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    maxWidth: '100%',
  },
  economicActualLabel: {
    color: Theme.colors.textMuted,
    fontSize: 10,
    fontWeight: '900',
    textTransform: 'uppercase',
  },
  economicActualValue: {
    color: Theme.colors.text,
    fontSize: 25,
    fontWeight: '900',
    lineHeight: 30,
  },
  economicFieldRow: {
    flexDirection: 'row',
    gap: Spacing.two,
  },
  economicField: {
    flex: 1,
    minWidth: 0,
  },
  economicFieldLabel: {
    color: Theme.colors.textMuted,
    fontSize: 10,
    fontWeight: '900',
    textTransform: 'uppercase',
  },
  economicFieldValue: {
    color: Theme.colors.text,
    fontSize: 13,
    fontWeight: '900',
  },
  economicRevisionText: {
    color: Theme.colors.textMuted,
    fontSize: 10,
    fontWeight: '700',
  },
  economicSurpriseRow: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  economicSurpriseValue: {
    color: Theme.colors.text,
    fontSize: 13,
    fontWeight: '900',
  },
  economicConsensusText: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '800',
  },
  economicComment: {
    fontSize: 12,
    fontWeight: '900',
  },
  economicReleaseDate: {
    color: Theme.colors.textMuted,
    fontSize: 10,
    fontWeight: '800',
  },
  metricLabel: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '800',
    marginBottom: Spacing.one,
    textTransform: 'uppercase',
  },
  metricValue: {
    color: Theme.colors.text,
    fontSize: 17,
    fontWeight: '900',
  },
  metricSubvalue: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    lineHeight: 16,
    marginTop: Spacing.one,
  },
  decisionHeroCard: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.accent,
    borderRadius: Theme.radii.card,
    borderWidth: StyleSheet.hairlineWidth,
    gap: Spacing.three,
    padding: Spacing.three,
  },
  decisionHeroHeader: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  decisionHeroTitleBlock: {
    flex: 1,
    minWidth: 0,
  },
  decisionHeroTitle: {
    color: Theme.colors.text,
    fontSize: 24,
    fontWeight: '900',
    letterSpacing: 0,
  },
  decisionMetricRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  decisionFieldGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  decisionField: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: StyleSheet.hairlineWidth,
    flexBasis: '47%',
    flexGrow: 1,
    gap: Spacing.one,
    minWidth: 140,
    padding: Spacing.twoAndHalf,
  },
  decisionFieldValue: {
    color: Theme.colors.text,
    fontSize: 13,
    fontWeight: '800',
    lineHeight: 18,
  },
  decisionChipsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  decisionChip: {
    backgroundColor: Theme.colors.accentSoft,
    borderColor: Theme.colors.accent,
    borderRadius: Theme.radii.pill,
    borderWidth: StyleSheet.hairlineWidth,
    paddingHorizontal: Spacing.two,
    paddingVertical: Spacing.one,
  },
  decisionChipText: {
    color: Theme.colors.accent,
    fontSize: 11,
    fontWeight: '900',
  },
  decisionPanel: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    gap: Spacing.twoAndHalf,
    padding: Spacing.twoAndHalf,
  },
  institutionalBadgeColumn: {
    alignItems: 'flex-end',
    flexShrink: 0,
    gap: Spacing.one,
  },
  institutionalBarStack: {
    gap: Spacing.two,
  },
  institutionalBarRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
  },
  institutionalBarSecondary: {
    opacity: 0.72,
  },
  institutionalBarLabel: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '900',
    width: 104,
  },
  institutionalBarTrack: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderRadius: Theme.radii.pill,
    flex: 1,
    height: 10,
    overflow: 'hidden',
  },
  institutionalBarFill: {
    borderRadius: Theme.radii.pill,
    height: '100%',
  },
  institutionalBarFillSecondary: {
    opacity: 0.72,
  },
  institutionalBarValue: {
    color: Theme.colors.text,
    fontSize: 12,
    fontWeight: '900',
    textAlign: 'right',
    width: 56,
  },
  institutionalDisclosureHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
    minHeight: 44,
  },
  institutionalEventLine: {
    color: Theme.colors.text,
    fontSize: 15,
    fontWeight: '900',
    lineHeight: 21,
  },
  decisionList: {
    gap: Spacing.two,
  },
  decisionSetupRow: {
    alignItems: 'center',
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: StyleSheet.hairlineWidth,
    flexDirection: 'row',
    gap: Spacing.two,
    minHeight: 54,
    padding: Spacing.two,
  },
  decisionRank: {
    color: Theme.colors.textMuted,
    fontSize: 13,
    fontWeight: '900',
    width: 20,
  },
  decisionSetupBody: {
    flex: 1,
    minWidth: 0,
  },
  decisionChecklistGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  checklistSummaryRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  decisionChecklistItem: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: StyleSheet.hairlineWidth,
    flexBasis: '47%',
    flexGrow: 1,
    gap: Spacing.two,
    minWidth: 145,
    padding: Spacing.two,
  },
  decisionChecklistLabel: {
    color: Theme.colors.text,
    fontSize: 12,
    fontWeight: '900',
  },
  decisionInvalidationBox: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: StyleSheet.hairlineWidth,
    gap: Spacing.one,
    padding: Spacing.twoAndHalf,
  },
  decisionGaugeScore: {
    color: Theme.colors.text,
    fontSize: 30,
    fontWeight: '900',
  },
  fearGreedGaugeTrack: {
    borderRadius: Theme.radii.pill,
    flexDirection: 'row',
    height: 14,
    overflow: 'hidden',
    position: 'relative',
  },
  fearGreedGaugeZone: {
    height: '100%',
  },
  fearGreedGaugeMarker: {
    backgroundColor: Theme.colors.text,
    borderRadius: 5,
    height: 22,
    marginLeft: -2,
    position: 'absolute',
    top: -4,
    width: 4,
  },
  fearGreedLabels: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  weightPairSelector: {
    flexDirection: 'row',
    gap: Spacing.two,
  },
  weightPairButton: {
    alignItems: 'center',
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.pill,
    borderWidth: StyleSheet.hairlineWidth,
    flex: 1,
    minHeight: 34,
    justifyContent: 'center',
    paddingHorizontal: Spacing.two,
  },
  weightPairButtonActive: {
    backgroundColor: Theme.colors.accentSoft,
    borderColor: Theme.colors.accent,
  },
  weightPairText: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '900',
  },
  weightPairTextActive: {
    color: Theme.colors.accent,
  },
  weightChartBox: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    overflow: 'hidden',
    position: 'relative',
  },
  weightSummaryGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  weightSummaryTile: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: StyleSheet.hairlineWidth,
    flexBasis: '47%',
    flexGrow: 1,
    gap: Spacing.one,
    minWidth: 128,
    padding: Spacing.twoAndHalf,
  },
  weightSummaryValue: {
    color: Theme.colors.text,
    fontSize: 16,
    fontWeight: '900',
  },
  decisionChangeGrid: {
    gap: Spacing.two,
  },
  decisionChangeGroup: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: StyleSheet.hairlineWidth,
    gap: Spacing.two,
    padding: Spacing.two,
  },
  compactDisclosure: {
    borderTopColor: Theme.colors.border,
    borderTopWidth: StyleSheet.hairlineWidth,
    gap: Spacing.two,
    paddingTop: Spacing.two,
  },
  compactDisclosureButton: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
    minHeight: 34,
  },
  compactDisclosureTitle: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '900',
  },
  compactDisclosureChevron: {
    color: Theme.colors.textMuted,
    fontSize: 18,
    fontWeight: '900',
  },
  compactDisclosureBody: {
    gap: Spacing.one,
  },
  breadthHeroCard: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    gap: Spacing.three,
    padding: Spacing.three,
  },
  breadthHeroStatus: {
    color: Theme.colors.text,
    fontSize: 24,
    fontWeight: '900',
    marginTop: Spacing.half,
  },
  breadthHeroMetrics: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  breadthPanel: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    gap: Spacing.twoAndHalf,
    padding: Spacing.twoAndHalf,
  },
  breadthPanelEmphasis: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    gap: Spacing.twoAndHalf,
    padding: Spacing.three,
  },
  breadthMockPanel: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.warning,
    borderRadius: Theme.radii.small,
    borderWidth: StyleSheet.hairlineWidth,
    gap: Spacing.two,
    padding: Spacing.twoAndHalf,
  },
  breadthMockOptions: {
    gap: Spacing.two,
    paddingRight: Spacing.two,
  },
  breadthMockChip: {
    alignItems: 'center',
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.pill,
    borderWidth: StyleSheet.hairlineWidth,
    justifyContent: 'center',
    minHeight: 34,
    paddingHorizontal: Spacing.three,
  },
  breadthMockChipActive: {
    backgroundColor: Theme.colors.warningSoft,
    borderColor: Theme.colors.warning,
  },
  breadthMockChipText: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '900',
  },
  breadthMockChipTextActive: {
    color: Theme.colors.warning,
  },
  breadthConfirmationSummary: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  breadthHistoryUnavailable: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    gap: Spacing.one,
    padding: Spacing.twoAndHalf,
  },
  breadthInlineMetrics: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  breadthProfileStack: {
    gap: Spacing.two,
  },
  breadthProfileSummary: {
    color: Theme.colors.text,
    fontSize: 15,
    fontWeight: '900',
  },
  breadthProfileMetricRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
    minHeight: 34,
  },
  breadthProfileLabelBlock: {
    width: 116,
  },
  breadthProfileMetricLabel: {
    color: Theme.colors.text,
    fontSize: 12,
    fontWeight: '900',
  },
  breadthProfileMetricStatus: {
    color: Theme.colors.textMuted,
    fontSize: 10,
    fontWeight: '800',
    marginTop: Spacing.half,
  },
  breadthProfileMetricTrack: {
    backgroundColor: Theme.colors.background,
    borderRadius: Theme.radii.pill,
    flex: 1,
    height: 9,
    overflow: 'hidden',
    position: 'relative',
  },
  breadthProfileMetricFill: {
    borderRadius: Theme.radii.pill,
    height: '100%',
  },
  breadthProfileMidpoint: {
    backgroundColor: Theme.colors.textMuted,
    height: '100%',
    left: '50%',
    opacity: 0.35,
    position: 'absolute',
    width: 1,
    zIndex: 2,
  },
  breadthProfileMetricValue: {
    color: Theme.colors.text,
    fontSize: 12,
    fontWeight: '900',
    textAlign: 'right',
    width: 42,
  },
  breadthCompactEmpty: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderRadius: Theme.radii.small,
    padding: Spacing.twoAndHalf,
  },
  splitBarStack: {
    gap: Spacing.two,
  },
  splitBarLabels: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  splitBarLabel: {
    color: Theme.colors.text,
    fontSize: 12,
    fontWeight: '900',
  },
  splitBarTrack: {
    backgroundColor: Theme.colors.background,
    borderRadius: Theme.radii.pill,
    flexDirection: 'row',
    height: 14,
    overflow: 'hidden',
    position: 'relative',
  },
  splitBarMidpoint: {
    backgroundColor: Theme.colors.textMuted,
    height: '100%',
    left: '50%',
    opacity: 0.35,
    position: 'absolute',
    width: 1,
    zIndex: 2,
  },
  splitBarSegment: {
    height: '100%',
  },
  splitBarNeutral: {
    backgroundColor: Theme.colors.border,
  },
  coverageGaugeTrack: {
    backgroundColor: Theme.colors.background,
    borderRadius: Theme.radii.pill,
    height: 10,
    overflow: 'hidden',
  },
  coverageGaugeFill: {
    borderRadius: Theme.radii.pill,
    height: '100%',
  },
  coverageScaleLabels: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: -Spacing.one,
  },
  breadthQualityBars: {
    gap: Spacing.two,
  },
  qualityBarRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
  },
  qualityBarLabel: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '900',
    width: 112,
  },
  qualityBarTrack: {
    backgroundColor: Theme.colors.background,
    borderRadius: Theme.radii.pill,
    flex: 1,
    height: 8,
    overflow: 'hidden',
  },
  qualityBarFill: {
    borderRadius: Theme.radii.pill,
    height: '100%',
  },
  qualityBarValue: {
    color: Theme.colors.text,
    fontSize: 12,
    fontWeight: '900',
    textAlign: 'right',
    width: 42,
  },
  sectorBreadthList: {
    gap: Spacing.two,
  },
  sectorBreadthRow: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    gap: Spacing.two,
    padding: Spacing.twoAndHalf,
  },
  sectorBreadthHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  sectorBreadthName: {
    color: Theme.colors.text,
    flex: 1,
    fontSize: 15,
    fontWeight: '900',
  },
  sectorBreadthPercent: {
    color: Theme.colors.success,
    fontSize: 14,
    fontWeight: '900',
  },
  sectorBreadthStats: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  sectorBreadthStat: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '800',
  },
  sectionHeaderRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  leadershipHeader: {
    alignItems: 'flex-start',
    gap: Spacing.one,
  },
  leadershipBadgeWrap: {
    alignSelf: 'flex-start',
  },
  summaryTitleBlock: {
    flex: 1,
    gap: Spacing.half,
    minWidth: 0,
  },
  indexDisclosureRow: {
    alignItems: 'center',
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  indexPanel: {
    backgroundColor: Theme.colors.card,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.card,
    borderWidth: 1,
    gap: Spacing.two,
    padding: Spacing.three,
  },
  indexLegend: {
    alignItems: 'center',
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.three,
  },
  legendItem: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.one,
  },
  legendDot: {
    borderRadius: 5,
    height: 10,
    width: 10,
  },
  legendText: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '900',
  },
  indexChartBox: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    overflow: 'hidden',
  },
  indexChartBaseline: {
    backgroundColor: 'rgba(148, 163, 184, 0.28)',
  },
  indexChartGridLine: {
    backgroundColor: 'rgba(148, 163, 184, 0.1)',
    height: 1,
    left: 0,
    position: 'absolute',
    right: 0,
  },
  indexChartYAxisLabel: {
    backgroundColor: 'rgba(15, 23, 42, 0.7)',
    color: Theme.colors.textMuted,
    fontSize: 9,
    fontWeight: '900',
    left: Spacing.one,
    paddingHorizontal: Spacing.one,
    position: 'absolute',
    top: -7,
  },
  indexChartEmpty: {
    alignItems: 'center',
    flex: 1,
    justifyContent: 'center',
  },
  indexLatestPoint: {
    backgroundColor: Theme.colors.background,
    borderRadius: 5,
    borderWidth: 2,
    height: 10,
    position: 'absolute',
    width: 10,
  },
  indexActivePoint: {
    backgroundColor: Theme.colors.background,
    borderRadius: 6,
    borderWidth: 2,
    height: 12,
    position: 'absolute',
    width: 12,
  },
  indexCrosshair: {
    backgroundColor: 'rgba(148, 163, 184, 0.22)',
    bottom: 22,
    position: 'absolute',
    top: 8,
    width: 1,
  },
  endpointLabel: {
    backgroundColor: 'rgba(15, 23, 42, 0.8)',
    fontSize: 9,
    fontWeight: '900',
    paddingHorizontal: Spacing.half,
    position: 'absolute',
  },
  indexLineSegment: {
    borderRadius: Theme.radii.pill,
    height: 2,
    position: 'absolute',
  },
  indexTooltip: {
    backgroundColor: 'rgba(15, 23, 42, 0.94)',
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    gap: Spacing.half,
    padding: Spacing.two,
    position: 'absolute',
    top: Spacing.two,
    width: 124,
  },
  macroTooltip: {
    width: 178,
  },
  tooltipRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.one,
  },
  tooltipDot: {
    borderRadius: 4,
    height: 8,
    width: 8,
  },
  tooltipTitle: {
    color: Theme.colors.text,
    fontSize: 11,
    fontWeight: '900',
  },
  tooltipText: {
    color: Theme.colors.textMuted,
    fontSize: 10,
    fontWeight: '800',
    width: 24,
  },
  tooltipValue: {
    color: Theme.colors.text,
    flex: 1,
    fontSize: 10,
    fontWeight: '900',
    textAlign: 'right',
  },
  indexXAxisLabel: {
    bottom: 5,
    color: Theme.colors.textMuted,
    fontSize: 9,
    fontWeight: '800',
    position: 'absolute',
    width: 42,
  },
  emptyText: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '900',
    textAlign: 'center',
  },
  macroLeadLagGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  macroSubsection: {
    borderTopColor: Theme.colors.border,
    borderTopWidth: StyleSheet.hairlineWidth,
    gap: Spacing.two,
    paddingTop: Spacing.two,
  },
  macroRotationRows: {
    gap: Spacing.two,
  },
  macroRotationRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
    minHeight: 28,
  },
  macroRotationLabel: {
    color: Theme.colors.text,
    fontSize: 12,
    fontWeight: '900',
    width: 76,
  },
  macroRotationTrack: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderRadius: Theme.radii.pill,
    flex: 1,
    height: 10,
    overflow: 'hidden',
    position: 'relative',
  },
  macroRotationZero: {
    backgroundColor: 'rgba(148, 163, 184, 0.45)',
    height: '100%',
    left: '50%',
    position: 'absolute',
    width: 1,
    zIndex: 2,
  },
  macroRotationBar: {
    borderRadius: Theme.radii.pill,
    height: '100%',
    position: 'absolute',
  },
  macroRotationBarPositive: {
    backgroundColor: Theme.colors.success,
  },
  macroRotationBarNegative: {
    backgroundColor: Theme.colors.danger,
  },
  macroRotationValue: {
    fontSize: 12,
    fontWeight: '900',
    textAlign: 'right',
    width: 58,
  },
  macroGaugeLabels: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  macroGaugeTrack: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderRadius: Theme.radii.pill,
    height: 14,
    overflow: 'hidden',
    position: 'relative',
  },
  macroGaugeCenter: {
    backgroundColor: 'rgba(148, 163, 184, 0.55)',
    height: '100%',
    left: '50%',
    position: 'absolute',
    width: 1,
  },
  macroGaugeMarker: {
    backgroundColor: Theme.colors.accent,
    borderRadius: 6,
    height: 22,
    marginLeft: -3,
    position: 'absolute',
    top: -4,
    width: 6,
  },
  macroFactorGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  macroFactorColumn: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: StyleSheet.hairlineWidth,
    flexBasis: '47%',
    flexGrow: 1,
    gap: Spacing.one,
    minWidth: 145,
    padding: Spacing.twoAndHalf,
  },
  macroEventValueRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  indexSummaryRow: {
    flexDirection: 'row',
    gap: Spacing.two,
  },
  indexSummaryBlock: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    flex: 1,
    gap: Spacing.half,
    minWidth: 0,
    padding: Spacing.two,
  },
  indexSummarySymbol: {
    color: Theme.colors.text,
    fontSize: 15,
    fontWeight: '900',
  },
  indexSummaryReturn: {
    fontSize: 17,
    fontWeight: '900',
  },
  indexSummaryMeta: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '800',
  },
  sparklineBox: {
    height: 34,
    marginTop: Spacing.one,
    overflow: 'hidden',
    position: 'relative',
  },
  sparklineEmpty: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderRadius: Theme.radii.small,
    height: 34,
    marginTop: Spacing.one,
  },
  sparklinePoint: {
    backgroundColor: Theme.colors.cardMuted,
    borderRadius: 4,
    borderWidth: 2,
    height: 8,
    position: 'absolute',
    width: 8,
  },
  priceBlock: {
    alignItems: 'flex-end',
    flexShrink: 0,
  },
  indexChange: {
    color: Theme.colors.success,
    fontSize: 13,
    fontWeight: '800',
    marginTop: Spacing.one,
  },
  indexChangeNegative: {
    color: Theme.colors.danger,
  },
  volumeGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  volumeTile: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    flex: 1,
    gap: Spacing.one,
    minWidth: '30%',
    padding: Spacing.two,
  },
  volumeTilePrimary: {
    flexBasis: '100%',
  },
  volumeTileHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  volumeSymbol: {
    color: Theme.colors.text,
    fontSize: 14,
    fontWeight: '900',
  },
  volumeLabel: {
    color: Theme.colors.text,
    fontSize: 12,
    fontWeight: '800',
    lineHeight: 16,
  },
  signalPill: {
    borderRadius: Theme.radii.pill,
    paddingHorizontal: Spacing.two,
    paddingVertical: Spacing.half,
  },
  signalPillText: {
    fontSize: 10,
    fontWeight: '900',
  },
  volumeUnavailableBar: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderRadius: Theme.radii.pill,
    minHeight: 20,
    justifyContent: 'center',
    paddingHorizontal: Spacing.two,
  },
  volumeRatioTrack: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderRadius: Theme.radii.pill,
    height: 16,
    overflow: 'hidden',
    position: 'relative',
  },
  volumeRatioFill: {
    borderRadius: Theme.radii.pill,
    bottom: 0,
    left: 0,
    opacity: 0.72,
    position: 'absolute',
    top: 0,
  },
  volumeAverageMarker: {
    backgroundColor: Theme.colors.text,
    bottom: 0,
    left: '50%',
    opacity: 0.72,
    position: 'absolute',
    top: 0,
    width: 1,
  },
  volumeAverageLabel: {
    color: Theme.colors.textMuted,
    fontSize: 8,
    fontWeight: '900',
    left: '50%',
    marginLeft: 3,
    position: 'absolute',
    top: 2,
  },
  indexSetupCard: {
    backgroundColor: Theme.colors.card,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.card,
    borderWidth: 1,
    gap: Spacing.two,
    padding: Spacing.three,
  },
  indexSetupHeader: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  indexSetupSymbol: {
    color: Theme.colors.text,
    fontSize: 20,
    fontWeight: '900',
  },
  indexSetupPrice: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '900',
    marginTop: Spacing.half,
  },
  indexSetupLabel: {
    color: Theme.colors.accent,
    fontSize: 12,
    fontWeight: '900',
    marginTop: Spacing.one,
  },
  returnLabel: {
    color: Theme.colors.textMuted,
    fontSize: 9,
    fontWeight: '900',
    marginTop: Spacing.half,
    textTransform: 'uppercase',
  },
  compactSetupRows: {
    gap: Spacing.two,
  },
  setupLine: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  setupLineLabel: {
    color: Theme.colors.textMuted,
    fontSize: 10,
    fontWeight: '900',
    textTransform: 'uppercase',
  },
  setupLineValue: {
    color: Theme.colors.text,
    flex: 1,
    fontSize: 12,
    fontWeight: '800',
    lineHeight: 17,
    textAlign: 'right',
  },
  technicalStrip: {
    backgroundColor: Theme.colors.cardMuted,
    borderRadius: Theme.radii.small,
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
    padding: Spacing.two,
  },
  technicalMiniValue: {
    flexGrow: 1,
    minWidth: '30%',
  },
  statLabel: {
    color: Theme.colors.textMuted,
    fontSize: 10,
    fontWeight: '900',
    textTransform: 'uppercase',
  },
  statValue: {
    color: Theme.colors.text,
    fontSize: 12,
    fontWeight: '900',
    marginTop: Spacing.half,
  },
  healthComponentList: {
    gap: Spacing.twoAndHalf,
  },
  healthComponentRow: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    gap: Spacing.two,
    padding: Spacing.twoAndHalf,
  },
  healthExplanation: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '700',
    lineHeight: 18,
  },
  healthDashboardSection: {
    gap: Spacing.two,
  },
  healthSectionHeader: {
    gap: Spacing.half,
  },
  healthSectionSubtitle: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '800',
  },
  healthOverviewCard: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    gap: Spacing.three,
    padding: Spacing.three,
  },
  healthOverviewTop: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: Spacing.three,
    justifyContent: 'space-between',
  },
  healthScoreBlock: {
    gap: Spacing.half,
  },
  healthScoreValue: {
    color: Theme.colors.text,
    fontSize: 40,
    fontWeight: '900',
    lineHeight: 44,
  },
  healthScoreCaption: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '900',
    textTransform: 'uppercase',
  },
  healthStatusStack: {
    alignItems: 'flex-end',
    gap: Spacing.one,
  },
  healthOverviewSummary: {
    color: Theme.colors.text,
    fontSize: 14,
    fontWeight: '700',
    lineHeight: 21,
  },
  healthOverviewMeta: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  healthMiniMetric: {
    backgroundColor: Theme.colors.cardMuted,
    borderRadius: Theme.radii.small,
    flexGrow: 1,
    gap: Spacing.one,
    minWidth: '47%',
    padding: Spacing.twoAndHalf,
  },
  healthMiniMetricLabel: {
    color: Theme.colors.textMuted,
    fontSize: 10,
    fontWeight: '900',
    textTransform: 'uppercase',
  },
  healthMiniMetricValue: {
    color: Theme.colors.text,
    fontSize: 13,
    fontWeight: '900',
    lineHeight: 18,
  },
  healthProfileCard: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    gap: Spacing.two,
    padding: Spacing.twoAndHalf,
  },
  healthProfileRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
  },
  healthProfileLabel: {
    color: Theme.colors.text,
    fontSize: 12,
    fontWeight: '900',
    width: 104,
  },
  healthProfileTrack: {
    backgroundColor: Theme.colors.background,
    borderRadius: Theme.radii.pill,
    flex: 1,
    height: 8,
    overflow: 'hidden',
  },
  healthProfileFill: {
    borderRadius: Theme.radii.pill,
    height: '100%',
  },
  healthProfileScore: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '900',
    textAlign: 'right',
    width: 42,
  },
  healthRadarCard: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    gap: Spacing.twoAndHalf,
    padding: Spacing.twoAndHalf,
  },
  healthRadarFrame: {
    alignItems: 'center',
    minHeight: 260,
    width: '100%',
  },
  healthRadarCanvas: {
    position: 'relative',
  },
  healthRadarLine: {
    borderRadius: Theme.radii.pill,
    position: 'absolute',
  },
  healthRadarPoint: {
    backgroundColor: Theme.colors.accent,
    borderColor: Theme.colors.text,
    borderRadius: 4,
    borderWidth: 1,
    height: 8,
    position: 'absolute',
    width: 8,
  },
  healthRadarLabel: {
    color: Theme.colors.textMuted,
    fontSize: 10,
    fontWeight: '900',
    position: 'absolute',
    textAlign: 'center',
    width: 92,
  },
  healthRadarRingLabel: {
    color: Theme.colors.textMuted,
    fontSize: 9,
    fontWeight: '900',
    opacity: 0.82,
    position: 'absolute',
  },
  healthRadarUnavailable: {
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 160,
  },
  healthRadarLegend: {
    borderTopColor: Theme.colors.border,
    borderTopWidth: 1,
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
    paddingTop: Spacing.two,
  },
  healthRadarLegendItem: {
    alignItems: 'center',
    backgroundColor: Theme.colors.backgroundMuted,
    borderRadius: Theme.radii.small,
    flexDirection: 'row',
    flexGrow: 1,
    gap: Spacing.one,
    minWidth: '47%',
    paddingHorizontal: Spacing.two,
    paddingVertical: Spacing.one,
  },
  healthRadarLegendDot: {
    borderRadius: 4,
    height: 8,
    width: 8,
  },
  healthRadarLegendLabel: {
    color: Theme.colors.textMuted,
    flex: 1,
    fontSize: 11,
    fontWeight: '900',
  },
  healthRadarLegendScore: {
    color: Theme.colors.text,
    fontSize: 12,
    fontWeight: '900',
  },
  healthComponentGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  healthComponentCard: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    flexGrow: 1,
    gap: Spacing.half,
    minWidth: '47%',
    padding: Spacing.two,
  },
  healthComponentCardHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  healthComponentName: {
    color: Theme.colors.text,
    flex: 1,
    fontSize: 13,
    fontWeight: '900',
  },
  healthScorePill: {
    borderRadius: Theme.radii.pill,
    minWidth: 42,
    paddingHorizontal: Spacing.two,
    paddingVertical: Spacing.one,
  },
  healthScorePillText: {
    fontSize: 12,
    fontWeight: '900',
    textAlign: 'center',
  },
  healthComponentStatus: {
    color: Theme.colors.accent,
    fontSize: 12,
    fontWeight: '900',
  },
  healthComponentMeaning: {
    color: Theme.colors.text,
    fontSize: 12,
    fontWeight: '700',
    lineHeight: 17,
  },
  healthDisclosure: {
    marginTop: Spacing.one,
  },
  healthDisclosureButton: {
    alignItems: 'center',
    alignSelf: 'flex-start',
    flexDirection: 'row',
    gap: Spacing.two,
    minHeight: 32,
    paddingVertical: Spacing.one,
  },
  healthDisclosureText: {
    color: Theme.colors.accent,
    fontSize: 11,
    fontWeight: '900',
  },
  healthDisclosureIcon: {
    color: Theme.colors.accent,
    fontSize: 14,
    fontWeight: '900',
  },
  healthDisclosureBody: {
    gap: Spacing.one,
    paddingTop: Spacing.one,
  },
  healthComponentRationale: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '700',
    lineHeight: 16,
    marginTop: Spacing.one,
  },
  healthTrendCard: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    gap: Spacing.two,
    padding: Spacing.twoAndHalf,
  },
  healthTrendHeader: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  healthTrendCompactRow: {
    alignItems: 'center',
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  healthUnavailableText: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '700',
    lineHeight: 18,
  },
  healthDriverColumns: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  healthDriverPanel: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    flexGrow: 1,
    gap: Spacing.two,
    minWidth: '47%',
    padding: Spacing.twoAndHalf,
  },
  healthDriverTitle: {
    color: Theme.colors.text,
    fontSize: 13,
    fontWeight: '900',
  },
  healthDriverList: {
    gap: Spacing.two,
  },
  healthDriverRow: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: Spacing.two,
  },
  healthDriverDot: {
    borderRadius: 4,
    height: 8,
    marginTop: 5,
    width: 8,
  },
  healthDriverText: {
    color: Theme.colors.text,
    flex: 1,
    fontSize: 12,
    fontWeight: '700',
    lineHeight: 17,
  },
  healthContributionCard: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    gap: Spacing.two,
    padding: Spacing.twoAndHalf,
  },
  healthContributionTotalRow: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  healthContributionTotalLabel: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '900',
    textTransform: 'uppercase',
  },
  healthContributionTotalValue: {
    color: Theme.colors.text,
    fontSize: 22,
    fontWeight: '900',
  },
  healthContributionRow: {
    gap: Spacing.one,
  },
  healthContributionHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  healthContributionName: {
    color: Theme.colors.text,
    fontSize: 12,
    fontWeight: '900',
  },
  healthContributionValue: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '900',
  },
  healthContributionTrack: {
    backgroundColor: Theme.colors.background,
    borderRadius: Theme.radii.pill,
    height: 7,
    overflow: 'hidden',
  },
  healthContributionFill: {
    borderRadius: Theme.radii.pill,
    height: '100%',
  },
  healthDecisionCard: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    gap: Spacing.three,
    padding: Spacing.three,
  },
  healthDecisionHeader: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  healthDecisionLabel: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '900',
    textTransform: 'uppercase',
  },
  healthDecisionStance: {
    color: Theme.colors.text,
    fontSize: 20,
    fontWeight: '900',
    marginTop: Spacing.half,
  },
  healthFillStrong: {
    backgroundColor: Theme.colors.success,
  },
  healthFillConstructive: {
    backgroundColor: Theme.colors.accent,
  },
  healthFillMixed: {
    backgroundColor: Theme.colors.warning,
  },
  healthFillWeak: {
    backgroundColor: Theme.colors.danger,
  },
  healthFillUnavailable: {
    backgroundColor: Theme.colors.border,
  },
  healthPillStrong: {
    backgroundColor: Theme.colors.successSoft,
  },
  healthPillConstructive: {
    backgroundColor: Theme.colors.accentSoft,
  },
  healthPillMixed: {
    backgroundColor: Theme.colors.warningSoft,
  },
  healthPillWeak: {
    backgroundColor: Theme.colors.dangerSoft,
  },
  healthPillUnavailable: {
    backgroundColor: Theme.colors.cardElevated,
  },
  healthTextStrong: {
    color: Theme.colors.success,
  },
  healthTextConstructive: {
    color: Theme.colors.accent,
  },
  healthTextMixed: {
    color: Theme.colors.warning,
  },
  healthTextWeak: {
    color: Theme.colors.danger,
  },
  healthTextUnavailable: {
    color: Theme.colors.textMuted,
  },
  healthDriverDotSupportive: {
    backgroundColor: Theme.colors.success,
  },
  healthDriverDotWarning: {
    backgroundColor: Theme.colors.warning,
  },
  healthDriverDotNegative: {
    backgroundColor: Theme.colors.danger,
  },
  healthDriverDotNeutral: {
    backgroundColor: Theme.colors.textMuted,
  },
  sectionStack: {
    gap: Spacing.three,
  },
  detailSectionTitle: {
    color: Theme.colors.text,
    fontSize: 15,
    fontWeight: '900',
  },
  vixRow: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  vixValue: {
    color: Theme.colors.text,
    fontSize: 34,
    fontWeight: '900',
  },
  normalBadge: {
    backgroundColor: Theme.colors.successSoft,
    borderRadius: Theme.radii.pill,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.two,
  },
  normalBadgeText: {
    color: Theme.colors.success,
    fontSize: 13,
    fontWeight: '900',
  },
  followThroughBox: {
    backgroundColor: Theme.colors.accentSoft,
    borderRadius: Theme.radii.small,
    marginTop: Spacing.two,
    padding: Spacing.twoAndHalf,
  },
  followThroughText: {
    color: Theme.colors.primary,
    fontSize: 16,
    fontWeight: '900',
  },
  biasPanel: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    gap: Spacing.two,
    marginBottom: Spacing.two,
    padding: Spacing.twoAndHalf,
  },
  biasHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  biasLabel: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '900',
    textTransform: 'uppercase',
  },
  biasBadge: {
    borderRadius: Theme.radii.pill,
    paddingHorizontal: Spacing.twoAndHalf,
    paddingVertical: Spacing.one,
  },
  biasBadgeText: {
    fontSize: 13,
    fontWeight: '900',
  },
  biasSummary: {
    color: Theme.colors.text,
    fontSize: 14,
    fontWeight: '700',
    lineHeight: 21,
  },
  institutionalIndexList: {
    gap: Spacing.two,
    marginTop: Spacing.two,
  },
  institutionalIndexCard: {
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    gap: Spacing.two,
    padding: Spacing.twoAndHalf,
  },
  institutionalIndexHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  institutionalIndexSymbol: {
    color: Theme.colors.text,
    fontSize: 18,
    fontWeight: '900',
  },
  followBadge: {
    backgroundColor: Theme.colors.card,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    paddingHorizontal: Spacing.two,
    paddingVertical: Spacing.one,
  },
  followBadgeTriggered: {
    backgroundColor: Theme.colors.successSoft,
    borderColor: Theme.colors.success,
  },
  followBadgeText: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '900',
  },
  followBadgeTextTriggered: {
    color: Theme.colors.success,
  },
  bodyText: {
    color: Theme.colors.text,
    fontSize: 15,
    lineHeight: 23,
  },
});
