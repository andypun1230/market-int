import { useMemo, useState } from "react";
import { useLocalSearchParams, useRouter } from "expo-router";
import { SymbolView } from "expo-symbols";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { DashboardCard } from "@/components/cards/DashboardCard";
import { PerformanceHeatmap } from "@/components/charts/PerformanceHeatmap";
import { RotationQuadrantChart } from "@/components/charts/RotationQuadrantChart";
import { AppScreen } from "@/components/ui/AppScreen";
import { DetailModal } from "@/components/ui/DetailModal";
import { EmptyState } from "@/components/ui/EmptyState";
import { MetricTile } from "@/components/ui/MetricTile";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { AlertList } from "@/components/ui/AlertList";
import { Spacing, Theme } from "@/constants/theme";
import { AskCopilotButton } from "@/features/copilot/components/AskCopilotButton";
import { createCopilotContext } from "@/features/copilot/context/buildScreenContext";
import { EntityCatalystsCard } from "@/features/context-intelligence/components/ContextIntelligenceCards";
import {
  SECTOR_TAB_TEST_SEED,
  TEST_HEATMAP_INTERVALS,
  TEST_ROTATION_INTERVALS,
  buildRotationAlerts,
  type SectorThemeTestItem,
  type TestThemeItem,
} from "@/data/sectorTabTestData";
import { SectorDetailContent } from "@/features/sectors/components/SectorDetailContent";
import { SectorThemeComparisonView } from "@/features/sectors/components/SectorThemeComparisonView";
import { SectorThemeFilterPanel } from "@/features/sectors/components/SectorThemeFilterPanel";
import { SectorThemeSearchModal } from "@/features/sectors/components/SectorThemeSearchModal";
import { ThemeRotationExperience } from "@/features/themes/components/ThemeRotationExperience";
import {
  DEFAULT_SECTOR_THEME_FILTERS,
  countActiveFilters,
  filterSectorThemeItems,
  type SectorThemeFilters,
} from "@/features/sectors/analysis/filters";
import { createTestSectorThemeRepository } from "@/features/sectors/repository/sectorThemeRepository";
import {
  formatClassification,
  formatCoverage,
  formatNullablePercent,
  normalizeSectorId,
  sourceLabel,
  type SectorId,
  type SectorRow,
} from "@/features/sectors/sectorSnapshot";
import { buildRotationChartSectors } from "@/features/sectors/rotationAvailability";
import { presentSnapshotAlerts } from "@/features/sectors/sectorAlertPresenter";
import { buildSectorThemeSearchItems } from "@/features/sectors/sectorThemeSearchModel";
import {
  selectCanonicalAtRiskSectors,
  selectCanonicalEmergingSectors,
} from "@/features/sectors/analysis/scanners";
import {
  formatThemeRole,
  formatThemeTaxonomyLabel,
} from "@/features/themes/presentation";
import { themeTabProvenance } from "@/features/themes/themeProvenance";
import {
  type LiveThemeItem,
  type ThemeOverlap,
} from "@/features/themes/themeSnapshot";
import { themeGovernancePresentation } from "@/features/themes/themeStatus";
import { useSectorUiPreferences } from "@/features/sectors/state/sectorUiPreferences";
import { WatchlistBookmarkButton } from "@/features/watchlist/WatchlistBookmarkButton";
import { rotationTrailHistoryDisclosure } from "@/features/sectors/rotationCopy";
import { buildWatchlistKey, useWatchlist } from "@/features/watchlist/store";
import {
  useSectorRotationTrails,
  useSectorSnapshot,
} from "@/hooks/useSectorSnapshot";
import { useThemeSnapshot } from "@/hooks/useThemeSnapshot";
import { useThemeRotation } from "@/hooks/useThemeRotation";
import { useThemeStatus } from "@/hooks/useThemeStatus";
import { areTestScenariosEnabled } from "@/services/runtimeConfig";

type ActiveCategory = "sectors" | "themes" | "signals";
type ActiveSection =
  | "sectorHeatmap"
  | "sectorRotation"
  | "sectorAlerts"
  | "themesHeatmap"
  | "themesRotation"
  | "themeAlerts"
  | "emergingLeadership"
  | "leadershipRisk";
type SelectedDetail =
  | { kind: "sector"; sectorId: SectorId }
  | { item: TestThemeItem | LiveThemeItem; kind: "theme" }
  | null;

const CATEGORY_OPTIONS: { key: ActiveCategory; label: string }[] = [
  { key: "sectors", label: "Sectors" },
  { key: "themes", label: "Themes" },
  { key: "signals", label: "Signals" },
];
const CONTENT_OPTIONS: Record<
  ActiveCategory,
  { key: ActiveSection; label: string }[]
> = {
  sectors: [
    { key: "sectorHeatmap", label: "Heatmap" },
    { key: "sectorRotation", label: "Rotation" },
    { key: "sectorAlerts", label: "Alerts" },
  ],
  themes: [
    { key: "themesHeatmap", label: "Heatmap" },
    { key: "themesRotation", label: "Rotation" },
    { key: "themeAlerts", label: "Alerts" },
  ],
  signals: [
    { key: "emergingLeadership", label: "Emerging" },
    { key: "leadershipRisk", label: "At Risk" },
  ],
};

