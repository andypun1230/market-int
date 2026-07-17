import { useMemo, useState } from 'react';
import { SymbolView } from 'expo-symbols';
import { Modal, Pressable, SafeAreaView, ScrollView, StyleSheet, Text, useWindowDimensions, View } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { AdvanceDeclineBar } from '@/components/charts/AdvanceDeclineBar';
import { BreadthHistoryChart } from '@/components/charts/BreadthHistoryChart';
import { BreadthParticipationBars } from '@/components/charts/BreadthParticipationBars';
import { PerformanceHeatmap } from '@/components/charts/PerformanceHeatmap';
import { RotationAlertsCard } from '@/components/charts/RotationAlertsCard';
import { RotationQuadrantChart } from '@/components/charts/RotationQuadrantChart';
import { RotationTimelineStrip } from '@/components/charts/RotationTimelineStrip';
import { TimeIntervalSelector } from '@/components/charts/TimeIntervalSelector';
import { AppScreen } from '@/components/ui/AppScreen';
import { DetailModal } from '@/components/ui/DetailModal';
import { MetricTile } from '@/components/ui/MetricTile';
import { StatusBadge, type Tone } from '@/components/ui/StatusBadge';
import { TestDataBadge } from '@/components/ui/TestDataBadge';
import { Spacing, Theme } from '@/constants/theme';
import { AskCopilotButton } from '@/features/copilot/components/AskCopilotButton';
import { createCopilotContext } from '@/features/copilot/context/buildScreenContext';
import {
  BREADTH_HISTORY_INTERVALS,
  buildRotationAlerts,
  formatQuadrant,
  getRotationWindow,
  SECTOR_TAB_TEST_SEED,
  TEST_HEATMAP_INTERVALS,
  TEST_ROTATION_INTERVALS,
  type TestRotationInterval,
  type TestSectorItem,
  type SectorThemeTestItem,
  type TestThemeItem,
} from '@/data/sectorTabTestData';
import { calculateLeadershipConcentration } from '@/features/sectors/analysis/concentration';
import { detectDivergences } from '@/features/sectors/analysis/divergence';
import {
  countActiveFilters,
  DEFAULT_SECTOR_THEME_FILTERS,
  filterSectorThemeItems,
  type SectorThemeFilters,
} from '@/features/sectors/analysis/filters';
import {
  type RotationLabelMode,
  type RotationQuadrantFilter,
} from '@/features/sectors/analysis/rotationLabels';
import {
  buildEmergingLeadershipScanner,
  buildLeadershipRiskScanner,
} from '@/features/sectors/analysis/scanners';
import { AnalysisSectionHeader } from '@/features/sectors/components/AnalysisSectionHeader';
import { ConcentrationSummary } from '@/features/sectors/components/ConcentrationSummary';
import { DivergenceBadge, DivergenceCard } from '@/features/sectors/components/DivergenceCard';
import { LeadershipScannerCard } from '@/features/sectors/components/LeadershipScannerCard';
import { RelevantStocksSection } from '@/features/sectors/components/RelevantStocksSection';
import { SectorThemeComparisonView } from '@/features/sectors/components/SectorThemeComparisonView';
import { SectorThemeFilterPanel } from '@/features/sectors/components/SectorThemeFilterPanel';
import { SectorThemeSearchModal } from '@/features/sectors/components/SectorThemeSearchModal';
import { createTestSectorThemeRepository } from '@/features/sectors/repository/sectorThemeRepository';
import { useSectorUiPreferences } from '@/features/sectors/state/sectorUiPreferences';
import { areTestScenariosEnabled } from '@/services/runtimeConfig';
import type {
  SectorActiveCategory,
  SectorActiveSection,
  SectorDetailSelection,
} from '@/features/sectors/types';
import { buildWatchlistKey, useWatchlist } from '@/features/watchlist/store';
import { WatchlistBookmarkButton } from '@/features/watchlist/WatchlistBookmarkButton';

type ActiveSection = SectorActiveSection;
type ActiveCategory = SectorActiveCategory;
type DetailSelection = SectorDetailSelection;

const CATEGORY_OPTIONS: { key: SectorActiveCategory; label: string }[] = [
  { key: 'sectors', label: 'Sectors' },
  { key: 'themes', label: 'Themes' },
  { key: 'signals', label: 'Signals' },
];
const CONTENT_OPTIONS: Record<SectorActiveCategory, { key: SectorActiveSection; label: string }[]> = {
  sectors: [
    { key: 'sectorHeatmap', label: 'Heatmap' },
    { key: 'sectorRotation', label: 'Rotation' },
    { key: 'sectorAlerts', label: 'Alerts' },
  ],
  themes: [
    { key: 'themesHeatmap', label: 'Heatmap' },
    { key: 'themesRotation', label: 'Rotation' },
    { key: 'themeAlerts', label: 'Alerts' },
  ],
  signals: [
    { key: 'emergingLeadership', label: 'Emerging' },
    { key: 'leadershipRisk', label: 'At Risk' },
  ],
};

