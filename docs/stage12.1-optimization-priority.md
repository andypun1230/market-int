# Stage 12.1 Optimization Priority

This is a recommendation backlog only. Stage 12.1 did not implement any item.

## Prioritized opportunities

| Rank | Severity | Opportunity | Evidence | Expected gain | Suggested validation |
|---:|---|---|---|---|---|
| 1 | High | Split route bundles and lazily load analytical modules | One 3.59 MB raw JS chunk; 60.49% unused on Home | 450–600 KB less first-load gzip; 40–90 ms less JS init | Bundle analyzer plus three cold launches per route |
| 2 | High | Make theme datasets route-specific, compact, or paged | `/market/themes` is 6.55 MB and gates Sectors-family views | >6 MB less sector-only transfer; data readiness toward <2 s warm/local | Payload contracts and Sectors/rotation/compare profiles |
| 3 | High | Precompute or parallelize Theme Rotation dependencies | Rotation starts after ~7 s base load and adds 3.39 s | Final visual from 10.48 s toward <4 s locally | Cold and warm dependency waterfall tests |
| 4 | High | Reduce cold Home/Market materialization cost | Cold critical APIs ~3.6–3.7 s; warm 40–50 ms | At least 1.5 s faster cold decision readiness | Cleared-cache p50/p95 API and route runs |
| 5 | Medium | Consolidate/terminate Stock Detail refresh polling earlier | Three `/stock-analysis/NVDA` reads plus two summaries | Final readiness from 3.70 s toward <1.5 s; ~520 KB less transfer | Snapshot-state contract and network-call-count test |
| 6 | Medium | Subset the Material Symbols font | 425 KB gzip font | 300–400 KB gzip reduction | Icon coverage, accessibility, and bundle snapshot |
| 7 | Medium | Bound and sweep request cache; cap/page report history | Unbounded Maps and all-history load | Bounded long-session heap and storage | 100-symbol and 1,000-report memory soak |
| 8 | Medium | Batch or virtualize heatmap load work | Two dropped-frame events; ~96 ms longest task | Zero observed load drops; lower listener/node work | Native and web frame trace |
| 9 | Medium | Virtualize long Copilot histories | Saved history produced 1,283 nodes | Estimated 30–60% lower long-chat DOM | Large-history scroll and heap test |
| 10 | Low | Deduplicate static route-alias HTML at deployment | Five exact pairs, ~231 KB redundant raw output | ~231 KB smaller export, no runtime gain | Deep-link hosting regression |
| 11 | Low | Prune platform-unused source assets | 1.37 MiB source asset set | Package-size reduction only | Per-platform asset manifest |

## Recommended execution order

1. Establish target-device/native baselines so changes can be compared with the same launch, FPS, and memory protocol.
2. Address server payload/dependency issues for themes and rotation; these dominate user waiting time.
3. Address cold Home/Market aggregation.
4. Split the JS bundle and subset the icon font.
5. Consolidate Stock Detail refresh behavior without changing snapshot semantics.
6. Bound long-session memory structures and then address heatmap/Copilot rendering risks.
7. Take deployment-only size work last.

## Guardrails for the optimization stage

- Preserve intelligence calculations, freshness, confidence, and provider semantics.
- Preserve canonical routes and existing information hierarchy.
- Compare decision-ready time, not only Lighthouse shell score.
- Require payload and request-count contract tests for network changes.
- Require memory soak and native frame captures for retention/render changes.
- Roll out one bottleneck class at a time so gains and regressions remain attributable.
