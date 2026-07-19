import { useMemo, useState } from 'react';
import { SymbolView } from 'expo-symbols';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { PerformanceHeatmap } from '@/components/charts/PerformanceHeatmap';
import { RotationQuadrantChart } from '@/components/charts/RotationQuadrantChart';
import { AppScreen } from '@/components/ui/AppScreen';
import { DetailModal } from '@/components/ui/DetailModal';
import { EmptyState } from '@/components/ui/EmptyState';
import { MetricTile } from '@/components/ui/MetricTile';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Spacing, Theme } from '@/constants/theme';
import { SECTOR_TAB_TEST_SEED, TEST_HEATMAP_INTERVALS, TEST_ROTATION_INTERVALS, buildRotationAlerts, type SectorThemeTestItem, type TestThemeItem } from '@/data/sectorTabTestData';
import { SectorDetailContent } from '@/features/sectors/components/SectorDetailContent';
import { SectorThemeComparisonView } from '@/features/sectors/components/SectorThemeComparisonView';
import { SectorThemeFilterPanel } from '@/features/sectors/components/SectorThemeFilterPanel';
import { SectorThemeSearchModal } from '@/features/sectors/components/SectorThemeSearchModal';
import { DEFAULT_SECTOR_THEME_FILTERS, countActiveFilters, filterSectorThemeItems, type SectorThemeFilters } from '@/features/sectors/analysis/filters';
import { createTestSectorThemeRepository } from '@/features/sectors/repository/sectorThemeRepository';
import { formatClassification, formatCoverage, formatNullablePercent, normalizeSectorId, sourceLabel, type SectorId, type SectorRow } from '@/features/sectors/sectorSnapshot';
import { buildRotationChartSectors } from '@/features/sectors/rotationAvailability';
import { useSectorUiPreferences } from '@/features/sectors/state/sectorUiPreferences';
import { WatchlistBookmarkButton } from '@/features/watchlist/WatchlistBookmarkButton';
import { rotationTrailHistoryDisclosure } from '@/features/sectors/rotationCopy';
import { buildWatchlistKey, useWatchlist } from '@/features/watchlist/store';
import { useSectorRotationTrails, useSectorSnapshot } from '@/hooks/useSectorSnapshot';
import { areTestScenariosEnabled } from '@/services/runtimeConfig';

type ActiveCategory = 'sectors' | 'themes' | 'signals';
type ActiveSection = 'sectorHeatmap' | 'sectorRotation' | 'sectorAlerts' | 'themesHeatmap' | 'themesRotation' | 'themeAlerts' | 'emergingLeadership' | 'leadershipRisk';
type SelectedDetail = { kind: 'sector'; sectorId: SectorId } | { item: TestThemeItem; kind: 'theme' } | null;

const CATEGORY_OPTIONS: { key: ActiveCategory; label: string }[] = [
  { key: 'sectors', label: 'Sectors' },
  { key: 'themes', label: 'Themes' },
  { key: 'signals', label: 'Signals' },
];
const CONTENT_OPTIONS: Record<ActiveCategory, { key: ActiveSection; label: string }[]> = {
  sectors: [{ key: 'sectorHeatmap', label: 'Heatmap' }, { key: 'sectorRotation', label: 'Rotation' }, { key: 'sectorAlerts', label: 'Alerts' }],
  themes: [{ key: 'themesHeatmap', label: 'Heatmap' }, { key: 'themesRotation', label: 'Rotation' }, { key: 'themeAlerts', label: 'Alerts' }],
  signals: [{ key: 'emergingLeadership', label: 'Emerging' }, { key: 'leadershipRisk', label: 'At Risk' }],
};

