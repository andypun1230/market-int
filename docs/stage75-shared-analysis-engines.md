# Stage 7.5 Shared Analysis Engines

## 1. Purpose

Stage 7.5 extracts reusable, deterministic policy from the validated Stage 7
agent pipeline without changing user-facing conclusions. It also removes
duplicate computation inside stock snapshot construction. The phase does not
add an intelligence service, model call, route, screen, report section, or PDF
behavior.

The baseline is commit `218e7ea53f98df14e8d864c6cd123952ad51fe0e`.
Its release-bearing runtime suite passed 30/30 cases, the frozen reference suite
passed 165/165 cases, and all 15 registered agents were exercised.

## 2. Pre-refactor architecture

The active Copilot pipeline already used deterministic, read-only adapters, but
several cross-cutting rules lived in multiple modules:

- source-state normalization and aggregation in `copilot/sources.py`, agent
  freshness construction in `copilot/agents.py`, and bundle freshness counts in
  `copilot/collector.py`;
- constrained-state and confidence rules in reasoning, validation, and agent
  contract validation;
- evidence first-win deduplication in agents, the collector, and reasoning;
- contradiction classification in reasoning and preservation checks in
  validation;
- numeric entity/metric binding, source identity, and same-security breakout
  checks as private validator helpers.

Separately, `StockAnalysisSnapshotBuilder` rebuilt the same leaf analyses from
the same frozen input bundle as composite sections called one another.

## 3. Post-refactor architecture

The implemented flow is:

```text
durable snapshots / immutable ReportDocument
                    |
          Stage 7 agent adapters
                    |
     CopilotFreshnessAdapter + stable AgentResultV1
                    |
      collector -> reasoning -> validation -> response
          |             |            |
     freshness +   contradiction +   evidence +
     evidence       confidence        confidence
          \_____________|____________/
              shared analysis engines
```

Shared engines live under `backend/app/analysis_engines/`. They depend on no
API, UI, report renderer, or orchestration module. Copilot-specific mapping is
in `backend/app/copilot/engine_adapters.py`; the stable Stage 7 contracts remain
in `backend/app/copilot/contracts.py`.

Stock snapshot construction now uses a per-build computation DAG in
`backend/app/stock_snapshots/builder.py`. It is a domain-owned optimization,
not a new intelligence service or a generic market-analysis formula.

## 4. Extracted engines

### Freshness and Availability Engine

Version: `freshness-availability-v1`.

The typed input records source state, provider status, generation and observation
timestamps, market date, expiry, expected update frequency, stale threshold,
completeness, provider, session context, test/fallback/mixed flags, warnings, and
an injectable clock. The output records normalized state, availability, age,
completeness, lineage fields, fallback/mixed disclosure, warnings, and a
confidence-cap recommendation.

It preserves the Stage 7 rules that stale data cannot be current, unavailable
data cannot become neutral evidence, fallback/test/mixed states remain labelled,
and constrained states cap confidence.

### Evidence Validation Engine

Version: `evidence-validation-v1`.

The engine provides stable first-win evidence identity with collision reporting,
entity/metric/unit/period claim binding, suitability/quarantine checks, source
identity and timestamp validation, semantic-claim compatibility, and
same-security price/trigger/volume breakout validation. Copilot validation still
owns policy wording and fail-closed response quarantine; the engine owns the
structured facts used by those checks.

### Contradiction Engine

Version: `contradiction-preservation-v1`.

The engine classifies structured findings as supporting, neutral, or opposing,
retains explicit claim-level contradiction links, supports the existing
watchlist caution mapping, and validates that contradiction truncation is
disclosed. Missing evidence remains separate. The engine never forces consensus.

### Confidence Adjustment Engine

Version: `confidence-adjustment-v1`.

The engine returns a confidence label, maximum allowed label, constrained flag,
and an explicit list of applied contributions. It preserves the existing Stage 7
rule set: navigation and bounded education may be high confidence; constrained,
missing, fallback, or absent factual evidence is limited; three or more current
evidence items may be moderate. Contradictions are disclosed as a contribution,
not hidden inside an unexplained aggregate score.

## 5. Domain-owned computation optimization

`_StockSectionComputation` memoizes both values and failures for one immutable
`StockDetailInputBundle`. Thirteen stock snapshot analyses are attempted no more
than once per build. Composite section helpers receive already-computed typed
dependencies. Existing public builder functions remain callable and retain their
serialized payloads.

This removes the previously observed repeated support/resistance, trend, volume,
relative-strength, risk, pattern, rating, and signal calculations without
changing their formulas or source selection. Source acquisition is attempted
fewer times where a repeated calculator previously reacquired the same input.

## 6. Deferred candidates

The detailed evidence is in `docs/stage75-shared-engine-audit.md`.

- Trend: similar names hide swing-trend, moving-average trend, regime trend, and
  breadth-specific EMA seed policies. Standardize contracts before extraction.
- Relative strength: positional and independently-ended series coexist with a
  stronger date-aligned implementation. Correcting them would change results and
  requires a formula/version migration.
- Volume: current-session inclusion and baseline semantics differ by surface.
  A shared engine requires an explicit inclusion policy and golden parity tests.
- Support/resistance: snapshot and legacy service cores are similar, but source
  acquisition, rounding, and risk-level precedence differ. Keep domain-owned
  until a pure input boundary is standardized.
- Pattern: existing stock patterns include deterministic mock fixtures and
  ambient volume work. Purity and provenance must be fixed before reuse.
- Risk metrics: stock trade-risk arithmetic, market risk scores, and report
  invalidation risk are distinct domains; level precedence also differs.
- Time-series alignment: a reusable aligner is justified, but adopting it in
  stock/sector/theme RS would intentionally correct behavior. It is deferred to
  a versioned behavioral phase.
