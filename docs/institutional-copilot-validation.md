# Institutional Copilot Validation

## Final validated result

**PASS WITH CONDITIONS** — Stage 7 is implementation-complete and the current agent-validation gates passed on 22 July 2026. The authoritative follow-on report is `docs/validation/stage7-agent-validation-report.md`; its machine result is `artifacts/stage7-agent-validation.json`. The conditions are disclosed data, evaluation-boundary, and production-integration gaps, not failing critical tests.

| Validation layer | Final result |
|---|---|
| Release-bearing hermetic runtime scenarios | 30/30 passed; all 15 agents and 7/7 injections |
| Frozen semantic/reference corpus | 165/165 passed; explicitly non-release |
| Executable deterministic fixtures | 30/30 passed; 86/86 declared assertions enforced |
| Backend full unittest discovery | 395/395 passed; 0 failures, 0 errors |
| Backend Copilot-focused regression suite | 111/111 passed before the final full-discovery gate |
| Backend compile validation | Passed |
| Frontend release checks | 10/10 passed: TypeScript, full ESLint, 28-screen data/UI validation, named tests, and export |
| Frontend named Copilot tests | 6/6 passed |
| Expo web export | Passed: 25 routes, 51 files, 5.5 MB |
| Manual application prompts | 15/15 passed |
| Visual review | 10/10 screenshots captured and reviewed at 1280×720 and 390×844 |
| Browser runtime errors | 0 observed |
| Release criteria | 20/20 passed |

The final live local API measurements used five quiescent samples per class. Navigation recorded p50 147.0 ms and p95 148.7 ms against the 500 ms target; a cached single-engine breadth query recorded p50 144.8 ms and p95 160.6 ms against the 2,000 ms target; a cached multi-agent ARM decision query recorded p50 176.0 ms and p95 181.7 ms against the 8,000 ms upper target. `performance.json` separately records deterministic fixture-adapter timings and does not claim to be a production-provider benchmark.

Manual testing confirmed exact Fear & Greed, Breadth, and ARM detail destinations; stock support and opposition; explicit confirmation and invalidation; report Research Focus continuity; saved-stock attention using hydrated device-local membership; the honest unavailable portfolio fallback; stale/partial labeling; evidence expansion; compact follow-up memory; cancellation with partial preservation; and retry completion. The final saved-stock answer names only candidates supported by cited deterministic setup/risk caution evidence, identifies the review as unranked, and does not infer holdings.

The remaining conditions are: some durable sources are stale or partial; authenticated portfolio and account-scoped watchlist providers are absent; reliable prior immutable report continuity is not universal; direct yields, credit, economic, and news feeds are incomplete; sessions remain process-local without production authentication or rate limiting; and the native software keyboard was not emulated during the web visual pass. These conditions are represented in `output/stage-7/release-gates.json` and surfaced honestly by the runtime where applicable.

## Release gates

Stage 7 is accepted only when all 30 required fixtures produce versioned intent, plan, evidence, reasoning, response, action, validation, and trace artifacts; backend and frontend focused tests pass; exact deep links are exercised; streaming cancellation and interruption preserve partial work; and the rendered app is manually inspected at desktop and compact mobile sizes.

The machine-readable evidence is stored under `output/stage-7/`. The fixture manifest is authoritative for case IDs and expected safety behavior. Performance output records warm navigation, cached single-engine, and multi-agent timings without forcing live provider refreshes.

## Automated coverage

| Layer | Required assertions |
|---|---|
| Contracts | Version tags, enum validation, aliases, bounded lists, serialization round trip |
| Intent | All taxonomy categories, entity resolution, horizon, ambiguity, decision/navigation split, follow-up inheritance |
| Planner | Minimal agent selection, dependencies, safe fallbacks, latency budget, parallelizable steps |
| Agents | Structured output, stable evidence IDs, provenance, freshness, partial/unavailable/timeout behavior |
| Evidence | Numeric grounding, source retention, deduplication, contradiction detection, test/stale state, no ownership inference |
| Reasoning | Support and opposition, confirmation/invalidation, missing evidence, insufficient-evidence stance |
| Safety | Ticker/number/source checks, causality, advice, ownership, stale actionability, prompt injection |
| API | JSON compatibility, NDJSON ordering, terminal response, malformed request, cancellation-safe generator |
| Frontend | Stream parser/deduplication, reducer states, cancel/retry/partial preservation, evidence grouping, freshness, action routing, context suggestions |
| Compatibility | Existing report versions, universal command search, stock detail, watchlist, market, sectors, and themes |

## Required fixture set

The 30 fixture IDs are: market state, market explanation, index comparison, breadth, leading sector, weakening theme, stock analysis, stock decision support, stock comparison, watchlist review, report Research Focus, risk, scenario, navigation, education, follow-up why, follow-up confirmation, ambiguous ticker, empty watchlist, stale watchlist, partial stock, mixed-source market, no prior report, report history, unsupported portfolio, invalid LLM output, agent timeout, stream interruption, retrieved prompt injection, and test-data environment.

Safety-specific fixtures must prove:

- the stock-decision answer contains evidence for and against;
- stale evidence is visible and cannot become a current actionable claim;
- the portfolio answer uses the honest unavailable fallback;
- prompt-injection text cannot alter policy or expose instructions;
- test data is never labeled live;
- missing report history is not converted into a change narrative;
- a timed-out agent yields a bounded partial response;
- an interrupted stream leaves the UI cancellable with received sections intact.

## Manual application matrix

The running application is exercised with the 15 prompts from the Stage 7 brief: market condition, breadth explanation, ARM decision support, NVDA challenge mode, CRWD/PANW comparison, Cybersecurity Research Focus, saved-stock attention, market-thesis invalidation, Fear & Greed navigation, Breadth navigation, prior-report change, unavailable portfolio concentration, then “Why?”, “What confirms it?”, and “Show me.”

For every run, record intent, selected agents, answer status, grounding, source/freshness display, contradictions, actions, follow-up continuity, elapsed time, console/runtime errors, and whether navigation reached and highlighted the exact destination.

## Visual review

Capture the default screen, market answer, stock decision, challenge mode, report Research Focus, navigation action, stale response, partial response, follow-up conversation, and a 390×844 compact viewport. Review density, hierarchy, evidence expansion, action clarity, safe areas, composer/keyboard behavior, loading/cancellation, and bottom-navigation interaction.

## Final result recording

The release record must use `PASS`, `PASS WITH CONDITIONS`, or `FAIL`. Any unrelated inherited failure is listed with a reproducing command and evidence that Stage 7 files are outside its failing path. It is not “fixed” by changing unrelated behavior.
