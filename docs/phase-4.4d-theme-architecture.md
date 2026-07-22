# Phase 4.4D Theme Architecture

## Governance and storage

`app/themes` owns immutable versioned definitions and members. `ThemeDefinitionService.import_reviewed` requires human review metadata, inclusion reasons, unique active members, correct equal weights, source references, and an active reviewed definition. `app/theme_snapshots` owns immutable snapshot payloads plus atomic latest and last-known-good pointers.

Theme IDs are canonical lowercase `snake_case` in package metadata, SQLite records, snapshots, API responses, and frontend models. Kebab-case values are accepted only at explicit command/query boundaries and normalize immediately; filenames remain kebab-case. The full mapping is recorded in `docs/phase-4.4d-governance-tooling.md`.

`import_theme_security_master.py` is the separate reviewed gate for constituents outside the existing S&P 100 security master. It requires a sector, provider history symbol, reviewer, review date, source URL, and retrieval date; it changes no index-universe membership.

## Data path

Reviewed active definition and members → durable `daily_price_bars` → equal-weight `theme_basket_bars` → Theme performance, breadth, participation, concentration, overlap, scores, and canonical rotation series → immutable ThemeSnapshot → snapshot-backed APIs and consumers.

No screen fetches constituents, history, or builds a basket. The background Theme task returns `skipped` with `human_review_required` before invoking the builder when no reviewed definition exists; once eligible, it only reads durable history and is deduplicated by the existing refresh coordinator.

Before review, `/market/themes/status` reports reference-package and security-master readiness while `/market/themes/snapshot/latest` returns HTTP 200 with the explicit unavailable payload. The frontend calls the status endpoint first and presents the same review gate for Theme Heatmap, Rotation, and Alerts; it does not request a ThemeSnapshot before the status is `live`.

## Methodology

Basket sessions are date-aligned, require the current and immediately prior observed shared session for each included member, exclude unavailable members from that session’s equal-weight denominator, and publish only at the configured coverage threshold. No price interpolation, future membership, mock substitution, or frontend calculation is used.

Participation combines positive 21-session member return participation (60%) and positive absolute contribution share (40%); it is not EMA50 breadth. Concentration uses absolute contribution shares, top-one/top-three shares, and HHI. Overlap reports common members, Jaccard overlap, weighted overlap, and a warning classification.

## Limitations

Historical series use the current reviewed basket unless a reviewed historical membership version is available. Proposed definitions are unavailable in strict live mode. A failed build preserves the latest valid snapshot.
