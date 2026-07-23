# Stage 9.2B — Divergence Rule Registry

Owners are partitioned by domain: market-index confirmation remains owned by `backend/app/breadth/builder.py::detect_divergence`; Sector/Theme divergence is owned by `backend/app/group_intelligence.py::detect_divergences`. No rule is calculated by both owners. Group output version: `group-divergence-v1`.

| Rule ID | Direction | Deterministic trigger |
|---|---|---|
| `index_rising_breadth_falling` | negative | index return >3% and above-20 breadth change <-8 points |
| `index_falling_breadth_improving` | positive | index return <-3% and above-20 breadth change >8 points |
| `sector_price_rising_participation_weakening` | negative | Sector 1M return >2% and above-50 breadth change <-5 points |
| `theme_relative_strength_rising_breadth_falling` | negative | Theme relative-strength change >1 and above-50 breadth change <-5 points |
| `index_high_not_confirmed_by_new_highs` | negative | index is at its period high and highs-minus-lows change <0 |
| `rank_improvement_without_persistence` | mixed | rank improves by at least 2 and current-state persistence is below 2 snapshots |
| `momentum_improvement_relative_trend_weak` | positive | relative momentum improves by >5 while relative strength remains below 0 |

Additional governed group cases cover general price/breadth divergence, rotation deterioration/improvement, A/D deterioration, highs/lows deterioration, and leadership concentration. They use the same output contract and deduplication policy.

## Output contract

Every alert contains a stable SHA-256-derived ID, rule ID, canonical entity, direction, severity, detection date, structured evidence, explanation, why-it-matters text, confirmation condition, invalidation condition, confidence, freshness, availability, and canonical destination.

Severity is a deterministic magnitude bucket. Results sort by severity, rule ID, and stable ID. IDs deduplicate before Sector alert grouping. Rules do not fire when a required metric is unavailable, preventing contradictory conclusions from fabricated defaults.

Focused backend tests independently cover all seven rule cases, positive and negative paths, stable repeated output, and duplicate-free identities.
