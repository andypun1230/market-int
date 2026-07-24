# Stage 12.2 Cache and Request Deduplication Report

## Objective

Reduce repeated transfer and computation without weakening freshness, provider-state, snapshot-identity, or availability semantics. Cache behavior remains an acceleration layer; it does not create or reinterpret intelligence.

## Implemented controls

| Layer | Change | Correctness guard |
|---|---|---|
| Browser request cache | Bounded 128-entry LRU for eligible GET responses | Existing TTL and stale policy remain endpoint-specific |
| In-flight requests | Identical cacheable requests share one promise | Failed or aborted requests are not retained as successful values |
| Theme summary | Five-minute semantic-contract cache | Contract version participates in the key |
| Theme rotation | Latest response primes an immutable identity key | Snapshot, taxonomy, model, profile, and timeframe participate in the key |
| Theme detail | Loaded only after detail is opened | Theme ID and immutable snapshot identity participate in the key |
| Async hooks | Abort signals and request sequence guards | Late responses cannot overwrite a newer route/request state |
| Repository stores | One schema/canonicalization initialization per storage instance | Reads and publication still use the same durable canonical store |

## Observed reuse

| Metric | Stage 12.1 | Stage 12.2 | Result |
|---|---:|---:|---|
| Repository memory hits | not separated | 171 | observed |
| Repository persistent hits | not separated | 19 | observed |
| Repository misses | not separated | 114 | observed |
| Memory hit rate | — | 60.0% | informational |
| Effective reuse `(memory + persistent) / (memory + misses)` | 58.0% | 66.7% | +8.7 pp |
| Service cache hits / misses | — | 29 / 30 | informational |
| Provider calls | — | 26 | no duplicate-per-theme pattern |
| Background refresh failures | — | 0 | PASS |

The 70% optimization target was narrowly missed, but the hard product budgets pass. Further TTL expansion was rejected because it could weaken freshness semantics.

## Request correctness

- Concurrent identical rotation calls are deduplicated.
- Compact and legacy rotation contracts resolve the same authoritative coordinates and identity.
- A new published snapshot produces a new immutable cache identity.
- Cache hits preserve provider, freshness, availability, and as-of labels from the source payload.
- A stale value is shown only through the existing stale-while-refresh state and remains labeled stale.
- Detail failure does not replace an available summary with an empty state.

## Memory and eviction

The browser cache is capped at 128 entries and refreshes recency on hits. After 28 repeated major-route navigations, the measured renderer RSS changed from 84,464 KB to 84,544 KB (+80 KB) and final DOM cardinality remained stable. This does not establish a native-memory guarantee, but no browser retention leak was confirmed.

## Follow-up

- Profile cache reuse and eviction on physical iOS and Android devices.
- Revisit the 70% reuse target only with production request traces; do not lengthen freshness windows solely to reach it.
- Preserve immutable identity keys if future compact contracts are added.

