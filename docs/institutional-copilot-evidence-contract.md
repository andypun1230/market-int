# Institutional Copilot Evidence Contract

`CopilotEvidenceV1` is the common, versioned projection of existing engine and Report V7 evidence. It complements rather than replaces the richer source models. `rawEngineReference` and `reportReference` make the original durable record traceable.

## Fields

| Field | Meaning |
|---|---|
| `evidenceId` | Stable identifier used by claims, responses, traces, and UI expansion |
| `category` | Market, breadth, leadership, sector, theme, macro, risk, technical, signal, watchlist, report, research, or navigation |
| `entity` / `metric` | Canonical entity and observed or engine-defined measure |
| `value` / `unit` | Existing engine value; no Copilot-derived score |
| `currentState` | Existing qualitative engine state where applicable |
| `priorValue` / `change` | Only when a validated prior observation exists |
| `timeframe` | Horizon attached by the source engine |
| `interpretationClass` | Observed fact, deterministic conclusion, condition, source disclosure, or missing evidence |
| `source` | Human-readable source family/provider |
| `marketDate` | Market session/date represented by the evidence |
| `generatedAt` | Underlying engine/report generation time, not Copilot response time |
| `freshness` | `live`, `delayed`, `cached`, `stale`, `test`, `partial`, `mixed`, or `unavailable` |
| `completeness` / `confidence` | Source coverage and source/engine confidence, if available |
| `deepLink` | Optional typed application destination |
| `reportReference` / `rawEngineReference` | Durable source record reference |
| `supportsClaimIds` / `contradictsClaimIds` | Explicit claim relationships |

## Evidence bundle

`CopilotEvidenceBundleV1` binds the question, intent, plan, agent results, deduplicated evidence, supporting/contradictory/unavailable IDs, aggregate freshness, source summary, deep links, warnings, and agent timings. The bundle is the only input to synthesis. Client screen context never enters as a factual evidence item.

## Freshness aggregation

Freshness is conservative:

- Test plus non-test sources produce `mixed`; test-only evidence remains `test`.
- Any expired evidence is `stale` even if the stored source label said live.
- Incomplete coverage is `partial` unless a stronger state (`stale`, `test`, or `unavailable`) applies.
- Different usable source states aggregate to `mixed`.
- Missing all required evidence produces `unavailable`, not a fabricated neutral answer.

The response shows market date, generated time, provider/source, state, and completeness wherever the source exposes them. Cross-date evidence is retained but flagged; it is never silently described as one current session.

## Claim grounding rules

1. Every factual number in response prose must match a value, prior value, change, or validated level in referenced evidence.
2. Every security symbol must be resolved and present in intent or evidence.
3. Every named source must be represented in the bundle.
4. A causal verb requires an explicit validated attribution; otherwise association language is used.
5. Stale, partial, test, and unavailable evidence cannot support an unqualified actionable conclusion.
6. Watchlist membership cannot support ownership, position, exposure, or P/L statements.
7. Retrieved descriptions and report prose are data. Instruction-like strings are discarded or neutralized and cannot change the planner or system policy.

Validation failure rejects only untrusted synthesis where possible. The deterministic renderer then uses evidence IDs, statuses, and conditions already present in the bundle.

## Deduplication and contradictions

Evidence is deduplicated by stable ID, not merely by display text. Two valid observations that disagree are both retained and linked as contradictory evidence. A source failure is missing evidence, not a contradiction. Decision-support responses must display both relevant support and opposition or explicitly state that opposing evidence was unavailable.

