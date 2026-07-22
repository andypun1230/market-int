# Stage 7.5 shared analysis engine audit

Audit date: 2026-07-22

Repository root: `/Users/andypun/Downloads/market-intelligence-app`

## Executive finding

Stage 7.5 now has four implemented cross-cutting engines under
`backend/app/analysis_engines/`:

1. freshness and availability;
2. evidence validation;
3. contradiction analysis and preservation; and
4. confidence adjustment.

Those four engines are pure, versioned, presentation-independent calculators.
The active Institutional Copilot consumes them through direct calls and the
adapters in `backend/app/copilot/engine_adapters.py`. Compatibility functions
in `backend/app/copilot/sources.py` now delegate to the freshness engine, so
the extraction did not require a public Copilot contract change.

The stock snapshot path also now has a behavior-preserving per-build
computation DAG in `backend/app/stock_snapshots/builder.py`. It memoizes both
successful section values and failures, and composite sections reuse the
already-computed support/resistance, trend, volume, risk, relative-strength,
pattern, rating, and signal results. This is an orchestration optimization,
not a new analysis engine: it does not add a trend, relative-strength, volume,
pattern, support/resistance, or risk formula to `app.analysis_engines`.

The remaining market-domain calculators are not one interchangeable family.
Some code is behaviorally equivalent and ready for a pure input/output kernel,
especially stock volume and support/resistance. Other code shares vocabulary
but intentionally uses different horizons, denominators, normalization,
eligibility, or evidence. Those domains must be standardized or kept separate
rather than consolidated by name alone.

## Decision summary

| Candidate | Current state | Recommendation | Extraction risk | Decision basis |
|---|---|---|---|---|
| Freshness / availability | Shared engine implemented and wired into active Copilot | **extract-now — completed** | Low inside Copilot; high if confused with snapshot lifecycle policy | The prior Copilot implementations were equivalent normalization and aggregation rules. Snapshot TTL, publication, and stale-while-revalidate behavior remain separate. |
| Evidence validation | Shared engine implemented and wired into active Copilot | **extract-now — completed** | Medium | De-duplication, source identity, claim binding, and breakout evidence checks were pure. Metric and entity matching remain deliberately heuristic and fail-closed. |
| Contradiction | Shared engine implemented and wired into active Copilot | **extract-now — completed** | Medium | Explicit contradiction flags, lexical polarity, support/opposition ordering, and preservation checks had one Stage 7 meaning. This is not a general logical contradiction solver. |
| Confidence | Shared engine implemented and wired into active Copilot | **extract-now — completed** | Medium | Stage 7 categorical confidence caps were equivalent across reasoning and validation. Numeric market, breadth, sector, theme, and report confidence scores are different domains. |
| Trend | Several distinct calculators remain | **standardize-first** | High | Trendline geometry, EMA regime, multi-timeframe factor scoring, breadth trend, and theme return trend are different analytical claims. |
| Relative strength | Stock, sector, theme, rotation, and report ratio implementations remain | **leave-domain-specific** | High | All compare performance, but they use different benchmarks, horizons, arithmetic, scoring, normalization, and membership semantics. Share time-series primitives, not one score. |
| Volume | Stock calculator and snapshot composition use the same rules; other volume domains differ | **extract-now** | Low to medium | The stock OHLCV kernel is behaviorally equivalent and already shares helper functions. Report volume, institutional days, and trade-print analysis must remain separate consumers. |
| Support / resistance | Stock service and stock snapshot use the same primitives and thresholds | **extract-now** | Low to medium | A pure candle-to-zones kernel can remove duplicate orchestration while preserving provider and snapshot adapters. |
| Patterns | Symbol-specific synthetic pattern service remains | **defer** | Very high | Most current detections are fixture-shaped, pattern levels are explicitly treated as mock dependencies, and volume confirmation can combine a synthetic chart with provider-backed volume. |
| Risk | Stock trade-plan and market risk systems remain distinct; even the two stock paths differ in level priority | **standardize-first** | High | Entry/stop dependency priority must be reconciled before extraction. Market risk dashboards are not stock trade-plan calculators. |
| Time-series | EMA, return, alignment, sampling, and rolling-series utilities are duplicated with material differences | **standardize-first** | High | Seed choice, rounding, missing-value behavior, lookback indexing, adjusted-bar eligibility, and date alignment are observable semantics. |
| Data completeness / entity binding | Claim binding is extracted; completeness and entity resolution remain distributed | **standardize-first** | High | Completeness requires a declared universe, denominator, eligibility policy, and market date. Entity resolution requires registry and conversation context; only evidence-to-claim binding is currently pure. |

The recommendation labels mean:

- **extract-now**: a pure calculator can be introduced without choosing a new
  formula; adapters preserve existing I/O and payloads.
- **standardize-first**: define canonical inputs, units, horizons, missing-data
  semantics, and versioning before moving code.
- **leave-domain-specific**: retain separate scoring or interpretation because
  the analytical questions are intentionally different, while allowing lower-
  level utilities to be shared.
- **defer**: current evidence or implementation maturity is insufficient for a
  production shared engine.

## Implemented Stage 7.5 baseline

### Shared package topology

The implemented package is deliberately independent of API, UI, report
rendering, provider selection, and Copilot orchestration:

