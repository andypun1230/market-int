import { useMemo, useState } from 'react';
import { ScrollView, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { SymbolView } from 'expo-symbols';

import { DashboardCard } from '@/components/cards/DashboardCard';
import { TimeIntervalSelector } from '@/components/charts/TimeIntervalSelector';
import { DetailModal } from '@/components/ui/DetailModal';
import { EmptyState } from '@/components/ui/EmptyState';
import { AppIcon } from '@/components/ui/AppIcon';
import { MetricTile } from '@/components/ui/MetricTile';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { TestDataBadge } from '@/components/ui/TestDataBadge';
import { Spacing, Theme, Typography } from '@/constants/theme';
import type { ConstituentTestItem, SectorThemeTestItem, TestHeatmapInterval } from '@/data/sectorTabTestData';
import {
  DEFAULT_RELEVANT_STOCK_FILTERS,
  applyRelevantStockQuickFilter,
  buildRelevantStockActiveFilterChips,
  countRelevantStockActiveFilters,
  filterRelevantStocks,
  getRelevantStockSortLabel,
  removeRelevantStockFilter,
  RELEVANT_STOCK_SORT_OPTIONS,
  resetRelevantStockFilters,
  sortRelevantStocks,
  summarizeRelevantStocks,
  type RelevantStockFilterKey,
  type RelevantStockFilters,
  type RelevantStockSortMode,
} from '@/features/sectors/analysis/relevantStocks';
import { buildWatchlistKey } from '@/features/watchlist/store';

type RelevantStocksSectionProps = {
  group: SectorThemeTestItem;
  initialInterval: TestHeatmapInterval;
  onToggleStockWatchlist: (stock: ConstituentTestItem) => void;
  stockWatchlistKeys: Set<string>;
};

const INTERVALS: TestHeatmapInterval[] = ['1D', '1W', '1M', '3M', '6M', '1Y'];

export function RelevantStocksSection({
  group,
  initialInterval,
  onToggleStockWatchlist,
  stockWatchlistKeys,
}: RelevantStocksSectionProps) {
  const [interval, setInterval] = useState<TestHeatmapInterval>(initialInterval);
  const [query, setQuery] = useState('');
  const [filters, setFilters] = useState<RelevantStockFilters>(DEFAULT_RELEVANT_STOCK_FILTERS);
  const [sortSheetVisible, setSortSheetVisible] = useState(false);
  const [filterSheetVisible, setFilterSheetVisible] = useState(false);
  const [selectedStock, setSelectedStock] = useState<ConstituentTestItem | null>(null);

  const filteredStocks = useMemo(() => {
    const filtered = filterRelevantStocks(group.constituents, query, filters, interval, stockWatchlistKeys);
    return sortRelevantStocks(filtered, filters.sortMode, interval, stockWatchlistKeys);
  }, [filters, group.constituents, interval, query, stockWatchlistKeys]);

  const summary = useMemo(() => summarizeRelevantStocks(filteredStocks, interval), [filteredStocks, interval]);
  const activeFilterCount = countRelevantStockActiveFilters(filters);
  const activeFilterChips = useMemo(() => buildRelevantStockActiveFilterChips(filters), [filters]);

  return (
    <>
      <DashboardCard
        title="Relevant Stocks"
        subtitle={`Search, filter, and save ${group.name} test constituents.`}
        accentColor={Theme.colors.accent}>
        <View style={styles.headerRow}>
          <TestDataBadge />
          <StatusBadge label={`${filteredStocks.length}/${group.constituents.length} shown`} tone="info" />
        </View>

        <TimeIntervalSelector intervals={INTERVALS} selected={interval} onChange={setInterval} />

        <RelevantStockSearchInput
          accessibilityLabel={`Search ${group.name} relevant stocks`}
          query={query}
          onChange={setQuery}
        />

        <RelevantStockQuickFilters filters={filters} onChange={setFilters} />

        <RelevantStockControlBar
          activeFilterCount={activeFilterCount}
          sortLabel={getRelevantStockSortLabel(filters.sortMode)}
          onOpenFilters={() => setFilterSheetVisible(true)}
          onOpenSort={() => setSortSheetVisible(true)}
        />

        <ActiveRelevantStockFilters
          chips={activeFilterChips}
          onRemove={(key) => setFilters((current) => removeRelevantStockFilter(current, key))}
          onReset={() => setFilters((current) => resetRelevantStockFilters(current))}
        />

        <RelevantStockResultsSummary
          filteredCount={filteredStocks.length}
          summary={summary}
        />

        <View style={styles.stockList}>
          {filteredStocks.map((stock) => (
            <RelevantStockRow
              interval={interval}
              key={`${group.id}-${stock.ticker}`}
              onOpen={() => setSelectedStock(stock)}
              onToggleWatchlist={() => onToggleStockWatchlist(stock)}
              saved={stockWatchlistKeys.has(buildWatchlistKey('stock', stock.ticker))}
              stock={stock}
            />
          ))}
        </View>

        {!filteredStocks.length ? (
          <EmptyState title="No relevant stocks match" message="Adjust search or filters to show more test constituents." />
        ) : null}
      </DashboardCard>

      <DetailModal
        onClose={() => setSortSheetVisible(false)}
        subtitle="Only one sort option can be active at a time."
        title="Sort Relevant Stocks"
        visible={sortSheetVisible}>
        <RelevantStockSortSheet
          selected={filters.sortMode}
          onSelect={(sortMode) => {
            setFilters((current) => ({ ...current, sortMode }));
            setSortSheetVisible(false);
          }}
        />
      </DetailModal>

      <DetailModal
        onClose={() => setFilterSheetVisible(false)}
        subtitle="Refine the stock list without changing the selected interval or sort."
        title="Advanced Filters"
        visible={filterSheetVisible}>
        <RelevantStockFilterSheet
          filters={filters}
          onChange={setFilters}
          onReset={() => setFilters((current) => resetRelevantStockFilters(current))}
        />
      </DetailModal>

      <DetailModal
        onClose={() => setSelectedStock(null)}
        subtitle={selectedStock ? `${group.name} constituent · Test Data` : undefined}
        title={selectedStock ? selectedStock.ticker : 'Stock Detail'}
        visible={Boolean(selectedStock)}>
        {selectedStock ? (
          <DashboardCard title={selectedStock.companyName ?? selectedStock.ticker} accentColor={Theme.colors.accent}>
            <View style={styles.headerRow}>
              <TestDataBadge />
              <StatusBadge label={selectedStock.momentumLabel} tone={getMomentumTone(selectedStock.momentumLabel)} />
              <StatusBadge label={selectedStock.marketCapCategory} tone="muted" />
            </View>
            <View style={styles.summaryGrid}>
              {INTERVALS.map((itemInterval) => (
                <MetricTile key={itemInterval} label={itemInterval} value={formatPercent(selectedStock.returns[itemInterval])} />
              ))}
              <MetricTile label="Relative Strength" value={selectedStock.relativeStrength} tone="info" />
              <MetricTile label="Relative Momentum" value={selectedStock.relativeMomentum} tone="info" />
              <MetricTile label="Weight" value={`${selectedStock.weight.toFixed(2)}%`} tone="muted" />
              <MetricTile label="Trend" value={selectedStock.above50Ema ? 'Above 50EMA' : 'Below 50EMA'} tone={selectedStock.above50Ema ? 'success' : 'warning'} />
            </View>
            <Pressable
              accessibilityLabel={`${stockWatchlistKeys.has(buildWatchlistKey('stock', selectedStock.ticker)) ? 'Remove' : 'Add'} ${selectedStock.ticker} stock watchlist`}
              accessibilityRole="button"
              onPress={() => onToggleStockWatchlist(selectedStock)}
              style={styles.primaryAction}>
              <Text style={styles.primaryActionText}>
                {stockWatchlistKeys.has(buildWatchlistKey('stock', selectedStock.ticker)) ? 'Saved to Stocks' : 'Add to Stocks Watchlist'}
              </Text>
            </Pressable>
          </DashboardCard>
        ) : null}
      </DetailModal>
    </>
  );
}

function RelevantStockSearchInput({
  accessibilityLabel,
  onChange,
  query,
}: {
  accessibilityLabel: string;
  onChange: (value: string) => void;
  query: string;
}) {
  return (
    <View style={styles.searchShell}>
      <SymbolView
        name={{ android: 'search', ios: 'magnifyingglass', web: 'magnifyingglass' } as never}
        size={17}
        tintColor={Theme.colors.textMuted}
        weight="bold"
      />
      <TextInput
        accessibilityLabel={accessibilityLabel}
        autoCapitalize="characters"
        autoCorrect={false}
        onChangeText={onChange}
        placeholder="Search ticker or company"
        placeholderTextColor={Theme.colors.textMuted}
        style={styles.searchInput}
        value={query}
      />
      {query ? (
        <Pressable
          accessibilityLabel="Clear stock search"
          accessibilityRole="button"
          hitSlop={8}
          onPress={() => onChange('')}
          style={styles.clearButton}>
          <SymbolView
            name={{ android: 'cancel', ios: 'xmark.circle.fill', web: 'xmark.circle.fill' } as never}
            size={17}
            tintColor={Theme.colors.textMuted}
            weight="bold"
          />
        </Pressable>
      ) : null}
    </View>
  );
}

function RelevantStockQuickFilters({
  filters,
  onChange,
}: {
  filters: RelevantStockFilters;
  onChange: (updater: (current: RelevantStockFilters) => RelevantStockFilters) => void;
}) {
  const quickFilters = [
    {
      active: filters.performance === 'positive',
      icon: { android: 'trending_up', ios: 'arrow.up.right', web: 'arrow.up.right' },
      key: 'leaders',
      label: 'Leaders',
      onPress: () => onChange((current) => applyRelevantStockQuickFilter(current, 'leaders')),
    },
    {
      active: filters.performance === 'negative',
      icon: { android: 'trending_down', ios: 'arrow.down.right', web: 'arrow.down.right' },
      key: 'laggards',
      label: 'Laggards',
      onPress: () => onChange((current) => applyRelevantStockQuickFilter(current, 'laggards')),
    },
    {
      active: filters.trend === 'above20',
      icon: { android: 'monitoring', ios: 'waveform.path.ecg', web: 'waveform.path.ecg' },
      key: 'above20',
      label: 'Above 20 EMA',
      onPress: () => onChange((current) => applyRelevantStockQuickFilter(current, 'above20')),
    },
    {
      active: filters.watchlist === 'saved',
      icon: { android: 'bookmark', ios: 'bookmark.fill', web: 'bookmark.fill' },
      key: 'saved',
      label: 'Saved',
      onPress: () => onChange((current) => applyRelevantStockQuickFilter(current, 'watchlisted')),
    },
  ] as const;

  return (
    <ScrollView
      horizontal
      contentContainerStyle={styles.quickFilterContent}
      showsHorizontalScrollIndicator={false}>
      {quickFilters.map((filter) => (
        <QuickFilterChip
          active={filter.active}
          icon={filter.icon}
          key={filter.key}
          label={filter.label}
          onPress={filter.onPress}
        />
      ))}
    </ScrollView>
  );
}

function RelevantStockControlBar({
  activeFilterCount,
  onOpenFilters,
  onOpenSort,
  sortLabel,
}: {
  activeFilterCount: number;
  onOpenFilters: () => void;
  onOpenSort: () => void;
  sortLabel: string;
}) {
  return (
    <View style={styles.controlBar}>
      <Pressable
        accessibilityLabel={`Sort relevant stocks by ${sortLabel}`}
        accessibilityRole="button"
        onPress={onOpenSort}
        style={({ pressed }) => [styles.toolbarButton, pressed && styles.pressed]}>
        <SymbolView
          name={{ android: 'sort', ios: 'arrow.up.arrow.down', web: 'arrow.up.arrow.down' } as never}
          size={15}
          tintColor={Theme.colors.accent}
          weight="bold"
        />
        <Text numberOfLines={1} style={styles.toolbarButtonText}>Sort: {sortLabel}</Text>
        <AppIcon name="chevronDown" size={17} />
      </Pressable>
      <Pressable
        accessibilityLabel={`Open advanced filters, ${activeFilterCount} active`}
        accessibilityRole="button"
        onPress={onOpenFilters}
        style={({ pressed }) => [styles.toolbarButton, styles.filterToolbarButton, pressed && styles.pressed]}>
        <SymbolView
          name={{ android: 'tune', ios: 'slider.horizontal.3', web: 'slider.horizontal.3' } as never}
          size={15}
          tintColor={Theme.colors.warning}
          weight="bold"
        />
        <Text numberOfLines={1} style={styles.toolbarButtonText}>Filters</Text>
        {activeFilterCount ? (
          <View style={styles.filterCountBadge}>
            <Text style={styles.filterCountText}>{activeFilterCount}</Text>
          </View>
        ) : null}
      </Pressable>
    </View>
  );
}

function ActiveRelevantStockFilters({
  chips,
  onRemove,
  onReset,
}: {
  chips: { key: RelevantStockFilterKey; label: string }[];
  onRemove: (key: RelevantStockFilterKey) => void;
  onReset: () => void;
}) {
  if (!chips.length) {
    return null;
  }

  return (
    <View style={styles.activeFilterBlock}>
      <View style={styles.activeFilterHeader}>
        <Text style={styles.activeFilterTitle}>Active Filters · {chips.length}</Text>
        <Pressable
          accessibilityLabel="Reset active stock filters"
          accessibilityRole="button"
          hitSlop={8}
          onPress={onReset}>
          <Text style={styles.resetFiltersText}>Reset Filters</Text>
        </Pressable>
      </View>
      <View style={styles.activeChipRow}>
        {chips.map((chip) => (
          <Pressable
            accessibilityLabel={`Remove ${chip.label} filter`}
            accessibilityRole="button"
            key={chip.key}
            onPress={() => onRemove(chip.key)}
            style={({ pressed }) => [styles.activeFilterChip, pressed && styles.pressed]}>
            <Text style={styles.activeFilterChipText}>{chip.label}</Text>
            <AppIcon color={Theme.colors.warning} name="close" size={12} />
          </Pressable>
        ))}
      </View>
    </View>
  );
}

function RelevantStockResultsSummary({
  filteredCount,
  summary,
}: {
  filteredCount: number;
  summary: ReturnType<typeof summarizeRelevantStocks>;
}) {
  return (
    <View style={styles.resultsSummary}>
      <Text style={styles.resultsSummaryTitle}>{filteredCount} stocks</Text>
      <Text style={styles.resultsSummaryText}>
        {summary.positives} positive · {summary.negatives} negative · Median {formatPercent(summary.medianReturn)}
      </Text>
    </View>
  );
}

function RelevantStockSortSheet({
  onSelect,
  selected,
}: {
  onSelect: (sortMode: RelevantStockSortMode) => void;
  selected: RelevantStockSortMode;
}) {
  return (
    <View style={styles.sheetStack}>
      {RELEVANT_STOCK_SORT_OPTIONS.map((option) => {
        const active = selected === option.key;
        return (
          <Pressable
            accessibilityLabel={`Sort by ${option.label}`}
            accessibilityRole="radio"
            accessibilityState={{ checked: active }}
            key={option.key}
            onPress={() => onSelect(option.key)}
            style={({ pressed }) => [styles.sheetOption, active && styles.sheetOptionActive, pressed && styles.pressed]}>
            <Text style={[styles.sheetOptionText, active && styles.sheetOptionTextActive]}>{option.label}</Text>
            <AppIcon color={active ? Theme.colors.accent : Theme.colors.textMuted} name={active ? 'neutralDot' : 'pending'} size={14} />
          </Pressable>
        );
      })}
    </View>
  );
}

function RelevantStockFilterSheet({
  filters,
  onChange,
  onReset,
}: {
  filters: RelevantStockFilters;
  onChange: (filters: RelevantStockFilters) => void;
  onReset: () => void;
}) {
  return (
    <View style={styles.sheetStack}>
      <View style={styles.sheetHeaderRow}>
        <Text style={styles.sheetIntro}>Advanced filters use the same state as the quick chips.</Text>
        <Pressable accessibilityRole="button" hitSlop={8} onPress={onReset}>
          <Text style={styles.resetFiltersText}>Reset Filters</Text>
        </Pressable>
      </View>
      <FilterGroup
        title="Performance"
        options={[
          ['positive', 'Positive'],
          ['negative', 'Negative'],
          ['nearZero', 'Near Zero'],
        ]}
        selected={filters.performance}
        onSelect={(performance) => onChange({ ...filters, performance: performance as RelevantStockFilters['performance'] })}
      />
      <FilterGroup
        title="Trend"
        options={[
          ['above20', 'Above 20 EMA'],
          ['below20', 'Below 20 EMA'],
          ['above50', 'Above 50 EMA'],
          ['below50', 'Below 50 EMA'],
        ]}
        selected={filters.trend}
        onSelect={(trend) => onChange({ ...filters, trend: trend as RelevantStockFilters['trend'] })}
      />
      <FilterGroup
        title="Relative Strength"
        options={[
          ['above100', 'RS above 100'],
          ['below100', 'RS below 100'],
        ]}
        selected={filters.relativeStrength}
        onSelect={(relativeStrength) => onChange({ ...filters, relativeStrength: relativeStrength as RelevantStockFilters['relativeStrength'] })}
      />
      <FilterGroup
        title="Momentum"
        options={[
          ['strong', 'Strong'],
          ['improving', 'Improving'],
          ['neutral', 'Neutral'],
          ['weakening', 'Weakening'],
          ['weak', 'Weak'],
        ]}
        selected={filters.momentum}
        onSelect={(momentum) => onChange({ ...filters, momentum: momentum as RelevantStockFilters['momentum'] })}
      />
      <FilterGroup
        title="Market Cap"
        options={[
          ['large', 'Large'],
          ['mid', 'Mid'],
          ['small', 'Small'],
        ]}
        selected={filters.marketCap}
        onSelect={(marketCap) => onChange({ ...filters, marketCap: marketCap as RelevantStockFilters['marketCap'] })}
      />
      <FilterGroup
        title="Watchlist"
        options={[
          ['saved', 'Saved only'],
          ['notSaved', 'Not saved'],
        ]}
        selected={filters.watchlist}
        onSelect={(watchlist) => onChange({ ...filters, watchlist: watchlist as RelevantStockFilters['watchlist'] })}
      />
    </View>
  );
}

function FilterGroup<T extends string>({
  onSelect,
  options,
  selected,
  title,
}: {
  onSelect: (value: T | 'all') => void;
  options: [T, string][];
  selected: T | 'all';
  title: string;
}) {
  return (
    <View style={styles.filterGroup}>
      <Text style={styles.filterGroupTitle}>{title}</Text>
      <View style={styles.filterGroupChips}>
        {options.map(([key, label]) => (
          <SheetChip
            active={selected === key}
            key={key}
            label={label}
            onPress={() => onSelect(selected === key ? 'all' : key)}
          />
        ))}
      </View>
    </View>
  );
}

function RelevantStockRow({
  interval,
  onOpen,
  onToggleWatchlist,
  saved,
  stock,
}: {
  interval: TestHeatmapInterval;
  onOpen: () => void;
  onToggleWatchlist: () => void;
  saved: boolean;
  stock: ConstituentTestItem;
}) {
  const value = stock.returns[interval];
  return (
    <Pressable
      accessibilityLabel={`Open ${stock.ticker} relevant stock detail`}
      accessibilityRole="button"
      onPress={onOpen}
      style={({ pressed }) => [styles.stockRow, pressed && styles.pressed]}>
      <View style={styles.stockMain}>
        <Text numberOfLines={1} style={styles.ticker}>{stock.ticker}</Text>
        <Text numberOfLines={1} style={styles.company}>{stock.companyName ?? 'Test constituent'}</Text>
      </View>
      <View style={styles.stockMetrics}>
        <Text style={[styles.returnText, { color: value >= 0 ? Theme.colors.success : Theme.colors.danger }]}>
          {formatPercent(value)}
        </Text>
        <Text style={styles.metaText}>RS {stock.relativeStrength.toFixed(1)}</Text>
      </View>
      <Pressable
        accessibilityLabel={`${saved ? 'Remove' : 'Add'} ${stock.ticker} stock watchlist`}
        accessibilityRole="button"
        hitSlop={8}
        onPress={(event) => {
          event.stopPropagation();
          onToggleWatchlist();
        }}
        style={[styles.saveButton, saved && styles.saveButtonActive]}>
        <Text style={[styles.saveText, saved && styles.saveTextActive]}>{saved ? 'Saved' : 'Add'}</Text>
      </Pressable>
    </Pressable>
  );
}

function QuickFilterChip({
  active,
  icon,
  label,
  onPress,
}: {
  active: boolean;
  icon: { android: string; ios: string; web: string };
  label: string;
  onPress: () => void;
}) {
  return (
    <Pressable
      accessibilityLabel={label}
      accessibilityRole="button"
      accessibilityState={{ selected: active }}
      onPress={onPress}
      style={({ pressed }) => [styles.quickFilterChip, active && styles.quickFilterChipActive, pressed && styles.pressed]}>
      <SymbolView
        name={icon as never}
        size={14}
        tintColor={active ? Theme.colors.accent : Theme.colors.textMuted}
        weight="bold"
      />
      <Text style={[styles.quickFilterText, active && styles.quickFilterTextActive]}>{label}</Text>
    </Pressable>
  );
}

function SheetChip({ active, label, onPress }: { active: boolean; label: string; onPress: () => void }) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected: active }}
      onPress={onPress}
      style={({ pressed }) => [styles.sheetChip, active && styles.sheetChipActive, pressed && styles.pressed]}>
      <Text style={[styles.sheetChipText, active && styles.sheetChipTextActive]}>{label}</Text>
    </Pressable>
  );
}

