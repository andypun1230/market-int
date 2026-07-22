# Stage 7 Institutional Copilot agent validation report

## 1. Executive result

**PASS WITH CONDITIONS**

The release-bearing, hermetic runtime suite passed 30/30 scenarios with zero release blockers. It executed the real Stage 7 classifier, planner, registry, collector, reasoning engine, response validator, action registry, fallback paths, and orchestrator. All 15 registered agents and all seven injected failure paths were exercised.

The separate 165-case frozen corpus passed 165/165, but it is explicitly marked **NON-RELEASE** because it validates frozen semantic contracts and evaluator behavior rather than executing every production pipeline boundary. The overall result remains PASS WITH CONDITIONS because live providers were intentionally excluded, the active implementation is deterministic rather than model-assisted, and documented production/data integrations remain unavailable.

| Gate | Result |
|---|---:|
| Release-bearing runtime scenarios | 30/30 passed |
| Frozen semantic/reference cases | 165/165 passed, non-release |
| Executable public-pipeline fixtures | 30/30 passed |
| Declared executable-fixture assertions | 86/86 implemented and enforced |
| Full backend unit discovery | 395/395 passed |
| Release blockers | 0 |
| Registered agents exercised | 15/15 |
| Failure injections observed | 7/7 |
| Frontend contract/release checks | Passed |

## 2. Repository revision

- Base commit: `3b48aae2f371f88087cf4d09220198dfd3af7e03`
- Validation target: the current working tree on top of that commit.
- The working tree already contained substantial Stage 5.8, Stage 6, Stage 7, report, frontend, and generated-artifact work. No commit or staging operation was performed during this validation pass.

## 3. Validation date

22 July 2026, Asia/Hong_Kong.

## 4. Agent inventory

The active registry contains 15 deterministic, read-only adapters:

1. Market
2. Index
3. Breadth
4. Leadership
5. Sector
6. Theme
7. Macro
8. Risk
9. Stock
10. Watchlist
11. Report
12. Research
13. Navigation
14. Educational
15. Portfolio

`Portfolio` already existed as an explicit unavailable boundary; it was not added in this task. Every agent uses `copilot-agent-result-v1`, has no active prompt or model version, and is described in `docs/stage7-agent-inventory.md` and `backend/app/copilot/agent_manifest.json`.

The active `/copilot/chat` and `/copilot/chat/stream` routes do not call the repository's legacy optional OpenAI Copilot service. Active agent selection and synthesis are deterministic.

## 5. Tests executed

The final repository-native command completed successfully:

```bash
make validate-stage7 PYTHON=venv/bin/python
```

It performed compile validation, all 395 backend unit tests, the 39-file executable-artifact check, the release-bearing runtime evaluation, the 165-case reference evaluation, the 165-case human-review artifact build, TypeScript, ESLint, the 28-screen data/UI manifest check, and four named Copilot frontend suites. Two additional frontend suites and a 25-route Expo web export were also run directly and passed.

The final classification-only evaluator change was followed by a focused 7/7 runtime-evaluation rerun and machine-artifact regeneration.

Existing operator artifacts remain indexed under `output/stage-7`: 15/15 manual prompt records and 10/10 reviewed screenshots. They were preserved by the generator rather than re-authored; no frontend behavior changed in this validation pass.

## 6. Fixture counts by category

### Release-bearing runtime scenarios

| Category | Count |
|---|---:|
| Market | 3 |
| Stock | 4 |
| Watchlist | 2 |
| Report | 2 |
| Routing | 2 |
| Breadth, Leadership, Sector, Theme, Macro, Risk, Research, Navigation, Educational, Portfolio | 1 each |
| Failure injection | 7 |
| **Total** | **30** |

Runtime suite memberships are: golden 24, routing 19, performance 14, safety 8, full 30.

### Frozen semantic corpus

| Category | Count |
|---|---:|
| Market | 15 |
| Breadth | 15 |
| Leadership | 8 |
| Sector | 8 |
| Theme | 9 |
| Macro | 10 |
| Risk | 15 |
| Stock | 25 |
| Watchlist | 10 |
| Research | 10 |
| Report | 5 |
| Navigation | 10 |
| Routing | 12 |
| Synthesis | 13 |
| **Total** | **165** |

The corpus contains 101 constrained-data cases, 42 contradiction cases, and 17 declared failure-injection cases. Suite memberships are golden 165, routing 35, performance 14, safety 13, full 165.

## 7. Results by agent

All registered agents traversed the production registry and runtime contract boundary. Counts are runtime invocations in the final evaluation; p95 values are in-process hermetic adapter latency, not live-provider latency.

| Agent | Calls | p95 ms | Result |
|---|---:|---:|---|
| Market | 6 | 0.457 | Passed |
| Index | 1 | 0.486 | Passed |
| Breadth | 5 | 0.483 | Passed |
| Leadership | 1 | 0.451 | Passed |
| Sector | 1 | 0.227 | Passed |
| Theme | 1 | 0.209 | Passed |
| Macro | 1 | 0.602 | Passed |
| Risk | 5 | 0.692 | Passed |
| Stock | 9 | 2.391 | Passed |
| Watchlist | 2 | 0.214 | Passed |
| Report | 4 | 0.870 | Passed |
| Research | 1 | 0.565 | Passed |
| Navigation | 1 | 0.020 | Passed |
| Educational | 1 | 0.018 | Passed |
| Portfolio | 1 | 0.066 | Passed unavailable-boundary behavior |

