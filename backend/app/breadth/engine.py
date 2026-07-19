from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from statistics import mean
from typing import Any

from app.breadth.models import BreadthCalculationInput, BreadthCalculationResult
from app.breadth.policy import WEIGHTS, BreadthPolicy, classify_score
from app.market_history.storage import DailyBar
from app.semantics import advance_decline_semantics, confidence_contract, coverage_dimension


def calculate_breadth(input_: BreadthCalculationInput, policy: BreadthPolicy | None = None) -> BreadthCalculationResult:
    """Pure calculation: all external I/O must happen before this function."""
    policy = policy or BreadthPolicy.from_environment()
    requested = {member.ticker for member in input_.members}
    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    stale: list[str] = []
    invalid: list[str] = []
    for member in input_.members:
        history = [bar for bar in input_.histories.get(member.ticker, ()) if bar.session_date <= input_.market_date]
        if not history:
            missing.append(member.ticker)
            continue
        if history[-1].session_date != input_.market_date:
            stale.append(member.ticker)
        try:
            rows.append(_member_row(member.ticker, member.sector, history, policy))
        except ValueError:
            invalid.append(member.ticker)
    core = _aggregate(rows, policy)
    coverage = _coverage(requested, rows, missing, stale, invalid, core, policy)
    score = _score(core, coverage, policy)
    classification = classify_score(score)
    trend = _trend(input_, score)
    confidence = _confidence(coverage, core)
    confidence_details = _confidence_details(coverage, core)
    warnings = list(coverage["coverage_warnings"])
    if coverage["coverage_status"] == "unavailable":
        warnings.append("Breadth is not published as a score until minimum coverage is available.")
        score = None
        classification = "unavailable"
    sectors = _sectors(rows, policy)
    input_hash = hashlib.sha256(json.dumps({"universe": input_.universe.universe_id, "market_date": input_.market_date, "histories": {ticker: [bar.session_date for bar in bars] for ticker, bars in sorted(input_.histories.items())}}, sort_keys=True).encode("utf-8")).hexdigest()[:24]
    core.update(confidence_details)
    return BreadthCalculationResult(input_.market_date, core, coverage, sectors, score, classification, trend, confidence, warnings, input_hash)


def _member_row(ticker: str, sector: str, bars: list[DailyBar], policy: BreadthPolicy) -> dict[str, Any]:
    close = bars[-1].close
    previous = bars[-2].close if len(bars) > 1 else None
    if previous is None:
        advance = None
    elif close > previous + policy.equality_tolerance:
        advance = "advancing"
    elif close < previous - policy.equality_tolerance:
        advance = "declining"
    else:
        advance = "unchanged"
    closes = [bar.close for bar in bars]
    return {"ticker": ticker, "sector": sector, "advance": advance, "above_20": _above_ema(closes, policy.ema20_min_bars), "above_50": _above_ema(closes, policy.ema50_min_bars), "above_200": _above_ema(closes, policy.ema200_min_bars), "high": _new_extreme(closes, policy.high_low_min_bars, "high", policy.equality_tolerance), "low": _new_extreme(closes, policy.high_low_min_bars, "low", policy.equality_tolerance)}


def _ema(values: list[float], span: int) -> float:
    alpha = 2 / (span + 1)
    result = values[0]
    for value in values[1:]:
        result = value * alpha + result * (1 - alpha)
    return result


def _above_ema(closes: list[float], minimum: int) -> bool | None:
    return closes[-1] > _ema(closes[-minimum:], minimum) if len(closes) >= minimum else None


def _new_extreme(closes: list[float], minimum: int, direction: str, tolerance: float) -> bool | None:
    if len(closes) < minimum:
        return None
    prior = closes[-minimum:-1]
    if not prior:
        return None
    return closes[-1] >= max(prior) - tolerance if direction == "high" else closes[-1] <= min(prior) + tolerance


def _aggregate(rows: list[dict[str, Any]], policy: BreadthPolicy) -> dict[str, Any]:
    advance_rows = [row for row in rows if row["advance"] is not None]
    advancing = sum(row["advance"] == "advancing" for row in advance_rows)
    declining = sum(row["advance"] == "declining" for row in advance_rows)
    unchanged = sum(row["advance"] == "unchanged" for row in advance_rows)
    return {
        "advancing_count": advancing,
        "declining_count": declining,
        "unchanged_count": unchanged,
        "net_advances": advancing - declining,
        **advance_decline_semantics(advancing, declining),
        "percent_advancing": _percent(advancing, len(advance_rows)),
        "percent_declining": _percent(declining, len(advance_rows)),
        "percent_above_20ema": _metric_percent(rows, "above_20"),
        "percent_above_50ema": _metric_percent(rows, "above_50"),
        "percent_above_200ema": _metric_percent(rows, "above_200"),
        "new_52_week_highs": sum(row["high"] is True for row in rows),
        "new_52_week_lows": sum(row["low"] is True for row in rows),
        "highs_minus_lows": sum(row["high"] is True for row in rows) - sum(row["low"] is True for row in rows),
        "high_low_ratio": _ratio(sum(row["high"] is True for row in rows), sum(row["low"] is True for row in rows)),
        "eligible_rows": len(rows),
    }


