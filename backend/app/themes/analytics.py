from __future__ import annotations

import math
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from statistics import median
from typing import Any, Iterable, Sequence

from app.analysis_engines.confidence import ConfidenceAdjustmentEngine, ConfidenceAdjustmentInput
from app.analysis_engines.contradiction import ContradictionAnalysisInput, ContradictionEngine, ContradictionFinding
from app.analysis_engines.freshness import FreshnessAvailabilityEngine, FreshnessAvailabilityInput
from app.themes.launch import TAXONOMY_VERSION, ThemeRegistry, get_launch_theme_registry


THEME_ANALYTICS_VERSION = "theme-intelligence-deterministic-v1"
WINDOWS = {"1d": 1, "1w": 5, "1m": 21, "3m": 63, "6m": 126, "1y": 252}


class ThemeAnalyticsEngine:
    """Deterministic equal-weight Theme analytics over caller-supplied histories.

    The engine never fetches data.  Production repositories and hermetic tests
    supply the same input shape, which prevents a test fixture from silently
    becoming a live provider fallback.
    """

    def __init__(self, registry: ThemeRegistry | None = None) -> None:
        self.registry = registry or get_launch_theme_registry()
        self.freshness = FreshnessAvailabilityEngine()
        self.contradictions = ContradictionEngine()
        self.confidence = ConfidenceAdjustmentEngine()

    def compute(
        self,
        theme_id: str,
        histories: dict[str, Sequence[Any]],
        benchmarks: dict[str, Sequence[Any]] | None = None,
        *,
        as_of: str | None = None,
        source_state: str = "unavailable",
        generated_at: str | None = None,
        previous_snapshot: dict[str, Any] | None = None,
        test_data: bool = False,
        observed_at: str | None = None,
        required_benchmark_symbols: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        definition = self.registry.definition(theme_id)
        if definition is None or definition.status == "retired":
            raise ValueError(f"unknown_or_retired_theme:{theme_id}")
        mappings = self.registry.constituents(definition.id)
        normalized = {symbol.upper(): self._values(values) for symbol, values in histories.items()}
        benchmark_values = {symbol.upper(): self._values(values) for symbol, values in (benchmarks or {}).items()}
        usable = {item.symbol: normalized.get(item.symbol, ()) for item in mappings if len(normalized.get(item.symbol, ())) >= 2}
        covered = len(usable)
        total = len(mappings)
        coverage = covered / total if total else 0.0
        history_sufficient = {symbol: values for symbol, values in usable.items() if len(values) >= 21}
        core = sum(item.exposure == "core" for item in mappings)
        significant = sum(item.exposure == "significant" for item in mappings)
        adjacent = sum(item.exposure == "adjacent" for item in mappings)
        experimental = sum(item.exposure == "experimental" for item in mappings)

        status = self._availability(definition.minimum_constituents, total, covered, len(history_sufficient), coverage)
        market_date = (as_of or datetime.now(timezone.utc).date().isoformat())[:10]
        generated = generated_at or f"{market_date}T00:00:00+00:00"
        freshness = self.freshness.evaluate(FreshnessAvailabilityInput(
            source_state=source_state,
            generated_at=generated,
            observed_at=observed_at,
            market_date=market_date,
            completeness=coverage,
            provider="caller_supplied_theme_history" if status != "unavailable" else "unavailable",
            test_data=test_data,
            mixed_sources=source_state == "mixed",
            now=self._as_datetime(generated) if test_data else None,
        ))

        constituent_returns = {
            window: {symbol: self._return(values, days) for symbol, values in usable.items()}
            for window, days in WINDOWS.items()
        }
        equal_weight = {
            window: self._mean(value for value in values.values() if value is not None)
            for window, values in constituent_returns.items()
        }
        median_returns = {
            window: self._median(value for value in values.values() if value is not None)
            for window, values in constituent_returns.items()
        }
        relative_strength: dict[str, Any] = {"equal_weight_returns": equal_weight, "median_constituent_returns": median_returns}
        required_benchmarks = {symbol.upper() for symbol in (required_benchmark_symbols or definition.benchmark_symbols)}
        missing_benchmarks: list[str] = []
        optional_missing_benchmarks: list[str] = []
        benchmark_order = tuple(dict.fromkeys((*definition.benchmark_symbols, *sorted(required_benchmarks))))
        for benchmark in benchmark_order:
            values = benchmark_values.get(benchmark, ())
            if not values:
                (missing_benchmarks if benchmark in required_benchmarks else optional_missing_benchmarks).append(benchmark)
            relative_strength[f"vs_{benchmark.lower()}"] = {
                window: self._subtract(equal_weight[window], self._return(values, days))
                for window, days in WINDOWS.items()
            }

        breadth = self._breadth(usable)
        momentum = self._momentum(equal_weight)
        contributions = self._contributions(constituent_returns["1m"])
        concentration = self._concentration(contributions)
        constituent_rows = self._constituent_rows(mappings, usable, constituent_returns, contributions)
        classification = self._leadership(relative_strength.get("vs_spy", {}), breadth, momentum, status, concentration)
        previous_state = str((previous_snapshot or {}).get("leadership_state") or "")
        previous_sessions = int((previous_snapshot or {}).get("persistence", {}).get("sessions_in_state") or 0)
        persistence_sessions = previous_sessions + 1 if previous_state == classification else 1

        evidence = self._evidence(definition.id, market_date, relative_strength, breadth, momentum, concentration, status)
        findings = self._contradiction_findings(definition.id, momentum, breadth, relative_strength)
        contradiction_result = self.contradictions.analyze(ContradictionAnalysisInput(findings=tuple(findings)))
        contradictions = [
            {"evidence_id": item.evidence_id, "statement": item.statement, "preserved": True}
            for item in findings if item.evidence_id in contradiction_result.opposing_evidence_ids
        ]
        required_missing = sum(value is None for value in (
            relative_strength.get("vs_spy", {}).get("1m"),
            breadth.get("percent_above_50_day_average"),
            momentum.get("medium_window"),
        )) + len(missing_benchmarks)
        confidence = self.confidence.adjust(ConfidenceAdjustmentInput(
            intent="theme_intelligence",
            evidence_count=len(evidence),
            freshness_state=freshness.state,
            missing_evidence_count=required_missing,
            stale_count=int(freshness.state == "stale"),
            partial_count=int(status == "partial" or freshness.state in {"partial", "mixed"}),
            unavailable_count=int(status == "unavailable"),
            test_count=int(freshness.state == "test"),
            contradiction_count=len(contradictions),
            unsupported_dimension_count=required_missing,
        ))
        missing_data = []
        if missing_benchmarks:
            missing_data.append({"dimension": "benchmarks", "symbols": missing_benchmarks})
        if optional_missing_benchmarks:
            missing_data.append({"dimension": "optional_benchmarks", "symbols": optional_missing_benchmarks})
        for period, eligible in breadth["eligible_counts"].items():
            if eligible < covered:
                missing_data.append({"dimension": f"breadth_{period}", "covered": eligible, "expected": covered})
        if status != "available":
            missing_data.append({"dimension": "constituent_coverage", "covered": covered, "expected": total})

        events = self._change_events(definition.id, previous_snapshot, classification, breadth, momentum, concentration, constituent_rows)
        leaders = [item for item in constituent_rows if item["availability"] == "available"][:5]
        laggards = [item for item in reversed(constituent_rows) if item["availability"] == "available"][:5]
        return {
            "theme_id": definition.id,
            "name": definition.name,
            "taxonomy_version": TAXONOMY_VERSION,
            "analytics_version": THEME_ANALYTICS_VERSION,
            "as_of": generated,
            "market_date": market_date,
            "market_session": "close",
            "status": status,
            "freshness": self._dump(freshness),
            "constituent_count": total,
            "covered_constituent_count": covered,
            "coverage_ratio": round(coverage, 6),
            "core_constituent_count": core,
            "significant_constituent_count": significant,
            "adjacent_constituent_count": adjacent,
            "experimental_constituent_count": experimental,
            "benchmark_symbols": list(definition.benchmark_symbols),
            "required_benchmark_symbols": sorted(required_benchmarks),
            "relative_strength": relative_strength,
            "breadth": breadth,
            "momentum": momentum,
            "persistence": {"sessions_in_state": persistence_sessions, "quality": "established" if persistence_sessions >= 5 else "developing"},
            "leadership_state": classification,
            "concentration": concentration,
            "leaders": leaders,
            "improving_constituents": [item for item in constituent_rows if item["trend"] == "improving"][:5],
            "weakening_constituents": [item for item in constituent_rows if item["trend"] == "weakening"][:5],
            "laggards": laggards,
            "constituents": constituent_rows,
            "change_events": events,
            "evidence": evidence,
            "contradictions": contradictions,
            "missing_data": missing_data,
            "confidence": self._dump(confidence),
            "source_status": {"state": freshness.state, "provider": freshness.provider, "test_data": freshness.state == "test"},
            "test_or_mock_label": "HERMETIC TEST DATA — NOT LIVE" if freshness.state == "test" else None,
        }

    @staticmethod
    def _availability(minimum: int, total: int, covered: int, history: int, ratio: float) -> str:
        if total < minimum or covered < max(2, minimum // 2):
            return "unavailable"
        if ratio < 0.75 or history < minimum:
            return "partial"
        return "available"

    @staticmethod
    def _values(values: Sequence[Any]) -> tuple[float, ...]:
        result: list[float] = []
        for item in values:
            value = item if isinstance(item, (int, float)) else item.get("close") if isinstance(item, dict) else getattr(item, "close", None)
            if isinstance(value, (int, float)) and math.isfinite(float(value)) and float(value) > 0:
                result.append(float(value))
        return tuple(result)

    @staticmethod
    def _return(values: Sequence[float], days: int) -> float | None:
        if len(values) <= days or values[-days - 1] <= 0:
            return None
        return round((values[-1] / values[-days - 1] - 1) * 100, 6)

    @staticmethod
    def _mean(values: Iterable[float]) -> float | None:
        selected = list(values)
        return round(sum(selected) / len(selected), 6) if selected else None

    @staticmethod
    def _median(values: Iterable[float]) -> float | None:
        selected = list(values)
        return round(median(selected), 6) if selected else None

    @staticmethod
    def _subtract(left: float | None, right: float | None) -> float | None:
        return round(left - right, 6) if left is not None and right is not None else None

    def _breadth(self, histories: dict[str, Sequence[float]]) -> dict[str, Any]:
        def above(period: int) -> tuple[float | None, int]:
            eligible = [values for values in histories.values() if len(values) >= period]
            count = sum(values[-1] > sum(values[-period:]) / period for values in eligible)
            return (round(count / len(eligible) * 100, 4), len(eligible)) if eligible else (None, 0)
        above20, eligible20 = above(20)
        above50, eligible50 = above(50)
        above200, eligible200 = above(200)
        daily = [self._return(values, 1) for values in histories.values()]
        daily_valid = [value for value in daily if value is not None]
        one_month = [self._return(values, 21) for values in histories.values()]
        one_month_valid = [value for value in one_month if value is not None]
        ordered = sorted(one_month_valid, key=abs, reverse=True)
        excluding = ordered[1:]
        return {
            "percent_above_20_day_average": above20,
            "percent_above_50_day_average": above50,
            "percent_above_200_day_average": above200,
            "advance_decline": {"advancing": sum(value > 0 for value in daily_valid), "declining": sum(value < 0 for value in daily_valid), "unchanged": sum(value == 0 for value in daily_valid)},
            "median_constituent_performance_1m": self._median(one_month_valid),
            "breadth_excluding_largest_constituent_1m": self._mean(excluding),
            "eligible_counts": {"20d": eligible20, "50d": eligible50, "200d": eligible200, "advance_decline": len(daily_valid)},
        }

    @staticmethod
    def _momentum(returns: dict[str, float | None]) -> dict[str, Any]:
        short, medium, long = returns.get("1w"), returns.get("1m"), returns.get("3m")
        available = [item for item in (short, medium, long) if item is not None]
        agreement = "unavailable"
        if len(available) >= 2:
            agreement = "positive" if all(item > 0 for item in available) else "negative" if all(item < 0 for item in available) else "conflicting"
        acceleration = None if short is None or medium is None else round(short - medium / 4.2, 6)
        return {"short_window": short, "medium_window": medium, "long_window": long, "acceleration": acceleration, "agreement": agreement}

    @staticmethod
    def _contributions(returns: dict[str, float | None]) -> dict[str, float]:
        values = {symbol: value for symbol, value in returns.items() if value is not None}
        if not values:
            return {}
        equal_weight = 1 / len(values)
        return {symbol: round(value * equal_weight, 8) for symbol, value in values.items()}

    @staticmethod
    def _concentration(contributions: dict[str, float]) -> dict[str, Any]:
        total = sum(abs(value) for value in contributions.values())
        shares = sorted((abs(value) / total for value in contributions.values()), reverse=True) if total else []
        top1 = shares[0] if shares else None
        top3 = sum(shares[:3]) if shares else None
        hhi = sum(value * value for value in shares)
        effective = 1 / hhi if hhi else 0
        classification = "unavailable" if not shares else "narrow" if (top1 or 0) >= 0.5 or effective < 3 else "moderately_concentrated" if (top3 or 0) >= 0.75 else "broad"
        return {"top_1_contribution": round((top1 or 0) * 100, 4) if top1 is not None else None, "top_3_contribution": round((top3 or 0) * 100, 4) if top3 is not None else None, "effective_constituent_count": round(effective, 4), "hhi": round(hhi, 6), "classification": classification}

    def _constituent_rows(self, mappings: Sequence[Any], histories: dict[str, Sequence[float]], returns: dict[str, dict[str, float | None]], contributions: dict[str, float]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for mapping in mappings:
            available = mapping.symbol in histories and returns["1m"].get(mapping.symbol) is not None
            short, medium = returns["1w"].get(mapping.symbol), returns["1m"].get(mapping.symbol)
            trend = "unavailable" if not available else "improving" if short is not None and medium is not None and short > medium / 4.2 else "weakening" if short is not None and short < 0 else "stable"
            rows.append({
                "symbol": mapping.symbol, "exposure": mapping.exposure, "trend": trend,
                "relative_strength": medium, "momentum": short,
                "breadth_participation": histories.get(mapping.symbol, ())[-1] > sum(histories.get(mapping.symbol, ())[-20:]) / min(20, len(histories.get(mapping.symbol, ()))) if available else None,
                "contribution": contributions.get(mapping.symbol), "rank": None,
                "availability": "available" if available else "unavailable",
                "evidence_references": [f"theme:{mapping.theme_id}:mapping:{mapping.symbol}"] if available else [],
            })
        rows.sort(key=lambda item: (item["availability"] != "available", -(item["relative_strength"] if isinstance(item["relative_strength"], (int, float)) else -10_000), item["symbol"]))
        for rank, item in enumerate((row for row in rows if row["availability"] == "available"), start=1):
            item["rank"] = rank
        return rows

    @staticmethod
    def _leadership(rs: dict[str, Any], breadth: dict[str, Any], momentum: dict[str, Any], status: str, concentration: dict[str, Any]) -> str:
        if status == "unavailable":
            return "neutral"
        one_month = rs.get("1m")
        breadth50 = breadth.get("percent_above_50_day_average")
        medium = momentum.get("medium_window")
        if one_month is None or breadth50 is None or medium is None:
            return "neutral"
        if one_month >= 1.5 and breadth50 >= 60 and medium > 0 and concentration.get("classification") != "narrow":
            return "leading"
        if one_month >= 0 and momentum.get("acceleration") is not None and momentum["acceleration"] > 0:
            return "improving"
        if one_month <= -2 and breadth50 <= 40 and medium < 0:
            return "lagging"
        if one_month < 0 or (momentum.get("acceleration") is not None and momentum["acceleration"] < 0):
            return "weakening"
        return "neutral"

    @staticmethod
    def _evidence(theme_id: str, market_date: str, rs: dict[str, Any], breadth: dict[str, Any], momentum: dict[str, Any], concentration: dict[str, Any], status: str) -> list[dict[str, Any]]:
        values = (
            ("relative_strength", rs.get("vs_spy", {}).get("1m"), "percent", "1m"),
            ("breadth", breadth.get("percent_above_50_day_average"), "percent", "50 sessions"),
            ("momentum", momentum.get("medium_window"), "percent", "1m"),
            ("concentration", concentration.get("top_1_contribution"), "percent", "1m"),
        )
        return [{"evidence_id": f"theme:{theme_id}:{metric}:{market_date}", "theme_id": theme_id, "metric": metric, "value": value, "unit": unit, "timeframe": timeframe, "market_date": market_date, "availability": status, "source": "caller_supplied_constituent_history", "analytics_version": THEME_ANALYTICS_VERSION} for metric, value, unit, timeframe in values if value is not None]

    @staticmethod
    def _contradiction_findings(theme_id: str, momentum: dict[str, Any], breadth: dict[str, Any], rs: dict[str, Any]) -> list[ContradictionFinding]:
        result: list[ContradictionFinding] = []
        if momentum.get("agreement") == "conflicting":
            result.append(ContradictionFinding(evidence_id=f"theme:{theme_id}:momentum-conflict", statement="Momentum windows are conflicting and do not confirm one direction.", interpretation_class="contradiction", explicitly_opposing=True))
        spy = rs.get("vs_spy", {}).get("1m")
        breadth50 = breadth.get("percent_above_50_day_average")
        if isinstance(spy, (int, float)) and spy > 0 and isinstance(breadth50, (int, float)) and breadth50 < 50:
            result.append(ContradictionFinding(evidence_id=f"theme:{theme_id}:narrow-breadth", statement="Positive relative strength is contradicted by narrow breadth.", interpretation_class="contradiction", explicitly_opposing=True))
        return result

    @staticmethod
    def _change_events(theme_id: str, previous: dict[str, Any] | None, state: str, breadth: dict[str, Any], momentum: dict[str, Any], concentration: dict[str, Any], constituents: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not previous:
            return []
        events: list[dict[str, Any]] = []
        old_state = previous.get("leadership_state")
        if old_state != state:
            events.append({"type": "leadership_transition", "theme_id": theme_id, "from": old_state, "to": state, "material": True})
        old_breadth = (previous.get("breadth") or {}).get("percent_above_50_day_average")
        new_breadth = breadth.get("percent_above_50_day_average")
        if isinstance(old_breadth, (int, float)) and isinstance(new_breadth, (int, float)) and abs(new_breadth - old_breadth) >= 15:
            events.append({"type": "breadth_improved_materially" if new_breadth > old_breadth else "breadth_deteriorated", "theme_id": theme_id, "change": round(new_breadth - old_breadth, 4), "material": True})
        if concentration.get("classification") == "narrow" and (previous.get("concentration") or {}).get("classification") != "narrow":
            events.append({"type": "leadership_narrowed", "theme_id": theme_id, "material": True})
        old_leader = ((previous.get("leaders") or [{}])[0]).get("symbol")
        new_leader = (constituents[0] if constituents else {}).get("symbol")
        if old_leader and new_leader and old_leader != new_leader:
            events.append({"type": "new_leading_constituent", "theme_id": theme_id, "from": old_leader, "to": new_leader, "material": True})
        return events

    @staticmethod
    def _dump(value: Any) -> dict[str, Any]:
        return asdict(value) if is_dataclass(value) else dict(vars(value))

    @staticmethod
    def _as_datetime(value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