Registry output is validated against the contract for the requested agent slot. An agent cannot bypass the registry by returning a valid result bearing another agent identity.

## 8. Routing metrics

Release-bearing runtime routing metrics:

- intent accuracy: 100%;
- exact required-agent recall: 100%;
- unnecessary-agent rate: 0%;
- invalid-route rate: 0%;
- mean agent count: 1.316;
- routing-suite fallback rate: 0%.

The past-tense query “Why did the market fall?” initially routed as unsupported. The classifier rule was corrected and protected by both a direct regression test and a frozen routing case.

## 9. Evidence-grounding results

Evidence grounding, factual correctness, contract correctness, and format compliance each scored 1.000 in the release-bearing suite. Accepted runtime cases had:

- zero unresolved cited evidence IDs;
- zero unsupported accepted numeric claims;
- zero accepted cross-entity or cross-metric numeric substitutions;
- zero wrong-source-ID identity reuse;
- zero accepted direct-yield claims from ETF proxies;
- zero accepted unsupported confirmed-breakout claims;
- zero accepted unknown action parameters.

Headline numbers now require a cited factor whose exact evidence carries the same value and matches the claim's entity, metric, and unit. Confirmed breakout evidence is grouped by security and requires the same security's price beyond its trigger plus affirmative volume evidence.

## 10. Contradiction-handling results

Contradiction handling scored 1.000. Runtime and frozen cases preserve opposing evidence, lower confidence under conflict, and retain confirmation/invalidation separation. Collected contradictions cannot be omitted; truncation requires an explicit disclosure.

The same evidence ID cannot serve as both confirmation and invalidation. A deterministic no-claim validation fallback is exempt from restating contradictions because it promotes no thesis. Valid evidence remains available after a synthesis-only fallback; bundle-level defects are quarantined.

## 11. Stale, missing, partial, and unavailable data

Freshness honesty scored 1.000. Runtime cases covered stale market data, partial stock data, confirmed-empty watchlists, unavailable breadth/report data, source exceptions, malformed sources, and bounded agent timeouts.

No accepted case presented stale evidence as current, produced an actionable stale conclusion, or retained high confidence with stale/partial/mixed/test/unavailable evidence. Explicit statements such as “currently unavailable” are not treated as stale-current violations, while “current price” from stale evidence is rejected.

## 12. Deep-link results

Deep-link accuracy scored 1.000. Runtime and frozen cases validated registered destinations, routes, tabs, sub-tabs, sections, entities, highlights, and exact parameter allowlists. Arbitrary parameters such as an injected `javascript:` URL are rejected even when the base destination is registered.

The executable 30-case pipeline also passed exact-action checks, and frontend destination safety tests passed.

## 13. Stability and repeatability

- All 15 handlers were executed repeatedly against frozen no-provider inputs with structurally identical results after excluding generated timestamps and durations.
- The 165-case corpus is checked in as strict JSONL with unique typed IDs and deterministic regeneration.
- The 30 executable fixture artifacts regenerated successfully and the subsequent 39-file `--check` reported current.
- The active agent and synthesis paths made zero model/provider calls in automated evaluation.

## 14. Performance and cost observations

Release-bearing hermetic runtime latency:

- mean: 3.272 ms;
- p50: 2.599 ms;
- p95: 6.491 ms;
- maximum: 8.456 ms;
- mean model calls: 0;
- token usage and estimated cost: unavailable/not applicable because the active path is deterministic.

Per-agent timings are included in the machine artifact. Development traces record time to first structured stream event. The backend currently emits structured sections only after synchronous completion; it is not token-level or incremental specialist-result streaming.

Freshness labels are not treated as cache telemetry. Cache-hit rate is deliberately null until upstream adapters expose actual hit/miss information.

The frozen reference corpus contains declared latency budgets, not measured runtime latency, and is not used for release performance claims.

## 15. Security and safety results

Safety scored 1.000 with zero release blockers. Seven runtime failure injections were executed and observed:

1. source exception;
2. malformed source;
3. missing snapshot;
4. bounded agent timeout;
5. requested-agent contract mismatch;
6. unsafe synthesis;
7. retrieved prompt injection.

Unsafe synthesis is replaced by deterministic, evidence-preserving fallback when the evidence bundle remains valid. Prompt injection or a bundle that fails the second validation pass is quarantined: the response is unavailable and exposes no evidence, actions, sources, or deep links.

Development traces record actual triggered rules separately from checks run. API keys, bearer tokens, passwords, emails, phone numbers, account identifiers, and device-local saved-symbol membership are redacted or pseudonymized. Early pipeline exceptions also produce an inspectable opt-in trace by request ID. Production logs continue to omit the raw query.

## 16. Defects discovered

The initial pass found these material defects or validation gaps:

