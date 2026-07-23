import { useCallback, useMemo, useState } from 'react';
import { useFocusEffect, useLocalSearchParams, useRouter } from 'expo-router';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { buildEntityDestination } from '@/architecture/entityRoutingRegistry';
import { DashboardCard } from '@/components/cards/DashboardCard';
import { AppButton } from '@/components/ui/AppButton';
import { AppIcon } from '@/components/ui/AppIcon';
import { AppScreen } from '@/components/ui/AppScreen';
import { DetailModal } from '@/components/ui/DetailModal';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { SegmentedControl } from '@/components/ui/SegmentedControl';
import { SkeletonCard } from '@/components/ui/SkeletonCard';
import { StockCard } from '@/components/watchlist/StockCard';
import { Spacing, Theme, Typography } from '@/constants/theme';
import { createCopilotContext } from '@/features/copilot/context/buildScreenContext';
import { WatchlistCatalystsCard } from '@/features/context-intelligence/components/ContextIntelligenceCards';
import { shouldRequestWatchlistCatalysts } from '@/features/context-intelligence/consumerPolicy';
import { normalizeSectorId, type SectorId } from '@/features/sectors/sectorSnapshot';
import { WatchlistSection } from '@/features/watchlist/components/WatchlistSection';
import { WatchlistBrief } from '@/features/watchlist/components/WatchlistSummary';
import { WatchlistListControls } from '@/features/watchlist/components/WatchlistListControls';
import { buildWatchlistKey, useWatchlist, type GroupWatchlistItem } from '@/features/watchlist/store';
import { classifyWatchlistItem } from '@/features/watchlist/watchlistClassifier';
import {
  groupWatchlistDecisionItems,
  WATCHLIST_DECISION_ORDER,
  type WatchlistDecisionGroup,
} from '@/features/watchlist/watchlistDecision';
import {
  DEFAULT_LIST_CONTROL_PREFERENCES,
  filterAndSortSectors,
  filterAndSortStocks,
  filterAndSortThemes,
  getFlatStockSortDescription,
  getStockSortOptions,
  isGroupedStockSort,
  SECTOR_FILTER_OPTIONS,
  SECTOR_SORT_OPTIONS,
  STOCK_FILTER_OPTIONS,
  THEME_FILTER_OPTIONS,
  THEME_SORT_OPTIONS,
  type ListControlPreferences,
  type WatchlistListFilter,
  type WatchlistViewMode,
} from '@/features/watchlist/watchlistListControls';
import { useWatchlistUiPreferences } from '@/features/watchlist/watchlistUiPreferences';
import type { ClassifiedWatchlistItem, WatchlistGroup } from '@/features/watchlist/types';
import { buildWatchlistCountModel } from '@/features/watchlist/watchlistCounts';
import { useWatchlistDashboard } from '@/hooks/useWatchlistDashboard';
import { useSectorSnapshot } from '@/hooks/useSectorSnapshot';
import { useThemeSnapshot } from '@/hooks/useThemeSnapshot';
import type { LiveThemeItem } from '@/features/themes/themeSnapshot';
import type { WatchlistSummaryItem } from '@/types/market';

type WatchlistTab = 'stocks' | 'sectors' | 'themes';

const WATCHLIST_TABS = [
  { key: 'stocks', label: 'Stocks' },
  { key: 'sectors', label: 'Sectors' },
  { key: 'themes', label: 'Themes' },
];
const DECISION_COLLAPSE_KEYS: Record<WatchlistDecisionGroup, WatchlistGroup> = {
  action_now: 'high_priority',
  improving: 'momentum',
  weakening: 'needs_attention',
  monitor: 'watching',
};

