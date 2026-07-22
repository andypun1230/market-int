export const CANONICAL_SECTOR_IDS = [
  "communication_services",
  "consumer_discretionary",
  "consumer_staples",
  "energy",
  "financials",
  "health_care",
  "industrials",
  "information_technology",
  "materials",
  "real_estate",
  "utilities",
] as const;

export type SectorId = (typeof CANONICAL_SECTOR_IDS)[number];
type UnknownRecord = Record<string, unknown>;
export type NullableNumber = number | null;

export type SectorRow = {
  sectorId: SectorId;
  displayName: string;
  etfSymbol: string;
  rank: number;
  classification: string;
  confidence: string;
  compositeScore: NullableNumber;
  dataConfidence: { label: string | null; reason: string | null };
  signalConfidence: { label: string | null; reason: string | null };
  representativeness: {
    label: string | null;
    reason: string | null;
    sampleSize: number | null;
  };
  totalMembers: number | null;
  eligibleMembers: number | null;
  coverageRatio: NullableNumber;
  returns: Record<"1D" | "1W" | "1M" | "3M" | "6M" | "1Y", NullableNumber>;
  relativeStrength: { vsSpy1M: NullableNumber; vsSpy3M: NullableNumber };
  breadth: {
    advancing: number | null;
    declining: number | null;
    unchanged: number | null;
    adRatio: NullableNumber;
    adRatioDisplay: string | null;
    adRatioSmoothed: NullableNumber;
    ratioMethod: string | null;
    above20: NullableNumber;
    above50: NullableNumber;
    above200: NullableNumber;
    highs: number | null;
    lows: number | null;
  };
  participation: {
    positive: NullableNumber;
    concentration: NullableNumber;
    divergence: NullableNumber;
    quality: string | null;
    definition: string | null;
  };
  scores: Record<string, NullableNumber>;
  explanation: string;
  warnings: string[];
};
export type SectorSnapshotModel = {
  snapshotId: string;
  universeId: string;
  universeVersion: string;
  marketDate: string;
  sourceState: string;
  status: string;
  benchmark: string;
  providerHistory: string | null;
  coverage: {
    constituentCoverage: NullableNumber;
    etfCoverage: NullableNumber;
    eligibleMembers: number | null;
    totalMembers: number | null;
  };
  sectors: SectorRow[];
  alerts: UnknownRecord[];
  warnings: string[];
};
export type SectorDetailModel = SectorSnapshotModel & {
  sector: SectorRow | null;
  constituents: {
    ticker: string;
    companyName: string;
    sectorId: SectorId;
    eligible: boolean;
    relevance: string | null;
    returns: SectorRow["returns"];
  }[];
  rotationMovement: SectorRotationMovement | null;
  rotationSeries: SectorRotationSeries[];
};
export const SECTOR_ROTATION_MODEL_VERSION =
  "sector-relative-trend-momentum-v1";
export type SectorRotationProfile = "short" | "medium" | "long";
export type SectorRotationPoint = {
  date: string;
  dateLabel: string;
  relativeMomentum: number;
  relativeStrength: number;
  relativeTrend: number;
  rawMomentum?: number;
  rawRs?: number;
  sourceProvider?: string;
  isSynthetic?: boolean;
  compatibilitySignature?: string;
  snapshotId?: string | null;
};
export type SectorRotationMovement = {
  direction: "gaining" | "losing" | "stable";
  state: "available" | "insufficient_history";
  relativeStrengthChange: number | null;
  relativeMomentumChange: number | null;
};
export type SectorRotationInterval = "1W" | "1M" | "3M";
export type SectorRotationSeries = {
  entityId: SectorId;
  displayName: string;
  shortLabel: string;
  interval: SectorRotationInterval;
  profile: SectorRotationProfile;
  benchmark: string;
  formulaVersion: string;
  modelVersion: string;
  normalizationVersion: string;
  sourceState: string;
  dataMode: string;
  status: string;
  currentPoint: SectorRotationPoint | null;
  trailPoints: SectorRotationPoint[];
  warnings: string[];
};
export type SectorRotationModel = {
  snapshotId: string;
  universeVersion: string;
  timeframe: SectorRotationInterval;
  profile: SectorRotationProfile;
  modelVersion: string;
  benchmark: string;
  eligibleCount: number;
  excludedCount: number;
  latestCommonDate: string | null;
  timeframeDefinition: Record<string, unknown>;
  trailsBySector: Map<SectorId, SectorRotationPoint[]>;
  marketTrailsBySector: Map<
    SectorId,
    Partial<Record<SectorRotationInterval, SectorRotationPoint[]>>
  >;
  seriesBySector: Map<
    SectorId,
    Partial<Record<SectorRotationInterval, SectorRotationSeries>>
  >;
  movements: Map<SectorId, SectorRotationMovement>;
  flowGroups: Record<
    "gaining" | "losing" | "stable",
    {
      sectorId: SectorId;
      displayName: string;
      etfSymbol: string;
      direction: string;
      state: string;
      relativeStrengthChange: number | null;
      relativeMomentumChange: number | null;
    }[]
  >;
  currentPositionsAvailable: boolean;
  etfTrailsAvailable: boolean;
  snapshotTransitionHistoryAvailable: boolean;
  currentPointCount: number;
  trailPointCount: number;
  transitionSnapshotCount: number;
  limitedHistoryReason: string | null;
  historyPointCount: number;
  movementAvailable: boolean;
  trailLimit: number;
  formulaVersion: string;
  normalizationVersion: string;
  warnings: string[];
};

