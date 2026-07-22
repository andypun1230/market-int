# Stage 7.5 shared analysis engines validation report

## 1. Overall result

**PASS WITH CONDITIONS**

Stage 7.5 extracted four meaningful, versioned, deterministic shared engines,
removed duplicate cross-cutting policy code, and replaced repeated stock snapshot
calculation with a per-build dependency DAG. The release-bearing Stage 7 runtime
suite passed 30/30, the frozen semantic corpus passed 165/165, all 15 agents were
exercised, all seven failure injections remained safe, and the pre/post semantic
comparison passed 30/30 with no changed meaning.

The result remains PASS WITH CONDITIONS because live-provider behavior and
latency are outside the hermetic evaluation, the 165-case corpus is explicitly
non-release-bearing, and the existing native simulator checks remain manual.

| Gate | Result |
|---|---:|
| Backend unit discovery | 414/414 passed |
| Stage 7-focused discovery | 91/91 passed |
| Institutional Copilot tests | 39/39 passed |
| Release-bearing runtime scenarios | 30/30 passed |
| Frozen semantic cases | 165/165 passed, non-release |
| Pre/post semantic equivalence | 30/30 passed |
| Registered agents exercised | 15/15 |
| Failure injections | 7/7 safe |
| Frontend checks | Passed |
| Expo static web export | 25 routes passed |
| Release blockers | 0 |

## 2. Repository revisions

- Baseline commit: `218e7ea53f98df14e8d864c6cd123952ad51fe0e`
- Baseline working tree: clean before the refactor.
- Final commit: not created; the validated target is the current working tree on
  top of the baseline commit.
- The Stage 7 target now accepts overridable result paths. Stage 7.5 routes its
  runtime, reference and human-review outputs to Stage 7.5 artifacts, so the
  canonical historical Stage 7 artifacts are not rewritten by reproduction.

## 3. Engines extracted

| Engine | Version | Shared responsibilities |
|---|---|---|
| Freshness and Availability | `freshness-availability-v1` | Source-state normalization, timestamp parsing, expiry/staleness, completeness, fallback/mixed disclosure, aggregation and confidence-cap recommendation |
| Evidence Validation | `evidence-validation-v1` | Stable deduplication, collision reporting, entity/metric/unit/period binding, suitability/quarantine, source identity/timestamps, semantic compatibility and same-security breakout validation |
| Contradiction Preservation | `contradiction-preservation-v1` | Supporting/neutral/opposing classification and fail-closed preservation or disclosed truncation of contradictory evidence |
| Confidence Adjustment | `confidence-adjustment-v1` | Explicit evidence-count and freshness rule contributions/caps without a hidden aggregate score |

Every engine has frozen typed input/output contracts, an explicit version,
deterministic implementation, direct unit tests and a presentation-independent
structured result. The package does not depend on UI, report rendering, agent
orchestration, model calls or network access.

## 4. Agent migration

All 15 registered agents remain available: market, index, breadth, leadership,
sector, theme, macro, risk, stock, watchlist, report, research, navigation,
educational and portfolio.

Freshness is used through the explicit Copilot adapter by market, index, breadth,
leadership, sector, theme, macro, risk, stock, report and research. Watchlist,
navigation, educational and portfolio retain their contract-specific cached,
live or unavailable construction and pass through the shared downstream contract
validator.

Evidence validation applies to the normal result boundary and downstream
contract pipeline for all 15 agents. Contradiction preservation and confidence
adjustment apply downstream to all 15 by design: agents retain domain evidence
selection and interpretation while collection, reasoning and response validation
share the cross-cutting policy. This avoids turning agents into aliases.

The precise per-agent, per-engine status is in
`backend/app/analysis_engines/engine_manifest.json`; the readable architecture
map is `docs/stage75-engine-dependency-map.md`.

## 5. Duplicate implementations and computation removed

- Freshness normalization, expiry, aggregation and constrained-state handling
  now delegate to one shared implementation.
- Evidence identity/deduplication, claim binding, source validation, semantic
  compatibility and confirmed-breakout validation now share one implementation.
- Contradiction polarity partitioning and response preservation rules now share
  one implementation.
- Confidence constraints at agent-contract, reasoning and response-validation
  boundaries now use explicit shared rule contributions.
