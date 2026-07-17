# Market Snapshot Architecture

## Why The Old Path Was Slow

The previous user-facing path let endpoints such as `/home/dashboard`, `/market/regime`, `/market/health`, `/market/decision-dashboard`, and `/market/details/*` call aggregate services directly. Those services recursively called other engines:

- `market-health` called index snapshots, breadth, regime, sectors, sector ETFs, leadership, institutional activity, volume, Fear & Greed, and cap rotation.
- `decision-dashboard` called health, regime, breadth, sectors, risk, leadership, probabilities, comparison, industry rotation, and institutional intelligence.
- Sector and breadth services could hydrate multiple history baskets.

The Polygon coordinator converted provider fan-out into a bounded queue, but user requests still waited for that queue and repeated derived calculations.

## Snapshot Flow

The new flow is:

1. `MarketSnapshotInputPlanner` creates one canonical input plan.
2. `MarketSnapshotBuilder` fetches normalized inputs through `MarketDataRepository`.
3. Calculations run once in the background build.
4. The completed or partial `MarketSnapshot` is persisted immutably in SQLite.
5. The `latest_snapshot_id` pointer is updated atomically.
6. Home and Market endpoints read the latest prepared snapshot.

## Model

`MarketSnapshot` stores immutable metadata plus independent `SnapshotSection` records. A section carries status, coverage, dependencies, warnings, duration, and payload. Snapshot statuses are `complete`, `partial`, `stale`, `unavailable`, and `initializing`.

Sections are independent: a failed optional section does not blank unrelated cards.

## Persistence

SQLite tables:

- `market_snapshots`
- `market_snapshot_state`

Published snapshots are never updated in place. A refresh inserts a new row and atomically advances `latest_snapshot_id`. `last_successful_snapshot_id` remains available after failed refreshes.

## Background Refresh

FastAPI startup initializes storage and schedules snapshot refresh without blocking application readiness. `MARKET_SNAPSHOT_STARTUP_REFRESH=false` disables startup refresh for tests.

Important env vars:

- `MARKET_SNAPSHOT_ENABLED`
- `MARKET_SNAPSHOT_REFRESH_INTERVAL_SECONDS`
- `MARKET_SNAPSHOT_STARTUP_REFRESH`
- `MARKET_SNAPSHOT_STARTUP_DELAY_SECONDS`
- `MARKET_SNAPSHOT_MAX_AGE_SECONDS`
- `MARKET_SNAPSHOT_STALE_SECONDS`
- `MARKET_SNAPSHOT_RETENTION_COUNT`

## Migrated Reads

These read snapshot payloads and do not fetch providers on warm reads:

- `/market/snapshot/latest`
- `/home/dashboard`
- `/market/core-snapshot`
- `/market/regime`
- `/market/health`
- `/market/risk`
- `/market/fear-greed`
- `/market/decision-dashboard`
- `/market/details/decision`
- `/market/details/structure`

If no snapshot exists, Home/Core return compact initializing payloads and trigger one background refresh.

## Out Of Scope

This pass intentionally does not implement full live sector/theme/breadth migration, new providers, Redis/Celery, WebSockets, or report/Copilot migration.