export default function SectorsScreen() {
  const testScenariosEnabled = areTestScenariosEnabled();
  const [sectorPreferences, updateSectorPreferences] = useSectorUiPreferences();
  const activeSection = sectorPreferences.activeSection;
  const [comparisonVisible, setComparisonVisible] = useState(false);
  const [filterVisible, setFilterVisible] = useState(false);
  const [searchVisible, setSearchVisible] = useState(false);
  const [comparisonItems, setComparisonItems] = useState<SectorThemeTestItem[]>([]);
  const [seedVersion, setSeedVersion] = useState(0);
  const [filtersBySection, setFiltersBySection] = useState<Partial<Record<ActiveSection, SectorThemeFilters>>>({});
  const [selectedSectorRotationKey, setSelectedSectorRotationKey] = useState<string | null>(null);
  const [selectedThemeRotationKey, setSelectedThemeRotationKey] = useState<string | null>(null);
  const [fullscreenRotation, setFullscreenRotation] = useState<'sector' | 'theme' | null>(null);
  const [selectedDetail, setSelectedDetail] = useState<DetailSelection>(null);
  const watchlist = useWatchlist();

  const seed = seedVersion === 0 ? SECTOR_TAB_TEST_SEED : `${SECTOR_TAB_TEST_SEED}-${seedVersion}`;
  const repository = useMemo(() => createTestSectorThemeRepository(seed), [seed]);
  const sectors = useMemo(() => repository.getSectors(), [repository]);
  const themes = useMemo(() => repository.getThemes(), [repository]);
  const benchmark = repository.getBenchmark();
  const allItems = useMemo<SectorThemeTestItem[]>(() => repository.getAllItems(), [repository]);
  const watchlistKeys = useMemo(
    () => new Set(watchlist.groupItems.map((item) => buildWatchlistKey(item.type, item.id))),
    [watchlist.groupItems],
  );
  const stockWatchlistKeys = useMemo(
    () => new Set(watchlist.stockItems.map((item) => buildWatchlistKey('stock', item.ticker))),
    [watchlist.stockItems],
  );
  const currentFilters = filtersBySection[activeSection] ?? DEFAULT_SECTOR_THEME_FILTERS;
  const activeCategory = getCategoryForSection(activeSection);
  const updateCurrentFilters = (filters: SectorThemeFilters) =>
    setFiltersBySection((current) => ({ ...current, [activeSection]: filters }));
  const toggleGroupWatchlist = (item: SectorThemeTestItem) => {
    watchlist.toggleWatchlistItem({ id: item.id, name: item.name, type: item.type });
  };
  const toggleStockWatchlist = (stock: { ticker: string; companyName?: string }) => {
    watchlist.toggleWatchlistItem({
      id: stock.ticker.toUpperCase(),
      name: stock.companyName,
      ticker: stock.ticker.toUpperCase(),
      type: 'stock',
    });
  };
  const isInGroupWatchlist = (item: SectorThemeTestItem) => watchlistKeys.has(buildWatchlistKey(item.type, item.id));
  const sectorHeatmapItems = useMemo(
    () => filterSectorThemeItems(sectors, filtersBySection.sectorHeatmap ?? DEFAULT_SECTOR_THEME_FILTERS, sectorPreferences.sectorHeatmapInterval, watchlistKeys) as TestSectorItem[],
    [watchlistKeys, filtersBySection.sectorHeatmap, sectorPreferences.sectorHeatmapInterval, sectors],
  );
  const sectorRotationItems = useMemo(
    () => filterSectorThemeItems(sectors, filtersBySection.sectorRotation ?? DEFAULT_SECTOR_THEME_FILTERS, '1M', watchlistKeys) as TestSectorItem[],
    [watchlistKeys, filtersBySection.sectorRotation, sectors],
  );
  const themeHeatmapItems = useMemo(
    () => filterSectorThemeItems(themes, filtersBySection.themesHeatmap ?? DEFAULT_SECTOR_THEME_FILTERS, sectorPreferences.themeHeatmapInterval, watchlistKeys) as TestThemeItem[],
    [watchlistKeys, filtersBySection.themesHeatmap, sectorPreferences.themeHeatmapInterval, themes],
  );
  const themeRotationItems = useMemo(
    () => filterSectorThemeItems(themes, filtersBySection.themesRotation ?? DEFAULT_SECTOR_THEME_FILTERS, '1M', watchlistKeys) as TestThemeItem[],
    [watchlistKeys, filtersBySection.themesRotation, themes],
  );
  const sectorAlerts = useMemo(
    () => buildRotationAlerts(sectors, sectorPreferences.sectorRotationInterval),
    [sectorPreferences.sectorRotationInterval, sectors],
  );
  const themeAlerts = useMemo(
    () => buildRotationAlerts(themes, sectorPreferences.themeRotationInterval),
    [sectorPreferences.themeRotationInterval, themes],
  );
  const emergingLeadership = useMemo(() => buildEmergingLeadershipScanner(allItems, 5), [allItems]);
  const leadershipRisk = useMemo(() => buildLeadershipRiskScanner(allItems, 5), [allItems]);
  const copilotContext = useMemo(
    () => createCopilotContext({
      payload: {
        activeSection,
        benchmark,
        emergingLeadership,
        leadershipRisk,
        sectors: sectors.slice(0, 12),
        selectedFilters: currentFilters,
        themes: themes.slice(0, 12),
      },
      routeName: '/sectors',
      screenTitle: activeCategory === 'themes' ? 'Themes' : activeCategory === 'signals' ? 'Sector & Theme Signals' : 'Sectors',
      screenType: activeCategory === 'themes' ? 'theme' : 'sector',
      sourceState: 'mock',
    }),
    [activeCategory, activeSection, benchmark, currentFilters, emergingLeadership, leadershipRisk, sectors, themes],
  );

  return (
    <AppScreen title="Sectors" subtitle={testScenariosEnabled ? 'Interface-development test data for sector and theme rotation visuals.' : 'Sector and theme rotation views.'}>
      <View style={styles.stack}>
        {testScenariosEnabled ? (
          <View style={styles.disclosureCard}>
            <View style={styles.disclosureHeader}>
              <TestDataBadge />
              <Text style={styles.seedText}>Seed {seed}</Text>
            </View>
            <Text style={styles.disclosureText}>
              Test data for interface development. These values are deterministic and are not current market data.
            </Text>
            <Pressable
              accessibilityRole="button"
              onPress={() => setSeedVersion((version) => version + 1)}
              style={({ pressed }) => [styles.regenerateButton, pressed && styles.pressedButton]}>
              <Text style={styles.regenerateText}>Regenerate Test Data</Text>
            </Pressable>
          </View>
        ) : null}

        <AskCopilotButton
          context={copilotContext}
          prompt={activeCategory === 'themes' ? 'Explain the leading themes and the main rotation risk.' : 'Explain sector leadership and rotation on this screen.'}
        />

        <SectorNavigation
          activeFilterCount={countActiveFilters(currentFilters)}
          activeCategory={activeCategory}
          selected={activeSection}
          onCategoryChange={(category) => updateSectorPreferences({ activeSection: getDefaultSectionForCategory(category, activeSection) })}
          onCompare={() => setComparisonVisible(true)}
          onFilter={() => setFilterVisible(true)}
          onSearch={() => setSearchVisible(true)}
          onSectionChange={(section) => updateSectorPreferences({ activeSection: section })}
        />

        {activeSection === 'sectorHeatmap' ? (
          <DashboardCard
            title="Sector Heatmap"
            accentColor={Theme.colors.success}>
            <HeatmapSectionHeader
              description="Sector gain or loss for the selected interval."
              interval={sectorPreferences.sectorHeatmapInterval}
              intervals={TEST_HEATMAP_INTERVALS}
              onChange={(sectorHeatmapInterval) => updateSectorPreferences({ sectorHeatmapInterval })}
            />
            <PerformanceHeatmap
              emptyLabel="No sectors match the current filters."
              getBadgeLabel={(item) => (detectDivergences(item).length ? 'Divergence' : null)}
              getName={(item) => item.name}
              getValue={(item) => item.returns[sectorPreferences.sectorHeatmapInterval]}
              isFavourite={isInGroupWatchlist}
              items={sectorHeatmapItems}
              onPressItem={(item) => setSelectedDetail({ item, kind: 'Sector' })}
              onToggleFavourite={toggleGroupWatchlist}
            />
          </DashboardCard>
        ) : null}

        {activeSection === 'sectorRotation' ? (
          <DashboardCard
            title="Sector Rotation"
            subtitle="Rotation based on relative strength and momentum."
            accentColor={Theme.colors.accent}>
            <SectionHeader
              benchmark={benchmark}
              interval={sectorPreferences.sectorRotationInterval}
              intervals={TEST_ROTATION_INTERVALS}
              onChange={(sectorRotationInterval) => updateSectorPreferences({ sectorRotationInterval })}
            />
            <RotationQuadrantChart
              benchmark={benchmark}
              getHistory={(item) => getRotationWindow(item, sectorPreferences.sectorRotationInterval).history}
              getItemKey={getRotationItemKey}
              getItemType={(item) => item.type}
              getName={(item) => item.name}
              getRelativeMomentum={(item) => getRotationWindow(item, sectorPreferences.sectorRotationInterval).relativeMomentum}
              getRelativeStrength={(item) => getRotationWindow(item, sectorPreferences.sectorRotationInterval).relativeStrength}
              interval={sectorPreferences.sectorRotationInterval}
              items={sectorRotationItems}
              labelMode={sectorPreferences.sectorRotationLabelMode}
              onExpand={() => setFullscreenRotation('sector')}
              onLabelModeChange={(sectorRotationLabelMode) => updateSectorPreferences({ sectorRotationLabelMode })}
              onPressItem={(item) => setSelectedDetail({ item, kind: 'Sector' })}
              onQuadrantFilterChange={(sectorRotationQuadrant) => updateSectorPreferences({ sectorRotationQuadrant })}
              onSelectItem={setSelectedSectorRotationKey}
              onToggleWatchlist={toggleGroupWatchlist}
              quadrantFilter={sectorPreferences.sectorRotationQuadrant}
              selectedItemKey={selectedSectorRotationKey}
              showExpandButton
              trailLength={4}
              watchlistKeys={watchlistKeys}
            />
          </DashboardCard>
        ) : null}

        {activeSection === 'sectorAlerts' ? (
          <RotationAlertsCard alerts={sectorAlerts} title="Sector Rotation Alerts" />
        ) : null}

        {activeSection === 'themesHeatmap' ? (
          <DashboardCard
            title="Themes Heatmap"
            accentColor={Theme.colors.purple}>
            <HeatmapSectionHeader
              description="Theme gain or loss for the selected interval."
              interval={sectorPreferences.themeHeatmapInterval}
              intervals={TEST_HEATMAP_INTERVALS}
              onChange={(themeHeatmapInterval) => updateSectorPreferences({ themeHeatmapInterval })}
            />
            <PerformanceHeatmap
              emptyLabel="No themes match the current filters."
              getBadgeLabel={(item) => (detectDivergences(item).length ? 'Divergence' : null)}
              getName={(item) => item.name}
              getValue={(item) => item.returns[sectorPreferences.themeHeatmapInterval]}
              isFavourite={isInGroupWatchlist}
              items={themeHeatmapItems}
              onPressItem={(item) => setSelectedDetail({ item, kind: 'Theme' })}
              onToggleFavourite={toggleGroupWatchlist}
            />
          </DashboardCard>
        ) : null}

        {activeSection === 'themesRotation' ? (
          <DashboardCard
            title="Themes Rotation"
            subtitle="Theme rotation based on relative strength and momentum."
            accentColor={Theme.colors.warning}>
            <SectionHeader
              benchmark={benchmark}
              interval={sectorPreferences.themeRotationInterval}
              intervals={TEST_ROTATION_INTERVALS}
              onChange={(themeRotationInterval) => updateSectorPreferences({ themeRotationInterval })}
            />
            <RotationQuadrantChart
              benchmark={benchmark}
              getHistory={(item) => getRotationWindow(item, sectorPreferences.themeRotationInterval).history}
              getItemKey={getRotationItemKey}
              getItemType={(item) => item.type}
              getName={(item) => item.name}
              getRelativeMomentum={(item) => getRotationWindow(item, sectorPreferences.themeRotationInterval).relativeMomentum}
              getRelativeStrength={(item) => getRotationWindow(item, sectorPreferences.themeRotationInterval).relativeStrength}
              interval={sectorPreferences.themeRotationInterval}
              items={themeRotationItems}
              labelMode={sectorPreferences.themeRotationLabelMode}
              onExpand={() => setFullscreenRotation('theme')}
              onLabelModeChange={(themeRotationLabelMode) => updateSectorPreferences({ themeRotationLabelMode })}
              onPressItem={(item) => setSelectedDetail({ item, kind: 'Theme' })}
              onQuadrantFilterChange={(themeRotationQuadrant) => updateSectorPreferences({ themeRotationQuadrant })}
              onSelectItem={setSelectedThemeRotationKey}
              onToggleWatchlist={toggleGroupWatchlist}
              quadrantFilter={sectorPreferences.themeRotationQuadrant}
              selectedItemKey={selectedThemeRotationKey}
              showExpandButton
              trailLength={4}
              watchlistKeys={watchlistKeys}
            />
          </DashboardCard>
        ) : null}

        {activeSection === 'themeAlerts' ? (
          <RotationAlertsCard alerts={themeAlerts} title="Themes Rotation Alerts" />
        ) : null}

        {activeSection === 'emergingLeadership' ? (
          <LeadershipScannerCard
            description="Groups gaining relative momentum and improving internal participation."
            isFavourite={isInGroupWatchlist}
            onPressItem={(item) => setSelectedDetail({ item, kind: item.type === 'sector' ? 'Sector' : 'Theme' } as DetailSelection)}
            onToggleFavourite={toggleGroupWatchlist}
            results={emergingLeadership}
            title="Emerging Leadership"
          />
        ) : null}

        {activeSection === 'leadershipRisk' ? (
          <LeadershipScannerCard
            description="Current leaders showing weaker momentum, breadth, or increasing concentration."
            isFavourite={isInGroupWatchlist}
            onPressItem={(item) => setSelectedDetail({ item, kind: item.type === 'sector' ? 'Sector' : 'Theme' } as DetailSelection)}
            onToggleFavourite={toggleGroupWatchlist}
            results={leadershipRisk}
            title="Leadership at Risk"
          />
        ) : null}
      </View>

      <DetailModal
        visible={Boolean(selectedDetail)}
        title={selectedDetail ? `${selectedDetail.kind}: ${selectedDetail.item.name}` : 'Details'}
        subtitle={selectedDetail?.kind === 'Theme' ? selectedDetail.item.parentSector : 'Sector detail · Test Data'}
        onClose={() => setSelectedDetail(null)}>
        <DetailContent
          benchmark={benchmark}
          detail={selectedDetail}
          preferences={sectorPreferences}
          updatePreferences={updateSectorPreferences}
          onToggleStockWatchlist={toggleStockWatchlist}
          stockWatchlistKeys={stockWatchlistKeys}
        />
      </DetailModal>

      <DetailModal
        visible={comparisonVisible}
        title="Compare"
        subtitle="Compare two or three sectors or themes."
        onClose={() => setComparisonVisible(false)}>
        <SectorThemeComparisonView
          favourites={watchlistKeys}
          items={allItems}
          onToggleFavourite={toggleGroupWatchlist}
          selectedItems={comparisonItems}
          setSelectedItems={setComparisonItems}
        />
      </DetailModal>

      <DetailModal
        visible={filterVisible}
        title="Filter & Sort"
        subtitle="Applies to the currently selected Sector tab panel."
        onClose={() => setFilterVisible(false)}>
        <SectorThemeFilterPanel filters={currentFilters} onChange={updateCurrentFilters} />
      </DetailModal>

      <SectorThemeSearchModal
        interval={activeSection === 'themesHeatmap' ? sectorPreferences.themeHeatmapInterval : sectorPreferences.sectorHeatmapInterval}
        isVisible={searchVisible}
        items={allItems}
        onClose={() => setSearchVisible(false)}
        onOpenItem={(item) => {
          setSearchVisible(false);
          setSelectedDetail({ item, kind: item.type === 'sector' ? 'Sector' : 'Theme' } as DetailSelection);
        }}
        onToggleWatchlist={toggleGroupWatchlist}
        watchlistKeys={watchlistKeys}
      />

      <RotationFullscreenModal
        benchmark={benchmark}
        interval={fullscreenRotation === 'theme' ? sectorPreferences.themeRotationInterval : sectorPreferences.sectorRotationInterval}
        items={fullscreenRotation === 'theme' ? themeRotationItems : sectorRotationItems}
        labelMode={fullscreenRotation === 'theme' ? sectorPreferences.themeRotationLabelMode : sectorPreferences.sectorRotationLabelMode}
        onClose={() => setFullscreenRotation(null)}
        onIntervalChange={(interval) =>
          updateSectorPreferences(
            fullscreenRotation === 'theme'
              ? { themeRotationInterval: interval }
              : { sectorRotationInterval: interval },
          )
        }
        onLabelModeChange={(labelMode) =>
          updateSectorPreferences(
            fullscreenRotation === 'theme'
              ? { themeRotationLabelMode: labelMode }
              : { sectorRotationLabelMode: labelMode },
          )
        }
        onOpenDetails={(item) => {
          setFullscreenRotation(null);
          setSelectedDetail({ item, kind: item.type === 'theme' ? 'Theme' : 'Sector' } as DetailSelection);
        }}
        onQuadrantFilterChange={(quadrantFilter) =>
          updateSectorPreferences(
            fullscreenRotation === 'theme'
              ? { themeRotationQuadrant: quadrantFilter }
              : { sectorRotationQuadrant: quadrantFilter },
          )
        }
        onSelectItem={fullscreenRotation === 'theme' ? setSelectedThemeRotationKey : setSelectedSectorRotationKey}
        onToggleWatchlist={toggleGroupWatchlist}
        quadrantFilter={fullscreenRotation === 'theme' ? sectorPreferences.themeRotationQuadrant : sectorPreferences.sectorRotationQuadrant}
        selectedItemKey={fullscreenRotation === 'theme' ? selectedThemeRotationKey : selectedSectorRotationKey}
        title={fullscreenRotation === 'theme' ? 'Themes Rotation' : 'Sector Rotation'}
        visible={fullscreenRotation !== null}
        watchlistKeys={watchlistKeys}
      />
    </AppScreen>
  );
}