- Stock snapshot construction now memoizes values and failures in a per-build
  DAG. Previously, one full build could calculate support/resistance 13 times,
  relative strength nine times, volume eight times, trend seven times, risk six
  times and patterns three times. Each is now attempted at most once.

The stock formulas and public standalone builder signatures were retained. A
payload-parity test verifies that the DAG has the same section semantics, and a
failure-locality test verifies that a failed dependency is not retried or allowed
to invalidate unrelated sections.

## 6. Files created

Architecture and integration:

- `backend/app/analysis_engines/__init__.py`
- `backend/app/analysis_engines/common/__init__.py`
- `backend/app/analysis_engines/freshness/__init__.py`
- `backend/app/analysis_engines/freshness/engine.py`
- `backend/app/analysis_engines/evidence_validation/__init__.py`
- `backend/app/analysis_engines/evidence_validation/engine.py`
- `backend/app/analysis_engines/contradiction/__init__.py`
- `backend/app/analysis_engines/contradiction/engine.py`
- `backend/app/analysis_engines/confidence/__init__.py`
- `backend/app/analysis_engines/confidence/engine.py`
- `backend/app/analysis_engines/engine_manifest.json`
- `backend/app/copilot/engine_adapters.py`

Tests and validation tooling:

- `backend/tests/test_stage75_shared_engines.py`
- `backend/tests/test_stage75_copilot_engine_adapters.py`
- `backend/tests/test_stage7_5_stock_snapshot_dag.py`
- `backend/tests/test_stage75_semantic_comparison.py`
- `backend/scripts/compare_stage75_semantics.py`
- `backend/scripts/augment_stage75_runtime_actions.py`
- `backend/scripts/benchmark_stage75_engines.py`

Documentation and evidence:

- `docs/stage75-shared-engine-audit.md`
- `docs/stage75-engine-dependency-map.md`
- `docs/stage75-shared-analysis-engines.md`
- `docs/validation/stage75-shared-engines-validation-report.md`
- `artifacts/stage75-pre-refactor-validation.json`
- `artifacts/stage75-pre-refactor-runtime-evaluation.json`
- `artifacts/stage75-post-refactor-runtime-evaluation.json`
- `artifacts/stage75-post-refactor-reference-evaluation.json`
- `artifacts/stage75-post-refactor-human-review.json`
- `artifacts/stage75-semantic-equivalence.json`
- `artifacts/stage75-engine-performance.json`
- `artifacts/stage75-shared-engines-validation.json`

## 7. Files modified

- `Makefile`
- `backend/app/copilot/agent_contracts.py`
- `backend/app/copilot/agents.py`
- `backend/app/copilot/collector.py`
- `backend/app/copilot/reasoning.py`
- `backend/app/copilot/sources.py`
- `backend/app/copilot/validation.py`
- `backend/app/stock_snapshots/builder.py`
- `docs/stage7-agent-inventory.md`

No endpoint, public route, public response field, screen, report layout or PDF
layout was changed.

## 8. Tests added

Nineteen tests were added:

- 12 shared-engine tests covering typed contracts, versions, determinism,
  boundaries, malformed/missing/stale input, source timestamps, quarantine,
  entity/metric/unit/period binding, same-security breakout evidence,
  contradictions and explicit confidence contributions;
- three adapter tests covering Copilot freshness shape, compatibility delegation
  and stable first-win evidence identity;
- three stock DAG tests covering exactly-once calculation, semantic payload
  parity and memoized failure locality;
- one semantic-comparator regression test proving that exact action-parameter
  drift fails even though latency is intentionally ignored.

## 9. Full validation results

The final `make validate-stage75 PYTHON=venv/bin/python` run passed:

- Python compilation;
- 414/414 backend tests;
- the checked-in Stage 7 executable-artifact currentness check;
- 30/30 release-bearing runtime scenarios with zero blockers;
- 165/165 frozen reference cases with every component score at 1.000;
- 7/7 observed failure injections;
- all 15 registered agents;
- TypeScript, ESLint and the 28-screen data/UI manifest;
- Copilot contract, transport, reducer and destination suites;
- Expo web export for 25 static routes;
- the 30-case semantic comparator;
- the shared-engine performance benchmark.

Runtime routing remained exact:

- intent accuracy: 100%;
- required-agent recall: 100%;
- unnecessary-agent rate: 0%;
- invalid-route rate: 0%;
- fallback rate: 0%;
- average selected agents: 1.316.

