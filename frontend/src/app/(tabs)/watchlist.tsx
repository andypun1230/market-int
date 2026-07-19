import { useCallback, useMemo, useState } from 'react';
import { useFocusEffect } from 'expo-router';
import { SymbolView } from 'expo-symbols';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { AppScreen } from '@/components/ui/AppScreen';
import { DetailModal } from '@/components/ui/DetailModal';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { SegmentedControl } from '@/components/ui/SegmentedControl';
import { SkeletonCard } from '@/components/ui/SkeletonCard';
import { StockCard } from '@/components/watchlist/StockCard';
import { Spacing, Theme } from '@/constants/theme';
import { AskCopilotButton } from '@/features/copilot/components/AskCopilotButton';
import { createCopilotContext } from '@/features/copilot/context/buildScreenContext';
import { SectorDetailContent } from '@/features/sectors/components/SectorDetailContent';
import { normalizeSectorId, type SectorId } from '@/features/sectors/sectorSnapshot';
import { WatchlistSection } from '@/features/watchlist/components/WatchlistSection';
import { WatchlistSummary } from '@/features/watchlist/components/WatchlistSummary';
import { buildWatchlistKey, useWatchlist, type GroupWatchlistItem } from '@/features/watchlist/store';
import { classifyWatchlistItem } from '@/features/watchlist/watchlistClassifier';
import {
  getSortLabel,
  groupSortedWatchlistItems,
  sortWatchlistItems,
  WATCHLIST_SORT_OPTIONS,
} from '@/features/watchlist/watchlistSort';
import { useWatchlistUiPreferences } from '@/features/watchlist/watchlistUiPreferences';
import type { ClassifiedWatchlistItem, WatchlistGroup } from '@/features/watchlist/types';
import { useWatchlistDashboard } from '@/hooks/useWatchlistDashboard';
import { useSectorSnapshot } from '@/hooks/useSectorSnapshot';
import type { WatchlistSummaryItem } from '@/types/market';

type WatchlistTab = 'stocks' | 'groups';

const WATCHLIST_TABS = [
  { key: 'stocks', label: 'Stocks' },
  { key: 'groups', label: 'Sectors' },
];
const WATCHLIST_GROUP_ORDER: WatchlistGroup[] = [
  'needs_attention',
  'high_priority',
  'momentum',
  'watching',
  'data_unavailable',
];

