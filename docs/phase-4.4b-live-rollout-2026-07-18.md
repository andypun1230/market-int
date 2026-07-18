# Phase 4.4B Live Rollout Record, 2026-07-18

## Completed gates

- Reviewed source: `backend/data/reference/sp100-2026-07-18.csv`.
- Source effective date: 2026-07-16; reviewer verification date: 2026-07-18.
- Source validation: PASS, 101 unique active equity securities, no invalid sectors, exchanges, mappings, or duplicate tickers. SHA-256: `5488729a1f914520500f8924fc6cc415fa0c67b5551d3a3bbdbd0e1c430587f4`.
- Import dry run: 101 additions, 0 removals, 0 invalid rows, 0 provider mapping warnings.
- Applied immutable universe: `sp100-v20260718`, member count 101, source timestamp 2026-07-16.
- Mapping validation: 101/101 stored history-provider symbols are canonical; no unsupported mappings. The configured Polygon provider reports daily adjusted history and volume capability, with mock fallback disabled for the check.

## Live gate status

The fresh strict direct-provider probe succeeded: AAPL returned HTTP 200 with five live candles, request ID `45ce4ed98bbd3097dc5caba4e3cd9a59`, and no fallback. The staged seed used a durable `/tmp/sp100-v20260718-live-seed-checkpoint.json` checkpoint, strict live Polygon history, concurrency 2, and bounded retries.

| Stage | New symbols | Inserted bars | Failures | Retries | 429 events |
| --- | ---: | ---: | ---: | ---: | ---: |
| Pilot | 10 | 4,500 | 0 | 0 | 0 |
| Expansion | 15 | 6,750 | 0 | 0 | 0 |
| Full resume | 76 | 33,764 | 0 | 0 | 0 |

The durable store contains 45,014 unique adjusted Polygon bars for all 101 members. `BRK.B` persisted through provider symbol `BRK-B`; `GOOG` and `GOOGL` each have 450 bars. HONA has 14 live sessions from 2026-06-29 because its trading history is new; it is included in member and advance/decline coverage, while EMA20/50/200 and 52-week eligibility transparently remain 99.01%.

The published immutable live snapshot is `breadth-sp100-v20260718-2026-07-17-e605cb5dfd`: complete 101/101 coverage, live Polygon provenance, latest and last-known-good pointers set to that snapshot, 26 advancing and 75 declining members, five 52-week highs, two lows, and 11 sector breadth rows. `validate_phase_4_4b.py --live` passes with no failures or conditions.

The breadth snapshot, Market Breadth, Home, Market Health, and Market Regime reads all return the same breadth ID, universe version `v20260718`, and market date `2026-07-17`; all were HTTP 200 with Polygon history patched to fail, proving zero warm constituent-provider calls.