- `backend/app/analysis_engines/freshness/engine.py`
  (`freshness-availability-v1`)
- `backend/app/analysis_engines/evidence_validation/engine.py`
  (`evidence-validation-v1`)
- `backend/app/analysis_engines/contradiction/engine.py`
  (`contradiction-preservation-v1`)
- `backend/app/analysis_engines/confidence/engine.py`
  (`confidence-adjustment-v1`)
- `backend/app/analysis_engines/__init__.py`
  (`stage75-analysis-engines-v1` package marker)

`backend/app/copilot/engine_adapters.py` maps the engine results back into the
stable Pydantic Copilot contracts. The focused behavioral coverage is in
`backend/tests/test_stage75_shared_engines.py`.

### Stock snapshot computation DAG

`StockAnalysisSnapshotBuilder._build_sections` now instantiates
`_StockSectionComputation` in
`backend/app/stock_snapshots/builder.py`. Its named nodes are:

- chart;
- technical;
- support/resistance;
- trend;
- volume;
- risk;
- relative strength;
- pattern;
- rating;
- signals;
- leadership;
- executive summary; and
- overall assessment.

The composite nodes call private dependency-aware helpers. The standalone
public builders keep their existing signatures and continue to assemble their
own dependencies when called outside the snapshot DAG. A cached exception is
re-raised to dependents, so one failing leaf is attempted once, sections that
depend on it become unavailable, and unrelated sections can still complete.

`backend/tests/test_stage7_5_stock_snapshot_dag.py` checks all thirteen
analysis calls execute exactly once, compares every DAG payload with the
standalone composition under a frozen clock, and checks failed-pattern
locality. The DAG applies only to `StockAnalysisSnapshot` construction. It
does not change the separate legacy aggregator in
`backend/app/services/stock_analysis_aggregate.py`.

## Candidate audit

### 1. Freshness and availability

**Existing paths and consumers**

- The shared implementation is
  `backend/app/analysis_engines/freshness/engine.py`:
  `FreshnessAvailabilityEngine.evaluate`, `summarize`,
  `state_from_source`, `normalize_source_state`, `aggregate_states`,
  `is_expired`, and `parse_datetime`.
- `backend/app/copilot/engine_adapters.py` exposes
  `CopilotFreshnessAdapter.evaluate` and `aggregate_states`.
- `backend/app/copilot/agents.py` uses the adapter in `_freshness` and
  `_merge_freshness` for eleven source-backed agents. Watchlist, navigation,
  educational, and portfolio retain contract-specific freshness construction
  and pass through the shared downstream validator.
- `backend/app/copilot/sources.py` retains the compatibility functions
  `normalize_source_state`, `aggregate_source_states`, `is_expired`,
  `freshness_state`, and `parse_datetime`; each delegates to the shared
  engine.
- `backend/app/copilot/collector.py:_freshness_summary` uses
  `FreshnessAvailabilityEngine.summarize` to create the bundle summary.
- `backend/app/copilot/reasoning.py`,
  `backend/app/copilot/validation.py`, and
  `backend/app/copilot/agent_contracts.py` normalize the summary state before
  applying confidence constraints.
- Market and stock snapshot lifecycle code remains outside this engine in
  `backend/app/snapshots/` and `backend/app/stock_snapshots/`. Provider state
  is still authored in `backend/app/providers/models.py` and
  `backend/app/services/market_data_repository.py`.

**Equivalence and differences**

The extracted Copilot rules are behaviorally equivalent to the former local
implementations: test data wins, expired or provider-stale data is stale,
initializing is unavailable, partial remains partial, mixed current sources
aggregate conservatively, and unavailable plus current becomes partial.
Completeness is clamped to `[0, 1]`, warnings are stable first-win
de-duplicated, and an injectable clock makes age tests deterministic.

This engine does not own snapshot publication, TTL selection, durable storage,
last-known-good fallback, refresh de-duplication, or stale-while-revalidate.
It also does not yet use the retained
`expected_update_frequency_seconds` or `market_session_context` fields to
alter staleness thresholds. Those are facts on the input contract, not an
implemented calendar-aware formula.

**Evidence dependencies**

The engine needs source state, provider status, generated and observed
timestamps, optional expiry, a caller-selected stale threshold, completeness,
provider label, test/fallback/mixed flags, warnings, and optionally an injected
UTC clock. It does not fetch data or infer a market calendar.

**Extraction risk**

Low for the completed Copilot normalization. Risk becomes high if callers
attempt to replace snapshot lifecycle or provider health policy with this
normalizer, because those systems make persistence and refresh decisions that
the engine intentionally does not make.

**Recommendation: extract-now — completed.** Keep snapshot lifecycle policy
domain-specific. A later calendar-aware extension needs explicit exchange,
session, expected-frequency, and holiday inputs plus a new engine version.

### 2. Evidence validation

**Existing paths and consumers**

- The shared implementation is
  `backend/app/analysis_engines/evidence_validation/engine.py`:
  `deduplicate`, `validate_claim_binding`,
  `validate_breakout_confirmation`, `claims_semantically_compatible`, source
  identity/timestamp validation, metric-family classification, scalar numeric
  parsing, and canonical fingerprints.
- `backend/app/copilot/engine_adapters.py` provides first-win evidence
  de-duplication for `CopilotEvidenceV1`.
