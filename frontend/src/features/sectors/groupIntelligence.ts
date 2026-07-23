export type CanonicalGroupType = "sector" | "theme";
export type CanonicalGroupTimeframe = "1D" | "1W" | "1M" | "3M" | "6M" | "1Y";
export type BreadthHistoryTimeframe = "1M" | "3M" | "6M" | "1Y";

export type CanonicalGroupItem = {
  availability: { reason: string | null; source_state: string; state: string };
  breadth: {
    above_20: number | null;
    above_50: number | null;
    above_200: number | null;
    advance_decline_ratio: number | null;
    advancing: number | null;
    declining: number | null;
    highs_minus_lows: number | null;
    new_highs: number | null;
    new_lows: number | null;
  };
  canonical_destination: { route: "/sectors"; params: { entityId: string; entityKind: CanonicalGroupType } };
  concentration: number | null;
  confidence: {
    data: { label: string; reason: string | null; score: number | null };
    signal: { label: string; reason: string | null; score: number | null };
  };
  evidence: { input_hash: string | null; snapshot_id: string | null };
  freshness: { as_of: string | null; generated_at: string | null; state: string };
  id: string;
  movement: { direction: "gaining" | "losing" | "stable" | "unavailable"; previous_state: string | null; recent_transition: boolean };
  name: string;
  parent: string | null;
  performance: Record<CanonicalGroupTimeframe, number | null>;
  persistence: { available: boolean; snapshot_count: number; state: string };
  quadrant: string;
  rank: number | null;
  rank_change: number | null;
  relative_momentum: number | null;
  relative_strength: number | null;
  state: string;
  type: CanonicalGroupType;
};

export type CanonicalGroupRegistry = {
  contract_version: "group-intelligence-v1";
  count: number;
  entity_type: CanonicalGroupType;
  items: CanonicalGroupItem[];
  market_date: string | null;
  model_versions: Record<string, string | number | null>;
  snapshot_id: string | null;
  source_state: string;
  status: "available" | "partial" | "unavailable" | "empty";
  total_count?: number;
  warnings: string[];
};

export type CanonicalGroupComparison = {
  canonical_url: string;
  contract_version: "group-comparison-v1";
  entity_type: CanonicalGroupType;
  items: CanonicalGroupItem[];
  market_date: string | null;
  model_versions: Record<string, string | number | null>;
  selected_ids: string[];
  selection_limits: { desktop_maximum: 5; minimum: 2; mobile_maximum: 3 };
  snapshot_id: string | null;
  status: "available" | "partial" | "unavailable";
  timeframe: CanonicalGroupTimeframe;
};

export type BreadthHistoryObservation = {
  above_20: number | null;
  above_50: number | null;
  above_200: number | null;
  advance_decline_ratio: number | null;
  advancing: number | null;
  declining: number | null;
  highs_minus_lows: number | null;
  market_date: string | null;
  new_highs: number | null;
  new_lows: number | null;
  snapshot_id: string | null;
};

export type CanonicalBreadthHistory = {
  available_metrics: string[];
  contract_version: "group-breadth-history-v1";
  entity_id: string;
  entity_type: CanonicalGroupType;
  interpretation: {
    conclusion: string;
    confidence: string;
    evidence: { change: number; from: number; metric: string; to: number }[];
    freshness: string | null;
    state: string;
  };
  limitation: string;
  observation_count: number;
  observations: BreadthHistoryObservation[];
  snapshot_ids: string[];
  status: "available" | "partial" | "unavailable";
  timeframe: BreadthHistoryTimeframe;
};

export type CanonicalDivergence = {
  availability: CanonicalGroupItem["availability"];
  canonical_destination: CanonicalGroupItem["canonical_destination"];
  confidence: { label: string; observation_count: number; score: number | null };
  detected_at: string | null;
  direction: "positive" | "negative" | "mixed";
  entity: { id: string; name: string; type: CanonicalGroupType };
  evidence: Record<string, number | string | null>;
  explanation: string;
  freshness: CanonicalGroupItem["freshness"];
  id: string;
  invalidation: string;
  rule_id: string;
  severity: "high" | "medium" | "low";
  why_it_matters: string;
  confirmation: string;
};

