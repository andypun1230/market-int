# Stage 8 Intelligence Dependency Map

## Runtime topology

```text
Explicit NewsProvider mode             Existing normalized market evidence
  unavailable / cached / hermetic        daily OHLCV / snapshots / mappings
                 |                                      |
                 v                                      v
          News repository                    Session input boundary
          (metadata only)             (production daily-only; test intraday)
                 |                                      |
                 v                                      v
 normalization -> credibility       calendar -> segmentation -> structure
      -> classification                         -> VWAP/volume when supported
      -> clustering                              -> catalyst association
      -> entity mapping                                  |
      -> materiality/reaction                            v
                 |                         SessionNarrativeResult
                 v                                      |
       NewsIntelligenceResult --------------------------+
                 |
                 v
       Existing 15-agent Copilot registry
                 |
     +-----------+-----------+-------------+-------------+
     v           v           v             v             v
    Home       Market    Sector/Theme      Stock       Watchlist
```

## Trust boundaries

| Boundary | Accepted | Rejected |
|---|---|---|
| Provider to normalization | Identifiers, metadata, timestamps, canonical URL, controlled summaries/facts, provider mode | Provider-specific objects exposed to consumers; invalid timestamps; silent fixture fallback |
| News persistence | Whitelisted event identity metadata, bounded headline, timestamps, provenance and correction lineage | Summaries, facts, evidence statements, reactions, article bodies, credentials, authentication headers |
| Event to cluster | Deterministic identifiers, normalized tokens, entity/type/time overlap, primary-source references | Treating repeated syndicated articles as independent confirmation |
| Event to entity | Existing symbol/sector/theme registries and explicit versioned relationships | Guessed suppliers, customers, holdings, or ambiguous common-word tickers |
| Event to reaction | Explicit supported price/volume window with evidence IDs | Causation, unsupported intraday windows, missing-data substitution |
| Session service | Validated timezone-aware bars and injected calendar; daily fallback contract | Intraday prose from daily bars; UTC-as-exchange-time assumptions |
| Services to Copilot | Typed immutable service results, scalar evidence, IDs and limitations | Raw provider payloads, article bodies, client-supplied facts |
| Consumers | Shared service DTOs with explicit status/source mode/freshness | Independent screen-level feeds or mock-as-live presentation |

## Existing Stage 7.5 engine reuse

Both services reuse the Freshness and Availability, Evidence Validation, Contradiction Preservation, and Confidence Adjustment engines. Domain-specific rules remain inside their service boundaries so the frozen Stage 7 contracts are not weakened.

## Availability matrix

| Capability | Production | Hermetic validation |
|---|---|---|
| News normalization, clustering, mapping, scoring | Runs only on explicitly supplied/cached validated events | Full |
| Live news acquisition | Unavailable | Not simulated as live |
| Close-to-close reaction | Supported when daily evidence covers the window | Full |
| 5/15-minute News reaction | Unavailable | Unavailable in the current daily-only News reaction engine |
| Production daily-only session state | Typed provenance and availability only; no intraday prose | Covered by explicit adapter fixtures |
| Session segments, turning points, session VWAP | Unavailable | Full with explicit bars/calendar |
| Intraday breadth timeline | Unavailable | No standalone breadth timeline is currently emitted |

## Agent boundary

The 15 validated agents remain registered; Stage 8 adds no News or Session agent. Explicit News routing reuses Market, Index, Leadership, Sector, Theme, Macro, Risk, Stock, Watchlist, and Research. In particular, `reaction_breadth`, `event_risk`, and `research_event_context` route to the existing Leadership, Risk, and Research agents. Explicit Session routing is validated through Market and Stock, with Index also permitted by the existing contract. The Report Agent has a typed retrieval seam for both News and Session evidence, but Stage 8 does not add it as a second agent to ordinary News/Session plans and does not change Report/PDF rendering. Legacy intents do not read the new sources, preserving Stage 7 source-call and routing behavior.

## Observability boundary

The service contracts expose stable result, event, cluster, evidence, mapping, claim, and source IDs plus per-component processing timings. The benchmark and validation artifacts record those values. There is no centralized trace/span recorder or exported production-trace integration in Stage 8, so these contract fields and timings must not be described as end-to-end production tracing.
