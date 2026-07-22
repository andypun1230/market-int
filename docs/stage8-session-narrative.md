# Stage 8 Session Narrative Domain

## Purpose and current production boundary

The Session Narrative domain provides deterministic analysis contracts for finalized US-equity 5-minute and 15-minute OHLCV bars. It can describe observed session structure, VWAP relationships, volume behavior, source-backed level tests, and the timing of sourced catalyst events.

The current production market-data stack does **not** provide eligible intraday bars. The production adapter therefore returns only `daily_only` or `unavailable`. It never resamples daily candles, invents intraday bars, or promotes mock or test data to live evidence.

The implementation is isolated in:

- `backend/app/analysis_engines/session/`
- `backend/app/intelligence/session_narrative/`
- `backend/tests/stage8/test_session_analysis.py`
- `backend/tests/stage8/test_session_narrative.py`

The machine-readable inventory is `backend/app/intelligence/session_narrative/session_manifest.json`.

## Public contracts

All domain contracts are Pydantic v2 models configured with `extra="forbid"`, `frozen=True`, `strict=True`, validated defaults, and typed enums. Unexpected fields and incorrectly typed values fail validation rather than being silently coerced.

### Analysis input

`SessionAnalysisInput` is the analytical boundary. It contains:

- symbol and intended session date;
- `5m` or `15m` interval;
- explicit data mode;
- ordered finalized intraday bars;
- optional prior close;
- optional source-backed support or resistance levels;
- optional expected-session-volume baseline and cumulative intraday profile;
- optional sourced catalyst events;
- provider, dataset, source ID, and source state;
- generated, observed, and injected-current timestamps;
- freshness threshold and explicit test-data flag.

Important validation rules include:

- `daily_only` and `unavailable` forbid intraday bars. An empty intraday observation set is accepted so the injected calendar can identify a holiday or weekend; on an open date it fails closed as unavailable.
- `intraday_5m` requires a `5m` interval and `intraday_15m` requires `15m`.
- Bar timestamps must be timezone-aware, unique, increasing, and aligned to the declared interval.
- OHLC prices must be finite and positive, with internally valid highs and lows.
- Volume and transaction counts cannot be negative.
- Unavailable sources cannot provide eligible intraday bars.
- `source_state=test` and `test_data=true` must be declared together.
- Known mock, fixture, and generated-test providers cannot be represented as live.
- Generated, observed, baseline, level, and catalyst timestamps cannot be later than their relevant injected observation boundary.

`IntradayBar.is_final` is explicit. A bar is eligible only when it is marked final and its interval end is not later than `observed_at`. Unfinished or future-ending bars are segmented for diagnostics but excluded from calculations.

### Analysis result

`SessionAnalysisResult` contains:

- status, explicit analysis state, data mode, interval, session date, and source ID;
- phase assignment for every supplied bar;
- per-phase aggregates, including range, direction, volatility proxy, close location, and completeness;
- session structure;
- VWAP analysis;
- volume analysis;
- source-backed level tests;
- conservative evidence-linked turning points;
- catalyst timeline hooks;
- quality, coverage, and freshness;
- evidence records and preserved contradictions;
- confidence result and every contributing cap;
- explicit limitations and the mandatory causality disclosure.

The analysis-state enum distinguishes `regular_session`, `premarket_only`, `after_hours_only`, `extended_hours_only`, `closed_holiday`, `closed_weekend`, `daily_only`, and `unavailable`. Closed and extended-hours-only states never infer regular-session structure, VWAP, volume pace, or levels. An unavailable or daily-only result contains no inferred session structure or intraday evidence.

### GET-ready production query and result

The transport-neutral endpoint composition is:

```text
SessionNarrativeQuery
  -> ProductionSessionDataAdapter.query(...)
  -> ProductionSessionNarrativeResult
```

`SessionNarrativeQuery` carries the symbol, requested 5-minute or 15-minute interval, optional requested session date, and an aware `as_of` timestamp.

`ProductionSessionNarrativeResult` exposes these exact top-level fields:

- `query`
- `status`
- `availability`
- `provider`
- `data_mode`
- `as_of`
- `latest_daily_session`
- `narrative`
- `limitations`
- `provenance`

The nested provenance includes provider, dataset, source ID, data mode, as-of timestamp, latest known daily session, intraday support, test-data detection, and the no-resampling production policy. Cross-field validators require query, result, narrative, and provenance timestamps, modes, providers, availability, and latest-session values to agree.

The following handlers are registered under the existing `/intelligence` router:

- `GET /intelligence/session/market`, using SPY as the market benchmark;
- `GET /intelligence/session/{symbol}`, using the explicitly requested symbol.

Both accept `interval=5m|15m`, an optional `session_date=YYYY-MM-DD`, and an optional timezone-aware `as_of`. They validate into `SessionNarrativeQuery`. The API then reads local Polygon daily storage with `DailyBarStorage.history(symbol, "polygon", end_date=<as_of New York market date>)` and uses only the last eligible stored session as daily provenance. This bound prevents a future stored daily bar from appearing in a historical query. The API passes that provenance into `ProductionSessionDataAdapter`, which deliberately performs no provider reads, and the routes remain fail-closed because the current production store has no eligible intraday source.

## Calendar and session boundaries

`MarketSessionCalendar` always uses `America/New_York`, including daylight-saving transitions. It has no remotely updated or silently changing holiday dependency. Callers inject the holidays and early closes that cover the requested period through `MarketCalendarConfig`; tests inject fixed values and are hermetic.

Default boundaries on an open weekday are:

| Phase | Boundary |
| --- | --- |
| Premarket | 04:00 inclusive to 09:30 exclusive |
| Opening phase | Regular open inclusive through 60 minutes after the open, exclusive |
| Morning | Opening-phase end through 12:00, bounded by final-hour start |
| Midday | 12:00 through 14:00, bounded by final-hour start |
| Afternoon | 14:00 through final-hour start |
| Final hour | First 30 minutes of the final hour: close minus 60 minutes through close minus 30 minutes |
| Close | Final 30 minutes before the actual regular close |
| After-hours | Regular close inclusive to 20:00 exclusive |
| Closed | Outside configured extended hours, weekends, or injected holidays |

The regular session is 09:30–16:00 unless the date has an injected early close. `opening_phase` defaults to the first 60 minutes. The final hour is intentionally split into mutually exclusive `final_hour` and `close` segments so consumers can compare the first and second halves. These boundaries are calculated from the actual normal or injected early close. Earlier phases collapse safely rather than overlapping when a close moves earlier.

For example, an injected 13:00 close produces:

- opening phase: 09:30–10:30;
- morning: 10:30–12:00;
- no midday segment;
- no afternoon segment;
- final hour: 12:00–12:30;
- close: 12:30–13:00;
- after-hours: 13:00–20:00.

A normal session expects 78 finalized 5-minute regular-session bars or 26 finalized 15-minute bars. A 13:00 early close expects 42 or 14 respectively. Expected-bar calculations count only intervals completed through the injected observation time.

Extended-hours bars are assigned phases when present. Their completeness is deliberately not inferred because the input does not declare a requested extended-hours coverage window.

## Analytical methods

### Phase aggregates

Every phase record exposes observed and expected bar counts, coverage where assessable, OHLC, return, volume, range in points and as a percentage of the phase open, direction, a volatility proxy, close location, a close-location band, explicit completeness, and limitations.

- Direction is `up`, `down`, or `flat` from phase open to phase close; an empty phase is `unavailable`.
- The volatility proxy is the root mean square of close-to-close percentage returns within the phase. It is unavailable with fewer than two finalized bars and is not realized or implied volatility.
- Close location is `(close - low) / (high - low)` and uses the same lower-quartile, middle-half, and upper-quartile bands as session structure. It is undefined for a zero-range or empty phase.
- Regular phases are `complete`, `partial`, or `missing` against expected intervals completed at the observation boundary. Extended-hours completeness is `unassessed` because the input has no requested extended-hours coverage window.

These aggregates are descriptive. They do not infer breadth, leadership, cross-asset confirmation, or institutional activity.

### Session structure

Structure uses finalized regular-session bars only:

- **Open:** first eligible regular bar open.
- **High/low:** extrema across eligible regular bars, with their timestamps.
- **Close:** last eligible regular bar close.
- **Gap:** percentage difference between the regular open and a supplied prior close. It is unavailable when the prior close is absent.
- **Range:** high minus low, plus range as a percentage of the open.
- **Close location:** `(close - low) / (high - low)`. At or above 0.75 is the upper quartile, at or below 0.25 is the lower quartile, and the rest is the middle half. A zero range is undefined.
- **Directional efficiency:** absolute first-to-last close movement divided by total close-to-close path distance.
- **Trend:** up or down requires at least a 0.25% open-to-last-close move and directional efficiency of at least 0.45; otherwise the result is `sideways_or_mixed`.
- **Reversal:** a bullish reversal requires at least a 0.30% downside excursion, a close above the open, and close location at or above 0.65. The bearish test is symmetric with an upside excursion, close below the open, and close location at or below 0.35.