export default function WatchlistScreen() {
  const router = useRouter();
  const {
    actionNonce: actionNonceParam,
    detailTab: detailTabParam,
    section: sectionParam,
    symbol: requestedSymbolParam,
  } = useLocalSearchParams<{
    actionNonce?: string | string[];
    detailTab?: string | string[];
    section?: string | string[];
    symbol?: string | string[];
  }>();
  const requestedSymbol = normalizeSymbol(Array.isArray(requestedSymbolParam) ? requestedSymbolParam[0] ?? '' : requestedSymbolParam ?? '');
  const requestedDetailTab = Array.isArray(detailTabParam) ? detailTabParam[0] : detailTabParam;
  const actionNonce = Array.isArray(actionNonceParam) ? actionNonceParam[0] : actionNonceParam;
  const requestedTab = firstWatchlistTab(sectionParam);
  const [isFocused, setIsFocused] = useState(false);
  const [localTab, setLocalTab] = useState<WatchlistTab>('stocks');
  const activeTab = requestedSymbol ? 'stocks' : requestedTab ?? localTab;
  const [searchText, setSearchText] = useState('');
  const [addPanelOpen, setAddPanelOpen] = useState(false);
  const [removedSymbols, setRemovedSymbols] = useState<string[]>([]);
  const [inputError, setInputError] = useState<string | null>(null);
  const watchlistStore = useWatchlist();
  const [watchlistPreferences, updateWatchlistPreferences] = useWatchlistUiPreferences();
  const {
    collapsedGroups,
  } = watchlistPreferences;
  const {
    snapshot: sectorSnapshot,
    loading: sectorsLoading,
    error: sectorsError,
    refetch: refetchSectors,
  } = useSectorSnapshot(activeTab === 'sectors');
  const {
    snapshot: themeSnapshot,
    loading: themesLoading,
    error: themesError,
    refetch: refetchThemes,
  } = useThemeSnapshot(activeTab === 'themes');

  useFocusEffect(
    useCallback(() => {
      setIsFocused(true);
      return () => setIsFocused(false);
    }, []),
  );

  const requestedStockSymbols = useMemo(
    () => Array.from(new Set([
      ...watchlistStore.stockItems.map((item) => item.ticker),
      ...(requestedSymbol ? [requestedSymbol] : []),
    ])).sort(),
    [requestedSymbol, watchlistStore.stockItems],
  );
  const intelligenceSymbols = useMemo(
    () => Array.from(new Set(
      watchlistStore.stockItems
        .map((item) => item.ticker.trim().toUpperCase())
        .filter(Boolean),
    )).sort(),
    [watchlistStore.stockItems],
  );
  const intelligenceSymbolKey = intelligenceSymbols.join(',');
  const { error, loading, refetch, watchlist } = useWatchlistDashboard(requestedStockSymbols, isFocused && activeTab === 'stocks');
  const savedItems = useMemo(
    () => mergeWatchlistItems(watchlist?.items ?? [], watchlistStore.stockItems, removedSymbols),
    [removedSymbols, watchlist, watchlistStore.stockItems],
  );
  const query = normalizeSymbol(searchText);
  const classifiedStockItems = useMemo<ClassifiedWatchlistItem[]>(
    () => savedItems.map((item, originalIndex) => ({
      classification: classifyWatchlistItem(item),
      item,
      originalIndex,
    })),
    [savedItems],
  );
  const canAdd = query.length > 0 && !savedItems.some((item) => item.ticker === query);
  const countModel = useMemo(() => buildWatchlistCountModel({
    locallySavedSymbols: watchlistStore.stockItems.map((item) => item.ticker),
    displayedItems: savedItems,
    catalystSymbols: intelligenceSymbols,
  }), [intelligenceSymbols, savedItems, watchlistStore.stockItems]);

  const savedSectors = useMemo(() => watchlistStore.groupItems
    .filter((item) => item.type === 'sector')
    .map((stored) => ({ stored, sectorId: normalizeSectorId(stored.id) ?? normalizeSectorId(stored.name) }))
    .filter((item): item is { stored: GroupWatchlistItem; sectorId: SectorId } => item.sectorId !== null)
    .map((item) => ({ ...item, row: sectorSnapshot?.sectors.find((row) => row.sectorId === item.sectorId) ?? null })), [sectorSnapshot, watchlistStore.groupItems]);
  const savedThemes = useMemo(() => watchlistStore.groupItems
    .filter((item) => item.type === 'theme')
    .map((stored) => ({
      stored,
      row: themeSnapshot?.items.find((item) => item.id === stored.id || item.name.toLowerCase() === stored.name.toLowerCase()) ?? null,
    })), [themeSnapshot, watchlistStore.groupItems]);
  const stockSortOptions = useMemo(() => getStockSortOptions(classifiedStockItems), [classifiedStockItems]);
  const stockPreferences = useMemo(() => normalizeAvailableSort(
    watchlistPreferences.listControls.stocks,
    stockSortOptions,
    DEFAULT_LIST_CONTROL_PREFERENCES.stocks,
  ), [stockSortOptions, watchlistPreferences.listControls.stocks]);
  const sectorPreferences = watchlistPreferences.listControls.sectors;
  const themePreferences = watchlistPreferences.listControls.themes;
  const sortedClassifiedItems = useMemo(
    () => filterAndSortStocks(classifiedStockItems, stockPreferences),
    [classifiedStockItems, stockPreferences],
  );
  const sortedSectors = useMemo(
    () => filterAndSortSectors(savedSectors, sectorPreferences),
    [savedSectors, sectorPreferences],
  );
  const sortedThemes = useMemo(
    () => filterAndSortThemes(savedThemes, themePreferences),
    [savedThemes, themePreferences],
  );
  const decisionGroups = useMemo(
    () => groupWatchlistDecisionItems(sortedClassifiedItems),
    [sortedClassifiedItems],
  );
  const activePreferences = activeTab === 'stocks' ? stockPreferences : activeTab === 'sectors' ? sectorPreferences : themePreferences;
  const activeSortOptions = activeTab === 'stocks' ? stockSortOptions : activeTab === 'sectors' ? SECTOR_SORT_OPTIONS : THEME_SORT_OPTIONS;
  const activeFilterOptions = activeTab === 'stocks' ? STOCK_FILTER_OPTIONS : activeTab === 'sectors' ? SECTOR_FILTER_OPTIONS : THEME_FILTER_OPTIONS;
  const activeTotalCount = activeTab === 'stocks' ? classifiedStockItems.length : activeTab === 'sectors' ? savedSectors.length : savedThemes.length;
  const activeResultCount = activeTab === 'stocks' ? sortedClassifiedItems.length : activeTab === 'sectors' ? sortedSectors.length : sortedThemes.length;
  const getFilteredResultCount = useCallback((filters: WatchlistListFilter[]) => {
    if (activeTab === 'stocks') return filterAndSortStocks(classifiedStockItems, { ...stockPreferences, filters }).length;
    if (activeTab === 'sectors') return filterAndSortSectors(savedSectors, { ...sectorPreferences, filters }).length;
    return filterAndSortThemes(savedThemes, { ...themePreferences, filters }).length;
  }, [activeTab, classifiedStockItems, savedSectors, savedThemes, sectorPreferences, stockPreferences, themePreferences]);
  const copilotContext = useMemo(
    () => createCopilotContext({
      payload: {
        activeTab,
        groupCounts: activeTab === 'stocks'
          ? WATCHLIST_DECISION_ORDER.reduce<Record<string, number>>((acc, group) => {
            acc[group] = decisionGroups[group].length;
            return acc;
          }, {})
          : activeTab === 'sectors'
            ? { saved_sectors: savedSectors.length }
            : { saved_themes: savedThemes.length },
        items: activeTab === 'stocks'
          ? sortedClassifiedItems.map(({ classification, item }) => ({
            changePercent: item.change_percent,
            risk: item.risk_flag,
            score: classification.score,
            signal: classification.primarySignal,
            ticker: item.ticker,
            group: classification.group,
          }))
          : activeTab === 'sectors'
            ? savedSectors.map(({ row, stored }) => ({ id: row?.sectorId ?? stored.id, name: row?.displayName ?? stored.name, score: row?.compositeScore, signal: row?.classification, type: 'sector' }))
            : savedThemes.map(({ row, stored }) => ({ id: row?.id ?? stored.id, name: row?.name ?? stored.name, score: row?.compositeScore, signal: row?.classification, type: 'theme' })),
        sortMode: activePreferences.sort,
      },
      routeName: '/watchlist',
      screenTitle: activeTab === 'stocks' ? 'Watchlist Stocks' : activeTab === 'sectors' ? 'Watchlist Sectors' : 'Watchlist Themes',
      screenType: 'watchlist',
      sourceState: activeTab === 'stocks'
        ? 'mixed'
        : activeTab === 'sectors'
          ? sectorSnapshot?.sourceState ?? 'unavailable'
          : themeSnapshot?.sourceState ?? 'unavailable',
    }),
    [activePreferences.sort, activeTab, decisionGroups, savedSectors, savedThemes, sectorSnapshot?.sourceState, sortedClassifiedItems, themeSnapshot?.sourceState],
  );

  const addSymbol = () => {
    if (!query) {
      setInputError('Enter a ticker symbol.');
      return;
    }
    if (!isValidSymbol(query)) {
      setInputError('Use letters, numbers, or dot only.');
      return;
    }
    if (!canAdd) {
      setInputError(`${query} is already on the watchlist.`);
      return;
    }
    watchlistStore.addStock(query);
    setRemovedSymbols((current) => current.filter((symbol) => symbol !== query));
    setInputError(null);
    setSearchText('');
  };

  const removeSymbol = (symbol: string) => {
    watchlistStore.removeStock(symbol);
    setRemovedSymbols((current) => (current.includes(symbol) ? current : [...current, symbol]));
  };

  const removeGroup = (item: GroupWatchlistItem) => {
    if (item.type === 'sector') {
      watchlistStore.removeSector(item.id);
    } else {
      watchlistStore.removeTheme(item.id);
    }
  };

  const toggleGroupCollapsed = (group: WatchlistDecisionGroup) => {
    const preferenceKey = DECISION_COLLAPSE_KEYS[group];
    updateWatchlistPreferences({
      collapsedGroups: {
        [preferenceKey]: !collapsedGroups[preferenceKey],
      },
    });
  };

  return (
    <AppScreen
      copilotContext={copilotContext}
      copilotPrompt={activeTab === 'stocks'
        ? 'Rank my watchlist and explain which name needs attention.'
        : activeTab === 'sectors'
          ? 'Explain my saved sectors using the current market snapshot.'
          : 'Explain my saved themes using the current theme snapshot.'}
      title="Watchlist"
      subtitle="Saved stocks, sectors, and themes.">
      <View style={styles.stack}>
        <View style={styles.topControlRow}>
          <View style={styles.tabSwitchWrap}>
            <SegmentedControl
              fullWidth
              onChange={(key) => {
                router.setParams({ commandTarget: undefined, section: undefined, symbol: undefined });
                setLocalTab(key as WatchlistTab);
                setAddPanelOpen(false);
              }}
              options={WATCHLIST_TABS}
              selectedKey={activeTab}
              variant="switch"
            />
          </View>
          <AddHeaderAction
            activeCategory={activeTab}
            open={addPanelOpen}
            onToggle={() => setAddPanelOpen((current) => !current)}
          />
        </View>

        <WatchlistListControls
          activeCategory={activeTab}
          activeFilters={activePreferences.filters}
          availableFilterOptions={activeFilterOptions}
          availableSortOptions={activeSortOptions}
          currentSort={activePreferences.sort}
          getResultCount={getFilteredResultCount}
          onApply={(nextPreferences) => updateWatchlistPreferences({
            listControls: { [activeTab]: nextPreferences },
          })}
          onReset={() => updateWatchlistPreferences({
            listControls: {
              [activeTab]: { ...DEFAULT_LIST_CONTROL_PREFERENCES[activeTab], filters: [] },
            },
          })}
          resultCount={activeResultCount}
          totalCount={activeTotalCount}
          viewMode={activePreferences.viewMode}
        />

        {activeTab === 'stocks' ? (
          <>
            {classifiedStockItems.length ? <WatchlistBrief counts={countModel} items={classifiedStockItems} /> : null}
            <WatchlistCatalystsCard
              enabled={shouldRequestWatchlistCatalysts({
                activeTab,
                focused: isFocused,
                hydrated: watchlistStore.hydrated,
                symbolCount: intelligenceSymbols.length,
              })}
              key={intelligenceSymbolKey}
              scopeExplanation={countModel.catalystScopeExplanation}
              symbols={intelligenceSymbols}
            />

            {loading ? (
              <WatchlistSkeleton />
            ) : (
              <>
                {error ? (
                  <ErrorState
                    title="Watchlist unavailable"
                    message={error}
                    onRetry={refetch}
                  />
                ) : null}

                {addPanelOpen ? (
                  <DashboardCard style={styles.compactControlCard}>
                    <StockAddPanel
                      canAdd={canAdd}
                      inputError={inputError}
                      onAdd={addSymbol}
                      onQueryChange={(value) => {
                        setSearchText(value);
                        setInputError(null);
                      }}
                      query={searchText}
                    />
                  </DashboardCard>
                ) : null}

                {isGroupedStockSort(stockPreferences.sort) ? (
                  <View style={styles.stack}>
                    {WATCHLIST_DECISION_ORDER.map((group) => {
                      const collapseKey = DECISION_COLLAPSE_KEYS[group];
                      return (
                      <WatchlistSection
                        collapsed={Boolean(collapsedGroups[collapseKey])}
                        group={group}
                        items={decisionGroups[group]}
                        key={group}
                        onToggleCollapsed={() => toggleGroupCollapsed(group)}>
                        {decisionGroups[group].map(({ classification, item }) => (
                          <StockCard
                            classification={classification}
                            key={item.ticker}
                            onRemove={removeSymbol}
                            openDetailTab={requestedDetailTab}
                            openDetails={requestedSymbol === item.ticker}
                            deepLinkNonce={actionNonce}
                            stock={item}
                            viewMode={stockPreferences.viewMode}
                          />
                        ))}
                      </WatchlistSection>
                      );
                    })}
                  </View>
                ) : (
                  <View style={styles.flatResults}>
                    <Text style={styles.flatDescriptor}>{getFlatStockSortDescription(stockPreferences.sort)}</Text>
                    {sortedClassifiedItems.map(({ classification, item }) => (
                      <StockCard
                        classification={classification}
                        key={item.ticker}
                        onRemove={removeSymbol}
                        openDetailTab={requestedDetailTab}
                        openDetails={requestedSymbol === item.ticker}
                        deepLinkNonce={actionNonce}
                        stock={item}
                        viewMode={stockPreferences.viewMode}
                      />
                    ))}
                  </View>
                )}

                {!error && savedItems.length === 0 ? (
                  <EmptyState
                    stateType="no_saved_entities"
                    title="No stock watchlist items"
                    message="Use the add and sort control, or save a stock from sector and theme detail views."
                  />
                ) : null}

                {!error && savedItems.length > 0 && sortedClassifiedItems.length === 0 ? (
                  <EmptyState
                    actionLabel="Clear filters"
                    title="No saved items match these filters."
                    message="Clear all active filters above or adjust the current filter selection."
                    onAction={() => updateWatchlistPreferences({
                      listControls: { stocks: { ...stockPreferences, filters: [] } },
                    })}
                    stateType="no_qualifying_results"
                  />
                ) : null}

              </>
            )}
          </>
        ) : activeTab === 'sectors' ? (
          <View style={styles.stack}>
            {!watchlistStore.hydrated || sectorsLoading ? (
              <SkeletonCard compact rows={2} title />
            ) : (
              <View style={styles.stack}>
                {sortedSectors.map(({ stored, sectorId, row }) => (
                  <SavedGroupCard
                    key={buildWatchlistKey('sector', sectorId)}
                    onOpen={() => router.push(buildEntityDestination('sector', {
                      entityId: sectorId,
                      entityName: row?.displayName ?? stored.name,
                    }) as never)}
                    onRemove={() => removeGroup(stored)}
                    subtitle={row ? `#${row.rank} · ${row.etfSymbol} · ${row.classification}` : 'Sector snapshot unavailable'}
                    title={row?.displayName ?? stored.name}
                    value={row?.compositeScore?.toFixed(1) ?? 'N/A'}
                    viewMode={sectorPreferences.viewMode}
                  />
                ))}
              </View>
            )}

            {watchlistStore.hydrated && !watchlistStore.groupItems.some((item) => item.type === 'sector') ? (
              <EmptyState
                actionLabel="Browse sectors"
                title="No saved sectors"
                message="Open the Sectors tab and save a sector to track it here."
                onAction={() => router.push('/sectors')}
                stateType="no_saved_entities"
              />
            ) : null}
            {watchlistStore.hydrated && savedSectors.length > 0 && sortedSectors.length === 0 ? (
              <EmptyState
                actionLabel="Clear filters"
                title="No saved items match these filters."
                message="Clear all active filters above or adjust the current filter selection."
                onAction={() => updateWatchlistPreferences({
                  listControls: { sectors: { ...sectorPreferences, filters: [] } },
                })}
                stateType="no_qualifying_results"
              />
            ) : null}
          </View>
        ) : (
          <View style={styles.stack}>
            {themesError ? <ErrorState title="Themes unavailable" message={themesError} /> : null}
            {!watchlistStore.hydrated || themesLoading ? (
              <SkeletonCard compact rows={2} title />
            ) : (
              <View style={styles.stack}>
                {sortedThemes.map(({ stored, row }) => (
                  <SavedGroupCard
                    key={buildWatchlistKey('theme', stored.id)}
                    onOpen={() => router.push(buildEntityDestination('theme', {
                      entityId: row?.id ?? stored.id,
                      entityName: row?.name ?? stored.name,
                    }) as never)}
                    onRemove={() => removeGroup(stored)}
                    subtitle={row ? `${row.parentSector} · ${row.classification} · ${formatThemeReturn(row)}` : 'Theme snapshot unavailable'}
                    title={row?.name ?? stored.name}
                    value={row?.rank ? `#${row.rank}` : 'N/A'}
                    viewMode={themePreferences.viewMode}
                  />
                ))}
              </View>
            )}
            {watchlistStore.hydrated && !watchlistStore.groupItems.some((item) => item.type === 'theme') ? (
              <EmptyState
                actionLabel="Browse themes"
                title="No saved themes"
                message="Open the Themes view and save a reviewed theme to track it here."
                onAction={() => router.push('/sectors')}
                stateType="no_saved_entities"
              />
            ) : null}
            {watchlistStore.hydrated && savedThemes.length > 0 && sortedThemes.length === 0 ? (
              <EmptyState
                actionLabel="Clear filters"
                title="No saved items match these filters."
                message="Clear all active filters above or adjust the current filter selection."
                onAction={() => updateWatchlistPreferences({
                  listControls: { themes: { ...themePreferences, filters: [] } },
                })}
                stateType="no_qualifying_results"
              />
            ) : null}
          </View>
        )}
      </View>

      <DetailModal
        onClose={() => setAddPanelOpen(false)}
        subtitle={activeTab === 'sectors'
          ? 'Choose from the current sector snapshot.'
          : 'Choose from the reviewed theme snapshot.'}
        title={activeTab === 'sectors' ? 'Add sector' : 'Add theme'}
        visible={addPanelOpen && activeTab !== 'stocks'}>
        {activeTab === 'sectors' ? (
          sectorsError ? (
            <ErrorState title="Sectors unavailable" message={sectorsError} onRetry={refetchSectors} />
          ) : sectorsLoading || !sectorSnapshot ? (
            <SkeletonCard compact rows={3} title />
          ) : (
            <GroupAddPicker
              emptyMessage="All available sectors are already saved."
              items={sectorSnapshot.sectors
                .filter((row) => !watchlistStore.isInWatchlist('sector', row.sectorId))
                .map((row) => ({
                  id: row.sectorId,
                  meta: `${row.etfSymbol} · #${row.rank} · ${row.classification}`,
                  name: row.displayName,
                }))}
              onAdd={(id, name) => watchlistStore.addSector(id, name)}
            />
          )
        ) : themesError ? (
          <ErrorState title="Themes unavailable" message={themesError} onRetry={refetchThemes} />
        ) : themesLoading || !themeSnapshot ? (
          <SkeletonCard compact rows={3} title />
        ) : (
          <GroupAddPicker
            emptyMessage="All available themes are already saved."
            items={themeSnapshot.items
              .filter((item) => !watchlistStore.isInWatchlist('theme', item.id))
              .map((item) => ({
                id: item.id,
                meta: `${item.parentSector} · ${item.rank ? `#${item.rank} · ` : ''}${item.classification}`,
                name: item.name,
              }))}
            onAdd={(id, name) => watchlistStore.addTheme(id, name)}
          />
        )}
      </DetailModal>
    </AppScreen>
  );
}