export default function SectorsScreen() {
  const router = useRouter();
  const {
    actionNonce: actionNonceParam,
    entityId: entityIdParam,
    entityKind: entityKindParam,
    entityName: entityNameParam,
    section: sectionParam,
  } = useLocalSearchParams<{
    actionNonce?: string | string[];
    entityId?: string | string[];
    entityKind?: string | string[];
    entityName?: string | string[];
    section?: string | string[];
  }>();
  const { snapshot, loading, error, refetch } = useSectorSnapshot();
  const testScenariosEnabled = areTestScenariosEnabled();
  const { status: themeStatus } = useThemeStatus(!testScenariosEnabled);
  const { snapshot: themeSnapshot } = useThemeSnapshot(!testScenariosEnabled);
  const [preferences, updatePreferences] = useSectorUiPreferences();
  const requestedSection = firstActiveSection(sectionParam);
  const activeSection =
    requestedSection ?? (preferences.activeSection as ActiveSection);
  const activeCategory = categoryForSection(activeSection);
  const {
    rotation,
    loading: sectorRotationLoading,
    error: sectorRotationError,
  } = useSectorRotationTrails(
    preferences.sectorRotationInterval,
    snapshot,
    activeSection === "sectorRotation",
  );
  const {
    rotation: themeRotation,
    loading: themeRotationLoading,
    error: themeRotationError,
  } = useThemeRotation(
    preferences.themeRotationInterval,
    themeSnapshot,
    !testScenariosEnabled && activeSection === "themesRotation",
  );
  const [selectedOverride, setSelected] = useState<SelectedDetail>(null);
  const [dismissedDeepLinkKey, setDismissedDeepLinkKey] = useState<
    string | null
  >(null);
  const [comparisonVisible, setComparisonVisible] = useState(false);
  const [filterVisible, setFilterVisible] = useState(false);
  const [filtersBySection, setFiltersBySection] = useState<
    Partial<Record<ActiveSection, SectorThemeFilters>>
  >({});
  const [searchVisible, setSearchVisible] = useState(false);
  const [comparisonItems, setComparisonItems] = useState<SectorThemeTestItem[]>(
    [],
  );
  const watchlist = useWatchlist();
  const themeRepository = useMemo(
    () =>
      testScenariosEnabled
        ? createTestSectorThemeRepository(SECTOR_TAB_TEST_SEED)
        : null,
    [testScenariosEnabled],
  );
  const themes = useMemo(
    () => themeRepository?.getThemes() ?? [],
    [themeRepository],
  );
  const modelItems = useMemo(
    () => themeRepository?.getAllItems() ?? [],
    [themeRepository],
  );
  const activeFilters =
    filtersBySection[activeSection] ?? DEFAULT_SECTOR_THEME_FILTERS;
  const watchlistKeys = useMemo(
    () =>
      new Set(
        watchlist.groupItems.map((item) =>
          buildWatchlistKey(item.type, item.id),
        ),
      ),
    [watchlist.groupItems],
  );
  const filteredThemes = useMemo(
    () =>
      filterSectorThemeItems(
        themes,
        activeFilters,
        preferences.themeHeatmapInterval,
        watchlistKeys,
      ) as TestThemeItem[],
    [activeFilters, preferences.themeHeatmapInterval, themes, watchlistKeys],
  );
  const rows = useMemo(() => snapshot?.sectors ?? [], [snapshot]);
  const rotationItems = useMemo(
    () =>
      buildRotationChartSectors(
        rotation,
        preferences.sectorRotationInterval,
        new Map(rows.map((row) => [row.sectorId, row.rank])),
      ),
    [preferences.sectorRotationInterval, rotation, rows],
  );
  const emerging = useMemo(() => selectCanonicalEmergingSectors(rows), [rows]);
  const risk = useMemo(() => selectCanonicalAtRiskSectors(rows), [rows]);
  const themeAlerts = useMemo(
    () => buildRotationAlerts(themes, preferences.themeRotationInterval),
    [preferences.themeRotationInterval, themes],
  );
  const liveThemes = useMemo(() => themeSnapshot?.items ?? [], [themeSnapshot]);
  const searchItems = useMemo(
    () =>
      buildSectorThemeSearchItems({
        sectors: rows,
        testItems: modelItems,
        themes: liveThemes,
      }),
    [liveThemes, modelItems, rows],
  );
  const themeRotationPoints = useMemo(
    () => themeRotation?.points ?? [],
    [themeRotation],
  );
  const themeProvenance = themeTabProvenance(themeSnapshot);
  const title =
    activeCategory === "themes"
      ? "Themes"
      : activeCategory === "signals"
        ? "Signals"
        : "Sectors";
  const subtitle =
    activeCategory === "themes"
      ? themeProvenance.subtitle
      : snapshot
        ? `S&P 100 sector snapshot · ${snapshot.marketDate}`
        : loading
          ? "Loading durable sector snapshot."
          : "Sector snapshot unavailable.";

  const deepLinkKey = `${firstParam(entityKindParam)}:${firstParam(entityIdParam)}:${firstParam(entityNameParam)}:${firstParam(actionNonceParam)}`;
  const deepLinkedSelection = useMemo<SelectedDetail>(() => {
    if (dismissedDeepLinkKey === deepLinkKey) return null;
    const entityKind = firstParam(entityKindParam);
    const entityId = firstParam(entityIdParam);
    const entityName = firstParam(entityNameParam);
    if (entityKind === "sector") {
      const sectorId =
        normalizeSectorId(entityId) ?? normalizeSectorId(entityName);
      return sectorId ? { kind: "sector", sectorId } : null;
    }
    if (entityKind === "theme") {
      if (activeSection === "themesRotation") return null;
      const candidates: (TestThemeItem | LiveThemeItem)[] = testScenariosEnabled
        ? themes
        : liveThemes;
      const item = candidates.find(
        (candidate) =>
          candidate.id.toLowerCase() === entityId.toLowerCase() ||
          candidate.name.toLowerCase() === entityName.toLowerCase(),
      );
      return item ? { item, kind: "theme" } : null;
    }
    return null;
  }, [
    deepLinkKey,
    dismissedDeepLinkKey,
    entityIdParam,
    entityKindParam,
    entityNameParam,
    liveThemes,
    testScenariosEnabled,
    themes,
    activeSection,
  ]);
  const selected = selectedOverride ?? deepLinkedSelection;
  const copilotContext = useMemo(
    () =>
      createCopilotContext({
        payload: {
          activeSection,
          sectorCount: rows.length,
          snapshotId: snapshot?.snapshotId,
          themeCount: liveThemes.length,
        },
        routeName: "/sectors",
        screenTitle: `${title} · ${activeSection}`,
        screenType: activeCategory === "themes" ? "theme" : "sector",
        sourceState:
          activeCategory === "themes"
            ? themeSnapshot?.sourceState
            : snapshot?.sourceState,
      }),
    [
      activeCategory,
      activeSection,
      liveThemes.length,
      rows.length,
      snapshot,
      themeSnapshot,
      title,
    ],
  );

  return (
    <AppScreen
      copilotContext={copilotContext}
      copilotPrompt={`Explain the ${title.toLowerCase()} ${activeSection} view and the clearest signal.`}
      title={title}
      subtitle={subtitle}
    >
      <View style={styles.stack}>
        {activeCategory === "themes" ? (
          themeProvenance.badges.length ? (
            <View style={styles.badges}>
              {themeProvenance.badges.map((label, index) => (
                <StatusBadge
                  key={label}
                  label={label}
                  tone={
                    index === 0 ? "info" : index === 1 ? "success" : "muted"
                  }
                />
              ))}
            </View>
          ) : null
        ) : snapshot ? (
          <View style={styles.badges}>
            <StatusBadge label="S&P 100" tone="info" />
            <StatusBadge
              label={`${formatCoverage(snapshot.coverage.constituentCoverage)} coverage`}
              tone="success"
            />
            <StatusBadge label={sourceLabel(snapshot)} tone="muted" />
          </View>
        ) : null}
        <SectorNavigation
          activeCategory={activeCategory}
          activeSection={activeSection}
          activeFilterCount={countActiveFilters(activeFilters)}
          comparisonEnabled={testScenariosEnabled}
          filterEnabled={testScenariosEnabled}
          onCategoryChange={(category) => {
            router.setParams({ commandTarget: undefined, section: undefined });
            updatePreferences({
              activeSection: defaultSectionForCategory(category, activeSection),
            });
          }}
          onCompare={() => setComparisonVisible(true)}
          onFilter={() => setFilterVisible((visible) => !visible)}
          onSearch={() => setSearchVisible(true)}
          onSectionChange={(section) => {
            router.setParams({ commandTarget: undefined, section: undefined });
            updatePreferences({ activeSection: section });
          }}
        />

        {filterVisible ? (
          <SectorThemeFilterPanel
            filters={activeFilters}
            onChange={(filters) =>
              setFiltersBySection((current) => ({
                ...current,
                [activeSection]: filters,
              }))
            }
          />
        ) : null}

        {!snapshot &&
        !loading &&
        activeCategory !== "themes" &&
        !(activeSection === "sectorRotation" && rotationItems.length) ? (
          <EmptyState
            title="Sector snapshot unavailable"
            message={
              error ??
              "The last-known-good sector snapshot could not be loaded."
            }
            actionLabel="Retry"
            onAction={refetch}
          />
        ) : null}

        {activeSection === "sectorHeatmap" && snapshot ? (
          <DashboardCard
            title="Sector Heatmap"
            subtitle="Tiles show ETF return for the selected interval. Rank reflects the overall leadership composite."
            accentColor={Theme.colors.success}
          >
            <IntervalTabs
              value={preferences.sectorHeatmapInterval}
              onChange={(sectorHeatmapInterval) =>
                updatePreferences({ sectorHeatmapInterval })
              }
            />
            <PerformanceHeatmap
              emptyLabel="No sectors have data for this interval."
              getName={(row) => row.displayName}
              getSubtitle={(row) =>
                `${row.etfSymbol} · #${row.rank} · ${formatClassification(row.classification)}`
              }
              getValue={(row) => row.returns[preferences.sectorHeatmapInterval]}
              items={rows}
              onPressItem={(row) =>
                setSelected({ kind: "sector", sectorId: row.sectorId })
              }
            />
            <Text style={styles.note}>
              Rank = overall relative position. Classification = current
              rotation state. Unavailable ETF history is shown as N/A.
            </Text>
          </DashboardCard>
        ) : null}

        {activeSection === "sectorRotation" && snapshot ? (
          <DashboardCard
            title="Sector Rotation Map"
            subtitle="Original transparent benchmark-relative trend and momentum model. Unavailable sectors are excluded."
            accentColor={Theme.colors.accent}
          >
            <SectorRotationProfileTabs
              value={preferences.sectorRotationInterval}
              onChange={(sectorRotationInterval) =>
                updatePreferences({ sectorRotationInterval })
              }
            />
            <Text style={styles.note}>
              Short, Medium, and Long select governed model profiles, not simple
              return windows.
            </Text>
            {sectorRotationLoading && !rotation ? (
              <Text style={styles.note}>
                Loading canonical Sector Rotation.
              </Text>
            ) : null}
            {sectorRotationError ? (
              <Text style={styles.note}>
                Sector Rotation unavailable: {sectorRotationError}
              </Text>
            ) : null}
            {rotation ? (
              rotationItems.length ? (
                <RotationQuadrantChart
                  benchmark={rotation.benchmark}
                  getHistory={(row) =>
                    rotation.seriesBySector.get(row.sectorId)?.[
                      preferences.sectorRotationInterval
                    ]?.trailPoints ?? []
                  }
                  getItemKey={(row) => row.sectorId}
                  getItemType={() => "sector"}
                  getLabel={(row) => row.etfSymbol}
                  getLabelPriority={(row) =>
                    (row.rank <= 3 ? 3000 - row.rank : 0) +
                    (rotation.movements.get(row.sectorId)?.direction ===
                    "gaining"
                      ? 1800
                      : rotation.movements.get(row.sectorId)?.direction ===
                          "losing"
                        ? 1600
                        : 0)
                  }
                  getName={(row) => row.displayName}
                  getRelativeMomentum={(row) =>
                    rotation.seriesBySector.get(row.sectorId)?.[
                      preferences.sectorRotationInterval
                    ]?.currentPoint?.relativeMomentum ?? null
                  }
                  getRelativeStrength={(row) =>
                    rotation.seriesBySector.get(row.sectorId)?.[
                      preferences.sectorRotationInterval
                    ]?.currentPoint?.relativeTrend ?? null
                  }
                  horizontalAxisLabel="Relative Trend"
                  indicatorDescription={`Relative Trend measures the smoothed trend of each sector ETF’s performance versus ${rotation.benchmark}. Relative Momentum measures whether that relative trend is accelerating or decelerating. · ${rotation.profile[0].toUpperCase()}${rotation.profile.slice(1)} profile`}
                  interpretationText="Above 100 means the benchmark-relative trend is strengthening; Relative Momentum above 100 means that trend is improving. Coordinates are not percentage returns."
                  interval={`${rotation.profile[0].toUpperCase()}${rotation.profile.slice(1)} profile`}
                  items={rotationItems}
                  labelMode={preferences.sectorRotationLabelMode}
                  onLabelModeChange={(sectorRotationLabelMode) =>
                    updatePreferences({ sectorRotationLabelMode })
                  }
                  onPressItem={(row) =>
                    setSelected({ kind: "sector", sectorId: row.sectorId })
                  }
                  onQuadrantFilterChange={(sectorRotationQuadrant) =>
                    updatePreferences({ sectorRotationQuadrant })
                  }
                  quadrantFilter={preferences.sectorRotationQuadrant}
                />
              ) : (
                <Text style={styles.note}>
                  No available sectors have governed {rotation.timeframe}{" "}
                  rotation metrics. {rotation.excludedCount} excluded.
                </Text>
              )
            ) : null}
            <RotationFlowSummary rotation={rotation} />
          </DashboardCard>
        ) : null}

        {activeSection === "sectorAlerts" && snapshot ? (
          <DashboardCard
            title="Rotation Alerts"
            accentColor={Theme.colors.warning}
          >
            <AlertList
              alerts={presentSnapshotAlerts(snapshot.alerts, "Sector")}
              emptyMessage="No transition alerts yet."
            />
          </DashboardCard>
        ) : null}

        {activeSection === "themesHeatmap" ? (
          testScenariosEnabled ? (
            <DashboardCard
              title="Theme Heatmap"
              subtitle="Test scenario data only; not live market intelligence."
              accentColor={Theme.colors.purple}
            >
              <View style={styles.themeSource}>
                <StatusBadge label="Test Data" tone="warning" />
                <Text style={styles.note}>
                  Theme inputs are not reviewed live data.
                </Text>
              </View>
              <IntervalTabs
                value={preferences.themeHeatmapInterval}
                onChange={(themeHeatmapInterval) =>
                  updatePreferences({ themeHeatmapInterval })
                }
              />
              <PerformanceHeatmap
                emptyLabel="No themes match the current configuration."
                getName={(item) => item.name}
                getSubtitle={(item) => item.parentSector}
                getValue={(item) =>
                  item.returns[preferences.themeHeatmapInterval]
                }
                items={filteredThemes}
                onPressItem={(item) => setSelected({ item, kind: "theme" })}
              />
            </DashboardCard>
          ) : liveThemes.length ? (
            <DashboardCard
              title="Theme Directory"
              subtitle="Canonical launch taxonomy with governed available, partial, and unavailable states."
              accentColor={Theme.colors.purple}
            >
              <IntervalTabs
                value={preferences.themeHeatmapInterval}
                onChange={(themeHeatmapInterval) =>
                  updatePreferences({ themeHeatmapInterval })
                }
              />
              <PerformanceHeatmap
                emptyLabel="No themes have governed data for this interval."
                getName={(item) => item.name}
                getSubtitle={(item) =>
                  `${item.parentSector} · ${item.rank === null ? item.status : `#${item.rank}`}`
                }
                getValue={(item) =>
                  item.returns[preferences.themeHeatmapInterval]
                }
                items={liveThemes}
                onPressItem={(item) => setSelected({ item, kind: "theme" })}
              />
              <Text style={styles.note}>
                {themeSnapshot?.pilotScope ??
                  "Only themes with published market evidence receive a rank."}{" "}
                Unavailable metrics remain N/A.
              </Text>
            </DashboardCard>
          ) : (
            <ThemeReviewGate status={themeStatus} />
          )
        ) : null}

        {activeSection === "themesRotation" ? (
          testScenariosEnabled ? (
            <DashboardCard
              title="Theme Rotation"
              subtitle="Test scenario trails - not live market intelligence."
              accentColor={Theme.colors.purple}
            >
              <View style={styles.themeSource}>
                <StatusBadge label="Test Data" tone="warning" />
                <Text style={styles.note}>
                  Generated fixture trails are available only in explicit
                  developer mode.
                </Text>
              </View>
              <RotationIntervalTabs
                value={preferences.themeRotationInterval}
                onChange={(themeRotationInterval) =>
                  updatePreferences({ themeRotationInterval })
                }
              />
              <RotationQuadrantChart
                benchmark="SPY"
                getHistory={(item) =>
                  item.rotation[preferences.themeRotationInterval].history
                }
                getItemKey={(item) => item.id}
                getItemType={() => "theme"}
                getName={(item) => item.name}
                getRelativeMomentum={(item) =>
                  item.rotation[preferences.themeRotationInterval]
                    .relativeMomentum
                }
                getRelativeStrength={(item) =>
                  item.rotation[preferences.themeRotationInterval]
                    .relativeStrength
                }
                interval={preferences.themeRotationInterval}
                items={themes}
                labelMode={preferences.themeRotationLabelMode}
                onLabelModeChange={(themeRotationLabelMode) =>
                  updatePreferences({ themeRotationLabelMode })
                }
                onPressItem={(item) => setSelected({ item, kind: "theme" })}
                onQuadrantFilterChange={(themeRotationQuadrant) =>
                  updatePreferences({ themeRotationQuadrant })
                }
                quadrantFilter={preferences.themeRotationQuadrant}
                showTestDataBadge
                trailLength={10}
              />
            </DashboardCard>
          ) : themeSnapshot ? (
            <DashboardCard
              title="Theme Rotation Map"
              subtitle="Original transparent benchmark-relative trend and momentum model. Unavailable themes are excluded."
              accentColor={Theme.colors.purple}
            >
              <ThemeRotationProfileTabs
                value={preferences.themeRotationInterval}
                onChange={(themeRotationInterval) =>
                  updatePreferences({ themeRotationInterval })
                }
              />
              <Text style={styles.note}>
                Short, Medium, and Long select governed model profiles, not
                simple return windows.
              </Text>
              {themeRotationLoading && !themeRotation ? (
                <Text style={styles.note}>
                  Loading canonical Theme Rotation.
                </Text>
              ) : null}
              {themeRotationError ? (
                <Text style={styles.note}>
                  Theme Rotation unavailable: {themeRotationError}
                </Text>
              ) : null}
              {themeRotation ? (
                themeRotationPoints.length ? (
                  <ThemeRotationExperience
                    initialFocusedThemeId={
                      firstParam(entityKindParam) === "theme"
                        ? firstParam(entityIdParam)
                        : null
                    }
                    initialLabelMode={preferences.themeRotationLabelMode}
                    initialMovement={preferences.themeRotationMovement}
                    initialQuadrant={preferences.themeRotationQuadrant}
                    initialTailLength={preferences.themeRotationTailLength}
                    initialUniverse={preferences.themeRotationUniverse}
                    onLabelModeChange={(themeRotationLabelMode) =>
                      updatePreferences({ themeRotationLabelMode })
                    }
                    onOpenThemeDetail={(point) => {
                      const item = liveThemes.find(
                        (theme) => theme.id === point.themeId,
                      );
                      if (item) setSelected({ item, kind: "theme" });
                    }}
                    onQuadrantChange={(themeRotationQuadrant) =>
                      updatePreferences({ themeRotationQuadrant })
                    }
                    onViewPreferenceChange={(patch) =>
                      updatePreferences({
                        ...(patch.movement
                          ? { themeRotationMovement: patch.movement }
                          : {}),
                        ...(patch.tailLength
                          ? { themeRotationTailLength: patch.tailLength }
                          : {}),
                        ...(patch.universe
                          ? { themeRotationUniverse: patch.universe }
                          : {}),
                      })
                    }
                    overlap={themeSnapshot.overlap}
                    rotation={themeRotation}
                    themes={liveThemes}
                  />
                ) : (
                  <Text style={styles.note}>
                    No available themes have governed {themeRotation.timeframe}{" "}
                    rotation metrics. {themeRotation.exclusions.length}{" "}
                    excluded.
                  </Text>
                )
              ) : null}
            </DashboardCard>
          ) : (
            <ThemeReviewGate status={themeStatus} />
          )
        ) : null}

        {activeSection === "themeAlerts" ? (
          testScenariosEnabled ? (
            <DashboardCard
              title="Theme Rotation Alerts"
              subtitle="Test scenario alerts - not live market intelligence."
              accentColor={Theme.colors.warning}
            >
              {themeAlerts.length ? (
                themeAlerts.map((alert) => (
                  <View key={alert.id} style={styles.alert}>
                    <Text style={styles.name}>{alert.name}</Text>
                    <Text style={styles.note}>{alert.message}</Text>
                  </View>
                ))
              ) : (
                <Text style={styles.note}>No theme rotation alerts.</Text>
              )}
            </DashboardCard>
          ) : liveThemes.length ? (
            <DashboardCard
              title="Theme Rotation Alerts"
              subtitle="Changes between immutable ThemeSnapshots."
              accentColor={Theme.colors.warning}
            >
              <AlertList
                alerts={presentSnapshotAlerts(themeSnapshot?.alerts ?? [], "Theme")}
                emptyMessage="No theme transition alerts yet. Further immutable snapshots are needed for change detection."
              />
            </DashboardCard>
          ) : (
            <ThemeReviewGate status={themeStatus} />
          )
        ) : null}

        {activeSection === "emergingLeadership" && snapshot ? (
          <Scanner
            title="Emerging Sectors"
            subtitle="Improving is the canonical classification; this list is not an overall ranking."
            rows={emerging}
            onOpen={(sectorId) => setSelected({ kind: "sector", sectorId })}
          />
        ) : null}
        {activeSection === "leadershipRisk" && snapshot ? (
          <Scanner
            title="At-Risk Sectors"
            subtitle="Leading sectors with deteriorating momentum or breadth qualify here."
            rows={risk}
            empty="No sectors currently meet the at-risk criteria."
            onOpen={(sectorId) => setSelected({ kind: "sector", sectorId })}
          />
        ) : null}
      </View>

      <DetailModal
        visible={Boolean(selected)}
        title={
          selected?.kind === "theme"
            ? selected.item.name
            : selected
              ? (snapshot?.sectors.find(
                  (row) => row.sectorId === selected.sectorId,
                )?.displayName ?? "Sector detail")
              : "Sector detail"
        }
        subtitle={
          selected?.kind === "theme"
            ? `Theme · ${selected.item.parentSector}`
            : snapshot
              ? `${snapshot.marketDate} · ${sourceLabel(snapshot)}`
              : undefined
        }
        onClose={() => {
          setSelected(null);
          setDismissedDeepLinkKey(deepLinkKey);
        }}
      >
        {selected?.kind === "sector" ? (
          <SectorDetailContent
            key={selected.sectorId}
            sectorId={selected.sectorId}
          />
        ) : null}
        {selected?.kind === "theme" ? (
          <ThemeDetailContent
            theme={selected.item}
            overlap={themeSnapshot?.overlap ?? []}
          />
        ) : null}
      </DetailModal>
      <SectorThemeSearchModal
        interval={
          activeCategory === "themes"
            ? preferences.themeHeatmapInterval
            : preferences.sectorHeatmapInterval
        }
        isVisible={searchVisible}
        items={searchItems}
        onClose={() => setSearchVisible(false)}
        onOpenItem={(item) => {
          setSearchVisible(false);
          if (item.type === "theme") {
            const theme = testScenariosEnabled
              ? themes.find((candidate) => candidate.id === item.id)
              : liveThemes.find((candidate) => candidate.id === item.id);
            if (theme) setSelected({ item: theme, kind: "theme" });
          } else {
            const sectorId = normalizeSectorId(item.id) ?? normalizeSectorId(item.name);
            if (sectorId) setSelected({ kind: "sector", sectorId });
          }
        }}
        onToggleWatchlist={(item) =>
          watchlist.toggleWatchlistItem({
            id: item.id,
            name: item.name,
            type: item.type,
          })
        }
        watchlistKeys={watchlistKeys}
      />
      <DetailModal
        visible={comparisonVisible}
        title="Compare Sectors & Themes"
        subtitle="Restored comparison configuration"
        onClose={() => setComparisonVisible(false)}
      >
        <SectorThemeComparisonView
          favourites={watchlistKeys}
          items={modelItems}
          onToggleFavourite={(item) =>
            watchlist.toggleWatchlistItem({
              id: item.id,
              name: item.name,
              type: item.type,
            })
          }
          selectedItems={comparisonItems}
          setSelectedItems={setComparisonItems}
        />
      </DetailModal>
    </AppScreen>
  );
}

