# Stage 8.75 Sector Rotation Model Specification

## Identity and scope

- Model ID: `sector-relative-trend-momentum`
- Version: `sector-relative-trend-momentum-v1`
- Effective date: 2026-07-23
- Benchmark: SPY
- Normalization: `zero-centered-rolling-robust-scale-v1`
- Entity input: governed adjusted daily close of the canonical sector ETF

This model uses the exact causal indicator kernel and governed Short, Medium, and Long parameters used by `theme-relative-trend-momentum-v1`. Theme inputs are equal-weight basket indexes; Sector inputs are the canonical adjusted sector ETF series. Sector constituent breadth and composite rank remain separate evidence.

## Formulas

For sector ETF adjusted close `S_t` and SPY adjusted close `B_t` on exact shared valid sessions:

- `relative_price_t = S_t / B_t`
- `log_relative_t = ln(relative_price_t)`
- `trend_spread_t = EMA_fast(log_relative)_t - EMA_slow(log_relative)_t`
- `relative_change_t = log_relative_t - log_relative_(t-1)`
- `relative_volatility_t = EWMA_std(relative_change)_t`
- `scaled_trend_t = trend_spread_t / max(relative_volatility_t, epsilon)`
- `Relative Trend_t = 100 + 2 * robust_signed_normalize(scaled_trend_t)`
- `trend_change_t = Relative Trend_t - Relative Trend_(t-lag)`
- `smoothed_trend_change_t = EMA(trend_change, momentum_smoothing)_t`
- `Relative Momentum_t = 100 + 2 * robust_signed_normalize(smoothed_trend_change_t)`

The robust signed normalization is causal. Its scale is the maximum of the trailing median absolute signal, `1.4826 * MAD`, and a floor (`1.0` for trend; `0.1` for momentum). Scores are explicitly winsorized at ±3 and every affected observation records a winsorization flag. There is no cross-sectional centering and no future-data fit.

## Profiles

| Profile | Alias | Frequency | Fast/slow EMA | Relative volatility | Normalization | Momentum lag/smoothing | Tail |
|---|---|---|---:|---:|---:|---:|---:|
| Short | 1W | daily | 10/30 | 30 | 60 | 3/5 | 8 daily observations |
| Medium | 1M | daily | 20/50 | 50 | 126 | 5/10 | 10 observations spaced three sessions |
| Long | 3M | last complete weekly session | 10/26 | 26 | 52 | 4/4 | 8 weekly observations |

The aliases are compatibility identifiers, not return windows.

## Quadrants and trajectories

- Leading: Relative Trend ≥100 and Relative Momentum ≥100
- Improving: Relative Trend <100 and Relative Momentum ≥100
- Weakening: Relative Trend ≥100 and Relative Momentum <100
- Lagging: Relative Trend <100 and Relative Momentum <100

Exactly 100 is non-negative. Unavailable observations are never classified. Each tail is an oldest-to-newest sequence from the latest continuous valid ETF/SPY segment. The endpoint, `dx`, `dy`, speed, angle, compass direction, cumulative distance, net displacement, acceleration, and quadrant-transition count are serialized by the backend. No movement direction is forced.

## Missing data and evidence

- only valid adjusted ETF and SPY closes are accepted;
- dates must intersect exactly;
- no forward-fill, zero-fill, interpolation, or fabricated previous point is allowed;
- an absent ETF observation on a valid SPY session breaks continuity;
- the latest continuity segment alone supplies a tail;
- the ETF and SPY provider series IDs, normalization diagnostics, winsorization flags, snapshot identity, and confidence are preserved per observation;
- sector constituent coverage remains disclosed separately and does not convert a valid ETF observation to a zero coordinate.

## Migration and downstream behavior

`SectorSnapshot.rotation_series` migrates to the new version. The former `relative-return-momentum-v1` series remains explicitly named `legacy_rotation_series` only for the existing compact-dashboard/report-scoring compatibility dependency. Sector rank, classification, breadth, ratings, watchlist behavior, and report candidate materiality are not recalculated from the new chart coordinates. Report figures may visualize the new canonical tails.

## Limitations

- The model is descriptive, not predictive and not a buy/sell signal.
- A sector ETF may not perfectly represent every constituent or industry in the sector.
- Weekly observations require a completed observed week.
- New or short-history ETFs require causal warm-up.
- Winsorization is deterministic and disclosed, so extreme displayed coordinates are intentionally bounded under this version.

## Intellectual-property statement

This is an original transparent implementation inspired only by the general concept of plotting relative-trend strength against the momentum of that trend. It does not reproduce proprietary formulas, use third-party indicator branding, or claim equivalence with another product.
