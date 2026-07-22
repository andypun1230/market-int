# Institutional Copilot Data Gaps

This file records known unavailable or unreliable inputs and the required product behavior. It prevents a model, agent, or UI from silently converting a gap into certainty.

| Gap | Current behavior | Permitted Copilot fallback |
|---|---|---|
| Authenticated portfolio holdings | No holdings, exposure, P/L, beta, or correlation provider exists | State that holdings are not connected and offer watchlist/saved-theme analysis |
| Genuine multi-day report continuity | Stored examples can share one market date; prior report may be absent | State that continuity cannot be established; never fabricate change |
| Direct yields/credit/VIX-curve feeds | Not consistently available in durable snapshots | Omit the relationship or label available ETF proxy evidence precisely |
| Economic events, catalysts, news | Legacy risk rows include hard-coded/sample events | Exclude them unless a validated, time-stamped provider is added |
| Ownership and institutional positions | Watchlist membership is not ownership | Use “saved,” “watched,” or “in your watchlist” only |
| Analyst targets/ratings | No validated institutional analyst feed | Do not create or repeat unsupported ratings/targets |
| Probability forecasts | Legacy synthetic probability output is not acceptable evidence | Use scenario conditions without invented probabilities |
| Some stock snapshots | Requested symbols may be expired, partial, or absent | Return per-symbol missing data; do not infer indicators or levels |
| Theme universe breadth | Only governed reviewed themes have durable intelligence | Mark an unsupported theme unavailable; do not improvise a basket/rank |
| Report personalization scope | Historical cache is not authenticated/user-scoped | Avoid cross-user personalized continuity; use only request-scoped saved hints |
| Company-name ambiguity | Registry can contain aliases or multiple matches | Ask one concise clarification instead of guessing a ticker |
| Provider/request freshness | Durable snapshots may be stale outside market hours | Show market date and source state; do not trigger live calls merely for Copilot |
| Authenticated saved-list membership | Saved membership is hydrated from device-local frontend storage; the backend has no account-scoped watchlist store | Prefer the explicit identity-only `savedSymbols` hint, distinguish an explicit empty list from missing context, and never treat backend default watchlist rows as user saves |
| Agent-level cache telemetry | Upstream snapshots expose freshness/source state but not whether a particular lookup was a cache hit | Report source-state counts; leave cache-hit rate unavailable rather than inferring it from `cached` or `delayed` freshness |

## Explicit denylist

The Copilot must not consume legacy `MOCK_VIX`, hard-coded market-risk rows, hard-coded CPI/Fed/earnings events, stubbed watchlist setup/level/date rows, or synthetic probability estimates as trusted evidence. A MarketSnapshot section marked live is still downgraded when nested coverage, expiration, or data-quality metadata says stale, mixed, partial, or test.

## Future integrations

The Portfolio interface is reserved for authenticated holdings and position metadata with source timestamps and user scoping. Future news/catalyst, economic calendar, credit/yield, fund-flow, and institutional-ownership providers must first supply durable provenance, freshness, coverage, and evidence IDs. Adding a provider does not authorize free-form causal attribution; attribution still requires a validated relationship record.

## Operational gaps

The current deployment is a local application without backend user authentication. Structured session memory is therefore bounded and process-local, suitable for follow-up continuity but not durable cross-device history. Saved-list membership is also device-local and supplied as identity-only request context; if that hint is absent, the backend reports membership unavailable instead of treating application defaults as user saves. Native transcript persistence should stay bounded and avoid sensitive raw content. Production rollout requires authenticated session and watchlist scoping, persistent session storage, retention controls, redaction policy, telemetry sampling, and rate limits.