export default function SectorsScreen() {
  const { snapshot, loading, error, refetch } = useSectorSnapshot();
  const { rotation } = useSectorRotationTrails();
  const [preferences, updatePreferences] = useSectorUiPreferences();
  const [selected, setSelected] = useState<SelectedDetail>(null);
  const [comparisonVisible, setComparisonVisible] = useState(false);
  const [filterVisible, setFilterVisible] = useState(false);
  const [filtersBySection, setFiltersBySection] = useState<Partial<Record<ActiveSection, SectorThemeFilters>>>({});
  const [searchVisible, setSearchVisible] = useState(false);
  const [comparisonItems, setComparisonItems] = useState<SectorThemeTestItem[]>([]);
  const watchlist = useWatchlist();
  const testScenariosEnabled = areTestScenariosEnabled();
  const themeRepository = useMemo(() => testScenariosEnabled ? createTestSectorThemeRepository(SECTOR_TAB_TEST_SEED) : null, [testScenariosEnabled]);
  const themes = useMemo(() => themeRepository?.getThemes() ?? [], [themeRepository]);
  const modelItems = useMemo(() => themeRepository?.getAllItems() ?? [], [themeRepository]);
  const activeSection = preferences.activeSection as ActiveSection;
  const activeCategory = categoryForSection(activeSection);
  const activeFilters = filtersBySection[activeSection] ?? DEFAULT_SECTOR_THEME_FILTERS;
  const watchlistKeys = useMemo(() => new Set(watchlist.groupItems.map((item) => buildWatchlistKey(item.type, item.id))), [watchlist.groupItems]);
  const filteredThemes = useMemo(() => filterSectorThemeItems(themes, activeFilters, preferences.themeHeatmapInterval, watchlistKeys) as TestThemeItem[], [activeFilters, preferences.themeHeatmapInterval, themes, watchlistKeys]);
  const rows = useMemo(() => snapshot?.sectors ?? [], [snapshot]);
  const rotationItems = useMemo(
    () => buildRotationChartSectors(
      rotation,
      preferences.sectorRotationInterval,
      new Map(rows.map((row) => [row.sectorId, row.rank])),
    ),
    [preferences.sectorRotationInterval, rotation, rows],
  );
  const emerging = rows.filter((row) => row.classification === 'Improving');
  const risk = rows.filter((row) => row.classification === 'Leading' && (row.scores.momentum ?? 100) < 50);
  const themeAlerts = useMemo(() => buildRotationAlerts(themes, preferences.themeRotationInterval), [preferences.themeRotationInterval, themes]);

  return (
    <AppScreen title="Sectors" subtitle={snapshot ? `S&P 100 sector snapshot · ${snapshot.marketDate}` : loading ? 'Loading durable sector snapshot.' : 'Sector snapshot unavailable.'}>
      <View style={styles.stack}>
        {snapshot ? <View style={styles.badges}><StatusBadge label="S&P 100" tone="info" /><StatusBadge label={`${formatCoverage(snapshot.coverage.constituentCoverage)} coverage`} tone="success" /><StatusBadge label={sourceLabel(snapshot)} tone="muted" /></View> : null}
        <SectorNavigation
          activeCategory={activeCategory}
          activeSection={activeSection}
          activeFilterCount={countActiveFilters(activeFilters)}
          onCategoryChange={(category) => updatePreferences({ activeSection: defaultSectionForCategory(category, activeSection) })}
          onCompare={() => setComparisonVisible(true)}
          onFilter={() => setFilterVisible((visible) => !visible)}
          onSearch={() => setSearchVisible(true)}
          onSectionChange={(section) => updatePreferences({ activeSection: section })}
        />

        {filterVisible ? <SectorThemeFilterPanel filters={activeFilters} onChange={(filters) => setFiltersBySection((current) => ({ ...current, [activeSection]: filters }))} /> : null}

        {!snapshot && !loading && activeCategory !== 'themes' && !(activeSection === 'sectorRotation' && rotationItems.length) ? <EmptyState title="Sector snapshot unavailable" message={error ?? 'The last-known-good sector snapshot could not be loaded.'} actionLabel="Retry" onAction={refetch} /> : null}

        {activeSection === 'sectorHeatmap' && snapshot ? <DashboardCard title="Sector Heatmap" subtitle="Tiles show ETF return for the selected interval. Rank reflects the overall leadership composite." accentColor={Theme.colors.success}><IntervalTabs value={preferences.sectorHeatmapInterval} onChange={(sectorHeatmapInterval) => updatePreferences({ sectorHeatmapInterval })} /><PerformanceHeatmap emptyLabel="No sectors have data for this interval." getName={(row) => row.displayName} getSubtitle={(row) => `${row.etfSymbol} · #${row.rank} · ${formatClassification(row.classification)}`} getValue={(row) => row.returns[preferences.sectorHeatmapInterval]} items={rows} onPressItem={(row) => setSelected({ kind: 'sector', sectorId: row.sectorId })} /><Text style={styles.note}>Rank = overall relative position. Classification = current rotation state. Unavailable ETF history is shown as N/A.</Text></DashboardCard> : null}

        {activeSection === 'sectorRotation' && (snapshot || rotationItems.length) ? <DashboardCard title="Sector Rotation" subtitle="Real adjusted ETF-versus-SPY history. Current points and tails share one stable rotation formula." accentColor={Theme.colors.accent}><RotationIntervalTabs value={preferences.sectorRotationInterval} onChange={(sectorRotationInterval) => updatePreferences({ sectorRotationInterval })} /><RotationQuadrantChart benchmark={snapshot?.benchmark ?? 'SPY'} getHistory={(row) => rotation?.seriesBySector.get(row.sectorId)?.[preferences.sectorRotationInterval]?.trailPoints ?? []} getItemKey={(row) => row.sectorId} getItemType={() => 'sector'} getLabel={(row) => row.etfSymbol} getLabelPriority={(row) => (row.rank <= 3 ? 3000 - row.rank : 0) + (rotation?.movements.get(row.sectorId)?.direction === 'gaining' ? 1800 : rotation?.movements.get(row.sectorId)?.direction === 'losing' ? 1600 : 0)} getName={(row) => row.displayName} getRelativeMomentum={(row) => rotation?.seriesBySector.get(row.sectorId)?.[preferences.sectorRotationInterval]?.currentPoint?.relativeMomentum ?? null} getRelativeStrength={(row) => rotation?.seriesBySector.get(row.sectorId)?.[preferences.sectorRotationInterval]?.currentPoint?.relativeStrength ?? null} interval={preferences.sectorRotationInterval} items={rotationItems} labelMode={preferences.sectorRotationLabelMode} onLabelModeChange={(sectorRotationLabelMode) => updatePreferences({ sectorRotationLabelMode })} onPressItem={(row) => setSelected({ kind: 'sector', sectorId: row.sectorId })} onQuadrantFilterChange={(sectorRotationQuadrant) => updatePreferences({ sectorRotationQuadrant })} quadrantFilter={preferences.sectorRotationQuadrant} trailLength={5} /><RotationFlowSummary rotation={rotation} /></DashboardCard> : null}

        {activeSection === 'sectorAlerts' && snapshot ? <DashboardCard title="Rotation Alerts" accentColor={Theme.colors.warning}>{snapshot.alerts.length ? snapshot.alerts.map((alert, index) => <Text key={index} style={styles.body}>{JSON.stringify(alert)}</Text>) : <Text style={styles.note}>No transition alerts yet.</Text>}</DashboardCard> : null}

        {activeSection === 'themesHeatmap' ? testScenariosEnabled ? <DashboardCard title="Theme Heatmap" subtitle="Test scenario data only; not live market intelligence." accentColor={Theme.colors.purple}><View style={styles.themeSource}><StatusBadge label="Test Data" tone="warning" /><Text style={styles.note}>Theme inputs are not reviewed live data.</Text></View><IntervalTabs value={preferences.themeHeatmapInterval} onChange={(themeHeatmapInterval) => updatePreferences({ themeHeatmapInterval })} /><PerformanceHeatmap emptyLabel="No themes match the current configuration." getName={(item) => item.name} getSubtitle={(item) => item.parentSector} getValue={(item) => item.returns[preferences.themeHeatmapInterval]} items={filteredThemes} onPressItem={(item) => setSelected({ item, kind: 'theme' })} /></DashboardCard> : <ThemeUnavailable title="Theme Heatmap" /> : null}

        {activeSection === 'themesRotation' ? testScenariosEnabled ? <DashboardCard title="Theme Rotation" subtitle="Test scenario trails - not live market intelligence." accentColor={Theme.colors.purple}><View style={styles.themeSource}><StatusBadge label="Test Data" tone="warning" /><Text style={styles.note}>Generated fixture trails are available only in explicit developer mode.</Text></View><RotationIntervalTabs value={preferences.themeRotationInterval} onChange={(themeRotationInterval) => updatePreferences({ themeRotationInterval })} /><RotationQuadrantChart benchmark="SPY" getHistory={(item) => item.rotation[preferences.themeRotationInterval].history} getItemKey={(item) => item.id} getItemType={() => 'theme'} getName={(item) => item.name} getRelativeMomentum={(item) => item.rotation[preferences.themeRotationInterval].relativeMomentum} getRelativeStrength={(item) => item.rotation[preferences.themeRotationInterval].relativeStrength} interval={preferences.themeRotationInterval} items={themes} labelMode={preferences.themeRotationLabelMode} onLabelModeChange={(themeRotationLabelMode) => updatePreferences({ themeRotationLabelMode })} onPressItem={(item) => setSelected({ item, kind: 'theme' })} onQuadrantFilterChange={(themeRotationQuadrant) => updatePreferences({ themeRotationQuadrant })} quadrantFilter={preferences.themeRotationQuadrant} showTestDataBadge trailLength={10} /></DashboardCard> : <ThemeUnavailable /> : null}

        {activeSection === 'themeAlerts' ? testScenariosEnabled ? <DashboardCard title="Theme Rotation Alerts" subtitle="Test scenario alerts - not live market intelligence." accentColor={Theme.colors.warning}>{themeAlerts.length ? themeAlerts.map((alert) => <View key={alert.id} style={styles.alert}><Text style={styles.name}>{alert.name}</Text><Text style={styles.note}>{alert.message}</Text></View>) : <Text style={styles.note}>No theme rotation alerts.</Text>}</DashboardCard> : <ThemeUnavailable /> : null}

        {activeSection === 'emergingLeadership' && snapshot ? <Scanner title="Emerging Sectors" subtitle="Improving is the canonical classification; this list is not an overall ranking." rows={emerging} onOpen={(sectorId) => setSelected({ kind: 'sector', sectorId })} /> : null}
        {activeSection === 'leadershipRisk' && snapshot ? <Scanner title="At-Risk Sectors" subtitle="Leading sectors with deteriorating momentum or breadth qualify here." rows={risk} empty="No sectors currently meet the at-risk criteria." onOpen={(sectorId) => setSelected({ kind: 'sector', sectorId })} /> : null}
      </View>

      <DetailModal visible={Boolean(selected)} title={selected?.kind === 'theme' ? selected.item.name : selected ? snapshot?.sectors.find((row) => row.sectorId === selected.sectorId)?.displayName ?? 'Sector detail' : 'Sector detail'} subtitle={selected?.kind === 'theme' ? `Theme · ${selected.item.parentSector}` : snapshot ? `${snapshot.marketDate} · ${sourceLabel(snapshot)}` : undefined} onClose={() => setSelected(null)}>
        {selected?.kind === 'sector' ? <SectorDetailContent sectorId={selected.sectorId} /> : null}
        {selected?.kind === 'theme' ? <ThemeDetailContent theme={selected.item} /> : null}
      </DetailModal>
      <SectorThemeSearchModal interval={activeCategory === 'themes' ? preferences.themeHeatmapInterval : preferences.sectorHeatmapInterval} isVisible={searchVisible} items={modelItems} onClose={() => setSearchVisible(false)} onOpenItem={(item) => { setSearchVisible(false); if (item.type === 'theme') setSelected({ item, kind: 'theme' }); else { const sectorId = normalizeSectorId(item.name); if (sectorId) setSelected({ kind: 'sector', sectorId }); } }} onToggleWatchlist={(item) => watchlist.toggleWatchlistItem({ id: item.id, name: item.name, type: item.type })} watchlistKeys={watchlistKeys} />
      <DetailModal visible={comparisonVisible} title="Compare Sectors & Themes" subtitle="Restored comparison configuration" onClose={() => setComparisonVisible(false)}><SectorThemeComparisonView favourites={watchlistKeys} items={modelItems} onToggleFavourite={(item) => watchlist.toggleWatchlistItem({ id: item.id, name: item.name, type: item.type })} selectedItems={comparisonItems} setSelectedItems={setComparisonItems} /></DetailModal>
    </AppScreen>
  );
}

