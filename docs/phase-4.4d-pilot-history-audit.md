# Phase 4.4D-2 Pilot History Audit

Generated: `2026-07-19T18:55:00Z`

## Durable pilot history

| Canonical ticker | Durable bars | First session | Last session | Provider history identity |
| --- | ---: | --- | --- | --- |
| MU | 450 | 2024-09-30 | 2026-07-17 | MU |
| SNDK | 351 | 2025-02-24 | 2026-07-17 | SNDK |
| WDC | 450 | 2024-09-30 | 2026-07-17 | WDC |
| STX | 450 | 2024-09-30 | 2026-07-17 | STX |
| MRVL | 450 | 2024-09-30 | 2026-07-17 | MRVL |
| NTAP | 450 | 2024-09-30 | 2026-07-17 | NTAP |
| P | 513 | 2024-07-01 | 2026-07-17 | PSTG through 2026-04-16; P from 2026-04-17 |
| CRWD | 450 | 2024-09-30 | 2026-07-17 | CRWD |
| PANW | 450 | 2024-09-30 | 2026-07-17 | PANW |
| FTNT | 450 | 2024-09-30 | 2026-07-17 | FTNT |
| ZS | 450 | 2024-09-30 | 2026-07-17 | ZS |
| OKTA | 450 | 2024-09-30 | 2026-07-17 | OKTA |
| CHKP | 450 | 2024-09-30 | 2026-07-17 | CHKP |
| S | 450 | 2024-09-30 | 2026-07-17 | S |

All series use adjusted live Polygon daily history. The two baskets have sufficient durable coverage for EMA200, 52-week calculations, relative strength, rotation, and equal-weight basket construction.

## Checkpoint and resume

The first strict-live seed worker batch completed durable writes before its checkpoint path was found missing. No bars were deleted. The CLI now creates its checkpoint parent deterministically. The resumed run completed all fourteen checkpoint entries with zero failures, zero inserts, and 168 bounded overlap updates; it never restarted the full histories.

## P / PSTG stitch

- Canonical security: `theme-sec-everpure-1474432` (`P` / Everpure)
- Historical alias: `PSTG` / Pure Storage
- PSTG source bars: 450; P source bars: 63; stitched total: 513
- Transition: 2026-04-16 PSTG close 67.80 to 2026-04-17 P close 66.97
- Boundary return: -1.2242%; overlap count: 0; alias transition gap count: 0; duplicate count: 0
- No synthetic return, smoothing, or manual normalization was applied.

The canonical rows retain the current ticker, canonical security ID, source symbol, Polygon provenance, and `PSTG_to_P_same_issuer_verified` lineage. The closed PSTG era is reused on resume; only the open P era receives a bounded overlap refresh.