function UtilityButton({
  badge,
  icon,
  label,
  onPress,
}: {
  badge?: number;
  icon: { android: string; ios: string; web: string };
  label: string;
  onPress: () => void;
}) {
  return (
    <Pressable
      accessibilityLabel={badge ? `${label}, ${badge} active filters` : label}
      accessibilityRole="button"
      onPress={onPress}
      style={({ pressed }) => [styles.utilityButton, pressed && styles.pressedButton]}>
      <SymbolView
        name={icon as never}
        size={17}
        tintColor={Theme.colors.accent}
        weight="bold"
      />
      {badge ? (
        <View style={styles.filterBadge}>
          <Text style={styles.filterBadgeText}>{badge}</Text>
        </View>
      ) : null}
    </Pressable>
  );
}

function SectorNavigation({
  activeFilterCount,
  activeCategory,
  onCompare,
  onCategoryChange,
  onFilter,
  onSearch,
  onSectionChange,
  selected,
}: {
  activeFilterCount: number;
  activeCategory: ActiveCategory;
  onCompare: () => void;
  onCategoryChange: (category: ActiveCategory) => void;
  onFilter: () => void;
  onSearch: () => void;
  onSectionChange: (section: ActiveSection) => void;
  selected: ActiveSection;
}) {
  return (
    <View style={styles.navigationBlock}>
      <View style={styles.navigationTopRow}>
        <View style={styles.categorySwitch}>
          {CATEGORY_OPTIONS.map((option) => {
            const isSelected = option.key === activeCategory;
            return (
              <Pressable
                accessibilityRole="button"
                accessibilityState={{ selected: isSelected }}
                key={option.key}
                onPress={() => onCategoryChange(option.key)}
                style={({ pressed }) => [
                  styles.categoryButton,
                  isSelected && styles.selectedCategoryButton,
                  pressed && styles.pressedButton,
                ]}>
                <Text style={[styles.categoryButtonText, isSelected && styles.selectedCategoryButtonText]}>
                  {option.label}
                </Text>
              </Pressable>
            );
          })}
        </View>
        <View style={styles.utilityToolbar}>
          <UtilityButton
            icon={{ android: 'search', ios: 'magnifyingglass', web: 'magnifyingglass' }}
            label="Search"
            onPress={onSearch}
          />
          <UtilityButton
            icon={{ android: 'compare_arrows', ios: 'rectangle.2.swap', web: 'rectangle.2.swap' }}
            label="Compare"
            onPress={onCompare}
          />
          <UtilityButton
            badge={activeFilterCount}
            icon={{ android: 'tune', ios: 'slider.horizontal.3', web: 'slider.horizontal.3' }}
            label="Filter"
            onPress={onFilter}
          />
        </View>
      </View>
      <View style={styles.contentSwitch}>
        {CONTENT_OPTIONS[activeCategory].map((option) => {
          const isSelected = option.key === selected;
        return (
          <Pressable
            accessibilityRole="button"
            accessibilityState={{ selected: isSelected }}
            key={option.key}
            onPress={() => onSectionChange(option.key)}
            style={({ pressed }) => [
              styles.contentButton,
              isSelected && styles.selectedContentButton,
              pressed && styles.pressedButton,
            ]}>
            <Text style={[styles.contentButtonText, isSelected && styles.selectedContentButtonText]}>
              {option.label}
            </Text>
          </Pressable>
        );
      })}
      </View>
    </View>
  );
}