def _coverage(requested: set[str], rows: list[dict[str, Any]], missing: list[str], stale: list[str], invalid: list[str], core: dict[str, Any], policy: BreadthPolicy) -> dict[str, Any]:
    available = len(rows)
    ratio = available / len(requested) if requested else 0.0
    indicator_counts = {"advance_decline": sum(row["advance"] is not None for row in rows), "EMA20": sum(row["above_20"] is not None for row in rows), "EMA50": sum(row["above_50"] is not None for row in rows), "EMA200": sum(row["above_200"] is not None for row in rows), "highs_lows": sum(row["high"] is not None for row in rows)}
    indicator = {key: coverage_dimension(value, available)["ratio"] for key, value in indicator_counts.items()}
    status = "complete" if ratio >= policy.min_complete_coverage and indicator["EMA200"] >= policy.min_complete_coverage else "partial" if available else "unavailable"
    warnings = []
    if missing: warnings.append(f"{len(missing)} constituent(s) have no stored history.")
    if stale: warnings.append(f"{len(stale)} constituent(s) are not aligned to the market date.")
    if indicator["EMA200"] < policy.min_complete_coverage: warnings.append("Long-term moving-average coverage is limited.")
    if available and ratio < policy.min_partial_coverage: warnings.append("Coverage is below the score-publication threshold; partial metrics are informational only.")
    return {
        "universe_size": len(requested),
        "members_requested": len(requested),
        "members_available": available,
        "members_eligible": available,
        "members_missing": sorted(missing),
        "members_stale": sorted(stale),
        "members_invalid": sorted(invalid),
        "coverage_ratio": round(ratio, 6),
        "indicator_coverage": indicator,
        "coverage_dimensions": {
            "universe": coverage_dimension(available, len(requested)),
            "advance_decline": coverage_dimension(indicator_counts["advance_decline"], available),
            "ema20": coverage_dimension(indicator_counts["EMA20"], available),
            "ema50": coverage_dimension(indicator_counts["EMA50"], available),
            "ema200": coverage_dimension(indicator_counts["EMA200"], available),
            "highs_lows": coverage_dimension(indicator_counts["highs_lows"], available),
        },
        "coverage_status": status,
        "coverage_warnings": warnings,
    }


def _sectors(rows: list[dict[str, Any]], policy: BreadthPolicy) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows: grouped[row["sector"]].append(row)
    result = []
    for sector, sector_rows in grouped.items():
        metrics = _aggregate(sector_rows, policy)
        score = _score(metrics, {"indicator_coverage": {"EMA200": _valid_ratio(sector_rows, "above_200")}})
        result.append({"sector": sector, "member_count": len(sector_rows), "available_count": len(sector_rows), "coverage_ratio": 1.0, **metrics, "sector_breadth_score": score, "status": classify_score(score), "trend": "stable"})
    return sorted(result, key=lambda item: (item["sector_breadth_score"] is None, -(item["sector_breadth_score"] or 0), item["sector"]))


def _score(core: dict[str, Any], coverage: dict[str, Any], policy: BreadthPolicy | None = None) -> float | None:
    if "coverage_ratio" in coverage and coverage["coverage_ratio"] < (policy or BreadthPolicy()).min_partial_coverage:
        return None
    values = {"percent_above_20ema": core["percent_above_20ema"], "percent_above_50ema": core["percent_above_50ema"], "percent_above_200ema": core["percent_above_200ema"], "daily_participation": core["percent_advancing"], "leadership": _leadership_score(core)}
    valid = [(WEIGHTS[key], value) for key, value in values.items() if value is not None]
    if not valid: return None
    total = sum(weight for weight, _ in valid)
    return round(sum(weight * value for weight, value in valid) / total, 2)


def _trend(input_: BreadthCalculationInput, score: float | None) -> str:
    return "stable" if score is not None else "unavailable"


def _confidence(coverage: dict[str, Any], core: dict[str, Any]) -> str:
    if coverage["coverage_status"] == "complete": return "high"
    if coverage["coverage_status"] == "partial": return "moderate"
    return "limited"


def _confidence_details(coverage: dict[str, Any], core: dict[str, Any]) -> dict[str, dict[str, Any]]:
    dimensions = coverage.get("coverage_dimensions", {})
    universe_ratio = float((dimensions.get("universe") or {}).get("ratio", 0))
    ema200_ratio = float((dimensions.get("ema200") or {}).get("ratio", 0))
    data_score = min(universe_ratio, ema200_ratio) * 100
    values = [
        core.get("percent_above_20ema"), core.get("percent_above_50ema"), core.get("percent_above_200ema"),
        core.get("percent_advancing"), _leadership_score(core),
    ]
    values = [float(value) for value in values if value is not None]
    supportive = sum(value >= 60 for value in values)
    caution = sum(value < 40 for value in values)
    signal_score = 85 if len(values) >= 4 and (supportive == len(values) or caution == len(values)) else 65 if len(values) >= 4 else 45 if values else None
    return confidence_contract(
        data_score=data_score,
        data_reason=f"Universe coverage {universe_ratio * 100:.2f}% and EMA200 eligibility {ema200_ratio * 100:.2f}%.",
        signal_score=signal_score,
        signal_reason=f"{supportive} supportive, {len(values) - supportive - caution} mixed, and {caution} caution breadth dimensions.",
    )


def _metric_percent(rows: list[dict[str, Any]], key: str) -> float | None:
    valid = [row for row in rows if row[key] is not None]
    return _percent(sum(row[key] is True for row in valid), len(valid))


def _valid_ratio(rows: list[dict[str, Any]], key: str) -> float:
    return round(sum(row[key] is not None for row in rows) / len(rows), 6) if rows else 0.0


def _percent(value: int, total: int) -> float | None:
    return round(value * 100 / total, 4) if total else None


def _ratio(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else round(numerator / denominator, 4)


def _leadership_score(core: dict[str, Any]) -> float | None:
    highs, lows = core["new_52_week_highs"], core["new_52_week_lows"]
    return 50.0 if highs == lows == 0 else round(highs * 100 / (highs + lows), 4) if highs + lows else None
