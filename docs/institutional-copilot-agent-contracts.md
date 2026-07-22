# Institutional Copilot Agent Contracts

Copilot agents are deterministic adapters, not independent LLM personas. Each accepts a plan step plus resolved entities, reads only trusted durable sources, and emits `AgentResultV1`. An agent result contains status, observations, conclusions, contradictions, metrics, levels, source references, evidence IDs, freshness, deep-link targets, warnings, missing data, and elapsed time.

The executable contract registry is `backend/app/copilot/agent_manifest.json`, loaded as typed models by `backend/app/copilot/agent_contracts.py`. `CopilotAgentRegistry.execute` validates every result against the manifest entry for the **requested registry slot**. A handler cannot self-declare a different valid agent to bypass the boundary. Schema version, freshness, evidence categories, destinations, source lineage, unique IDs, level references, confirmation/invalidation separation, constrained-confidence caps, status/freshness consistency, disclosures, and failure categories are enforced. Any error is converted to a typed failed result with `failure_category=agent_contract`; no invalid factual evidence is returned.

Statuses are `complete`, `partial`, `stale`, `unavailable`, or `failed`. Missing optional data must be explicit. An adapter cannot fill a gap with client values or model prose.

| Agent | Trusted inputs | Primary output | Key fallback |
|---|---|---|---|
| Market | MarketSnapshot and report market claims | Regime/posture evidence | Unavailable when no durable snapshot/report fact exists |
| Index | MarketSnapshot index section | Existing index state and comparison facts | Report missing entity separately |
| Breadth | BreadthSnapshot and linked report evidence | Participation/confirmation observations | Stale/partial state remains visible |
| Leadership | SectorSnapshot, ThemeSnapshot | Existing ranks/states and contradictions | Never create a replacement ranking |
| Sector | SectorSnapshot | Selected sector evidence | Require a resolved sector |
| Theme | ThemeSnapshot and theme definitions | Theme state, breadth, participation, provenance | Unsupported theme is unavailable |
| Macro | Validated market/report macro evidence | Observed cross-asset context | Preserve ETF-proxy disclosure; omit unsupported events |
| Risk | Validated report/stock risk conditions | Existing risks and invalidation conditions | Exclude hard-coded legacy event data |
| Stock | StockAnalysisSnapshot | Existing technical/signal/risk facts and levels | No request-time provider call; partial per symbol |
| Watchlist | Saved-symbol hints plus durable stock snapshots | Evidence-backed changes for saved securities | Empty/stale lists are stated, never converted to holdings |
| Report | Immutable ReportDocument | Claims, scenarios, conditions, sources | State when prior report/history is absent |
| Research | Report V7 Research Focus and evolution history | Selection rationale and continuity | Never fabricate yesterday-to-today continuity |
| Navigation | Typed application destination registry | Exact `CopilotActionV1` | Ask for destination only when genuinely ambiguous |
| Educational | Curated bounded definitions | Concept explanation | Separates education from current-market claims |
| Portfolio | Future holdings provider interface | Reserved exposure/concentration evidence | Always honest unavailable fallback today |

## Collector behavior

The planner names required and optional agents. Independent agents run concurrently under a per-plan latency budget. The dependency field is retained in the contract, but current minimal V1 plans do not emit dependent step chains. The collector deduplicates evidence by stable evidence ID, records differing observations as contradictions rather than overwriting them, aggregates source states conservatively, and preserves successful results after a timeout or failure.

After synthesis, the response validator separately enforces claim-to-evidence binding, source identity, report lineage, contradiction preservation, freshness language, proxy labels, numeric/entity/metric/unit consistency, confirmation coherence, registered action parameters, and safety policy. A synthesis-only failure uses deterministic fallback reasoning. If that fallback still fails because the request or evidence bundle is unsafe, the orchestrator quarantines the bundle and returns unavailable freshness with no evidence or actions.

A navigation request uses Navigation only. A simple stock analysis uses Stock. A decision-support request can add Market, Breadth, Leadership, Risk, Research, and Watchlist only where the requested decision and available context make them relevant. This prevents the Copilot from treating every question as a full market refresh.

## Portfolio interface

The future `PortfolioAgent` boundary accepts a user-scoped holdings provider with holdings, cost/position metadata, exposure, sector/theme mappings, beta, correlations, and P/L provenance. Until an authenticated provider exists, the agent returns `unavailable`; no placeholder values or watchlist-derived exposure are permitted.
