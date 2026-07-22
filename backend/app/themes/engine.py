from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Iterable

from app.market_history.storage import DailyBar
from app.rotation.engine import build_rotation_series
from app.rotation.policy import INTERVAL_POLICIES
from app.semantics import advance_decline_semantics, confidence_contract, coverage_dimension
from app.themes.models import ThemeBasketBar, ThemeDefinition, ThemeMember
from app.themes.policy import THEME_PARTICIPATION_FORMULA_VERSION, THEME_SCORING_WEIGHTS, ThemePolicy, clip_score, coverage_status, representativeness, score_classification
from app.themes.presentation import format_taxonomy_label


PERFORMANCE_WINDOWS = {"1d": 1, "1w": 5, "1m": 21, "3m": 63, "6m": 126, "1y": 252}


def build_theme_row(
    definition: ThemeDefinition,
    members: list[ThemeMember],
    histories: dict[str, tuple[DailyBar, ...]],
    basket: list[ThemeBasketBar],
    benchmark: tuple[DailyBar, ...],
    *,
    source_state: str,
    policy: ThemePolicy | None = None,
) -> dict[str, Any]:
    current = policy or ThemePolicy()
    active = [member for member in members if member.active]
    market_date = basket[-1].session_date if basket else ""
    basket_history = tuple(to_daily_bar(bar) for bar in basket)
    aligned_histories = {ticker: tuple(bar for bar in values if not market_date or bar.session_date <= market_date) for ticker, values in histories.items()}
    eligible = [member for member in active if len(aligned_histories.get(member.ticker.upper(), ())) >= current.minimum_history_days]
    coverage = basket[-1].coverage_ratio if basket else 0.0
    performance = {key: pct_return(basket_history, days) for key, days in PERFORMANCE_WINDOWS.items()}
    benchmark_returns = {key: pct_return(benchmark, days) for key, days in PERFORMANCE_WINDOWS.items()}
    rs = {f"vs_spy_{key}": subtract(performance[key], benchmark_returns[key]) for key in ("1w", "1m", "3m")}
    breadth = build_breadth(eligible, aligned_histories)
    participation = build_participation(eligible, aligned_histories, current.participation_lookback_sessions)
    concentration = build_concentration(eligible, aligned_histories, current.participation_lookback_sessions)
    components = {
        "momentum": return_score(performance["1m"], performance["3m"]),
        "relative_strength": return_score(rs["vs_spy_1m"], rs["vs_spy_3m"]),
        "breadth": breadth["percent_above_ema50"],
        "participation": participation["participation_score"],
        "concentration_quality": concentration["quality_score"],
    }
    available = {key: value for key, value in components.items() if value is not None}
    total_weight = sum(THEME_SCORING_WEIGHTS[key] for key in available)
    contributions = {
        key: {
            "score": value,
            "weight": round(THEME_SCORING_WEIGHTS[key] / total_weight, 6) if value is not None and total_weight else 0.0,
            "weighted_contribution": round(value * THEME_SCORING_WEIGHTS[key] / total_weight, 4) if value is not None and total_weight else None,
        }
        for key, value in components.items()
    }
    composite = round(sum(value["weighted_contribution"] or 0 for value in contributions.values()), 2) if available else None
    classification = score_classification(components["relative_strength"], components["momentum"], components["breadth"], components["participation"])
    data_score = min(coverage, len(eligible) / len(active) if active else 0.0) * 100
    signal_values = [value for value in components.values() if value is not None]
    supportive = sum(value >= 55 for value in signal_values)
    caution = sum(value < 45 for value in signal_values)
    signal_score = 85 if len(signal_values) == 5 and (supportive >= 4 or caution >= 4) else 65 if len(signal_values) >= 4 else 40 if signal_values else None
    confidence = confidence_contract(
        data_score=data_score,
        data_reason=f"{len(eligible)}/{len(active)} active members have durable long-history eligibility; basket coverage is {coverage:.1%}.",
        signal_score=signal_score,
        signal_reason=f"{supportive} supportive, {len(signal_values) - supportive - caution} mixed, and {caution} caution score dimensions.",
    )
    rotation = {
        interval: build_rotation_series(
            entity_type="theme", entity_id=definition.theme_id, display_name=definition.display_name,
            short_label=definition.theme_id, entity_symbol=f"theme:{definition.theme_id}:{definition.version}",
            entity_history=basket_history, benchmark_symbol="SPY", benchmark_history=benchmark,
            interval=interval, source_state=source_state, data_mode="live" if source_state == "live" else "test",
            universe_id=definition.theme_id, universe_version=definition.version, coverage_ratio=coverage,
        ).model_dump()
        for interval in INTERVAL_POLICIES
    }
    warnings = ["Historical results use the current reviewed constituent basket; historical membership versions are not yet available."]
    if len(active) < 4:
        warnings.append("Representativeness is limited because fewer than four active members are available.")
    if coverage_status(coverage, current) == "partial":
        warnings.append("Coverage is partial; interpretation should remain cautious.")
    if coverage_status(coverage, current) == "unavailable":
        warnings.append("Coverage is below the live publication threshold.")
    row = {
        "theme_id": definition.theme_id,
        "display_name": definition.display_name,
        "version": definition.version,
        "definition": {
            "description": definition.description,
            "methodology": definition.methodology,
            "weighting_policy": definition.weighting_policy,
            "primary_benchmark": definition.primary_benchmark,
            "secondary_benchmark": definition.secondary_benchmark,
            "parent_sector_ids": list(definition.parent_sector_ids),
            "parent_sector_labels": [format_taxonomy_label(value) for value in definition.parent_sector_ids],
            "historical_disclosure": "Historical results use the current reviewed constituent basket unless historical membership versions are available.",
            "amends_version": definition.amends_version,
            "amendment_reason": definition.amendment_reason,
            "corporate_action_amendment": definition.corporate_action_amendment,
            "correction_metadata": definition.correction_metadata,
        },
        "member_count": len(active), "eligible_count": len(eligible), "coverage_ratio": round(coverage, 6),
        "coverage_status": coverage_status(coverage, current), "performance": performance,
        "relative_strength": {**rs, "trend": trend_label(rs["vs_spy_1m"], rs["vs_spy_3m"])},
        "breadth": breadth, "participation": participation, "concentration": concentration,
        "component_scores": components, "weighted_contributions": contributions,
        "score_semantics": {
            "score_type": "absolute_weighted_composite",
            "displayed_score_type": "absolute_weighted_composite",
            "display_label": "Absolute composite score",
            "scale": "0-100",
            "formula_version": current.scoring_formula_version,
            "component_scores": components,
            "weighted_contributions": contributions,
            "cross_sectional_percentile": None,
            "interpretation": "The score is the audited weighted sum of component scores. Rank is separate and only relative to the active reviewed pilot themes.",
        },
        "basket_methodology": {
            "policy": "daily_rebalanced_equal_weight",
            "formula_version": current.basket_formula_version,
            "weighting": "Each eligible current-basket member receives equal weight at every eligible daily rebalance.",
            "eligibility": f"A session requires consecutive valid adjusted closes and at least {definition.partial_coverage_threshold:.0%} member coverage.",
            "historical_disclosure": "Historical results use the current reviewed constituent basket unless historical membership versions are available.",
        },
        "composite_score": composite, "classification": classification,
        "data_confidence": confidence["data_confidence"], "signal_confidence": confidence["signal_confidence"],
        "representativeness": representativeness(len(eligible)), "members": member_disclosure(active, aligned_histories, current.participation_lookback_sessions),
        "rotation_series": rotation, "warnings": warnings,
        "provenance": {
            "category": "live_verified" if source_state == "live" else "test_fixture",
            "definition_status": definition.status, "source_state": source_state,
            "history_provider": "polygon", "basket_formula_version": current.basket_formula_version,
            "scoring_formula_version": current.scoring_formula_version,
            "current_basket_historical": True,
            "review_commit": definition.review_commit,
            "corporate_action_amendment": definition.corporate_action_amendment,
        },
    }
    row["input_hash"] = hashlib.sha256(json.dumps({"definition": definition.model_dump(), "members": [member.model_dump() for member in active], "basket": [bar.input_hash for bar in basket], "benchmark": [bar.session_date for bar in benchmark]}, sort_keys=True).encode()).hexdigest()
    return row


