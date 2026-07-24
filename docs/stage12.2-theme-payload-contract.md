# Stage 12.2 Theme Payload Contract

## Contract split

| Consumer | Endpoint | Contract | Authority |
|---|---|---|---|
| Directory, heatmap, search/filter inputs, leadership list | `GET /market/themes` | `theme_summary_v1` | `ThemeIntelligenceService` projection of the canonical snapshot |
| Detail modal, constituent/governance methodology | `GET /market/themes/{theme_id}` | `theme_detail_v1` | Canonical Theme Intelligence row |
| Rotation map | `GET /market/themes/rotation/summary` | `theme_rotation_summary_v1` | Canonical ThemeSnapshot rotation series |
| Legacy/full analytical consumers | `GET /market/themes/rotation` | existing full payload | Canonical ThemeSnapshot rotation series |
| Comparison | `GET /market/groups/compare` | existing canonical group comparison | Group Intelligence |

No calculation was copied into a serializer. Summary contracts select existing authoritative fields.

## Summary fields

The list payload preserves theme ID/display name, taxonomy and snapshot identity, status/source/freshness/confidence, rank and classification, composite score, coverage, member count, performance, participation, concentration, score semantics, pilot/methodology labels, warnings, aliases, and the compact definition required for canonical filtering.

It omits full members, evidence records, provenance records, rotation series, repository statistics, coverage audit, and duplicate `rows`.

## Rotation fields

The compact rotation payload preserves theme identity, aliases/parent sectors, snapshot/taxonomy/model/profile/timeframe identity, current and previous coordinates, governed trail points, quadrant/trajectory/movement, rank/label priority, confidence, evidence references, coverage, availability, exclusions, freshness/as-of, and warnings.

It omits duplicated top-level `series`, `tails`, normalization metadata, current-point duplicates, compatibility signatures, and full theme detail.

## Detail guarantee

The detail route preserves full members, provenance, rotation series, contribution analytics, breadth, concentration, methodology, warnings, missing data, and relevant overlap. The separate evidence and constituent routes remain available. Contract tests prove fields omitted from list/rotation remain present in detail fixtures and that compact coordinates equal the legacy full response.

## Size and parse results

| Contract | Raw | Gzip | Hard budget | Result |
|---|---:|---:|---:|---|
| Theme summary | 86,710 B | 8,360 B | <1 MB gzip | PASS |
| Theme rotation | 114,347 B | 15,332 B | <500 KB gzip | PASS |
| Example Theme Detail | 122,843 B | 13,069 B | on demand | PASS |

Theme summary parse p50/p95 is 0.182/0.339 ms; adapter normalization is 0.080/0.337 ms. The Stage 12.1 legacy payload parsed at 13.875/20.044 ms.

## Identity and invalidation

- Summary cache key: semantic contract version, five-minute TTL.
- Rotation key: taxonomy version, immutable snapshot ID, model version, timeframe/profile.
- Detail key: taxonomy version, immutable snapshot ID, canonical theme ID, contract version.
- A latest rotation response primes the immutable identity key. Explicit refresh and published snapshot changes obtain a new identity rather than mutating cached intelligence.