export type CanonicalDivergenceResponse = {
  contract_version: "group-divergence-v1";
  count: number;
  entity_id: string;
  entity_type: CanonicalGroupType;
  items: CanonicalDivergence[];
  snapshot_id: string | null;
  status: "available" | "empty" | "unavailable";
  timeframe: BreadthHistoryTimeframe;
};

export type CanonicalSectorAlert = CanonicalDivergence & {
  group: "leadership" | "momentum" | "breadth" | "risk";
  type:
    | "entered_leading"
    | "exited_leading"
    | "entered_improving"
    | "breadth_deterioration"
    | "momentum_reversal"
    | "relative_strength_breakout"
    | "persistence_loss"
    | "rotation_acceleration"
    | "concentration_warning";
};

export type CanonicalSectorAlerts = {
  contract_version: "sector-alerts-v1";
  count: number;
  items: CanonicalSectorAlert[];
  market_date: string | null;
  snapshot_id: string | null;
  status: "available" | "empty" | "unavailable";
  types: CanonicalSectorAlert["type"][];
};

export type CanonicalGroupFilters = {
  availability: "all" | "available" | "partial" | "unavailable";
  breadthMinimum: number | null;
  movement: "all" | "gaining" | "losing" | "stable";
  momentumMinimum: number | null;
  quadrant: "all" | "leading" | "improving" | "weakening" | "lagging";
  rankMaximum: number | null;
  recentTransition: boolean;
  savedOnly: boolean;
  strongMovement: boolean;
};

export const DEFAULT_CANONICAL_GROUP_FILTERS: CanonicalGroupFilters = {
  availability: "all",
  breadthMinimum: null,
  movement: "all",
  momentumMinimum: null,
  quadrant: "all",
  rankMaximum: null,
  recentTransition: false,
  savedOnly: false,
  strongMovement: false,
};

export function filterCanonicalGroups(
  items: CanonicalGroupItem[],
  filters: CanonicalGroupFilters,
  savedKeys: Set<string>,
) {
  return items.filter((item) => {
    if (filters.quadrant !== "all" && item.quadrant !== filters.quadrant) return false;
    if (filters.availability !== "all" && item.availability.state !== filters.availability) return false;
    if (filters.rankMaximum !== null && (item.rank === null || item.rank > filters.rankMaximum)) return false;
    if (filters.breadthMinimum !== null && (item.breadth.above_50 === null || item.breadth.above_50 < filters.breadthMinimum)) return false;
    if (filters.momentumMinimum !== null && (item.relative_momentum === null || item.relative_momentum < filters.momentumMinimum)) return false;
    if (filters.movement !== "all" && item.movement.direction !== filters.movement) return false;
    if (filters.recentTransition && !item.movement.recent_transition) return false;
    if (filters.savedOnly && !savedKeys.has(`${item.type}:${item.id}`)) return false;
    if (filters.strongMovement && Math.abs(item.rank_change ?? 0) < 2) return false;
    return true;
  });
}

export function countCanonicalGroupFilters(filters: CanonicalGroupFilters) {
  return [
    filters.availability !== "all",
    filters.breadthMinimum !== null,
    filters.movement !== "all",
    filters.momentumMinimum !== null,
    filters.quadrant !== "all",
    filters.rankMaximum !== null,
    filters.recentTransition,
    filters.savedOnly,
    filters.strongMovement,
  ].filter(Boolean).length;
}

export function comparisonSelectionLimit(width: number) {
  return width < 720 ? 3 : 5;
}

export function formatNullableMetric(value: number | null, suffix = "") {
  return value === null ? "N/A" : `${value >= 0 ? "+" : ""}${value.toFixed(1)}${suffix}`;
}
