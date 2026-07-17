from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.copilot_formatting import compact_sentence_list, format_copilot_label, format_copilot_value


@dataclass(frozen=True)
class StrategicReasoning:
    narrative: str
    direct_answer: str
    evidence: list[str]
    counterargument: str
    conditions: list[str]
    decision_context: str
    confidence_reasons: list[str]


class TradeOffEngine:
    def build(self, signals: dict[str, Any], existing_points: list[str], existing_risks: list[str]) -> dict[str, list[str] | str]:
        pros = []
        cons = []

        if is_positive_text(signals.get("trend")) or number(signals.get("health_score")) >= 70:
            pros.append("Trend evidence remains intact, which keeps the base case tilted toward continuation.")
        if is_positive_text(signals.get("breadth")) or number(signals.get("breadth_score")) >= 65:
            pros.append("Breadth participation is confirming enough to reduce single-index dependence.")
        if number(signals.get("risk_score"), 100) <= 35 or is_contained_text(signals.get("risk")):
            pros.append("Risk is contained, so volatility is not yet forcing a defensive read.")
        if signals.get("leader"):
            pros.append(f"{signals['leader']} leadership gives the market a clear sponsorship group.")

        risk_text = " ".join(existing_risks).lower()
        if "sentiment" in risk_text or "greed" in risk_text:
            cons.append("Sentiment is the main offset because crowded optimism can make pullbacks sharper.")
        if "concentrat" in risk_text or "narrow" in risk_text:
            cons.append("Leadership concentration is the main counterweight because fewer groups are carrying the move.")
        if is_negative_text(signals.get("breadth")):
            cons.append("Breadth is not confirming strongly, which raises divergence risk.")
        if number(signals.get("risk_score"), 0) >= 45:
            cons.append("Risk is high enough to reduce confidence in follow-through.")

        if not pros:
            pros = compact_sentence_list(existing_points, 2) or ["The current context has some supporting evidence, but it is incomplete."]
        if not cons:
            cons = compact_sentence_list(existing_risks, 2) or ["The strongest counterargument is that source data or confirmation may be incomplete."]

        overall = "Pros currently outweigh risks." if len(pros) >= len(cons) else "Risks are beginning to offset the positive evidence."
        return {"pros": compact_sentence_list(pros, 3), "cons": compact_sentence_list(cons, 3), "overall": overall}