Contract correctness, contradiction handling, cost efficiency, deep-link
accuracy, evidence grounding, factual correctness, format compliance, freshness
honesty, latency, routing relevance and safety each scored 1.000.

## 10. Semantic equivalence

**PASS — 30/30 equivalent, zero mismatches.**

The comparator ran the full pre-refactor baseline commit and final working-tree
runtime suites case by case. It rejects changes to conclusion class, evidence
identity, claims, contradictions, confidence, freshness, missing evidence,
selected agents, deep links, exact action IDs/destinations/parameter maps,
validation state, failure categories and component scores. It ignores only
generated timestamps, measured duration and internal module paths. Exact action
payloads were captured from all 30 hermetic scenarios on both revisions.

The frozen 165-case semantic corpus also passed 165/165. It remains
non-release-bearing; the 30-case runtime suite is the release-bearing evidence.

## 11. Performance comparison

The isolated baseline commit and final working tree were compared on the same 14
hermetic performance cases:

| Metric | Before | After | Change |
|---|---:|---:|---:|
| Mean | 2.840 ms | 3.058 ms | +7.68% |
| p50 | 2.483 ms | 2.569 ms | +3.44% |
| p95 | 5.807 ms | 5.892 ms | +1.47% |
| p99 | 7.037 ms | 6.884 ms | -2.18% |
| Maximum | 7.345 ms | 7.132 ms | -2.90% |

The p95 change is inside the 15% guardrail and is not a material unexplained
regression. The table uses the isolated, matched pre/post artifacts so that both
measurements have the same fixture set and execution boundary.

Per-agent timings were also compared:

| Agent | Calls | p50 before | p50 after | p95 before | p95 after |
|---|---:|---:|---:|---:|---:|
| Breadth | 5 | 0.332 | 0.358 | 0.390 | 0.455 |
| Educational | 1 | 0.017 | 0.020 | 0.017 | 0.020 |
| Index | 1 | 0.441 | 0.497 | 0.441 | 0.497 |
| Leadership | 1 | 0.314 | 0.346 | 0.314 | 0.346 |
| Macro | 1 | 0.421 | 0.426 | 0.421 | 0.426 |
| Market | 6 | 0.137 | 0.150 | 0.419 | 0.443 |
| Navigation | 1 | 0.017 | 0.022 | 0.017 | 0.022 |
| Portfolio | 1 | 0.025 | 0.028 | 0.025 | 0.028 |
| Report | 4 | 0.679 | 0.773 | 0.717 | 1.177 |
| Research | 1 | 0.502 | 0.532 | 0.502 | 0.532 |
| Risk | 5 | 0.502 | 0.567 | 0.576 | 0.669 |
| Sector | 1 | 0.184 | 0.199 | 0.184 | 0.199 |
| Stock | 9 | 0.697 | 0.713 | 1.989 | 1.712 |
| Theme | 1 | 0.164 | 0.188 | 0.164 | 0.188 |
| Watchlist | 2 | 0.159 | 0.167 | 0.179 | 0.201 |

These are small-sample, mostly sub-millisecond adapter measurements. Report p95
increased by 0.460 ms over four calls while stock p95 decreased by 0.276 ms;
total-request p95 is the release guardrail and changed by only +1.47%.

At 5,000 calls per operation, engine p95 values were 14.208 microseconds for
confidence, 35.625 for contradiction, 51.667 for breakout validation, 105.083
for claim binding and 28.667 for freshness. Benchmark peak memory was 228,112
bytes. Fresh-process engine import added a measured mean 36.818 ms, but that diagnostic
includes interpreter startup and is not on the already-running request path.

Model calls and hermetic network calls remained zero.

## 12. API and frontend compatibility

- Existing backend endpoints and public fields are unchanged.
- Deep-link validation and destinations passed unchanged.
- Loading, error and unavailable contracts passed their existing suites.
- TypeScript, lint, data/UI, Copilot contracts, transport, reducer and
  destinations passed.
- Expo produced all 25 static web routes.
- No analysis-engine screen or production diagnostic navigation was added.
- Report and PDF design were not changed.

## 13. Defects found and fixed

1. A pre-existing stock snapshot inefficiency recalculated shared section inputs
   through nested composite builders. A memoized dependency DAG now computes each
   section once and preserves standalone APIs and payload semantics.
