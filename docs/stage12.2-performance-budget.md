# Stage 12.2 Performance Budget

## Release budgets

| Category | Metric | Target | Hard limit | Observed | Result |
|---|---|---:|---:|---:|---|
| Decision readiness | Home p50 | <=1,500 ms | <=2,000 ms | 498 ms | PASS |
| Decision readiness | Market p50 | <=1,500 ms | <=2,000 ms | 460 ms | PASS |
| Decision readiness | Sectors p50 | <=2,000 ms | <=2,500 ms | 2,225 ms | PASS with target miss |
| Decision readiness | Theme Rotation p50 | <=2,000 ms | <=3,000 ms | 354 ms | PASS |
| Decision readiness | Stock Detail p50 | <=1,500 ms | <=2,000 ms | 394 ms | PASS |
| Payload | Theme summary gzip | <=500 KB | <1 MB | 8,360 B | PASS |
| Payload | Theme rotation gzip | <=250 KB | <500 KB | 15,332 B | PASS |
| Bundle | Home initial JS gzip | <=700 KB | <=900 KB | 587,699 B | PASS |
| Main thread | Desktop TBT | <=100 ms | <=300 ms | 0 ms | PASS |
| Memory | Repeat-nav retained growth | no monotonic leak | investigate >10 MB | +80 KB/28 cycles | PASS |
| Cache | Effective reuse | >=70% | no correctness tradeoff | 66.7% | CONDITION |

## Measurement rules

- Use a production web export served locally, not a development bundle.
- Record at least three independent desktop runs; report median as p50 and maximum as a conservative small-sample p95.
- Start decision-ready timing only from the navigation start mark and end it at the committed critical decision layer.
- Report route-complete separately so deferred content does not disguise critical readiness.
- Use raw and gzip transfer sizes for API and JavaScript contracts.
- Compare compact contracts with the same immutable snapshot/taxonomy/model identity as the legacy contract.
- Measure cold-service latency after restart separately from warm cache latency.
- Never improve a budget by extending financial freshness, hiding availability, suppressing errors, or pre-rendering unsupported conclusions.

## Guardrail budgets

- Zero per-item N+1 requests on Theme Directory or Rotation.
- Zero late-response overwrites after navigation or explicit refresh.
- Zero false empty states when an authoritative summary remains available.
- Zero unbounded client-cache growth.
- Zero route removals or financial-model changes.
- Zero historical artifact rewrites within Stage 12.2.

## Release interpretation

A target miss with a hard-limit pass may ship as **PASS WITH CONDITIONS** when correctness and visual acceptance pass and a concrete follow-up is recorded. Any hard-limit failure, correctness regression, stale-data misrepresentation, or financial-contract divergence is **FAIL**.

Strict cross-platform PASS additionally requires native iOS and Android cold/warm launch, frame pacing, and heap traces on representative devices.