export default function WatchlistScreen() {
  const [isFocused, setIsFocused] = useState(false);
  const [activeTab, setActiveTab] = useState<WatchlistTab>('stocks');
  const [searchText, setSearchText] = useState('');
  const [stockToolbarOpen, setStockToolbarOpen] = useState(false);
  const [sectorThemeSearchText, setSectorThemeSearchText] = useState('');
  const [sectorThemeToolbarOpen, setSectorThemeToolbarOpen] = useState(false);
  const [removedSymbols, setRemovedSymbols] = useState<string[]>([]);
  const [inputError, setInputError] = useState<string | null>(null);
  const [selectedGroup, setSelectedGroup] = useState<SectorId | null>(null);
  const watchlistStore = useWatchlist();
  const [watchlistPreferences, updateWatchlistPreferences] = useWatchlistUiPreferences();
  const {
    collapsedGroups,
    sortMode,
  } = watchlistPreferences;
  const { snapshot: sectorSnapshot } = useSectorSnapshot(activeTab === 'groups');

  useFocusEffect(
    useCallback(() => {
      setIsFocused(true);
      return () => setIsFocused(false);
    }, []),
  );

  const requestedStockSymbols = useMemo(
    () => watchlistStore.stockItems.map((item) => item.ticker).sort(),
    [watchlistStore.stockItems],
  );
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
  const visibleClassifiedItems = useMemo(
    () => classifiedStockItems.filter(({ item }) => !query || item.ticker.includes(query)),
    [classifiedStockItems, query],
  );
  const sortedClassifiedItems = useMemo(
    () => sortWatchlistItems(visibleClassifiedItems, sortMode),
    [sortMode, visibleClassifiedItems],
  );
  const groupedClassifiedItems = useMemo(
    () => groupSortedWatchlistItems(sortedClassifiedItems),
    [sortedClassifiedItems],
  );
  const canAdd = query.length > 0 && !savedItems.some((item) => item.ticker === query);

  const sectorThemeQuery = sectorThemeSearchText.trim().toLowerCase();
  const savedSectors = useMemo(() => watchlistStore.groupItems
    .filter((item) => item.type === 'sector')
    .map((stored) => ({ stored, sectorId: normalizeSectorId(stored.id) ?? normalizeSectorId(stored.name) }))
    .filter((item): item is { stored: GroupWatchlistItem; sectorId: SectorId } => item.sectorId !== null)
    .map((item) => ({ ...item, row: sectorSnapshot?.sectors.find((row) => row.sectorId === item.sectorId) ?? null }))
    .filter(({ stored, row }) => !sectorThemeQuery || [stored.id, stored.name, row?.displayName, row?.sectorId].filter(Boolean).join(' ').toLowerCase().includes(sectorThemeQuery))
    .sort((a, b) => (a.row?.rank ?? 999) - (b.row?.rank ?? 999)), [sectorSnapshot, sectorThemeQuery, watchlistStore.groupItems]);
  const copilotContext = useMemo(
    () => createCopilotContext({
      payload: {
        activeTab,
        groupCounts: activeTab === 'stocks'
          ? WATCHLIST_GROUP_ORDER.reduce<Record<string, number>>((acc, group) => {
            acc[group] = groupedClassifiedItems[group].length;
            return acc;
          }, {})
          : { saved_sectors: savedSectors.length },
        items: activeTab === 'stocks'
          ? sortedClassifiedItems.map(({ classification, item }) => ({
            changePercent: item.change_percent,
            risk: item.risk_flag,
            score: classification.score,
            signal: classification.primarySignal,
            ticker: item.ticker,
            group: classification.group,
          }))
          : savedSectors.map(({ row, stored }) => ({ id: row?.sectorId ?? stored.id, name: row?.displayName ?? stored.name, score: row?.compositeScore, signal: row?.classification, type: 'sector' })),
        sortMode: activeTab === 'stocks' ? sortMode : 'snapshot_rank',
      },
      routeName: '/watchlist',
      screenTitle: activeTab === 'stocks' ? 'Watchlist Stocks' : 'Watchlist Sectors & Themes',
      screenType: 'watchlist',
      sourceState: activeTab === 'stocks' ? 'mixed' : sectorSnapshot?.sourceState ?? 'unavailable',
    }),
    [activeTab, groupedClassifiedItems, savedSectors, sectorSnapshot?.sourceState, sortMode, sortedClassifiedItems],
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

  const toggleGroupCollapsed = (group: WatchlistGroup) => {
    updateWatchlistPreferences({
      collapsedGroups: {
        [group]: !collapsedGroups[group],
      },
    });
  };

  return (
    <AppScreen title="Watchlist" subtitle="Saved stocks, sectors, and themes.">
      <View style={styles.stack}>
        <View style={styles.topControlRow}>
          <View style={styles.tabSwitchWrap}>
            <SegmentedControl
              fullWidth
              onChange={(key) => setActiveTab(key as WatchlistTab)}
              options={WATCHLIST_TABS}
              selectedKey={activeTab}
              variant="switch"
            />
          </View>
          {activeTab === 'stocks' ? (
            <StockHeaderActions
              open={stockToolbarOpen}
              onToggle={() => setStockToolbarOpen((current) => !current)}
            />
          ) : (
            <SectorThemeHeaderActions
              open={sectorThemeToolbarOpen}
              onToggle={() => setSectorThemeToolbarOpen((current) => !current)}
            />
          )}
        </View>

        <AskCopilotButton
          context={copilotContext}
          prompt={activeTab === 'stocks' ? 'Rank my watchlist and explain which name needs attention.' : 'Explain my saved sectors using the current market snapshot.'}
        />

        {activeTab === 'stocks' ? (
          <>
            {classifiedStockItems.length ? <WatchlistSummary items={classifiedStockItems} /> : null}

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

                {stockToolbarOpen ? (
                  <DashboardCard style={styles.compactControlCard}>
                    <StockSearchPanel
                      canAdd={canAdd}
                      inputError={inputError}
                      onAdd={addSymbol}
                      onQueryChange={(value) => {
                        setSearchText(value);
                        setInputError(null);
                      }}
                      query={searchText}
                    />
                    <StockSortPanel
                      onSortChange={(nextSortMode) => updateWatchlistPreferences({ sortMode: nextSortMode })}
                      sortMode={sortMode}
                    />
                    {sortMode === 'manualOrder' ? (
                      <Text style={styles.helperText}>Manual Order follows your saved ticker order.</Text>
                    ) : null}
                  </DashboardCard>
                ) : null}

                <View style={styles.stack}>
                  {WATCHLIST_GROUP_ORDER.map((group) => (
                    <WatchlistSection
                      collapsed={Boolean(collapsedGroups[group])}
                      group={group}
                      items={groupedClassifiedItems[group]}
                      key={group}
                      onToggleCollapsed={() => toggleGroupCollapsed(group)}>
                      {groupedClassifiedItems[group].map(({ classification, item }) => (
                        <StockCard
                          classification={classification}
                          key={item.ticker}
                          onRemove={removeSymbol}
                          stock={item}
                        />
                      ))}
                    </WatchlistSection>
                  ))}
                </View>

                {!error && savedItems.length === 0 ? (
                  <EmptyState
                    title="No stock watchlist items"
                    message="Add a ticker above, or add relevant stocks from sector and theme detail views."
                  />
                ) : null}

                {!error && savedItems.length > 0 && visibleClassifiedItems.length === 0 ? (
                  <EmptyState
                    title="No stock matches"
                    message="Try another ticker search."
                  />
                ) : null}
              </>
            )}
          </>
        ) : (
          <View style={styles.stack}>
            {sectorThemeToolbarOpen ? (
              <DashboardCard style={styles.compactControlCard}>
                <SectorThemeSearchPanel
                  query={sectorThemeSearchText}
                  onQueryChange={setSectorThemeSearchText}
                />
              </DashboardCard>
            ) : null}

            {!watchlistStore.hydrated ? (
              <SkeletonCard compact rows={2} title />
            ) : (
              <View style={styles.stack}>
                {savedSectors.map(({ stored, sectorId, row }) => (
                  <DashboardCard key={buildWatchlistKey('sector', sectorId)}>
                    <Pressable accessibilityRole="button" onPress={() => setSelectedGroup(sectorId)} style={styles.summaryHeaderRow}>
                      <View><Text style={styles.summaryTitle}>{row?.displayName ?? stored.name}</Text><Text style={styles.summarySubtitle}>{row ? `#${row.rank} · ${row.etfSymbol} · ${row.classification}` : 'Sector snapshot unavailable'}</Text></View>
                      <Text style={styles.summaryCount}>{row?.compositeScore?.toFixed(2) ?? 'N/A'}</Text>
                    </Pressable>
                    <Pressable accessibilityRole="button" onPress={() => removeGroup(stored)} style={styles.removeGroupButton}><Text style={styles.removeGroupText}>Remove</Text></Pressable>
                  </DashboardCard>
                ))}
                {watchlistStore.groupItems.some((item) => item.type === 'theme') ? <Text style={styles.helperText}>Live theme intelligence is not yet available.</Text> : null}
              </View>
            )}

            {watchlistStore.hydrated && watchlistStore.groupItems.length === 0 ? (
              <EmptyState
                title="No saved sectors"
                message="Open the Sectors tab and save a sector to track it here."
              />
            ) : null}
            {watchlistStore.hydrated && watchlistStore.groupItems.length > 0 && savedSectors.length === 0 ? (
              <EmptyState
                title="No saved groups match"
                message="Change the search to show saved sectors."
              />
            ) : null}
          </View>
        )}
      </View>

      <DetailModal
        onClose={() => setSelectedGroup(null)}
        subtitle={sectorSnapshot ? `${sectorSnapshot.marketDate} · ${sectorSnapshot.sourceState === 'live' ? 'Live Polygon history' : 'Snapshot data'}` : undefined}
        title={selectedGroup ? sectorSnapshot?.sectors.find((row) => row.sectorId === selectedGroup)?.displayName ?? 'Sector detail' : 'Sector detail'}
        visible={Boolean(selectedGroup)}>
        {selectedGroup ? <SectorDetailContent sectorId={selectedGroup} /> : null}
      </DetailModal>
    </AppScreen>
  );
}

