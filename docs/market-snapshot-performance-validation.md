# Market Snapshot Performance Validation

## Before

Observed live cold-path bottlenecks included:

- market summary around 49 seconds
- market health around 74 seconds
- risk dashboard around 74 seconds
- sectors around 98 seconds
- sector breadth and leadership sometimes exceeding client timeout budgets

Root cause: user requests triggered live history hydration and recursive aggregate calculations.

## After

The snapshot architecture separates background build latency from user read latency. Warm user-facing reads deserialize the latest prepared snapshot and should make zero provider calls.

Targets:

- `/market/snapshot/latest`: under 300 ms
- `/home/dashboard`: under 500 ms
- `/market/regime`: under 500 ms
- `/market/health`: under 500 ms
- `/market/risk`: under 500 ms
- `/market/decision-dashboard`: under 500 ms
- `/market/fear-greed`: under 500 ms

## Validator

Run test-mode validation:

```bash
cd backend
python3 scripts/validate_market_snapshot_performance.py --test --warm --json-output ../docs/market-snapshot-performance-validation.json
```

Run live validation explicitly:

```bash
cd backend
python3 scripts/validate_market_snapshot_performance.py --live --cold --json-output /tmp/market-snapshot-cold.json
python3 scripts/validate_market_snapshot_performance.py --live --warm --json-output /tmp/market-snapshot-warm.json
python3 scripts/validate_market_snapshot_performance.py --live --restart --json-output /tmp/market-snapshot-restart.json
```

## Current Conditions

`PASS WITH CONDITIONS` remains acceptable for:

- simulated sector/theme/breadth areas that are intentionally not fully migrated
- native visual checks
- external live-provider latency during background builds

It is not acceptable for warm Home/Market reads to trigger provider calls.
