# Stage 9.2B — Breadth History Specification

Endpoint: `GET /market/groups/breadth-history`  
Owner: `backend/app/group_intelligence.py::build_breadth_history`  
Version: `group-breadth-history-v1`

## Inputs

- `entity_type`: `sector` or `theme`
- `entity_id`: canonical entity identity
- `timeframe`: 1M, 3M, 6M, or 1Y

## Measures

- percent above 20 EMA
- percent above 50 EMA
- percent above 200 EMA
- advance/decline ratio and available counts
- new highs, new lows, and highs minus lows

Sector and Theme responses share the contract. A measure that the upstream snapshot does not publish remains `null`; the response status becomes partial where appropriate.

## Historical integrity

Only immutable SectorSnapshot or ThemeSnapshot payloads in durable storage are read. No series is backfilled, interpolated, copied from another entity, or generated from a current snapshot. `snapshot_ids` lists the exact evidence used.

## Interpretation owner

`_breadth_interpretation` is the sole conclusion owner. It compares the first and latest available observations, counts improving and weakening internal measures, and emits:

- state: expanding, weakening, stable, diverging, or unavailable;
- one conclusion;
- structured evidence with from/to/change;
- confidence based on available measure count and observation count;
- evidence freshness.

At least two observations are required. Missing history produces an unavailable conclusion with an explanatory reason.