function AddHeaderAction({
  activeCategory,
  onToggle,
  open,
}: {
  activeCategory: WatchlistTab;
  onToggle: () => void;
  open: boolean;
}) {
  return (
    <View style={styles.stockActionRow}>
      <IconButton
        active={open}
        accessibilityLabel={activeCategory === 'stocks'
          ? 'Open add ticker panel'
          : `Open add ${activeCategory === 'sectors' ? 'sector' : 'theme'} panel`}
        onPress={onToggle}
      />
    </View>
  );
}

function GroupAddPicker({
  emptyMessage,
  items,
  onAdd,
}: {
  emptyMessage: string;
  items: { id: string; meta: string; name: string }[];
  onAdd: (id: string, name: string) => void;
}) {
  if (!items.length) {
    return <EmptyState stateType="empty" title="Everything is saved" message={emptyMessage} />;
  }
  return (
    <View style={styles.addPickerList}>
      {items.map((item) => (
        <Pressable
          accessibilityLabel={`Add ${item.name} to watchlist`}
          accessibilityRole="button"
          key={item.id}
          onPress={() => onAdd(item.id, item.name)}
          style={({ pressed }) => [styles.addPickerRow, pressed && styles.pressedButton]}>
          <View style={styles.addPickerText}>
            <Text numberOfLines={1} style={styles.addPickerName}>{item.name}</Text>
            <Text numberOfLines={1} style={styles.addPickerMeta}>{item.meta}</Text>
          </View>
          <View style={styles.addPickerButton}>
            <AppIcon name="add" size={17} />
          </View>
        </Pressable>
      ))}
    </View>
  );
}