These are fixed descriptive tests, not predictions.

### Conservative turning points

Turning points use finalized regular-session closes only. A candidate must be a strict peak or trough within a five-bar window with two bars on each side. Both adjacent legs must move at least 0.30%; the stored magnitude is the smaller leg. Endpoints are never eligible, candidates fewer than four bars apart compete by magnitude, and at most the six strongest records are retained in timeline order.

Each record includes a stable ID, peak/trough kind, timestamp, phase, price, all five supporting bar timestamps and closes, movement magnitude, source-bound evidence IDs, confidence, and explicit limitations. Test or constrained inputs remain `limited`; a non-test live, delayed, or cached source can reach `moderate` only when the smaller leg is at least 0.75%. The result is descriptive and does not predict a reversal or continuation.

### Source-backed level tests

Support and resistance tests operate only on supplied `ReferenceLevel` values with a source ID and aware as-of time. A result records whether the level was touched, breached intrabar, and crossed by the last eligible close.

Statuses are:

- `not_tested`
- `tested_held`
- `rejected`
- `unconfirmed_break`
- `confirmed_break`

A confirmed resistance or support break requires a close beyond the level and matching volume-path confirmation. Without that supported volume confirmation, a closing break remains unconfirmed.

### Session VWAP and deviation

The VWAP calculation uses only eligible regular-session volume:

1. When every volume-bearing bar has provider-reported aggregate bar VWAP, those bar VWAP values are volume-weighted into session VWAP.
2. When no reported bar VWAP exists, the engine volume-weights `(high + low + close) / 3` and labels the result `ohlc_typical_price_proxy`.
3. Mixed availability produces `mixed_reported_and_proxy` and reports the share of volume covered by provider VWAP.
4. Zero eligible volume makes VWAP unavailable.

The result includes last-close deviation from the calculated measure and an above, below, or at relation. Proxy and mixed results explicitly state that they are not a uniform transaction-level VWAP.

### Volume pace, profile, and confirmation

Observed volume is aggregated by regular-session phase. Phase shares describe the observed eligible volume distribution.

Volume pace is available only with a `VolumeBaseline` containing:

- expected full-session volume;
- source ID and as-of time;
- a monotonic cumulative intraday profile for partial-session comparisons.

The engine linearly interpolates the expected cumulative fraction between supplied profile points. A completed session uses 100% of expected full-session volume. Observed volume is then divided by expected volume through the observation boundary:

- greater than 1.10: `above_expected`;
- less than 0.90: `below_expected`;
- otherwise: `in_line`.

Above-expected volume can confirm an upward or downward deterministic price path. Below-expected volume produces explicit nonconfirmation for a directional path. A sideways path remains neutral. Without the required baseline/profile, pace and confirmation are unavailable.

This analysis describes bar volume relative to a supplied historical baseline. It does not measure order flow or identify institutional buying or selling.

### Catalyst timeline hooks

`CatalystEvent` supplies an event ID, sourced headline, category, source ID, affected entities, event status, optional 0–100 materiality, aware event/publication timestamps, and a bounded 5–120 minute observation window. Event IDs must be unique within the input. Events not yet published at the injected `observed_at` boundary are excluded.

The engine assigns the event to a session phase and may report the nearest eligible price from a finalized bar closing before the event and the last eligible post-event bar whose interval closes inside the requested window. The result preserves the exact reaction-window start/end, requested minutes, and eligible bar starts. It also preserves affected entities, event status, materiality, attribution confidence, and attribution limitations. Attribution is at most `limited`; it is `unavailable` when the response cannot be calculated or the event is retracted, disputed, or unverified. Any resulting percentage is an observed temporal response only. The event headline remains sourced metadata and is not converted into an explanation.

Every catalyst item states:

> Temporal proximity does not establish causality.

The narrative-level disclosure further states that the domain does not assert that an event caused a price or volume move.

## Quality, evidence, contradictions, and confidence

### Coverage and freshness

Regular-session coverage compares distinct eligible bar starts with expected completed bar starts. Missing intervals, bars outside configured hours, and unfinished bars are recorded explicitly. A session is complete only after its regular close with near-complete eligible coverage.

`FreshnessAvailabilityEngine` receives the injected current time, source state, provider, generated/observed timestamps, session date, configured staleness threshold, test-data state, and calculated completeness. Its normalized freshness and availability are copied into `SessionQuality` and emitted as evidence.

