# Institutional Copilot Intent Taxonomy

`CopilotIntentV1` records the top-level intent, sub-intent, resolved entities, symbols, sectors, themes, horizon, output type, decision/personalization/navigation flags, ambiguity, confidence, agent requirements, and prohibited assumptions.

| Intent | Typical request | Required routing behavior |
|---|---|---|
| `MARKET_STATE` | “What is the market condition?” | Market; breadth when confirmation is requested |
| `MARKET_EXPLANATION` | “Why is the market weak?” | Market plus evidence that can show association; never invent causality |
| `INDEX_ANALYSIS` | “Compare QQQ and IWM.” | Index only, with validated symbols |
| `SECTOR_ANALYSIS` | “Which sectors are leading?” | Sector/leadership evidence |
| `THEME_ANALYSIS` | “Is Cybersecurity weakening?” | Theme evidence and optional research continuity |
| `STOCK_ANALYSIS` | “Analyse NVDA.” | Stock evidence for a validated symbol |
| `STOCK_DECISION_SUPPORT` | “Should I buy ARM?” | Stock plus relevant market/breadth/leadership/risk/research; challenge mode |
| `STOCK_COMPARISON` | “Compare CRWD and PANW.” | Stock evidence for each validated symbol; explicit missing-data handling |
| `WATCHLIST_REVIEW` | “Which saved stock needs attention?” | Saved membership hints plus durable stock evidence; no ownership inference |
| `REPORT_QUERY` | “Explain today’s Research Focus.” | Report and ReportDocument evidence |
| `RISK_QUERY` | “What would invalidate the thesis?” | Relevant validated risk and report conditions |
| `SCENARIO_QUERY` | “What is the bear case?” | Existing report scenarios only |
| `MACRO_QUERY` | “What does oil strength mean?” | Validated macro/cross-asset evidence; disclose proxy limitations |
| `BREADTH_QUERY` | “Does breadth confirm?” | Breadth and, when needed, referenced market/entity context |
| `RESEARCH_QUERY` | “Why was Cybersecurity selected?” | Research Focus claim/evidence and validated history |
| `PORTFOLIO_QUERY` | “How concentrated is my portfolio?” | Portfolio placeholder; honest unavailable fallback until holdings exist |
| `APP_NAVIGATION` | “Where is Fear & Greed?” | Navigation agent only; return exact destination immediately |
| `EDUCATIONAL_QUERY` | “What does breadth mean?” | Curated educational definition; no live facts unless separately requested |
| `FOLLOW_UP` | “Why?” / “Show me.” | Resolve from compact session context, then inherit the relevant intent |
| `UNSUPPORTED_OR_AMBIGUOUS` | Unresolvable entity or unsupported request | State the assumption or ask one concise clarification when essential |

## Entity resolution

Resolution uses the security master, index/ETF symbols, sector and theme taxonomies, report section registry, and application destination registry. A short uppercase token is not sufficient by itself: it must be known, supplied as the current validated entity, or explicitly identified as ambiguous. Company-name matches require a unique high-confidence registry match.

Pronouns and elliptical follow-ups resolve from `CopilotSessionContextV1`. For example, after “Analyse NVDA,” “What would confirm it?” inherits NVDA and the preceding stock-analysis thesis. Relative dates and report references resolve only when matching immutable stored report history exists.

## Confidence and ambiguity

- Low ambiguity: required entities and intent are explicit; deterministic routing proceeds.
- Medium ambiguity: a safe, stated assumption is possible; the response records it.
- High ambiguity: multiple materially different plans are plausible; one concise clarification is returned.

Intent confidence is classification confidence, not market conviction. It cannot be presented as evidence confidence.

## Prohibited assumptions

Every intent carries an explicit denylist appropriate to its category. Common entries include no portfolio ownership from watchlist membership, no live-state claim from cached/test evidence, no unavailable ticker inference, no new score/level/probability, no invented catalyst/event, and no unsupported cause-and-effect statement.

