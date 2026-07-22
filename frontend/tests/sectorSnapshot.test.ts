import { getSectorDetail, getSectorSnapshot } from "../src/services/api";
import { clearRequestCache } from "../src/services/requestCache";
import {
  adaptSectorDetail,
  adaptSectorRotation,
  adaptSectorSnapshot,
  CANONICAL_SECTOR_IDS,
  formatNullablePercent,
  normalizeSectorId,
  selectPublishedRotationWindow,
} from "../src/features/sectors/sectorSnapshot";
import {
  buildRotationChartSectors,
  rotationRenderState,
} from "../src/features/sectors/rotationAvailability";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

const sector = {
  breadth_metrics: { advancing: 1, declining: 0, unchanged: 0 },
  classification: "Improving",
  component_scores: {
    breadth: 60,
    momentum: 61,
    participation: 62,
    relative_strength: 63,
  },
  composite_score: 61.5,
  confidence: "high",
  coverage_ratio: 1,
  display_name: "Information Technology",
  eligible_members: 2,
  etf_symbol: "XLK",
  price_metrics: {
    return_1d: 1,
    return_1w: 2,
    return_1m: 3,
    return_3m: 4,
    return_6m: 5,
    return_1y: 6,
  },
  rank: 2,
  relative_strength_metrics: { vs_spy_1m: 1, vs_spy_3m: 2 },
  sector_id: "information_technology",
  total_members: 2,
};