function RotationFullscreenModal({
  benchmark,
  interval,
  items,
  labelMode,
  onClose,
  onIntervalChange,
  onLabelModeChange,
  onOpenDetails,
  onQuadrantFilterChange,
  onSelectItem,
  onToggleWatchlist,
  quadrantFilter,
  selectedItemKey,
  title,
  visible,
  watchlistKeys,
}: {
  benchmark: string;
  interval: TestRotationInterval;
  items: SectorThemeTestItem[];
  labelMode: RotationLabelMode;
  onClose: () => void;
  onIntervalChange: (interval: TestRotationInterval) => void;
  onLabelModeChange: (mode: RotationLabelMode) => void;
  onOpenDetails: (item: SectorThemeTestItem) => void;
  onQuadrantFilterChange: (filter: RotationQuadrantFilter) => void;
  onSelectItem: (itemKey: string | null) => void;
  onToggleWatchlist: (item: SectorThemeTestItem) => void;
  quadrantFilter: RotationQuadrantFilter;
  selectedItemKey: string | null;
  title: string;
  visible: boolean;
  watchlistKeys: Set<string>;
}) {
  const { height, width } = useWindowDimensions();
  const chartSize = Math.max(330, Math.min(width - Spacing.three * 2, height * 0.58, 520));

  return (
    <Modal animationType="slide" onRequestClose={onClose} visible={visible}>
      <SafeAreaView style={styles.fullscreenSafeArea}>
        <View style={styles.fullscreenHeader}>
          <View style={styles.fullscreenTitleBlock}>
            <Text style={styles.fullscreenTitle}>{title}</Text>
            <Text style={styles.fullscreenSubtitle}>Expanded relative strength and momentum chart · Test Data</Text>
          </View>
          <Pressable
            accessibilityLabel={`Close ${title}`}
            accessibilityRole="button"
            onPress={onClose}
            style={({ pressed }) => [styles.fullscreenCloseButton, pressed && styles.pressedButton]}>
            <Text style={styles.fullscreenCloseText}>Close</Text>
          </Pressable>
        </View>
        <ScrollView contentContainerStyle={styles.fullscreenContent} showsVerticalScrollIndicator={false}>
          <SectionHeader benchmark={benchmark} interval={interval} intervals={TEST_ROTATION_INTERVALS} onChange={onIntervalChange} />
          <RotationQuadrantChart
            benchmark={benchmark}
            chartSize={chartSize}
            getHistory={(item) => getRotationWindow(item, interval).history}
            getItemKey={getRotationItemKey}
            getItemType={(item) => item.type}
            getName={(item) => item.name}
            getRelativeMomentum={(item) => getRotationWindow(item, interval).relativeMomentum}
            getRelativeStrength={(item) => getRotationWindow(item, interval).relativeStrength}
            interval={interval}
            items={items}
            labelMode={labelMode}
            maxSmartLabels={14}
            onLabelModeChange={onLabelModeChange}
            onPressItem={onOpenDetails}
            onQuadrantFilterChange={onQuadrantFilterChange}
            onSelectItem={onSelectItem}
            onToggleWatchlist={onToggleWatchlist}
            presentation="fullscreen"
            quadrantFilter={quadrantFilter}
            selectedItemKey={selectedItemKey}
            watchlistKeys={watchlistKeys}
          />
        </ScrollView>
      </SafeAreaView>
    </Modal>
  );
}