function SectorNavigation({ activeCategory, activeFilterCount, activeSection, onCategoryChange, onCompare, onFilter, onSearch, onSectionChange }: { activeCategory: ActiveCategory; activeFilterCount: number; activeSection: ActiveSection; onCategoryChange: (category: ActiveCategory) => void; onCompare: () => void; onFilter: () => void; onSearch: () => void; onSectionChange: (section: ActiveSection) => void }) {
  return <View style={styles.navigation}><View style={styles.navigationTopRow}><View style={styles.categorySwitch}>{CATEGORY_OPTIONS.map((option) => <Pressable accessibilityRole="button" accessibilityState={{ selected: activeCategory === option.key }} key={option.key} onPress={() => onCategoryChange(option.key)} style={[styles.categoryButton, activeCategory === option.key && styles.categoryButtonActive]}><Text style={[styles.categoryText, activeCategory === option.key && styles.categoryTextActive]}>{option.label}</Text></Pressable>)}</View><View style={styles.utilityToolbar}><UtilityButton icon={{ android: 'search', ios: 'magnifyingglass', web: 'search' }} label="Search" onPress={onSearch} /><UtilityButton icon={{ android: 'compare_arrows', ios: 'rectangle.2.swap', web: 'compare_arrows' }} label="Compare" onPress={onCompare} /><UtilityButton badge={activeFilterCount} icon={{ android: 'tune', ios: 'slider.horizontal.3', web: 'tune' }} label="Filter and sort" onPress={onFilter} /></View></View><View style={styles.contentSwitch}>{CONTENT_OPTIONS[activeCategory].map((option) => <Pressable accessibilityRole="button" accessibilityState={{ selected: activeSection === option.key }} key={option.key} onPress={() => onSectionChange(option.key)} style={[styles.contentButton, activeSection === option.key && styles.contentButtonActive]}><Text style={[styles.contentText, activeSection === option.key && styles.contentTextActive]}>{option.label}</Text></Pressable>)}</View></View>;
}

