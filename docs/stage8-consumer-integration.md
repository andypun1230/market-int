# Stage 8 Consumer Integration

## Principle and implemented presentation boundary

Every integrated surface reads the same typed News Intelligence or Session Narrative result. Consumers do not reclassify events, calculate materiality, infer causation, or fetch provider payloads. The current frontend is a deliberately compact subset of the backend contracts; availability in a DTO does not mean that every field is rendered.

Stage 8 requests are failure-isolated from existing core dashboard requests. An unavailable context service must not break a Stage 7 screen.

## Surface contracts

| Surface | Query | Current Stage 8 presentation | Failure behavior |
|---|---|---|---|
| Home | One market-wide News query | “What Moved the Market,” capped at three compact event rows | Explicit loading, partial, stale, unavailable, and no-material-events states |
| Market Overview | Market Session query | Session state, headline, one supporting claim or availability message, first caveat, and causality disclosure | `daily_only` label when intraday evidence is absent; independent of core dashboard |
| Sector detail | Selected sector only | Compact Catalyst rows | No unrelated market-wide headlines; unavailable card does not block detail |
| Theme detail | Selected theme only | Compact Catalyst rows | Synthetic/test themes remain visibly test-labelled and do not request live catalysts |
| Stock detail | Selected symbol while detail is open | Compact Material Events rows in Overview | Does not replace Technical, Signals, Risk, or Compare; no fetch while collapsed |
| Watchlist | One batched query for explicit device-saved symbols | Compact Watchlist Catalysts rows and saved-symbol count | Never interprets saved symbols as holdings; no N+1 requests |
| Copilot | Typed service read for explicit news/session intents | Existing agents expose scalar fact/reaction/interpretation evidence with service IDs | Legacy intents make no Stage 8 source calls; unavailable evidence produces a grounded limitation |
| Report | Typed Report Agent retrieval seam for News and Session | No new ReportDocument field, PDF section, or renderer logic | Retrieval remains separate from report rendering |

All current News cards render the service-state/freshness badge and, when present, the canonical headline, source name and quality, publication time, the surface-relevant materiality score, affected-entity labels, and reaction summary. They render only the first contradiction; the first limitation is shown only when it is not already the card's main message. The Session card renders the state badge, headline, one supporting claim or availability message, the first caveat, and the causality disclosure.

## Presentation conditions

The backend contracts expose more detail than the current cards. The following are not yet rendered by the Stage 8 frontend:

- interactive event links or event-detail navigation, even though typed deep-link metadata and Copilot destinations exist;
- confirmed facts, evidence statements, evidence IDs, full correction/cluster lineage, or source-detail drill-down;
- reaction windows, numeric return/volume/breadth inputs, or the controlled reaction classification;
- more than the first contradiction or first limitation;
- Session phase aggregates, structure, VWAP, volume pace, level tests, turning points, catalyst timeline, claim-to-evidence detail, confidence, or full provenance timestamps;
- sector/theme breadth, thesis, or horizon context; stock volume, technical, or thesis-implication context; and named Stage 8 Watchlist states such as material news, unusual reaction, thesis change, event risk, no material change, and stale;
- any Report/PDF presentation of News or Session evidence.

## Deep links

Stage 8 reuses the registered destinations and exact parameter contracts:

- Home: `/`
- Market: `/market`
- Sector or theme detail: `/sectors` with registered entity parameters
- Stock detail or Watchlist: `/watchlist` with the registered symbol/detail parameters
- Report: `/report`

Events remain API/detail-card data. Typed service deep links survive the backend and Copilot adaptation, but the current frontend context rows are not interactive. Stage 8 does not create a standalone News screen or add arbitrary event parameters to validated Copilot actions.

## Consumer safety rules

1. Derive the displayed service-state/freshness badge from explicit result fields; never infer state from whether rows are present.
2. Label `hermetic` and `mock` data as test data in developer/test surfaces only.
3. Show `daily_only` instead of intraday labels when 5/15-minute data is absent.
4. Keep “coincided with,” “followed,” “consistent with,” “not confirmed by,” and “contradicted by” language from the service.
5. Never show raw article text, HTML, Markdown, script, authentication data, or unsafe URLs.
6. Preserve partial results and limitations instead of filling missing fields.
7. Cache canonicalized filters and deduplicate in-flight calls. Watchlist queries are batched.

## Report retrieval seam

The existing Report Agent can retrieve typed News and Session evidence through the common agent registry, and focused tests validate that seam. This does not write the evidence into `ReportDocument` and does not render it in a report or PDF. Any future renderer must use validated contract fields and must not cluster, score, map, or interpret events. No Report or PDF design changes are part of Stage 8.
