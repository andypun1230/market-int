# Phase 4.4D Live Rollout Gate

## Current status

Architecture is ready for deterministic validation. Live Theme Intelligence is **not activated** because no ThemeDefinition package has received human review and separate activation approval. Proposed packages in `backend/data/reference/themes/` are reference inputs only and cannot be applied by the import command. Theme IDs are canonical lowercase `snake_case`; kebab-case package filenames and legacy command aliases remain boundary-only compatibility forms.

## Required approval sequence

1. Review every constituent, role, inclusion/exclusion reason, source reference, date, provider symbol, and duplicate class across the six proposed packages.
2. Add reviewed security-master records for any member outside the current S&P 100 master, including provider mappings and share-class decisions.
3. Complete `docs/phase-4.4d-theme-definition-review.md` with a reviewer identity and date for each definition and member.
4. Change only the approved package frontmatter to `status: active`, preserving its immutable version and effective date.
5. Run an import dry run, then apply the approved package. The importer rejects missing review metadata, unsupported policy changes, and missing security-master mappings.
6. Seed only approved members with `seed_theme_histories.py --strict-live --resume`; use the durable Polygon adjusted-bar store and checkpoints.
7. Build one ThemeSnapshot and confirm warm API reads make no constituent provider calls before enabling any user-facing live claim.

## Operational commands

```sh
cd backend
python3 scripts/import_theme_security_master.py --file /path/to/reviewed-theme-security-master.csv --dry-run
python3 scripts/import_theme_security_master.py --file /path/to/reviewed-theme-security-master.csv --apply
python3 scripts/import_theme_definitions.py --theme memory_storage --definition-file data/reference/themes/memory-storage-v1.md --members-file data/reference/themes/memory-storage-v1.csv --dry-run
python3 scripts/seed_theme_histories.py --all-themes --resume --strict-live --lookback-calendar-days 450 --concurrency 2
python3 scripts/build_theme_snapshot.py --json-output /tmp/theme-snapshot.json
python3 scripts/validate_phase_4_4d.py --live --pilot --warm --restart --report --copilot-context --json-output ../docs/phase-4.4d-live-validation.json --markdown-output ../docs/phase-4.4d-live-validation.md
```

The final command reports a condition, rather than a false live pass, while the review gate remains closed. The seed and build commands mutate durable data and must not be run before review and security-master validation.

## Native QA after approval

- Open Sectors -> Themes and confirm the snapshot date, source state, and theme rank match `/market/themes/snapshot/latest`.
- Switch Heatmap, Rotation, and Alerts. Confirm 1W, 1M, and 3M tails are real basket history and no test-data badge appears.
- Open a theme detail and verify definition version, coverage, participation, concentration, and the historical current-basket disclosure.
- Verify Home, Decision Dashboard, Report, and Copilot reference the same `theme_snapshot_id`; static strategy preferences remain labelled separately.