function StockHeaderActions({ onToggle, open }: { onToggle: () => void; open: boolean }) {
  return (
    <View style={styles.stockActionRow}>
      <IconButton
        active={open}
        accessibilityLabel="Open stock search and sort toolbar"
        icon={{ android: 'tune', ios: 'slider.horizontal.3', web: 'slider.horizontal.3' }}
        onPress={onToggle}
      />
    </View>
  );
}

function SectorThemeHeaderActions({ onToggle, open }: { onToggle: () => void; open: boolean }) {
  return (
    <View style={styles.stockActionRow}>
      <IconButton
        active={open}
        accessibilityLabel="Open sector and theme search and sort toolbar"
        icon={{ android: 'tune', ios: 'slider.horizontal.3', web: 'slider.horizontal.3' }}
        onPress={onToggle}
      />
    </View>
  );
}

function IconButton({
  accessibilityLabel,
  active,
  icon,
  onPress,
}: {
  accessibilityLabel: string;
  active: boolean;
  icon: { android: string; ios: string; web: string };
  onPress: () => void;
}) {
  return (
    <Pressable
      accessibilityLabel={accessibilityLabel}
      accessibilityRole="button"
      accessibilityState={{ selected: active }}
      onPress={onPress}
      style={({ pressed }) => [styles.iconButton, active && styles.iconButtonActive, pressed && styles.pressedButton]}>
      <SymbolView
        name={icon as never}
        size={17}
        tintColor={active ? Theme.colors.accent : Theme.colors.textMuted}
        weight="bold"
      />
    </Pressable>
  );
}