function getCategoryForSection(section: ActiveSection): ActiveCategory {
  if (section.startsWith('themes')) {
    return 'themes';
  }
  if (section === 'emergingLeadership' || section === 'leadershipRisk') {
    return 'signals';
  }
  return 'sectors';
}

function getDefaultSectionForCategory(category: ActiveCategory, current: ActiveSection): ActiveSection {
  if (getCategoryForSection(current) === category) {
    return current;
  }
  switch (category) {
    case 'themes':
      return 'themesHeatmap';
    case 'signals':
      return 'emergingLeadership';
    case 'sectors':
    default:
      return 'sectorHeatmap';
  }
}

function getRotationItemKey(item: SectorThemeTestItem) {
  return buildWatchlistKey(item.type, item.id);
}

function SectionHeader<T extends string>({
  benchmark,
  interval,
  intervals,
  onChange,
}: {
  benchmark?: string;
  interval: T;
  intervals: readonly T[];
  onChange: (value: T) => void;
}) {
  return (
    <AnalysisSectionHeader
      badge={
        <View style={styles.badgeRow}>
          <TestDataBadge />
          {benchmark ? <Text style={styles.sourceText}>Benchmark {benchmark}</Text> : null}
        </View>
      }
      controls={<TimeIntervalSelector intervals={intervals} selected={interval} onChange={onChange} />}
    />
  );
}

