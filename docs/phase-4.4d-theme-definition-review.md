# Phase 4.4D Theme Definition Review

## Decision status

All six v1 packages are **proposed**. None is reviewed, active, imported, seeded, or eligible for a live ThemeSnapshot. The importer rejects `--apply` until a human supplies review metadata for both the definition and every active member.

## Locked methodology

- Equal-weight current-member basket, recalculated from adjusted daily Polygon history.
- Primary benchmark: `SPY`; secondary benchmark only where documented in a reviewed definition.
- Complete coverage: 90% or higher; partial: 75% to under 90%; below 75% is unavailable.
- Historical results use the current reviewed v1 basket and disclose the survivorship/current-basket limitation.
- Overlap is calculated and disclosed; it is never independent confirmation.

## Proposed packages

| Theme | Package | Proposed members | Expected overlap | Membership confidence | Review status |
| --- | --- | --- | --- | --- | --- |
| Memory & Storage | `memory_storage` (`memory-storage-v1.md`) | MU, WDC, STX, SNDK | AI Infrastructure, Semiconductors if future changes add shared chip names | Needs human verification of SNDK mapping | Proposed |
| Cybersecurity | `cybersecurity` (`cybersecurity-v1.md`) | PANW, CRWD, FTNT, ZS | Low expected overlap with current six | Confirm pure-play versus platform scope | Proposed |
| AI Infrastructure | `ai_infrastructure` (`ai-infrastructure-v1.md`) | NVDA, AVGO, ANET, DELL, SMCI | High expected overlap with Semiconductors and Cloud & Data Centers | Confirm systems versus chip scope | Proposed |
| Semiconductors | `semiconductors` (`semiconductors-v1.md`) | NVDA, AVGO, AMD, QCOM, TXN | High expected overlap with AI Infrastructure | Confirm analog/embedded inclusion | Proposed |
| Cloud & Data Centers | `cloud_data_centers` (`cloud-data-centers-v1.md`) | MSFT, AMZN, GOOGL, ORCL, EQIX | Expected overlap with AI Infrastructure | Confirm cloud platforms plus data-center infrastructure mix | Proposed |
| Defense & Aerospace | `defense_aerospace` (`defense-aerospace-v1.md`) | LMT, NOC, RTX, GD, LHX | Sector overlap with Industrials | Confirm commercial aerospace treatment | Proposed |

## Per-member evidence

Each CSV in `backend/data/reference/themes/` records ticker, company, role, equal weight, written inclusion reason, official-company source URL, retrieval date (`2026-07-19`), and `Human review required`. These sources are maintainable reference inputs, not automatic approval.

## Required human decisions

1. Name the reviewer and review date for each definition and member.
2. Confirm or edit every inclusion reason and constituent role.
3. Resolve `SNDK` security-master and provider-symbol mapping before the Memory & Storage pilot.
4. Resolve whether AI Infrastructure / Cloud & Data Centers retain cross-sector scope and no secondary benchmark.
5. Confirm each proposed overlap is acceptable and disclosed.
6. Change each approved package to `reviewed`, then separately activate a version only through the importer.

No Codex-generated package is marked reviewed by this repository.