function IconButton({
  accessibilityLabel,
  active,
  onPress,
}: {
  accessibilityLabel: string;
  active: boolean;
  onPress: () => void;
}) {
  return (
    <AppButton
      accessibilityLabel={accessibilityLabel}
      accessibilityState={{ selected: active }}
      label={accessibilityLabel}
      leadingIcon={<AppIcon color={active ? Theme.colors.accent : Theme.colors.textMuted} name="add" size={17} />}
      onPress={onPress}
      style={[styles.iconButton, active && styles.iconButtonActive]}
      variant="icon"
    />
  );
}

function StockAddPanel({
  canAdd,
  inputError,
  onAdd,
  onQueryChange,
  query,
}: {
  canAdd: boolean;
  inputError: string | null;
  onAdd: () => void;
  onQueryChange: (value: string) => void;
  query: string;
}) {
  return (
    <View style={styles.searchPanel}>
      <View style={styles.searchRow}>
        <TextInput
          accessibilityLabel="Add ticker"
          autoCapitalize="characters"
          autoCorrect={false}
          onChangeText={(value) => onQueryChange(value.toUpperCase())}
          onSubmitEditing={onAdd}
          placeholder="Add ticker"
          placeholderTextColor={Theme.colors.textMuted}
          returnKeyType="done"
          style={styles.searchInput}
          value={query}
        />
        <AppButton
          accessibilityLabel="Add ticker to stock watchlist"
          disabled={!canAdd}
          label="Add ticker"
          leadingIcon={<AppIcon name="add" size={18} />}
          onPress={onAdd}
          style={styles.addTickerButton}
          variant="icon"
        />
      </View>
      {inputError ? <Text style={styles.errorText}>{inputError}</Text> : null}
    </View>
  );
}

