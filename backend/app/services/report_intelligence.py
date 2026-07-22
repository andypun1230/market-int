from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

MAX_HISTORY = 10


def build_report_snapshot(report: Any) -> dict[str, Any]:
    generated_time = datetime.now(timezone.utc).isoformat()
    sectors = get_ranked_items(getattr(report, "sector_dashboard", None), "sectors", fallback=getattr(getattr(report, "sector_etfs", None), "items", []))
    themes = get_ranked_items(getattr(report, "sector_dashboard", None), "themes", fallback=[])
    watchlist_items = (getattr(report, "watchlist_summary", None) or {}).get("items") or []
    health = getattr(report, "market_health", None)
    risk = getattr(report, "risk_dashboard", None)
    playbook = getattr(getattr(report, "decision_dashboard", None), "playbook", None)
    components = getattr(health, "components", None)
    fear_greed = getattr(report, "fear_greed", None)
    snapshot = {
        "reportId": f"{getattr(report, 'date', 'report')}-{uuid4().hex[:8]}",
        "marketDate": getattr(report, "date", None),
        "generatedTime": generated_time,
        "marketHealth": {
            "score": number(getattr(health, "overall_score", None)),
            "status": getattr(health, "status", None),
        },
        "risk": {
            "score": number(getattr(risk, "score", None)),
            "status": classify_risk(number(getattr(risk, "score", None))),
        },
        "breadth": {
            "score": number(getattr(components, "breadth", None)),
            "status": "Healthy" if number(getattr(components, "breadth", None), 0) >= 70 else "Mixed",
        },
        "regime": getattr(report, "market_regime", None),
        "sectorRanking": sectors,
        "themeRanking": themes,
        "watchlistSummary": [normalize_watchlist_item(item) for item in watchlist_items],
        "signalSummary": {
            "trend": number(getattr(components, "trend", None)),
            "breadth": number(getattr(components, "breadth", None)),
            "sectorStrength": number(getattr(components, "sector_strength", None)),
            "volume": number(getattr(components, "volume", None)),
            "momentum": number(getattr(components, "momentum", None)),
            "risk": number(getattr(risk, "score", None)),
            "sentiment": number(getattr(fear_greed, "score", None)),
        },
        "macroSummary": {
            "events": list(getattr(report, "tomorrow_watch", []) or []),
            "state": (getattr(report, "macro", None) or {}).get("state_label", "Unavailable"),
            "currentRisks": (getattr(report, "macro", None) or {}).get("current_risks", []),
            "invalidationConditions": (getattr(report, "macro", None) or {}).get("invalidation_conditions"),
        },
        "playbook": {
            "headline": getattr(playbook, "headline", None),
            "summary": getattr(playbook, "summary", None),
            "mainRisk": getattr(playbook, "main_risk", None),
            "preferredStrategy": getattr(playbook, "preferred_strategy", None),
        },
    }
    snapshot["historicalMetrics"] = build_historical_metrics(snapshot)
    return snapshot


class ReportComparisonEngine:
    def compare(self, previous: dict[str, Any] | None, current: dict[str, Any]) -> dict[str, Any]:
        if not previous:
            return {
                "available": False,
                "summary": "Baseline report established.",
                "items": [],
            }

        items: list[dict[str, Any]] = []
        add_score_change(items, "Market Health", previous, current, ("marketHealth", "score"), threshold=3, lower_is_better=False)
        add_score_change(items, "Risk", previous, current, ("risk", "score"), threshold=5, lower_is_better=True)
        add_score_change(items, "Breadth", previous, current, ("breadth", "score"), threshold=3, lower_is_better=False)

        previous_regime = get_path(previous, "regime")
        current_regime = get_path(current, "regime")
        if previous_regime and current_regime and previous_regime != current_regime:
            items.append({
                "label": "Market Regime",
                "previous": previous_regime,
                "current": current_regime,
                "direction": "changed",
                "importance": "High",
                "reason": f"Regime changed from {previous_regime} to {current_regime}, so positioning assumptions should be rechecked.",
            })

        items.extend(rank_changes("Sector Leadership", previous.get("sectorRanking", []), current.get("sectorRanking", []), limit=5))
        items.extend(watchlist_changes(previous.get("watchlistSummary", []), current.get("watchlistSummary", [])))
        items.extend(macro_changes(previous.get("macroSummary", {}), current.get("macroSummary", {})))

        items = sorted(items, key=change_sort_key)[:8]
        return {
            "available": True,
            "summary": "Meaningful changes detected." if items else "No meaningful changes since the previous report.",
            "items": items,
        }