- `backend/app/copilot/agents.py:_dedupe_agent_evidence`,
  `backend/app/copilot/collector.py:_dedupe_evidence`, and
  `backend/app/copilot/agent_contracts.py:validate_agent_result` consume the
  shared identity rule.
- `backend/app/copilot/validation.py` uses the engine for source lineage
  identity, timestamp/date syntax, same-entity breakout confirmation,
  evidence-to-claim entity/metric/unit binding, metric families, and semantic
  compatibility between claim fragments.
- `backend/app/copilot/entities.py` and `backend/app/copilot/intent.py` still
  resolve user entities before validation; the evidence engine does not query
  registries.

**Equivalence and differences**

De-duplication is stable and first-win. The engine additionally reports the
count of duplicates and fingerprints conflicting duplicates, although the
simple Copilot adapter returns only the retained items. Claim binding matches
explicit entity keys, a finite vocabulary of metric families, percent and
currency clues, optional timeframes, and evidence suitability. Breakout
confirmation requires a current price above a trigger plus supportive volume
for the same entity.

This is validation of structured support, not validation that a market value
is economically true. Source timestamp validation is syntactic; it does not
check future time, exchange sessions, or whether two sources observed the same
underlying event. The engine supports explicit claim and evidence timeframes,
but the current `_evidence_matches_claim` adapter passes only the evidence
timeframe. With no parsed claim timeframe, the period check remains permissive
on that path. Metric-family matching is lexical and does not replace a metric
ontology.

**Evidence dependencies**

The strongest path needs stable evidence/source IDs, canonical entity keys,
metric name, unit, scalar value or current state, interpretation class,
quarantine state, timeframe, provider, dataset, generated timestamp, market
date, and raw immutable-engine reference. Breakout checks additionally need
price, trigger/resistance, and volume evidence keyed to the same security.

**Extraction risk**

Medium. The pure rules are safe, but widening the metric vocabulary or entity
matching can create false support. Quietly treating unknown metrics or aliases
as compatible would be more dangerous than leaving a claim unsupported.

**Recommendation: extract-now — completed.** Preserve fail-closed behavior.
Before applying this engine beyond Copilot, standardize canonical metric IDs,
unit IDs, entity IDs, and explicit claim periods rather than adding more prose
patterns.

### 3. Contradiction

**Existing paths and consumers**

- The shared implementation is
  `backend/app/analysis_engines/contradiction/engine.py`:
  `ContradictionEngine.analyze`, `validate_preservation`,
  `is_explicit_contradiction`, and `polarity`.
- `backend/app/copilot/collector.py` uses the explicit contradiction predicate
  when populating `contradictory_evidence_ids`.
- `backend/app/copilot/reasoning.py` maps evidence to
  `ContradictionFinding`, then uses `analyze` to select ordered supporting and
  opposing evidence. Watchlist cautions and research-selection priority are
  supplied as structured flags.
- `backend/app/copilot/validation.py` uses `validate_preservation` to require
  contradictory evidence in challenge/risk reasoning or an explicit
  truncation disclosure. A deterministic no-claim fallback is treated as
  valid without pretending it preserved a thesis it did not make.

**Equivalence and differences**

The engine preserves prior Stage 7 behavior: explicit contradiction metadata
wins; watchlist caution is opposing; otherwise a bounded positive/negative
lexicon supplies polarity. Declared support can restrict the supporting set,
and research-selection evidence can be ordered first. Preservation checks
whether the expected contradiction IDs were cited and whether omitted IDs were
disclosed.

It does not compare two numeric observations, resolve unit conversions,
establish temporal inconsistency, or prove logical negation. A statement that
contains both positive and negative terms is neutral unless structured
metadata makes it opposing. Contradiction IDs still originate in the agents
and evidence bundle; the engine does not invent claim relationships.

**Evidence dependencies**

Analysis needs evidence ID, a safe textual statement, interpretation class,
explicit `contradicts_claim_ids`, optional opposing/watchlist flags, declared
support, and research-priority flags. Preservation needs expected and cited
IDs, truncation disclosure, and whether the response intentionally failed
closed without a factual claim.

**Extraction risk**

Medium. The structured path is robust; the lexical fallback is sensitive to
domain wording and should not be presented as formal contradiction detection.
Changing the term lists can alter which evidence is surfaced as risk.

**Recommendation: extract-now — completed.** Add numeric or temporal
contradiction types only as new structured contracts with explicit units,
entities, periods, and tolerances.

### 4. Confidence

**Existing paths and consumers**

- The shared implementation is
  `backend/app/analysis_engines/confidence/engine.py`:
  `ConfidenceAdjustmentEngine.adjust`, `is_constrained`, and
  `label_exceeds`.
- `backend/app/copilot/reasoning.py` uses it to assign the final categorical
  label and to determine whether a bundle is constrained.
- `backend/app/copilot/validation.py` uses the same constrained-state rule for
  high-confidence caps and stale/fallback limitation checks.
- `backend/app/copilot/agent_contracts.py` applies the rule to individual agent
  output.
- The engine consumes freshness states normalized by the shared freshness
  engine.
- Numeric confidence remains separate in
  `backend/app/semantics.py:confidence_contract`,
  `backend/app/breadth/engine.py`,
  `backend/app/sector_snapshots/engine.py`,
  `backend/app/themes/engine.py`,
  `backend/app/services/decision_confidence.py`, and report builders.