const aliases: Record<string, SectorId> = {
  technology: "information_technology",
  tech: "information_technology",
  "information technology": "information_technology",
  information_technology: "information_technology",
  healthcare: "health_care",
  "health care": "health_care",
  health_care: "health_care",
  communications: "communication_services",
  communication: "communication_services",
  "communication services": "communication_services",
  communication_services: "communication_services",
  "consumer cyclical": "consumer_discretionary",
  "consumer discretionary": "consumer_discretionary",
  consumer_discretionary: "consumer_discretionary",
  "consumer defensive": "consumer_staples",
  "consumer staples": "consumer_staples",
  consumer_staples: "consumer_staples",
  industrial: "industrials",
  financial: "financials",
  material: "materials",
  utility: "utilities",
};
export function normalizeSectorId(
  value: string | null | undefined,
): SectorId | null {
  const key = (value ?? "").trim().toLowerCase();
  return (CANONICAL_SECTOR_IDS as readonly string[]).includes(key)
    ? (key as SectorId)
    : (aliases[key] ?? null);
}
export function formatNullablePercent(value: NullableNumber): string {
  if (value === null || !Number.isFinite(value)) return "N/A";
  return `${value > 0 ? "+" : ""}${value.toFixed(2)}%`;
}
export function formatNullableCount(value: number | null): string {
  return value === null || !Number.isFinite(value) ? "N/A" : String(value);
}
export function formatCoverage(value: NullableNumber): string {
  return value === null || !Number.isFinite(value)
    ? "N/A"
    : `${Math.round(value * 100)}%`;
}
export function formatClassification(value: string | null | undefined): string {
  return ["Leading", "Improving", "Neutral", "Weakening", "Lagging"].includes(
    value ?? "",
  )
    ? value!
    : "Unavailable";
}
export function sourceLabel(snapshot: SectorSnapshotModel): string {
  return snapshot.sourceState === "live"
    ? "Live Polygon history"
    : snapshot.sourceState === "test"
      ? "Test Data"
      : "Snapshot data";
}

