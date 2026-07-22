# Report V7 Research Selection

## Deterministic candidate universe

The engine currently constructs candidates from frozen ThemeSnapshot rows, frozen SectorSnapshot rows, and saved-security snapshot rows. The schema also reserves industry group, security cluster, market divergence, and cross-asset divergence categories; those categories are not emitted until their required immutable inputs exist.

Each candidate records identity, category, direction, current/prior rank, rank change, current/change in relative strength, 1D through 1Y returns where available, breadth and change, momentum, volume, persistence, divergence, qualifying constituents, saved overlap, freshness, source quality, data completeness, evidence IDs, supported figure types, and disqualifying conditions.

Positive and negative candidates use the same weights. Direction-aware functions score the magnitude, persistence, and breadth of either confirmed strength or confirmed weakness. This permits a newly deteriorating laggard to outrank a stable leader without changing the policy weights.

## Research Priority Score

Every dimension is normalized to 0–100. A missing dimension contributes zero. The final score is:

`sum(dimension_score × fixed_weight)`

| Dimension | Weight | Rationale |
| --- | ---: | --- |
| Market significance | 15% | Rewards material rank/extreme status in the reviewed universe. |
| Leadership/weakness magnitude | 15% | Treats strong positive and strong negative evidence symmetrically. |
| Change or acceleration | 15% | Allows fresh deterioration or improvement to outrank a static extreme. |
| Persistence | 10% | Tests agreement across supported horizons and relative strength. |
| Breadth confirmation | 10% | Distinguishes broad group evidence from narrow concentration. |
| Volume confirmation | 5% | Adds confirmation when a validated comparable field exists; otherwise zero. |
| Relative divergence | 10% | Rewards separation from SPY in either supported direction. |
| User relevance | 15% | Makes relevant evidence more useful without overriding the market gates. |
| Data completeness | 3% | Modestly rewards complete research inputs. |
| Freshness | 2% | Rewards current evidence while a separate gate blocks stale/unavailable data. |

Weights sum to 100%. The user-relevance contribution is capped at 15 score points. It cannot overcome stale data, insufficient completeness, missing constituents, missing figures, or a score below the threshold.

## Personal relevance

The engine derives overlap only from explicit saved preferences and validated membership:

- High, score 100: exact saved sector/theme; at least three fresh saved securities in the group; or an individual saved security with a major supported change.
- Moderate, score 60: one or two fresh saved securities in the group, or a saved validated parent group.
- Low, score 0: no direct saved overlap.

Stale saved overlap is retained as an audit note but scores zero and cannot elevate a candidate. Saved items are described as saved, watched, or on the watchlist. The selection model does not infer holdings, cost basis, exposure, or intent.

## Materiality and evidence gates

Primary threshold: 60. Secondary threshold: 65.

A candidate is disqualified when any applicable condition is true:

- `stale_or_unavailable_subject_data`
- `data_completeness_below_60_percent`
- `fewer_than_two_supported_figures`
- `fewer_than_three_qualifying_constituents` for group candidates
- `individual_security_change_not_material` for individual candidates
- `classification_unavailable`
- `neutral_without_material_divergence`
- `materiality_score_below_threshold`

An individual change is material when a supported prior classification changed, the security score changed by at least 15 points, or latest-session price change is at least 4% in magnitude.

## Ranking and tie-breaking

Candidates sort by:

1. qualified before disqualified;
2. higher Research Priority Score;
3. higher market-significance contribution;
4. higher change/acceleration contribution;
5. lexicographically stable candidate ID.

The result is independent of source row order. No randomness, scheduled topic rotation, clock-based topic choice, or language-model selection is used.

## Primary and secondary policy

The highest qualified candidate becomes the primary. A secondary note is optional and must be a qualified opposing direction, score at least 65, remain within 15 points of the primary, and be distinct enough to provide counter-evidence. If no primary qualifies, the report stores the full competing-candidate explanations and the no-focus reason but emits no empty page.

The machine-readable decision includes selected and secondary IDs, threshold, selected-because reasons, competing candidates, score differences, omitted count, user-relevance contribution, missing evidence, and freshness status. The methodology appendix presents a concise Research Focus Selection entry without exposing renderer internals.

## Fallback matrix

| Condition | Behavior |
| --- | --- |
| No candidate clears all gates | Omit focus; show the exact Executive Summary fallback once. |
| Empty watchlist | Use market significance only and omit personalization language. |
| Stale watchlist | Do not elevate; keep saved-security review non-actionable and visibly stale. |
| Partial taxonomy | Show only validated membership links; omit unsupported levels. |
| No prior report | Omit rank-change claims and state “Baseline established.” once. |
| Fewer than three reliable timeline points | Omit Market Evolution. |
| Missing breadth or volume | Score that dimension zero; select only if remaining evidence and gates qualify. |
| Fewer than two rendered research figures | Withdraw an otherwise scored selection and record the limitation. |
