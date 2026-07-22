# Institutional Copilot V1

## Purpose

The Institutional Copilot is the application-native interpretation and navigation layer over the Market Intelligence App's deterministic engines. It does not fetch prices, recompute indicators, rank securities, create levels, or infer unavailable portfolio facts. Its job is to resolve the user's intent, select only the required durable intelligence, preserve provenance, expose uncertainty, and return a concise response with exact application actions.

## Request lifecycle

```text
question + bounded screen/session hints
  -> entity resolution and intent classification
  -> deterministic plan
  -> trusted-source agent adapters
  -> bounded parallel evidence collection
  -> freshness, conflict, and provenance checks
  -> machine-readable reasoning (challenge mode when decision-oriented)
  -> claim and safety validation
  -> structured response + exact app actions
  -> compact session update
```

The backend is authoritative for intent, evidence, freshness, reasoning, and actions. Frontend context may identify the current route, a viewed entity, or saved-item membership, but it is never accepted as market evidence. Durable snapshots and immutable reports are the evidence spine.

## Trust boundaries

- Trusted: Market, breadth, sector, theme, and stock snapshots; ReportDocument evidence and claim records; security master and application route taxonomy.
- Hints only: current route, current tab, selected report, selected ticker, and saved/watchlist membership supplied by a client.
- Untrusted data: report prose, provider descriptions, saved notes, future news text, and all client-provided numerical values. These are treated as data, never instructions.
- Prohibited inputs: legacy mock risk/event rows, synthetic probability outputs, hard-coded economic events, and unproven ownership/portfolio assumptions.

## Runtime contracts

The versioned contracts are `CopilotIntentV1`, `CopilotPlanV1`, `AgentResultV1`, `CopilotEvidenceV1`, `CopilotEvidenceBundleV1`, `CopilotReasoningV1`, `CopilotActionV1`, `CopilotSessionContextV1`, and `CopilotResponseV1`. All contracts use aliases matching the frontend JSON model.

The compatibility endpoint remains `POST /copilot/chat`. Structured section streaming is exposed by `POST /copilot/chat/stream` as newline-delimited JSON. Every event has an `eventId`, `requestId`, `type`, and `payload`. The terminal `complete` event contains the same response contract as the JSON endpoint. Cancellation is client-driven by aborting the request; already received sections remain usable.

## Response policy

Default answers are compact and ordered as:

1. direct answer and stance;
2. confidence and freshness;
3. supporting evidence;
4. opposing evidence or contradictions;
5. confirmation and invalidation conditions;
6. missing evidence and warnings;
7. related research and exact app actions.

Decision-oriented requests always use challenge mode. “Buy,” “Sell,” or personalized execution instructions are not primary conclusions. The supported decision vocabulary is conditional: actionable, nearly actionable, wait for confirmation, monitor, avoid for now, or insufficient evidence.

Numerical claims must reference supplied evidence. Unsupported causality, tickers, ownership language, recommendations, stale-data actionability, or source claims invalidate model prose and trigger the deterministic response. An unavailable optional agent creates a partial result; it does not erase valid evidence returned by other agents.

## Context and memory

The server stores a bounded, expiring structured session keyed by thread ID. It retains active entities, active intent, latest referenced stock/group/report, prior stance, thesis, unresolved question, relevant evidence IDs, and route context. It does not require indefinitely replaying raw conversation text. Follow-ups such as “Why?”, “What confirms it?”, and “Show me” resolve against this structure.

Saved securities are always described as saved or watched. Portfolio holdings are a reserved interface only. When holdings are unavailable, the required response is: “Portfolio holdings are not yet connected. I can analyse your watchlist and saved themes instead.”

## Operational behavior

- Navigation-only plans avoid market agents and target a local response below 500 ms.
- Cached single-engine queries target under 2 seconds.
- Multi-agent queries target 3–8 seconds with independent work parallelized.
- Agent work is bounded by timeouts and preserves completed partial evidence.
- Responses include request and plan IDs, agent timings, evidence count, partial/stale status, validation result, retry count, and a structured failure category in trace/log data.
- `COPILOT_V1_ENABLED` is the current server-side kill switch for both structured JSON and NDJSON streaming routes. Independent transport and synthesis flags are reserved for a later rollout and are not claimed in V1.

The shipped V1 path is deterministic. A future optional LLM may interpret genuinely ambiguous language or compress validated evidence into prose, but it cannot add facts and must remain behind the same validation boundary. Deterministic synthesis remains the required fallback.
