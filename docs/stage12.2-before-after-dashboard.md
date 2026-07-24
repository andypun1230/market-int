# Stage 12.2 Before/After Performance Dashboard

**Measurement date:** 2026-07-24  
**Classification:** **PASS WITH CONDITIONS**

## Executive dashboard

| Area | Baseline | Optimized | Status |
|---|---:|---:|---|
| Home decision-ready | 4,020 ms | 498 ms p50 / 563 ms p95 | PASS |
| Market decision-ready | 3,972 ms | 460 ms / 483 ms | PASS |
| Sectors decision-ready | 7,113 ms | 2,225 ms / 2,232 ms | PASS; target miss, hard budget met |
| Theme Rotation decision-ready | 10,480 ms | 354 ms / 356 ms | PASS |
| Stock Detail decision-ready | 3,697 ms | 394 ms / 824 ms | PASS |
| Theme summary gzip | 639,751 B | 8,360 B | PASS |
| Rotation gzip | 47,571 B | 15,332 B | PASS |
| Home initial JS gzip | 908,888 B | 587,699 B | PASS |
| Effective cache reuse | 58.0% | 66.7% | improved; target condition |
| Repeat-navigation renderer RSS | — | +80 KB over 28 cycles | no leak confirmed |

## Latency improvement

| Screen | Reduction from baseline |
|---|---:|
| Home | 87.6% |
| Market | 88.4% |
| Sectors | 68.7% |
| Theme Rotation | 96.6% |
| Stock Detail | 89.3% |

## Payload and parsing

| Measure | Baseline | Stage 12.2 |
|---|---:|---:|
| Theme list raw | 6,553,498 B | 86,710 B |
| Theme list parse p50 / p95 | 13.875 / 20.044 ms | 0.182 / 0.339 ms |
| Theme normalization p50 / p95 | 0.245 / 0.386 ms | 0.080 / 0.337 ms |
| Rotation raw | 497,499 B | 114,347 B |
| Example on-demand detail raw | embedded in list | 122,843 B |

## Mobile simulation

These Lighthouse values simulate constrained mobile web and are not substitutes for native-device traces.

| Screen | FCP | LCP | TTI | TBT |
|---|---:|---:|---:|---:|
| Home | 907 ms | 4,108 ms | 5,785 ms | within 193–238 ms range |
| Market | 905 ms | 10,458 ms | 10,458 ms | within range |
| Sectors | 907 ms | 8,265 ms | 8,265 ms | within range |
| Theme Rotation | 905 ms | 9,615 ms | 9,615 ms | within range |
| Stock Detail | 909 ms | 9,042 ms | 9,042 ms | within range |
| Reports | 904 ms | 6,754 ms | 6,754 ms | within range |
| Copilot | 905 ms | 4,098 ms | 5,986 ms | within range |

Decision-ready user timing and Lighthouse LCP answer different questions. The hard Stage 12.2 budgets use the former; constrained mobile LCP remains a release follow-up.

## Gate summary

- Desktop-web hard budgets: **PASS**.
- Payload contracts and identity equivalence: **PASS**.
- Production export, TypeScript, lint, frontend tests, and focused backend tests: **PASS**.
- Full backend: **635/636**, with one historical Stage 8.75 snapshot-evidence mismatch caused by intentionally unchanged historical artifacts.
- Native iOS/Android startup, frame, and heap evidence: **OUTSTANDING**.
- Overall: **PASS WITH CONDITIONS**.