function StockSearchPanel({
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
          accessibilityLabel="Search or add ticker"
          autoCapitalize="characters"
          autoCorrect={false}
          onChangeText={(value) => onQueryChange(value.toUpperCase())}
          onSubmitEditing={onAdd}
          placeholder="Search or add ticker"
          placeholderTextColor={Theme.colors.textMuted}
          returnKeyType="done"
          style={styles.searchInput}
          value={query}
        />
        <Pressable
          accessibilityLabel="Add ticker to stock watchlist"
          accessibilityRole="button"
          disabled={!canAdd}
          onPress={onAdd}
          style={({ pressed }) => [styles.addTickerButton, !canAdd && styles.disabledButton, pressed && styles.pressedButton]}>
          <Text style={styles.addTickerText}>+</Text>
        </Pressable>
      </View>
      {inputError ? <Text style={styles.errorText}>{inputError}</Text> : null}
    </View>
  );
}

function StockSortPanel({
  onSortChange,
  sortMode,
}: {
  onSortChange: (sortMode: typeof WATCHLIST_SORT_OPTIONS[number]['key']) => void;
  sortMode: typeof WATCHLIST_SORT_OPTIONS[number]['key'];
}) {
  return (
    <View style={styles.sortPanel}>
      <Text style={styles.sortPanelTitle}>Sort: {getSortLabel(sortMode)}</Text>
      <View style={styles.sortOptionGrid}>
        {WATCHLIST_SORT_OPTIONS.map((option) => {
          const selected = option.key === sortMode;
          return (
            <Pressable
              accessibilityLabel={`Sort by ${option.label}`}
              accessibilityRole="button"
              accessibilityState={{ selected }}
              key={option.key}
              onPress={() => onSortChange(option.key)}
              style={({ pressed }) => [styles.sortOption, selected && styles.sortOptionSelected, pressed && styles.pressedButton]}>
              <Text numberOfLines={1} style={[styles.sortOptionText, selected && styles.sortOptionTextSelected]}>{option.label}</Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

function SectorThemeSearchPanel({
  onQueryChange,
  query,
}: {
  onQueryChange: (query: string) => void;
  query: string;
}) {
  return (
    <View style={styles.searchPanel}>
      <Text style={styles.sortPanelTitle}>Search saved sectors and themes</Text>
      <TextInput
        accessibilityLabel="Search saved sectors and themes"
        autoCapitalize="words"
        autoCorrect={false}
        onChangeText={onQueryChange}
        placeholder="Search sectors or themes"
        placeholderTextColor={Theme.colors.textMuted}
        returnKeyType="search"
        style={styles.searchInput}
        value={query}
      />
    </View>
  );
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

function isValidSymbol(value: string) {
  return /^[A-Z0-9.]{1,10}$/.test(value);
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
    fontSize: 23,
    fontWeight: '900',
    lineHeight: 24,
  },
  badgeRow: {
    alignItems: 'center',
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
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
    fontSize: 12,
    fontWeight: '800',
  },
  helperText: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '800',
    lineHeight: 17,
    marginTop: Spacing.two,
  },
  iconButton: {
    alignItems: 'center',
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    height: 42,
    justifyContent: 'center',
    width: 42,
  },
  iconButtonActive: {
    backgroundColor: Theme.colors.accentSoft,
    borderColor: Theme.colors.accent,
  },
  list: {
    gap: Spacing.two,
  },
  metricGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
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
    fontSize: 15,
    fontWeight: '900',
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
  sortOption: {
    alignItems: 'center',
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    flexGrow: 1,
    minHeight: 36,
    minWidth: '47%',
    paddingHorizontal: Spacing.two,
    justifyContent: 'center',
  },
  sortOptionGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.one,
  },
  sortOptionSelected: {
    backgroundColor: Theme.colors.accentSoft,
    borderColor: Theme.colors.accent,
  },
  sortOptionText: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: '800',
  },
  sortOptionTextSelected: {
    color: Theme.colors.text,
  },
  sortPanel: {
    gap: Spacing.two,
  },
  sortPanelTitle: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '900',
    textTransform: 'uppercase',
  },
  stack: {
    gap: Spacing.three,
  },
  summaryCount: {
    color: Theme.colors.accent,
    fontSize: 12,
    fontWeight: '900',
  },
  summaryHeaderRow: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
    marginBottom: Spacing.two,
  },
  removeGroupButton: {
    alignItems: 'center',
    alignSelf: 'flex-start',
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    justifyContent: 'center',
    minHeight: 32,
    paddingHorizontal: Spacing.two,
  },
  removeGroupText: {
    color: Theme.colors.danger,
    fontSize: 12,
    fontWeight: '800',
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
    fontSize: 9,
    fontWeight: '900',
    textTransform: 'uppercase',
  },
  summaryMetricRow: {
    flexDirection: 'row',
    gap: Spacing.one,
  },
  summaryMetricValue: {
    fontSize: 13,
    fontWeight: '900',
    marginTop: Spacing.half,
  },
  summarySubtitle: {
    color: Theme.colors.textMuted,
    fontSize: 11,
    fontWeight: '700',
    lineHeight: 15,
  },
  summaryTitle: {
    color: Theme.colors.text,
    fontSize: 14,
    fontWeight: '900',
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
});