function getMomentumTone(momentum: ConstituentTestItem['momentumLabel']) {
  switch (momentum) {
    case 'strong':
      return 'success' as const;
    case 'improving':
      return 'info' as const;
    case 'weakening':
      return 'warning' as const;
    case 'weak':
      return 'danger' as const;
    case 'neutral':
    default:
      return 'muted' as const;
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
  activeChipRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  activeFilterBlock: {
    gap: Spacing.two,
  },
  activeFilterChip: {
    alignItems: 'center',
    backgroundColor: Theme.colors.warningSoft,
    borderColor: Theme.colors.warning,
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    flexDirection: 'row',
    gap: Spacing.one,
    minHeight: 30,
    paddingHorizontal: Spacing.two,
    justifyContent: 'center',
  },
  activeFilterChipText: {
    color: Theme.colors.warning,
    fontSize: Typography.caption.fontSize,
    fontWeight: Typography.weights.strong,
  },
  activeFilterHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  activeFilterTitle: {
    color: Theme.colors.textMuted,
    fontSize: Typography.caption.fontSize,
    fontWeight: Typography.weights.strong,
    textTransform: 'uppercase',
  },
  company: {
    color: Theme.colors.textMuted,
    fontSize: Typography.caption.fontSize,
    fontWeight: Typography.weights.strong,
  },
  clearButton: {
    alignItems: 'center',
    height: 32,
    justifyContent: 'center',
    width: 32,
  },
  controlBar: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: Spacing.two,
  },
  filterCountBadge: {
    alignItems: 'center',
    backgroundColor: Theme.colors.warning,
    borderRadius: Theme.radii.pill,
    height: 18,
    justifyContent: 'center',
    minWidth: 18,
    paddingHorizontal: 5,
  },
  filterCountText: {
    color: Theme.colors.background,
    fontSize: Typography.chartLabel.fontSize,
    fontWeight: Typography.weights.strong,
  },
  filterGroup: {
    gap: Spacing.two,
  },
  filterGroupChips: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  filterGroupTitle: {
    color: Theme.colors.text,
    fontSize: Typography.control.fontSize,
    fontWeight: Typography.weights.strong,
  },
  filterToolbarButton: {
    flex: 0.72,
  },
  headerRow: {
    alignItems: 'center',
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  metaText: {
    color: Theme.colors.textMuted,
    fontSize: Typography.caption.fontSize,
    fontWeight: Typography.weights.strong,
    textAlign: 'right',
  },
  pressed: {
    opacity: 0.78,
  },
  primaryAction: {
    alignItems: 'center',
    backgroundColor: Theme.colors.accent,
    borderRadius: Theme.radii.small,
    minHeight: 44,
    justifyContent: 'center',
    marginTop: Spacing.two,
    paddingHorizontal: Spacing.three,
  },
  primaryActionText: {
    color: Theme.colors.text,
    fontSize: Typography.control.fontSize,
    fontWeight: Typography.weights.strong,
  },
  quickFilterChip: {
    alignItems: 'center',
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    flexDirection: 'row',
    gap: Spacing.one,
    minHeight: 34,
    justifyContent: 'center',
    paddingHorizontal: Spacing.twoAndHalf,
  },
  quickFilterChipActive: {
    backgroundColor: Theme.colors.accentSoft,
    borderColor: Theme.colors.accent,
  },
  quickFilterContent: {
    gap: Spacing.two,
    paddingRight: Spacing.three,
  },
  quickFilterText: {
    color: Theme.colors.textMuted,
    fontSize: Typography.caption.fontSize,
    fontWeight: Typography.weights.strong,
  },
  quickFilterTextActive: {
    color: Theme.colors.accent,
  },
  resetFiltersText: {
    color: Theme.colors.warning,
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.strong,
  },
  resultsSummary: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    gap: Spacing.one,
    padding: Spacing.twoAndHalf,
  },
  resultsSummaryText: {
    color: Theme.colors.textMuted,
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.strong,
  },
  resultsSummaryTitle: {
    color: Theme.colors.text,
    fontSize: Typography.body.fontSize,
    fontWeight: Typography.weights.strong,
  },
  returnText: {
    fontSize: Typography.body.fontSize,
    fontWeight: Typography.weights.strong,
    textAlign: 'right',
  },
  saveButton: {
    alignItems: 'center',
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    justifyContent: 'center',
    minHeight: 44,
    minWidth: 58,
  },
  saveButtonActive: {
    borderColor: Theme.colors.warning,
  },
  saveText: {
    color: Theme.colors.textMuted,
    fontSize: Typography.caption.fontSize,
    fontWeight: Typography.weights.strong,
  },
  saveTextActive: {
    color: Theme.colors.warning,
  },
  searchInput: {
    color: Theme.colors.text,
    flex: 1,
    fontSize: Typography.body.fontSize,
    fontWeight: Typography.weights.strong,
    minHeight: 42,
    padding: 0,
  },
  searchShell: {
    alignItems: 'center',
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    flexDirection: 'row',
    gap: Spacing.two,
    minHeight: 44,
    paddingHorizontal: Spacing.twoAndHalf,
  },
  sheetChip: {
    alignItems: 'center',
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    justifyContent: 'center',
    minHeight: 34,
    paddingHorizontal: Spacing.twoAndHalf,
  },
  sheetChipActive: {
    backgroundColor: Theme.colors.accentSoft,
    borderColor: Theme.colors.accent,
  },
  sheetChipText: {
    color: Theme.colors.textMuted,
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.strong,
  },
  sheetChipTextActive: {
    color: Theme.colors.accent,
  },
  sheetHeaderRow: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: Spacing.two,
    justifyContent: 'space-between',
  },
  sheetIntro: {
    color: Theme.colors.textMuted,
    flex: 1,
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.emphasis,
    lineHeight: 17,
  },
  sheetOption: {
    alignItems: 'center',
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    flexDirection: 'row',
    justifyContent: 'space-between',
    minHeight: 48,
    paddingHorizontal: Spacing.three,
  },
  sheetOptionActive: {
    backgroundColor: Theme.colors.accentSoft,
    borderColor: Theme.colors.accent,
  },
  sheetOptionText: {
    color: Theme.colors.text,
    fontSize: Typography.body.fontSize,
    fontWeight: Typography.weights.strong,
  },
  sheetOptionTextActive: {
    color: Theme.colors.accent,
  },
  sheetStack: {
    gap: Spacing.three,
  },
  stockList: {
    gap: Spacing.one,
  },
  stockMain: {
    flex: 1,
    minWidth: 0,
  },
  stockMetrics: {
    minWidth: 74,
  },
  stockRow: {
    alignItems: 'center',
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    flexDirection: 'row',
    gap: Spacing.two,
    minHeight: 58,
    paddingHorizontal: Spacing.two,
    paddingVertical: Spacing.one,
  },
  summaryGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  toolbarButton: {
    alignItems: 'center',
    backgroundColor: Theme.colors.cardMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    flex: 1,
    flexDirection: 'row',
    gap: Spacing.one,
    justifyContent: 'center',
    minHeight: 42,
    minWidth: 0,
    paddingHorizontal: Spacing.two,
  },
  toolbarButtonText: {
    color: Theme.colors.text,
    flexShrink: 1,
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.strong,
  },
  toolbarChevron: {
    color: Theme.colors.textMuted,
    fontSize: Typography.small.fontSize,
    fontWeight: Typography.weights.strong,
  },
  ticker: {
    color: Theme.colors.text,
    fontSize: Typography.bodyLarge.fontSize,
    fontWeight: Typography.weights.strong,
  },
});