**Equivalence and differences**

For factual market answers, stale, partial, mixed, test, unavailable, fallback,
missing, unsupported, or zero-evidence input caps the result at `limited`.
Unconstrained answers with at least three validated evidence items are
`moderate`; fewer remain `limited`. Navigation and bounded educational answers
are explicitly exempt and can be `high`. Contradictions are preserved but do
not receive an undocumented numeric penalty.

This engine does not calculate market conviction, signal confidence, data
confidence, a probability, or a stock rating. The `source_quality` input is
retained but does not currently change the result. The highest factual market
label in this Stage 7 contract is `moderate`; that must not be mapped onto a
0–100 domain score without a separate formula.

**Evidence dependencies**

The engine needs intent, validated evidence count, normalized freshness state,
missing/stale/partial/unavailable/test counts, contradiction count,
unsupported-dimension count, fallback state, and the deterministic non-market
exemption.

**Extraction risk**

Medium. The completed categorical extraction is low risk, but reusing it for
domain scores would erase documented weighting, coverage, and signal-agreement
semantics.

**Recommendation: extract-now — completed** for Stage 7 answer confidence.
Leave numeric domain confidence formulas domain-specific and expose their
contributions through stable contracts rather than routing them through this
engine.

### 5. Trend

**Existing paths and consumers**

- `backend/app/services/trendline.py` detects 3-bar swing highs/lows, fits a
  line through the first and latest qualifying swing, counts 2% touches,
  projects the current line, and declares a break beyond 1%. It is consumed by
  `backend/app/api/market.py`, `backend/app/services/analysis.py`,
  `backend/app/services/stock_analysis_aggregate.py`, and
  `backend/app/services/stock_rating.py`.
- `backend/app/stock_snapshots/builder.py:build_trend_section` uses the same
  `trendline.py` primitives over the canonical input bundle and is cached once
  by `_StockSectionComputation`. Its result feeds rating and multi-timeframe
  signals.
- `backend/app/services/timeframe_signal_service.py` builds short, medium, and
  long factor sets from EMA position/slope, returns, RSI/MACD, relative
  strength, volume, support/resistance, trendline, pattern compatibility, and
  market alignment. It is consumed directly by
  `stock_analysis_aggregate.py` and through the snapshot builder.
- `backend/app/services/multi_timeframe.py` is a separate symbol-specific mock
  fixture with Weekly/Daily/4H/1H labels and scores. It is consumed by the
  legacy stock aggregate and report compatibility code; it is not equivalent
  to `MultiTimeframeTechnicalSignals`.
- `backend/app/services/market_data.py:classify_trend` classifies an index from
  price versus EMA50/EMA200.
- `backend/app/breadth/engine.py:_trend` currently reports only `stable` when a
  breadth score exists and `unavailable` otherwise.
- `backend/app/themes/engine.py:trend_label` labels 1-month/3-month relative
  returns as Improving, Weakening, Mixed, or Unavailable. Sector
  classification and rotation quadrants add still different notions of trend.

**Equivalence and differences**

The service and snapshot trendline geometry are equivalent and already share
low-level functions. The other implementations are not equivalent. A rising
price line, an EMA regime, a multi-factor technical score, a return-spread
direction, a breadth-history direction, and a rotation path answer different
questions. Horizons also differ: daily 240/450-bar trendlines, short/medium/
long signal windows, fixture Weekly-to-1H labels, and 1M/3M theme comparisons.

The snapshot DAG removes repeated computation inside one snapshot, but it does
not reconcile these meanings or introduce a canonical trend formula.

**Evidence dependencies**

Trendline geometry needs ordered OHLC candles, current close, at least two
qualifying swings, lookback/touch/break tolerances, source state, and `as_of`.
Multi-timeframe signals need a much larger evidence bundle: adjusted closes,
EMA/RSI/MACD sufficiency, support/resistance, volume, relative strength,
trendline, compatible pattern evidence, factor status, and methodology
version. Theme, breadth, and rotation trend need immutable universe/basket
identity and historical snapshots or benchmark-aligned series.

**Extraction risk**

High. A shared `trend` label would silently conflate geometry, regime,
momentum, and cross-sectional leadership. Minimum history and missing-data
behavior also differ materially.

**Recommendation: standardize-first.** Define separate named contracts such as
`TrendlineGeometry`, `MovingAverageRegime`, `MultiHorizonTechnicalSignal`, and
`RelativePerformanceTrend`. The behaviorally equivalent trendline candle
kernel can then be extracted without making it the universal Trend Engine.

### 6. Relative strength

**Existing paths and consumers**

- `backend/app/services/relative_strength.py` computes stock 5-, 20-, and
  nominal 60-day returns, compares 20-day return with SPY, QQQ, and a mapped
  sector benchmark, maps outperformance to a 0–100 midpoint-50 score, and
  weights available comparisons 40/30/30. It is consumed by
  `backend/app/api/market.py`, `backend/app/services/analysis.py`,
  `backend/app/services/stock_analysis_aggregate.py`, and
  `backend/app/services/stock_rating.py`.
- `backend/app/stock_snapshots/builder.py:build_relative_strength_section`
  uses the same service helpers and weights, but consumes the snapshot's
  canonical stock history and cached benchmark histories. The DAG supplies
  that one result to rating, signals, leadership, and overall assessment.
