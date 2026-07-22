from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.services.copilot_context_builder import (
    build_context_labels,
    generated_at,
    get_context_source_state,
    sanitize_copilot_context,
)
from app.services.copilot_entities import resolve_comparison_entities
from app.services.copilot_formatting import (
    UNAVAILABLE_LABEL,
    compact_answer,
    compact_sentence_list,
    format_copilot_label,
    format_copilot_value,
)
from app.services.copilot_prompt_builder import COPILOT_SYSTEM_PROMPT, build_copilot_payload
from app.services.copilot_reasoning import StrategicReasoningEngine
from app.services.copilot_safety import FINANCIAL_DISCLAIMER, asks_for_personalized_advice
from app.services.openai_client import generate_structured_chat_response
from app.services.theme_intelligence import enrich_copilot_theme_context


def answer_copilot_chat(
    message: str,
    context: dict[str, Any],
    history: list[dict[str, str]] | None = None,
    thread_id: str | None = None,
) -> dict[str, Any]:
    normalized_message = " ".join(message.strip().split())
    sanitized_context = enrich_copilot_theme_context(normalized_message, sanitize_copilot_context(context))
    fallback = build_rule_copilot_response(normalized_message, sanitized_context, history)
    openai_response = generate_structured_chat_response(
        COPILOT_SYSTEM_PROMPT,
        build_copilot_payload(normalized_message, sanitized_context, fallback, history),
    )
    response = merge_openai_response(fallback, openai_response) if openai_response else fallback
    source_state = get_context_source_state(sanitized_context)
    context_used = build_context_labels(sanitized_context)
    return {
        "threadId": thread_id or f"copilot-{uuid4().hex[:12]}",
        "answer": response["answer"],
        "answerSections": response.get("answer_sections"),
        "grounding": {
            "contextUsed": context_used,
            "sourceState": source_state,
            "generatedAt": generated_at(),
        },
        "suggestedFollowUps": build_follow_ups(normalized_message, sanitized_context),
        "confidence": response.get("confidence", 68),
        "answerConfidence": build_answer_confidence(sanitized_context, response),
        "generatedBy": response.get("generated_by", "rules"),
        "disclaimer": response.get("disclaimer", ""),
    }