function HeatmapSectionHeader<T extends string>({
  description,
  interval,
  intervals,
  onChange,
}: {
  description: string;
  interval: T;
  intervals: readonly T[];
  onChange: (value: T) => void;
}) {
  return (
    <AnalysisSectionHeader
      badge={<StatusBadge label="Test Data" tone="muted" />}
      controls={<TimeIntervalSelector intervals={intervals} selected={interval} onChange={onChange} />}
      description={description}
    />
  );
}

function DetailContent({
  benchmark,
  detail,
  preferences,
  updatePreferences,
  onToggleStockWatchlist,
  stockWatchlistKeys,
}: {
  benchmark: string;
  detail: DetailSelection;
  preferences: ReturnType<typeof useSectorUiPreferences>[0];
  updatePreferences: ReturnType<typeof useSectorUiPreferences>[1];
  onToggleStockWatchlist: (stock: { ticker: string; companyName?: string }) => void;
  stockWatchlistKeys: Set<string>;
}) {
  const breadthInterval = preferences.detailBreadthInterval;
  const rotationInterval = preferences.detailRotationInterval;

  if (!detail) {
    return null;
  }

  const item = detail.item;
  const rotation = getRotationWindow(item, rotationInterval);
  const singleItem = [item];
  const alerts = buildRotationAlerts(singleItem, rotationInterval, 3);
  const divergences = detectDivergences(item);
  const concentration = calculateLeadershipConcentration(item);
  const copilotContext = createCopilotContext({
    payload: {
      benchmark,
      focused: item,
      selected: item,
    },
    routeName: '/sectors',
    screenTitle: `${detail.kind}: ${item.name}`,
    screenType: detail.kind === 'Theme' ? 'theme' : 'sector',
    sourceState: 'mock',
  });

  return (
    <View style={styles.detailStack}>
      <View style={styles.badgeRow}>
        <TestDataBadge />
        <StatusBadge label={formatQuadrant(rotation.quadrant)} tone={getQuadrantTone(rotation.quadrant)} />
        <DivergenceBadge count={divergences.length} />
        <WatchlistBookmarkButton id={item.id} name={item.name} type={item.type} />
      </View>

      <AskCopilotButton
        context={copilotContext}
        prompt={`Explain ${item.name} leadership and the main risk.`}
      />

      <DashboardCard title={`${detail.kind} Performance Summary`} accentColor={Theme.colors.success}>
        <View style={styles.metricGrid}>
          {TEST_HEATMAP_INTERVALS.map((interval) => (
            <MetricTile key={interval} label={interval} value={formatPercent(item.returns[interval])} />
          ))}
        </View>
      </DashboardCard>

      {detail.kind === 'Sector' ? (
        <>
          <BreadthParticipationBars breadth={detail.item.breadth} />
          <AdvanceDeclineBar breadth={detail.item.breadth} />

          <DashboardCard title="Breadth History" accentColor={Theme.colors.accent}>
            <SectionHeader
              interval={breadthInterval}
              intervals={BREADTH_HISTORY_INTERVALS}
              onChange={(detailBreadthInterval) => updatePreferences({ detailBreadthInterval })}
            />
            <BreadthHistoryChart points={detail.item.breadthHistory[breadthInterval]} />
          </DashboardCard>
        </>
      ) : null}

      <DivergenceCard signals={divergences} />
      <ConcentrationSummary concentration={concentration} />
      <RelevantStocksSection
        group={item}
        initialInterval="1M"
        onToggleStockWatchlist={onToggleStockWatchlist}
        stockWatchlistKeys={stockWatchlistKeys}
      />

      <RotationTimelineStrip history={rotation.history} />

      <DashboardCard title="Expanded Rotation Trail" subtitle="Longer deterministic trail for selected item." accentColor={Theme.colors.purple}>
        <SectionHeader
          benchmark={benchmark}
          interval={rotationInterval}
          intervals={TEST_ROTATION_INTERVALS}
          onChange={(detailRotationInterval) => updatePreferences({ detailRotationInterval })}
        />
        <RotationQuadrantChart
          benchmark={benchmark}
          chartSize={330}
          getHistory={(currentItem) => getRotationWindow(currentItem, rotationInterval).history}
          getName={(currentItem) => currentItem.name}
          getRelativeMomentum={(currentItem) => getRotationWindow(currentItem, rotationInterval).relativeMomentum}
          getRelativeStrength={(currentItem) => getRotationWindow(currentItem, rotationInterval).relativeStrength}
          interval={rotationInterval}
          items={singleItem}
          maxItems={1}
          trailLength={10}
        />
      </DashboardCard>

      <RotationAlertsCard alerts={alerts} title="Recent Rotation Alerts" />
    </View>
  );
}