function SavedGroupCard({
  onOpen,
  onRemove,
  subtitle,
  title,
  value,
  viewMode,
}: {
  onOpen: () => void;
  onRemove: () => void;
  subtitle: string;
  title: string;
  value: string;
  viewMode: WatchlistViewMode;
}) {
  const compact = viewMode === 'compact';
  return (
    <DashboardCard style={compact ? { ...styles.savedGroupCard, ...styles.savedGroupCardCompact } : styles.savedGroupCard}>
      <View style={styles.savedGroupRow}>
      <Pressable accessibilityLabel={`Open ${title}`} accessibilityRole="button" onPress={onOpen} style={[styles.summaryHeaderRow, compact && styles.summaryHeaderRowCompact]}>
        <View style={styles.savedGroupText}>
          <Text numberOfLines={1} style={styles.summaryTitle}>{title}</Text>
          <Text numberOfLines={compact ? 1 : 2} style={styles.summarySubtitle}>{compact ? compactGroupSubtitle(subtitle) : subtitle}</Text>
        </View>
        <Text style={styles.summaryCount}>{value}</Text>
        <AppIcon name="chevronRight" size={17} />
      </Pressable>
      <Pressable accessibilityLabel={`Remove ${title} from watchlist`} accessibilityRole="button" hitSlop={8} onPress={onRemove} style={styles.savedStateButton}>
        <AppIcon color={Theme.colors.warning} name="saved" size={17} />
      </Pressable>
      </View>
    </DashboardCard>
  );
}

