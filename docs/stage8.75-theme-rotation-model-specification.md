# Theme Rotation Map — Model Specification

Model ID: `theme-relative-trend-momentum`  
Model version: `theme-relative-trend-momentum-v1`  
Normalization version: `zero-centered-rolling-robust-scale-v1`  
Effective from: 2026-07-23  
Benchmark: SPY  
Taxonomy at adoption: `2026.07.1`

## Purpose and naming

The Theme Rotation Map is an original transparent, RRG-inspired implementation of the general idea of plotting benchmark-relative trend strength against the momentum of that relative trend. It does not reproduce proprietary formulas, claim equivalence with a third-party product, or use proprietary indicator names. Coordinates are contextual analytical evidence, not buy/sell signals and not percentage returns.

## Governed theme index

For current mapped constituent `i` with consecutive valid governed adjusted closes:

`r(i,t) = adjusted_close(i,t) / adjusted_close(i,t-1) - 1`

Missing observations are excluded rather than assigned zero. A session is unavailable below the unchanged governed 75% partial-coverage floor. Eligible constituents receive equal weight:

`theme_return(t) = mean(r(i,t))`

`theme_index(0) = 100`

`theme_index(t) = theme_index(t-1) * (1 + theme_return(t))`

Every basket bar records eligible count, total count, coverage ratio, formula version, input hash, source state, and generation time. Constituent histories are loaded in one overlapping-symbol-aware repository batch. Historical analysis uses current taxonomy membership because historical-membership data is not available; no survivorship-free claim is made.

## Benchmark-relative line

Theme and SPY observations are intersected on exact valid adjusted sessions. The engine neither forward-fills nor connects across a missing benchmark session. A zero or missing SPY close makes the observation unavailable.

`relative_price(t) = theme_index(t) / SPY_adjusted_close(t)`

For display evidence only:

`relative_price_rebased(t) = 100 * relative_price(t) / relative_price(segment_start)`

The latest continuous segment is used. A discontinuity is explicitly disclosed and never bridged by a tail.

## Relative Trend

`log_relative(t) = ln(relative_price(t))`

`fast(t) = EMA(log_relative, fast_window)`

`slow(t) = EMA(log_relative, slow_window)`

`trend_spread(t) = fast(t) - slow(t)`

`relative_change(t) = log_relative(t) - log_relative(t-1)`

`relative_volatility(t) = causal EWMA standard deviation(relative_change, volatility_window)`

`scaled_trend(t) = trend_spread(t) / max(relative_volatility(t), epsilon)`

If both spread and volatility are numerically zero, `scaled_trend` is zero. Normalization is a causal zero-centered robust signed scale. Over the trailing normalization window:

`robust_scale = max(median(abs(signal)), 1.4826 * MAD(signal), scale_floor)`

`raw_robust_score = signal / robust_scale`

`robust_score = winsor(raw_robust_score, -3, +3)`

`Relative Trend = 100 + 2 * robust_score`

The structural neutral is zero signal, not the theme's trailing median. This keeps a persistent positive relative trend above 100 after its momentum settles. Relative-volatility scaling makes the input dimensionless; per-theme causal robust scaling makes another theme's addition/removal unable to jump an existing coordinate. Cross-sectional centering was rejected for version 1 because its universe-composition jumps outweighed the incremental comparability benefit. Winsorization is never silent: raw score, scale, MAD, limit, history count, and the winsorized flag are serialized per observation.

## Relative Momentum

`trend_change(t) = Relative Trend(t) - Relative Trend(t-momentum_lag)`

`smoothed_trend_change(t) = EMA(trend_change, momentum_smoothing)`

The same causal robust signed normalization is applied with its own 0.1 scale floor:

`Relative Momentum = 100 + 2 * robust_score(smoothed_trend_change)`

Relative Momentum is therefore momentum of Relative Trend. It is not raw price return, RSI, relative return, or current return minus previous return. Above 100 means the relative trend is improving; below 100 means it is losing momentum.

