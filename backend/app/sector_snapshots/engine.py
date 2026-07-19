from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Any

from app.market_history.storage import DailyBar
from app.securities.registry import SECTOR_BY_ID, canonical_sector_id
from app.semantics import advance_decline_semantics, confidence_contract, coverage_dimension
from app.sector_snapshots.policy import SectorPolicy


def pct_return(bars: tuple[DailyBar, ...], lookback: int) -> float | None:
    if len(bars) <= lookback or bars[-lookback - 1].close <= 0:
        return None
    return round((bars[-1].close / bars[-lookback - 1].close - 1) * 100, 3)


def ema(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    value = sum(values[:period]) / period
    multiplier = 2 / (period + 1)
    for close in values[period:]:
        value = close * multiplier + value * (1 - multiplier)
    return value


def build_sector_rows(members: tuple[Any, ...], histories: dict[str, tuple[DailyBar, ...]], etf_histories: dict[str, tuple[DailyBar, ...]], benchmark: tuple[DailyBar, ...], policy: SectorPolicy) -> tuple[list[dict[str, Any]], dict[str, Any], str]:
    by_sector: dict[str, list[Any]] = defaultdict(list)
    invalid: list[str] = []
    for member in members:
        sector_id = getattr(member, "sector_id", None) or canonical_sector_id(member.sector)
        if not sector_id:
            invalid.append(member.ticker)
        else:
            by_sector[sector_id].append(member)
    benchmark_1m = pct_return(benchmark, 21)
    benchmark_3m = pct_return(benchmark, 63)
    rows: list[dict[str, Any]] = []
    eligible_total = 0
    for sector_id, definition in SECTOR_BY_ID.items():
        sector_members = by_sector.get(sector_id, [])
        etf_bars = etf_histories.get(definition["etf_symbol"], ())
        eligible = [member for member in sector_members if len(histories.get(member.ticker, ())) >= policy.minimum_history_days]
        eligible_total += len(eligible)
        advances = declines = unchanged = above20 = above50 = above200 = highs = lows = 0
        positive_contributors: list[float] = []
        for member in eligible:
            bars = histories[member.ticker]; closes = [bar.close for bar in bars]; latest = closes[-1]; previous = closes[-2]
            if latest > previous: advances += 1
            elif latest < previous: declines += 1
            else: unchanged += 1
            above20 += int(latest > (ema(closes, 20) or latest + 1))
            above50 += int(latest > (ema(closes, 50) or latest + 1))
            above200 += int(latest > (ema(closes, 200) or latest + 1))
            window = closes[-252:]
            highs += int(len(window) == 252 and latest >= max(window))
            lows += int(len(window) == 252 and latest <= min(window))
            value = pct_return(bars, 21)
            if value is not None and value > 0: positive_contributors.append(value)
        count = len(eligible)
        breadth = round((advances / count) * 100, 2) if count else None
        etf_1d = pct_return(etf_bars, 1); etf_1m = pct_return(etf_bars, 21); etf_3m = pct_return(etf_bars, 63); etf_6m = pct_return(etf_bars, 126); etf_1y = pct_return(etf_bars, 252); etf_1w = pct_return(etf_bars, 5)
        rs_1m = round(etf_1m - benchmark_1m, 3) if etf_1m is not None and benchmark_1m is not None else None
        rs_3m = round(etf_3m - benchmark_3m, 3) if etf_3m is not None and benchmark_3m is not None else None
        momentum = policy.score_return((etf_1m or 0) * 0.6 + (etf_3m or 0) * 0.4) if etf_1m is not None and etf_3m is not None else None
        relative_strength = policy.score_return((rs_1m or 0) * 0.6 + (rs_3m or 0) * 0.4) if rs_1m is not None and rs_3m is not None else None
        breadth_score = breadth
        # Participation is intentionally a separate one-month contributor
        # measure, not a second copy of percent above EMA50.
        participation = round((len(positive_contributors) / count) * 100, 2) if count else None
        concentration = round((max(positive_contributors) / sum(positive_contributors)) * 100, 2) if len(positive_contributors) > 1 and sum(positive_contributors) else None
        participation_score = round(participation * 0.8 + (100 - min(concentration or 0, 100)) * 0.2, 2) if participation is not None else None
        component_values = {"momentum": momentum, "relative_strength": relative_strength, "breadth": breadth_score, "participation": participation_score}
        available_scores = [value for value in component_values.values() if value is not None]
        composite = round(sum(available_scores) / len(available_scores), 2) if available_scores else None
        classification = classify(relative_strength, momentum, breadth_score, participation_score)
        coverage = round(count / len(sector_members), 4) if sector_members else 0.0
        warnings = []
        if not sector_members: warnings.append("No active S&P 100 constituents are classified in this sector.")
        if len(etf_bars) < policy.minimum_history_days: warnings.append("ETF history is below the EMA200 readiness threshold.")
        if count < len(sector_members): warnings.append(f"{len(sector_members) - count} constituent(s) are ineligible because durable history is insufficient.")
        divergence = round((etf_1m or 0) - ((participation or 0) - 50) / 10, 3) if etf_1m is not None and participation is not None else None
        data_score = min(coverage, 1.0 if len(etf_bars) >= policy.minimum_history_days else 0.0) * 100
        signal_values = [value for value in component_values.values() if value is not None]
        supportive = sum(value >= 60 for value in signal_values)
        caution = sum(value < 40 for value in signal_values)
        signal_score = 85 if len(signal_values) == 4 and (supportive == 4 or caution == 4) else 65 if len(signal_values) >= 3 else 45 if signal_values else None
        confidence = confidence_contract(
            data_score=data_score,
            data_reason=f"{count}/{len(sector_members)} constituents have durable long-history eligibility and ETF history is {'ready' if len(etf_bars) >= policy.minimum_history_days else 'limited'}.",
            signal_score=signal_score,
            signal_reason=f"{supportive} supportive, {len(signal_values) - supportive - caution} mixed, and {caution} caution composite dimensions.",
        )
        component_weight = 1 / len(available_scores) if available_scores else 0.0
        component_contributions = {
            key: {"score": value, "weight": round(component_weight, 6) if value is not None else 0.0, "weighted_contribution": round(value * component_weight, 4) if value is not None else None}
            for key, value in component_values.items()
        }
        rows.append({
            "sector_id": sector_id,
            "display_name": definition["display_name"],
            "etf_symbol": definition["etf_symbol"],
            "total_members": len(sector_members),
            "eligible_members": count,
            "sample_size": count,
            **representativeness(count),
            "coverage_ratio": coverage,
            "coverage_dimensions": {
                "constituents": coverage_dimension(count, len(sector_members)),
                "ema20": coverage_dimension(count, len(sector_members)),
                "ema50": coverage_dimension(count, len(sector_members)),
                "ema200": coverage_dimension(count, len(sector_members)),
                "highs_lows": coverage_dimension(count, len(sector_members)),
            },
            "price_metrics": {"return_1d": etf_1d, "return_1w": etf_1w, "return_1m": etf_1m, "return_3m": etf_3m, "return_6m": etf_6m, "return_1y": etf_1y, "ema20": ema([bar.close for bar in etf_bars], 20), "ema50": ema([bar.close for bar in etf_bars], 50), "ema200": ema([bar.close for bar in etf_bars], 200)},
            "relative_strength_metrics": {"vs_spy_1m": rs_1m, "vs_spy_3m": rs_3m},
            "breadth_metrics": {"advancing": advances, "declining": declines, "unchanged": unchanged, **advance_decline_semantics(advances, declines), "percent_above_ema20": round(above20 / count * 100, 2) if count else None, "percent_above_ema50": round(above50 / count * 100, 2) if count else None, "percent_above_ema200": round(above200 / count * 100, 2) if count else None, "new_52_week_highs": highs, "new_52_week_lows": lows},
            "participation_metrics": {"positive_contributor_percent": participation, "top_contributor_concentration": concentration, "breadth_etf_divergence": divergence, "quality": "broad" if participation is not None and participation >= 60 else "narrow" if participation is not None and participation < 40 else "mixed", "definition": "Percent of eligible constituents with a positive 21-session return.", "lookback_sessions": 21, "is_distinct_from_ema50": True},
            "component_scores": component_values,
            "composite_audit": {"formula": "equal_weight_mean_of_available_component_scores", "formula_version": "sector-composite-v1", "contributions": component_contributions, "total_weight": round(sum(item["weight"] for item in component_contributions.values()), 6), "weighted_total": round(sum(item["weighted_contribution"] or 0 for item in component_contributions.values()), 4)},
            "composite_score": composite,
            "classification": classification,
            "confidence": confidence["data_confidence"]["label"].lower(),
            **confidence,
            "explanation": explanation(classification, rs_1m, etf_1m, participation),
            "warnings": warnings,
            "provenance": {"constituent_provider": "polygon", "etf_provider": "polygon", "benchmark": "SPY", "universe_scope": "S&P 100"},
        })
    coverage = {"total_members": len(members), "eligible_members": eligible_total, "constituent_coverage_ratio": round(eligible_total / len(members), 4) if members else 0.0, "coverage_dimensions": {"universe": coverage_dimension(eligible_total, len(members)), "ema20": coverage_dimension(eligible_total, len(members)), "ema50": coverage_dimension(eligible_total, len(members)), "ema200": coverage_dimension(eligible_total, len(members)), "highs_lows": coverage_dimension(eligible_total, len(members))}, "classified_members": sum(len(value) for value in by_sector.values()), "invalid_classifications": invalid, "required_etfs": [definition["etf_symbol"] for definition in SECTOR_BY_ID.values()], "ready_etfs": [symbol for symbol, bars in etf_histories.items() if len(bars) >= policy.minimum_history_days], "etf_coverage_ratio": round(sum(len(bars) >= policy.minimum_history_days for bars in etf_histories.values()) / len(SECTOR_BY_ID), 4)}
    input_hash = hashlib.sha256(json.dumps({"calculation_version": "sector-snapshot-v2", "members": [(member.ticker, getattr(member, "sector_id", None) or member.sector) for member in members], "histories": {key: len(value) for key, value in histories.items()}, "etfs": {key: len(value) for key, value in etf_histories.items()}}, sort_keys=True).encode()).hexdigest()
    return rows, coverage, input_hash


def representativeness(sample_size: int) -> dict[str, str]:
    if sample_size >= 10:
        return {"sample_size_band": "high", "breadth_representativeness": "High", "representativeness_reason": f"{sample_size} eligible constituents meet the documented 10-member high-representativeness threshold.", "breadth_confidence": "High"}
    if sample_size >= 4:
        return {"sample_size_band": "moderate", "breadth_representativeness": "Moderate", "representativeness_reason": f"{sample_size} eligible constituents meet the documented 4-member moderate-representativeness threshold.", "breadth_confidence": "Moderate"}
    return {"sample_size_band": "limited", "breadth_representativeness": "Limited", "representativeness_reason": f"Only {sample_size} eligible constituent{'s' if sample_size != 1 else ''}; breadth is not as representative as a broad sector sample.", "breadth_confidence": "Limited"}


def classify(rs: float | None, momentum: float | None, breadth: float | None, participation: float | None) -> str:
    if None in (rs, momentum, breadth, participation): return "Unavailable"
    if rs >= 55 and momentum >= 55 and breadth >= 55 and participation >= 55: return "Leading"
    if rs >= 50 and (breadth >= 55 or momentum >= 55): return "Improving"
    if rs <= 45 and momentum <= 45 and (breadth <= 45 or participation <= 45): return "Lagging"
    if momentum <= 45 or breadth <= 45: return "Weakening"
    return "Neutral"


def explanation(classification: str, rs: float | None, return_1m: float | None, participation: float | None) -> str:
    if classification == "Unavailable": return "Durable ETF or constituent history is not yet sufficient."
    return f"{classification}: ETF 1-month return {return_1m if return_1m is not None else 'n/a'}%, relative strength {rs if rs is not None else 'n/a'}, participation {participation if participation is not None else 'n/a'}%."