class StrategicReasoningEngine:
    def __init__(self, context: dict[str, Any], history: list[dict[str, str]] | None = None) -> None:
        self.context = context or {}
        self.history = history or []

    def build(
        self,
        *,
        message: str,
        intent: str,
        base_answer: str,
        points: list[str],
        risks: list[str],
        watch: list[str],
    ) -> StrategicReasoning:
        signals = extract_market_signals(self.context)
        relationships = self.detect_relationships(signals)
        tradeoff = TradeOffEngine().build(signals, points, risks)
        narrative = self.build_market_narrative(signals, relationships, intent)
        counterargument = self.strongest_counterargument(tradeoff, risks)
        conditions = self.view_change_conditions(signals, watch)
        decision_context = self.so_what(signals, intent, counterargument)
        direct_answer = self.compose_direct_answer(base_answer, narrative, counterargument, conditions, decision_context)
        evidence = compact_sentence_list([*relationships, *points, str(tradeoff["overall"])], 3)
        confidence_reasons = self.confidence_reasons(signals, relationships)
        return StrategicReasoning(
            narrative=narrative,
            direct_answer=direct_answer,
            evidence=evidence,
            counterargument=counterargument,
            conditions=conditions,
            decision_context=decision_context,
            confidence_reasons=confidence_reasons,
        )

    def detect_relationships(self, signals: dict[str, Any]) -> list[str]:
        observations: list[str] = []
        trend_positive = is_positive_text(signals.get("trend")) or number(signals.get("health_score")) >= 70
        breadth_positive = is_positive_text(signals.get("breadth")) or number(signals.get("breadth_score")) >= 65
        breadth_negative = is_negative_text(signals.get("breadth")) or (0 < number(signals.get("breadth_score")) < 55)
        risk_contained = number(signals.get("risk_score"), 100) <= 35 or is_contained_text(signals.get("risk"))
        risk_rising = number(signals.get("risk_score"), 0) >= 45 or is_negative_text(signals.get("risk"))

        if trend_positive and breadth_positive:
            observations.append("Trend quality is reinforced because participation is confirming the index move.")
        if trend_positive and breadth_negative:
            observations.append("Index strength with weaker breadth creates a participation divergence rather than broad confirmation.")
        if risk_contained and trend_positive:
            observations.append("Contained risk allows the trend signal to carry more weight in the decision read.")
        if risk_rising:
            observations.append("Rising risk reduces confidence because volatility or macro pressure can interrupt follow-through.")

        leader = signals.get("leader")
        secondary = signals.get("secondary_leader")
        if leader and secondary and str(leader).lower() != str(secondary).lower():
            observations.append(f"{leader} leadership with {secondary} improving points to rotation rather than a one-group market.")
        elif leader:
            observations.append(f"{leader} remains the main sponsorship group, so the market read depends heavily on that leadership staying intact.")

        historical = self.historical_observations(signals)
        observations.extend(historical)
        return compact_sentence_list(observations, 5)

    def historical_observations(self, signals: dict[str, Any]) -> list[str]:
        history_items = report_history_items(self.context)
        if not history_items:
            return []

        observations: list[str] = []
        leader = str(signals.get("leader") or "").lower()
        if leader:
            count = sum(1 for item in history_items if leader and leader in str(item).lower())
            if count >= 2:
                observations.append(f"{format_copilot_label(leader)} has appeared repeatedly in recent report history, so leadership has persistence rather than being a one-day move.")

        risk_values = [number(value_at(item, "risk.score"), None) for item in history_items if number(value_at(item, "risk.score"), None) is not None]
        if len(risk_values) >= 3 and risk_values[-1] < risk_values[0]:
            observations.append("Risk has declined across recent report snapshots, which improves the quality of the current playbook.")
        elif len(risk_values) >= 3 and risk_values[-1] > risk_values[0]:
            observations.append("Risk has risen across recent report snapshots, which lowers the margin for error.")
        return observations[:2]

    def build_market_narrative(self, signals: dict[str, Any], relationships: list[str], intent: str) -> str:
        leader = signals.get("leader")
        if leader and (is_positive_text(signals.get("trend")) or number(signals.get("health_score")) >= 65):
            return (
                f"Today's story is a market still leaning on {leader} leadership while participation and risk determine how durable that leadership is."
            )
        if relationships:
            return relationships[0]
        if intent == "compare":
            return "The comparison is about which side has better momentum quality after accounting for risk and data gaps."
        return "The current read is best judged by how trend, participation, leadership, and risk agree or diverge."

    def strongest_counterargument(self, tradeoff: dict[str, list[str] | str], risks: list[str]) -> str:
        cons = tradeoff.get("cons")
        if isinstance(cons, list) and cons:
            return cons[0]
        return compact_sentence_list(risks, 1)[0] if risks else "The opposing view is that confirmation may be incomplete."

    def view_change_conditions(self, signals: dict[str, Any], watch: list[str]) -> list[str]:
        negative_terms = ("deterior", "weaken", "expand", "loss", "below", "elevat", "high", "fail", "rise", "narrow")
        conditions = compact_sentence_list(
            [item for item in watch if any(term in item.lower() for term in negative_terms)],
            2,
        )
        if conditions:
            return conditions
        if number(signals.get("risk_score"), 100) <= 35:
            return ["risk expands from contained to elevated", "breadth loses confirmation"]
        return ["risk declines while participation improves", "leadership broadens beyond the current leaders"]

    def so_what(self, signals: dict[str, Any], intent: str, counterargument: str) -> str:
        if intent == "risk":
            return "So what: risk does not need to be avoided entirely, but position sizing and confirmation matter more when the counterargument is active."
        if intent == "compare":
            return "So what: prefer the side with better momentum quality only if the risk and entry-quality gap is acceptable."
        if intent == "rank_watchlist":
            return "So what: the ranking should prioritize names with aligned trend, setup, and risk instead of chasing the largest one-day move."
        if signals.get("leader"):
            return f"So what: exposure to {signals['leader']} remains easier to justify while the evidence holds, but diversification still matters if leadership is narrow."
        return "So what: the decision posture should stay conditional until trend, participation, and risk are pointing in the same direction."

    def compose_direct_answer(
        self,
        base_answer: str,
        narrative: str,
        counterargument: str,
        conditions: list[str],
        decision_context: str,
    ) -> str:
        condition_text = " or ".join(conditions[:2]) if conditions else "the supporting evidence changes"
        return (
            f"{base_answer} {narrative} The strongest counterargument is that {counterargument[0].lower() + counterargument[1:] if counterargument else 'confirmation is incomplete'}. "
            f"If {condition_text.lower()}, the conclusion should be revisited. {decision_context}"
        )

    def confidence_reasons(self, signals: dict[str, Any], relationships: list[str]) -> list[str]:
        reasons = []
        if relationships:
            reasons.append("Trend, participation, leadership, and risk relationships were evaluated together.")
        if signals.get("health_score") is not None and signals.get("risk_score") is not None:
            reasons.append("Health and risk inputs are both present.")
        if signals.get("leader"):
            reasons.append("Leadership context is available.")
        return compact_sentence_list(reasons or ["Confidence is limited by available context depth."], 3)


