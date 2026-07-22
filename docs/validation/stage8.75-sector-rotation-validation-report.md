# Stage 8.75 Sector Rotation Validation Report

Result: **PASS**

Snapshot: `sector-sp100-v20260718-2026-07-21-67cb07c4fe`; model: `sector-relative-trend-momentum-v1`; schema: `5`.

The Sector Rotation graph now uses the exact causal Relative Trend / Relative Momentum kernel and profile parameters validated for Theme Rotation, with adjusted canonical sector ETF closes as the entity index and SPY as benchmark.

| Profile | Sectors | Coordinates | Leading | Improving | Weakening | Lagging |
|---|---:|---:|---:|---:|---:|---:|
| Short | 11 | 88 | 4 | 2 | 0 | 5 |
| Medium | 11 | 110 | 2 | 6 | 2 | 1 |
| Long | 11 | 88 | 1 | 5 | 1 | 4 |

Mathematical/parity tests: **9/9 passed**.

The old fixed-window series remains only in the explicitly named compatibility field used by the compact dashboard/report-scoring dependency. Sector rankings, classifications, breadth, and report candidate scoring are unchanged.

Hermetic validation made zero network calls, zero model calls, and zero provider calls during warm canonical retrieval.

## Reproduction

`make validate-stage8-75 PYTHON=python3`