async function run() {
  const snapshot = adaptSectorSnapshot({
    benchmark: "SPY",
    coverage: { constituent_coverage_ratio: 1 },
    market_date: "2026-07-17",
    sectors: [
      sector,
      {
        ...sector,
        display_name: "Energy",
        etf_symbol: "XLE",
        rank: 1,
        sector_id: "energy",
      },
    ],
    snapshot_id: "sector-live",
    source_state: "live",
    status: "complete",
    universe_id: "sp100",
    universe_version: "v1",
  });
  assert(
    snapshot?.sectors.map((item) => item.rank).join(",") === "1,2",
    "snapshot rows use canonical composite rank order",
  );
  assert(
    snapshot?.sectors[1].returns["6M"] === 5 &&
      snapshot?.sectors[1].returns["1Y"] === 6,
    "all six snapshot return intervals are retained",
  );
  assert(
    formatNullablePercent(null) === "N/A",
    "unavailable returns remain N/A instead of zero",
  );
  assert(
    normalizeSectorId("Technology") === "information_technology",
    "saved Technology alias resolves to the canonical sector id",
  );
  const rotationWindow = selectPublishedRotationWindow(
    [
      {
        date: "2026-04-17",
        dateLabel: "2026-04-17",
        relativeTrend: 100,
        relativeStrength: 100,
        relativeMomentum: 100,
      },
      {
        date: "2026-07-17",
        dateLabel: "2026-07-17",
        relativeTrend: 102,
        relativeStrength: 102,
        relativeMomentum: 101,
      },
    ],
    "1W",
  );
  assert(
    rotationWindow.length === 1 && rotationWindow[0].date === "2026-07-17",
    "rotation interval filters published snapshot points without fabricating history",
  );
  const rotation = adaptSectorRotation({
    snapshot_id: "sector-live",
    universe_version: "v1",
    timeframe: "1W",
    profile: "short",
    rotation_model_version: "sector-relative-trend-momentum-v1",
    formula_version: "sector-relative-trend-momentum-v1",
    market_trails: {
      information_technology: {
        "1W": [
          { date: "2026-07-11", relative_trend: 98, relative_momentum: 99 },
          { date: "2026-07-17", relative_trend: 101, relative_momentum: 102 },
        ],
      },
    },
    series: [
      {
        entity_id: "information_technology",
        display_name: "Information Technology",
        short_label: "XLK",
        benchmark_symbol: "SPY",
        interval: "1W",
        profile: "short",
        model_version: "sector-relative-trend-momentum-v1",
        formula_version: "sector-relative-trend-momentum-v1",
        normalization_version: "zero-centered-rolling-robust-scale-v1",
        source_state: "live",
        data_mode: "live",
        status: "complete",
        current_point: {
          market_date: "2026-07-17",
          raw_rs: 1,
          raw_momentum: 0.5,
          relative_trend: 101,
          relative_momentum: 100.5,
          source_provider: "polygon",
          is_synthetic: false,
        },
        trail_points: [
          {
            market_date: "2026-07-11",
            raw_rs: -2,
            raw_momentum: -1,
            relative_trend: 98,
            relative_momentum: 99,
            source_provider: "polygon",
            is_synthetic: false,
          },
          {
            market_date: "2026-07-17",
            raw_rs: 1,
            raw_momentum: 0.5,
            relative_trend: 101,
            relative_momentum: 100.5,
            source_provider: "polygon",
            is_synthetic: false,
          },
        ],
      },
    ],
  });
  assert(rotation !== null, "canonical versioned sector rotation adapts");
  assert(
    rotation.marketTrailsBySector.get("information_technology")?.["1W"]
      ?.length === 2,
    "interval-specific durable market tails are retained for sector rotation",
  );
  assert(
    rotation.seriesBySector.get("information_technology")?.["1W"]?.currentPoint
      ?.date === "2026-07-17",
    "canonical series retains the current point and real market date",
  );
  assert(
    rotation.seriesBySector
      .get("information_technology")
      ?.["1W"]?.trailPoints.at(-1)?.relativeStrength === 101,
    "canonical chart coordinates use the audited plotted values",
  );

  const shallowRotation = adaptSectorRotation({
    snapshot_id: "sector-live",
    universe_version: "v1",
    timeframe: "1M",
    profile: "medium",
    rotation_model_version: "sector-relative-trend-momentum-v1",
    current_positions_available: true,
    etf_trails_available: true,
    snapshot_transition_history_available: false,
    current_point_count: 11,
    trail_point_count: 55,
    transition_snapshot_count: 1,
    limited_history_reason:
      "Snapshot transition alerts require additional daily SectorSnapshots.",
    movement_available: false,
    series: CANONICAL_SECTOR_IDS.flatMap((sectorId, sectorIndex) =>
      ["1W", "1M", "3M"].map((interval, intervalIndex) => ({
        entity_id: sectorId,
        display_name: sectorId,
        short_label: `ETF${sectorIndex}`,
        benchmark_symbol: "SPY",
        interval,
        profile:
          interval === "1W" ? "short" : interval === "3M" ? "long" : "medium",
        model_version: "sector-relative-trend-momentum-v1",
        formula_version: "sector-relative-trend-momentum-v1",
        normalization_version: "zero-centered-rolling-robust-scale-v1",
        source_state: "live",
        data_mode: "live",
        status: "complete",
        current_point: {
          market_date: "2026-07-17",
          relative_trend: 100 + sectorIndex,
          relative_momentum: 100 + intervalIndex,
          source_provider: "polygon",
          is_synthetic: false,
        },
        trail_points: Array.from({ length: 5 }, (_, pointIndex) => ({
          market_date: `2026-07-${String(13 + pointIndex).padStart(2, "0")}`,
          relative_trend: 96 + sectorIndex + pointIndex,
          relative_momentum: 97 + intervalIndex + pointIndex,
          source_provider: "polygon",
          is_synthetic: false,
        })),
      })),
    ),
  });
  assert(shallowRotation !== null, "canonical multi-profile fixture adapts");
  assert(
    !shallowRotation.snapshotTransitionHistoryAvailable,
    "shallow snapshot-transition history remains explicitly unavailable",
  );
  (["1W", "1M", "3M"] as const).forEach((interval) => {
    const chartSectors = buildRotationChartSectors(
      shallowRotation,
      interval,
      new Map(),
    );
    assert(
      chartSectors.length === 11,
      `${interval} keeps all valid current sector positions renderable`,
    );
    assert(
      rotationRenderState(shallowRotation, interval) === "ready",
      `${interval} does not use transition history as a chart readiness gate`,
    );
  });
  assert(
    rotationRenderState(
      adaptSectorRotation({
        snapshot_id: "sector-live",
        universe_version: "v1",
        timeframe: "1W",
        profile: "short",
        rotation_model_version: "sector-relative-trend-momentum-v1",
        series: [],
      }),
      "1W",
    ) === "unavailable",
    "only truly empty current positions produce rotation unavailable state",
  );

  const detail = adaptSectorDetail({
    benchmark: "SPY",
    coverage: { constituent_coverage_ratio: 1 },
    market_date: "2026-07-17",
    snapshot_id: "sector-live",
    source_state: "live",
    status: "complete",
    universe_id: "sp100",
    universe_version: "v1",
    sector,
    constituents: [
      {
        company_name: "Example",
        eligible: true,
        returns: { "1d": 1, "1w": 2, "1m": 3, "3m": 4, "6m": 5, "1y": 6 },
        sector_id: "information_technology",
        ticker: "EXMP",
      },
    ],
  });
  assert(
    detail?.constituents[0].ticker === "EXMP" &&
      detail.constituents[0].returns["1M"] === 3,
    "detail uses snapshot-backed constituent data and normalizes its return periods",
  );

  const originalFetch = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = (async () => {
    calls += 1;
    return new Response(
      JSON.stringify({ ...snapshot, sector, constituents: [] }),
      { status: 200 },
    );
  }) as typeof fetch;
  try {
    clearRequestCache("sector-");
    await Promise.all([getSectorSnapshot(), getSectorSnapshot()]);
    await Promise.all([
      getSectorDetail("Technology"),
      getSectorDetail("information_technology"),
    ]);
    assert(
      calls === 2,
      "snapshot and canonicalized detail requests each dedupe across repeated mounts and aliases",
    );
  } finally {
    clearRequestCache("sector-");
    globalThis.fetch = originalFetch;
  }
}

void run();