- `backend/app/sector_snapshots/engine.py` calculates ETF minus SPY percentage
  return over 21 and 63 sessions, combines the horizons 60/40, normalizes with
  `SectorPolicy.score_return`, and combines relative strength with momentum,
  breadth, and participation.
- `backend/app/themes/engine.py` performs the analogous calculations on a
  versioned equal-weight theme basket, but uses Theme policy weights,
  eligibility, concentration, and current-basket historical disclosure.
- `backend/app/rotation/engine.py` date-aligns valid adjusted entity and
  benchmark bars, computes relative return and the change in relative return,
  then plots both around 100 using interval-specific policies.
- `backend/app/reports/document_builder.py:_build_ratio_figure` computes a
  date-aligned adjusted-close ratio such as QQQ/SPY. It presents the ratio
  level and direction; it does not calculate the stock, sector, theme, or
  rotation score.
- Downstream readers include sector/theme dashboards, reports, Copilot agents,
  `timeframe_signal_service.py`, and `leadership_signal_service.py`, but those
  consume already-typed results rather than recomputing one shared formula.

**Equivalence and differences**

Every implementation describes relative performance, but the arithmetic is
not interchangeable. Stock RS scores the difference between percentage
returns and blends three benchmarks. Sector/theme RS uses two horizons against
SPY inside a wider composite. Rotation uses date-aligned historical return
spreads and return-spread momentum. Report figures use a price ratio. A rising
price ratio and positive difference of period returns often agree
directionally, but they are not the same value or evidence claim.

Stock `calculate_return` returns `0.0` for missing history; the
timeframe-signal return helper returns `None`; sector/theme `pct_return` also
returns `None` but rounds differently. Benchmark availability, mapping, and
weight renormalization are observable output semantics.

**Evidence dependencies**

All valid variants require positive, session-ordered prices and an explicit
lookback. Robust cross-asset variants additionally need date alignment,
adjusted/quality flags, benchmark identity, provider identity, market date,
minimum history, and missing-series policy. Sector/theme variants require
universe or basket version, member eligibility and coverage, benchmark
selection, formula/normalization version, and historical-membership
disclosure.

**Extraction risk**

High. Consolidating the scores would change published classifications,
rankings, rotation quadrants, or report evidence. Even extracting the return
function before resolving `0.0` versus `None`, rounding, and alignment would
be behavior-changing.

**Recommendation: leave-domain-specific.** Keep stock RS, sector/theme
composites, rotation, and report ratios as distinct versioned formulas. After
the time-series standardization described below, share only canonical
date-alignment and period-return primitives.

### 7. Volume

**Existing paths and consumers**

- `backend/app/services/volume_analysis.py` owns the stock OHLCV rules: prior
  20-session average volume, relative volume, 1.5x surge, 0.60x dry-up,
  close-above-prior-20-high breakout confirmation, one-day accumulation/
  distribution, five-session climax detection, quality score, labels, and
  summary.
- `backend/app/stock_snapshots/builder.py:build_volume_section` uses the same
  helper functions and output model over canonical snapshot candles. The DAG
  reuses the result in rating, signals, and leadership.
- `backend/app/services/pattern_detection.py:build_pattern` calls
  `analyze_volume` to attach `VolumeConfirmation` to a detected pattern.
- `backend/app/services/timeframe_signal_service.py`,
  `backend/app/services/stock_rating.py`,
  `backend/app/services/leadership_signal_service.py`,
  `backend/app/services/market_health.py`,
  `backend/app/services/analysis.py`, and
  `backend/app/services/stock_analysis_aggregate.py` consume the stock volume
  output. `backend/app/api/market.py` exposes the single-symbol and watchlist
  endpoints.
- `backend/app/reports/document_builder.py` independently displays daily
  volume and annotates latest volume versus a 20-session average. Its current
  calculation includes the latest observation in that average, unlike the
  stock service's prior-session denominator.
- `backend/app/services/institutional_activity.py` detects index distribution,
  accumulation, stall, churning, and follow-through days from generated index
  candles. `backend/app/services/block_trade_analysis.py` analyzes individual
  trade-print notional and relative size. These are not the stock daily-volume
  engine.

**Equivalence and differences**

The stock service and stock snapshot section are behaviorally equivalent and
already share all classification helpers; only data acquisition and model
assembly differ. The report average has a different denominator. Institutional
day logic adds price-change and prior-day-volume thresholds. Block-trade logic
uses trade prints and a median-size/notional test, not daily OHLCV.

Pattern volume confirmation currently introduces an important evidence seam:
the pattern chart is generated by the symbol-specific pattern fixture while
`analyze_volume` fetches market history. Extraction must preserve and disclose
the source of each component rather than imply they are one candle set.

**Evidence dependencies**

The stock kernel needs ordered OHLCV, current and previous sessions, the prior
20-session high and volume window, at least 25 sessions for climax logic,
source metadata, and `as_of`. A production result should carry whether volume
is raw/adjusted, the session calendar, missing/zero-volume handling, and the
exact denominator window. Institutional days and trade prints need separate
typed inputs.

**Extraction risk**