function SectorNavigation({
  activeCategory,
  activeFilterCount,
  activeSection,
  comparisonEnabled,
  filterEnabled,
  onCategoryChange,
  onCompare,
  onFilter,
  onSearch,
  onSectionChange,
}: {
  activeCategory: ActiveCategory;
  activeFilterCount: number;
  activeSection: ActiveSection;
  comparisonEnabled: boolean;
  filterEnabled: boolean;
  onCategoryChange: (category: ActiveCategory) => void;
  onCompare: () => void;
  onFilter: () => void;
  onSearch: () => void;
  onSectionChange: (section: ActiveSection) => void;
}) {
  return (
    <View style={styles.navigation}>
      <View style={styles.navigationTopRow}>
        <View style={styles.categorySwitch}>
          {CATEGORY_OPTIONS.map((option) => (
            <Pressable
              accessibilityRole="button"
              accessibilityState={{ selected: activeCategory === option.key }}
              key={option.key}
              onPress={() => onCategoryChange(option.key)}
              style={[
                styles.categoryButton,
                activeCategory === option.key && styles.categoryButtonActive,
              ]}
            >
              <Text
                style={[
                  styles.categoryText,
                  activeCategory === option.key && styles.categoryTextActive,
                ]}
              >
                {option.label}
              </Text>
            </Pressable>
          ))}
        </View>
        <View style={styles.utilityToolbar}>
          <UtilityButton
            icon={{ android: "search", ios: "magnifyingglass", web: "search" }}
            label="Search"
            onPress={onSearch}
          />
          <UtilityButton
            disabled={!comparisonEnabled}
            icon={{
              android: "compare_arrows",
              ios: "rectangle.2.swap",
              web: "compare_arrows",
            }}
            label="Compare"
            onPress={onCompare}
          />
          <UtilityButton
            badge={activeFilterCount}
            disabled={!filterEnabled}
            icon={{ android: "tune", ios: "slider.horizontal.3", web: "tune" }}
            label="Filter and sort"
            onPress={onFilter}
          />
        </View>
      </View>
      <View style={styles.contentSwitch}>
        {CONTENT_OPTIONS[activeCategory].map((option) => (
          <Pressable
            accessibilityRole="button"
            accessibilityState={{ selected: activeSection === option.key }}
            key={option.key}
            onPress={() => onSectionChange(option.key)}
            style={[
              styles.contentButton,
              activeSection === option.key && styles.contentButtonActive,
            ]}
          >
            <Text
              style={[
                styles.contentText,
                activeSection === option.key && styles.contentTextActive,
              ]}
            >
              {option.label}
            </Text>
          </Pressable>
        ))}
      </View>
    </View>
  );
}