def build_overlap_matrix(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for index, left in enumerate(rows):
        left_members = {member["ticker"]: member for member in left.get("members", [])}
        for right in rows[index + 1:]:
            right_members = {member["ticker"]: member for member in right.get("members", [])}
            common = sorted(set(left_members) & set(right_members)); union = set(left_members) | set(right_members)
            jaccard = len(common) / len(union) if union else 0.0
            weighted = sum(min(float(left_members[ticker].get("weight", 0)), float(right_members[ticker].get("weight", 0))) for ticker in common)
            result.append({"left_theme_id": left["theme_id"], "right_theme_id": right["theme_id"], "common_members": common, "shared_count": len(common), "union_count": len(union), "jaccard_overlap": round(jaccard, 6), "weighted_overlap": round(weighted, 6), "classification": "high" if jaccard >= .5 else "moderate" if jaccard >= .25 else "low"})
    return result


def build_alerts(rows: list[dict[str, Any]], previous: dict[str, Any] | None, market_date: str) -> list[dict[str, Any]]:
    prior = {row.get("theme_id"): row for row in (previous or {}).get("rows", [])}
    alerts: list[dict[str, Any]] = []
    for row in rows:
        before = prior.get(row["theme_id"], {})
        if row["classification"] in {"Leading", "Improving"} and row["classification"] != before.get("classification"):
            alerts.append({"alert_id": f"{row['theme_id']}:{row['classification']}:{market_date}", "theme_id": row["theme_id"], "type": f"entered_{row['classification'].lower()}", "market_date": market_date, "source_snapshot_id": before.get("snapshot_id"), "confidence": row["signal_confidence"]["label"], "explanation": f"{row['display_name']} entered {row['classification']}.", "invalidation_condition": "A subsequent immutable ThemeSnapshot no longer supports the classification."})
    return alerts


def pct_return(bars: Iterable[Any], days: int) -> float | None:
    values = list(bars)
    if len(values) <= days or values[-days - 1].close <= 0:
        return None
    return round((values[-1].close / values[-days - 1].close - 1) * 100, 4)


def ema(values: list[float], period: int) -> float | None:
    if len(values) < period: return None
    output = sum(values[:period]) / period; alpha = 2 / (period + 1)
    for value in values[period:]: output = value * alpha + output * (1 - alpha)
    return output


def build_breadth(members: list[ThemeMember], histories: dict[str, tuple[DailyBar, ...]]) -> dict[str, Any]:
    rows = [histories.get(member.ticker.upper(), ()) for member in members]
    valid = [bars for bars in rows if len(bars) >= 2]
    advancing = sum(bars[-1].close > bars[-2].close for bars in valid); declining = sum(bars[-1].close < bars[-2].close for bars in valid); unchanged = len(valid) - advancing - declining
    def above(period: int) -> tuple[int, int]:
        values = [bars for bars in valid if len(bars) >= period]
        return sum(bars[-1].close > (ema([bar.close for bar in bars], period) or float("inf")) for bars in values), len(values)
    above20, eligible20 = above(20); above50, eligible50 = above(50); above200, eligible200 = above(200)
    high_rows = [bars for bars in valid if len(bars) >= 252]
    return {
        "advancing": advancing, "declining": declining, "unchanged": unchanged, **advance_decline_semantics(advancing, declining),
        "percent_above_ema20": percent(above20, eligible20), "percent_above_ema50": percent(above50, eligible50), "percent_above_ema200": percent(above200, eligible200),
        "new_52_week_highs": sum(bars[-1].close >= max(bar.close for bar in bars[-252:]) for bars in high_rows),
        "new_52_week_lows": sum(bars[-1].close <= min(bar.close for bar in bars[-252:]) for bars in high_rows),
        "eligible_counts": {"advance_decline": len(valid), "ema20": eligible20, "ema50": eligible50, "ema200": eligible200, "highs_lows": len(high_rows)},
        "coverage_dimensions": {"universe": coverage_dimension(len(valid), len(members)), "ema20": coverage_dimension(eligible20, len(members)), "ema50": coverage_dimension(eligible50, len(members)), "ema200": coverage_dimension(eligible200, len(members)), "highs_lows": coverage_dimension(len(high_rows), len(members))},
    }


def build_participation(members: list[ThemeMember], histories: dict[str, tuple[DailyBar, ...]], lookback: int) -> dict[str, Any]:
    returns = [(member, pct_return(histories.get(member.ticker.upper(), ()), lookback)) for member in members]
    eligible = [(member, value) for member, value in returns if value is not None]
    positive = [(member, value) for member, value in eligible if value > 0]
    denominator = sum(abs(value * member.weight) for member, value in eligible)
    positive_share = sum(value * member.weight for member, value in positive) / denominator * 100 if denominator else None
    positive_percent = percent(len(positive), len(eligible))
    score = clip_score((positive_percent or 0) * .6 + (positive_share or 0) * .4) if eligible else None
    positive_contribution_share = round(positive_share, 4) if positive_share is not None else None
    negative_count = sum(value < 0 for _, value in eligible)
    return {
        "positive_return_member_count": len(positive), "negative_return_member_count": negative_count,
        "positive_member_count": len(positive), "negative_member_count": negative_count,
        "positive_return_participation_pct": positive_percent, "positive_contribution_share_pct": positive_contribution_share,
        "positive_return_participation": positive_percent, "positive_contribution_share": positive_contribution_share,
        "participation_horizon": "1M / 21 sessions", "participation_score": score, "score_scale": "0-100",
        "selected_horizon_sessions": lookback, "formula_version": THEME_PARTICIPATION_FORMULA_VERSION,
        "definition": "60% positive-return member participation plus 40% positive absolute-contribution share; distinct from EMA50 breadth.",
    }


def build_concentration(members: list[ThemeMember], histories: dict[str, tuple[DailyBar, ...]], lookback: int) -> dict[str, Any]:
    values = [(member, pct_return(histories.get(member.ticker.upper(), ()), lookback)) for member in members]
    contributions = [(member, (value or 0) * member.weight) for member, value in values if value is not None]
    total_abs = sum(abs(value) for _, value in contributions)
    shares = sorted(((member, abs(value) / total_abs if total_abs else 0.0) for member, value in contributions), key=lambda item: item[1], reverse=True)
    top_one = shares[0][1] * 100 if shares else None; top_three = sum(share for _, share in shares[:3]) * 100 if shares else None
    hhi = sum(share * share for _, share in shares)
    label = "high" if (top_one or 0) >= 60 or hhi >= .5 else "elevated" if (top_three or 0) >= 75 or hhi >= .30 else "moderate" if hhi >= .18 else "low"
    quality = {"low": 100, "moderate": 75, "elevated": 45, "high": 20}[label]
    top_contributors = [{"ticker": member.ticker, "absolute_contribution_share_pct": round(share * 100, 4), "absolute_contribution_share": round(share * 100, 4)} for member, share in shares[:3]]
    return {
        "top_one_absolute_contribution_share_pct": round(top_one, 4) if top_one is not None else None,
        "top_three_absolute_contribution_share_pct": round(top_three, 4) if top_three is not None else None,
        "top_one_absolute_contribution_share": round(top_one, 4) if top_one is not None else None,
        "top_three_absolute_contribution_share": round(top_three, 4) if top_three is not None else None,
        "concentration_hhi": round(hhi, 6), "contribution_hhi": round(hhi, 6),
        "positive_contributor_count": sum(value > 0 for _, value in contributions), "negative_contributor_count": sum(value < 0 for _, value in contributions),
        "classification": label, "concentration_quality_score": quality, "quality_score": quality, "quality_score_scale": "0-100",
        "top_contributors": top_contributors, "denominator": "absolute contribution share",
    }


def member_disclosure(members: list[ThemeMember], histories: dict[str, tuple[DailyBar, ...]], lookback: int) -> list[dict[str, Any]]:
    return [{"ticker": member.ticker, "company_name": member.company_name, "role": member.role, "weight": member.weight, "purity": member.purity, "importance": member.importance, "inclusion_reason": member.inclusion_reason, "return_1m": pct_return(histories.get(member.ticker.upper(), ()), lookback), "previous_ticker": member.previous_ticker, "previous_company_name": member.previous_company_name, "corporate_action_type": member.corporate_action_type, "corporate_action_effective_date": member.corporate_action_effective_date, "continuity_status": member.continuity_status, "history_continuity_required": member.history_continuity_required} for member in members]


def to_daily_bar(bar: ThemeBasketBar) -> DailyBar:
    return DailyBar(ticker=f"THEME:{bar.theme_id}:{bar.theme_version}", provider="polygon", session_date=bar.session_date, timestamp=f"{bar.session_date}T00:00:00+00:00", open=bar.index_level / (1 + bar.daily_return) if bar.daily_return > -1 else bar.index_level, high=bar.index_level, low=bar.index_level, close=bar.index_level, volume=0.0, adjusted=True, quality_status="valid", source_timestamp=bar.generated_at)


def return_score(short: float | None, medium: float | None) -> float | None:
    values = [value for value in (short, medium) if value is not None]
    return clip_score(50 + sum(values) / len(values) * 5) if values else None


def trend_label(short: float | None, medium: float | None) -> str:
    if short is None or medium is None: return "Unavailable"
    return "Improving" if short >= medium and short >= 0 else "Weakening" if short < 0 and medium < 0 else "Mixed"


def subtract(left: float | None, right: float | None) -> float | None:
    return round(left - right, 4) if left is not None and right is not None else None


def percent(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator * 100, 4) if denominator else None
