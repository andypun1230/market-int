# Stage 8.75 Theme Rotation progressive UX

## Scope and invariant

This patch changes Theme Rotation presentation only. Canonical analytical coordinates, the Relative Trend / Relative Momentum formulas, normalization, taxonomy, mappings, providers, ranking, coverage rules, and evidence thresholds are unchanged. Hidden themes remain in the fetched source and are available through **Show all themes** or reset. Smart labels never remove points.

## View modes

- **Overview** scans the governed universe with Smart labels and short tails. The default Meaningful filter is visibly disclosed.
- **Compare** uses the same chart and stable full-response domain for 2–8 selected themes by default. It uses 8-point tails, Selected labels, and a compact governed-metric table. Larger selections remain possible with a readability warning.
- **Focus** starts on the first node, tail, label, or selector Focus action. It uses the full genuine tail, a full label, a textual inspector, and explicit detail/save/exit/related actions. Other themes are faint current-point context or may be hidden, so their tails do not compete with the focused trajectory.

Focus explicitly overrides quadrant, movement, and transition filters so a selected endpoint cannot disappear. The active summary discloses this override.

## Universe and selection

Composite universe labels are presentation groups whose membership is resolved from canonical `parent_sector_ids`:

- Technology & AI: Information Technology
- Consumer & Digital: Consumer Discretionary or Communication Services
- Industrials & Strategic Growth: Industrials, Energy, Utilities, Materials, or Real Estate
- Healthcare: Health Care
- Finance & Crypto: Financials
- Saved Themes: canonical theme IDs in the unified watchlist
- Custom Selection: explicit canonical selection

The selector searches canonical name, canonical ID, and reviewed aliases, normalizes separators, deduplicates canonical IDs, excludes retired definitions, preserves insertion order, supports select-all-visible and clear, and discloses unavailable rows without plotting invalid coordinates. More than 8 selections on compact screens or 12 on larger screens produces a soft warning, never an analytical failure.

## Related themes

Related themes are deterministic. The resolver scores shared canonical parent sectors first and then existing constituent overlap (`max(jaccard, weighted overlap)`). It sorts by score, rank, display name, and canonical ID. It does not use names or an LLM. Focus may emphasize those themes or use them to build an up-to-8 comparison.

## Filters and tails

Quadrant filtering uses the current canonical endpoint and keeps or removes the whole tail. Tail choices are Current, 3, 5, 8, and Full. Projection only slices backend observations; it never creates, interpolates, or connects observations. The backend already emits only the latest continuous tail segment.

Movement uses canonical response metrics and policy `theme-rotation-view-policy-v1`:

- Meaningful: canonical speed above the source median, canonical net displacement above the source median, or a canonical recent quadrant transition.
- Fast Movers: deterministic top 20% by canonical speed, with canonical ID tie-breaking.
- Stable: deterministic bottom 20% by canonical speed with an available latest transition that did not change quadrant.

These are visibility rules, not analytical reclassification. Threshold fractions and the policy version are exported together.

Transition filters consume the canonical `latest_quadrant_transition` descriptor: Entered Leading, Entered Improving, Lost Leading, Quadrant Changed, and No Recent Change. A row without previous history is excluded from specific transition filters and is never assumed unchanged.

## Deterministic filter order

`buildVisibleRotationView(source, viewState)` is the only view filter pipeline:

1. Canonical row-level eligibility
2. Universe/category/saved filter
3. Explicit selection for Custom or Compare
4. Overview/Compare/Focus constraint
5. Current-endpoint quadrant
6. Governed movement metrics
7. Canonical latest transition
8. Genuine-tail projection
9. Label candidate selection

It returns visible themes, tails, current points, rendered label IDs, user and data exclusions, counts, related IDs, movement sets, and an active-filter summary. It never mutates source rows.

## Labels and counts

- Smart: points remain visible; deterministic priority is Focus, explicit selection, saved, quadrant changer, fast mover, canonical label priority, leader, then improver.
- Selected: labels explicit comparison selections; in Focus, labels only the inspected theme while the comparison selection remains preserved.
- All: attempts every visible label with deterministic collision fallback.
- None: removes labels only.

The footer separates plotted themes, rendered label candidates, themes hidden by presentation filters, and themes unavailable by governed evidence. It also reports genuine historical-node count and the movement policy version.

## Saved themes and deep links

The existing unified watchlist is the only saved-theme store. Saved IDs drive the Saved Themes universe, chart badges, Smart priority, Focus save/unsave, and the selector's **Load saved themes** comparison action. Saved Theme cards now open Theme Rotation in Focus rather than navigating away on the first inspection tap.

## Persistence

The existing session preference seam retains safe label, quadrant, universe, movement, and tail choices. Temporary mode, focused IDs, related-theme state, and custom comparison selections are not persisted. Automatically selecting a full Focus tail does not overwrite the saved tail preference. No new persistence system was introduced.

## Responsive and accessible behavior

Compact screens start with Overview, All Themes, All quadrants, Meaningful movement, All transitions, 3-point tails, and Smart labels. Larger screens use 5-point Overview tails. A compact toolbar opens the existing modal/sheet pattern for filters and multi-select, leaving chart space available. All filters have visible labels; selection rows expose checkbox state; focus state, counts, quadrant, direction, trajectory metrics, and filter summaries have text equivalents; buttons retain practical 44px minimum targets; and the shared modal preserves reduced-motion behavior.

## Performance

Hook request identity depends only on canonical snapshot/taxonomy/model/profile inputs. Presentation state is local and memoized, so labels, quadrant, tail length, movement, transition, focus, and comparison do not refetch. The full response supplies the stable chart domain. Metadata and saved-ID maps, chart-domain points, related resolution, label keys, and selection keys are memoized. The governed universe is 26 rows; deterministic overlap work is bounded.

The Stage 8.75 benchmark records p50/p95 for the full selector, universe, movement, transition, tail, Smart labels, Focus, and Compare.

## Known limitations

- A 26-label All view can still be dense on a phone; it remains intentionally available and is not the default.
- Compare selections above the recommended limit remain available but may require user label/tail adjustment.
- Related-theme quality is limited to reviewed parent metadata and the available overlap matrix.
- Native device font metrics can move collision fallbacks slightly; no coordinate or point is affected.
