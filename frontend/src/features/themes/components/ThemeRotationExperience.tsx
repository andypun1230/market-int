import { useMemo, useState } from 'react';
import {
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  useWindowDimensions,
  View,
} from 'react-native';

import { RotationQuadrantChart } from '@/components/charts/RotationQuadrantChart';
import { DashboardCard } from '@/components/cards/DashboardCard';
import { DetailModal } from '@/components/ui/DetailModal';
import { EmptyState } from '@/components/ui/EmptyState';
import { SegmentedControl } from '@/components/ui/SegmentedControl';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Spacing, Theme } from '@/constants/theme';
import type { RotationLabelMode } from '@/features/sectors/analysis/rotationLabels';
import type { CanonicalThemeRotationPoint, ThemeRotationModel } from '@/features/themes/themeRotation';
import type { LiveThemeItem, ThemeOverlap } from '@/features/themes/themeSnapshot';
import {
  DEFAULT_THEME_ROTATION_VIEW_STATE,
  THEME_ROTATION_UNIVERSE_OPTIONS,
  THEME_ROTATION_VIEW_POLICY,
  buildVisibleRotationView,
  removeThemeFromComparison,
  searchThemeOptions,
  selectAllThemeOptions,
  selectionReadabilityWarning,
  toggleThemeSelection,
  type ThemeRotationFocusContext,
  type ThemeRotationMovementFilter,
  type ThemeRotationQuadrantFilter,
  type ThemeRotationTailLength,
  type ThemeRotationThemeMetadata,
  type ThemeRotationTransitionFilter,
  type ThemeRotationUniverse,
  type ThemeRotationViewMode,
  type ThemeRotationViewState,
} from '@/features/themes/themeRotationView';
import { buildWatchlistKey, useWatchlist } from '@/features/watchlist/store';

type ThemeRotationExperienceProps = {
  initialFocusedThemeId?: string | null;
  initialLabelMode: RotationLabelMode;
  initialMovement: ThemeRotationMovementFilter;
  initialQuadrant: ThemeRotationQuadrantFilter;
  initialTailLength: ThemeRotationTailLength;
  initialUniverse: ThemeRotationUniverse;
  onLabelModeChange: (mode: RotationLabelMode) => void;
  onOpenThemeDetail: (point: CanonicalThemeRotationPoint) => void;
  onQuadrantChange: (quadrant: ThemeRotationQuadrantFilter) => void;
  onViewPreferenceChange: (patch: {
    movement?: ThemeRotationMovementFilter;
    tailLength?: ThemeRotationTailLength;
    universe?: ThemeRotationUniverse;
  }) => void;
  overlap: ThemeOverlap[];
  rotation: ThemeRotationModel;
  themes: LiveThemeItem[];
};

const MODE_OPTIONS = [
  { key: 'overview', label: 'Overview' },
  { key: 'compare', label: 'Compare' },
  { key: 'focus', label: 'Focus' },
];
const QUADRANT_OPTIONS = [
  { key: 'all', label: 'All' },
  { key: 'leading', label: 'Leading' },
  { key: 'improving', label: 'Improving' },
  { key: 'weakening', label: 'Weakening' },
  { key: 'lagging', label: 'Lagging' },
];
const MOVEMENT_OPTIONS = [
  { key: 'all', label: 'All' },
  { key: 'meaningful', label: 'Meaningful' },
  { key: 'fast', label: 'Fast Movers' },
  { key: 'stable', label: 'Stable' },
];
const TRANSITION_OPTIONS = [
  { key: 'all', label: 'All' },
  { key: 'entered_leading', label: 'Entered Leading' },
  { key: 'entered_improving', label: 'Entered Improving' },
  { key: 'lost_leading', label: 'Lost Leading' },
  { key: 'quadrant_changed', label: 'Quadrant Changed' },
  { key: 'no_recent_change', label: 'No Recent Change' },
];
const TAIL_OPTIONS = [
  { key: 'current', label: 'Current' },
  { key: '3', label: '3' },
  { key: '5', label: '5' },
  { key: '8', label: '8' },
  { key: 'full', label: 'Full' },
];
const LABEL_OPTIONS = [
  { key: 'smart', label: 'Smart' },
  { key: 'selected', label: 'Selected' },
  { key: 'all', label: 'All' },
  { key: 'none', label: 'None' },
];

