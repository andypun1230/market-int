# Stage 11.2C Screen-Reader Semantic Report

## Result

**PASS**

Representative runtime semantic-tree checks covered Home, Market, Sector Heatmap, Theme Rotation, Watchlist, Stock Detail, alerts, Compare, Report Preview, Copilot, Settings, empty/error/loading, and unmatched-route states.

## Findings

- Screen and card headings form a logical hierarchy.
- Horizontal navigation exposes tablist/tab roles and selected state; position hints are provided where practical.
- Modals expose a dialog name, Close action, modal boundary and focus trap.
- Charts expose concise region summaries; chart-only labels are not the sole interpretation path.
- Alerts announce severity before title/detail and include confidence/freshness once.
- Comparison rows expose header text and each value has a metric-qualified accessible label.
- Report sections expose named tabs and roving selection.
- Copilot exposes a named input, send state, question/answer roles and localized generation time.
- Settings switches expose checked/disabled state and 44×44 targets.
- Empty, error, loading and unmatched-route states expose headings, concise descriptions and reachable actions.
- Decorative icons are hidden and runtime snapshots contain zero control characters.

Dynamic completions avoid duplicate announcements through centralized loading/state surfaces. Native iOS and Android semantics use React Native accessibility roles/states; web behavior was verified in the runtime accessibility tree.