function UtilityButton({ badge, icon, label, onPress }: { badge?: number; icon: { android: string; ios: string; web: string }; label: string; onPress: () => void }) { return <Pressable accessibilityLabel={badge ? `${label}, ${badge} active filters` : label} accessibilityRole="button" onPress={onPress} style={({ pressed }) => [styles.utilityButton, pressed && styles.pressed]}><SymbolView name={icon as never} size={17} tintColor={Theme.colors.accent} weight="bold" />{badge ? <View style={styles.filterBadge}><Text style={styles.filterBadgeText}>{badge}</Text></View> : null}</Pressable>; }

function IntervalTabs({ value, onChange }: { value: typeof TEST_HEATMAP_INTERVALS[number]; onChange: (value: typeof TEST_HEATMAP_INTERVALS[number]) => void }) { return <View style={styles.tabs}>{TEST_HEATMAP_INTERVALS.map((item) => <Pressable key={item} onPress={() => onChange(item)} style={[styles.tab, value === item && styles.tabActive]}><Text style={[styles.tabText, value === item && styles.tabTextActive]}>{item}</Text></Pressable>)}</View>; }
function RotationIntervalTabs({ value, onChange }: { value: typeof TEST_ROTATION_INTERVALS[number]; onChange: (value: typeof TEST_ROTATION_INTERVALS[number]) => void }) { return <View style={styles.tabs}>{TEST_ROTATION_INTERVALS.map((item) => <Pressable key={item} onPress={() => onChange(item)} style={[styles.tab, value === item && styles.tabActive]}><Text style={[styles.tabText, value === item && styles.tabTextActive]}>{item}</Text></Pressable>)}</View>; }