## Profiles

| Profile | Compatibility alias | Input | Fast / slow EMA | Volatility | Normalization | Momentum lag / smoothing | Tail | Spacing |
|---|---|---|---|---|---|---|---|---|
| Short | 1W | daily | 10 / 30 sessions | 30 | 60 | 3 / 5 | 8 | 1 session |
| Medium | 1M | daily | 20 / 50 sessions | 50 | 126 | 5 / 10 | 10 | 3 sessions |
| Long | 3M | last complete session of each week | 10 / 26 weeks | 26 | 52 | 4 / 4 | 8 | 1 week |

The aliases are API compatibility values only. The UI calls the controls Short, Medium, and Long and explains that they are model profiles, not simple return windows. Long excludes the current calendar week unless a Friday session is present.

## Tail, direction, and quadrants

Each backend tail contains genuine canonical observations, oldest to newest. No prior point is fabricated or interpolated. Each observation includes both axes, underlying index/benchmark/relative-price evidence, coverage, normalization inputs and metadata, confidence, evidence references, missing-data fields, and winsor flags. The endpoint is `is_current=true`.

For consecutive tail points:

`dx = Relative Trend(t) - Relative Trend(t-1)`

`dy = Relative Momentum(t) - Relative Momentum(t-1)`

`speed = sqrt(dx^2 + dy^2)`

`direction_angle = atan2(dy, dx)`

The tail also records compass direction, cumulative distance, net displacement, recent speed acceleration, and quadrant-transition count. Direction is descriptive and is not a trade instruction.

- Leading: trend `>= 100`, momentum `>= 100`
- Improving: trend `< 100`, momentum `>= 100`
- Weakening: trend `>= 100`, momentum `< 100`
- Lagging: trend `< 100`, momentum `< 100`

Exactly 100 is non-negative. Clockwise rotation is an expected possible tendency, never a forced constraint; reversals, counter-clockwise paths, skips, stalls, and no movement are allowed.

## Evidence, confidence, and availability

The existing Stage 7.5 evidence gates remain authoritative. A coordinate is unavailable without a continuous smoothing/normalization warm-up, exact benchmark intersection, valid positive prices, and canonical evidence references. Confidence begins with actual constituent coverage and is reduced for incomplete tails and disclosed winsorization. Discontinuities and current-membership history are warnings. Optional evidence cannot remove a row that otherwise satisfies the existing canonical evidence gate, and unavailable values are never changed to zero.

## API and migration

Canonical requests are:

- `/market/themes/rotation?profile=short`
- `/market/themes/rotation?profile=medium`
- `/market/themes/rotation?profile=long`

`timeframe=1W|1M|3M` and the older `interval` alias remain accepted. Responses identify taxonomy, snapshot, model, normalization, benchmark, profile definition, current counts, quadrant counts, canonical tails, exclusions, and evidence metadata. Snapshot hashes and frontend request keys contain the new model version. The legacy `relative-return-momentum-v1` engine remains identifiable for sector compatibility; Theme Rotation no longer uses it.

Theme ranking, report candidate scoring, report materiality, Copilot claims, stock/sector ratings, watchlist scores, taxonomy, mappings, security master, providers, and availability thresholds are unchanged. Reports may continue reading the compatibility coordinate fields for a contextual chart; the underlying Theme series identifies the new version and does not feed scoring.

## Limitations

- Historical baskets use current membership.
- The model is descriptive rather than validated as a return predictor.
- Per-theme historical robust scaling favors temporal/universe stability over forced cross-sectional centering.
- A temporary shock can be winsorized and still affect EMA state until it decays naturally.
- A newly listed theme may be unavailable or carry limited confidence until causal warm-up and tail history exist.
- Weekly completeness uses the last observed Friday rule; unusual exchange closures are not inferred from a separate exchange-calendar service in version 1.
- Parameters require governed versioning before change; tuning must optimize mechanical stability/responsiveness, not profitability or a preferred screenshot.