function compactGroupSubtitle(subtitle: string) {
  const parts = subtitle.split(' · ');
  return parts.find((part) => ['Leading', 'Improving', 'Neutral', 'Weakening', 'Lagging'].includes(part))
    ?? parts.at(-1)
    ?? subtitle;
}

function formatThemeReturn(theme: LiveThemeItem) {
  const value = theme.returns['1M'];
  if (value === null) return '1M N/A';
  return `1M ${value > 0 ? '+' : ''}${value.toFixed(1)}%`;
}

function mergeWatchlistItems(
  backendItems: WatchlistSummaryItem[],
  stockItems: { ticker: string; name?: string }[],
  removedSymbols: string[],
) : WatchlistSummaryItem[] {
  const removed = new Set(removedSymbols);
  const bySymbol = new Map<string, WatchlistSummaryItem>();
  backendItems.forEach((item) => {
    if (!removed.has(item.ticker)) {
      bySymbol.set(item.ticker, item);
    }
  });
  stockItems.forEach((item) => {
    const symbol = item.ticker.toUpperCase();
    if (!removed.has(symbol) && !bySymbol.has(symbol)) {
      bySymbol.set(symbol, {
        ticker: symbol,
        trend: 'Preparing analysis',
        setup: item.name ? `${item.name} saved from watchlist; analysis is preparing.` : 'Preparing analysis snapshot.',
        support_zone: 'N/A',
        risk_flag: 'N/A',
        price: null,
        change_percent: null,
        data_source: 'unavailable',
        is_live: false,
        is_stale: false,
        fallback_used: false,
        as_of: null,
        overall_status: 'pending',
        status_reason_code: 'snapshot_missing',
        status_reason: 'Preparing analysis snapshot.',
        quote_status: 'unavailable',
        analysis_status: 'initializing',
        retryable: true,
        refreshing: true,
        available_fields: [],
        missing_fields: ['chart', 'rating', 'risk', 'trend'],
      });
    }
  });
  return [...bySymbol.values()];
}

