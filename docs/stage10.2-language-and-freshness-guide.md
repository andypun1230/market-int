# Stage 10.2 Language and Freshness Guide

Primary surfaces use trader-facing terms: Data source, Calculation method, Coverage, Confidence, Updated, Evidence, and Limitations.

Implementation terms such as backend-owned, canonical contract, registry, governance, immutable snapshot, and model identifier belong only in methodology, diagnostics, provenance, developer documentation, or source code. Raw provider enums are never user-facing.

## Freshness vocabulary

- Updated just now
- Updated 8 minutes ago
- Cached from 10:32 AM
- Data is 2 hours old
- Last successful update yesterday
- Live source unavailable; showing cached data
- Last update unavailable

Rules:

- “Live” requires verified current provider capability.
- Cached and stale are always qualified.
- “Partial” identifies usable and missing domains.
- Unavailable means missing; it is never displayed as zero.
- Screen-local freshness wording must use the shared formatter where a timestamp exists.
- Technical snapshot/model identifiers remain behind evidence/methodology or diagnostic disclosure where practical.

