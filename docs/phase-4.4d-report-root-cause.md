# Phase 4.4D-2 Daily Report Root Cause

## Classification

**D. PDF template ignoring valid JSON Theme data.**

The screenshot report, `2026-07-17-9218a5db`, was a current pre-store capture,
not an old immutable pre-pilot report. Its JSON already contained published
ThemeSnapshot `theme-2026-07-17-f8ca1be84c`, Cybersecurity (#1, Leading,
100.0), and Memory & Storage (#2, Improving, 62.16). The legacy PDF renderer
ignored that data and rendered hardcoded Phase 4.4D unavailable text.

The pre-store response had no durable report-cache identity or schema metadata,
so there is no legacy cache key to preserve. It remains an archived baseline
capture and was not rewritten.

## Root Cause

`backend/app/services/report.py` had divergent report paths: JSON hydrated
`theme_intelligence`, while the PDF sector/theme page and leadership narrative
used literal unavailable placeholders. There was also no immutable report
storage, latest pointer, or report-ID-pinned PDF URL.

During live verification, report assembly also invoked the interactive market
narrative. That seeded Copilot's shared `analysis:market` cache while the
report no-fetch guard was active, leaving a partial no-provider view available
to later Copilot reads. This was an independent cache-isolation defect.

## Resolution

- `theme_report` freezes the published ThemeSnapshot once in canonical report
  JSON; PDF rendering consumes only that frozen payload.
- The report identity includes Market, Breadth, Sector, and Theme snapshot IDs,
  report schema, and PDF format version.
- SQLite persists immutable JSON and a write-once PDF BLOB; only the separate
  latest pointer is mutable.
- `/report/daily/pdf?report_id=<id>` returns the exact immutable PDF and the
  frontend stores a report-ID-pinned URL. Legacy generic URLs are marked stale.
- `report_snapshot_read()` blocks provider cache misses and stale refresh work.
  The report-local executive brief is now built from already captured inputs,
  never through the shared interactive market-analysis cache.
- Visual-PDF tests use unique temporary report/cache SQLite paths and restore
  environment variables, preventing test records from reaching report history.

## Final Live Evidence

| Item | Result |
| --- | --- |
| New report ID | `daily-2026-07-17-b74b5db9e204` |
| Generated at | `2026-07-20T05:43:16.514953+00:00` |
| Schema / PDF format | `daily-report-v14` / `daily-report-pdf-v4` |
| MarketSnapshot | `market-20260720T054032Z-c06d8b2b` |
| BreadthSnapshot | `breadth-sp100-v20260718-2026-07-17-56a0bae1cb` |
| SectorSnapshot | `sector-sp100-v20260718-2026-07-17-5397be31d6` |
| ThemeSnapshot | `theme-2026-07-17-f8ca1be84c` |
| JSON Theme section | exactly Cybersecurity (#1, Leading, 100.0) and Memory & Storage (#2, Improving, 62.16) |
| PDF Theme / rotation | visible on page 3, including 1M coordinates and trails |
| Legacy unavailable text | absent |
| Provider work around JSON + PDF | provider calls `16 -> 16 -> 16`; background refreshes `16 -> 16 -> 16` |
| Repeat generation | same report ID and identical JSON SHA-256 `3e822459960647ad5fc4447f493d1d293176d957895c316f6a9b53574c274a35` |

Final cache key:

`report:daily:daily-report-v14:daily-report-pdf-v4:json:market-20260720T054032Z-c06d8b2b:breadth-sp100-v20260718-2026-07-17-56a0bae1cb:sector-sp100-v20260718-2026-07-17-5397be31d6:theme-2026-07-17-f8ca1be84c`

The immutable PDF is
`backend/output/pdf/daily_market_report_daily-2026-07-17-b74b5db9e204.pdf`.
Visual QA is
`backend/tmp/phase-4.4d-report-final-render/latest-theme-page-3.png`.

## Immutability

`INSERT OR IGNORE` preserves an existing identity payload and `pdf_blob IS
NULL` makes PDF assignment write-once. The latest pointer moves independently.
Focused storage tests prove an attempted rewrite returns the original payload;
the old pre-store capture and all valid stored reports were not rewritten.