- Per-entity data-completeness requirements: the current contract carries entity
  lists but collection enforces category counts. Adding minimum-per-entity and
  metric IDs is a contract extension, not a behavior-neutral extraction.

## 7. Engine contracts and assumptions

All four engines use frozen dataclass contracts, publish a version identifier,
and return structured values rather than answer prose. They are side-effect free
except that freshness uses the current UTC clock when an adapter does not inject
`now`, matching Stage 7 behavior. Tests inject `now` for deterministic boundary
coverage.

No engine may import:

- FastAPI or endpoint code;
- frontend code or destination rendering;
- report/PDF rendering;
- Copilot orchestration or session state;
- a provider client or model client.

## 8. Agent adapters

The 15 registered agents remain domain adapters. They continue to select source
fields, evidence categories, conditions, limitations, and deep links.

`CopilotFreshnessAdapter` maps the shared freshness result to
`CopilotFreshnessV1`. `CopilotEvidenceValidationAdapter` maps stable evidence
identity to `CopilotEvidenceV1`. Reasoning and validation consume the
contradiction and confidence contracts after collection. No agent imports an
engine implementation detail directly.

The exact direct and downstream dependency graph is documented in
`docs/stage75-engine-dependency-map.md` and
`backend/app/analysis_engines/engine_manifest.json`.

## 9. Testing strategy

Coverage includes:

- engine unit, boundary, missing, stale, malformed, deterministic, and
  fail-closed tests in `test_stage75_shared_engines.py`;
- Copilot adapter tests in `test_stage75_copilot_engine_adapters.py`;
- stock computation exactly-once, semantic-payload parity, and failure-locality
  tests in `test_stage7_5_stock_snapshot_dag.py`;
- semantic-comparator action-parameter drift coverage in
  `test_stage75_semantic_comparison.py`;
- existing Stage 7 agent-contract, claim-validation, runtime, routing, tracing,
  failure-injection, and Institutional Copilot tests;
- 30 case-by-case pre/post runtime semantic comparisons in
  `artifacts/stage75-semantic-equivalence.json`;
- the 165-case frozen semantic corpus and the 30 checked-in executable Stage 7
  artifacts;
- the full backend suite and all existing frontend type, lint, data-contract,
  transport, reducer, destination, and route-export checks.

Semantic comparison rejects changes to conclusion class, evidence identity,
claims, contradictions, confidence, freshness, missing evidence, selected agents,
deep links, exact action IDs/destinations/parameters, validation status, failure
categories, and component scores. It ignores only timestamps, measured latency,
agent duration, and internal paths.

## 10. Performance comparison

The isolated baseline-commit run and current run both use the release-bearing
hermetic evaluator with 14 performance cases:

| Metric | Before | After | Change |
|---|---:|---:|---:|
| Mean | 2.840 ms | 3.058 ms | +7.68% |
| p50 | 2.483 ms | 2.569 ms | +3.44% |
| p95 | 5.807 ms | 5.892 ms | +1.47% |
| p99 | 7.037 ms | 6.884 ms | -2.18% |
| Max | 7.345 ms | 7.132 ms | -2.90% |

The p95 result is within the 15% guardrail. Model calls and network calls remain
zero. Per-engine microbenchmarks, memory peak, and fresh-process import timing
are in `artifacts/stage75-engine-performance.json`; per-agent latency is in the
pre/post runtime evaluation artifacts.

## 11. Known limitations

- Runtime evaluation is hermetic and does not measure live-provider latency.
- Microbenchmarks are process- and machine-sensitive and are diagnostic, not a
  release threshold.
- Import timing includes interpreter startup noise.
- The stock DAG removes repeated computation but does not yet turn every stock
  formula into a reusable cross-domain engine.
- Intent-level per-entity evidence completeness remains a documented contract
  refinement rather than a silent Stage 7.5 behavior change.

## 12. Rules for future engines

Extract only when the calculation is genuinely shared, the semantic contract is
equivalent, or a shared validator is required for safety. A new engine must have
typed input/output, explicit thresholds, source/freshness assumptions, a version,
direct tests, adapter tests, and frozen semantic equivalence. Domain conclusions,
deep links, and presentation wording remain outside engines.

Behavior-changing corrections require a formula version bump, targeted defect
test, explicit expected-output migration, and a separate release decision.

## 13. Adding a new consumer

1. Import the public engine contract from its package `__init__.py`.
2. Add a domain adapter that maps durable typed data into the engine input.
3. Map the result into the consumer's existing contract without exposing engine
   internals or changing public fields.
4. Add engine boundary tests, adapter tests, and affected Stage 7 golden cases.
5. Add the real dependency and version to `engine_manifest.json`.
6. Run the full Stage 7.5 validation target and inspect semantic/performance
   artifacts before merging.

## 14. Validation commands

From the repository root:

```bash
make validate-stage75 PYTHON=venv/bin/python
```

Focused commands:

```bash
cd backend
venv/bin/python -m unittest \
  tests.test_stage75_shared_engines \
  tests.test_stage75_copilot_engine_adapters \
  tests.test_stage7_5_stock_snapshot_dag \
  tests.test_stage75_semantic_comparison
venv/bin/python scripts/augment_stage75_runtime_actions.py \
  --artifact ../artifacts/stage75-post-refactor-runtime-evaluation.json
venv/bin/python scripts/compare_stage75_semantics.py \
  --before ../artifacts/stage75-pre-refactor-runtime-evaluation.json \
  --after ../artifacts/stage75-post-refactor-runtime-evaluation.json \
  --output ../artifacts/stage75-semantic-equivalence.json
venv/bin/python scripts/benchmark_stage75_engines.py \
  --output ../artifacts/stage75-engine-performance.json
```