Low to medium for the stock kernel because formulas and outputs already match.
Risk is high only if report, institutional-day, or trade-print concepts are
folded into the same score.

**Recommendation: extract-now.** Move the existing stock OHLCV computation to
a pure candle-input engine with no provider calls; keep the service and
snapshot adapters and their current output contracts. Do not migrate report,
institutional activity, or block-trade formulas without a separate contract.

### 8. Support and resistance

**Existing paths and consumers**

- `backend/app/services/support_resistance.py` owns 3-bar swing detection, 1%
  level clustering, the last-30-session low/high additions, nearest support/
  resistance selection, breakout level, 1.5%-below-support stop reference,
  and EMA20/EMA50 support values.
- `backend/app/stock_snapshots/builder.py:build_support_resistance_section`
  uses those exact helper functions over the canonical snapshot history. The
  DAG supplies the one result to risk, rating, and signals.
- `backend/app/services/risk.py` consumes the standalone result after fetching
  its own history and pattern levels.
- `backend/app/services/timeframe_signal_service.py` consumes breakout,
  support, and price-position fields.
- `backend/app/services/stock_rating.py`,
  `backend/app/services/stock_analysis_aggregate.py`,
  `backend/app/services/analysis.py`, and
  `backend/app/services/report.py` consume or publish the result.
- `backend/app/api/market.py` exposes the direct symbol endpoint.

**Equivalence and differences**

The service and snapshot calculation are equivalent for the same candles and
metadata. They differ only in acquisition: the service fetches 240 daily bars
through `get_symbol_history`; the snapshot uses the selected canonical bundle,
currently planned at 450 days. A longer input can reveal older swings and
therefore can legitimately produce different zones even with the same
algorithm.

Trendline swing points are related but not equivalent. Trendline functions
retain point index/date and fit geometry; support/resistance functions retain
price levels and cluster them. Pattern key levels are authored by the pattern
service and are not calculated support/resistance.

**Evidence dependencies**

The pure calculation needs ordered high/low/close candles, current close,
lookback and clustering tolerances, the 30-session recent window, EMA input
sufficiency, symbol, source metadata, and `as_of`. The adapter must preserve
the exact requested history window because it affects eligible swings.

**Extraction risk**

Low to medium. The formula is already shared at helper level. The main risks
are changing the input window, rounding order, cluster ordering, or fallback
behavior while moving orchestration.

**Recommendation: extract-now.** Introduce a pure candle-to-
`SupportResistanceResponse` kernel and keep provider and snapshot acquisition
outside it. Golden tests must cover identical candles, no-candle behavior,
cluster ordering, and the 240-versus-450-day adapter distinction.

### 9. Patterns

**Existing paths and consumers**

- `backend/app/services/pattern_detection.py` generates symbol-specific 60-bar
  synthetic candles for MU, NVDA, ARM, and SNDK. It detects a double bottom,
  bull flag, tight consolidation, or bullish engulfing setup and authors fixed
  pattern IDs, descriptions, markers, and key levels.
- `build_pattern` calls `backend/app/services/volume_analysis.py:analyze_volume`
  for volume confirmation.
- `backend/app/api/market.py`,
  `backend/app/services/analysis.py`, and
  `backend/app/services/stock_analysis_aggregate.py` expose the pattern
  result.
- `backend/app/services/risk.py:_first_pattern_levels` prioritizes the first
  pattern's breakout/neckline and stop reference. Its dependency-quality
  output explicitly identifies `pattern_levels` as mock.
- `backend/app/services/stock_rating.py` uses detected patterns for pattern
  quality in the standalone rating path.
- `backend/app/services/timeframe_signal_service.py:build_pattern_factor`
  admits only a source-compatible pattern and checks breakout proximity to
  support/resistance.
- `backend/app/stock_snapshots/builder.py:build_pattern_section` calls the same
  service once through the DAG; signals consume the cached payload.
- `backend/app/providers/mock_provider.py` also uses the pattern fixture candle
  generator.

**Equivalence and differences**

There is one pattern service, not several equivalent production detectors.
Only bullish engulfing is expressed as a generally shaped candle rule. The
double-bottom and bull-flag tests depend on fixed slices in a 60-bar fixture;
tight consolidation is emitted for ARM without a separate general detector.
The authored key levels and markers are part of the fixture behavior.

Pattern compatibility in `timeframe_signal_service.py` is validation, not
detection. Volume confirmation may be provider-backed even though the chart
and levels are synthetic. The snapshot DAG prevents repeated calls inside one
snapshot but does not make the pattern evidence live or generic.

**Evidence dependencies**

A production pattern engine would need a canonical adjusted OHLCV series,
session dates, pattern-window and tolerance definitions, breakout status,
volume computed from the same or explicitly linked series, source state,
`as_of`, formula version, and evidence-level provenance for markers and key
levels. The current implementation instead depends on symbol identity and
synthetic fixture construction.

**Extraction risk**

Very high. Packaging the current functions as a shared engine would give
fixture-shaped logic an unjustified production abstraction and could obscure
the mixed-source volume dependency.

**Recommendation: defer.** Keep the current implementation explicitly
domain/test-specific until live pattern methodologies, same-series volume
provenance, confidence calibration, and golden labeled datasets exist. The DAG
optimization is sufficient for current duplicate-call control.

### 10. Risk

**Existing paths and consumers**