def extract_market_signals(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "trend": first_value(context, [
            "market.market_health.status",
            "market.marketHealth.status",
            "market.health.status",
            "report.marketHealth.status",
            "report.market_health.status",
            "focusedMetric.status",
        ]),
        "health_score": first_value(context, [
            "market.market_health.overall_score",
            "market.marketHealth.overallScore",
            "market.health.score",
            "report.marketHealth.score",
            "report.marketConviction.score",
        ]),
        "breadth": first_value(context, [
            "market.breadth_summary.breadth_status",
            "market.breadthSummary.breadthStatus",
            "market.breadth.status",
            "report.breadth.status",
        ]),
        "breadth_score": first_value(context, [
            "market.breadth_summary.breadth_score",
            "market.breadthSummary.breadthScore",
            "market.breadth.breadth_score",
            "market.breadth.score",
            "report.breadth.score",
        ]),
        "risk": first_value(context, [
            "market.risk_summary.status",
            "market.riskSummary.status",
            "market.risk.status",
            "report.risk.status",
        ]),
        "risk_score": first_value(context, [
            "market.risk_summary.score",
            "market.riskSummary.score",
            "market.risk.score",
            "report.risk.score",
        ]),
        "leader": first_value(context, [
            "market.top_sector.name",
            "market.topSector.name",
            "market.leadership.topSector",
            "report.topSector",
            "report.marketSnapshot.leadership",
            "sector.focused.name",
            "theme.focused.name",
            "sector.selected.name",
            "theme.selected.name",
        ]),
        "secondary_leader": first_value(context, [
            "market.top_industry_group.name",
            "market.topIndustryGroup.name",
            "market.top_theme.name",
            "market.topTheme.name",
            "report.topTheme",
        ]),
    }


def first_value(context: dict[str, Any], paths: list[str]) -> Any:
    for path in paths:
        value = value_at(context, path)
        if value not in (None, ""):
            return value
    return None


def report_history_items(context: dict[str, Any]) -> list[dict[str, Any]]:
    for path in ("report.history", "report.reportHistory", "market.reportHistory", "market.previousReports"):
        value = value_at(context, path)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)][:8]
    return []


def is_positive_text(value: Any) -> bool:
    text = str(value or "").lower()
    return any(term in text for term in ("uptrend", "healthy", "constructive", "leading", "improving", "bullish", "pass", "positive"))


def is_negative_text(value: Any) -> bool:
    text = str(value or "").lower()
    return any(term in text for term in ("weak", "deteriorating", "defensive", "lagging", "bearish", "fail", "negative", "elevated"))


def is_contained_text(value: Any) -> bool:
    text = str(value or "").lower()
    return any(term in text for term in ("low", "contained", "manageable", "controlled"))


def number(value: Any, default: float | None = 0) -> float | None:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def value_at(value: Any, path: str) -> Any:
    current = value
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current
