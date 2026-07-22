# Phase 4.4D-0 Governance Tooling

## Identifier audit before cleanup

| Display name | Persisted ID before cleanup | Accepted CLI aliases before cleanup | Filename slug | API/frontend ID before cleanup |
| --- | --- | --- | --- | --- |
| Memory & Storage | `memory-storage` | exact raw value only | `memory-storage` | raw snapshot value |
| Cybersecurity | `cybersecurity` | exact raw value only | `cybersecurity` | raw snapshot value |
| AI Infrastructure | `ai-infrastructure` | exact raw value only | `ai-infrastructure` | raw snapshot value |
| Semiconductors | `semiconductors` | exact raw value only | `semiconductors` | raw snapshot value |
| Cloud & Data Centers | `cloud-data-centers` | exact raw value only | `cloud-data-centers` | raw snapshot value |
| Defense & Aerospace | `defense-aerospace` | exact raw value only | `defense-aerospace` | raw snapshot value |

The mismatch between `memory_storage` and `memory-storage` was an input-boundary defect, not a review decision. No definition was approved, imported, activated, seeded, or published while correcting it.

## Canonical policy

- Persisted, API, snapshot, and frontend IDs are lowercase snake_case.
- Supported boundary aliases are the canonical value and its kebab-case legacy form only.
- Filenames remain kebab-case and never determine a persisted ID.
- Unknown aliases are rejected as `unknown_theme_id`; display names and fuzzy matches are not aliases.

| Canonical ID | Accepted alias | Filename slug | Display name |
| --- | --- | --- | --- |
| `memory_storage` | `memory-storage` | `memory-storage` | Memory & Storage |
| `cybersecurity` | none | `cybersecurity` | Cybersecurity |
| `ai_infrastructure` | `ai-infrastructure` | `ai-infrastructure` | AI Infrastructure |
| `semiconductors` | none | `semiconductors` | Semiconductors |
| `cloud_data_centers` | `cloud-data-centers` | `cloud-data-centers` | Cloud & Data Centers |
| `defense_aerospace` | `defense-aerospace` | `defense-aerospace` | Defense & Aerospace |

## Pre-review workflow

```sh
cd backend
python3 scripts/audit_theme_provenance.py --all-themes --mode all --json-output ../docs/phase-4.4d-theme-provenance.json --markdown-output ../docs/phase-4.4d-theme-provenance.md
python3 scripts/import_theme_definitions.py --theme memory_storage --definition-file data/reference/themes/memory-storage-v1.md --members-file data/reference/themes/memory-storage-v1.csv --version v1 --dry-run
curl -sS http://127.0.0.1:8000/market/themes/status | python3 -m json.tool
```

Expected pre-review status is `awaiting_review`: six proposed packages, zero reviewed/active definitions, no published snapshot, and no provider work. Before any pilot, a human must review definitions and members, resolve security-master records, separately activate a reviewed version, then perform the documented live validation.
