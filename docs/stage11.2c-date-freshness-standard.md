# Stage 11.2C Date & Freshness Standard

## Owner

`frontend/src/features/trust/dateFreshnessPresentation.ts`

`confidenceFreshnessPresentation.ts` delegates user-facing freshness grammar to this owner.

## Supported grammar

- Updated just now
- Updated X minutes ago
- Updated X hours ago
- Updated yesterday
- Updated on localized date
- Cached from localized time
- Last successful update
- Evidence through localized date
- Generated localized date and time

The formatter accepts injected `now`, locale, and time zone values for deterministic testing. Browser output follows the current locale clock policy and contains no raw ISO timestamps on primary surfaces.

Observation time, provider update time, snapshot generation, report generation, cache time, and evidence cutoff are distinct labels. A date-only cutoff is never described as “updated.”

Report-document provenance retains exact IDs and cutoffs because report content is frozen. Diagnostics may remain more precise but cannot contradict the plain-language label.