function RotationFlowSummary({ rotation }: { rotation: ReturnType<typeof useSectorRotationTrails>['rotation'] }) { if (!rotation?.movementAvailable) return <Text style={styles.note}>{rotationTrailHistoryDisclosure}</Text>; const groups = [['Gaining leadership', rotation.flowGroups.gaining], ['Losing leadership', rotation.flowGroups.losing], ['Stable', rotation.flowGroups.stable]] as const; return <View style={styles.flow}><Text style={styles.flowTitle}>Leadership flow</Text>{groups.filter(([, items]) => items.length).map(([label, items]) => <Text key={label} style={styles.note}>{label}: {items.map((item) => item.etfSymbol).join(', ')}</Text>)}</View>; }

function ThemeUnavailable({ title = 'Theme Rotation' }: { title?: string }) { return <DashboardCard title={title} subtitle="Live theme inputs have not been reviewed or published." accentColor={Theme.colors.purple}><Text style={styles.note}>Live theme rotation is not yet available.</Text></DashboardCard>; }

function ThemeDetailContent({ theme }: { theme: TestThemeItem }) { return <View style={styles.detailStack}><View style={styles.badges}><StatusBadge label="Test Data" tone="warning" /><WatchlistBookmarkButton id={theme.id} name={theme.name} type="theme" /></View><DashboardCard title="Theme Performance" accentColor={Theme.colors.purple}><View style={styles.metricGrid}>{TEST_HEATMAP_INTERVALS.map((interval) => <MetricTile key={interval} label={interval} value={formatNullablePercent(theme.returns[interval])} />)}</View></DashboardCard><DashboardCard title="Theme Rotation" subtitle="Test scenario trail - not live market intelligence." accentColor={Theme.colors.accent}><View style={styles.metricGrid}><MetricTile label="Parent Sector" value={theme.parentSector} /><MetricTile label="Relative Strength" value={theme.relativeStrength.toFixed(1)} /><MetricTile label="Relative Momentum" value={theme.relativeMomentum.toFixed(1)} /><MetricTile label="Quadrant" value={theme.quadrant} /></View></DashboardCard></View>; }