function getQuadrantTone(quadrant: ReturnType<typeof getRotationWindow>['quadrant']): Tone {
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

function formatPercent(value: number) {
  const prefix = value > 0 ? '+' : '';
  return `${prefix}${value.toLocaleString('en-US', {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  })}%`;
}

const styles = StyleSheet.create({
  badgeRow: {
    alignItems: 'center',
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
    marginBottom: Spacing.two,
  },
  categoryButton: {
    alignItems: 'center',
    borderRadius: Theme.radii.pill,
    flex: 1,
    justifyContent: 'center',
    minHeight: 36,
    paddingHorizontal: Spacing.two,
    paddingVertical: Spacing.one,
  },
  categoryButtonText: {
    color: Theme.colors.textMuted,
    fontSize: 13,
    fontWeight: '900',
    textAlign: 'center',
  },
  categorySwitch: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    flex: 1,
    flexDirection: 'row',
    gap: Spacing.half,
    minWidth: 0,
    padding: 3,
  },
  contentButton: {
    alignItems: 'center',
    borderBottomColor: 'transparent',
    borderBottomWidth: 2,
    flex: 1,
    justifyContent: 'center',
    minHeight: 38,
    paddingHorizontal: Spacing.one,
    paddingVertical: Spacing.one,
  },
  contentButtonText: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '900',
    textAlign: 'center',
  },
  contentSwitch: {
    backgroundColor: Theme.colors.card,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    flexDirection: 'row',
    paddingHorizontal: Spacing.one,
  },
  detailStack: {
    gap: Spacing.three,
  },
  disclosureCard: {
    backgroundColor: Theme.colors.card,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.card,
    borderWidth: 1,
    gap: Spacing.two,
    padding: Spacing.three,
  },
  disclosureHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  disclosureText: {
    color: Theme.colors.textMuted,
    fontSize: 13,
    fontWeight: '700',
    lineHeight: 19,
  },
  fullscreenCloseButton: {
    alignItems: 'center',
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    justifyContent: 'center',
    minHeight: 44,
    paddingHorizontal: Spacing.twoAndHalf,
    paddingVertical: Spacing.one,
  },
  fullscreenCloseText: {
    color: Theme.colors.text,
    fontSize: 13,
    fontWeight: '900',
  },
  fullscreenContent: {
    gap: Spacing.three,
    padding: Spacing.three,
    paddingBottom: Spacing.five,
  },
  fullscreenHeader: {
    alignItems: 'flex-start',
    borderBottomColor: Theme.colors.border,
    borderBottomWidth: 1,
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
    padding: Spacing.three,
  },
  fullscreenSafeArea: {
    backgroundColor: Theme.colors.background,
    flex: 1,
  },
  fullscreenSubtitle: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '700',
    lineHeight: 17,
  },
  fullscreenTitle: {
    color: Theme.colors.text,
    fontSize: 22,
    fontWeight: '900',
    lineHeight: 28,
  },
  fullscreenTitleBlock: {
    flex: 1,
    gap: Spacing.one,
  },
  metricGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  pressedButton: {
    opacity: 0.78,
  },
  regenerateButton: {
    alignItems: 'center',
    alignSelf: 'flex-start',
    backgroundColor: Theme.colors.warningSoft,
    borderColor: Theme.colors.warning,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    minHeight: 44,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.two,
  },
  regenerateText: {
    color: Theme.colors.warning,
    fontSize: 12,
    fontWeight: '900',
  },
  filterBadge: {
    alignItems: 'center',
    backgroundColor: Theme.colors.warning,
    borderRadius: Theme.radii.pill,
    height: 18,
    justifyContent: 'center',
    minWidth: 18,
    paddingHorizontal: 5,
  },
  filterBadgeText: {
    color: Theme.colors.background,
    fontSize: 10,
    fontWeight: '900',
    textAlign: 'center',
  },
  sectionHeader: {
    marginBottom: Spacing.two,
  },
  seedText: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '900',
  },
  navigationBlock: {
    gap: Spacing.two,
  },
  navigationTopRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
  },
  selectedCategoryButton: {
    backgroundColor: Theme.colors.accentSoft,
  },
  selectedCategoryButtonText: {
    color: Theme.colors.accent,
  },
  selectedContentButton: {
    borderBottomColor: Theme.colors.accent,
  },
  selectedContentButtonText: {
    color: Theme.colors.accent,
  },
  sourceText: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '800',
  },
  stack: {
    gap: Spacing.three,
  },
  utilityButton: {
    alignItems: 'center',
    backgroundColor: Theme.colors.card,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    height: 40,
    justifyContent: 'center',
    width: 40,
  },
  utilityToolbar: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.one,
  },
});