class MarketConvictionEngine:
    def calculate(self, snapshot: dict[str, Any], convergence: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
        signals = snapshot.get("signalSummary", {})
        sectors = snapshot.get("sectorRanking", [])
        macro_state = snapshot.get("macroSummary", {}).get("state")
        components = [
            ("Trend", normalize_score(signals.get("trend")), 14),
            ("Breadth", normalize_score(signals.get("breadth")), 14),
            ("Leadership", normalize_score(signals.get("sectorStrength")), 13),
            ("Sector Rotation", rotation_score(sectors), 9),
            ("Momentum", normalize_score(signals.get("momentum")), 10),
            ("Volume", normalize_score(signals.get("volume")), 9),
            ("Risk", inverse_score(signals.get("risk")), 10),
            ("Sentiment", sentiment_conviction(signals.get("sentiment")), 6),
            ("Macro", 85 if macro_state in ("Strong Risk-On", "Risk-On") else 75 if macro_state == "Balanced" else 50, 6),
        ]
        raw = sum(score * weight for _, score, weight in components) / sum(weight for _, _, weight in components)
        disagreement_penalty = max(0, (convergence.get("total", 0) - convergence.get("passed", 0)) * 4)
        warning_penalty = 0 if warnings == ["No significant market contradictions detected."] else min(10, len(warnings) * 3)
        score = round(max(0, min(100, raw - disagreement_penalty - warning_penalty)))
        why_not_higher = conviction_constraints(snapshot, warnings)
        why_not_lower = conviction_supports(snapshot)
        return {
            "score": score,
            "rating": conviction_rating(score),
            "stars": max(1, min(5, round(score / 20))),
            "summary": conviction_summary(score),
            "whyNotHigher": why_not_higher,
            "whyNotLower": why_not_lower,
            "contributors": [
                {"label": label, "score": round(score_value), "weight": weight}
                for label, score_value, weight in components
            ],
        }


class DecisionChecklistEngine:
    def build(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        signals = snapshot.get("signalSummary", {})
        watchlist = snapshot.get("watchlistSummary", [])
        items = [
            checklist_item("Trend intact", signals.get("trend"), 65, 50, higher_is_better=True),
            checklist_item("Breadth confirms", signals.get("breadth"), 65, 50, higher_is_better=True),
            checklist_item("Leadership broad", signals.get("sectorStrength"), 65, 50, higher_is_better=True),
            checklist_item("Risk acceptable", signals.get("risk"), 45, 65, higher_is_better=False),
            checklist_item("Volatility acceptable", signals.get("risk"), 45, 65, higher_is_better=False),
            checklist_item("Macro risk", macro_checklist_score(snapshot.get("macroSummary", {}).get("state")), 70, 50, higher_is_better=True),
            checklist_item("Watchlist confirms", watchlist_confirmation_score(watchlist), 55, 40, higher_is_better=True),
        ]
        passed = sum(1 for item in items if item["status"] == "Pass")
        watch = sum(1 for item in items if item["status"] == "Watch")
        return {
            "items": items,
            "passed": passed,
            "total": len(items),
            "watch": watch,
            "readiness": "Favorable" if passed >= 5 and watch <= 2 else "Mixed" if passed >= 3 else "Not Ready",
            "summary": f"{passed} of {len(items)} checklist items are favorable.",
        }


class ConfidenceEngine:
    def calculate(
        self,
        snapshot: dict[str, Any],
        conviction: dict[str, Any],
        checklist: dict[str, Any],
        convergence: dict[str, Any],
        warnings: list[str],
    ) -> dict[str, Any]:
        base = (
            conviction.get("score", 0) * 0.45
            + convergence.get("score", 0) * 0.25
            + (checklist.get("passed", 0) / max(1, checklist.get("total", 1))) * 100 * 0.2
            + inverse_score(snapshot.get("signalSummary", {}).get("risk")) * 0.1
        )
        if warnings != ["No significant market contradictions detected."]:
            base -= min(12, len(warnings) * 4)
        score = round(max(0, min(100, base)))
        reason_parts = []
        if convergence.get("rating") == "High":
            reason_parts.append("trend, breadth, leadership, and risk mostly agree")
        if warnings != ["No significant market contradictions detected."]:
            reason_parts.append("contradictions reduce certainty")
        if checklist.get("readiness") == "Favorable":
            reason_parts.append("the decision checklist is favorable")
        return {
            "score": score,
            "rating": "High" if score >= 80 else "Medium" if score >= 60 else "Low",
            "reason": "; ".join(reason_parts) or "signal agreement is mixed",
        }


class ScenarioEngine:
    def build(self, snapshot: dict[str, Any], conviction: dict[str, Any], warnings: list[str]) -> list[dict[str, Any]]:
        score = number(conviction.get("score"), 60) or 60
        bullish = max(20, min(70, round(score * 0.62)))
        correction = max(10, min(45, round((100 - score) * 0.45)))
        sideways = max(15, 100 - bullish - correction)
        total = bullish + sideways + correction
        bullish = round(bullish / total * 100)
        correction = round(correction / total * 100)
        sideways = max(0, 100 - bullish - correction)
        return [
            {
                "name": "Bullish Continuation",
                "probability": bullish,
                "conditions": "Breadth expands, leaders hold trend, breakouts confirm.",
                "why": "Trend, breadth, and leadership remain aligned.",
                "changesProbability": "Rises if leadership broadens and volatility stays contained.",
                "expectedBehaviour": "Indexes grind higher with leadership support.",
                "suggestedResponse": "Add selectively to high-quality setups.",
            },
            {
                "name": "Sideways Consolidation",
                "probability": sideways,
                "conditions": "Indexes hold support while momentum cools.",
                "why": "Elevated sentiment can slow upside even when trend is intact.",
                "changesProbability": "Rises if momentum cools without breadth damage.",
                "expectedBehaviour": "Rotation improves beneath the surface without broad damage.",
                "suggestedResponse": "Maintain exposure and wait for cleaner entries.",
            },
            {
                "name": "Correction",
                "probability": correction,
                "conditions": warnings[0] if warnings else "Breadth weakens, volatility expands, or leadership narrows.",
                "why": "Contradictions or risk expansion would weaken the current thesis.",
                "changesProbability": "Rises if breadth rolls over or volatility expands.",
                "expectedBehaviour": "Failed breakouts and defensive rotation become more common.",
                "suggestedResponse": "Reduce marginal exposure and respect invalidation levels.",
            },
        ]


class RelationshipEngine:
    def detect(self, snapshot: dict[str, Any]) -> list[str]:
        signals = snapshot.get("signalSummary", {})
        sectors = snapshot.get("sectorRanking", [])
        relationships: list[str] = []
        if number(signals.get("breadth"), 0) >= 65 and number(signals.get("risk"), 100) < 40:
            relationships.append("Breadth strength combined with contained risk raises conviction in the current playbook.")
        if number(signals.get("trend"), 0) >= 65 and number(signals.get("volume"), 0) >= 65:
            relationships.append("Trend and volume are moving together, which supports the quality of the advance.")
        if number(signals.get("sentiment"), 0) >= 75 and number(signals.get("risk"), 100) < 35:
            relationships.append("Low measured risk is offset by elevated sentiment, reducing room for careless entries.")
        return relationships[:4]


class CommentaryEngine:
    def build(
        self,
        snapshot: dict[str, Any],
        conviction: dict[str, Any],
        confidence: dict[str, Any],
        relationships: list[str],
        warnings: list[str],
        confirmations: list[str],
    ) -> dict[str, Any]:
        top_sector = first_name(snapshot.get("sectorRanking", []), "sector leadership")
        breadth = get_path(snapshot, "breadth", "status") or "mixed"
        risk = get_path(snapshot, "risk", "status") or "monitored"
        thesis = (
            f"The current market thesis is that the uptrend remains investable because {str(breadth).lower()} breadth, "
            f"{top_sector} sector leadership continues to support the current evidence."
        )
        tradeoff = build_tradeoff(snapshot, warnings, confirmations)
        context = build_historical_context(snapshot)
        confidence_reason = (
            f"Confidence is {confidence.get('score', 'N/A')}% because {confidence.get('reason', 'signal agreement is mixed')}. "
            f"The main constraint is {strip_terminal(warnings[0]) if warnings else 'limited contradiction across core signals'}."
        )
        relationship_sentence = relationships[0] if relationships else "No strong cross-signal relationship materially changes the base case."
        return {
            "thesis": thesis,
            "crossTabNarrative": (
                f"{relationship_sentence} {tradeoff['overall']} This supports a {conviction.get('rating', 'mixed').lower()} read rather than a binary bullish or bearish call."
            ),
            "confidenceReasoning": confidence_reason,
            "tradeOff": tradeoff,
            "historicalContext": context,
            "invalidation": [
                "Breadth deterioration",
                "Volatility expansion",
                "Leadership narrowing",
                "Loss of intermediate trend support",
            ],
        }


class PreviousPlaybookEngine:
    def review(self, previous: dict[str, Any] | None, current: dict[str, Any]) -> dict[str, Any]:
        if not previous:
            return {"available": False, "summary": "Insufficient history.", "score": None, "items": []}
        previous_playbook = previous.get("playbook", {})
        score = 5.0
        items = []
        health_delta = number(get_path(current, "marketHealth", "score"), 0) - number(get_path(previous, "marketHealth", "score"), 0)
        risk_delta = number(get_path(current, "risk", "score"), 0) - number(get_path(previous, "risk", "score"), 0)
        if health_delta >= 0:
            score += 1.5
            items.append({"label": "Market", "result": "Confirmed", "detail": "Health held or improved."})
        else:
            items.append({"label": "Market", "result": "Mixed", "detail": "Health weakened."})
        if risk_delta <= 0:
            score += 1.0
            items.append({"label": "Risk", "result": "Contained", "detail": "Risk did not trigger."})
        else:
            items.append({"label": "Risk", "result": "Warning", "detail": "Risk increased."})
        if first_name(current.get("sectorRanking", []), "") == first_name(previous.get("sectorRanking", []), ""):
            score += 1.0
            items.append({"label": "Leadership", "result": "Confirmed", "detail": "Top sector remained intact."})
        headline = previous_playbook.get("headline") or "Previous playbook"
        score = round(max(0, min(10, score)), 1)
        return {
            "available": True,
            "previousPlaybook": headline,
            "outcome": "Correct" if score >= 7.5 else "Mixed" if score >= 5 else "Incorrect",
            "score": score,
            "items": items,
            "summary": f"Previous playbook assessment: {score}/10.",
        }


class MarketEvolutionEngine:
    def build(self, history: list[dict[str, Any]], current: dict[str, Any], conviction: dict[str, Any], confidence: dict[str, Any]) -> dict[str, Any]:
        points = [snapshot.get("historicalMetrics", {}) for snapshot in history[-(MAX_HISTORY - 1):]]
        current_metrics = build_historical_metrics(current)
        current_metrics["conviction"] = conviction.get("score")
        current_metrics["confidence"] = confidence.get("score")
        points.append(current_metrics)
        return {
            "available": len(points) >= 2,
            "points": points[-MAX_HISTORY:],
            "summary": "Recent report history is available." if len(points) >= 2 else "Insufficient history.",
        }


class SignalConvergenceEngine:
    def calculate(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        signals = snapshot.get("signalSummary", {})
        sectors = snapshot.get("sectorRanking", [])
        risk = number(signals.get("risk"), 100)
        sentiment = number(signals.get("sentiment"), 50)
        checks = [
            signal_check("Trend", number(signals.get("trend"), 0) >= 60, signals.get("trend")),
            signal_check("Breadth", number(signals.get("breadth"), 0) >= 60, signals.get("breadth")),
            signal_check("Sector Leadership", number(signals.get("sectorStrength"), 0) >= 60, signals.get("sectorStrength")),
            signal_check("Momentum", number(signals.get("momentum"), 0) >= 60, signals.get("momentum")),
            signal_check("Volume", number(signals.get("volume"), 0) >= 60, signals.get("volume")),
            signal_check("Risk", risk < 50, risk),
            signal_check("Sentiment", sentiment < 80, sentiment),
            signal_check("Macro", snapshot.get("macroSummary", {}).get("state") != "High Risk", snapshot.get("macroSummary", {}).get("state")),
        ]
        passed = sum(1 for item in checks if item["passed"])
        score = round((passed / len(checks)) * 100)
        return {
            "score": score,
            "passed": passed,
            "total": len(checks),
            "rating": "High" if score >= 80 else "Medium" if score >= 55 else "Low",
            "status": "Strong" if score >= 80 else "Mixed" if score >= 55 else "Weak",
            "items": checks,
            "summary": f"{passed} of {len(checks)} independent signals are aligned.",
        }


class MarketIntelligenceEngine:
    def build(
        self,
        snapshot: dict[str, Any],
        convergence: dict[str, Any],
        hidden_warnings: list[str],
        changes: dict[str, Any],
        conviction: dict[str, Any] | None = None,
        confidence: dict[str, Any] | None = None,
        checklist: dict[str, Any] | None = None,
        scenarios: list[dict[str, Any]] | None = None,
        hidden_confirmations: list[str] | None = None,
        commentary: dict[str, Any] | None = None,
        relationships: list[str] | None = None,
    ) -> dict[str, Any]:
        top_sector = first_name(snapshot.get("sectorRanking", []), "sector leadership")
        health = snapshot.get("marketHealth", {})
        risk = snapshot.get("risk", {})
        breadth = snapshot.get("breadth", {})
        playbook = snapshot.get("playbook", {})
        recommendation = playbook.get("headline") or "Stay Selective"
        warning_text = hidden_warnings[0] if hidden_warnings else "No significant contradictions detected."
        cross_tab = (
            f"{snapshot.get('regime')} is supported by {breadth.get('status', 'mixed').lower()} breadth, "
            f"{top_sector} sector leadership. "
            f"Risk remains {str(risk.get('status') or 'monitored').lower()}, so the report favors selective action rather than broad chasing."
        )
        market_narrative = (
            f"The market setup is {str(health.get('status') or 'mixed').lower()} because trend, breadth, leadership, "
            f"and risk are mostly aligned. The main caveat is: {warning_text}"
        )
        action_summary = [
            "Prioritize names aligned with leading sectors and verified setups.",
            "Treat new entries cautiously if sentiment or breadth diverges.",
            "Use risk triggers as invalidation conditions rather than predictions.",
        ]
        return {
            "recommendation": recommendation,
            "marketNarrative": (commentary or {}).get("thesis") or market_narrative,
            "crossTabNarrative": (commentary or {}).get("crossTabNarrative") or cross_tab,
            "confidenceReasoning": (commentary or {}).get("confidenceReasoning"),
            "tradeOff": (commentary or {}).get("tradeOff") or {},
            "historicalContext": (commentary or {}).get("historicalContext") or {},
            "relationships": relationships or [],
            "thesis": (commentary or {}).get("thesis"),
            "invalidation": (commentary or {}).get("invalidation") or [],
            "signalAlignment": convergence,
            "primaryOpportunity": f"{top_sector} sector leadership.",
            "primaryRisk": playbook.get("mainRisk") or warning_text,
            "hiddenWarnings": hidden_warnings,
            "hiddenConfirmations": hidden_confirmations or [],
            "marketConviction": conviction or {},
            "confidence": confidence or {},
            "decisionChecklist": checklist or {},
            "scenarios": scenarios or [],
            "keyChanges": changes.get("items", []),
            "actionSummary": action_summary,
        }


def build_hidden_warnings(snapshot: dict[str, Any], convergence: dict[str, Any]) -> list[str]:
    signals = snapshot.get("signalSummary", {})
    sectors = snapshot.get("sectorRanking", [])
    watchlist = snapshot.get("watchlistSummary", [])
    warnings: list[str] = []
    if number(signals.get("trend"), 0) >= 70 and number(signals.get("breadth"), 0) < 60:
        warnings.append("Trend is positive, but breadth is not confirming the move.")
    if number(signals.get("risk"), 100) < 35 and number(signals.get("sentiment"), 0) >= 75:
        warnings.append("Risk score is low, but sentiment is elevated.")
    if number(signals.get("sectorStrength"), 0) >= 70 and number(signals.get("volume"), 0) < 60:
        warnings.append("Leadership is constructive, but volume confirmation is weaker.")
    qqq = find_named_index(watchlist, "QQQ")
    if sectors and number(sectors[-1].get("return"), 0) < 0 and number(signals.get("sectorStrength"), 0) >= 70:
        warnings.append("Top leadership is strong, but lagging groups still show weak participation.")
    if qqq:
        pass
    return warnings[:4] or ["No significant market contradictions detected."]


def build_report_intelligence(
    previous_snapshot: dict[str, Any] | None,
    current_snapshot: dict[str, Any],
    history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    changes = ReportComparisonEngine().compare(previous_snapshot, current_snapshot)
    convergence = SignalConvergenceEngine().calculate(current_snapshot)
    hidden_warnings = build_hidden_warnings(current_snapshot, convergence)
    conviction = MarketConvictionEngine().calculate(current_snapshot, convergence, hidden_warnings)
    checklist = DecisionChecklistEngine().build(current_snapshot)
    confidence = ConfidenceEngine().calculate(current_snapshot, conviction, checklist, convergence, hidden_warnings)
    scenarios = ScenarioEngine().build(current_snapshot, conviction, hidden_warnings)
    hidden_confirmations = build_hidden_confirmations(current_snapshot)
    relationships = RelationshipEngine().detect(current_snapshot)
    playbook_review = PreviousPlaybookEngine().review(previous_snapshot, current_snapshot)
    evolution = MarketEvolutionEngine().build(history or [], current_snapshot, conviction, confidence)
    commentary = CommentaryEngine().build(
        current_snapshot,
        conviction,
        confidence,
        relationships,
        hidden_warnings,
        hidden_confirmations,
    )
    narrative = MarketIntelligenceEngine().build(
        current_snapshot,
        convergence,
        hidden_warnings,
        changes,
        conviction=conviction,
        confidence=confidence,
        checklist=checklist,
        scenarios=scenarios,
        hidden_confirmations=hidden_confirmations,
        commentary=commentary,
        relationships=relationships,
    )
    return {
        "changes": changes,
        "convergence": convergence,
        "hidden_warnings": hidden_warnings,
        "hidden_confirmations": hidden_confirmations,
        "relationships": relationships,
        "conviction": conviction,
        "checklist": checklist,
        "confidence": confidence,
        "scenarios": scenarios,
        "playbook_review": playbook_review,
        "evolution": evolution,
        "commentary": commentary,
        "narrative": narrative,
    }


def add_score_change(
    items: list[dict[str, Any]],
    label: str,
    previous: dict[str, Any],
    current: dict[str, Any],
    path: tuple[str, ...],
    threshold: float,
    lower_is_better: bool,
) -> None:
    before = number(get_path(previous, *path))
    after = number(get_path(current, *path))
    if before is None or after is None:
        return
    delta = after - before
    if abs(delta) < threshold:
        return
    direction = "improving" if (delta < 0 if lower_is_better else delta > 0) else "weakening"
    reason = explain_score_change(label, direction, delta)
    items.append({
        "label": label,
        "previous": round(before, 1),
        "current": round(after, 1),
        "delta": round(delta, 1),
        "direction": direction,
        "importance": "Critical" if abs(delta) >= threshold * 2 else "High",
        "reason": reason,
    })


def rank_changes(label: str, previous_items: list[dict[str, Any]], current_items: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    previous_rank = {item.get("name"): index + 1 for index, item in enumerate(previous_items)}
    output = []
    for index, item in enumerate(current_items[:limit], 1):
        name = item.get("name")
        before = previous_rank.get(name)
        if before is None:
            output.append({"label": f"{label}: {name}", "previous": "Unranked", "current": f"#{index}", "direction": "new", "importance": "High", "reason": f"{name} entered the top leadership group."})
        elif index == 1 and before != 1:
            output.append({"label": f"{label}: {name}", "previous": f"#{before}", "current": "#1", "direction": "improving", "importance": "High", "reason": f"{name} became the leading group."})
        elif abs(before - index) >= 2:
            direction = "improving" if index < before else "weakening"
            output.append({"label": f"{label}: {name}", "previous": f"#{before}", "current": f"#{index}", "direction": direction, "importance": "Medium", "reason": f"{name} ranking is {direction} within the leadership table."})
    return output[:4]


def watchlist_changes(previous_items: list[dict[str, Any]], current_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    previous_by_symbol = {item.get("symbol"): item for item in previous_items}
    output = []
    for item in current_items:
        symbol = item.get("symbol")
        before = previous_by_symbol.get(symbol)
        if not symbol or not before:
            continue
        for key, label in [("setup", "Setup"), ("trend", "Trend"), ("risk", "Risk")]:
            previous_value = before.get(key)
            current_value = item.get(key)
            if previous_value and current_value and previous_value != current_value:
                output.append({"label": f"{symbol} {label}", "previous": previous_value, "current": current_value, "direction": "changed", "importance": "High", "reason": f"{symbol} {label.lower()} changed from {previous_value} to {current_value}."})
                break
    return output[:5]


def macro_changes(previous: dict[str, Any], current: dict[str, Any]) -> list[dict[str, Any]]:
    previous_events = set(previous.get("events") or [])
    output = []
    for event in current.get("events") or []:
        if event not in previous_events:
            output.append({"label": "Macro Event", "previous": "Not listed", "current": event, "direction": "new", "importance": "Medium", "reason": f"{event} is now part of the next-session risk calendar."})
    return output[:3]


def get_ranked_items(dashboard: Any, key: str, fallback: Any = None) -> list[dict[str, Any]]:
    if isinstance(dashboard, dict) and isinstance(dashboard.get(key), list):
        source = dashboard.get(key) or []
        output = [
            {
                "name": item.get("name") or item.get("sector") or "N/A",
                "return": number((item.get("returns") or {}).get("1m")),
                "status": (item.get("metadata") or {}).get("status"),
            }
            for item in source
            if isinstance(item, dict)
        ]
    else:
        output = []
        for item in fallback or []:
            output.append(
                {
                    "name": getattr(item, "sector", None) or getattr(item, "name", None) or "N/A",
                    "return": number(getattr(item, "return_mtd", None) or getattr(item, "return_1m", None)),
                    "status": getattr(item, "status", None),
                }
            )
    return sorted(output, key=lambda item: number(item.get("return"), -999), reverse=True)


def normalize_watchlist_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "symbol": item.get("symbol") or item.get("ticker"),
        "changePercent": number(item.get("change_percent")),
        "setup": item.get("setup") or item.get("main_setup"),
        "trend": item.get("trend") or item.get("rating"),
        "risk": item.get("risk_flag"),
        "pattern": item.get("pattern_name"),
    }


def signal_check(label: str, passed: bool, value: Any) -> dict[str, Any]:
    return {"label": label, "passed": bool(passed), "status": "PASS" if passed else "FAIL", "value": value}


def get_path(value: dict[str, Any], *path: str) -> Any:
    current: Any = value
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def number(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def classify_risk(score: float | None) -> str:
    if score is None:
        return "Unavailable"
    if score < 35:
        return "Low"
    if score < 65:
        return "Moderate"
    return "High"


def first_name(items: list[dict[str, Any]], fallback: str) -> str:
    return str(items[0].get("name") or fallback) if items else fallback


def find_named_index(items: list[dict[str, Any]], symbol: str) -> dict[str, Any] | None:
    return next((item for item in items if item.get("symbol") == symbol), None)


def change_sort_key(item: dict[str, Any]) -> tuple[int, int]:
    importance = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    direction = {"weakening": 0, "changed": 1, "improving": 2, "new": 2, "unchanged": 4}
    return (importance.get(str(item.get("importance")), 9), direction.get(str(item.get("direction")), 9))


def normalize_score(value: Any) -> float:
    return max(0.0, min(100.0, number(value, 50) or 50))


def inverse_score(value: Any) -> float:
    return max(0.0, min(100.0, 100 - (number(value, 50) or 50)))


def sentiment_conviction(value: Any) -> float:
    sentiment = number(value, 50) or 50
    distance_from_neutral = abs(sentiment - 50)
    return max(35.0, min(100.0, 100 - distance_from_neutral * 1.4))


def rotation_score(items: list[dict[str, Any]]) -> float:
    if not items:
        return 50.0
    top_returns = [number(item.get("return"), 0) or 0 for item in items[:5]]
    positive = sum(1 for value in top_returns if value > 0)
    return min(100.0, 45 + positive * 9 + max(top_returns or [0]) * 4)


def conviction_rating(score: int) -> str:
    if score >= 90:
        return "Exceptional Alignment"
    if score >= 80:
        return "High Conviction"
    if score >= 70:
        return "Constructive"
    if score >= 60:
        return "Mixed"
    if score >= 40:
        return "Low Conviction"
    return "Defensive"


def conviction_summary(score: int) -> str:
    if score >= 90:
        return "Strong trend continuation"
    if score >= 80:
        return "Evidence supports the playbook"
    if score >= 70:
        return "Constructive but selective"
    if score >= 60:
        return "Mixed evidence"
    if score >= 40:
        return "Low conviction"
    return "Defensive posture"


def checklist_item(label: str, value: Any, pass_threshold: float, watch_threshold: float, higher_is_better: bool) -> dict[str, Any]:
    parsed = number(value, 0) or 0
    if higher_is_better:
        status = "Pass" if parsed >= pass_threshold else "Watch" if parsed >= watch_threshold else "Fail"
    else:
        status = "Pass" if parsed <= pass_threshold else "Watch" if parsed <= watch_threshold else "Fail"
    return {"label": label, "status": status, "value": round(parsed, 1), "reason": checklist_reason(label, status, parsed)}


def macro_checklist_score(state: object) -> int:
    return {
        "Strong Risk-On": 85,
        "Risk-On": 75,
        "Balanced": 60,
        "Defensive Rotation": 40,
        "Risk-Off": 25,
    }.get(state, 0)


def watchlist_confirmation_score(items: list[dict[str, Any]]) -> float:
    if not items:
        return 50.0
    changes = [number(item.get("changePercent"), 0) or 0 for item in items]
    positive = sum(1 for value in changes if value >= 0)
    return round((positive / len(changes)) * 100)


def build_hidden_confirmations(snapshot: dict[str, Any]) -> list[str]:
    signals = snapshot.get("signalSummary", {})
    confirmations = []
    if number(signals.get("trend"), 0) >= 65 and number(signals.get("breadth"), 0) >= 65:
        confirmations.append("Breadth confirms the prevailing trend.")
    if number(signals.get("risk"), 100) < 35:
        confirmations.append("Risk remains contained relative to the current playbook.")
    if number(signals.get("momentum"), 0) >= 65 and number(signals.get("volume"), 0) >= 65:
        confirmations.append("Momentum and volume are aligned.")
    return confirmations[:4]


def conviction_constraints(snapshot: dict[str, Any], warnings: list[str]) -> list[str]:
    signals = snapshot.get("signalSummary", {})
    constraints = []
    if number(signals.get("sentiment"), 0) >= 70:
        constraints.append("Sentiment remains elevated.")
    if number(signals.get("sectorStrength"), 0) < 70:
        constraints.append("Leadership is constructive but not broad enough for maximum conviction.")
    macro_risks = snapshot.get("macroSummary", {}).get("currentRisks") or []
    if macro_risks:
        constraints.append(str(macro_risks[0]))
    if warnings and warnings != ["No significant market contradictions detected."]:
        constraints.append(strip_terminal(warnings[0]))
    return constraints[:3] or ["No major constraint beyond normal market uncertainty."]


def conviction_supports(snapshot: dict[str, Any]) -> list[str]:
    signals = snapshot.get("signalSummary", {})
    supports = []
    if number(signals.get("breadth"), 0) >= 65:
        supports.append("Breadth confirms the trend.")
    if number(signals.get("trend"), 0) >= 60:
        supports.append("Trend remains intact.")
    if number(signals.get("risk"), 100) < 45:
        supports.append("Risk remains contained.")
    if number(signals.get("volume"), 0) >= 60:
        supports.append("Volume does not contradict the advance.")
    return supports[:3] or ["Some evidence still supports staying engaged."]


def explain_score_change(label: str, direction: str, delta: float) -> str:
    magnitude = abs(delta)
    if label == "Risk":
        if direction == "improving":
            return f"Risk improved by {magnitude:.1f} points, which increases room for selective exposure."
        return f"Risk worsened by {magnitude:.1f} points, which lowers the margin for aggressive positioning."
    if label == "Market Health":
        if direction == "improving":
            return f"Market health improved by {magnitude:.1f} points, confirming better trend or participation quality."
        return f"Market health fell by {magnitude:.1f} points, so the prior thesis needs more confirmation."
    if label == "Breadth":
        if direction == "improving":
            return f"Breadth improved by {magnitude:.1f} points, showing wider participation behind the move."
        return f"Breadth weakened by {magnitude:.1f} points, suggesting participation is narrowing."
    return f"{label} is {direction} by {magnitude:.1f} points."


def checklist_reason(label: str, status: str, value: float) -> str:
    if label == "Trend intact":
        return "Trend remains above the report's intermediate support threshold." if status == "Pass" else "Trend support is not strong enough for a clean pass."
    if label == "Breadth confirms":
        return "Participation supports the index move." if status == "Pass" else "Participation is not broad enough for full confirmation."
    if label == "Leadership broad":
        return "Leadership supports the playbook." if status == "Pass" else "Leadership remains somewhat concentrated."
    if label == "Risk acceptable":
        return "Risk is contained relative to the current stance." if status == "Pass" else "Risk is high enough to limit aggression."
    if label == "Volatility acceptable":
        return "Volatility is not disrupting trend." if status == "Pass" else "Volatility requires monitoring."
    if label == "Macro risk":
        return "Macro conditions are manageable but event risk remains." if status != "Fail" else "Macro risk is elevated."
    if label == "Watchlist confirms":
        return "Saved names broadly support the market read." if status == "Pass" else "Watchlist action is mixed."
    return f"Checklist value: {value:.1f}."


def build_tradeoff(snapshot: dict[str, Any], warnings: list[str], confirmations: list[str]) -> dict[str, Any]:
    pros = confirmations[:3] or ["Trend and leadership provide some support."]
    cons = []
    if warnings and warnings != ["No significant market contradictions detected."]:
        cons.extend(warnings[:2])
    if number(get_path(snapshot, "signalSummary", "sentiment"), 0) >= 70:
        cons.append("Sentiment reduces the reward for late entries.")
    macro_risks = snapshot.get("macroSummary", {}).get("currentRisks") or []
    if macro_risks:
        cons.append(str(macro_risks[0]))
    cons = cons[:3] or ["No major offsetting risk beyond normal market uncertainty."]
    overall = "Pros currently outweigh risks." if len(pros) >= len(cons) else "Risks are beginning to offset the positive evidence."
    return {"pros": pros, "cons": cons, "overall": overall}


def build_historical_context(snapshot: dict[str, Any]) -> dict[str, Any]:
    metrics = snapshot.get("historicalMetrics", {})
    return {
        "health": f"Current health score is {format_metric(metrics.get('health'))}.",
        "risk": f"Current risk score is {format_metric(metrics.get('risk'))}.",
        "breadth": f"Current breadth score is {format_metric(metrics.get('breadth'))}.",
        "leader": f"{metrics.get('sectorLeader') or 'Sector leadership'} leads the sector ranking.",
    }


def strip_terminal(text: Any) -> str:
    return str(text or "").strip().rstrip(".!?")


def format_metric(value: Any) -> str:
    parsed = number(value)
    return "N/A" if parsed is None else f"{parsed:.0f}"


def build_historical_metrics(snapshot: dict[str, Any]) -> dict[str, Any]:
    sectors = snapshot.get("sectorRanking", [])
    watchlist = snapshot.get("watchlistSummary", [])
    return {
        "reportId": snapshot.get("reportId"),
        "marketDate": snapshot.get("marketDate"),
        "regime": snapshot.get("regime"),
        "health": number(get_path(snapshot, "marketHealth", "score")),
        "risk": number(get_path(snapshot, "risk", "score")),
        "breadth": number(get_path(snapshot, "breadth", "score")),
        "leadership": number(get_path(snapshot, "signalSummary", "sectorStrength")),
        "conviction": snapshot.get("conviction"),
        "confidence": snapshot.get("confidence"),
        "playbook": get_path(snapshot, "playbook", "headline"),
        "sectorLeader": first_name(sectors, None) if sectors else None,
        "sectorLaggard": first_name([sectors[-1]], None) if sectors else None,
        "volatilityState": snapshot.get("volatilityState"),
        "researchFocus": snapshot.get("researchFocus"),
        "topIdea": get_path(watchlist[0], "symbol") if watchlist else None,
    }