### Evidence validation

`EvidenceValidationEngine` is used to:

- validate source timestamp and market-date lineage;
- generate stable, source-bound evidence identities;
- deduplicate evidence deterministically with first-win semantics.

Evidence covers regular-session coverage, source freshness, range, close location, trend, gap when available, reversal when present, VWAP deviation, volume pace, level tests, turning points, catalyst timing, and missing intervals.

For `available` and `partial` narratives, every claim must carry at least one evidence ID, and every referenced ID must exist in the narrative's nested evidence set. Duplicate nested evidence IDs and duplicate IDs within a claim are rejected. This cross-field validator prevents prose from escaping the engine's source lineage.

### Contradiction preservation

`ContradictionEngine` classifies supporting, opposing, and neutral evidence. The session engine also creates explicit contradiction evidence for mechanically opposing observations, including examples such as:

- an upward path with a lower-quartile last close;
- a downward path with an upper-quartile last close;
- an upward path whose last close is below the calculated VWAP measure;
- a directional path not confirmed by the supplied volume baseline.

Contradictions remain in the evidence set and are not silently averaged away.

### Confidence

`ConfidenceAdjustmentEngine` receives validated evidence depth, freshness, missing bars, unavailable analytical dimensions, test state, and contradiction count. Its result includes the final label, maximum allowed label, constrained state, and every rule contribution.

The shared Stage 7.5 policy caps stale, partial, mixed, test, unavailable, fallback, missing-evidence, or unsupported-dimension results at `limited`. A sufficiently complete, current, source-backed result can reach `moderate`; the session domain does not manufacture `high` confidence.

## Stage 7.5 shared-engine reuse

The domain calls the existing engines directly rather than reimplementing their rules:

- `freshness-availability-v1`
- `evidence-validation-v1`
- `contradiction-preservation-v1`
- `confidence-adjustment-v1`

Their version identifiers are retained in the session result so downstream consumers can audit which shared rules produced freshness, contradiction, and confidence conclusions.

## Relationship to the rest of Stage 8

Session Narrative is a typed intelligence service beneath the existing Stage 7 agent layer, not a duplicate agent. Market Overview can consume the SPY market route, while Copilot can call the symbol route for explicit session-analysis intents. The service does not fetch news: only caller-supplied, validated catalyst events enter its timeline. Consumers receive the same status, provenance, evidence, limitations, and causality disclosures rather than a separate fabricated narrative path.

## Production data policy

`ProductionSessionDataAdapter` is an honest capability adapter, not a data fetcher.

- Eligible configured daily history returns `data_mode=daily_only`, `status=daily_only`, and no intraday claims.
- No eligible source returns `data_mode=unavailable` and `status=unavailable`.
- A mock, fixture, or generated-test provider returns unavailable, sets `test_data_detected=true`, and clears daily source ID/latest-session provenance.
- Daily candles are never resampled or interpolated into session bars.
- Latest daily session is carried only as provenance context; it is not used to infer phases, VWAP, volume pace, or catalyst response.
- The adapter does not perform provider reads and cannot silently fall back to mock data.

Until a real provider supplies finalized 5-minute or 15-minute OHLCV with honest provenance, production session narratives remain fail-closed.

## Known limitations

- Holidays and early closes must be injected for the requested period; there is intentionally no bundled live exchange-calendar feed.
- There is currently no production intraday provider.
- Extended-hours completeness is not assessed.
- Turning points require two finalized bars on both sides, so endpoints and still-forming pivots are intentionally omitted.
- The typical-price VWAP fallback is a proxy, not transaction-level VWAP.
- Volume pace needs a source-backed expected-volume baseline and cumulative profile.
- Level tests need explicitly supplied, source-backed levels.
- Gap needs a supplied prior close.
- Catalyst timing cannot establish causality.
- Catalyst materiality is supplied metadata, not independently scored by the session engine.
- Bar volume cannot establish order flow or institutional activity.
- The registered API routes currently return only honest `daily_only` or `unavailable` results until a production intraday provider is added.

## Verification

Run the focused session suite from `backend/`:

```bash
PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m unittest discover -s tests/stage8 -p 'test_session_*.py' -v
```

Expected implementation result: 28 tests pass.

Run the shared Stage 7.5 regression set:

```bash
PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m unittest -v \
  tests.test_stage75_shared_engines \
  tests.test_stage75_copilot_engine_adapters
```

Expected result: 15 tests pass.

Validate the session manifest separately:

```bash
jq empty app/intelligence/session_narrative/session_manifest.json
```
