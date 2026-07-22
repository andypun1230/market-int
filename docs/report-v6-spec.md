# Report V6 Specification

## Product contract

Report V6 is a chart-led daily research briefing built from one immutable `ReportDocument`. The API response persists that document; both the browser preview and PDF render it without independently rebuilding prose. V5 report records and stored PDFs remain readable.

The analytical order is fixed unless a section has no supportable evidence:

1. Cover and current thesis
2. Executive summary
3. Major index structure
4. Breadth and participation
5. Leadership and rotation
6. Cross-asset and macro confirmation
7. Risk, volatility, credit, and sentiment
8. Scenario framework and sourced events
9. Watchlist and security research
10. Next-session operating plan
11. Methodology, sources, and limitations

Complete after-close reports target 12-16 pages and 15-25 meaningful figures. These are targets, not padding requirements. Unsupported sections and figures are omitted and recorded in the limitations registry.

## Architecture

The existing ReportLab renderer remains the PDF engine. It already provides deterministic, vector-first output, embedded PDF metadata, immutable blob storage, and no browser/runtime deployment dependency. V6 separates its concerns into:

- `reports/document.py`: strongly typed report, claim, evidence, figure, source, quality, scenario, security, and monitoring models.
- `reports/document_builder.py`: deterministic aggregation and grounded analytical writing.
- `reports/figures.py`: figure specifications and transformations from frozen report inputs and durable history.
- `reports/pdf_v6.py`: page composition and drawing only.
- frontend V6 preview: renders the serialized `ReportDocument`; V5 falls back to its existing preview.

Report generation continues inside `report_snapshot_read()`. No V6 builder or renderer may initiate provider traffic. Time series come from frozen response fields or durable snapshot/bar storage.

## Grounding rules

- Every factual number used in prose is represented by an `EvidencePoint` and referenced by ID.
- Every figure has at least one `SourceReference`, an as-of timestamp, timeframe, data-quality state, caption, observation, interpretation, confirmation condition, and risk condition.
- Claims reference supporting evidence and optional counter-evidence.
- Deterministic writers may describe coincidence, consistency, confirmation, divergence, and conditions. They may not invent causality, events, probabilities, analogues, citations, or targets.
- Stale or partial security data cannot produce an actionable classification.
- Numerical scenario probabilities are allowed only when the frozen probability engine identifies a validated model. Otherwise scenarios use qualitative likelihood labels.
- Previous-report comparisons are emitted only when a prior immutable report exists and compatible metrics have aligned dates.
- Unsupported data produces a compact limitation, never a synthetic series or empty figure.

## ReportDocument contract

`ReportDocument` carries identity, session type, market/generation/cutoff timestamps, thesis, ordered sections, evidence registry, claim registry, figure registry, source registry, scenarios, security research, monitoring conditions, limitations, page estimate, figure count, word count, completeness, and source status.

Sections contain ordered content blocks referencing claims, figures, tables, scenarios, security items, and monitoring conditions. Content text is authoritative and shared. Renderer-specific layout is intentionally excluded.

## Figure contract

All charts use a light background, restrained navy/charcoal hierarchy, colorblind-safe positive/risk accents, visible units, and consistent scales for comparable panels. Core charts are full width where practical. Price figures include volume when available; moving averages and levels appear only with adequate observations.

The canonical caption order is:

1. Figure number, title, timeframe, and as-of date
2. Observation
3. Interpretation
4. Confirmation
5. Risk
6. Source IDs and transformation method

## Session behavior

- Pre-market: previous completed session evidence, levels, supported overnight context, sourced events only.
- Intraday: explicitly incomplete; no completed-session claims.
- After close: completed daily breadth, leadership, risk, and price evidence.
- Weekend/holiday: market date remains the last completed session; library grouping uses generation date; weekly structure receives more weight.

## Compatibility and storage

New reports use `daily-report-pdf-v6` and `daily-report-v22`. The report schema adds optional serialized document and frozen-OHLCV fields so historical V5 JSON remains valid. Existing stored V5 PDF blobs are never regenerated or overwritten. The PDF endpoint dispatches by stored format when regeneration is required.

## Validation

Validation covers source integrity, numerical grounding, missing/stale behavior, section omission, previous-report behavior, claim deduplication, figure metadata/series, V5/V6 preview dispatch, and V5 PDF compatibility. Main sample PDFs are rendered at 180-200 DPI and reviewed through contact sheets for clipping, overlap, blank pages, chart size, caption attachment, hierarchy, and whitespace.

The mandatory external benchmark comparison and final Stage 5.7 disposition are recorded in `docs/report-v6-benchmark-review.md`.