function normalizeSymbol(value: string) {
  return value.trim().toUpperCase();
}

function firstWatchlistTab(value: string | string[] | undefined): WatchlistTab | null {
  const tab = Array.isArray(value) ? value[0] : value;
  if (tab === 'groups') return 'sectors';
  return tab === 'stocks' || tab === 'sectors' || tab === 'themes' ? tab : null;
}

function isValidSymbol(value: string) {
  return /^[A-Z0-9.]{1,10}$/.test(value);
}

function normalizeAvailableSort(
  preferences: ListControlPreferences,
  options: { key: string }[],
  defaults: ListControlPreferences,
) {
  return options.some((option) => option.key === preferences.sort)
    ? preferences
    : { ...preferences, sort: defaults.sort };
}

function WatchlistSkeleton() {
  return (
    <View style={styles.list}>
      {Array.from({ length: 5 }).map((_, index) => (
        <SkeletonCard key={index} compact rows={2} />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  addPickerButton: {
    alignItems: 'center',
    backgroundColor: Theme.colors.accentSoft,
    borderColor: Theme.colors.accent,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    height: 44,
    justifyContent: 'center',
    width: 44,
  },
  addPickerIcon: {
    color: Theme.colors.accent,
    fontSize: Typography.scoreTitle.fontSize,
    fontWeight: Typography.weights.strong,
    lineHeight: 22,
  },
  addPickerList: {
    gap: Spacing.one,
  },
  addPickerMeta: {
    color: Theme.colors.textMuted,
    fontSize: Typography.caption.fontSize,
    fontWeight: Typography.weights.emphasis,
  },
  addPickerName: {
    color: Theme.colors.text,
    fontSize: Typography.body.fontSize,
    fontWeight: Typography.weights.strong,
  },
  addPickerRow: {
    alignItems: 'center',
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    flexDirection: 'row',
    gap: Spacing.two,
    minHeight: 58,
    paddingHorizontal: Spacing.two,
    paddingVertical: Spacing.one,
  },
  addPickerText: {
    flex: 1,
    gap: Spacing.half,
    minWidth: 0,
  },
  addTickerButton: {
    alignItems: 'center',
    backgroundColor: Theme.colors.accent,
    borderRadius: Theme.radii.small,
    height: 44,
    justifyContent: 'center',
    width: 44,
  },
  addTickerText: {
    color: Theme.colors.text,
    fontSize: Typography.decisionState.fontSize,
    fontWeight: Typography.weights.strong,
    lineHeight: 24,
  },
  compactControlCard: {
    padding: Spacing.twoAndHalf,
  },
  disabledButton: {
    backgroundColor: Theme.colors.cardMuted,
    opacity: 0.6,
  },
  errorText: {
    color: Theme.colors.warning,
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.strong,
  },
  flatDescriptor: {
    color: Theme.colors.textMuted,
    fontSize: Typography.caption.fontSize,
    fontWeight: Typography.weights.strong,
    lineHeight: 16,
    marginBottom: Spacing.half,
  },
  flatResults: {
    gap: Spacing.one,
  },
  groupChevron: {
    color: Theme.colors.textMuted,
    fontSize: Typography.decisionHero.fontSize,
    fontWeight: Typography.weights.strong,
  },
  iconButton: {
    alignItems: 'center',
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    height: 44,
    justifyContent: 'center',
    width: 44,
  },
  iconButtonActive: {
    backgroundColor: Theme.colors.accentSoft,
    borderColor: Theme.colors.accent,
  },
  list: {
    gap: Spacing.two,
  },
  pressedButton: {
    opacity: 0.78,
  },
  searchInput: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    color: Theme.colors.text,
    flex: 1,
    fontSize: Typography.bodyLarge.fontSize,
    fontWeight: Typography.weights.strong,
    minHeight: 44,
    paddingHorizontal: Spacing.twoAndHalf,
  },
  searchPanel: {
    gap: Spacing.two,
  },
  searchRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
  },
  savedGroupCard: {
    padding: Spacing.twoAndHalf,
  },
  savedGroupCardCompact: {
    paddingVertical: Spacing.one,
  },
  savedGroupRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.one,
  },
  savedGroupText: {
    flex: 1,
    gap: Spacing.half,
    minWidth: 0,
  },
  stack: {
    gap: Spacing.three,
  },
  summaryCount: {
    color: Theme.colors.accent,
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.strong,
  },
  summaryHeaderRow: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
    flex: 1,
    minHeight: 44,
    minWidth: 0,
  },
  summaryHeaderRowCompact: {
    alignItems: 'center',
  },
  savedStateButton: {
    alignItems: 'center',
    borderRadius: Theme.radii.pill,
    height: 44,
    justifyContent: 'center',
    width: 44,
  },
  savedStateIcon: {
    color: Theme.colors.warning,
    fontSize: Typography.cardTitle.fontSize,
    fontWeight: Typography.weights.strong,
  },
  summaryMetric: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    flex: 1,
    minWidth: 0,
    paddingHorizontal: Spacing.one,
    paddingVertical: Spacing.one,
  },
  summaryMetricLabel: {
    color: Theme.colors.textMuted,
    fontSize: Typography.caption.fontSize,
    fontWeight: Typography.weights.strong,
    textTransform: 'uppercase',
  },
  summaryMetricRow: {
    flexDirection: 'row',
    gap: Spacing.one,
  },
  summaryMetricValue: {
    fontSize: Typography.control.fontSize,
    fontWeight: Typography.weights.strong,
    marginTop: Spacing.half,
  },
  summarySubtitle: {
    color: Theme.colors.textMuted,
    fontSize: Typography.caption.fontSize,
    fontWeight: Typography.weights.emphasis,
    lineHeight: 15,
  },
  summaryTitle: {
    color: Theme.colors.text,
    fontSize: Typography.body.fontSize,
    fontWeight: Typography.weights.strong,
  },
  stockActionRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.one,
  },
  tabSwitchWrap: {
    flex: 1,
    minWidth: 0,
  },
  topControlRow: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
  },
  webToolbarIcon: {
    color: Theme.colors.textMuted,
    fontSize: Typography.detailTitle.fontSize,
    fontWeight: Typography.weights.strong,
  },
  webToolbarIconActive: {
    color: Theme.colors.accent,
  },
});