export function adaptSectorSnapshot(
  value: unknown,
): SectorSnapshotModel | null {
  if (!record(value) || !text(value.snapshot_id)) return null;
  const rows = array(value.sectors)
    .map(adaptRow)
    .filter((row): row is SectorRow => row !== null)
    .sort((a, b) => a.rank - b.rank || a.sectorId.localeCompare(b.sectorId));
  return {
    snapshotId: text(value.snapshot_id)!,
    universeId: text(value.universe_id) ?? "",
    universeVersion: text(value.universe_version) ?? "",
    marketDate: text(value.market_date) ?? "",
    sourceState: text(value.source_state) ?? "unavailable",
    status: text(value.status) ?? "unavailable",
    benchmark: text(value.benchmark) ?? "SPY",
    providerHistory: text(
      record(value.provider_provenance)
        ? value.provider_provenance.history_provider
        : null,
    ),
    coverage: {
      constituentCoverage: numberAt(
        value.coverage,
        "constituent_coverage_ratio",
      ),
      etfCoverage: numberAt(value.coverage, "etf_coverage_ratio"),
      eligibleMembers: numberAt(value.coverage, "eligible_members"),
      totalMembers: numberAt(value.coverage, "total_members"),
    },
    sectors: rows,
    alerts: array(value.alerts).filter(record),
    warnings: array(value.warnings).filter(
      (item): item is string => typeof item === "string",
    ),
  };
}
export function adaptSectorDetail(value: unknown): SectorDetailModel | null {
  if (!record(value)) return null;
  const base = adaptSectorSnapshot({
    ...value,
    sectors: value.sector ? [value.sector] : [],
  });
  if (!base) return null;
  const sector = base.sectors[0] ?? null;
  const rawMovement = record(value.rotation_movement)
    ? value.rotation_movement
    : null;
  const direction = text(rawMovement?.direction);
  const state = text(rawMovement?.state);
  const rotationMovement =
    (direction === "gaining" ||
      direction === "losing" ||
      direction === "stable") &&
    (state === "available" || state === "insufficient_history")
      ? ({
          direction,
          state,
          relativeStrengthChange: number(rawMovement?.relative_strength_change),
          relativeMomentumChange: number(rawMovement?.relative_momentum_change),
        } as SectorRotationMovement)
      : null;
  return {
    ...base,
    sector,
    rotationMovement,
    rotationSeries: array(value.rotation_series).flatMap(adaptRotationSeries),
    constituents: array(value.constituents).flatMap((item) => {
      if (!record(item)) {
        return [];
      }
      const sectorId = normalizeSectorId(text(item.sector_id));
      if (!sectorId) return [];
      return [
        {
          ticker: text(item.ticker) ?? "",
          companyName: text(item.company_name) ?? text(item.ticker) ?? "",
          sectorId,
          eligible: Boolean(item.eligible),
          relevance: text(item.relevance),
          returns: returns(item.returns),
        },
      ];
    }),
  };
}
export function adaptSectorRotation(
  value: unknown,
): SectorRotationModel | null {
  if (!record(value)) return null;
  const snapshotId = text(value.snapshot_id);
  const universeVersion = text(value.universe_version);
  const timeframe = rotationInterval(value.timeframe ?? value.interval);
  const profile = rotationProfile(value.profile);
  const modelVersion = text(value.rotation_model_version);
  if (
    !snapshotId ||
    !universeVersion ||
    !timeframe ||
    !profile ||
    modelVersion !== SECTOR_ROTATION_MODEL_VERSION
  )
    return null;
  const legacy = adaptLegacySectorRotation(value);
  return {
    ...legacy,
    snapshotId,
    universeVersion,
    timeframe,
    profile,
    modelVersion,
    benchmark: text(value.benchmark) ?? "SPY",
    eligibleCount: number(value.eligible_count) ?? legacy.currentPointCount,
    excludedCount: number(value.excluded_count) ?? 0,
    latestCommonDate: text(value.latest_common_date),
    timeframeDefinition: record(value.timeframe_definition)
      ? value.timeframe_definition
      : {},
  };
}