def build_rule_copilot_response(
    message: str,
    context: dict[str, Any],
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    lowered = message.lower()
    intent = "context"
    if "conviction" in lowered:
        intent = "conviction"
        answer, points, risks, watch = explain_conviction(context)
    elif "what changed" in lowered or "changed since" in lowered:
        intent = "changes"
        answer, points, risks, watch = explain_changes(context)
    elif "rank" in lowered and "watchlist" in lowered:
        intent = "rank_watchlist"
        answer, points, risks, watch = rank_watchlist(context)
    elif "compare" in lowered or " vs " in lowered:
        intent = "compare"
        answer, points, risks, watch = compare_entities(message, context)
    elif "invalidate" in lowered or "invalid" in lowered:
        intent = "invalidation"
        answer, points, risks, watch = explain_invalidation(context)
    elif "risk" in lowered:
        intent = "risk"
        answer, points, risks, watch = explain_risk(context)
    elif "leading" in lowered or "sector" in lowered or "theme" in lowered:
        intent = "leadership"
        answer, points, risks, watch = explain_leadership(context)
    else:
        intent = infer_intent_from_memory(message, history)
        if intent == "conviction":
            answer, points, risks, watch = explain_conviction(context)
        elif intent == "risk":
            answer, points, risks, watch = explain_risk(context)
        elif intent == "rank_watchlist":
            answer, points, risks, watch = rank_watchlist(context)
        elif intent == "leadership":
            answer, points, risks, watch = explain_leadership(context)
        else:
            answer, points, risks, watch = explain_context(context)

    if asks_for_personalized_advice(message):
        answer = (
            "I cannot give personal buy, sell, allocation, or options instructions. "
            f"{answer}"
        )

    source_note = source_state_note(get_context_source_state(context))
    if source_note and get_context_source_state(context) in {"stale", "unavailable"}:
        risks = [source_note, *risks]

    strategic = StrategicReasoningEngine(context, history).build(
        message=message,
        intent=intent,
        base_answer=answer,
        points=points,
        risks=risks,
        watch=watch,
    )
    answer = strategic.direct_answer
    points = strategic.evidence
    risks = [strategic.counterargument, *risks]
    watch = strategic.conditions

    answer = compact_answer(answer, max_words=160)

    compact_risks = compact_sentence_list(risks, 1)

    return {
        "type": "ai_chat_response",
        "answer": answer,
        "answer_sections": {
            "directAnswer": answer,
            "why": compact_sentence_list(points, 3),
            "mainCaution": compact_risks[0] if compact_risks else None,
            "whatWouldChange": compact_sentence_list(watch, 2),
        },
        "key_points": compact_sentence_list(points, 3),
        "risks": compact_sentence_list(risks, 2),
        "what_to_watch": compact_sentence_list(watch, 2),
        "strategic_narrative": strategic.narrative,
        "decision_context": strategic.decision_context,
        "strategic_confidence_reasons": strategic.confidence_reasons,
        "related_symbols": extract_related_symbols(context),
        "confidence": 72 if get_context_source_state(context) not in {"unavailable", "stale"} else 55,
        "generated_by": "rules",
        "disclaimer": FINANCIAL_DISCLAIMER,
    }


def explain_conviction(context: dict[str, Any]) -> tuple[str, list[str], list[str], list[str]]:
    conviction = find_first_dict(context, ["focusedMetric", "report.marketConviction", "report.market_conviction", "market.conviction", "market.marketConviction"])
    confidence = find_first_dict(context, ["report.confidence", "report.recommendation_confidence", "market.confidence"])
    score = value_at(conviction, "score") or value_at(context.get("focusedMetric"), "value") or "N/A"
    rating = value_at(conviction, "rating") or value_at(context.get("focusedMetric"), "status") or "N/A"
    why_not_higher = list_of_text(value_at(conviction, "whyNotHigher") or value_at(conviction, "why_not_higher"))
    why_not_lower = list_of_text(value_at(conviction, "whyNotLower") or value_at(conviction, "why_not_lower"))
    contributors = list_of_dicts(value_at(conviction, "contributors"))[:4]
    contributor_text = [
        f"{format_copilot_label(item.get('label', 'Signal'))}: {format_copilot_value(item.get('score'))}/100"
        for item in contributors
    ]
    answer = (
        f"Conviction is {score}/100 ({format_copilot_label(rating)}) because the supporting signals are aligned, but not broad enough to remove pullback risk."
    )
    points = contributor_text or ["Conviction uses the report's structured signal components."]
    risks = why_not_higher or ["The limiting factors are not available in the current context."]
    watch = ["Broader leadership", "Stronger trend quality", "Lower sentiment pressure"]
    if why_not_lower:
        points.extend(why_not_lower[:1])
    return answer, points, risks, watch


def explain_changes(context: dict[str, Any]) -> tuple[str, list[str], list[str], list[str]]:
    changes = find_first_dict(context, ["report.reportChanges", "report.report_changes", "report.meaningfulChanges", "market.changes"])
    items = list_of_dicts(value_at(changes, "items"))[:5]
    if not items:
        return (
            "I do not see meaningful previous-report change data in the current context.",
            ["No stored comparison items were provided."],
            ["A generated previous report snapshot may be required."],
            ["Generate and save reports over time to improve change analysis."],
        )
    points = [
        f"{format_copilot_label(item.get('label', 'Change'))}: {item.get('reason') or item.get('current') or 'changed'}"
        for item in items
    ]
    return (
        "The meaningful changes are the items that moved enough to alter the market read, not every small metric fluctuation.",
        points,
        [item.get("label", "Change") for item in items if item.get("direction") in {"weakening", "changed"}],
        ["Watch whether these changes persist in the next report snapshot."],
    )


def rank_watchlist(context: dict[str, Any]) -> tuple[str, list[str], list[str], list[str]]:
    items = get_watchlist_items(context)
    if not items:
        return (
            "I do not have enough watchlist data in the current context to rank the saved names reliably.",
            ["Watchlist context is unavailable."],
            ["Ranking would be incomplete without saved item signals."],
            ["Open Copilot from the Watchlist screen after data loads."],
        )
    ranked_context = [score_watchlist_item(item) for item in items]
    meaningful = [item for item in ranked_context if item["availableDimensions"] >= 2]
    if not meaningful:
        performance_order = sorted(
            items,
            key=lambda item: -safe_number(item.get("changePercent") or item.get("change_percent"), -999),
        )[:5]
        return (
            "There is not enough analytical data to produce a meaningful watchlist ranking. I can only show a simple daily-performance ordering from the loaded context.",
            [f"{item.get('ticker') or item.get('symbol')}: daily change {format_copilot_value(item.get('changePercent') or item.get('change_percent'))}" for item in performance_order],
            ["Ranking quality is limited because setup, risk, trend, or alignment fields are missing."],
            ["Load stock detail data or refresh watchlist signals for a higher-quality ranking."],
        )
    ranked = sorted(meaningful, key=lambda item: (-item["score"], item["ticker"]))[:5]
    points = [
        f"{item['ticker']} — {item['category']}: {item['reason']}"
        for item in ranked
    ]
    top_names = ", ".join(item["ticker"] for item in ranked[:3])
    completeness = "moderate" if any(item["completeness"] != "high" for item in ranked) else "high"
    return (
        f"The strongest watchlist names are {top_names}. Ranking uses loaded trend, signal, setup, risk, and alignment fields; daily change is only a minor input.",
        points,
        [f"Ranking confidence is {completeness} because some stock-level fields may be incomplete."],
        ["Re-check ranking if market health, sector leadership, or the stock's signal changes."],
    )


def compare_entities(message: str, context: dict[str, Any]) -> tuple[str, list[str], list[str], list[str]]:
    matches, missing = resolve_comparison_entities(message, context)
    if len(matches) < 2:
        return (
            "I do not have enough structured data to compare those entities meaningfully.",
            ["One or both comparison entities could not be resolved."],
            [f"Missing entity data: {', '.join(missing) if missing else 'comparison peer'}"],
            ["Open Copilot from a stock, sector, theme, or watchlist context with the compared entities loaded."],
        )
    left, right = matches[0], matches[1]
    left_name = str(left.get("displayName") or left.get("id"))
    right_name = str(right.get("displayName") or right.get("id"))
    winners = comparison_winners(left, right)
    points = winners or [describe_comparison_entity(left), describe_comparison_entity(right)]
    gap = comparison_gap(left, right)
    winner_names = [item.split(": ", 1)[1] for item in winners[:2] if ": " in item and "No clear winner" not in item]
    bottom_line = (
        f"{winner_names[0]} has the better common-field profile"
        if winner_names
        else "Neither side has a decisive edge from the loaded fields"
    )
    return (
        f"{left_name} vs {right_name}: {bottom_line}. Treat missing fields as data gaps rather than conclusions.",
        points,
        [gap] if gap else ["The comparison is limited to fields available from current app engines."],
        ["The preferred setup depends on whether momentum quality or risk control is the priority."],
    )


def explain_invalidation(context: dict[str, Any]) -> tuple[str, list[str], list[str], list[str]]:
    invalidation = list_of_text(value_at(context, "report.invalidation") or value_at(context, "report.reportNarrative.invalidation") or value_at(context, "market.invalidation"))
    focused = context.get("focusedMetric") if isinstance(context.get("focusedMetric"), dict) else {}
    supporting = list_of_text(value_at(focused, "relatedRisks"))
    watch = invalidation or supporting or [
        "Breadth deterioration",
        "Volatility expansion",
        "Leadership narrowing",
        "Loss of key support or trend confirmation",
    ]
    return (
        "The current view weakens if the evidence supporting the playbook stops agreeing.",
        ["Invalidation should be treated as a condition to monitor, not a prediction."],
        watch,
        watch[:3],
    )


def explain_risk(context: dict[str, Any]) -> tuple[str, list[str], list[str], list[str]]:
    risk = find_first_dict(context, ["market.risk", "report.risk", "market.riskDashboard", "report.risk_dashboard"])
    score = risk.get("score", value_at(context, "focusedMetric.value"))
    status = risk.get("status", value_at(context, "focusedMetric.status"))
    contributors = list_of_dicts(risk.get("contributors"))[:4]
    points = [
        f"{item.get('label') or item.get('name')}: {item.get('explanation') or item.get('value') or item.get('score')}"
        for item in contributors
    ] or ["Risk combines volatility, breadth, sentiment, macro, liquidity, and concentration where available."]
    return (
        f"Risk is {status or 'unavailable'} with a score of {score if score is not None else 'N/A'} because volatility, breadth, sentiment, and concentration are not exerting equal pressure.",
        points,
        list_of_text(risk.get("warnings")) or ["Risk can change quickly if volatility or breadth deteriorates."],
        ["Watch volatility, breadth participation, leadership concentration, and macro events."],
    )


def explain_leadership(context: dict[str, Any]) -> tuple[str, list[str], list[str], list[str]]:
    sector = find_focused_group(context)
    name = sector.get("name") or sector.get("sector") or sector.get("theme") or value_at(context, "focusedMetric.title") or "This group"
    if sector.get("theme_id"):
        performance = sector.get("performance") if isinstance(sector.get("performance"), dict) else {}
        relative_strength = sector.get("relative_strength") if isinstance(sector.get("relative_strength"), dict) else {}
        breadth = sector.get("breadth") if isinstance(sector.get("breadth"), dict) else {}
        participation = sector.get("participation") if isinstance(sector.get("participation"), dict) else {}
        concentration = sector.get("concentration") if isinstance(sector.get("concentration"), dict) else {}
        score = sector.get("absolute_composite_score")
        rank = sector.get("rank")
        points = [
            f"Absolute composite score: {format_copilot_value(score)} / 100; rank #{format_copilot_value(rank)} in the active pilot.",
            f"Returns: 1M {format_copilot_value(performance.get('1m'))} and 3M {format_copilot_value(performance.get('3m'))}; 1M RS versus SPY {format_copilot_value(relative_strength.get('vs_spy_1m'))}.",
            f"Breadth above EMA50: {format_copilot_value(breadth.get('percent_above_ema50'))}; positive-return participation: {format_copilot_value(participation.get('positive_return_participation_pct'))}%; concentration: {format_copilot_label(concentration.get('classification'))} (HHI {format_copilot_value(concentration.get('concentration_hhi'))}).",
        ]
        cautions = list_of_text(sector.get("warnings")) or ["Historical returns use the current reviewed basket until historical membership versions are available."]
        return (
            f"{name} is {format_copilot_label(sector.get('classification'))} in the live ThemeSnapshot because its audited absolute composite is {format_copilot_value(score)} / 100, with rank #{format_copilot_value(rank)} among the active reviewed pilot themes.",
            points,
            cautions,
            ["Watch whether relative strength, breadth, participation, and concentration remain consistent in the next immutable ThemeSnapshot."],
        )
    performance = sector.get("performance") or sector.get("return") or sector.get("selectedReturn")
    rotation = sector.get("rotation") or sector.get("quadrant") or sector.get("status") or sector.get("primaryStatus")
    breadth = sector.get("breadth") or sector.get("breadthStatus")
    relative_strength = sector.get("relativeStrength") or sector.get("relative_strength") or sector.get("relativeStrengthScore")
    points = [
        f"Performance: {format_copilot_value(performance)}",
        f"Relative strength: {format_copilot_value(relative_strength)}",
        f"Rotation: {format_copilot_label(rotation)}",
    ]
    if breadth is not None:
        points.append(f"Breadth: {format_copilot_value(breadth)}")
    return (
        f"{name} is leading because performance, relative strength, and rotation evidence are carrying more sponsorship than the peer set.",
        points,
        ["Leadership weakens if relative momentum fades or gains become concentrated."],
        ["Watch rotation status, breadth participation, and whether constituents confirm the move."],
    )


def explain_context(context: dict[str, Any]) -> tuple[str, list[str], list[str], list[str]]:
    screen = context.get("screenTitle") or context.get("screenType") or "current screen"
    focused = context.get("focusedMetric") if isinstance(context.get("focusedMetric"), dict) else None
    if focused:
        title = focused.get("title", "this metric")
        value = focused.get("value", "N/A")
        status = focused.get("status", "N/A")
        answer = f"{title} is {value} ({status}). The interpretation should come from the supporting evidence in this screen."
        points = list_of_text(focused.get("supportingEvidence")) or ["Focused metric evidence is limited in the current context."]
        risks = list_of_text(focused.get("relatedRisks")) or ["No specific related risks were provided."]
        watch = ["Watch the inputs that feed this metric and any source-state warnings."]
        return answer, points, risks, watch
    return (
        f"I am using the context from {screen}. Ask about a score, card, report section, stock, sector, theme, or watchlist ranking for a more specific explanation.",
        build_context_labels(context),
        ["Some details may be unavailable if the screen has not loaded them yet."],
        build_follow_ups("", context)[:3],
    )


def merge_openai_response(fallback: dict[str, Any], candidate: dict[str, Any] | None) -> dict[str, Any]:
    if not candidate:
        return fallback
    merged_answer = compact_answer(candidate.get("answer") or fallback["answer"], max_words=180)
    return {
        **fallback,
        "answer": merged_answer,
        "answer_sections": {
            **(fallback.get("answer_sections") or {}),
            "directAnswer": merged_answer,
            "why": compact_sentence_list(candidate.get("key_points") or fallback["key_points"], 3),
            "mainCaution": compact_sentence_list(candidate.get("risks") or fallback["risks"], 1)[0]
            if compact_sentence_list(candidate.get("risks") or fallback["risks"], 1)
            else None,
            "whatWouldChange": compact_sentence_list(candidate.get("what_to_watch") or fallback["what_to_watch"], 2),
        },
        "key_points": candidate.get("key_points") or fallback["key_points"],
        "risks": candidate.get("risks") or fallback["risks"],
        "what_to_watch": candidate.get("what_to_watch") or fallback["what_to_watch"],
        "related_symbols": candidate.get("related_symbols") or fallback["related_symbols"],
        "confidence": candidate.get("confidence") or fallback["confidence"],
        "generated_by": "openai",
        "disclaimer": candidate.get("disclaimer") or fallback["disclaimer"],
    }


def build_follow_ups(message: str, context: dict[str, Any]) -> list[str]:
    screen_type = str(context.get("screenType") or context.get("screen_type") or "general")
    if "conviction" in message.lower() or screen_type == "report":
        return ["What would increase Conviction?", "Explain the hidden warnings.", "What changed since the previous report?"]
    if screen_type == "watchlist":
        return ["Rank my watchlist.", "Which name needs attention?", "Compare my top two names."]
    if screen_type == "stock":
        return ["What is the main risk?", "Is this setup extended?", "What would invalidate the setup?"]
    if screen_type in {"sector", "theme"}:
        return ["Is leadership broad or concentrated?", "What would weaken this group?", "Compare with another leader."]
    return ["Why is Conviction not higher?", "What is the main risk?", "What would invalidate today's view?"]


def source_state_note(source_state: str) -> str:
    if source_state == "mock":
        return "Mock context; treat this as a workflow demonstration rather than a live market view."
    if source_state == "mixed":
        return "Analysis uses a mixture of mock and available provider data."
    if source_state == "stale":
        return "Some inputs may be stale."
    if source_state == "unavailable":
        return "I do not have enough current app data to answer every part reliably."
    return ""


def find_first_dict(context: dict[str, Any], paths: list[str]) -> dict[str, Any]:
    for path in paths:
        value = value_at(context, path)
        if isinstance(value, dict):
            return value
    return {}


def value_at(value: Any, path: str) -> Any:
    current = value
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def list_of_text(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item is not None][:8]
    if isinstance(value, str) and value:
        return [value]
    return []


def list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def get_watchlist_items(context: dict[str, Any]) -> list[dict[str, Any]]:
    watchlist = context.get("watchlist")
    if isinstance(watchlist, dict):
        items = watchlist.get("items") or watchlist.get("savedItems") or watchlist.get("leaders")
        return list_of_dicts(items)
    report_items = value_at(context, "report.watchlistRanking") or value_at(context, "report.watchlist_summary.items")
    return list_of_dicts(report_items)


def extract_related_symbols(context: dict[str, Any]) -> list[str]:
    symbols = []
    for item in get_watchlist_items(context)[:6]:
        symbol = item.get("ticker") or item.get("symbol")
        if symbol:
            symbols.append(str(symbol).upper())
    stock_symbol = value_at(context, "stock.symbol")
    if stock_symbol:
        symbols.insert(0, str(stock_symbol).upper())
    return list(dict.fromkeys(symbols))[:6]


def extract_requested_entities(message: str) -> set[str]:
    return {token.strip(".,?!:;()[]").upper() for token in message.split() if token.strip(".,?!:;()[]").isalpha() and 1 <= len(token.strip(".,?!:;()[]")) <= 5}


def describe_entity(item: dict[str, Any]) -> str:
    name = item.get("ticker") or item.get("symbol") or item.get("name") or "Entity"
    score = item.get("score") or item.get("overall_score") or item.get("relativeStrength")
    signal = item.get("signal") or item.get("rating") or item.get("status") or item.get("main_setup")
    risk = item.get("risk") or item.get("risk_level") or item.get("riskState")
    return f"{name}: {signal or 'no signal provided'}; score {score if score is not None else 'N/A'}; risk {risk or 'N/A'}."


def safe_number(value: Any, default: float) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def build_answer_confidence(context: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    source_state = get_context_source_state(context)
    reasons: list[str] = list(response.get("strategic_confidence_reasons") or [])
    if response.get("generated_by") == "openai":
        reasons.append("Model wording was checked against the structured app context.")
    else:
        reasons.append("Answer was generated from deterministic app context.")

    context_labels = build_context_labels(context)
    if len(context_labels) >= 2:
        reasons.append("Multiple context fields were available.")
    elif context_labels:
        reasons.append("Only a narrow slice of screen context was available.")
    else:
        reasons.append("Very little screen context was available.")

    if source_state in {"live", "cached", "delayed"}:
        level = "high"
        reasons.append(f"Source state is {format_copilot_label(source_state)}.")
    elif source_state in {"mock", "mixed"}:
        level = "moderate"
        reasons.append(f"Source state is {format_copilot_label(source_state)}.")
    else:
        level = "limited"
        reasons.append(f"Source state is {format_copilot_label(source_state)}.")

    if any(UNAVAILABLE_LABEL.lower() in str(item).lower() for item in response.get("key_points", [])):
        level = "limited"
        reasons.append("Some requested fields were unavailable.")

    return {"level": level, "reasons": compact_sentence_list(reasons, 3)}


def infer_intent_from_memory(message: str, history: list[dict[str, str]] | None) -> str:
    lowered = message.lower()
    if "that" not in lowered and "this" not in lowered:
        return "context"
    recent = " ".join(str(item.get("content", "")) for item in (history or [])[-4:]).lower()
    if "conviction" in recent:
        return "conviction"
    if "risk" in recent:
        return "risk"
    if "watchlist" in recent or "rank" in recent:
        return "rank_watchlist"
    if "compare" in recent or " vs " in recent:
        return "compare"
    if "sector" in recent or "theme" in recent or "technology" in recent or "financial" in recent:
        return "leadership"
    return "context"


def score_watchlist_item(item: dict[str, Any]) -> dict[str, Any]:
    ticker = str(item.get("ticker") or item.get("symbol") or "Unknown").upper()
    raw_score = safe_number(item.get("score") or item.get("overall_score"), 0)
    daily_change = safe_number(item.get("changePercent") or item.get("change_percent"), 0)
    signal = format_copilot_label(item.get("signal") or item.get("primarySignal") or item.get("main_setup") or item.get("rating"))
    risk = format_copilot_label(item.get("risk") or item.get("risk_flag") or item.get("riskLevel"))
    trend = format_copilot_label(item.get("trend") or item.get("trend_status") or item.get("status"))
    alignment = format_copilot_label(item.get("alignment") or item.get("market_alignment") or item.get("group"))
    volume = format_copilot_label(item.get("volume") or item.get("volumeSignal") or item.get("volume_signal"))

    score = raw_score * 0.45
    dimensions = 0

    positive_terms = ("breakout", "momentum", "strong", "leader", "constructive", "bullish", "high priority")
    warning_terms = ("risk", "weak", "lost", "laggard", "bearish", "stale", "unavailable")

    for value, weight in (
        (signal, 22),
        (trend, 16),
        (alignment, 12),
        (volume, 8),
    ):
        lowered = value.lower()
        if value != UNAVAILABLE_LABEL:
            dimensions += 1
        if any(term in lowered for term in positive_terms):
            score += weight
        if any(term in lowered for term in warning_terms):
            score -= weight

    if risk != UNAVAILABLE_LABEL:
        dimensions += 1
        if any(term in risk.lower() for term in ("low", "contained", "moderate")):
            score += 8
        if any(term in risk.lower() for term in ("high", "elevated", "risk", "weak")):
            score -= 14

    if item.get("score") is not None or item.get("overall_score") is not None:
        dimensions += 1

    score += max(min(daily_change, 8), -8) * 0.8
    category = signal if signal != UNAVAILABLE_LABEL else trend
    if category == UNAVAILABLE_LABEL:
        category = "Loaded signals"

    reason_parts = [
        part
        for part in (
            f"signal {signal}" if signal != UNAVAILABLE_LABEL else None,
            f"trend {trend}" if trend != UNAVAILABLE_LABEL else None,
            f"risk {risk}" if risk != UNAVAILABLE_LABEL else None,
        )
        if part
    ]
    reason = "; ".join(reason_parts[:3]) or "limited analytical fields loaded"

    return {
        "ticker": ticker,
        "score": round(score, 1),
        "availableDimensions": dimensions,
        "completeness": "high" if dimensions >= 4 else "moderate" if dimensions >= 2 else "limited",
        "category": category,
        "reason": reason,
    }


def describe_comparison_entity(entity: dict[str, Any]) -> str:
    name = str(entity.get("displayName") or entity.get("id") or "Entity")
    fields = [
        f"score {format_copilot_value(entity.get('score'))}",
        f"signal {format_copilot_label(entity.get('signal'))}",
        f"risk {format_copilot_label(entity.get('risk'))}",
        f"relative strength {format_copilot_value(entity.get('relativeStrength'))}",
        f"momentum {format_copilot_label(entity.get('momentum'))}",
    ]
    return f"{name}: " + "; ".join(fields[:5])


def comparison_winners(left: dict[str, Any], right: dict[str, Any]) -> list[str]:
    left_name = str(left.get("displayName") or left.get("id"))
    right_name = str(right.get("displayName") or right.get("id"))
    categories = [
        ("Conviction", compare_numeric_field(left, right, "score")),
        ("Momentum", compare_text_strength(left, right, "momentum")),
        ("Risk", compare_risk_field(left, right)),
        ("Entry quality", compare_text_strength(left, right, "setup")),
        ("Sector/theme alignment", compare_text_strength(left, right, "signal")),
    ]
    output = []
    for label, winner in categories:
        if winner == "left":
            output.append(f"{label}: {left_name}")
        elif winner == "right":
            output.append(f"{label}: {right_name}")
        elif winner == "tie":
            output.append(f"{label}: No clear winner")
        if len(output) >= 5:
            break
    return output


def compare_numeric_field(left: dict[str, Any], right: dict[str, Any], field: str) -> str | None:
    left_value = safe_number(left.get(field), -999)
    right_value = safe_number(right.get(field), -999)
    if left_value == -999 or right_value == -999:
        return None
    if abs(left_value - right_value) < 3:
        return "tie"
    return "left" if left_value > right_value else "right"


def compare_text_strength(left: dict[str, Any], right: dict[str, Any], field: str) -> str | None:
    left_score = text_strength_score(left.get(field))
    right_score = text_strength_score(right.get(field))
    if left_score is None or right_score is None:
        return None
    if abs(left_score - right_score) <= 1:
        return "tie"
    return "left" if left_score > right_score else "right"


def compare_risk_field(left: dict[str, Any], right: dict[str, Any]) -> str | None:
    left_score = risk_text_score(left.get("risk"))
    right_score = risk_text_score(right.get("risk"))
    if left_score is None or right_score is None:
        return None
    if abs(left_score - right_score) <= 1:
        return "tie"
    return "left" if left_score > right_score else "right"


def text_strength_score(value: Any) -> int | None:
    text = str(value or "").lower()
    if not text or UNAVAILABLE_LABEL.lower() in text:
        return None
    score = 0
    for term, points in (
        ("breakout", 5),
        ("strong", 4),
        ("bullish", 4),
        ("constructive", 3),
        ("improving", 3),
        ("watching", 1),
        ("neutral", 0),
        ("weak", -3),
        ("lagging", -4),
        ("bearish", -4),
    ):
        if term in text:
            score += points
    return score


def risk_text_score(value: Any) -> int | None:
    text = str(value or "").lower()
    if not text or UNAVAILABLE_LABEL.lower() in text:
        return None
    if "low" in text or "contained" in text:
        return 4
    if "moderate" in text or "manageable" in text:
        return 2
    if "high" in text or "elevated" in text:
        return -3
    if "risk" in text:
        return -1
    return 0


def comparison_gap(left: dict[str, Any], right: dict[str, Any]) -> str | None:
    comparable_fields = ("score", "signal", "risk", "relativeStrength", "momentum", "volumeState", "setup")
    missing = []
    for field in comparable_fields:
        if left.get(field) in (None, "", UNAVAILABLE_LABEL) or right.get(field) in (None, "", UNAVAILABLE_LABEL):
            missing.append(format_copilot_label(field))
    if not missing:
        return None
    return "Data gap: " + ", ".join(missing[:3]) + (" are incomplete." if len(missing) == 1 else " are incomplete.")


def find_focused_group(context: dict[str, Any]) -> dict[str, Any]:
    for path in (
        "sector.focused",
        "theme.focused",
        "sector.selected",
        "theme.selected",
        "focusedGroup",
        "focusedMetric.calculationInputs.group",
    ):
        value = value_at(context, path)
        if isinstance(value, dict):
            return value

    focused_title = value_at(context, "focusedMetric.title")
    for collection_path in ("sector.sectors", "sector.themes", "theme.themes", "market.sectors", "market.themes"):
        collection = value_at(context, collection_path)
        if not isinstance(collection, list):
            continue
        for item in collection:
            if isinstance(item, dict) and focused_title and str(item.get("name") or "").lower() == str(focused_title).lower():
                return item
        if collection and isinstance(collection[0], dict):
            return collection[0]

    sector = context.get("sector")
    if isinstance(sector, dict):
        return sector
    theme = context.get("theme")
    if isinstance(theme, dict):
        return theme
    return {}
