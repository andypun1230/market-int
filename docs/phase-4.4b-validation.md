# Phase 4.4B Validation

## Automated Test Result

`python3 scripts/validate_phase_4_4b.py --test` creates an isolated temporary SQLite database, imports a deterministic four-member universe, stores 270 adjusted daily bars per member, publishes an immutable snapshot, and checks warm breadth, snapshot, and history APIs.

Latest result: PASS. The fixture published `sp100-test-v1`, had 4/4 available members, 100% indicator coverage including EMA200, one persisted history point, zero provider calls on warm read, and a warm API elapsed time below 300 ms.

## Live Rollout Status

PASS. The strict live rollout completed for `sp100-v20260718`: all 101 members have durable live Polygon history through 2026-07-17, and `breadth-sp100-v20260718-2026-07-17-e605cb5dfd` is complete with 100% member coverage. The final live validator has no failures or conditions; warm cross-screen reads use that same snapshot without constituent-provider calls. See [the live rollout record](phase-4.4b-live-rollout-2026-07-18.md) for staged seed evidence and the HONA eligibility caveat.