export function ThemeRotationExperience({
  initialFocusedThemeId,
  initialLabelMode,
  initialMovement,
  initialQuadrant,
  initialTailLength,
  initialUniverse,
  onLabelModeChange,
  onOpenThemeDetail,
  onQuadrantChange,
  onViewPreferenceChange,
  overlap,
  rotation,
  themes,
}: ThemeRotationExperienceProps) {
  const { width } = useWindowDimensions();
  const compact = width < 700;
  const watchlist = useWatchlist();
  const initialFocus = rotation.points.some((point) => point.themeId === initialFocusedThemeId)
    ? initialFocusedThemeId ?? null
    : null;
  const [viewState, setViewState] = useState<ThemeRotationViewState>(() => ({
    ...DEFAULT_THEME_ROTATION_VIEW_STATE,
    focusedThemeId: initialFocus,
    labelMode: initialFocus ? 'selected' : initialLabelMode,
    mode: initialFocus ? 'focus' : 'overview',
    movement: initialMovement,
    quadrant: initialQuadrant,
    smartLabelLimit: compact ? 6 : 8,
    tailLength: initialFocus ? 'full' : compact && initialTailLength === '5' ? '3' : initialTailLength,
    universe: initialUniverse,
  }));
  const [filtersVisible, setFiltersVisible] = useState(false);
  const [selectorVisible, setSelectorVisible] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const metadata = useMemo<ThemeRotationThemeMetadata[]>(() => themes.map((theme) => ({
    aliases: theme.aliases,
    id: theme.id,
    name: theme.name,
    parentSectorIds: theme.parentSectorIds,
    rank: theme.rank,
    status: theme.status,
    taxonomyStatus: theme.taxonomyStatus,
  })), [themes]);
  const savedThemeIds = useMemo(() => new Set(
    watchlist.groupItems.filter((item) => item.type === 'theme').map((item) => item.id),
  ), [watchlist.groupItems]);
  const view = useMemo(() => buildVisibleRotationView({ metadata, overlap, rotation, savedThemeIds }, viewState), [metadata, overlap, rotation, savedThemeIds, viewState]);
  const selectorOptions = useMemo(() => searchThemeOptions(metadata, searchQuery), [metadata, searchQuery]);
  const plottableIds = useMemo(() => new Set(rotation.points.map((point) => point.themeId)), [rotation.points]);
  const labelItemKeys = useMemo(() => new Set(view.renderedLabels.map((themeId) => `theme:${themeId}`)), [view.renderedLabels]);
  const selectedItemKeys = useMemo(() => new Set(viewState.selectedThemeIds.map((themeId) => `theme:${themeId}`)), [viewState.selectedThemeIds]);
  const chartDomainPoints = useMemo(() => rotation.points.flatMap((point) => point.history), [rotation.points]);
  const watchlistKeys = useMemo(() => new Set([...savedThemeIds].map((id) => buildWatchlistKey('theme', id))), [savedThemeIds]);
  const warning = selectionReadabilityWarning(viewState.selectedThemeIds.length, compact);

  const updateState = (patch: Partial<ThemeRotationViewState>) => {
    setViewState((current) => ({ ...current, ...patch }));
    const focusScoped = patch.mode === 'focus' || (viewState.mode === 'focus' && patch.mode === undefined);
    onViewPreferenceChange({
      movement: patch.movement,
      tailLength: focusScoped ? undefined : patch.tailLength,
      universe: patch.universe,
    });
  };
  const updateLabelMode = (labelMode: RotationLabelMode) => {
    updateState({ labelMode });
    onLabelModeChange(labelMode);
  };
  const updateQuadrant = (quadrant: ThemeRotationQuadrantFilter) => {
    updateState({ quadrant });
    onQuadrantChange(quadrant);
  };
  const enterFocus = (themeId: string) => {
    updateState({
      focusedThemeId: themeId,
      labelMode: 'selected',
      mode: 'focus',
      showRelatedThemes: false,
      tailLength: 'full',
    });
  };
  const selectMode = (mode: ThemeRotationViewMode) => {
    if (mode === 'compare' && viewState.selectedThemeIds.length < 2) {
      setSelectorVisible(true);
      return;
    }
    if (mode === 'focus' && !viewState.focusedThemeId) {
      setSelectorVisible(true);
      return;
    }
    updateState({
      focusedThemeId: mode === 'focus' ? viewState.focusedThemeId : null,
      labelMode: mode === 'compare' ? 'selected' : viewState.labelMode,
      mode,
      movement: mode === 'compare' ? 'all' : viewState.movement,
      quadrant: mode === 'compare' ? 'all' : viewState.quadrant,
      showRelatedThemes: false,
      tailLength: mode === 'compare' ? '8' : mode === 'focus' ? 'full' : compact ? '3' : '5',
      transition: mode === 'compare' ? 'all' : viewState.transition,
    });
    if (mode === 'compare') onQuadrantChange('all');
  };
  const resetOverview = () => {
    updateState({
      focusContext: 'faint',
      focusedThemeId: null,
      labelMode: 'smart',
      mode: 'overview',
      movement: 'meaningful',
      quadrant: 'all',
      showRelatedThemes: false,
      tailLength: compact ? '3' : '5',
      transition: 'all',
      universe: 'all',
    });
    onLabelModeChange('smart');
    onQuadrantChange('all');
  };
  const showAllThemes = () => {
    updateState({
      focusedThemeId: null,
      mode: 'overview',
      movement: 'all',
      quadrant: 'all',
      transition: 'all',
      universe: 'all',
    });
    onQuadrantChange('all');
  };
  const toggleSaved = (point: CanonicalThemeRotationPoint) => {
    watchlist.toggleWatchlistItem({ id: point.themeId, name: point.displayName, type: 'theme' });
  };

  return (
    <View style={styles.stack}>
      <SegmentedControl
        fullWidth
        label="View mode"
        onChange={(value) => selectMode(value as ThemeRotationViewMode)}
        options={MODE_OPTIONS}
        selectedKey={viewState.mode}
        variant="switch"
      />

      <View accessibilityLabel={view.activeFilterSummary.join('. ')} style={styles.summaryChips}>
        {view.activeFilterSummary.map((item) => <View key={item} style={styles.summaryChip}><Text style={styles.summaryChipText}>{item}</Text></View>)}
      </View>

      <View style={styles.toolbar}>
        <Pressable accessibilityLabel="Open Theme Rotation filters" accessibilityRole="button" onPress={() => setFiltersVisible(true)} style={styles.toolbarButton}>
          <Text style={styles.toolbarButtonText}>Filters</Text>
        </Pressable>
        <Pressable accessibilityLabel="Select themes" accessibilityRole="button" onPress={() => setSelectorVisible(true)} style={styles.toolbarButton}>
          <Text style={styles.toolbarButtonText}>Select themes · {viewState.selectedThemeIds.length}</Text>
        </Pressable>
        <Pressable accessibilityRole="button" onPress={resetOverview} style={styles.linkButton}>
          <Text style={styles.linkText}>Reset Overview</Text>
        </Pressable>
      </View>

      {viewState.mode === 'overview' && viewState.movement === 'meaningful' ? (
        <View style={styles.notice}>
          <Text style={styles.noticeText}>Showing meaningful movers. Stable themes remain available.</Text>
          <Pressable accessibilityRole="button" onPress={showAllThemes} style={styles.noticeAction}>
            <Text style={styles.noticeActionText}>Show all themes</Text>
          </Pressable>
        </View>
      ) : null}

      {!view.visibleThemes.length ? (
        <EmptyState
          actionLabel="Show all themes"
          message={viewState.universe === 'saved' && !savedThemeIds.size ? 'Save a reviewed theme, or return to All Themes.' : 'No eligible themes match the active presentation filters.'}
          onAction={showAllThemes}
          title={viewState.universe === 'saved' ? 'No saved themes to plot' : 'No themes match'}
        />
      ) : (
        <RotationQuadrantChart
          benchmark={rotation.benchmark}
          domainPoints={chartDomainPoints}
          getHistory={(item) => item.history}
          getItemKey={(item) => item.themeId}
          getItemType={() => 'theme'}
          getLabelPriority={(item) => item.labelPriority}
          getName={(item) => item.displayName}
          getOpacity={(item) => item.viewOpacity}
          getRelativeMomentum={(item) => item.relativeMomentum}
          getRelativeStrength={(item) => item.relativeTrend}
          horizontalAxisLabel="Relative Trend"
          indicatorDescription={`Relative Trend measures the smoothed trend of each theme’s performance versus ${rotation.benchmark}. Relative Momentum measures whether that relative trend is accelerating or decelerating. · ${title(rotation.profile)} profile`}
          interpretationText="Above 100 means the benchmark-relative trend is strengthening; Relative Momentum above 100 means that trend is improving. Coordinates are not percentage returns."
          interval={`${title(rotation.profile)} profile`}
          items={view.visibleThemes}
          labelItemKeys={labelItemKeys}
          labelMode={viewState.labelMode}
          onPressItem={(point) => onOpenThemeDetail(point)}
          onSelectItem={(key) => {
            if (key?.startsWith('theme:')) enterFocus(key.slice('theme:'.length));
          }}
          onToggleWatchlist={toggleSaved}
          quadrantFilter="all"
          selectedItemKey={viewState.mode === 'focus' && viewState.focusedThemeId ? `theme:${viewState.focusedThemeId}` : null}
          selectedItemKeys={selectedItemKeys}
          showControls={false}
          watchlistKeys={watchlistKeys}
        />
      )}

      <Text accessibilityLabel={`${view.counts.plotted} themes plotted. ${view.counts.labels} labels. ${view.counts.hiddenByFilters} hidden by filters. ${view.counts.unavailableByEvidence} unavailable due to evidence.`} style={styles.counts}>
        {view.counts.plotted} themes plotted · {view.counts.labels} labels · {view.counts.hiddenByFilters} hidden by filters
        {view.counts.unavailableByEvidence ? ` · ${view.counts.unavailableByEvidence} unavailable by evidence` : ''}
      </Text>
      <Text style={styles.disclosure}>{view.counts.historicalNodes} genuine historical nodes shown · {THEME_ROTATION_VIEW_POLICY.version}</Text>

      {viewState.mode === 'focus' && view.focusedTheme ? (
        <FocusDetails
          point={view.focusedTheme}
          relatedNames={view.relatedThemeIds.map((id) => metadata.find((item) => item.id === id)?.name).filter((name): name is string => Boolean(name))}
          saved={savedThemeIds.has(view.focusedTheme.themeId)}
          showRelated={viewState.showRelatedThemes}
          onExit={() => updateState({ focusedThemeId: null, labelMode: initialLabelMode, mode: 'overview', showRelatedThemes: false, tailLength: compact ? '3' : '5' })}
          onOpen={() => onOpenThemeDetail(view.focusedTheme!)}
          onRelated={() => updateState({ showRelatedThemes: !viewState.showRelatedThemes })}
          onSave={() => toggleSaved(view.focusedTheme!)}
          onCompareRelated={() => {
            const selectedThemeIds = selectAllThemeOptions([view.focusedTheme!.themeId], view.relatedThemeIds).slice(0, 8);
            updateState({ focusedThemeId: null, labelMode: 'selected', mode: 'compare', movement: 'all', quadrant: 'all', selectedThemeIds, tailLength: '8', transition: 'all' });
            onQuadrantChange('all');
          }}
        />
      ) : null}

      {viewState.mode === 'compare' ? (
        <CompareSummary
          points={view.visibleThemes}
          onRemove={(themeId) => {
            const next = removeThemeFromComparison(viewState, themeId, compact);
            setViewState(next);
            if (next.mode === 'overview') onViewPreferenceChange({ tailLength: next.tailLength });
          }}
        />
      ) : null}

      <FilterModal
        visible={filtersVisible}
        state={viewState}
        onClose={() => setFiltersVisible(false)}
        onLabel={updateLabelMode}
        onQuadrant={updateQuadrant}
        onState={updateState}
        onUniverse={(universe) => {
          updateState({ universe });
          if (universe === 'custom') setSelectorVisible(true);
        }}
      />

      <DetailModal visible={selectorVisible} title="Select Themes" subtitle="Search canonical names and aliases. Selection order is preserved." onClose={() => setSelectorVisible(false)}>
        <TextInput
          accessibilityLabel="Search canonical themes and aliases"
          autoCapitalize="none"
          autoCorrect={false}
          onChangeText={setSearchQuery}
          placeholder="Search themes or aliases"
          placeholderTextColor={Theme.colors.textMuted}
          style={styles.searchInput}
          value={searchQuery}
        />
        <View style={styles.selectorActions}>
          <Pressable accessibilityRole="button" onPress={() => updateState({ selectedThemeIds: selectAllThemeOptions(viewState.selectedThemeIds, selectorOptions.map((item) => item.id)) })} style={styles.toolbarButton}>
            <Text style={styles.toolbarButtonText}>Select all visible</Text>
          </Pressable>
          <Pressable accessibilityRole="button" onPress={() => updateState({ selectedThemeIds: [] })} style={styles.toolbarButton}>
            <Text style={styles.toolbarButtonText}>Clear selection</Text>
          </Pressable>
          {savedThemeIds.size ? (
            <Pressable accessibilityRole="button" onPress={() => updateState({ selectedThemeIds: selectAllThemeOptions(viewState.selectedThemeIds, [...savedThemeIds]) })} style={styles.toolbarButton}>
              <Text style={styles.toolbarButtonText}>Load saved themes</Text>
            </Pressable>
          ) : null}
        </View>
        <Text style={styles.counts}>{viewState.selectedThemeIds.length} selected</Text>
        {warning ? <Text style={styles.warning}>{warning}</Text> : null}
        <View style={styles.results}>
          {selectorOptions.map((item) => {
            const selected = viewState.selectedThemeIds.includes(item.id);
            const available = plottableIds.has(item.id);
            return (
              <View key={item.id} style={styles.resultRow}>
                <Pressable
                  accessibilityLabel={`${selected ? 'Deselect' : 'Select'} ${item.name}. ${available ? 'Available' : 'Unavailable for plotting'}.`}
                  accessibilityRole="checkbox"
                  accessibilityState={{ checked: selected }}
                  onPress={() => updateState({ selectedThemeIds: toggleThemeSelection(viewState.selectedThemeIds, item.id) })}
                  style={styles.resultMain}>
                  <Text style={styles.resultName}>{selected ? '✓ ' : ''}{item.name}</Text>
                  <Text style={styles.resultMeta}>{available ? `${item.parentSectorIds.map(title).join(', ') || 'Cross-sector'} · ${item.rank ? `#${item.rank}` : 'Unranked'}` : `${item.status} · will not plot invalid coordinates`}</Text>
                </Pressable>
                {available ? <Pressable accessibilityLabel={`Focus ${item.name}`} accessibilityRole="button" onPress={() => { enterFocus(item.id); setSelectorVisible(false); }} style={styles.focusButton}><Text style={styles.focusButtonText}>Focus</Text></Pressable> : null}
              </View>
            );
          })}
        </View>
        {viewState.selectedThemeIds.length >= 2 ? (
          <Pressable accessibilityLabel={`Compare ${viewState.selectedThemeIds.length} selected themes`} accessibilityRole="button" onPress={() => { updateState({ focusedThemeId: null, labelMode: 'selected', mode: 'compare', movement: 'all', quadrant: 'all', tailLength: '8', transition: 'all', universe: 'custom' }); onQuadrantChange('all'); setSelectorVisible(false); }} style={styles.primaryButton}>
            <Text style={styles.primaryButtonText}>Compare selected themes</Text>
          </Pressable>
        ) : <Text style={styles.disclosure}>Select at least 2 themes to enter Compare mode.</Text>}
      </DetailModal>
    </View>
  );
}

function FilterModal({
  onClose,
  onLabel,
  onQuadrant,
  onState,
  onUniverse,
  state,
  visible,
}: {
  onClose: () => void;
  onLabel: (mode: RotationLabelMode) => void;
  onQuadrant: (quadrant: ThemeRotationQuadrantFilter) => void;
  onState: (patch: Partial<ThemeRotationViewState>) => void;
  onUniverse: (universe: ThemeRotationUniverse) => void;
  state: ThemeRotationViewState;
  visible: boolean;
}) {
  return (
    <DetailModal visible={visible} title="Theme Rotation Filters" subtitle="Presentation filters never change canonical coordinates." onClose={onClose}>
      <SegmentedControl label="Universe" options={THEME_ROTATION_UNIVERSE_OPTIONS} selectedKey={state.universe} wrap onChange={(value) => onUniverse(value as ThemeRotationUniverse)} />
      <SegmentedControl label="Current quadrant" options={QUADRANT_OPTIONS} selectedKey={state.quadrant} wrap onChange={(value) => onQuadrant(value as ThemeRotationQuadrantFilter)} />
      <SegmentedControl label="Movement" options={MOVEMENT_OPTIONS} selectedKey={state.movement} wrap onChange={(value) => onState({ movement: value as ThemeRotationMovementFilter })} />
      <SegmentedControl label="Latest transition" options={TRANSITION_OPTIONS} selectedKey={state.transition} wrap onChange={(value) => onState({ transition: value as ThemeRotationTransitionFilter })} />
      <SegmentedControl label="Tail length" options={TAIL_OPTIONS} selectedKey={state.tailLength} wrap onChange={(value) => onState({ tailLength: value as ThemeRotationTailLength })} />
      <SegmentedControl label="Labels" options={LABEL_OPTIONS} selectedKey={state.labelMode} wrap onChange={(value) => onLabel(value as RotationLabelMode)} />
      {state.mode === 'focus' ? <SegmentedControl label="Focus context" options={[{ key: 'faint', label: 'Faint context' }, { key: 'hidden', label: 'Hidden' }]} selectedKey={state.focusContext} onChange={(value) => onState({ focusContext: value as ThemeRotationFocusContext })} /> : null}
    </DetailModal>
  );
}

function FocusDetails({
  onCompareRelated,
  onExit,
  onOpen,
  onRelated,
  onSave,
  point,
  relatedNames,
  saved,
  showRelated,
}: {
  onCompareRelated: () => void;
  onExit: () => void;
  onOpen: () => void;
  onRelated: () => void;
  onSave: () => void;
  point: CanonicalThemeRotationPoint;
  relatedNames: string[];
  saved: boolean;
  showRelated: boolean;
}) {
  const transition = point.latestQuadrantTransition;
  const confidence = typeof point.confidence.label === 'string' ? point.confidence.label : 'Undisclosed';
  return (
    <DashboardCard title={`${point.displayName} Focus`} subtitle="The full governed tail is emphasized; context themes are presentation-only.">
      <View style={styles.badges}>
        <StatusBadge label={title(point.quadrant)} tone={point.quadrant === 'leading' ? 'success' : point.quadrant === 'improving' ? 'info' : point.quadrant === 'weakening' ? 'warning' : 'muted'} />
        {saved ? <StatusBadge label="Saved" tone="info" /> : null}
      </View>
      <View style={styles.detailGrid}>
        <DetailValue label="Relative Trend" value={point.relativeTrend.toFixed(2)} />
        <DetailValue label="Relative Momentum" value={point.relativeMomentum.toFixed(2)} />
        <DetailValue label="Direction" value={title(point.direction)} />
        <DetailValue label="Speed" value={point.speed.toFixed(3)} />
        <DetailValue label="Tail" value={`${point.history.length} points`} />
        <DetailValue label="Latest transition" value={transition ? `${title(transition.from)} → ${title(transition.to)}` : 'Insufficient history'} />
        <DetailValue label="Rank" value={point.rank ? `#${point.rank}` : 'N/A'} />
        <DetailValue label="Confidence" value={title(confidence)} />
        <DetailValue label="As of" value={point.asOf} />
      </View>
      <Text style={styles.disclosure}>{point.partialCoverageDisclosure ?? `Coverage ${point.coverageRatio === null ? 'N/A' : `${Math.round(point.coverageRatio * 100)}%`}.`}</Text>
      {showRelated && relatedNames.length ? <Text style={styles.relatedText}>Related: {relatedNames.join(', ')}</Text> : null}
      <View style={styles.actionWrap}>
        <Action label="Exit Focus" onPress={onExit} />
        <Action label={showRelated ? 'Hide related themes' : 'Show related themes'} onPress={onRelated} />
        <Action label="Compare with related" onPress={onCompareRelated} />
        <Action label="Open Theme Detail" onPress={onOpen} />
        <Action label={saved ? 'Unsave theme' : 'Save theme'} onPress={onSave} />
      </View>
    </DashboardCard>
  );
}

function CompareSummary({ points, onRemove }: { points: CanonicalThemeRotationPoint[]; onRemove: (themeId: string) => void }) {
  return (
    <DashboardCard title={`Compare Summary · ${points.length} themes`} subtitle="Current governed metrics; the chart domain remains based on the full canonical response.">
      <View style={styles.results}>
        {points.map((point) => (
          <View key={point.themeId} style={styles.compareRow}>
            <View style={styles.resultMain}>
              <Text style={styles.resultName}>{point.displayName}</Text>
              <Text style={styles.resultMeta}>{title(point.quadrant)} · Trend {point.relativeTrend.toFixed(2)} · Momentum {point.relativeMomentum.toFixed(2)} · {title(point.direction)} · Speed {point.speed.toFixed(3)} · Distance {point.distanceTravelled.toFixed(3)} · {point.rank ? `#${point.rank}` : 'N/A'}</Text>
            </View>
            <Pressable accessibilityLabel={`Remove ${point.displayName} from comparison`} accessibilityRole="button" onPress={() => onRemove(point.themeId)} style={styles.focusButton}><Text style={styles.focusButtonText}>Remove</Text></Pressable>
          </View>
        ))}
      </View>
    </DashboardCard>
  );
}

function DetailValue({ label, value }: { label: string; value: string }) {
  return <View style={styles.detailValue}><Text style={styles.detailLabel}>{label}</Text><Text style={styles.detailText}>{value}</Text></View>;
}

function Action({ label, onPress }: { label: string; onPress: () => void }) {
  return <Pressable accessibilityLabel={label} accessibilityRole="button" onPress={onPress} style={styles.toolbarButton}><Text style={styles.toolbarButtonText}>{label}</Text></Pressable>;
}

function title(value: string) {
  return value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
}

const styles = StyleSheet.create({
  actionWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.two, marginTop: Spacing.three },
  badges: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.two, marginBottom: Spacing.two },
  compareRow: { alignItems: 'center', borderTopColor: Theme.colors.border, borderTopWidth: 1, flexDirection: 'row', gap: Spacing.two, paddingVertical: Spacing.two },
  counts: { color: Theme.colors.text, fontSize: 12, fontWeight: '900' },
  detailGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.two },
  detailLabel: { color: Theme.colors.textMuted, fontSize: 10, fontWeight: '900', textTransform: 'uppercase' },
  detailText: { color: Theme.colors.text, fontSize: 13, fontWeight: '900' },
  detailValue: { backgroundColor: Theme.colors.backgroundMuted, borderColor: Theme.colors.border, borderRadius: Theme.radii.small, borderWidth: 1, flexBasis: 140, flexGrow: 1, gap: Spacing.one, padding: Spacing.two },
  disclosure: { color: Theme.colors.textMuted, fontSize: 12, lineHeight: 18 },
  focusButton: { alignItems: 'center', borderColor: Theme.colors.accent, borderRadius: Theme.radii.small, borderWidth: 1, justifyContent: 'center', minHeight: 44, paddingHorizontal: Spacing.two },
  focusButtonText: { color: Theme.colors.accent, fontSize: 12, fontWeight: '900' },
  linkButton: { justifyContent: 'center', minHeight: 44, paddingHorizontal: Spacing.two },
  linkText: { color: Theme.colors.accent, fontSize: 12, fontWeight: '900' },
  notice: { alignItems: 'center', backgroundColor: Theme.colors.accentSoft, borderColor: Theme.colors.accent, borderRadius: Theme.radii.small, borderWidth: 1, flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.two, justifyContent: 'space-between', padding: Spacing.two },
  noticeAction: { alignItems: 'center', minHeight: 44, justifyContent: 'center', paddingHorizontal: Spacing.two },
  noticeActionText: { color: Theme.colors.accent, fontSize: 12, fontWeight: '900' },
  noticeText: { color: Theme.colors.text, flex: 1, fontSize: 12, lineHeight: 18, minWidth: 180 },
  primaryButton: { alignItems: 'center', backgroundColor: Theme.colors.accent, borderRadius: Theme.radii.small, justifyContent: 'center', minHeight: 48, paddingHorizontal: Spacing.three },
  primaryButtonText: { color: Theme.colors.background, fontSize: 13, fontWeight: '900' },
  relatedText: { color: Theme.colors.text, fontSize: 12, lineHeight: 18, marginTop: Spacing.two },
  resultMain: { flex: 1, gap: Spacing.one, minWidth: 0 },
  resultMeta: { color: Theme.colors.textMuted, fontSize: 11, lineHeight: 16 },
  resultName: { color: Theme.colors.text, fontSize: 13, fontWeight: '900' },
  resultRow: { alignItems: 'center', backgroundColor: Theme.colors.cardMuted, borderColor: Theme.colors.border, borderRadius: Theme.radii.small, borderWidth: 1, flexDirection: 'row', gap: Spacing.two, minHeight: 52, padding: Spacing.two },
  results: { gap: Spacing.two },
  searchInput: { backgroundColor: Theme.colors.backgroundMuted, borderColor: Theme.colors.border, borderRadius: Theme.radii.small, borderWidth: 1, color: Theme.colors.text, fontSize: 15, minHeight: 48, paddingHorizontal: Spacing.three },
  selectorActions: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.two },
  stack: { gap: Spacing.three },
  summaryChip: { backgroundColor: Theme.colors.cardMuted, borderColor: Theme.colors.border, borderRadius: Theme.radii.pill, borderWidth: 1, paddingHorizontal: Spacing.two, paddingVertical: Spacing.one },
  summaryChips: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.one },
  summaryChipText: { color: Theme.colors.textMuted, fontSize: 10, fontWeight: '900' },
  toolbar: { alignItems: 'center', flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.two },
  toolbarButton: { alignItems: 'center', backgroundColor: Theme.colors.cardMuted, borderColor: Theme.colors.border, borderRadius: Theme.radii.small, borderWidth: 1, justifyContent: 'center', minHeight: 44, paddingHorizontal: Spacing.two },
  toolbarButtonText: { color: Theme.colors.text, fontSize: 12, fontWeight: '900' },
  warning: { color: Theme.colors.warning, fontSize: 12, lineHeight: 18 },
});