function Scanner({ title, subtitle, rows, empty = 'No sectors match this scanner.', onOpen }: { title: string; subtitle: string; rows: SectorRow[]; empty?: string; onOpen: (id: SectorId) => void }) { return <DashboardCard title={title} subtitle={subtitle} accentColor={Theme.colors.purple}>{rows.length ? rows.map((row) => <Pressable key={row.sectorId} onPress={() => onOpen(row.sectorId)} style={styles.row}><View><Text style={styles.name}>#{row.rank} {row.displayName}</Text><Text style={styles.note}>{row.etfSymbol} · {formatClassification(row.classification)}</Text></View><Text style={styles.value}>{row.compositeScore?.toFixed(2) ?? 'N/A'}</Text></Pressable>) : <Text style={styles.note}>{empty}</Text>}</DashboardCard>; }

function categoryForSection(section: ActiveSection): ActiveCategory { if (section.startsWith('themes') || section === 'themeAlerts') return 'themes'; if (section === 'emergingLeadership' || section === 'leadershipRisk') return 'signals'; return 'sectors'; }
function defaultSectionForCategory(category: ActiveCategory, current: ActiveSection): ActiveSection { if (categoryForSection(current) === category) return current; return category === 'themes' ? 'themesHeatmap' : category === 'signals' ? 'emergingLeadership' : 'sectorHeatmap'; }

const styles = StyleSheet.create({
  alert: { borderTopColor: Theme.colors.border, borderTopWidth: 1, gap: Spacing.half, paddingVertical: Spacing.two },
  badges: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.two },
  body: { color: Theme.colors.text, fontSize: 13 },
  categoryButton: { alignItems: 'center', borderRadius: Theme.radii.pill, flex: 1, justifyContent: 'center', minHeight: 36, paddingHorizontal: Spacing.two, paddingVertical: Spacing.one },
  categoryButtonActive: { backgroundColor: Theme.colors.accentSoft },
  categorySwitch: { backgroundColor: Theme.colors.backgroundMuted, borderColor: Theme.colors.border, borderRadius: Theme.radii.pill, borderWidth: 1, flexBasis: 210, flexDirection: 'row', flexGrow: 1, flexShrink: 1, gap: Spacing.half, minWidth: 0, padding: 3 },
  categoryText: { color: Theme.colors.textMuted, fontSize: 13, fontWeight: '900', textAlign: 'center' },
  categoryTextActive: { color: Theme.colors.accent },
  contentButton: { alignItems: 'center', borderBottomColor: 'transparent', borderBottomWidth: 2, flex: 1, justifyContent: 'center', minHeight: 38, paddingHorizontal: Spacing.one, paddingVertical: Spacing.one },
  contentButtonActive: { borderBottomColor: Theme.colors.accent },
  contentSwitch: { backgroundColor: Theme.colors.card, borderColor: Theme.colors.border, borderRadius: Theme.radii.small, borderWidth: 1, flexDirection: 'row', paddingHorizontal: Spacing.one },
  contentText: { color: Theme.colors.textMuted, fontSize: 12, fontWeight: '900', textAlign: 'center' },
  contentTextActive: { color: Theme.colors.accent },
  detailStack: { gap: Spacing.three },
  metricGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.two },
  name: { color: Theme.colors.text, fontSize: 14, fontWeight: '900' },
  navigation: { gap: Spacing.two },
  navigationTopRow: { alignItems: 'center', flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.two },
  note: { color: Theme.colors.textMuted, fontSize: 13, fontWeight: '700' },
  row: { alignItems: 'center', borderTopColor: Theme.colors.border, borderTopWidth: 1, flexDirection: 'row', justifyContent: 'space-between', paddingVertical: Spacing.two },
  pressed: { opacity: 0.78 },
  stack: { gap: Spacing.three },
  tab: { borderColor: Theme.colors.border, borderRadius: Theme.radii.small, borderWidth: 1, paddingHorizontal: Spacing.two, paddingVertical: Spacing.one },
  tabActive: { backgroundColor: Theme.colors.accentSoft, borderColor: Theme.colors.accent },
  tabs: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.one },
  tabText: { color: Theme.colors.textMuted, fontSize: 12, fontWeight: '800' },
  tabTextActive: { color: Theme.colors.accent },
  themeSource: { gap: Spacing.one, marginBottom: Spacing.two },
  utilityButton: { alignItems: 'center', backgroundColor: Theme.colors.card, borderColor: Theme.colors.border, borderRadius: Theme.radii.pill, borderWidth: 1, height: 40, justifyContent: 'center', width: 40 },
  utilityToolbar: { alignItems: 'center', alignSelf: 'flex-end', flexDirection: 'row', gap: Spacing.one, marginLeft: 'auto' },
  filterBadge: { alignItems: 'center', backgroundColor: Theme.colors.warning, borderRadius: Theme.radii.pill, height: 18, justifyContent: 'center', minWidth: 18, paddingHorizontal: 5, position: 'absolute', right: -5, top: -5 },
  filterBadgeText: { color: Theme.colors.background, fontSize: 10, fontWeight: '900' },
  flow: { borderTopColor: Theme.colors.border, borderTopWidth: 1, gap: Spacing.half, paddingTop: Spacing.two },
  flowTitle: { color: Theme.colors.text, fontSize: 13, fontWeight: '900' },
  value: { color: Theme.colors.accent, fontSize: 16, fontWeight: '900' },
});