2. The initial evidence-engine implementation eagerly calculated canonical
   fingerprints and produced an unacceptable noisy p95 increase. Fingerprints
   are now calculated only for actual conflicting identities; final p95 is
   +1.47% versus the isolated baseline.
3. Extraction exposed a fail-closed validation gap for malformed source
   timestamps/market dates and factual factors citing missing-evidence records.
   The response validator now rejects those invalid paths. The shared-engine
   tests cover timestamp/date rejection and quarantine, and all baseline fixture
   meanings remain unchanged.
4. The first Stage 7.5 reproduction target wrote current results to canonical
   Stage 7 artifact paths. Stage 7 output paths are now overridable, and the
   Stage 7.5 target writes only Stage 7.5-specific runtime, reference and review
   artifacts.
5. The first semantic comparator checked destinations but not exact action
   parameter maps. A dedicated hermetic action-capture step now records and
   compares complete action payloads for all 30 cases, with a failing regression
   test for parameter drift.

No validated conclusion changed, and none of these fixes introduced new
intelligence behavior.

## 14. Deferred extractions

| Candidate | Reason deferred |
|---|---|
| Trend | Current calculation and output are stock-domain-specific; no second equivalent shared contract is proven |
| Relative strength | Benchmark selection, weighting, alignment and stock model outputs have observable domain semantics |
| Volume | Current functions and stock adapters lack a versioned cross-domain contract |
| Pattern | Input is not yet a frozen shared-history contract; no new pattern behavior was authorized |
| Support/resistance | Existing level generation is stock-domain logic with observable output semantics |
| Risk metrics | Current risk composition is inside the stock DAG and has no reusable versioned contract |
| Time-series alignment | Existing date intersection, positional and independently-ended comparisons are not equivalent; unification would change behavior |
| Data completeness | Thresholds remain domain-specific and require an explicit per-entity/per-metric contract extension |

These are recorded as deferred, not implemented, in the machine manifest. Market
regime, breadth participation, sector rotation, theme research priority,
watchlist priority, report retrieval and navigation resolution remain correctly
owned by their domains.

## 15. Remaining conditions

- Native simulator visual rendering remains a manual Stage 7 check.
- Rapid tab-switch cancellation remains a manual Stage 7 check.
- Native screenshot capture on UI failures remains a manual Stage 7 check.
- Live-provider behavior and latency were not exercised by the hermetic suite.
- Fresh-process import measurements are diagnostic and machine-sensitive.
- Deferred formula engines need separately versioned behavioral migrations.

There are no known automated-test failures or release blockers.

## 16. Exact reproduction commands

From the repository root:

```bash
cd /Users/andypun/Downloads/market-intelligence-app
make validate-stage75 PYTHON=venv/bin/python
```

Focused engine and DAG tests:

```bash
cd /Users/andypun/Downloads/market-intelligence-app/backend
venv/bin/python -m unittest \
  tests.test_stage75_shared_engines \
  tests.test_stage75_copilot_engine_adapters \
  tests.test_stage7_5_stock_snapshot_dag \
  tests.test_stage75_semantic_comparison
```

Rebuild the semantic and performance artifacts:

```bash
cd /Users/andypun/Downloads/market-intelligence-app/backend
venv/bin/python scripts/augment_stage75_runtime_actions.py \
  --artifact ../artifacts/stage75-post-refactor-runtime-evaluation.json
venv/bin/python scripts/compare_stage75_semantics.py \
  --before ../artifacts/stage75-pre-refactor-runtime-evaluation.json \
  --after ../artifacts/stage75-post-refactor-runtime-evaluation.json \
  --output ../artifacts/stage75-semantic-equivalence.json
venv/bin/python scripts/benchmark_stage75_engines.py \
  --output ../artifacts/stage75-engine-performance.json
```

## 17. Final scope confirmations

- All 15 Stage 7 agents remain registered, available and exercised.
- No future-stage agent or intelligence service was added.
- No report or PDF design changed.
- No model-assisted behavior or model call was introduced.
- No public API route or field was silently renamed or removed.
- Historical Stage 7 validation results were not rewritten.

Primary human report: `docs/validation/stage75-shared-engines-validation-report.md`.

Primary machine artifact: `artifacts/stage75-shared-engines-validation.json`.