function UtilityButton({
  badge,
  disabled = false,
  icon,
  label,
  onPress,
}: {
  badge?: number;
  disabled?: boolean;
  icon: { android: string; ios: string; web: string };
  label: string;
  onPress: () => void;
}) {
  return (
    <Pressable
      accessibilityLabel={badge ? `${label}, ${badge} active filters` : label}
      accessibilityRole="button"
      accessibilityState={{ disabled }}
      disabled={disabled}
      onPress={onPress}
      style={({ pressed }) => [styles.utilityButton, disabled && styles.utilityButtonDisabled, pressed && styles.pressed]}
    >
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

function IntervalTabs({
  value,
  onChange,
}: {
  value: (typeof TEST_HEATMAP_INTERVALS)[number];
  onChange: (value: (typeof TEST_HEATMAP_INTERVALS)[number]) => void;
}) {
  return (
    <View style={styles.tabs}>
      {TEST_HEATMAP_INTERVALS.map((item) => (
        <Pressable
          key={item}
          onPress={() => onChange(item)}
          style={[styles.tab, value === item && styles.tabActive]}
        >
          <Text
            style={[styles.tabText, value === item && styles.tabTextActive]}
          >
            {item}
          </Text>
        </Pressable>
      ))}
    </View>
  );
}
function RotationIntervalTabs({
  value,
  onChange,
}: {
  value: (typeof TEST_ROTATION_INTERVALS)[number];
  onChange: (value: (typeof TEST_ROTATION_INTERVALS)[number]) => void;
}) {
  return (
    <View style={styles.tabs}>
      {TEST_ROTATION_INTERVALS.map((item) => (
        <Pressable
          key={item}
          onPress={() => onChange(item)}
          style={[styles.tab, value === item && styles.tabActive]}
        >
          <Text
            style={[styles.tabText, value === item && styles.tabTextActive]}
          >
            {item}
          </Text>
        </Pressable>
      ))}
    </View>
  );
}
function SectorRotationProfileTabs({
  value,
  onChange,
}: {
  value: (typeof TEST_ROTATION_INTERVALS)[number];
  onChange: (value: (typeof TEST_ROTATION_INTERVALS)[number]) => void;
}) {
  const options = [
    { key: "1W", label: "Short" },
    { key: "1M", label: "Medium" },
    { key: "3M", label: "Long" },
  ] as const;
  return (
    <View
      accessibilityLabel="Sector Rotation model profile"
      style={styles.tabs}
    >
      {options.map((item) => (
        <Pressable
          accessibilityRole="button"
          accessibilityState={{ selected: value === item.key }}
          key={item.key}
          onPress={() => onChange(item.key)}
          style={[styles.tab, value === item.key && styles.tabActive]}
        >
          <Text
            style={[styles.tabText, value === item.key && styles.tabTextActive]}
          >
            {item.label}
          </Text>
        </Pressable>
      ))}
    </View>
  );
}
function ThemeRotationProfileTabs({
  value,
  onChange,
}: {
  value: (typeof TEST_ROTATION_INTERVALS)[number];
  onChange: (value: (typeof TEST_ROTATION_INTERVALS)[number]) => void;
}) {
  const options = [
    { key: "1W", label: "Short" },
    { key: "1M", label: "Medium" },
    { key: "3M", label: "Long" },
  ] as const;
  return (
    <View accessibilityLabel="Theme Rotation model profile" style={styles.tabs}>
      {options.map((item) => (
        <Pressable
          accessibilityRole="button"
          accessibilityState={{ selected: value === item.key }}
          key={item.key}
          onPress={() => onChange(item.key)}
          style={[styles.tab, value === item.key && styles.tabActive]}
        >
          <Text
            style={[styles.tabText, value === item.key && styles.tabTextActive]}
          >
            {item.label}
          </Text>
        </Pressable>
      ))}
    </View>
  );
}

function RotationFlowSummary({
  rotation,
}: {
  rotation: ReturnType<typeof useSectorRotationTrails>["rotation"];
}) {
  if (!rotation?.movementAvailable)
    return <Text style={styles.note}>{rotationTrailHistoryDisclosure}</Text>;
  const groups = [
    ["Gaining leadership", rotation.flowGroups.gaining],
    ["Losing leadership", rotation.flowGroups.losing],
    ["Stable", rotation.flowGroups.stable],
  ] as const;
  return (
    <View style={styles.flow}>
      <Text style={styles.flowTitle}>Leadership flow</Text>
      {groups
        .filter(([, items]) => items.length)
        .map(([label, items]) => (
          <Text key={label} style={styles.note}>
            {label}: {items.map((item) => item.etfSymbol).join(", ")}
          </Text>
        ))}
    </View>
  );
}

function ThemeReviewGate({
  status,
}: {
  status: ReturnType<typeof useThemeStatus>["status"];
}) {
  const presentation = themeGovernancePresentation(status);
  return (
    <DashboardCard
      title={presentation.title}
      subtitle="Live Theme Heatmap, Rotation, and Alerts are intentionally gated."
      accentColor={Theme.colors.purple}
    >
      <View style={styles.detailStack}>
        <Text style={styles.note}>{presentation.body}</Text>
        {presentation.pilotThemes.map((theme) => (
          <Text key={theme.displayName} style={styles.body}>
            {theme.displayName} -{" "}
            {theme.reviewStatus === "awaiting_review"
              ? "Awaiting review"
              : theme.reviewStatus}
          </Text>
        ))}
        <Text style={styles.note}>{presentation.footer}</Text>
      </View>
    </DashboardCard>
  );
}

function ThemeDetailContent({
  theme,
  overlap,
}: {
  theme: TestThemeItem | LiveThemeItem;
  overlap: ThemeOverlap[];
}) {
  if ("sourceState" in theme)
    return (
      <View style={styles.detailStack}>
        <View style={styles.badges}>
          <StatusBadge
            label={
              theme.status === "available"
                ? "Available"
                : theme.status === "partial"
                  ? "Partial"
                  : "Unavailable"
            }
            tone={
              theme.status === "available"
                ? "success"
                : theme.status === "partial"
                  ? "warning"
                  : "muted"
            }
          />
          <WatchlistBookmarkButton
            id={theme.id}
            name={theme.name}
            type="theme"
          />
        </View>
        <AskCopilotButton
          context={createCopilotContext({
            payload: {
              theme_id: theme.id,
              display_name: theme.name,
              rank: theme.rank,
              composite_score: theme.compositeScore,
              performance: theme.returns,
              participation: theme.participation,
              concentration: theme.concentration,
              members: theme.members,
            },
            routeName: "/sectors",
            screenTitle: `${theme.name} Theme`,
            screenType: "theme",
            sourceState: theme.sourceState,
          })}
          prompt={`Why is ${theme.name} ${theme.classification.toLowerCase()}?`}
        />
        <EntityCatalystsCard
          enabled
          entityId={theme.id}
          key={theme.id}
          kind="theme"
        />
        <DashboardCard
          title="Theme Performance"
          accentColor={Theme.colors.purple}
        >
          <View style={styles.metricGrid}>
            {TEST_HEATMAP_INTERVALS.map((interval) => (
              <MetricTile
                key={interval}
                label={interval}
                value={formatNullablePercent(theme.returns[interval])}
              />
            ))}
          </View>
        </DashboardCard>
        <DashboardCard
          title="Theme Intelligence"
          subtitle="Reviewed definition and durable Polygon adjusted history."
          accentColor={Theme.colors.accent}
        >
          <View style={styles.metricGrid}>
            <MetricTile
              label="Rank"
              value={theme.rank ? `#${theme.rank}` : "N/A"}
            />
            <MetricTile
              label={theme.scoreSemantics.label ?? "Absolute composite score"}
              value={
                theme.compositeScore === null
                  ? "N/A"
                  : `${theme.compositeScore.toFixed(1)} / 100`
              }
            />
            <MetricTile
              label="Breadth Coverage"
              value={
                theme.coverageRatio === null
                  ? "N/A"
                  : `${Math.round(theme.coverageRatio * 100)}%`
              }
            />
            <MetricTile
              label="Participation score"
              value={
                theme.participation.score === null
                  ? "N/A"
                  : `${theme.participation.score.toFixed(1)} / 100`
              }
            />
            <MetricTile
              label="Positive-return participation"
              value={
                theme.participation.positiveReturnParticipationPct === null
                  ? "N/A"
                  : `${theme.participation.positiveReturnParticipationPct.toFixed(1)}%`
              }
            />
            <MetricTile label="Classification" value={theme.classification} />
          </View>
          <Text style={styles.note}>
            {theme.pilotScope ??
              theme.scoreSemantics.relativeRankScope ??
              "Rank is scoped to the active reviewed pilot themes."}
          </Text>
        </DashboardCard>
        <DashboardCard
          title="Concentration"
          subtitle="Absolute contribution shares over the participation horizon."
          accentColor={Theme.colors.warning}
        >
          <View style={styles.metricGrid}>
            <MetricTile
              label="Top contributor"
              value={theme.concentration.topContributors[0]?.ticker ?? "N/A"}
            />
            <MetricTile
              label="Top-one share"
              value={
                theme.concentration.topOneSharePct === null
                  ? "N/A"
                  : `${theme.concentration.topOneSharePct.toFixed(1)}%`
              }
            />
            <MetricTile
              label="Top-three share"
              value={
                theme.concentration.topThreeSharePct === null
                  ? "N/A"
                  : `${theme.concentration.topThreeSharePct.toFixed(1)}%`
              }
            />
            <MetricTile
              label="Concentration HHI"
              value={theme.concentration.hhi?.toFixed(2) ?? "N/A"}
            />
            <MetricTile
              label="Concentration"
              value={theme.concentration.classification ?? "N/A"}
            />
            <MetricTile
              label="Quality score"
              value={
                theme.concentration.qualityScore === null
                  ? "N/A"
                  : `${theme.concentration.qualityScore.toFixed(0)} / 100`
              }
            />
          </View>
        </DashboardCard>
        <DashboardCard
          title="Overlap"
          subtitle="Common approved members with the other active pilot theme."
          accentColor={Theme.colors.purple}
        >
          {overlap
            .filter(
              (item) =>
                item.leftThemeId === theme.id || item.rightThemeId === theme.id,
            )
            .map((item) => (
              <View
                key={`${item.leftThemeId}:${item.rightThemeId}`}
                style={styles.alert}
              >
                <Text style={styles.name}>
                  {formatThemeTaxonomyLabel(
                    item.leftThemeId === theme.id
                      ? item.rightThemeId
                      : item.leftThemeId,
                  )}
                </Text>
                <Text style={styles.note}>
                  Common members: {item.commonMembers.join(", ") || "None"} ·
                  Jaccard {item.jaccardOverlap?.toFixed(2) ?? "N/A"} · Weighted{" "}
                  {item.weightedOverlap?.toFixed(2) ?? "N/A"}
                </Text>
              </View>
            ))}
        </DashboardCard>
        <DashboardCard
          title="Constituents"
          subtitle={`${theme.memberCount ?? theme.members.length} current members · equal weight`}
          accentColor={Theme.colors.success}
        >
          {theme.members.map((member) => (
            <View key={member.ticker} style={styles.alert}>
              <Text style={styles.name}>
                {member.ticker} · {member.companyName}
              </Text>
              <Text style={styles.note}>
                {formatThemeRole(member.role)} · Purity {member.purity ?? "N/A"}{" "}
                · Importance{" "}
                {member.importance === null
                  ? "Not reviewed"
                  : member.importance}{" "}
                ·{" "}
                {member.weight === null
                  ? "N/A"
                  : `${(member.weight * 100).toFixed(2)}%`}
              </Text>
              <Text style={styles.note}>{member.inclusionReason}</Text>
              {member.previousTicker ? (
                <Text style={styles.note}>
                  Former identity: {member.previousTicker} /{" "}
                  {member.previousCompanyName ?? "Unavailable"} ·{" "}
                  {member.continuityStatus ?? "historical alias"}
                </Text>
              ) : null}
            </View>
          ))}
        </DashboardCard>
        <Text style={styles.note}>
          {theme.basketMethodology === "daily_rebalanced_equal_weight"
            ? "Daily-rebalanced equal-weight current reviewed basket."
            : "Reviewed current basket."}{" "}
          {theme.historicalDisclosure ?? ""}
        </Text>
      </View>
    );
  return (
    <View style={styles.detailStack}>
      <View style={styles.badges}>
        <StatusBadge label="Test Data" tone="warning" />
        <WatchlistBookmarkButton id={theme.id} name={theme.name} type="theme" />
      </View>
      <EntityCatalystsCard
        enabled={false}
        entityId={theme.id}
        forceTestContext
        kind="theme"
      />
      <DashboardCard
        title="Theme Performance"
        accentColor={Theme.colors.purple}
      >
        <View style={styles.metricGrid}>
          {TEST_HEATMAP_INTERVALS.map((interval) => (
            <MetricTile
              key={interval}
              label={interval}
              value={formatNullablePercent(theme.returns[interval])}
            />
          ))}
        </View>
      </DashboardCard>
      <DashboardCard
        title="Theme Rotation"
        subtitle="Test scenario trail - not live market intelligence."
        accentColor={Theme.colors.accent}
      >
        <View style={styles.metricGrid}>
          <MetricTile label="Parent Sector" value={theme.parentSector} />
          <MetricTile
            label="Relative Strength"
            value={theme.relativeStrength.toFixed(1)}
          />
          <MetricTile
            label="Relative Momentum"
            value={theme.relativeMomentum.toFixed(1)}
          />
          <MetricTile label="Quadrant" value={theme.quadrant} />
        </View>
      </DashboardCard>
    </View>
  );
}

function Scanner({
  title,
  subtitle,
  rows,
  empty = "No sectors match this scanner.",
  onOpen,
}: {
  title: string;
  subtitle: string;
  rows: SectorRow[];
  empty?: string;
  onOpen: (id: SectorId) => void;
}) {
  return (
    <DashboardCard
      title={title}
      subtitle={subtitle}
      accentColor={Theme.colors.purple}
    >
      {rows.length ? (
        rows.map((row) => (
          <Pressable
            key={row.sectorId}
            onPress={() => onOpen(row.sectorId)}
            style={styles.row}
          >
            <View>
              <Text style={styles.name}>
                #{row.rank} {row.displayName}
              </Text>
              <Text style={styles.note}>
                {row.etfSymbol} · {formatClassification(row.classification)}
              </Text>
            </View>
            <Text style={styles.value}>
              {row.compositeScore?.toFixed(2) ?? "N/A"}
            </Text>
          </Pressable>
        ))
      ) : (
        <Text style={styles.note}>{empty}</Text>
      )}
    </DashboardCard>
  );
}

function categoryForSection(section: ActiveSection): ActiveCategory {
  if (section.startsWith("themes") || section === "themeAlerts")
    return "themes";
  if (section === "emergingLeadership" || section === "leadershipRisk")
    return "signals";
  return "sectors";
}
function defaultSectionForCategory(
  category: ActiveCategory,
  current: ActiveSection,
): ActiveSection {
  if (categoryForSection(current) === category) return current;
  return category === "themes"
    ? "themesHeatmap"
    : category === "signals"
      ? "emergingLeadership"
      : "sectorHeatmap";
}
function firstParam(value: string | string[] | undefined) {
  return Array.isArray(value) ? (value[0] ?? "") : (value ?? "");
}
function firstActiveSection(
  value: string | string[] | undefined,
): ActiveSection | null {
  const section = firstParam(value);
  return Object.values(CONTENT_OPTIONS)
    .flat()
    .some((item) => item.key === section)
    ? (section as ActiveSection)
    : null;
}

const styles = StyleSheet.create({
  alert: {
    borderTopColor: Theme.colors.border,
    borderTopWidth: 1,
    gap: Spacing.half,
    paddingVertical: Spacing.two,
  },
  badges: { flexDirection: "row", flexWrap: "wrap", gap: Spacing.two },
  body: { color: Theme.colors.text, fontSize: 13 },
  categoryButton: {
    alignItems: "center",
    borderRadius: Theme.radii.pill,
    flex: 1,
    justifyContent: "center",
    minHeight: 36,
    paddingHorizontal: Spacing.two,
    paddingVertical: Spacing.one,
  },
  categoryButtonActive: { backgroundColor: Theme.colors.accentSoft },
  categorySwitch: {
    backgroundColor: Theme.colors.backgroundMuted,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    flexBasis: 210,
    flexDirection: "row",
    flexGrow: 1,
    flexShrink: 1,
    gap: Spacing.half,
    minWidth: 0,
    padding: 3,
  },
  categoryText: {
    color: Theme.colors.textMuted,
    fontSize: 13,
    fontWeight: "900",
    textAlign: "center",
  },
  categoryTextActive: { color: Theme.colors.accent },
  contentButton: {
    alignItems: "center",
    borderBottomColor: "transparent",
    borderBottomWidth: 2,
    flex: 1,
    justifyContent: "center",
    minHeight: 38,
    paddingHorizontal: Spacing.one,
    paddingVertical: Spacing.one,
  },
  contentButtonActive: { borderBottomColor: Theme.colors.accent },
  contentSwitch: {
    backgroundColor: Theme.colors.card,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    flexDirection: "row",
    paddingHorizontal: Spacing.one,
  },
  contentText: {
    color: Theme.colors.textMuted,
    fontSize: 12,
    fontWeight: "900",
    textAlign: "center",
  },
  contentTextActive: { color: Theme.colors.accent },
  detailStack: { gap: Spacing.three },
  metricGrid: { flexDirection: "row", flexWrap: "wrap", gap: Spacing.two },
  name: { color: Theme.colors.text, fontSize: 14, fontWeight: "900" },
  navigation: { gap: Spacing.two },
  navigationTopRow: {
    alignItems: "center",
    flexDirection: "row",
    flexWrap: "wrap",
    gap: Spacing.two,
  },
  note: { color: Theme.colors.textMuted, fontSize: 13, fontWeight: "700" },
  row: {
    alignItems: "center",
    borderTopColor: Theme.colors.border,
    borderTopWidth: 1,
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: Spacing.two,
  },
  pressed: { opacity: 0.78 },
  stack: { gap: Spacing.three },
  tab: {
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.small,
    borderWidth: 1,
    paddingHorizontal: Spacing.two,
    paddingVertical: Spacing.one,
  },
  tabActive: {
    backgroundColor: Theme.colors.accentSoft,
    borderColor: Theme.colors.accent,
  },
  tabs: { flexDirection: "row", flexWrap: "wrap", gap: Spacing.one },
  tabText: { color: Theme.colors.textMuted, fontSize: 12, fontWeight: "800" },
  tabTextActive: { color: Theme.colors.accent },
  themeSource: { gap: Spacing.one, marginBottom: Spacing.two },
  utilityButton: {
    alignItems: "center",
    backgroundColor: Theme.colors.card,
    borderColor: Theme.colors.border,
    borderRadius: Theme.radii.pill,
    borderWidth: 1,
    height: 40,
    justifyContent: "center",
    width: 40,
  },
  utilityButtonDisabled: { opacity: 0.45 },
  utilityToolbar: {
    alignItems: "center",
    alignSelf: "flex-end",
    flexDirection: "row",
    gap: Spacing.one,
    marginLeft: "auto",
  },
  filterBadge: {
    alignItems: "center",
    backgroundColor: Theme.colors.warning,
    borderRadius: Theme.radii.pill,
    height: 18,
    justifyContent: "center",
    minWidth: 18,
    paddingHorizontal: 5,
    position: "absolute",
    right: -5,
    top: -5,
  },
  filterBadgeText: {
    color: Theme.colors.background,
    fontSize: 10,
    fontWeight: "900",
  },
  flow: {
    borderTopColor: Theme.colors.border,
    borderTopWidth: 1,
    gap: Spacing.half,
    paddingTop: Spacing.two,
  },
  flowTitle: { color: Theme.colors.text, fontSize: 13, fontWeight: "900" },
  value: { color: Theme.colors.accent, fontSize: 16, fontWeight: "900" },
});
