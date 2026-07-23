# Stage 9.2B — Sector/Theme Compare Specification

## Contract

Endpoint: `GET /market/groups/compare`  
Owner: `backend/app/group_intelligence.py::compare_groups`  
Version: `group-comparison-v1`

Inputs are `entity_type`, comma-separated canonical `ids`, and `timeframe`. Comparison is same-type only because the selected registry is itself typed as `sector` or `theme`.

## Selection rules

| Context | Minimum | Maximum |
|---|---:|---:|
| Desktop | 2 | 5 |
| Mobile (<720px) | 2 | 3 |
| Backend request | 2 | 5 |

Duplicate IDs are removed deterministically. Unknown IDs, mixed-type requests, unsupported timeframes, and selection counts outside the contract return an explicit validation error. The frontend never silently drops valid metrics or manufactures replacements.

## Normalized fields

Every item returns identity, type, name, parent, state/quadrant, 1D/1W/1M/3M/6M/1Y performance, relative strength, relative momentum, breadth above 20/50/200 EMA, A/D ratio and counts, highs/lows, persistence, rank, rank change, movement, data confidence, signal confidence, freshness, availability, evidence identity, and canonical destination.

Null means unavailable. It is rendered as `N/A`, not zero.

## State and URL

The canonical comparison URL is:

`/sectors?compareType={sector|theme}&compareIds={canonical_ids}&compareTimeframe={timeframe}`

Selection and timeframe changes update these parameters. Loading, incomplete selection, available, partial, failed, and unavailable states are explicit. Entity names in the comparison table drill into the existing canonical detail modal.

## Accessibility

- Entity selection uses checkbox semantics and exposes checked/disabled state.
- Timeframes expose selected button state.
- Mobile maximum is described in visible text.
- Identity links have button semantics and open the canonical detail destination.

