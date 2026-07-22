# Stage 8.75 Sector Rotation Mathematics Audit

This audit was recorded before the Sector Rotation mathematics was changed. It documents the legacy graph contract and the downstream compatibility boundary.

## Legacy pipeline

1. `SectorSnapshotBuilder` reads each governed sector ETF's adjusted daily history and adjusted SPY history.
2. `app.rotation.engine.build_rotation_series` intersects valid adjusted ETF and SPY dates.
3. For a selected interval and endpoint `t`, the x-axis input is:

   `raw_rs(t, L) = 100 * ((ETF_t / ETF_(t-L) - 1) - (SPY_t / SPY_(t-L) - 1))`

4. The plotted x coordinate is `100 + raw_rs(t, L)`.
5. The y-axis input is `raw_momentum(t) = raw_rs(t, L) - raw_rs(t-M, L)`.
6. The plotted y coordinate is `100 + raw_momentum(t)`.
7. The legacy intervals are `1W: L=5, M=1, spacing=1`; `1M: L=21, M=5, spacing=5`; and `3M: L=63, M=21, spacing=15`.
8. Every tail contains at most five genuine dates. There is no EMA smoothing, log-relative series, volatility scaling, rolling robust normalization, or momentum-of-trend calculation.
9. Values are time-series return differences shifted by 100, not cross-sectional or historical standardized signals. Missing dates are intersected, but the legacy calculation does not explicitly break continuity when an ETF observation is absent on an otherwise valid SPY session.
10. Quadrants use the deterministic 100 boundaries. Exactly 100 is non-negative on each axis.

## Why the paths are short and abrupt

Five observations of highly overlapping fixed-window returns often form nearly straight paths. Rolling-window entry and exit effects can move both axes abruptly. The midpoint shift clusters small return differences near 100 without making sectors comparable through volatility or robust scale. The y-axis measures a change in a raw return window rather than the momentum of a smoothed relative trend, so the graph does not implement a continuous rotational state model.

## Consumers and migration boundary

- `/market/sectors/rotation` and the Sector Rotation card consume the durable ETF/SPY series.
- the sector detail view reads the series persisted in `SectorSnapshot.rotation_series`.
- report figures may visualize canonical sector tails.
- sector ranking and classification use the existing composite analytics and do not depend on the chart coordinates.
- report research scoring currently reads the compact sector dashboard rotation field. The legacy series is retained under a separately named compatibility field for that consumer so the analytical visualization migration does not silently alter report candidate scoring.
- frontend test scenarios remain explicitly gated fixtures and are not a production fallback.

The new Sector graph is versioned separately. It reuses the exact causal Relative Trend / Relative Momentum mathematical kernel and governed Short, Medium, and Long profiles already validated for Theme Rotation.