- the 165-case runner compared checked-in reference outputs with checked-in expectations and was incorrectly suitable for overbroad PASS claims;
- all 86 semantic assertions in the 30 executable fixtures were declared but not executed;
- required-agent checks allowed unnecessary agents;
- requested-agent identity could be self-declared by a miswired handler;
- duplicate stock evidence IDs caused a contract failure;
- headline numbers could be authorized by another entity or metric with the same value;
- breakout evidence could combine price/trigger/volume from different securities;
- stale “current price” language could pass, while honest unavailable language could fail;
- source IDs could resolve to different timestamps/lineage;
- contradictions could be omitted or truncated without disclosure;
- confirmation and invalidation fixture generation could reuse one evidence item;
- registered actions accepted arbitrary non-reserved parameters;
- a second failed fallback validation was relabeled fallback while invalid evidence remained exposed;
- short-term language could be misread as a short recommendation;
- development traces reported every check as triggered, inferred cache hits from freshness, retained private membership/PII, and omitted early exceptions;
- confirmed-empty saved membership was modeled as unavailable in one fixture path;
- one market-explanation phrase routed as unsupported.

## 17. Defects fixed

Every item above received a deterministic correction and regression coverage. Key fixes include:

- a release-bearing 30-scenario runtime evaluator over the real pipeline;
- explicit NON-RELEASE labeling for reference/routing-only evaluation;
- a fail-closed 86-ID semantic assertion registry;
- runtime manifest enforcement against the requested agent;
- evidence deduplication and stricter entity/metric/unit/source validation;
- same-security breakout confirmation checks;
- report source timestamp identity correction;
- contradiction-preservation and condition-coherence checks;
- exact action-parameter allowlists;
- evidence quarantine after a second failed validation pass;
- PII-aware development tracing and exception traces;
- corrected empty-watchlist and routing behavior;
- a persistent local human-review CLI and artifact.

## 18. Remaining conditions

The following are non-release-blocking but prevent an unconditional PASS:

- runtime sources are deterministic hermetic adapters; automated tests perform no live provider/network calls;
- the 165-case semantic corpus is comprehensive but non-release-bearing by design;
- the active Copilot is deterministic, so stochastic model stability, token use, and model cost cannot be evaluated;
- direct yields, credit, economic events/news, authenticated holdings, and account-scoped saved-list sources remain unavailable or incomplete;
- sessions and review persistence are local/process-scoped; production authentication, retention, rate limits, and durable session storage remain integration work;
- cache hit/miss telemetry is not exposed by upstream adapters;
- streaming is structured section transport rather than incremental agent/token streaming;
- production positive-field mapping is covered through hermetic source objects and selected durable snapshots, not an optional live-market smoke run;
- existing manual/visual operator evidence was retained and indexed rather than repeated after backend-only validation changes.

## 19. Recommended next actions

1. Add an explicitly isolated, non-CI live smoke suite for production provider adapters and source timestamps.
2. Sample and classify the 165 generated human-review rows; retain reviewer notes outside production navigation.
3. Add authenticated account scoping before enabling portfolio or cross-device saved-list behavior.
4. Expose real upstream cache hit/miss telemetry before publishing a cache-hit metric.
5. If perceived latency requires it, stream completed specialist sections incrementally without weakening validation.
6. Keep `make validate-stage7` and the runtime machine artifact as required pre-release gates.

## 20. Exact reproduction commands

```bash
cd /Users/andypun/Downloads/market-intelligence-app
make validate-stage7 PYTHON=venv/bin/python
```

Individual evaluation commands:

```bash
cd /Users/andypun/Downloads/market-intelligence-app/backend

venv/bin/python -m app.copilot.evaluation.run_stage7 --mode runtime --suite full \
  --output ../artifacts/stage7-agent-validation.json

venv/bin/python -m app.copilot.evaluation.run_stage7 --mode runtime --suite routing
venv/bin/python -m app.copilot.evaluation.run_stage7 --mode runtime --suite performance
venv/bin/python -m app.copilot.evaluation.run_stage7 --mode runtime --suite safety

venv/bin/python -m app.copilot.evaluation.run_stage7 --mode reference --suite full \
  --output ../artifacts/stage7-reference-evaluation.json

venv/bin/python -m app.copilot.evaluation.review build \
  --results ../artifacts/stage7-reference-evaluation.json \
  --output ../artifacts/stage7-human-review.json

venv/bin/python -m app.copilot.tracing REQUEST_ID --trace-dir TRACE_DIRECTORY --full
venv/bin/python scripts/generate_stage7_copilot_artifacts.py --check
```

Example local review update:

```bash
venv/bin/python -m app.copilot.evaluation.review set-review \
  --review-file ../artifacts/stage7-human-review.json \
  --case-id market-broad-confirmed-advance \
  --classification correct \
  --usefulness useful
```

- Machine result: `artifacts/stage7-agent-validation.json`
- Frozen reference result: `artifacts/stage7-reference-evaluation.json`
- Local review artifact: `artifacts/stage7-human-review.json`

No future-stage agent was added. Report/PDF design was not changed; only Copilot-side report evidence lineage was corrected. Existing critical backend and frontend tests pass.