- `backend/app/services/risk.py` builds a stock trade plan from ATR14,
  support/resistance, and the first pattern's breakout/neckline/stop levels. It
  calculates entry, stop, 1R/2R targets, reward percentages, risk percentage,
  volatility, risk class, position-size note, and summary.
- `backend/app/stock_snapshots/builder.py:build_risk_section` uses the same ATR,
  classification, note, summary, and target arithmetic, but its dependency-
  aware helper uses support/resistance only. It does not prioritize pattern
  key levels. The DAG reuses this result in rating and executive summary.
- `backend/app/services/stock_rating.py` maps the risk level to a risk-control
  component. `stock_analysis_aggregate.py`, `analysis.py`, `report.py`, and
  `backend/app/api/market.py` consume the standalone trade plan.
- `backend/app/services/regime.py:build_market_risk` produces a market-level
  risk response.
- `backend/app/services/risk_dashboard_v2.py` builds a separate 0–100 market
  risk score from market health, fear/greed, breadth, regime volatility, and
  institutional state. `backend/app/snapshots/builder.py` captures both market
  risk sections, and home/report/decision-intelligence readers consume them.
- `backend/app/reports/document_builder.py` records the frozen market risk
  score as evidence; it does not recompute the stock stop-distance plan.

**Equivalence and differences**

The stock paths share target arithmetic and risk classification, but their
entry/stop priority is not equivalent. The standalone service prefers pattern
breakout or neckline and pattern stop, then support/resistance. The snapshot
path uses support/resistance directly. This can change entry, stop, risk
percentage, and every downstream target.

Market risk and stock trade-plan risk are different concepts. The former is a
portfolio/market posture score; the latter is setup-specific stop distance and
reward geometry. A confidence cap is different again.

**Evidence dependencies**

The stock plan needs canonical OHLC candles, ATR period and calculation,
current price, chosen entry-level provenance, chosen stop-level provenance,
fallback ATR policy, rounding, and an explicit dependency-quality record.
Market risk needs the frozen market-health, sentiment, breadth, volatility,
and institutional inputs and their individual freshness/provenance.

**Extraction risk**

High. Extracting before reconciling pattern-level priority would bless one
stock behavior and change the other. Combining stock and market risk would be
an analytical category error.

**Recommendation: standardize-first.** Decide and version the stock level-
selection contract, including whether mock pattern levels are admissible.
After that, extract only a pure stock trade-plan calculator. Leave market risk
and its dashboard as separate domain engines.

### 11. Time-series

**Existing paths and consumers**

- `backend/app/services/technical_indicators.py` provides scalar SMA/EMA,
  RSI, ATR, and MACD. EMA is seeded with the first-period SMA and rounded to two
  decimals at the public boundary.
- `backend/app/sector_snapshots/engine.py:ema` and
  `backend/app/themes/engine.py:ema` implement nearly the same EMA recurrence
  without the same boundary rounding. `backend/app/breadth/engine.py:_ema`
  implements another local variant.
- `backend/app/reports/document_builder.py:moving_average` emits a full rolling
  SMA series. `exponential_moving_average` emits a full EMA series seeded from
  the first observation rather than an initial-period SMA. These are
  presentation evidence calculations and are observably different from the
  scalar technical-indicator EMA.
- Period returns appear in
  `backend/app/services/relative_strength.py`,
  `backend/app/services/timeframe_signal_service.py`,
  `backend/app/sector_snapshots/engine.py`,
  `backend/app/themes/engine.py`,
  `backend/app/services/basket_data.py`, and
  `backend/app/services/macro_state.py`. They differ on `None` versus `0.0`,
  rounding, input type, and horizon naming.
- `backend/app/rotation/engine.py:aligned_pairs` filters for valid adjusted
  `DailyBar` observations and aligns by session date. Its sampling and
  relative-return functions are tied to versioned interval policies.
- `backend/app/reports/document_builder.py:_build_ratio_figure` performs its
  own intersection-by-session-date. Stock relative strength currently zips
  close arrays and therefore assumes alignment rather than proving it.
- Durable time-series storage remains in `backend/app/market_history/storage.py`
  and snapshot-specific storage modules. A calculation engine must not absorb
  persistence concerns.

**Equivalence and differences**

There are reusable mathematical ideas, but no single current behavior. EMA
seed and rounding differ. Return functions disagree on missing data. Some
series require adjusted and quality-valid bars; others accept plain close
lists. Rotation needs paired session dates and policy-based historical sample
points, while report charts need all aligned display points. Snapshot chart
windows slice the last N observations and do not claim N exchange sessions.

**Evidence dependencies**

A canonical layer needs typed observations with entity, session date,
timestamp, value/unit, adjusted flag, quality state, provider, and source
timestamp. Every operation must declare sort/de-duplication policy, calendar,
alignment join, lookback indexing, minimum observations, missing/zero behavior,
seed, rounding, and formula version.

**Extraction risk**

High. A mechanically shared EMA or return helper could change published
sector/theme scores, stock indicators, rotation trails, and report figures
despite looking algebraically similar.

**Recommendation: standardize-first.** Specify canonical scalar and full-
series operations and freeze golden vectors for each current variant. Then
extract only operations whose adapters can reproduce existing results exactly;
retain explicitly versioned variants where seed or rounding is intentional.

