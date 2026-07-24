# Stage 12.2 Progressive Rendering Specification

## Instrumentation

Every instrumented route may emit:

1. `market-intelligence:<route>:first-analytical-content`
2. `market-intelligence:<route>:decision-ready`
3. `market-intelligence:<route>:route-complete`

Layout-effect timing records the committed decision layer instead of a delayed passive effect. Metrics are separate and never redefine availability or freshness.

## Screen layers

| Screen | Critical decision layer | Secondary layer |
|---|---|---|
| Home | data-state banner and Home decision summary | supporting cards/evidence |
| Market | canonical core/regime overview and headline indices | structure, decision, institutional drill-downs/history |
| Sectors | ranked sectors and current snapshot state | rotation history, comparisons, registries |
| Theme Rotation | compact current plot/top movement and profile identity | directory metadata, related themes, detail, advanced comparison |
| Stock Detail | current quote, overview decision summary, key risk | technical/signals/risk/compare evidence |
| Reports | report library/history | generation and PDF |
| Copilot | saved shell/session | new streamed answer |

## State rules

- Existing geometry/skeleton primitives are preserved.
- A loading secondary never converts available critical content to empty/unavailable.
- Cached/stale/partial/live labels come from authoritative payload state.
- Unsupported conclusions are not rendered before their owning response exists.
- Theme Detail shows the published list summary while detail loads; on failure it says the summary remains available.
- Full detail is requested only when the modal opens.

## Acceptance evidence

Twenty required cases and 23 screenshots are recorded in `artifacts/stage12.2-visual-acceptance.json`. The failure case intentionally disabled the backend after the critical Theme Rotation data was present; the UI retained the summary and displayed `Theme detail failed: Failed to fetch` instead of a false empty state.