function adaptLegacySectorRotation(value: UnknownRecord): any {
  const trailsBySector = new Map<SectorId, SectorRotationPoint[]>();
  const marketTrailsBySector = new Map<
    SectorId,
    Partial<Record<SectorRotationInterval, SectorRotationPoint[]>>
  >();
  const seriesBySector = new Map<
    SectorId,
    Partial<Record<SectorRotationInterval, SectorRotationSeries>>
  >();
  const movements = new Map<SectorId, SectorRotationMovement>();
  const empty: any = {
    trailsBySector,
    marketTrailsBySector,
    seriesBySector,
    movements,
    flowGroups: { gaining: [], losing: [], stable: [] },
    currentPositionsAvailable: false,
    etfTrailsAvailable: false,
    snapshotTransitionHistoryAvailable: false,
    currentPointCount: 0,
    trailPointCount: 0,
    transitionSnapshotCount: 0,
    limitedHistoryReason: null,
    historyPointCount: 0,
    movementAvailable: false,
    trailLimit: 4,
    formulaVersion: "",
    normalizationVersion: "",
    warnings: [],
  };
  const adaptPoints = (raw: unknown) => array(raw).flatMap(adaptRotationPoint);
  if (record(value.trails))
    Object.entries(value.trails).forEach(([rawId, rawTrail]) => {
      const sectorId = normalizeSectorId(rawId);
      if (sectorId) trailsBySector.set(sectorId, adaptPoints(rawTrail));
    });
  if (record(value.market_trails))
    Object.entries(value.market_trails).forEach(([rawId, rawIntervals]) => {
      const sectorId = normalizeSectorId(rawId);
      if (!sectorId || !record(rawIntervals)) return;
      marketTrailsBySector.set(sectorId, {
        "1W": adaptPoints(rawIntervals["1W"]),
        "1M": adaptPoints(rawIntervals["1M"]),
        "3M": adaptPoints(rawIntervals["3M"]),
      });
    });
  array(value.series)
    .flatMap(adaptRotationSeries)
    .forEach((series) => {
      const entries = seriesBySector.get(series.entityId) ?? {};
      entries[series.interval] = series;
      seriesBySector.set(series.entityId, entries);
    });
  if (record(value.movements))
    Object.entries(value.movements).forEach(([rawId, rawMovement]) => {
      const sectorId = normalizeSectorId(rawId);
      if (!sectorId || !record(rawMovement)) return;
      const direction = text(rawMovement.direction);
      const state = text(rawMovement.state);
      if (
        (direction === "gaining" ||
          direction === "losing" ||
          direction === "stable") &&
        (state === "available" || state === "insufficient_history")
      )
        movements.set(sectorId, {
          direction,
          state,
          relativeStrengthChange: number(rawMovement.relative_strength_change),
          relativeMomentumChange: number(rawMovement.relative_momentum_change),
        });
    });
  const flowGroups = (["gaining", "losing", "stable"] as const).reduce(
    (groups, key) => {
      groups[key] = array(
        record(value.flow_groups) ? value.flow_groups[key] : [],
      ).flatMap((item) => {
        if (!record(item)) return [];
        const sectorId = normalizeSectorId(text(item.sector_id));
        return sectorId
          ? [
              {
                sectorId,
                displayName: text(item.display_name) ?? sectorId,
                etfSymbol: text(item.etf_symbol) ?? "",
                direction: text(item.direction) ?? key,
                state: text(item.state) ?? "",
                relativeStrengthChange: number(item.relative_strength_change),
                relativeMomentumChange: number(item.relative_momentum_change),
              },
            ]
          : [];
      });
      return groups;
    },
    {
      gaining: [],
      losing: [],
      stable: [],
    } as SectorRotationModel["flowGroups"],
  );
  const currentPointCount =
    number(value.current_point_count) ??
    Array.from(seriesBySector.values()).filter((intervals) =>
      Object.values(intervals).some((series) => series?.currentPoint),
    ).length;
  const trailPointCount =
    number(value.trail_point_count) ??
    Array.from(seriesBySector.values())
      .flatMap((intervals) => Object.values(intervals))
      .reduce((count, series) => count + (series?.trailPoints.length ?? 0), 0);
  return {
    ...empty,
    trailsBySector,
    marketTrailsBySector,
    seriesBySector,
    movements,
    flowGroups,
    currentPositionsAvailable:
      value.current_positions_available === true || currentPointCount > 0,
    etfTrailsAvailable:
      value.etf_trails_available === true ||
      trailPointCount > currentPointCount,
    snapshotTransitionHistoryAvailable:
      value.snapshot_transition_history_available === true ||
      value.movement_available === true,
    currentPointCount,
    trailPointCount,
    transitionSnapshotCount:
      number(value.transition_snapshot_count) ??
      number(value.history_point_count) ??
      0,
    limitedHistoryReason: text(value.limited_history_reason),
    historyPointCount: number(value.history_point_count) ?? 0,
    movementAvailable: value.movement_available === true,
    trailLimit: number(value.trail_limit) ?? 4,
    formulaVersion: text(value.formula_version) ?? "",
    normalizationVersion: text(value.normalization_version) ?? "",
    warnings: array(value.warnings).filter(
      (item): item is string => typeof item === "string",
    ),
  };
}
function adaptRotationPoint(value: unknown): SectorRotationPoint[] {
  if (!record(value)) return [];
  const date =
    text(value.market_date) ?? text(value.date) ?? text(value.date_label);
  const relativeTrend =
    number(value.relative_trend) ??
    number(value.plotted_x) ??
    number(value.relative_strength);
  const relativeMomentum =
    number(value.relative_momentum) ?? number(value.plotted_y);
  return date !== null && relativeTrend !== null && relativeMomentum !== null
    ? [
        {
          date,
          dateLabel: text(value.date_label) ?? date,
          relativeTrend,
          relativeStrength: relativeTrend,
          relativeMomentum,
          rawRs: number(value.raw_rs) ?? undefined,
          rawMomentum: number(value.raw_momentum) ?? undefined,
          sourceProvider: text(value.source_provider) ?? undefined,
          isSynthetic: value.is_synthetic === true,
          compatibilitySignature:
            text(value.compatibility_signature) ?? undefined,
          snapshotId: text(value.snapshot_id),
        },
      ]
    : [];
}
function adaptRotationSeries(value: unknown): SectorRotationSeries[] {
  if (!record(value)) return [];
  const entityId = normalizeSectorId(text(value.entity_id));
  const interval = rotationInterval(value.interval);
  const profile = rotationProfile(value.profile);
  const modelVersion = text(value.model_version);
  if (
    !entityId ||
    !interval ||
    !profile ||
    modelVersion !== SECTOR_ROTATION_MODEL_VERSION
  )
    return [];
  const current = adaptRotationPoint(value.current_point)[0] ?? null;
  const trailPoints = array(value.trail_points).flatMap(adaptRotationPoint);
  return [
    {
      entityId,
      displayName: text(value.display_name) ?? entityId,
      shortLabel: text(value.short_label) ?? "",
      interval,
      profile,
      benchmark: text(value.benchmark_symbol) ?? "SPY",
      formulaVersion: text(value.formula_version) ?? "",
      modelVersion,
      normalizationVersion: text(value.normalization_version) ?? "",
      sourceState: text(value.source_state) ?? "unavailable",
      dataMode: text(value.data_mode) ?? "unavailable",
      status: text(value.status) ?? "unavailable",
      currentPoint: current,
      trailPoints,
      warnings: array(value.warnings).filter(
        (item): item is string => typeof item === "string",
      ),
    },
  ];
}
export function selectPublishedRotationWindow(
  points: SectorRotationPoint[],
  interval: "1W" | "1M" | "3M",
): SectorRotationPoint[] {
  if (!points.length) return [];
  const days = interval === "1W" ? 7 : interval === "1M" ? 31 : 93;
  const latest = new Date(points[points.length - 1].date);
  if (Number.isNaN(latest.valueOf())) return points;
  const earliest = new Date(latest);
  earliest.setDate(earliest.getDate() - days);
  const visible = points.filter((point) => {
    const date = new Date(point.date);
    return !Number.isNaN(date.valueOf()) && date >= earliest;
  });
  return visible.length ? visible : [points[points.length - 1]];
}
export function adaptSectorSnapshotHistory(
  value: unknown,
): Map<SectorId, SectorRotationPoint[]> {
  const history = new Map<SectorId, SectorRotationPoint[]>();
  if (!record(value)) return history;
  array(value.items).forEach((snapshot) => {
    if (!record(snapshot)) return;
    const date = text(snapshot.market_date);
    if (!date) return;
    array(snapshot.sectors).forEach((rawRow) => {
      const row = adaptRow(rawRow);
      if (
        !row ||
        row.scores.relativeStrength === null ||
        row.scores.momentum === null
      )
        return;
      const points = history.get(row.sectorId) ?? [];
      const relativeTrend = 50 + row.scores.relativeStrength;
      points.push({
        date,
        dateLabel: date,
        relativeTrend,
        relativeStrength: relativeTrend,
        relativeMomentum: 50 + row.scores.momentum,
      });
      history.set(row.sectorId, points);
    });
  });
  return history;
}
export function sectorById(
  snapshot: SectorSnapshotModel | null,
  id: string | null | undefined,
) {
  const canonical = normalizeSectorId(id);
  return canonical
    ? (snapshot?.sectors.find((row) => row.sectorId === canonical) ?? null)
    : null;
}
function adaptRow(value: unknown): SectorRow | null {
  if (!record(value)) return null;
  const sectorId = normalizeSectorId(text(value.sector_id));
  if (!sectorId) return null;
  const breadth = record(value.breadth_metrics) ? value.breadth_metrics : {};
  const participation = record(value.participation_metrics)
    ? value.participation_metrics
    : {};
  const scores = record(value.component_scores) ? value.component_scores : {};
  const dataConfidence = record(value.data_confidence)
    ? value.data_confidence
    : {};
  const signalConfidence = record(value.signal_confidence)
    ? value.signal_confidence
    : {};
  return {
    sectorId,
    displayName: text(value.display_name) ?? sectorId,
    etfSymbol: text(value.etf_symbol) ?? "",
    rank: number(value.rank) ?? 999,
    classification: formatClassification(text(value.classification)),
    confidence: text(value.confidence) ?? "low",
    compositeScore: number(value.composite_score),
    dataConfidence: {
      label: text(dataConfidence.label),
      reason: text(dataConfidence.reason),
    },
    signalConfidence: {
      label: text(signalConfidence.label),
      reason: text(signalConfidence.reason),
    },
    representativeness: {
      label: text(value.breadth_representativeness),
      reason: text(value.representativeness_reason),
      sampleSize: number(value.sample_size) ?? number(value.eligible_members),
    },
    totalMembers: number(value.total_members),
    eligibleMembers: number(value.eligible_members),
    coverageRatio: number(value.coverage_ratio),
    returns: returns(value.price_metrics),
    relativeStrength: {
      vsSpy1M: numberAt(value.relative_strength_metrics, "vs_spy_1m"),
      vsSpy3M: numberAt(value.relative_strength_metrics, "vs_spy_3m"),
    },
    breadth: {
      advancing: numberAt(breadth, "advancing"),
      declining: numberAt(breadth, "declining"),
      unchanged: numberAt(breadth, "unchanged"),
      adRatio: numberAt(breadth, "advance_decline_ratio"),
      adRatioDisplay: text(breadth.advance_decline_ratio_display),
      adRatioSmoothed: numberAt(breadth, "advance_decline_ratio_smoothed"),
      ratioMethod: text(breadth.ratio_method),
      above20: numberAt(breadth, "percent_above_ema20"),
      above50: numberAt(breadth, "percent_above_ema50"),
      above200: numberAt(breadth, "percent_above_ema200"),
      highs: numberAt(breadth, "new_52_week_highs"),
      lows: numberAt(breadth, "new_52_week_lows"),
    },
    participation: {
      positive: numberAt(participation, "positive_contributor_percent"),
      concentration: numberAt(participation, "top_contributor_concentration"),
      divergence: numberAt(participation, "breadth_etf_divergence"),
      quality: text(participation.quality),
      definition: text(participation.definition),
    },
    scores: {
      momentum: number(scores.momentum),
      relativeStrength: number(scores.relative_strength),
      breadth: number(scores.breadth),
      participation: number(scores.participation),
    },
    explanation: text(value.explanation) ?? "",
    warnings: array(value.warnings).filter(
      (item): item is string => typeof item === "string",
    ),
  };
}
function returns(value: unknown): SectorRow["returns"] {
  return {
    "1D": numberAt(value, "return_1d") ?? numberAt(value, "1d"),
    "1W": numberAt(value, "return_1w") ?? numberAt(value, "1w"),
    "1M": numberAt(value, "return_1m") ?? numberAt(value, "1m"),
    "3M": numberAt(value, "return_3m") ?? numberAt(value, "3m"),
    "6M": numberAt(value, "return_6m") ?? numberAt(value, "6m"),
    "1Y": numberAt(value, "return_1y") ?? numberAt(value, "1y"),
  };
}
function rotationInterval(value: unknown): SectorRotationInterval | null {
  const normalized = typeof value === "string" ? value.toUpperCase() : "";
  return normalized === "1W" || normalized === "1M" || normalized === "3M"
    ? normalized
    : null;
}
function rotationProfile(value: unknown): SectorRotationProfile | null {
  return value === "short" || value === "medium" || value === "long"
    ? value
    : null;
}
function record(value: unknown): value is UnknownRecord {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}
function array(value: unknown[]): unknown[];
function array(value: unknown): unknown[];
function array(value: unknown) {
  return Array.isArray(value) ? value : [];
}
function text(value: unknown) {
  return typeof value === "string" ? value : null;
}
function number(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}
function numberAt(value: unknown, key: string) {
  return record(value) ? number(value[key]) : null;
}