### 12. Data completeness and entity binding

**Existing paths and consumers**

- Evidence-to-claim binding is implemented in
  `backend/app/analysis_engines/evidence_validation/engine.py` and consumed by
  `backend/app/copilot/validation.py` as described above.
- User entity resolution remains in
  `backend/app/copilot/entities.py:CopilotEntityResolver`, backed by the
  security master, canonical sector taxonomy, current ThemeSnapshot, current
  ReportDocument, screen context, and active conversation entities.
  `backend/app/copilot/intent.py` converts those results into typed intent
  entities. Action validation in `backend/app/copilot/validation.py` restricts
  destinations to validated entities.
- Generic payload validation exists in
  `backend/app/validation/data_quality.py` and provider history validation in
  `backend/app/providers/history_validation.py`.
- `backend/app/semantics.py:coverage_dimension` supplies a common
  eligible/total/ratio/display shape. Breadth, sector, and theme engines use it
  but retain domain eligibility and publication thresholds.
- `backend/app/breadth/engine.py:_coverage` calculates universe and indicator-
  specific coverage, missing/stale/invalid members, and score publication
  readiness under `BreadthPolicy`.
- `backend/app/sector_snapshots/engine.py` calculates constituent and ETF
  coverage after canonical sector classification and minimum-history
  eligibility.
- `backend/app/themes/engine.py` combines active membership, basket coverage,
  per-indicator eligibility, representativeness, and Theme policy thresholds.
- `backend/app/snapshots/builder.py:build_input_coverage` distinguishes
  required and optional market inputs. The stock builder separately computes
  required stock-input plus cached-benchmark coverage.
- `backend/app/reports/document_builder.py:_completeness` counts five report
  component groups, while `_data_quality` measures observations versus an
  expected count for a specific figure. These two values have different
  denominators and purposes.

**Equivalence and differences**

Entity binding has three layers that must not be collapsed:

1. entity resolution identifies a registered security, index, sector, theme,
   report section, or contextual reference;
2. evidence binding checks that a factual claim is supported by evidence for
   a compatible entity, metric, unit, and period; and
3. action binding prevents navigation or mutation targets outside the
   validated intent.

Only the second layer is currently a pure shared engine. Resolution requires
live application registries and conversation context. Action binding requires
the destination registry and policy.

Likewise, completeness is not one percentage. `4/5` report component groups,
`90/100` universe members, `8/11` sector constituents, `20/20` EMA-eligible
members, and `2/3` cached benchmarks are different evidence claims. The common
shape in `coverage_dimension` does not make their denominators equivalent.

**Evidence dependencies**

Completeness requires the declared universe or requested dependency set,
version, market date, total denominator, eligible numerator, missing/stale/
invalid reasons, minimum-history and indicator-specific policy, required versus
optional status, and publication threshold. Entity resolution needs canonical
IDs, aliases, security-master and taxonomy versions, explicit user text,
screen context, and session context. Claim binding needs the structured fields
listed in the evidence-validation section.

**Extraction risk**

High. A generic completeness score without denominator and eligibility
semantics would be misleading. Moving registry-backed entity resolution into a
pure engine would either introduce hidden I/O or freeze stale registry state.

**Recommendation: standardize-first.** Keep domain eligibility calculators and
registry-backed resolution in their current domains. Standardize a versioned
`CoverageAssessment` contract that always carries numerator, denominator,
eligibility rule, universe/version, market date, and reasons. Continue using
the extracted evidence engine only for claim-to-evidence binding.

## Safe next implementation sequence

1. Keep the four implemented cross-cutting engines stable and add adapters,
   not UI/report/provider dependencies, when a new consumer adopts them.
2. Extract a pure stock support/resistance kernel with golden parity for the
   service and snapshot adapters.
3. Extract a pure stock volume kernel with the prior-20-session denominator
   preserved exactly; do not fold in report, institutional-day, or trade-print
   rules.
4. Specify time-series contracts and golden vectors before touching EMA,
   return, alignment, or rolling-series code.
5. Use those contracts to clarify trendline versus EMA regime versus
   multi-horizon signal semantics.
6. Reconcile the standalone and snapshot stock risk level-priority rules before
   extracting a risk-plan kernel.
7. Keep stock, sector, theme, rotation, and report relative-strength formulas
   separately versioned.
8. Defer a shared production pattern engine until its evidence is based on
   canonical live candles with same-series volume provenance and labeled
   validation data.

## Non-claims and guardrails

- There is no implemented shared Trend Engine, Relative Strength Engine,
  Volume Engine, Pattern Engine, Support/Resistance Engine, Risk Metric Engine,
  or Time-Series Engine under `backend/app/analysis_engines/` at this audit
  point.
- The stock computation DAG is not a formula migration. It changes evaluation
  reuse inside one snapshot build and preserves standalone builder APIs and
  payload semantics.
- The four shared engines do not fetch providers, publish snapshots, render
  reports, resolve application registries, or call a model.
- The confidence engine does not replace numeric domain-confidence formulas.
- The evidence engine does not establish market truth; it validates structured
  support and lineage supplied by adapters.
- The contradiction engine does not perform general logical or causal
  inference.
- Pattern key levels remain mock-dependent in the current stock risk service
  and must not be described as live calculated levels without their existing
  dependency-quality disclosure.
