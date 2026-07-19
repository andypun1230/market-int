# Phase 4.4C Validation

`backend/scripts/validate_phase_4_4c.py` verifies the canonical taxonomy, aliases, deterministic snapshot regression suite, live provenance/readiness, restart persistence, and warm reads with Polygon history patched to fail.

The validator reports partial coverage instead of promoting it to complete. Snapshot history is limited to actually published daily snapshots; it never backfills a fabricated rotation timeline.
