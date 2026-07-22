# Stage 8.75 Theme Rotation Mathematics — Pre-change Audit

Audit date: 2026-07-23  
Scope: the Theme Rotation analytical path before the Relative Trend / Relative Momentum patch  
Legacy model identifier: `relative-return-momentum-v1`  
Legacy normalization identifier: `midpoint-100-relative-return-v1`

This document records the implementation before any analytical formula was changed. Theme Rotation migrated first. Sector Rotation subsequently adopted the same causal kernel under its own model version while retaining this implementation only in an explicitly named downstream compatibility field.

## Current pipeline

1. `ThemeSnapshotBuilder.build` loads every required adjusted daily history in one repository batch. The primary benchmark is governed adjusted daily `SPY` history.
2. `build_equal_weight_basket_history` creates each current-membership theme basket. For session `t`, a constituent is eligible only when it has valid adjusted observations on `t` and the immediately preceding union session, and its preceding close is positive. Missing constituents are excluded, never assigned a zero return. The basket is omitted when the existing coverage floor is not met.
3. The eligible constituent return is `r(i,t) = close(i,t) / close(i,t-1) - 1`. The equal-weight theme return is the arithmetic mean of eligible returns. The index starts at 100 and chains as `index(t) = index(t-1) * (1 + mean(r(i,t)))`. Raw prices are neither averaged nor summed.
4. The basket index and SPY are intersected on exact valid adjusted market dates. There is no forward fill. Non-valid or non-adjusted bars are discarded.
5. `app.rotation.engine.build_rotation_series` calculates the legacy rotation coordinates for each selected interval and serializes them under the immutable ThemeSnapshot row's `rotation_series`.
6. `app.theme_snapshots.readers.rotation_payload` is the canonical `/market/themes/rotation` response builder. It applies row-level availability/evidence gates, exposes the current point and trail, and returns stable theme ordering and exclusions.
7. The frontend API client, identity-scoped `useThemeRotation` hook, and `adaptThemeRotation` adapter consume the canonical response. The adapter renames backend `plotted_x` / `plotted_y` coordinates for the chart; it does not compute the legacy indicators. `RotationQuadrantChart` transforms canonical coordinates to pixels and handles labels and quadrant filtering.
8. Test-scenario rotation values in `frontend/src/data/sectorTabTestData.ts` are an explicitly gated fixture path. They are not a production fallback. Production Theme Rotation does not reconstruct unavailable coordinates from ranking, returns, or optional evidence.

## Exact legacy axes

For an entity/benchmark aligned pair sequence ending at index `t` and legacy lookback `L`:

`entity_return(t,L) = entity_close(t) / entity_close(t-L) - 1`

`benchmark_return(t,L) = benchmark_close(t) / benchmark_close(t-L) - 1`

`raw_rs(t,L) = 100 * (entity_return(t,L) - benchmark_return(t,L))`

The horizontal coordinate is:

`x(t) = 100 + raw_rs(t,L)`

For legacy momentum lag `M`:

`raw_momentum(t,L,M) = raw_rs(t,L) - raw_rs(t-M,L)`

The vertical coordinate is:

`y(t) = 100 + raw_momentum(t,L,M)`

There is no logarithmic relative-price line, EMA trend, volatility scaling, temporal z-score, cross-sectional normalization, robust scaling, winsorization, or momentum smoothing. “Normalization” only adds the fixed midpoint 100. The values are time-series rolling-return differences, not cross-sectional universe-normalized values.

## Legacy interval behavior

| UI interval | Relative-return lookback | Momentum lag | Tail sampling | Tail size | Actual meaning |
|---|---:|---:|---:|---:|---|
| `1W` | 5 sessions | 1 session | every session | 5 | five-day relative-return snapshots |
| `1M` | 21 sessions | 5 sessions | every 5 sessions | 5 | 21-session relative-return snapshots |
| `3M` | 63 sessions | 21 sessions | every 15 sessions | 5 | 63-session relative-return snapshots |

All inputs are daily adjusted bars and all series update on a daily snapshot rebuild. `1W`, `1M`, and `3M` are return-window / lag / spacing configurations, not distinct coherent trend-model profiles. In particular, `3M` is not a weekly model.

## Missing data and historical tails

- Theme basket observations below the governed coverage floor are omitted.
- Entity and benchmark observations are used only on exact common valid adjusted dates.
- A missing or non-positive starting price makes the coordinate unavailable; unavailable coordinates are not replaced with zero.
- The engine returns no tail unless the lookback, momentum lag, sampling spacing, and five-point requirement fit the aligned history.
- The five tail points are genuine sequential calculations and are ordered oldest to newest. They are not fabricated frontend points. However, each point is an independently calculated rolling-return coordinate and the implementation does not explicitly segment a tail when a missing market session occurs inside the aligned sequence.
- Quadrants are deterministic: `x >= 100, y >= 100` is Leading; `x >= 100, y < 100` is Weakening; `x < 100, y < 100` is Lagging; otherwise Improving. Exactly 100 is treated as non-negative on either axis.

## Why the legacy graph behaves unlike a rotational trend model

- **Short, mostly straight paths:** every tail has only five points. Nearby points use heavily overlapping fixed return windows, so successive x values and their first differences often move almost linearly.
- **Limited natural phase behavior:** y is a lagged difference of raw relative returns rather than the momentum of a smoothed relative trend. It has no designed faster/slower phase relationship with x.
- **Clustering:** shifting small percentage-point relative-return values by 100 leaves many observations near the same region, while the absence of volatility/robust scaling makes cross-theme distances inconsistent.
- **Abrupt movement:** a session entering or leaving a fixed lookback window can move x abruptly; subtracting two such windows amplifies that behavior on y. Sparse 1M/3M sampling makes visual jumps larger.
- **Insufficient smoothness:** neither axis is smoothed and there is no robust outlier treatment. The chart connects sparse sampled snapshots rather than a longer continuous trend/momentum state path.

## Endpoints and downstream consumers

- API: `GET /market/themes/rotation?timeframe=1w|1m|3m` (with `interval` compatibility handling in the route) reads the snapshot once through `rotation_payload`.
- Frontend: Theme Rotation on the Sectors/Themes surface uses the dedicated response, hook, adapter, and quadrant chart. Smart labels affect labels only after the prior integration patch; quadrant filters affect plotted themes.
- Reports: report research and document/chart builders read the ThemeSnapshot `rotation_series`, normally selecting `1M`. They use rotation as contextual evidence/visualization rather than changing theme ranking inputs.
- Copilot: Theme destinations and theme detail context do not calculate coordinates. Existing evidence/claim restrictions remain independent of this model.
- Ranking and ratings: Theme ranking is produced by the existing composite analytics before rotation serialization. Stock ratings, sector ratings, watchlist scores, report candidate materiality, and provider behavior do not depend on the legacy Theme chart coordinates.
- Sector rotation: the later Sector migration is explicitly versioned as `sector-relative-trend-momentum-v1`; the legacy engine remains only under `legacy_rotation_series` for compact-dashboard/report-scoring compatibility.

## Migration constraint

The Theme replacement must expose an explicit new model/version/effective date, keep the legacy engine identifiable, migrate API/frontend naming from Relative Strength to Relative Trend, and preserve evidence lineage. It must not claim equivalence to proprietary formulas or alter ranking, availability, taxonomy, mappings, security master, providers, reports, or Copilot policy.
